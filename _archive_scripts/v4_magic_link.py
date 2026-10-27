"""
v4_magic_link.py
Genere des liens uniques qui connectent automatiquement un utilisateur.
Utile pour partager un acces demo a un collegue.
"""
from pathlib import Path
import datetime
import shutil
import sqlite3

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
MODULES = BASE / "v3_modules"
DB = BASE / "database.db"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_magic_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAIN, backup / "main.py")
shutil.copy2(DB, backup / "database.db")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. Table magic_links
# ============================================================
conn = sqlite3.connect(DB)
conn.execute("""
    CREATE TABLE IF NOT EXISTS magic_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT NOT NULL UNIQUE,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT,
        max_uses INTEGER DEFAULT 0,
        used_count INTEGER DEFAULT 0,
        revoked INTEGER DEFAULT 0,
        note TEXT DEFAULT ''
    )
""")
conn.execute("CREATE INDEX IF NOT EXISTS idx_magic_token ON magic_links(token)")
conn.commit()
conn.close()
print("[OK] table magic_links creee")

# ============================================================
# 2. Module magic_links
# ============================================================
MAGIC = '''"""Magic link : connexion automatique via URL."""
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Response
from pydantic import BaseModel

SESSION_COOKIE = "elokinab_session"
SESSION_TTL_DAYS = 365


class MagicCreate(BaseModel):
    user_id: int
    expires_in_days: Optional[int] = 30
    max_uses: int = 0  # 0 = illimite
    note: str = ""


def install_magic_links(app, get_db, require_role):
    def _row(r):
        return {k: r[k] for k in r.keys()} if r else None

    # --------------------------------------------------------
    # Creer un magic link (ADMIN ou PHARMACIEN)
    # --------------------------------------------------------
    @app.post("/api/admin/magic-link")
    def create_magic_link(payload: MagicCreate,
                          user=Depends(require_role("ADMIN", "PHARMACIEN"))):
        conn = get_db()
        try:
            target = conn.execute(
                "SELECT id, email, role FROM users WHERE id=? AND is_active=1",
                (payload.user_id,)
            ).fetchone()
            if target is None:
                raise HTTPException(404, "Utilisateur introuvable ou inactif")

            token = secrets.token_urlsafe(32)
            now = datetime.now()
            expires = None
            if payload.expires_in_days and payload.expires_in_days > 0:
                expires = (now + timedelta(days=payload.expires_in_days)).isoformat(timespec="seconds")

            cur = conn.execute(
                "INSERT INTO magic_links (token, user_id, created_at, expires_at,"
                " max_uses, used_count, revoked, note)"
                " VALUES (?, ?, ?, ?, ?, 0, 0, ?)",
                (token, payload.user_id, now.isoformat(timespec="seconds"),
                 expires, payload.max_uses, payload.note)
            )
            conn.commit()
            link_id = cur.lastrowid
            row = conn.execute(
                "SELECT * FROM magic_links WHERE id=?", (link_id,)
            ).fetchone()
        finally:
            conn.close()

        return {
            **_row(row),
            "access_url": "/acces/" + token,
            "target_email": target["email"],
            "target_role": target["role"]
        }

    # --------------------------------------------------------
    # Lister les magic links actifs
    # --------------------------------------------------------
    @app.get("/api/admin/magic-links")
    def list_magic_links(user=Depends(require_role("ADMIN", "PHARMACIEN"))):
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT ml.*, u.email AS user_email, u.role AS user_role,"
                " u.full_name AS user_name"
                " FROM magic_links ml JOIN users u ON u.id = ml.user_id"
                " ORDER BY ml.id DESC LIMIT 100"
            ).fetchall()
        finally:
            conn.close()
        return [_row(r) for r in rows]

    # --------------------------------------------------------
    # Revoquer un magic link
    # --------------------------------------------------------
    @app.delete("/api/admin/magic-link/{link_id}")
    def revoke_magic_link(link_id: int,
                          user=Depends(require_role("ADMIN", "PHARMACIEN"))):
        conn = get_db()
        try:
            conn.execute("UPDATE magic_links SET revoked=1 WHERE id=?", (link_id,))
            conn.commit()
        finally:
            conn.close()
        return {"ok": True}

    # --------------------------------------------------------
    # Acces public : /acces/{token}
    # --------------------------------------------------------
    @app.get("/acces/{token}", include_in_schema=False)
    def access_magic_link(token: str):
        from fastapi.responses import RedirectResponse

        conn = get_db()
        try:
            ml = conn.execute(
                "SELECT * FROM magic_links WHERE token=?", (token,)
            ).fetchone()
            if ml is None:
                raise HTTPException(404, "Lien invalide")
            if ml["revoked"]:
                raise HTTPException(403, "Lien revoque")
            if ml["expires_at"]:
                try:
                    exp = datetime.fromisoformat(ml["expires_at"])
                    if datetime.now() > exp:
                        raise HTTPException(403, "Lien expire")
                except ValueError:
                    pass
            if ml["max_uses"] and ml["used_count"] >= ml["max_uses"]:
                raise HTTPException(403, "Lien deja utilise")

            user = conn.execute(
                "SELECT * FROM users WHERE id=? AND is_active=1", (ml["user_id"],)
            ).fetchone()
            if user is None:
                raise HTTPException(403, "Utilisateur inactif")

            # Incrementer usage
            conn.execute(
                "UPDATE magic_links SET used_count = used_count + 1 WHERE id=?",
                (ml["id"],)
            )

            # Creer une session
            session_token = secrets.token_urlsafe(48)
            now = datetime.now()
            exp = now + timedelta(days=SESSION_TTL_DAYS)
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at, expires_at)"
                " VALUES (?, ?, ?, ?)",
                (session_token, user["id"],
                 now.isoformat(timespec="seconds"),
                 exp.isoformat(timespec="seconds"))
            )
            conn.commit()

            # Redirection selon le role
            role = user["role"]
            if role == "PROFESSIONNEL":
                target = "/professionnel"
            elif role in ("PHARMACIEN", "ADMIN"):
                target = "/pharmacien"
            else:
                target = "/"

            resp = RedirectResponse(url=target, status_code=302)
            resp.set_cookie(
                SESSION_COOKIE, session_token,
                httponly=True, samesite="none", secure=True,
                max_age=SESSION_TTL_DAYS * 86400, path="/"
            )
            return resp
        finally:
            conn.close()


'''
(MODULES / "magic_links.py").write_text(MAGIC, encoding="utf-8")
print("[OK] v3_modules/magic_links.py")

# ============================================================
# 3. Patch main.py
# ============================================================
src = MAIN.read_text(encoding="utf-8")
if "install_magic_links" not in src:
    old = "install_b2b(app, get_db, require_role, UPLOADS_DIR)"
    new = (old + "\n"
           "from v3_modules.magic_links import install_magic_links\n"
           "install_magic_links(app, get_db, require_role)")
    if old in src:
        src = src.replace(old, new, 1)
        MAIN.write_text(src, encoding="utf-8")
        print("[OK] main.py -> install_magic_links")
    else:
        print("[!] anchor install_b2b introuvable")
else:
    print("[i] main.py deja patche")

# ============================================================
# 4. Script helper : generer un lien pour un utilisateur
# ============================================================
HELPER = '''"""
generate_link.py - Genere un magic link pour un utilisateur.

Usage :
    python generate_link.py <email_ou_id>
    python generate_link.py pro@test.tg
    python generate_link.py 17 --days 7
    python generate_link.py pro@test.tg --once
"""
import argparse
import secrets
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "database.db"

PUBLIC_URL = "https://radar-broader-met-compromise.trycloudflare.com"  # <-- a modifier


def find_user(conn, key):
    if str(key).isdigit():
        return conn.execute("SELECT * FROM users WHERE id=?", (int(key),)).fetchone()
    return conn.execute(
        "SELECT * FROM users WHERE email=?", (str(key).lower(),)
    ).fetchone()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("user", help="Email ou ID de l'utilisateur")
    ap.add_argument("--days", type=int, default=30, help="Duree de validite en jours (0 = jamais)")
    ap.add_argument("--once", action="store_true", help="Utilisable une seule fois")
    ap.add_argument("--note", default="", help="Note")
    ap.add_argument("--url", default=PUBLIC_URL, help="URL publique de base")
    args = ap.parse_args()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        user = find_user(conn, args.user)
        if user is None:
            print("[ERREUR] Utilisateur introuvable :", args.user)
            return 1
        if not user["is_active"]:
            print("[ERREUR] Utilisateur inactif")
            return 1

        token = secrets.token_urlsafe(32)
        now = datetime.now()
        expires = None
        if args.days > 0:
            expires = (now + timedelta(days=args.days)).isoformat(timespec="seconds")
        max_uses = 1 if args.once else 0

        conn.execute(
            "INSERT INTO magic_links (token, user_id, created_at, expires_at,"
            " max_uses, used_count, revoked, note)"
            " VALUES (?, ?, ?, ?, ?, 0, 0, ?)",
            (token, user["id"], now.isoformat(timespec="seconds"),
             expires, max_uses, args.note)
        )
        conn.commit()
    finally:
        conn.close()

    full_url = args.url.rstrip("/") + "/acces/" + token
    print()
    print("=" * 70)
    print(" LIEN D'ACCES DIRECT")
    print("=" * 70)
    print(" Utilisateur : " + user["email"])
    print(" Nom         : " + (user["full_name"] or ""))
    print(" Role        : " + user["role"])
    print(" Duree       : " + (str(args.days) + " jours" if args.days > 0 else "illimitee"))
    print(" Usage       : " + ("1 fois" if args.once else "illimite"))
    print()
    print(" URL A ENVOYER :")
    print()
    print("   " + full_url)
    print()
    print("=" * 70)
    print(" A envoyer par WhatsApp / SMS / Email au collegue.")
    print(" Quiconque a ce lien peut se connecter avec ce compte.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''
(BASE / "generate_link.py").write_text(HELPER, encoding="utf-8")
print("[OK] generate_link.py")

print()
print("=" * 60)
print("MAGIC LINK INSTALLE")
print("=" * 60)
print()
print("Routes admin (ADMIN/PHARMACIEN) :")
print("  POST   /api/admin/magic-link          (creer)")
print("  GET    /api/admin/magic-links         (lister)")
print("  DELETE /api/admin/magic-link/{id}     (revoquer)")
print()
print("Route publique :")
print("  GET    /acces/{token}                 (auto-login + redirect)")
print()
print("Utilitaire :")
print("  python generate_link.py <email>")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print()
print("Puis genere un lien :")
print("  python generate_link.py pro@test.tg")