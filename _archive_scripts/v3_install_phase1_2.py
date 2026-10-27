"""
v3_install_phase1_2.py
Elokinab Health V3 - Phase 1 (backup + migration DB) + Phase 2 (auth).

Ne casse rien : tout est additif.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "database.db"
MAIN = BASE / "main.py"
MODULES = BASE / "v3_modules"
STATIC = BASE / "static"

# ============================================================
# 0. BACKUP DATE
# ============================================================
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_v3_" + stamp)
backup.mkdir(parents=True, exist_ok=True)

shutil.copy2(DB_PATH, backup / "database.db")
shutil.copy2(MAIN, backup / "main.py")
for f in STATIC.glob("*.html"):
    shutil.copy2(f, backup / ("static_" + f.name))
for f in STATIC.glob("*.js"):
    shutil.copy2(f, backup / ("static_" + f.name))
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. DOSSIER v3_modules
# ============================================================
MODULES.mkdir(exist_ok=True)
(MODULES / "__init__.py").write_text("", encoding="utf-8")

# ============================================================
# 2. migrations.py
# ============================================================
MIGRATIONS = '''"""Migrations sures et idempotentes pour Elokinab Health V3."""
import sqlite3


SCHEMA_V3 = [
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        phone TEXT DEFAULT '',
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'PATIENT',
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT NOT NULL UNIQUE,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS addresses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        label TEXT DEFAULT '',
        full_address TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        is_default INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS professional_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        structure_name TEXT NOT NULL,
        structure_type TEXT NOT NULL,
        manager_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT DEFAULT '',
        address TEXT DEFAULT '',
        latitude REAL,
        longitude REAL,
        notes TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'PENDING',
        reviewed_at TEXT,
        reviewed_by INTEGER,
        rejection_reason TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER,
        product_name TEXT NOT NULL,
        unit_price REAL NOT NULL,
        quantity INTEGER NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS prescriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING',
        reviewed_at TEXT,
        reviewed_by INTEGER,
        comment TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        payment_method TEXT NOT NULL DEFAULT 'MANUAL',
        payment_number TEXT DEFAULT '',
        payment_name TEXT DEFAULT '',
        proof_file TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'PENDING',
        submitted_at TEXT,
        verified_at TEXT,
        verified_by INTEGER,
        rejection_reason TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS deliveries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL UNIQUE,
        vehicle_type TEXT NOT NULL,
        driver_id INTEGER,
        status TEXT NOT NULL DEFAULT 'ASSIGNED',
        assigned_at TEXT,
        accepted_at TEXT,
        picked_up_at TEXT,
        delivered_at TEXT,
        failed_at TEXT,
        notes TEXT DEFAULT '',
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        order_id INTEGER,
        channel TEXT NOT NULL DEFAULT 'IN_APP',
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        is_read INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        target_type TEXT DEFAULT '',
        target_id INTEGER,
        details TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )""",
    """CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)""",
    """CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)""",
    """CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)""",
    """CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)""",
]


ORDERS_NEW_COLS = [
    ("user_id", "INTEGER"),
    ("customer_type", "TEXT DEFAULT 'PARTICULIER'"),
    ("delivery_vehicle_type", "TEXT DEFAULT 'MOTO'"),
    ("payment_status", "TEXT DEFAULT 'PENDING'"),
    ("delivery_status", "TEXT DEFAULT 'NONE'"),
    ("prescription_status", "TEXT DEFAULT 'NONE'"),
    ("professional_id", "INTEGER"),
]

PRODUCTS_NEW_COLS = [
    ("stock_quantity", "INTEGER DEFAULT 0"),
    ("stock_min_threshold", "INTEGER DEFAULT 5"),
    ("is_active", "INTEGER DEFAULT 1"),
]

SETTINGS_NEW_COLS = [
    ("motorbike_base_fee", "REAL DEFAULT 300"),
    ("motorbike_price_per_km", "REAL DEFAULT 100"),
    ("motorbike_minimum_fee", "REAL DEFAULT 300"),
    ("motorbike_max_distance", "REAL DEFAULT 0"),
    ("car_base_fee", "REAL DEFAULT 1000"),
    ("car_price_per_km", "REAL DEFAULT 250"),
    ("car_minimum_fee", "REAL DEFAULT 1000"),
    ("car_max_distance", "REAL DEFAULT 0"),
    ("payment_number", "TEXT DEFAULT ''"),
    ("payment_name", "TEXT DEFAULT ''"),
    ("pharmacy_name", "TEXT DEFAULT 'Elokinab Health'"),
    ("pharmacy_phone", "TEXT DEFAULT ''"),
    ("pharmacy_address", "TEXT DEFAULT ''"),
]


def _cols(cur, table):
    return {row[1] for row in cur.execute("PRAGMA table_info(" + table + ")").fetchall()}


def _tables(cur):
    return {row[0] for row in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}


def _add_columns(cur, table, cols):
    existing = _cols(cur, table)
    for name, ddl in cols:
        if name not in existing:
            cur.execute("ALTER TABLE " + table + " ADD COLUMN " + name + " " + ddl)


def run_migrations(db_path):
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    for stmt in SCHEMA_V3:
        cur.execute(stmt)
    tables = _tables(cur)
    if "orders" in tables:
        _add_columns(cur, "orders", ORDERS_NEW_COLS)
    if "products" in tables:
        _add_columns(cur, "products", PRODUCTS_NEW_COLS)
    if "pharmacy_settings" in tables:
        _add_columns(cur, "pharmacy_settings", SETTINGS_NEW_COLS)
    conn.commit()
    conn.close()
    return True
'''
(MODULES / "migrations.py").write_text(MIGRATIONS, encoding="utf-8")
print("[OK] v3_modules/migrations.py")

# ============================================================
# 3. auth.py
# ============================================================
AUTH = '''"""Auth Elokinab Health V3 - stdlib uniquement (scrypt + sessions)."""
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Cookie, HTTPException, Response
from pydantic import BaseModel


SESSION_COOKIE = "elokinab_session"
SESSION_TTL_DAYS = 30

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

        response.set_cookie(SESSION_COOKIE, token, httponly=True,
                            samesite="lax", max_age=SESSION_TTL_DAYS * 86400)
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

        response.set_cookie(SESSION_COOKIE, token, httponly=True,
                            samesite="lax", max_age=SESSION_TTL_DAYS * 86400)
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
'''
(MODULES / "auth.py").write_text(AUTH, encoding="utf-8")
print("[OK] v3_modules/auth.py")

# ============================================================
# 4. PATCH main.py
# ============================================================
src = MAIN.read_text(encoding="utf-8")

if "v3_modules" not in src:
    injection = (
        "\n# ============================================================\n"
        "# V3 - Migrations + Auth\n"
        "# ============================================================\n"
        "from v3_modules.migrations import run_migrations\n"
        "from v3_modules.auth import install_auth\n"
        "\n"
        "init_db()\n"
        "run_migrations(DB_PATH)\n"
        "require_role = install_auth(app, get_db, row_to_dict)\n"
        "# ============================================================\n"
    )
    # Retirer l'ancien "init_db()" orphelin pour eviter double appel (idempotent de toute facon)
    marker = "\ninit_db()\n"
    if marker in src:
        src = src.replace(marker, injection + "\n", 1)
        print("[OK] main.py -> init_db() remplace par bloc V3")
    else:
        # Fallback : inserer avant __main__
        anchor = 'if __name__ == "__main__":'
        if anchor in src:
            src = src.replace(anchor, injection + "\n" + anchor, 1)
            print("[OK] main.py -> bloc V3 insere avant __main__")
        else:
            print("[!] Point d'insertion introuvable dans main.py")
    MAIN.write_text(src, encoding="utf-8")
else:
    print("[i] main.py deja patche V3")

# ============================================================
# 5. FRONTEND - login / register
# ============================================================
AUTH_CSS = '''
*{box-sizing:border-box}
body.auth-body{
  margin:0;font-family:"Segoe UI",system-ui,sans-serif;
  background:linear-gradient(135deg,#0f9d76,#0a7a5a);
  min-height:100vh;display:flex;align-items:center;justify-content:center;
  padding:20px;color:#0f2620;
}
.auth-card{
  background:#fff;border-radius:20px;padding:32px;
  width:100%;max-width:420px;box-shadow:0 20px 60px rgba(0,0,0,.25);
}
.auth-logo{
  display:flex;align-items:center;gap:12px;margin-bottom:22px;
}
.auth-logo-mark{
  width:44px;height:44px;border-radius:12px;
  background:linear-gradient(135deg,#0f9d76,#37c79c);
  color:#fff;font-size:24px;font-weight:800;
  display:flex;align-items:center;justify-content:center;
}
.auth-logo-text{line-height:1.15}
.auth-logo-text strong{font-size:17px;display:block}
.auth-logo-text small{font-size:11px;color:#6c8a80;text-transform:uppercase;letter-spacing:.08em}
.auth-card h1{font-size:22px;margin:0 0 6px}
.auth-card p.sub{color:#6c8a80;font-size:14px;margin:0 0 22px}
.auth-field{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.auth-field label{font-size:13px;font-weight:700}
.auth-field input,.auth-field select{
  padding:12px 14px;border:1px solid #ddece6;border-radius:11px;
  font-size:15px;font-family:inherit;outline:none;background:#fff;color:#0f2620;
}
.auth-field input:focus,.auth-field select:focus{border-color:#0f9d76}
.auth-btn{
  width:100%;padding:14px;border:0;border-radius:12px;
  background:#0f9d76;color:#fff;font-weight:700;font-size:15px;
  cursor:pointer;transition:.15s;
}
.auth-btn:hover{background:#0a7a5a}
.auth-btn:disabled{opacity:.6;cursor:not-allowed}
.auth-msg{
  padding:10px 12px;border-radius:10px;font-size:13px;margin-bottom:12px;
  background:#fdecec;color:#b23c3c;border:1px solid #f6d2d2;
}
.auth-msg.ok{background:#e8f7f1;color:#0a7a5a;border-color:#c7e9dc}
.auth-alt{text-align:center;font-size:13px;color:#6c8a80;margin-top:16px}
.auth-alt a{color:#0a7a5a;font-weight:700;text-decoration:none}
.auth-back{text-align:center;margin-top:16px;font-size:13px}
.auth-back a{color:#6c8a80;text-decoration:none}
.hidden{display:none!important}
'''
(STATIC / "auth.css").write_text(AUTH_CSS, encoding="utf-8")
print("[OK] static/auth.css")

LOGIN_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Connexion - Elokinab Health</title>
<link rel="stylesheet" href="/static/auth.css">
</head>
<body class="auth-body">
<form class="auth-card" id="login-form">
  <div class="auth-logo">
    <div class="auth-logo-mark">+</div>
    <div class="auth-logo-text">
      <strong>Elokinab Health</strong>
      <small>Pharmacie digitale</small>
    </div>
  </div>
  <h1>Connexion</h1>
  <p class="sub">Accedez a votre espace personnel.</p>
  <div id="msg" class="auth-msg hidden"></div>
  <div class="auth-field">
    <label for="email">Email</label>
    <input type="email" id="email" name="email" required autocomplete="email">
  </div>
  <div class="auth-field">
    <label for="password">Mot de passe</label>
    <input type="password" id="password" name="password" required autocomplete="current-password">
  </div>
  <button class="auth-btn" id="btn" type="submit">Se connecter</button>
  <div class="auth-alt">Pas de compte ? <a href="/static/register.html">Creer un compte</a></div>
  <div class="auth-back"><a href="/">Retour a l'accueil</a></div>
</form>
<script src="/static/auth.js"></script>
<script>EH.initLogin();</script>
</body>
</html>
'''
(STATIC / "login.html").write_text(LOGIN_HTML, encoding="utf-8")
print("[OK] static/login.html")

REGISTER_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Creer un compte - Elokinab Health</title>
<link rel="stylesheet" href="/static/auth.css">
</head>
<body class="auth-body">
<form class="auth-card" id="register-form">
  <div class="auth-logo">
    <div class="auth-logo-mark">+</div>
    <div class="auth-logo-text">
      <strong>Elokinab Health</strong>
      <small>Pharmacie digitale</small>
    </div>
  </div>
  <h1>Creer un compte</h1>
  <p class="sub">Particulier ou structure professionnelle.</p>
  <div id="msg" class="auth-msg hidden"></div>
  <div class="auth-field">
    <label for="role">Type de compte</label>
    <select id="role" name="role">
      <option value="PATIENT">Particulier</option>
      <option value="PROFESSIONNEL">Professionnel de sante</option>
    </select>
  </div>
  <div class="auth-field">
    <label for="full_name">Nom complet</label>
    <input type="text" id="full_name" name="full_name" required autocomplete="name">
  </div>
  <div class="auth-field">
    <label for="email">Email</label>
    <input type="email" id="email" name="email" required autocomplete="email">
  </div>
  <div class="auth-field">
    <label for="phone">Telephone</label>
    <input type="tel" id="phone" name="phone" placeholder="Ex : 90 00 00 00" autocomplete="tel">
  </div>
  <div class="auth-field">
    <label for="password">Mot de passe (6 caracteres minimum)</label>
    <input type="password" id="password" name="password" required minlength="6" autocomplete="new-password">
  </div>
  <button class="auth-btn" id="btn" type="submit">Creer mon compte</button>
  <div class="auth-alt">Deja inscrit ? <a href="/static/login.html">Se connecter</a></div>
  <div class="auth-back"><a href="/">Retour a l'accueil</a></div>
</form>
<script src="/static/auth.js"></script>
<script>EH.initRegister();</script>
</body>
</html>
'''
(STATIC / "register.html").write_text(REGISTER_HTML, encoding="utf-8")
print("[OK] static/register.html")

AUTH_JS = '''var EH = (function () {
  function $(id) { return document.getElementById(id); }
  function showMsg(text, ok) {
    var m = $("msg");
    if (!m) return;
    m.textContent = text;
    m.className = "auth-msg" + (ok ? " ok" : "");
  }
  function hideMsg() { var m = $("msg"); if (m) m.className = "auth-msg hidden"; }

  function post(path, body) {
    return fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (r) {
      return r.json().then(function (data) {
        if (!r.ok) throw new Error(data.detail || "Erreur serveur");
        return data;
      });
    });
  }

  function initLogin() {
    var form = $("login-form");
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      hideMsg();
      var btn = $("btn");
      btn.disabled = true; btn.textContent = "Connexion...";
      post("/api/auth/login", {
        email: $("email").value.trim(),
        password: $("password").value
      }).then(function () {
        showMsg("Connexion reussie. Redirection...", true);
        setTimeout(function () { window.location.href = "/"; }, 600);
      }).catch(function (e) {
        showMsg(e.message);
        btn.disabled = false; btn.textContent = "Se connecter";
      });
    });
  }

  function initRegister() {
    var form = $("register-form");
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      hideMsg();
      var btn = $("btn");
      btn.disabled = true; btn.textContent = "Creation...";
      post("/api/auth/register", {
        role: $("role").value,
        full_name: $("full_name").value.trim(),
        email: $("email").value.trim(),
        phone: $("phone").value.trim(),
        password: $("password").value
      }).then(function () {
        showMsg("Compte cree. Redirection...", true);
        setTimeout(function () { window.location.href = "/"; }, 600);
      }).catch(function (e) {
        showMsg(e.message);
        btn.disabled = false; btn.textContent = "Creer mon compte";
      });
    });
  }

  return { initLogin: initLogin, initRegister: initRegister };
})();
'''
(STATIC / "auth.js").write_text(AUTH_JS, encoding="utf-8")
print("[OK] static/auth.js")

# ============================================================
# 6. RESUME
# ============================================================
print()
print("=" * 60)
print("PHASE 1 + 2 installees.")
print("=" * 60)
print()
print("Backup :", backup.name)
print()
print("Fichiers crees :")
print("  v3_modules/migrations.py")
print("  v3_modules/auth.py")
print("  static/login.html")
print("  static/register.html")
print("  static/auth.js")
print("  static/auth.css")
print()
print("Fichier modifie :")
print("  main.py")
print()
print("Tables ajoutees :")
print("  users, sessions, addresses, professional_profiles,")
print("  order_items, prescriptions, payments, deliveries,")
print("  notifications, audit_logs")
print()
print("Colonnes ajoutees :")
print("  orders : user_id, customer_type, delivery_vehicle_type,")
print("           payment_status, delivery_status, prescription_status,")
print("           professional_id")
print("  products : stock_quantity, stock_min_threshold, is_active")
print("  pharmacy_settings : moto/car fees, payment_number/name,")
print("                      pharmacy_name/phone/address")
print()
print("Routes ajoutees :")
print("  POST   /api/auth/register")
print("  POST   /api/auth/login")
print("  POST   /api/auth/logout")
print("  GET    /api/auth/me")
print("  PATCH  /api/auth/me")
print("  GET    /api/auth/roles")
print("  GET    /static/login.html")
print("  GET    /static/register.html")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  python main.py")