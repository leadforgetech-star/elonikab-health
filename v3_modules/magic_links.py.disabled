"""Magic link : connexion automatique via URL."""
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


