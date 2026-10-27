"""
v3_install_phase3.py
Phase 3 : profils professionnels + validation admin.
Additif uniquement.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
MODULES = BASE / "v3_modules"
STATIC = BASE / "static"

# ============================================================
# 0. BACKUP
# ============================================================
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_v3_p3_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAIN, backup / "main.py")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. v3_modules/professionals.py
# ============================================================
PROS = '''"""Gestion des profils professionnels (Phase 3)."""
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel


VALID_STRUCTURE_TYPES = {
    "CLINIQUE", "HOPITAL", "CABINET_MEDICAL",
    "LABORATOIRE", "CENTRE_SANTE", "AUTRE",
}

VALID_STATUSES = {"PENDING", "APPROVED", "REJECTED", "SUSPENDED"}


class ProfessionalProfileCreate(BaseModel):
    structure_name: str
    structure_type: str
    manager_name: str
    phone: str
    email: str = ""
    address: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: str = ""


class ProfessionalReview(BaseModel):
    status: str
    rejection_reason: str = ""


def _row_to_dict(row):
    return {k: row[k] for k in row.keys()} if row else None


def install_professionals(app, get_db, require_role):
    """Enregistre les routes /api/professionals/*."""

    # ---- Cote professionnel ----

    @app.post("/api/professionals/profile")
    def create_or_update_profile(
        payload: ProfessionalProfileCreate,
        user=require_role("PROFESSIONNEL"),
    ):
        if payload.structure_type not in VALID_STRUCTURE_TYPES:
            raise HTTPException(400, "Type de structure invalide")
        if not payload.structure_name.strip() or not payload.manager_name.strip():
            raise HTTPException(400, "Nom de structure et responsable obligatoires")
        if not payload.phone.strip():
            raise HTTPException(400, "Telephone obligatoire")

        conn = get_db()
        try:
            existing = conn.execute(
                "SELECT id, status FROM professional_profiles WHERE user_id = ?",
                (user["id"],),
            ).fetchone()
            now = datetime.now().isoformat(timespec="seconds")

            if existing is None:
                cur = conn.execute(
                    "INSERT INTO professional_profiles"
                    " (user_id, structure_name, structure_type, manager_name,"
                    " phone, email, address, latitude, longitude, notes,"
                    " status, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)",
                    (user["id"], payload.structure_name.strip(),
                     payload.structure_type, payload.manager_name.strip(),
                     payload.phone.strip(), payload.email.strip(),
                     payload.address.strip(), payload.latitude,
                     payload.longitude, payload.notes.strip(), now),
                )
                pid = cur.lastrowid
            else:
                if existing["status"] == "APPROVED":
                    raise HTTPException(
                        400,
                        "Profil approuve : contactez la pharmacie pour modification",
                    )
                conn.execute(
                    "UPDATE professional_profiles SET"
                    " structure_name=?, structure_type=?, manager_name=?,"
                    " phone=?, email=?, address=?, latitude=?, longitude=?,"
                    " notes=?, status='PENDING', rejection_reason=''"
                    " WHERE user_id=?",
                    (payload.structure_name.strip(), payload.structure_type,
                     payload.manager_name.strip(), payload.phone.strip(),
                     payload.email.strip(), payload.address.strip(),
                     payload.latitude, payload.longitude,
                     payload.notes.strip(), user["id"]),
                )
                pid = existing["id"]
            conn.commit()
            row = conn.execute(
                "SELECT * FROM professional_profiles WHERE id = ?", (pid,)
            ).fetchone()
        finally:
            conn.close()
        return _row_to_dict(row)

    @app.get("/api/professionals/me")
    def get_my_profile(user=require_role("PROFESSIONNEL")):
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT * FROM professional_profiles WHERE user_id = ?",
                (user["id"],),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            raise HTTPException(404, "Profil non cree")
        return _row_to_dict(row)

    # ---- Cote pharmacien / admin ----

    @app.get("/api/professionals")
    def list_profiles(
        status: str = "",
        user=require_role("PHARMACIEN", "ADMIN"),
    ):
        conn = get_db()
        try:
            sql = ("SELECT p.*, u.email AS user_email, u.full_name AS user_name"
                   " FROM professional_profiles p"
                   " JOIN users u ON u.id = p.user_id")
            params = []
            if status.strip():
                sql += " WHERE p.status = ?"
                params.append(status.strip().upper())
            sql += " ORDER BY p.created_at DESC"
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
        return [_row_to_dict(r) for r in rows]

    @app.get("/api/professionals/{profile_id}")
    def get_profile(profile_id: int, user=require_role("PHARMACIEN", "ADMIN")):
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT p.*, u.email AS user_email, u.full_name AS user_name"
                " FROM professional_profiles p"
                " JOIN users u ON u.id = p.user_id WHERE p.id = ?",
                (profile_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            raise HTTPException(404, "Profil introuvable")
        return _row_to_dict(row)

    @app.patch("/api/professionals/{profile_id}/status")
    def review_profile(
        profile_id: int,
        payload: ProfessionalReview,
        user=require_role("PHARMACIEN", "ADMIN"),
    ):
        new_status = payload.status.strip().upper()
        if new_status not in {"APPROVED", "REJECTED", "SUSPENDED"}:
            raise HTTPException(400, "Statut invalide")
        if new_status == "REJECTED" and not payload.rejection_reason.strip():
            raise HTTPException(400, "Motif de refus obligatoire")

        conn = get_db()
        try:
            row = conn.execute(
                "SELECT id FROM professional_profiles WHERE id = ?",
                (profile_id,),
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Profil introuvable")
            conn.execute(
                "UPDATE professional_profiles SET status=?, rejection_reason=?,"
                " reviewed_at=?, reviewed_by=? WHERE id=?",
                (new_status, payload.rejection_reason.strip(),
                 datetime.now().isoformat(timespec="seconds"),
                 user["id"], profile_id),
            )
            conn.commit()
            updated = conn.execute(
                "SELECT * FROM professional_profiles WHERE id = ?",
                (profile_id,),
            ).fetchone()
        finally:
            conn.close()
        return _row_to_dict(updated)

    @app.get("/api/professionals/stats/summary")
    def stats(user=require_role("PHARMACIEN", "ADMIN")):
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS n FROM professional_profiles GROUP BY status"
            ).fetchall()
            counts = {r["status"]: r["n"] for r in rows}
        finally:
            conn.close()
        return {
            "pending": counts.get("PENDING", 0),
            "approved": counts.get("APPROVED", 0),
            "rejected": counts.get("REJECTED", 0),
            "suspended": counts.get("SUSPENDED", 0),
            "total": sum(counts.values()),
        }


'''
(MODULES / "professionals.py").write_text(PROS, encoding="utf-8")
print("[OK] v3_modules/professionals.py")

# ============================================================
# 2. Patch main.py
# ============================================================
src = MAIN.read_text(encoding="utf-8")

if "install_professionals" not in src:
    old_block = 'require_role = install_auth(app, get_db, row_to_dict)'
    new_block = (
        'require_role = install_auth(app, get_db, row_to_dict)\n'
        'from v3_modules.professionals import install_professionals\n'
        'install_professionals(app, get_db, require_role)'
    )
    if old_block in src:
        src = src.replace(old_block, new_block, 1)
        print("[OK] main.py -> install_professionals branche")
    else:
        print("[!] anchor install_auth introuvable")
    MAIN.write_text(src, encoding="utf-8")
else:
    print("[i] main.py deja patche Phase 3")

# ============================================================
# 3. FRONTEND - page profil professionnel
# ============================================================
PRO_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Profil professionnel - Elokinab Health</title>
<link rel="stylesheet" href="/static/auth.css">
<style>
  .auth-card{max-width:520px}
  textarea{width:100%;padding:12px 14px;border:1px solid #ddece6;border-radius:11px;font-family:inherit;font-size:14px;resize:vertical;outline:none}
  textarea:focus{border-color:#0f9d76}
  .status-pill{display:inline-block;font-size:11px;font-weight:800;padding:5px 10px;border-radius:999px;text-transform:uppercase;letter-spacing:.05em;margin-bottom:14px}
  .status-PENDING{background:#fff4e0;color:#b26b00}
  .status-APPROVED{background:#e3f7ee;color:#0a7a5a}
  .status-REJECTED{background:#fdecec;color:#b23c3c}
  .status-SUSPENDED{background:#e6e9ec;color:#4b5563}
</style>
</head>
<body class="auth-body">
<form class="auth-card" id="pro-form">
  <div class="auth-logo">
    <div class="auth-logo-mark">+</div>
    <div class="auth-logo-text">
      <strong>Elokinab Health</strong>
      <small>Espace professionnel</small>
    </div>
  </div>
  <h1>Profil de la structure</h1>
  <p class="sub">Ces informations sont verifiees par la pharmacie avant validation.</p>
  <div id="status-wrap"></div>
  <div id="msg" class="auth-msg hidden"></div>

  <div class="auth-field">
    <label for="structure_name">Nom de la structure</label>
    <input type="text" id="structure_name" required>
  </div>
  <div class="auth-field">
    <label for="structure_type">Type de structure</label>
    <select id="structure_type">
      <option value="CLINIQUE">Clinique</option>
      <option value="HOPITAL">Hopital</option>
      <option value="CABINET_MEDICAL">Cabinet medical</option>
      <option value="LABORATOIRE">Laboratoire</option>
      <option value="CENTRE_SANTE">Centre de sante</option>
      <option value="AUTRE">Autre</option>
    </select>
  </div>
  <div class="auth-field">
    <label for="manager_name">Responsable</label>
    <input type="text" id="manager_name" required>
  </div>
  <div class="auth-field">
    <label for="phone">Telephone</label>
    <input type="tel" id="phone" required>
  </div>
  <div class="auth-field">
    <label for="email">Email de contact (facultatif)</label>
    <input type="email" id="email">
  </div>
  <div class="auth-field">
    <label for="address">Adresse</label>
    <input type="text" id="address">
  </div>
  <div class="auth-field">
    <label>Position GPS (facultatif)</label>
    <button type="button" class="auth-btn" id="gps-btn" style="background:#6c8a80;margin-bottom:8px">📍 Utiliser ma position</button>
    <input type="number" id="latitude" step="0.00001" placeholder="Latitude">
    <input type="number" id="longitude" step="0.00001" placeholder="Longitude" style="margin-top:8px">
  </div>
  <div class="auth-field">
    <label for="notes">Informations complementaires</label>
    <textarea id="notes" rows="3"></textarea>
  </div>
  <button class="auth-btn" id="btn" type="submit">Enregistrer mon profil</button>
  <div class="auth-alt"><a href="/">Retour a l'accueil</a></div>
</form>
<script src="/static/professional.js"></script>
</body>
</html>
'''
(STATIC / "professional.html").write_text(PRO_HTML, encoding="utf-8")
print("[OK] static/professional.html")

PRO_JS = '''(function () {
  function $(id) { return document.getElementById(id); }
  function showMsg(t, ok) {
    var m = $("msg"); if (!m) return;
    m.textContent = t; m.className = "auth-msg" + (ok ? " ok" : "");
  }
  function hideMsg() { var m = $("msg"); if (m) m.className = "auth-msg hidden"; }

  var STATUS_LABELS = {
    PENDING: "En attente de validation",
    APPROVED: "Approuve",
    REJECTED: "Refuse",
    SUSPENDED: "Suspendu"
  };

  function loadProfile() {
    fetch("/api/professionals/me").then(function (r) {
      if (r.status === 404) return null;
      if (r.status === 401) { window.location.href = "/static/login.html"; return null; }
      if (!r.ok) return null;
      return r.json();
    }).then(function (p) {
      if (!p) return;
      $("structure_name").value = p.structure_name || "";
      $("structure_type").value = p.structure_type || "CLINIQUE";
      $("manager_name").value = p.manager_name || "";
      $("phone").value = p.phone || "";
      $("email").value = p.email || "";
      $("address").value = p.address || "";
      $("latitude").value = p.latitude || "";
      $("longitude").value = p.longitude || "";
      $("notes").value = p.notes || "";
      var w = $("status-wrap");
      if (p.status) {
        w.innerHTML = '<span class="status-pill status-' + p.status + '">' +
          (STATUS_LABELS[p.status] || p.status) + '</span>';
        if (p.status === "REJECTED" && p.rejection_reason) {
          showMsg("Motif du refus : " + p.rejection_reason);
        }
      }
    });
  }

  function submit(ev) {
    ev.preventDefault();
    hideMsg();
    var btn = $("btn"); btn.disabled = true; btn.textContent = "Enregistrement...";
    var body = {
      structure_name: $("structure_name").value.trim(),
      structure_type: $("structure_type").value,
      manager_name: $("manager_name").value.trim(),
      phone: $("phone").value.trim(),
      email: $("email").value.trim(),
      address: $("address").value.trim(),
      notes: $("notes").value.trim()
    };
    var lat = $("latitude").value;
    var lon = $("longitude").value;
    if (lat) body.latitude = Number(lat);
    if (lon) body.longitude = Number(lon);

    fetch("/api/professionals/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    }).then(function () {
      showMsg("Profil enregistre. En attente de validation.", true);
      btn.disabled = false; btn.textContent = "Enregistrer mon profil";
      loadProfile();
    }).catch(function (e) {
      showMsg(e.message);
      btn.disabled = false; btn.textContent = "Enregistrer mon profil";
    });
  }

  function gps() {
    if (!navigator.geolocation) { showMsg("GPS indisponible"); return; }
    var b = $("gps-btn"); b.disabled = true; b.textContent = "Localisation...";
    navigator.geolocation.getCurrentPosition(function (pos) {
      $("latitude").value = pos.coords.latitude.toFixed(5);
      $("longitude").value = pos.coords.longitude.toFixed(5);
      b.disabled = false; b.textContent = "📍 Utiliser ma position";
    }, function () {
      b.disabled = false; b.textContent = "📍 Utiliser ma position";
      showMsg("Position introuvable");
    }, { enableHighAccuracy: true, timeout: 15000 });
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadProfile();
    $("pro-form").addEventListener("submit", submit);
    $("gps-btn").addEventListener("click", gps);
  });
})();
'''
(STATIC / "professional.js").write_text(PRO_JS, encoding="utf-8")
print("[OK] static/professional.js")

print()
print("=" * 60)
print("PHASE 3 installee.")
print("=" * 60)
print()
print("Routes ajoutees :")
print("  POST   /api/professionals/profile          (PROFESSIONNEL)")
print("  GET    /api/professionals/me               (PROFESSIONNEL)")
print("  GET    /api/professionals                  (PHARMACIEN/ADMIN)")
print("  GET    /api/professionals/{id}             (PHARMACIEN/ADMIN)")
print("  PATCH  /api/professionals/{id}/status      (PHARMACIEN/ADMIN)")
print("  GET    /api/professionals/stats/summary    (PHARMACIEN/ADMIN)")
print()
print("Frontend :")
print("  /static/professional.html  (formulaire structure)")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  python main.py")