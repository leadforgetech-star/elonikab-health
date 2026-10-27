"""Auth Elokinab Health V3 - stdlib uniquement (scrypt + sessions)."""
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Cookie, HTTPException, Response
from pydantic import BaseModel


SESSION_COOKIE = "elokinab_session"
SESSION_TTL_DAYS = 365

VALID_ROLES = {
    "PATIENT", "PROFESSIONNEL", "PHARMACIEN",
    "LIVREUR_MOTO", "CHAUFFEUR", "ADMIN",
}

PUBLIC_ROLES = {"PATIENT", "PROFESSIONNEL"}


# --- Hashing ---

def hash_password(password):
    if not password or len(password) < 6:
        raise ValueError("Mot de passe trop court (6 caracteres minimum)")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt,
                            n=2**14, r=8, p=1, dklen=32)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password, stored):
    try:
        scheme, salt_b64, digest_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt,
                                n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(expected, actual)
    except Exception:
        return False


def new_token():
    return secrets.token_urlsafe(48)


# --- Pydantic models ---

class RegisterRequest(BaseModel):
    email: str
    phone: str = ""
    password: str
    full_name: str
    role: str = "PATIENT"


class LoginRequest(BaseModel):
    email: str
    password: str


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None


# --- Installation ---

def install_auth(app, get_db, row_to_dict):
    """Enregistre les routes /api/auth/* sur app.
    Retourne une factory require_role(*roles)."""

    def _public(row):
        if row is None:
            return None
        d = {k: row[k] for k in row.keys()}
        d.pop("password_hash", None)
        return d

    def _create_session(conn, user_id):
        token = new_token()
        now = datetime.now()
        exp = now + timedelta(days=SESSION_TTL_DAYS)
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at)"
            " VALUES (?, ?, ?, ?)",
            (token, user_id,
             now.isoformat(timespec="seconds"),
             exp.isoformat(timespec="seconds")),
        )
        return token

    def load_user_from_cookie(session_token):
        if not session_token:
            return None
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id"
                " WHERE s.token = ? AND s.expires_at > ?",
                (session_token, datetime.now().isoformat(timespec="seconds")),
            ).fetchone()
            return row
        finally:
            conn.close()

    def get_current_user(session_token: Optional[str] = Cookie(None, alias=SESSION_COOKIE)):
        row = load_user_from_cookie(session_token)
        if row is None:
            return None
        return _public(row)

    def require_role(*roles):
        def dep(session_token: Optional[str] = Cookie(None, alias=SESSION_COOKIE)):
            row = load_user_from_cookie(session_token)
            if row is None:
                raise HTTPException(401, "Non authentifie")
            if not row["is_active"]:
                raise HTTPException(403, "Compte desactive")
            if row["role"] not in roles:
                raise HTTPException(403, "Acces refuse pour ce role")
            return _public(row)
        return dep

    # ---- ROUTES ----

    @app.post("/api/auth/register")
    def register(payload: RegisterRequest, response: Response):
        email = payload.email.strip().lower()
        if "@" not in email or len(email) < 5:
            raise HTTPException(400, "Email invalide")
        if payload.role not in VALID_ROLES:
            raise HTTPException(400, "Role invalide")
        if payload.role not in PUBLIC_ROLES:
            raise HTTPException(403, "Ce role ne peut pas etre cree publiquement")

        conn = get_db()
        try:
            if conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
                raise HTTPException(409, "Un compte existe deja avec cet email")
            try:
                pwd_hash = hash_password(payload.password)
            except ValueError as e:
                raise HTTPException(400, str(e))
            now = datetime.now().isoformat(timespec="seconds")
            cur = conn.execute(
                "INSERT INTO users (email, phone, password_hash, full_name,"
                " role, is_active, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)",
                (email, payload.phone.strip(), pwd_hash,
                 payload.full_name.strip(), payload.role, now),
            )
            user_id = cur.lastrowid
            token = _create_session(conn, user_id)
            conn.commit()
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        finally:
            conn.close()

        response.set_cookie(
            SESSION_COOKIE, token,
            httponly=True, samesite="none", secure=True,
            max_age=SESSION_TTL_DAYS * 86400, path="/"
        )
        return {"user": _public(row)}

    @app.post("/api/auth/login")
    def login(payload: LoginRequest, response: Response):
        email = payload.email.strip().lower()
        conn = get_db()
        try:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if row is None or not verify_password(payload.password, row["password_hash"]):
                raise HTTPException(401, "Email ou mot de passe incorrect")
            if not row["is_active"]:
                raise HTTPException(403, "Compte desactive")
            token = _create_session(conn, row["id"])
            conn.commit()
        finally:
            conn.close()

        response.set_cookie(
            SESSION_COOKIE, token,
            httponly=True, samesite="none", secure=True,
            max_age=SESSION_TTL_DAYS * 86400, path="/"
        )
        return {"user": _public(row)}

    @app.post("/api/auth/logout")
    def logout(response: Response,
               session_token: Optional[str] = Cookie(None, alias=SESSION_COOKIE)):
        if session_token:
            conn = get_db()
            try:
                conn.execute("DELETE FROM sessions WHERE token = ?", (session_token,))
                conn.commit()
            finally:
                conn.close()
        response.delete_cookie(SESSION_COOKIE)
        return {"ok": True}

    @app.get("/api/auth/me")
    def me(session_token: Optional[str] = Cookie(None, alias=SESSION_COOKIE)):
        row = load_user_from_cookie(session_token)
        if row is None:
            raise HTTPException(401, "Non authentifie")
        return _public(row)

    @app.patch("/api/auth/me")
    def update_me(payload: UpdateProfileRequest,
                  session_token: Optional[str] = Cookie(None, alias=SESSION_COOKIE)):
        row = load_user_from_cookie(session_token)
        if row is None:
            raise HTTPException(401, "Non authentifie")
        fields = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None}
        if not fields:
            return _public(row)
        sets = ", ".join(k + " = ?" for k in fields.keys())
        vals = list(fields.values())
        conn = get_db()
        try:
            conn.execute(
                "UPDATE users SET " + sets + ", updated_at = ? WHERE id = ?",
                vals + [datetime.now().isoformat(timespec="seconds"), row["id"]],
            )
            conn.commit()
            updated = conn.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()
        finally:
            conn.close()
        return _public(updated)

    # ---- Endpoints d'information ----

    @app.get("/api/auth/roles")
    def list_roles():
        return {"roles": sorted(VALID_ROLES), "public_roles": sorted(PUBLIC_ROLES)}

    return require_role
