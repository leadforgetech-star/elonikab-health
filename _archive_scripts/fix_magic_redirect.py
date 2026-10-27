"""
fix_magic_redirect.py
Remplace le 302 cacheable par une page HTML qui fait
window.location.replace vers /professionnel?_v=<timestamp>
=> URL unique a chaque fois, aucun cache possible.
"""
from pathlib import Path
import re
import shutil

BASE = Path(__file__).resolve().parent
MAGIC = BASE / "v3_modules" / "magic_links.py"
shutil.copy2(MAGIC, MAGIC.with_suffix(".py.bak3"))
print("[OK] Backup ->", MAGIC.with_suffix(".py.bak3").name)

src = MAGIC.read_text(encoding="utf-8")

# ============================================================
# 1. Localiser le bloc de la fonction access_magic_link
# ============================================================
pattern = re.compile(
    r'(@app\.get\("/acces/\{token\}"[^\n]*\)\n'
    r'def access_magic_link\(token: str\):.*?)(?=\n@app\.|\n\nclass |\n\ndef |\Z)',
    re.DOTALL,
)

m = pattern.search(src)
if not m:
    print("[!] access_magic_link introuvable dans magic_links.py")
    raise SystemExit(1)

old_block = m.group(1)
print("[i] Ancien bloc (extrait) :")
print("   " + old_block.split("\n")[0][:80])
print("   " + old_block.split("\n")[1][:80])

# ============================================================
# 2. Nouveau bloc : retourne HTML au lieu de 302
# ============================================================
new_block = '''@app.get("/acces/{token}", include_in_schema=False)
def access_magic_link(token: str):
    import time
    from fastapi.responses import HTMLResponse

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

        # Creer session
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

        # Cible selon role
        role = user["role"]
        if role == "PROFESSIONNEL":
            target = "/professionnel"
        elif role in ("PHARMACIEN", "ADMIN"):
            target = "/pharmacien"
        else:
            target = "/"

        # HTML qui force un rechargement avec cache-bust
        cb = str(int(time.time() * 1000))
        html = (
            '<!DOCTYPE html>'
            '<html lang="fr"><head><meta charset="utf-8">'
            '<title>Redirection...</title>'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<style>'
            'body{font-family:-apple-system,"Segoe UI",system-ui,sans-serif;'
            'display:flex;align-items:center;justify-content:center;'
            'height:100vh;margin:0;background:#F5F8FC;color:#64748B}'
            '.sp{width:40px;height:40px;border:3px solid #E2E8F0;'
            'border-top-color:#1A4A7E;border-radius:50%;'
            'animation:s 1s linear infinite}'
            '@keyframes s{to{transform:rotate(360deg)}}'
            '</style></head><body><div class="sp"></div>'
            '<script>'
            'window.location.replace("' + target + '?_v=' + cb + '");'
            '</script>'
            '</body></html>'
        )

        resp = HTMLResponse(content=html)
        resp.set_cookie(
            SESSION_COOKIE, session_token,
            httponly=True, samesite="none", secure=True,
            max_age=SESSION_TTL_DAYS * 86400, path="/"
        )
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
    finally:
        conn.close()'''

src = pattern.sub(new_block + "\n", src, count=1)
MAGIC.write_text(src, encoding="utf-8")
print("[OK] access_magic_link remplace")

# ============================================================
# 3. Verification
# ============================================================
check = MAGIC.read_text(encoding="utf-8")
ok1 = "window.location.replace" in check
ok2 = "?_v=" in check
ok3 = "no-store, no-cache" in check
print()
print("=" * 60)
print("VERIFICATION")
print("=" * 60)
print("  window.location.replace     :", ok1)
print("  ?_v= cache bust             :", ok2)
print("  Cache-Control no-store      :", ok3)
print()
print("=" * 60)
print("FIX APPLIQUE")
print("=" * 60)
print()
print("Comportement :")
print("  /acces/{token}")
print("    -> HTML minimal (spinner)")
print("    -> JS: window.location.replace('/professionnel?_v=<ms>')")
print("    -> URL unique => aucun cache navigateur possible")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print("=" * 60)