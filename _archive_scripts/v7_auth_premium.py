"""
v7_auth_premium.py
Auth premium : forgot password, login par tel, inscription 3 etapes.
Ne casse rien : routes et pages actuelles continuent de fonctionner.
"""
from pathlib import Path
import datetime
import re
import shutil
import sqlite3

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
MAIN = BASE / "main.py"
AUTH = BASE / "v3_modules" / "auth.py"
DB = BASE / "database.db"

# ============================================================
# 0. Backup
# ============================================================
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_v7_auth_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(DB, backup / "database.db")
shutil.copy2(MAIN, backup / "main.py")
shutil.copy2(AUTH, backup / "auth.py")
for f in ("login.html", "register.html"):
    p = STATIC / f
    if p.exists():
        shutil.copy2(p, backup / f)
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. Table password_resets
# ============================================================
conn = sqlite3.connect(DB)
conn.execute("""
    CREATE TABLE IF NOT EXISTS password_resets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT NOT NULL UNIQUE,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        used INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
""")
conn.execute("CREATE INDEX IF NOT EXISTS idx_pwreset_token ON password_resets(token)")
conn.commit()

# Nettoyer les anciens tokens
cutoff = (datetime.datetime.now() - datetime.timedelta(days=2)).isoformat(timespec="seconds")
conn.execute("DELETE FROM password_resets WHERE created_at < ?", (cutoff,))
conn.commit()
conn.close()
print("[OK] Table password_resets")

# ============================================================
# 2. Backend : forgot / reset / login par tel / register etabli
# ============================================================
src = AUTH.read_text(encoding="utf-8")

# 2.1 Etendre RegisterRequest
old_reg = '''class RegisterRequest(BaseModel):
    email: str
    phone: str = ""
    password: str
    full_name: str
    role: str = "PATIENT"'''
new_reg = '''class RegisterRequest(BaseModel):
    email: str
    phone: str = ""
    password: str
    full_name: str
    role: str = "PATIENT"
    # Optionnels : utilises si role == PROFESSIONNEL
    establishment_type: str = ""
    establishment_name: str = ""
    establishment_city: str = ""
    establishment_responsible: str = ""


class ForgotRequest(BaseModel):
    identifier: str  # email ou telephone


class ResetRequest(BaseModel):
    token: str
    new_password: str'''
if old_reg in src:
    src = src.replace(old_reg, new_reg, 1)
    print("[OK] auth.py -> RegisterRequest etendu")

# 2.2 Modifier login pour accepter email OU telephone
old_login = '''    @app.post("/api/auth/login")
    def login(payload: LoginRequest, response: Response, request: Request):
        email = payload.email.strip().lower()
        conn = get_db()
        try:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if row is None or not verify_password(payload.password, row["password_hash"]):
                raise HTTPException(401, "Email ou mot de passe incorrect")'''
new_login = '''    @app.post("/api/auth/login")
    def login(payload: LoginRequest, response: Response, request: Request):
        ident = payload.email.strip()
        conn = get_db()
        try:
            # Chercher par email OU telephone
            row = None
            if "@" in ident:
                row = conn.execute(
                    "SELECT * FROM users WHERE email = ?", (ident.lower(),)
                ).fetchone()
            else:
                # Normaliser le telephone (retirer espaces, tirets, +)
                phone_clean = "".join(c for c in ident if c.isdigit())
                if phone_clean:
                    # Essayer plusieurs formats
                    row = conn.execute(
                        "SELECT * FROM users WHERE phone = ? OR phone = ? OR phone = ?",
                        (ident, phone_clean, "+" + phone_clean)
                    ).fetchone()
            if row is None or not verify_password(payload.password, row["password_hash"]):
                raise HTTPException(401, "Identifiants incorrects")'''
if old_login in src:
    src = src.replace(old_login, new_login, 1)
    print("[OK] auth.py -> login accepte email ou telephone")

# 2.3 Modifier register pour creer professional_profile si PRO
old_register_body = '''            cur = conn.execute(
                "INSERT INTO users (email, phone, password_hash, full_name,"
                " role, is_active, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)",
                (email, payload.phone.strip(), pwd_hash,
                 payload.full_name.strip(), payload.role, now),
            )
            user_id = cur.lastrowid
            token = _create_session(conn, user_id)
            conn.commit()
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()'''
new_register_body = '''            cur = conn.execute(
                "INSERT INTO users (email, phone, password_hash, full_name,"
                " role, is_active, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)",
                (email, payload.phone.strip(), pwd_hash,
                 payload.full_name.strip(), payload.role, now),
            )
            user_id = cur.lastrowid

            # Si professionnel : creer le profil etablissement
            if payload.role == "PROFESSIONNEL":
                type_map = {
                    "CLINIQUE": "CLINIQUE",
                    "PHARMACIE": "AUTRE",
                    "CABINET_MEDICAL": "CABINET_MEDICAL",
                    "LABORATOIRE": "LABORATOIRE",
                    "AUTRE": "AUTRE",
                    "HOPITAL": "HOPITAL",
                    "CENTRE_SANTE": "CENTRE_SANTE",
                }
                stype = type_map.get(
                    (payload.establishment_type or "").upper(),
                    "AUTRE"
                )
                sname = (payload.establishment_name or "").strip() or payload.full_name.strip()
                sresp = (payload.establishment_responsible or "").strip() or payload.full_name.strip()
                scity = (payload.establishment_city or "").strip()
                conn.execute(
                    "INSERT INTO professional_profiles"
                    " (user_id, structure_name, structure_type, manager_name,"
                    "  phone, email, address, status, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, 'APPROVED', ?)",
                    (user_id, sname, stype, sresp,
                     payload.phone.strip(), email, scity, now),
                )

            token = _create_session(conn, user_id)
            conn.commit()
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()'''
if old_register_body in src:
    src = src.replace(old_register_body, new_register_body, 1)
    print("[OK] auth.py -> register cree le profil etablissement")

# 2.4 Ajouter forgot / reset AVANT les endpoints d'info
new_endpoints = '''
    # ---- Mot de passe oublie ----

    @app.post("/api/auth/forgot-password")
    def forgot_password(payload: ForgotRequest):
        ident = payload.identifier.strip()
        if not ident:
            raise HTTPException(400, "Email ou telephone requis")

        conn = get_db()
        try:
            # Chercher par email ou telephone
            row = None
            if "@" in ident:
                row = conn.execute(
                    "SELECT id, email FROM users WHERE email = ?",
                    (ident.lower(),)
                ).fetchone()
            else:
                phone_clean = "".join(c for c in ident if c.isdigit())
                if phone_clean:
                    row = conn.execute(
                        "SELECT id, email FROM users WHERE phone = ? OR phone = ? OR phone = ?",
                        (ident, phone_clean, "+" + phone_clean)
                    ).fetchone()

            # Pour eviter l'enumeration : toujours repondre 200
            if row is None:
                return {"ok": True, "message": "Si un compte existe, un lien vous sera envoye."}

            token = secrets.token_urlsafe(32)
            now = datetime.now()
            expires = (now + timedelta(hours=2)).isoformat(timespec="seconds")
            conn.execute(
                "INSERT INTO password_resets (token, user_id, created_at, expires_at, used)"
                " VALUES (?, ?, ?, ?, 0)",
                (token, row["id"], now.isoformat(timespec="seconds"), expires)
            )
            conn.commit()
        finally:
            conn.close()

        # En dev : on retourne le lien direct (normalement envoye par email/SMS)
        reset_url = "/static/reset.html?token=" + token
        return {
            "ok": True,
            "message": "Un lien de reinitialisation a ete genere.",
            "reset_url": reset_url,
            "email": row["email"],
        }

    @app.post("/api/auth/reset-password")
    def reset_password(payload: ResetRequest):
        token = payload.token.strip()
        pwd = payload.new_password
        if not token or len(pwd) < 6:
            raise HTTPException(400, "Mot de passe trop court (6 caracteres minimum)")

        conn = get_db()
        try:
            row = conn.execute(
                "SELECT * FROM password_resets WHERE token = ? AND used = 0",
                (token,)
            ).fetchone()
            if row is None:
                raise HTTPException(400, "Lien invalide ou deja utilise")
            try:
                exp = datetime.fromisoformat(row["expires_at"])
                if datetime.now() > exp:
                    raise HTTPException(400, "Lien expire")
            except ValueError:
                pass

            try:
                pwd_hash = hash_password(pwd)
            except ValueError as e:
                raise HTTPException(400, str(e))

            conn.execute(
                "UPDATE users SET password_hash=?, updated_at=? WHERE id=?",
                (pwd_hash, datetime.now().isoformat(timespec="seconds"), row["user_id"])
            )
            conn.execute(
                "UPDATE password_resets SET used=1 WHERE id=?",
                (row["id"],)
            )
            # Invalider toutes les sessions de cet utilisateur
            conn.execute("DELETE FROM sessions WHERE user_id=?", (row["user_id"],))
            conn.commit()
        finally:
            conn.close()

        return {"ok": True, "message": "Mot de passe reinitialise. Vous pouvez vous connecter."}

'''
anchor = "    @app.get(\"/api/auth/roles\")"
if anchor in src and "/forgot-password" not in src:
    src = src.replace(anchor, new_endpoints + anchor, 1)
    print("[OK] auth.py -> routes forgot/reset ajoutees")

AUTH.write_text(src, encoding="utf-8")

# ============================================================
# 3. Page Login premium
# ============================================================
LOGIN_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Connexion - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
:root{
  --blue:#174A7E;--blue-dark:#0F3457;--blue-soft:#E8F0F8;
  --ink:#0F172A;--muted:#64748B;--line:#E2E8F0;--bg:#F5F8FC;
  --danger:#B23C3C;--ok:#0A7A5A;
}
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  font-family:-apple-system,"Segoe UI",system-ui,sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.5;font-size:15px;
  min-height:100vh;display:flex;align-items:center;justify-content:center;
  padding:20px;-webkit-font-smoothing:antialiased;
}
.card{
  width:100%;max-width:420px;background:#fff;
  border-radius:20px;padding:34px 28px;
  box-shadow:0 12px 40px rgba(15,23,42,.08);
}
.brand{
  display:flex;align-items:center;gap:12px;margin-bottom:26px;
}
.brand-logo{
  width:46px;height:46px;border-radius:12px;
  background:linear-gradient(135deg,#174A7E,#2A6BA8);color:#fff;
  display:flex;align-items:center;justify-content:center;
  font-size:24px;font-weight:800;
}
.brand-name{font-size:17px;font-weight:800;line-height:1.1}
.brand-tag{
  font-size:10.5px;color:var(--muted);
  text-transform:uppercase;letter-spacing:.1em;
  margin-top:2px;
}
h1{font-size:22px;font-weight:800;letter-spacing:-.02em;margin:0 0 6px}
.sub{font-size:13.5px;color:var(--muted);margin:0 0 22px;line-height:1.5}
.msg{
  padding:11px 14px;border-radius:11px;font-size:13px;
  margin-bottom:16px;background:#FDE8E8;color:var(--danger);
  border:1px solid #F6D2D2;
}
.msg.ok{background:#E6F7F1;color:var(--ok);border-color:#C7E9DC}
.msg.hidden{display:none}
.field{display:flex;flex-direction:column;gap:6px;margin-bottom:14px;position:relative}
.field label{font-size:12.5px;font-weight:700;color:var(--ink)}
.field input{
  padding:13px 42px 13px 14px;border:1.5px solid var(--line);
  border-radius:11px;font-family:inherit;font-size:15px;
  outline:none;background:#fff;color:var(--ink);width:100%;
  transition:.15s;
}
.field input:focus{border-color:var(--blue);box-shadow:0 0 0 3px var(--blue-soft)}
.field .toggle-eye{
  position:absolute;right:6px;top:50%;transform:translateY(-50%);
  width:36px;height:36px;border:0;background:transparent;
  cursor:pointer;color:var(--muted);font-size:16px;
  display:flex;align-items:center;justify-content:center;border-radius:8px;
}
.field .toggle-eye:hover{background:var(--bg);color:var(--blue)}
.row-between{
  display:flex;align-items:center;justify-content:space-between;
  gap:12px;margin:4px 0 18px;flex-wrap:wrap;
}
.check{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--ink);cursor:pointer}
.check input{accent-color:var(--blue);width:16px;height:16px}
.link{font-size:13px;color:var(--blue);font-weight:700;text-decoration:none}
.link:hover{color:var(--blue-dark);text-decoration:underline}
.btn{
  width:100%;padding:15px;border:0;border-radius:12px;
  background:var(--blue);color:#fff;font-weight:800;font-size:15px;
  cursor:pointer;transition:.15s;
}
.btn:hover:not(:disabled){background:var(--blue-dark);transform:translateY(-1px)}
.btn:disabled{background:#C7D5E3;cursor:not-allowed}
.alt{
  text-align:center;font-size:13.5px;color:var(--muted);
  margin-top:22px;padding-top:20px;border-top:1px solid var(--line);
}
.alt a{color:var(--blue);font-weight:800;text-decoration:none}
.alt a:hover{text-decoration:underline}
.foot{
  text-align:center;font-size:11.5px;color:var(--muted);
  margin-top:16px;line-height:1.5;
}
</style>
</head>
<body>
<form class="card" id="login-form" autocomplete="on">
  <div class="brand">
    <div class="brand-logo">+</div>
    <div>
      <div class="brand-name">Elokinab Health</div>
      <div class="brand-tag">Healthcare Procurement</div>
    </div>
  </div>

  <h1>Bon retour parmi nous.</h1>
  <p class="sub">Connectez-vous a votre espace professionnel.</p>

  <div id="msg" class="msg hidden"></div>

  <div class="field">
    <label for="email">Adresse e-mail ou telephone</label>
    <input type="text" id="email" name="email" required autocomplete="username"
           placeholder="vous@clinique.tg ou 90 00 00 00">
  </div>

  <div class="field">
    <label for="password">Mot de passe</label>
    <input type="password" id="password" name="password" required autocomplete="current-password">
    <button type="button" class="toggle-eye" id="toggle-eye" aria-label="Afficher le mot de passe">&#128065;</button>
  </div>

  <div class="row-between">
    <label class="check">
      <input type="checkbox" id="remember" checked>
      Rester connecte
    </label>
    <a class="link" href="/static/forgot.html">Mot de passe oublie ?</a>
  </div>

  <button class="btn" id="btn" type="submit">Se connecter</button>

  <div class="alt">
    Pas encore de compte ? <a href="/inscription">Creer un compte professionnel</a>
  </div>

  <div class="foot">
    Votre espace professionnel, protege et confidentiel.
  </div>
</form>

<script src="/static/safe_locale.js"></script>
<script src="/static/login.js"></script>
</body>
</html>
'''
(STATIC / "login.html").write_text(LOGIN_HTML, encoding="utf-8")
print("[OK] login.html reecrit")

LOGIN_JS = '''/* Login Elokinab Health */
(function () {
  var $ = function (id) { return document.getElementById(id); };
  function showMsg(t, ok) {
    var m = $("msg"); m.textContent = t;
    m.className = "msg" + (ok ? " ok" : "");
  }
  function hideMsg() { $("msg").className = "msg hidden"; }

  document.addEventListener("DOMContentLoaded", function () {
    // Toggle mot de passe
    var eye = $("toggle-eye");
    var pwd = $("password");
    if (eye && pwd) {
      eye.addEventListener("click", function () {
        if (pwd.type === "password") {
          pwd.type = "text";
          eye.innerHTML = "&#128584;";
          eye.setAttribute("aria-label", "Masquer le mot de passe");
        } else {
          pwd.type = "password";
          eye.innerHTML = "&#128065;";
          eye.setAttribute("aria-label", "Afficher le mot de passe");
        }
      });
    }

    // Submit
    $("login-form").addEventListener("submit", function (ev) {
      ev.preventDefault();
      hideMsg();
      var btn = $("btn");
      btn.disabled = true; btn.textContent = "Connexion...";

      fetch("/api/auth/login", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: $("email").value.trim(),
          password: $("password").value
        })
      })
      .then(function (r) {
        return r.json().then(function (d) {
          if (!r.ok) throw new Error(d.detail || "Identifiants incorrects");
          return d;
        });
      })
      .then(function (d) {
        try { localStorage.setItem("eh_user_cache",
          JSON.stringify({ user: d.user, _at: Date.now() })); } catch (e) {}
        showMsg("Connexion reussie. Redirection...", true);
        var role = d.user && d.user.role;
        var target = "/";
        if (role === "PROFESSIONNEL") target = "/professionnel";
        else if (role === "PHARMACIEN" || role === "ADMIN") target = "/pharmacien";
        setTimeout(function () { window.location.href = target; }, 500);
      })
      .catch(function (e) {
        showMsg(e.message || "Erreur de connexion");
        btn.disabled = false; btn.textContent = "Se connecter";
      });
    });
  });
})();
'''
(STATIC / "login.js").write_text(LOGIN_JS, encoding="utf-8")
print("[OK] login.js cree")

# ============================================================
# 4. Page Inscription 3 etapes
# ============================================================
REGISTER_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Inscription - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
:root{
  --blue:#174A7E;--blue-dark:#0F3457;--blue-soft:#E8F0F8;
  --ink:#0F172A;--muted:#64748B;--line:#E2E8F0;--bg:#F5F8FC;
  --danger:#B23C3C;--ok:#0A7A5A;
}
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  font-family:-apple-system,"Segoe UI",system-ui,sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.5;font-size:15px;
  min-height:100vh;padding:20px;-webkit-font-smoothing:antialiased;
}
.card{
  width:100%;max-width:480px;margin:20px auto;background:#fff;
  border-radius:20px;padding:30px 26px;
  box-shadow:0 12px 40px rgba(15,23,42,.08);
}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:22px}
.brand-logo{
  width:42px;height:42px;border-radius:11px;
  background:linear-gradient(135deg,#174A7E,#2A6BA8);color:#fff;
  display:flex;align-items:center;justify-content:center;
  font-size:22px;font-weight:800;
}
.brand-name{font-size:16px;font-weight:800;line-height:1.1}
.brand-tag{font-size:10px;color:var(--muted);text-transform:uppercase;
  letter-spacing:.1em;margin-top:2px}
h1{font-size:21px;font-weight:800;letter-spacing:-.02em;margin:0 0 4px}
.sub{font-size:13px;color:var(--muted);margin:0 0 18px;line-height:1.5}

/* Progress bar */
.progress{margin:0 0 22px}
.progress-text{
  display:flex;justify-content:space-between;
  font-size:11px;font-weight:800;
  text-transform:uppercase;letter-spacing:.08em;
  color:var(--muted);margin-bottom:8px;
}
.progress-track{
  height:6px;background:#EEF2F7;border-radius:999px;overflow:hidden;
}
.progress-fill{
  height:100%;background:linear-gradient(90deg,#174A7E,#2A6BA8);
  border-radius:999px;transition:width .3s cubic-bezier(.4,0,.2,1);
}

.step{display:none}
.step.active{display:block}

.field{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.field label{font-size:12.5px;font-weight:700;color:var(--ink)}
.field input, .field select{
  padding:13px 14px;border:1.5px solid var(--line);border-radius:11px;
  font-family:inherit;font-size:15px;outline:none;background:#fff;color:var(--ink);
  width:100%;transition:.15s;
}
.field input:focus, .field select:focus{
  border-color:var(--blue);box-shadow:0 0 0 3px var(--blue-soft);
}

.types{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:14px}
.type-btn{
  padding:14px 12px;border:1.5px solid var(--line);border-radius:11px;
  background:#fff;cursor:pointer;font-family:inherit;
  display:flex;flex-direction:column;align-items:center;gap:6px;
  font-size:12.5px;font-weight:700;color:var(--ink);
  transition:.15s;
}
.type-btn:hover{border-color:var(--blue)}
.type-btn.active{
  border-color:var(--blue);background:var(--blue-soft);color:var(--blue-dark);
}
.type-btn .ico{font-size:20px}

.row-2{display:grid;grid-template-columns:1fr 1fr;gap:12px}

.msg{
  padding:11px 14px;border-radius:11px;font-size:13px;
  margin-bottom:14px;background:#FDE8E8;color:var(--danger);
  border:1px solid #F6D2D2;
}
.msg.ok{background:#E6F7F1;color:var(--ok);border-color:#C7E9DC}
.msg.hidden{display:none}

.actions{
  display:flex;gap:10px;margin-top:20px;padding-top:18px;
  border-top:1px solid var(--line);
}
.btn{
  flex:1;padding:15px;border:0;border-radius:12px;
  font-weight:800;font-size:14.5px;
  cursor:pointer;transition:.15s;
}
.btn-primary{background:var(--blue);color:#fff}
.btn-primary:hover:not(:disabled){background:var(--blue-dark)}
.btn-primary:disabled{background:#C7D5E3;cursor:not-allowed}
.btn-ghost{
  background:#fff;border:1.5px solid var(--line);
  color:var(--ink);
}
.btn-ghost:hover{border-color:var(--blue);color:var(--blue)}

.checks{display:flex;flex-direction:column;gap:10px;margin-top:12px}
.check{display:flex;align-items:flex-start;gap:10px;font-size:12.5px;color:var(--ink);cursor:pointer;line-height:1.5}
.check input{accent-color:var(--blue);width:16px;height:16px;margin-top:2px;flex-shrink:0}
.check a{color:var(--blue);font-weight:700;text-decoration:none}

.alt{
  text-align:center;font-size:13px;color:var(--muted);
  margin-top:18px;padding-top:16px;border-top:1px solid var(--line);
}
.alt a{color:var(--blue);font-weight:800;text-decoration:none}

.strength{
  height:4px;background:#EEF2F7;border-radius:999px;overflow:hidden;margin-top:6px;
}
.strength-fill{height:100%;width:0%;transition:.3s;background:#DC2626}
.strength-fill.weak{background:#DC2626;width:33%}
.strength-fill.medium{background:#F59E0B;width:66%}
.strength-fill.strong{background:#0A7A5A;width:100%}

@media (max-width:400px){
  .card{padding:22px 18px}
  .row-2{grid-template-columns:1fr}
  .types{grid-template-columns:1fr}
}
</style>
</head>
<body>

<form class="card" id="register-form" autocomplete="on">
  <div class="brand">
    <div class="brand-logo">+</div>
    <div>
      <div class="brand-name">Elokinab Health</div>
      <div class="brand-tag">Healthcare Procurement</div>
    </div>
  </div>

  <h1>Creer mon compte</h1>
  <p class="sub">Quelques informations pour rejoindre Elokinab Health.</p>

  <div class="progress">
    <div class="progress-text">
      <span id="progress-label">Etape 1/3</span>
      <span id="progress-title">Etablissement</span>
    </div>
    <div class="progress-track"><div class="progress-fill" id="progress-fill" style="width:33%"></div></div>
  </div>

  <div id="msg" class="msg hidden"></div>

  <!-- ETAPE 1 : ETABLISSEMENT -->
  <div class="step active" data-step="1">
    <div class="field">
      <label>Type d'etablissement *</label>
      <div class="types" id="types">
        <button type="button" class="type-btn" data-value="CLINIQUE">
          <span class="ico">&#127973;</span>Clinique
        </button>
        <button type="button" class="type-btn" data-value="PHARMACIE">
          <span class="ico">&#128138;</span>Pharmacie
        </button>
        <button type="button" class="type-btn" data-value="CABINET_MEDICAL">
          <span class="ico">&#129658;</span>Cabinet medical
        </button>
        <button type="button" class="type-btn" data-value="LABORATOIRE">
          <span class="ico">&#128300;</span>Laboratoire
        </button>
        <button type="button" class="type-btn" data-value="HOPITAL" style="grid-column:1/-1">
          <span class="ico">&#127974;</span>Hopital / Centre de sante
        </button>
        <button type="button" class="type-btn" data-value="AUTRE" style="grid-column:1/-1">
          <span class="ico">&#10133;</span>Autre structure
        </button>
      </div>
      <input type="hidden" id="establishment_type" value="">
    </div>

    <div class="field">
      <label for="establishment_name">Nom de l'etablissement *</label>
      <input type="text" id="establishment_name" required placeholder="Ex : Clinique Les Merveilles">
    </div>

    <div class="field">
      <label for="establishment_city">Ville *</label>
      <input type="text" id="establishment_city" required placeholder="Ex : Lome">
    </div>
  </div>

  <!-- ETAPE 2 : RESPONSABLE -->
  <div class="step" data-step="2">
    <div class="field">
      <label for="full_name">Nom du responsable *</label>
      <input type="text" id="full_name" required placeholder="Ex : Dr Adjalo Georges">
    </div>

    <div class="field">
      <label for="phone">Telephone *</label>
      <input type="tel" id="phone" required placeholder="Ex : 90 00 00 00" autocomplete="tel">
    </div>

    <div class="field">
      <label for="email">E-mail *</label>
      <input type="email" id="email" required placeholder="vous@clinique.tg" autocomplete="email">
    </div>
  </div>

  <!-- ETAPE 3 : SECURITE -->
  <div class="step" data-step="3">
    <div class="field">
      <label for="password">Mot de passe * (6 caracteres minimum)</label>
      <input type="password" id="password" required minlength="6" autocomplete="new-password">
      <div class="strength"><div class="strength-fill" id="strength-fill"></div></div>
    </div>

    <div class="checks">
      <label class="check">
        <input type="checkbox" id="terms" required>
        <span>J'accepte les <a href="#" onclick="return false">conditions d'utilisation</a> et la <a href="#" onclick="return false">politique de confidentialite</a>.</span>
      </label>
      <label class="check">
        <input type="checkbox" id="accurate" required>
        <span>Je certifie que les informations fournies sont exactes.</span>
      </label>
    </div>
  </div>

  <!-- ACTIONS -->
  <div class="actions">
    <button type="button" class="btn btn-ghost hidden" id="btn-prev">Retour</button>
    <button type="button" class="btn btn-primary" id="btn-next">Continuer</button>
    <button type="submit" class="btn btn-primary hidden" id="btn-submit">Creer mon compte</button>
  </div>

  <div class="alt">
    Deja un compte ? <a href="/connexion">Se connecter</a>
  </div>
</form>

<script src="/static/safe_locale.js"></script>
<script src="/static/register.js"></script>
</body>
</html>
'''
(STATIC / "register.html").write_text(REGISTER_HTML, encoding="utf-8")
print("[OK] register.html reecrit")

REGISTER_JS = '''/* Register Elokinab Health - 3 etapes */
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var currentStep = 1;

  function showMsg(t, ok) {
    var m = $("msg");
    m.textContent = t;
    m.className = "msg" + (ok ? " ok" : "");
    m.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  function hideMsg() { $("msg").className = "msg hidden"; }

  function setStep(n) {
    currentStep = n;
    // Afficher uniquement l'etape n
    var steps = document.querySelectorAll(".step");
    Array.prototype.forEach.call(steps, function (s) {
      s.classList.toggle("active", parseInt(s.getAttribute("data-step"), 10) === n);
    });

    // Progress bar
    var labels = { 1: "Etablissement", 2: "Responsable", 3: "Securite" };
    $("progress-label").textContent = "Etape " + n + "/3";
    $("progress-title").textContent = labels[n] || "";
    $("progress-fill").style.width = Math.round((n / 3) * 100) + "%";

    // Boutons
    $("btn-prev").classList.toggle("hidden", n === 1);
    $("btn-next").classList.toggle("hidden", n === 3);
    $("btn-submit").classList.toggle("hidden", n !== 3);
  }

  function validateStep(n) {
    hideMsg();
    if (n === 1) {
      if (!$("establishment_type").value) {
        showMsg("Selectionnez le type d'etablissement."); return false;
      }
      if (!$("establishment_name").value.trim()) {
        showMsg("Le nom de l'etablissement est obligatoire."); return false;
      }
      if (!$("establishment_city").value.trim()) {
        showMsg("La ville est obligatoire."); return false;
      }
    }
    if (n === 2) {
      if (!$("full_name").value.trim()) {
        showMsg("Le nom du responsable est obligatoire."); return false;
      }
      if (!$("phone").value.trim()) {
        showMsg("Le telephone est obligatoire."); return false;
      }
      var email = $("email").value.trim();
      if (!email || email.indexOf("@") === -1) {
        showMsg("E-mail invalide."); return false;
      }
    }
    if (n === 3) {
      var pwd = $("password").value;
      if (!pwd || pwd.length < 6) {
        showMsg("Mot de passe trop court (6 caracteres minimum)."); return false;
      }
      if (!$("terms").checked) {
        showMsg("Vous devez accepter les conditions d'utilisation."); return false;
      }
      if (!$("accurate").checked) {
        showMsg("Vous devez certifier l'exactitude des informations."); return false;
      }
    }
    return true;
  }

  function setupTypes() {
    var box = $("types");
    if (!box) return;
    Array.prototype.forEach.call(box.querySelectorAll(".type-btn"), function (b) {
      b.addEventListener("click", function () {
        Array.prototype.forEach.call(box.querySelectorAll(".type-btn"), function (x) {
          x.classList.remove("active");
        });
        b.classList.add("active");
        $("establishment_type").value = b.getAttribute("data-value");
      });
    });
  }

  function setupStrength() {
    var pwd = $("password");
    var fill = $("strength-fill");
    if (!pwd || !fill) return;
    pwd.addEventListener("input", function () {
      var v = pwd.value || "";
      var score = 0;
      if (v.length >= 6) score++;
      if (v.length >= 10) score++;
      if (/[A-Z]/.test(v) && /[a-z]/.test(v)) score++;
      if (/[0-9]/.test(v)) score++;
      if (/[^A-Za-z0-9]/.test(v)) score++;
      fill.className = "strength-fill";
      if (v.length === 0) { fill.style.width = "0%"; return; }
      if (score <= 2) fill.classList.add("weak");
      else if (score <= 3) fill.classList.add("medium");
      else fill.classList.add("strong");
    });
  }

  function submit() {
    if (!validateStep(3)) return;
    var btn = $("btn-submit");
    btn.disabled = true;
    btn.textContent = "Creation...";

    var payload = {
      email: $("email").value.trim(),
      phone: $("phone").value.trim(),
      password: $("password").value,
      full_name: $("full_name").value.trim(),
      role: "PROFESSIONNEL",
      establishment_type: $("establishment_type").value,
      establishment_name: $("establishment_name").value.trim(),
      establishment_city: $("establishment_city").value.trim(),
      establishment_responsible: $("full_name").value.trim()
    };

    fetch("/api/auth/register", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
    .then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur d'inscription");
        return d;
      });
    })
    .then(function (d) {
      try { localStorage.setItem("eh_user_cache",
        JSON.stringify({ user: d.user, _at: Date.now() })); } catch (e) {}
      showMsg("Compte cree. Redirection...", true);
      setTimeout(function () { window.location.href = "/professionnel"; }, 600);
    })
    .catch(function (e) {
      showMsg(e.message);
      btn.disabled = false;
      btn.textContent = "Creer mon compte";
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupTypes();
    setupStrength();

    $("btn-next").addEventListener("click", function () {
      if (validateStep(currentStep)) setStep(currentStep + 1);
    });
    $("btn-prev").addEventListener("click", function () {
      hideMsg();
      setStep(currentStep - 1);
    });
    $("register-form").addEventListener("submit", function (ev) {
      ev.preventDefault();
      submit();
    });

    setStep(1);
  });
})();
'''
(STATIC / "register.js").write_text(REGISTER_JS, encoding="utf-8")
print("[OK] register.js cree")

# ============================================================
# 5. Page Mot de passe oublie
# ============================================================
FORGOT_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Mot de passe oublie - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
:root{--blue:#174A7E;--blue-dark:#0F3457;--blue-soft:#E8F0F8;
  --ink:#0F172A;--muted:#64748B;--line:#E2E8F0;--bg:#F5F8FC;
  --danger:#B23C3C;--ok:#0A7A5A}
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;padding:0}
body{font-family:-apple-system,"Segoe UI",system-ui,sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.5;font-size:15px;
  min-height:100vh;display:flex;align-items:center;justify-content:center;
  padding:20px}
.card{width:100%;max-width:420px;background:#fff;
  border-radius:20px;padding:32px 26px;
  box-shadow:0 12px 40px rgba(15,23,42,.08)}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:24px}
.brand-logo{width:44px;height:44px;border-radius:12px;
  background:linear-gradient(135deg,#174A7E,#2A6BA8);color:#fff;
  display:flex;align-items:center;justify-content:center;
  font-size:22px;font-weight:800}
.brand-name{font-size:16px;font-weight:800;line-height:1.1}
.brand-tag{font-size:10px;color:var(--muted);text-transform:uppercase;
  letter-spacing:.1em;margin-top:2px}
h1{font-size:20px;font-weight:800;margin:0 0 6px}
.sub{font-size:13px;color:var(--muted);margin:0 0 20px;line-height:1.5}
.field{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.field label{font-size:12.5px;font-weight:700}
.field input{padding:13px 14px;border:1.5px solid var(--line);
  border-radius:11px;font-family:inherit;font-size:15px;outline:none;
  width:100%;transition:.15s}
.field input:focus{border-color:var(--blue);box-shadow:0 0 0 3px var(--blue-soft)}
.btn{width:100%;padding:15px;border:0;border-radius:12px;
  background:var(--blue);color:#fff;font-weight:800;font-size:15px;
  cursor:pointer;transition:.15s}
.btn:hover:not(:disabled){background:var(--blue-dark)}
.btn:disabled{background:#C7D5E3;cursor:not-allowed}
.msg{padding:11px 14px;border-radius:11px;font-size:13px;
  margin-bottom:14px;background:#FDE8E8;color:var(--danger);
  border:1px solid #F6D2D2}
.msg.ok{background:#E6F7F1;color:var(--ok);border-color:#C7E9DC}
.msg.hidden{display:none}
.link{display:block;text-align:center;margin-top:16px;
  font-size:13px;color:var(--blue);font-weight:700;text-decoration:none}
.link:hover{text-decoration:underline}
.reset-link{display:block;margin-top:12px;padding:12px;
  background:var(--blue-soft);color:var(--blue-dark);
  border-radius:11px;font-weight:700;text-decoration:none;
  text-align:center;font-size:13px;word-break:break-all}
</style>
</head>
<body>
<form class="card" id="forgot-form">
  <div class="brand">
    <div class="brand-logo">+</div>
    <div>
      <div class="brand-name">Elokinab Health</div>
      <div class="brand-tag">Healthcare Procurement</div>
    </div>
  </div>

  <h1>Mot de passe oublie</h1>
  <p class="sub">Entrez votre e-mail ou telephone. Un lien de reinitialisation sera cree.</p>

  <div id="msg" class="msg hidden"></div>

  <div class="field">
    <label for="identifier">E-mail ou telephone</label>
    <input type="text" id="identifier" required placeholder="vous@clinique.tg ou 90 00 00 00">
  </div>

  <button class="btn" type="submit" id="btn">Envoyer</button>

  <a class="link" href="/connexion">Retour a la connexion</a>
</form>

<script src="/static/safe_locale.js"></script>
<script>
(function () {
  var $ = function (id) { return document.getElementById(id); };
  function showMsg(t, ok) {
    var m = $("msg"); m.textContent = t;
    m.className = "msg" + (ok ? " ok" : "");
  }
  $("forgot-form").addEventListener("submit", function (ev) {
    ev.preventDefault();
    $("msg").className = "msg hidden";
    var btn = $("btn");
    btn.disabled = true; btn.textContent = "Envoi...";
    fetch("/api/auth/forgot-password", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier: $("identifier").value.trim() })
    })
    .then(function (r) { return r.json().then(function (d) {
      if (!r.ok) throw new Error(d.detail || "Erreur");
      return d;
    }); })
    .then(function (d) {
      showMsg(d.message || "Lien envoye.", true);
      if (d.reset_url) {
        var a = document.createElement("a");
        a.className = "reset-link";
        a.href = d.reset_url;
        a.textContent = "Ouvrir le lien de reinitialisation";
        $("msg").parentNode.insertBefore(a, $("btn"));
      }
      btn.disabled = false; btn.textContent = "Envoyer";
    })
    .catch(function (e) {
      showMsg(e.message);
      btn.disabled = false; btn.textContent = "Envoyer";
    });
  });
})();
</script>
</body>
</html>
'''
(STATIC / "forgot.html").write_text(FORGOT_HTML, encoding="utf-8")
print("[OK] forgot.html")

# ============================================================
# 6. Page Reset password
# ============================================================
RESET_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Reinitialiser - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
:root{--blue:#174A7E;--blue-dark:#0F3457;--blue-soft:#E8F0F8;
  --ink:#0F172A;--muted:#64748B;--line:#E2E8F0;--bg:#F5F8FC;
  --danger:#B23C3C;--ok:#0A7A5A}
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;padding:0}
body{font-family:-apple-system,"Segoe UI",system-ui,sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.5;font-size:15px;
  min-height:100vh;display:flex;align-items:center;justify-content:center;
  padding:20px}
.card{width:100%;max-width:420px;background:#fff;
  border-radius:20px;padding:32px 26px;
  box-shadow:0 12px 40px rgba(15,23,42,.08)}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:24px}
.brand-logo{width:44px;height:44px;border-radius:12px;
  background:linear-gradient(135deg,#174A7E,#2A6BA8);color:#fff;
  display:flex;align-items:center;justify-content:center;
  font-size:22px;font-weight:800}
.brand-name{font-size:16px;font-weight:800;line-height:1.1}
.brand-tag{font-size:10px;color:var(--muted);text-transform:uppercase;
  letter-spacing:.1em;margin-top:2px}
h1{font-size:20px;font-weight:800;margin:0 0 6px}
.sub{font-size:13px;color:var(--muted);margin:0 0 20px;line-height:1.5}
.field{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.field label{font-size:12.5px;font-weight:700}
.field input{padding:13px 14px;border:1.5px solid var(--line);
  border-radius:11px;font-family:inherit;font-size:15px;outline:none;
  width:100%;transition:.15s}
.field input:focus{border-color:var(--blue);box-shadow:0 0 0 3px var(--blue-soft)}
.btn{width:100%;padding:15px;border:0;border-radius:12px;
  background:var(--blue);color:#fff;font-weight:800;font-size:15px;
  cursor:pointer;transition:.15s}
.btn:hover:not(:disabled){background:var(--blue-dark)}
.btn:disabled{background:#C7D5E3;cursor:not-allowed}
.msg{padding:11px 14px;border-radius:11px;font-size:13px;
  margin-bottom:14px;background:#FDE8E8;color:var(--danger);
  border:1px solid #F6D2D2}
.msg.ok{background:#E6F7F1;color:var(--ok);border-color:#C7E9DC}
.msg.hidden{display:none}
.link{display:block;text-align:center;margin-top:16px;
  font-size:13px;color:var(--blue);font-weight:700;text-decoration:none}
</style>
</head>
<body>
<form class="card" id="reset-form">
  <div class="brand">
    <div class="brand-logo">+</div>
    <div>
      <div class="brand-name">Elokinab Health</div>
      <div class="brand-tag">Healthcare Procurement</div>
    </div>
  </div>

  <h1>Nouveau mot de passe</h1>
  <p class="sub">Choisissez un nouveau mot de passe securise.</p>

  <div id="msg" class="msg hidden"></div>

  <div class="field">
    <label for="new_password">Nouveau mot de passe (6 caracteres minimum)</label>
    <input type="password" id="new_password" required minlength="6">
  </div>

  <button class="btn" type="submit" id="btn">Reinitialiser</button>

  <a class="link" href="/connexion">Retour a la connexion</a>
</form>

<script src="/static/safe_locale.js"></script>
<script>
(function () {
  var $ = function (id) { return document.getElementById(id); };
  function showMsg(t, ok) {
    var m = $("msg"); m.textContent = t;
    m.className = "msg" + (ok ? " ok" : "");
  }

  var params = new URLSearchParams(window.location.search);
  var token = params.get("token") || "";

  if (!token) {
    showMsg("Lien invalide. Demandez un nouveau lien.");
  }

  $("reset-form").addEventListener("submit", function (ev) {
    ev.preventDefault();
    if (!token) return;
    $("msg").className = "msg hidden";
    var btn = $("btn");
    btn.disabled = true; btn.textContent = "Traitement...";
    fetch("/api/auth/reset-password", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: token, new_password: $("new_password").value })
    })
    .then(function (r) { return r.json().then(function (d) {
      if (!r.ok) throw new Error(d.detail || "Erreur");
      return d;
    }); })
    .then(function (d) {
      showMsg(d.message || "Mot de passe reinitialise.", true);
      setTimeout(function () { window.location.href = "/connexion"; }, 1500);
    })
    .catch(function (e) {
      showMsg(e.message);
      btn.disabled = false; btn.textContent = "Reinitialiser";
    });
  });
})();
</script>
</body>
</html>
'''
(STATIC / "reset.html").write_text(RESET_HTML, encoding="utf-8")
print("[OK] reset.html")

print()
print("=" * 60)
print("AUTH PREMIUM LIVRE")
print("=" * 60)
print()
print("Backend :")
print("  - Table password_resets")
print("  - POST /api/auth/forgot-password")
print("  - POST /api/auth/reset-password")
print("  - Login accepte email OU telephone")
print("  - Register cree le professional_profile si PRO")
print()
print("Frontend :")
print("  - login.html   (nouveau design + show/hide password)")
print("  - register.html (3 etapes + progress bar)")
print("  - login.js, register.js")
print("  - forgot.html, reset.html")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print()
print("Puis teste sur iPhone :")
print("  /connexion  (nouveau design)")
print("  /inscription (3 etapes)")
print("  /static/forgot.html")