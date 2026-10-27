"""
v3_auto_approve_pros.py
Les profils professionnels sont auto-approuves a la creation.
Plus de statut PENDING, plus de validation manuelle requise.
"""
from pathlib import Path
import datetime
import shutil
import sqlite3

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
MODULES = BASE / "v3_modules"
DB = BASE / "database.db"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_auto_approve_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. professionals.py : forcer APPROVED a la creation
# ============================================================
PROS = MODULES / "professionals.py"
shutil.copy2(PROS, backup / "professionals.py")
src = PROS.read_text(encoding="utf-8")

# Patch 1 : INSERT -> APPROVED au lieu de PENDING
old_insert = '''            if existing is None:
                cur = conn.execute(
                    "INSERT INTO professional_profiles"
                    " (user_id, structure_name, structure_type, manager_name,"
                    " phone, email, address, latitude, longitude, notes,"
                    " status, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)",'''
new_insert = '''            if existing is None:
                cur = conn.execute(
                    "INSERT INTO professional_profiles"
                    " (user_id, structure_name, structure_type, manager_name,"
                    " phone, email, address, latitude, longitude, notes,"
                    " status, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'APPROVED', ?)",'''
if old_insert in src:
    src = src.replace(old_insert, new_insert, 1)
    print("[OK] professionals.py -> INSERT avec APPROVED")

# Patch 2 : UPDATE -> APPROVED au lieu de PENDING
old_update = '''                conn.execute(
                    "UPDATE professional_profiles SET"
                    " structure_name=?, structure_type=?, manager_name=?,"
                    " phone=?, email=?, address=?, latitude=?, longitude=?,"
                    " notes=?, status='PENDING', rejection_reason=''"
                    " WHERE user_id=?",'''
new_update = '''                conn.execute(
                    "UPDATE professional_profiles SET"
                    " structure_name=?, structure_type=?, manager_name=?,"
                    " phone=?, email=?, address=?, latitude=?, longitude=?,"
                    " notes=?, status='APPROVED', rejection_reason=''"
                    " WHERE user_id=?",'''
if old_update in src:
    src = src.replace(old_update, new_update, 1)
    print("[OK] professionals.py -> UPDATE avec APPROVED")

# Patch 3 : suppression du bloc qui empeche de modifier si APPROVED
old_block = '''                if existing["status"] == "APPROVED":
                    raise HTTPException(
                        400,
                        "Profil approuve : contactez la pharmacie pour modification",
                    )
                conn.execute('''
new_block = '''                conn.execute('''
if old_block in src:
    src = src.replace(old_block, new_block, 1)
    print("[OK] professionals.py -> blocage modification retire")

PROS.write_text(src, encoding="utf-8")

# ============================================================
# 2. cart.py : retirer le blocage sur statut non-APPROVED
# ============================================================
CART = MODULES / "cart.py"
shutil.copy2(CART, backup / "cart.py")
csrc = CART.read_text(encoding="utf-8")

old_check = '''            # Un professionnel doit avoir un profil approuve
            if user["role"] == "PROFESSIONNEL":
                pro = conn.execute(
                    "SELECT status FROM professional_profiles WHERE user_id = ?",
                    (user["id"],),
                ).fetchone()
                if pro is None or pro["status"] != "APPROVED":
                    raise HTTPException(403, "Compte professionnel non approuve")

'''
if old_check in csrc:
    csrc = csrc.replace(old_check, "", 1)
    CART.write_text(csrc, encoding="utf-8")
    print("[OK] cart.py -> blocage professionnel retire")
else:
    print("[i] cart.py -> pas de blocage a retirer")

# ============================================================
# 3. Update en base : passer tous les PENDING existants a APPROVED
# ============================================================
conn = sqlite3.connect(DB)
cur = conn.cursor()
n = cur.execute(
    "UPDATE professional_profiles SET status='APPROVED' WHERE status != 'APPROVED'"
).rowcount
conn.commit()
conn.close()
print("[OK] " + str(n) + " profil(s) pro passe(s) a APPROVED en base")

# ============================================================
# 4. Frontend : retirer le bandeau PENDING sur professional.html
# ============================================================
PROJS = STATIC / "professional.js"
shutil.copy2(PROJS, backup / "professional.js")
pjs = PROJS.read_text(encoding="utf-8")

# Retirer la generation du bandeau de statut et du message de refus
old_status_block = '''      var w = $("status-wrap");
      if (p.status) {
        w.innerHTML = '<span class="status-pill status-' + p.status + '">' +
          (STATUS_LABELS[p.status] || p.status) + '</span>';
        if (p.status === "REJECTED" && p.rejection_reason) {
          showMsg("Motif du refus : " + p.rejection_reason);
        }
      }'''
new_status_block = '''      var w = $("status-wrap");
      if (w) w.innerHTML = "";'''
if old_status_block in pjs:
    pjs = pjs.replace(old_status_block, new_status_block, 1)
    print("[OK] professional.js -> bandeau statut retire")
else:
    print("[i] professional.js -> pattern statut introuvable")

# Retirer le message d'erreur "En attente de validation" apres save
old_msg = '''      showMsg("Profil enregistre. En attente de validation.", true);'''
new_msg = '''      showMsg("Profil enregistre.", true);'''
if old_msg in pjs:
    pjs = pjs.replace(old_msg, new_msg, 1)
    print("[OK] professional.js -> message simplifie")

PROJS.write_text(pjs, encoding="utf-8")

# ============================================================
# 5. Frontend : retirer le lien "Pro en attente" sur le dashboard pharmacien
# ============================================================
PHJS = STATIC / "pharmacien.js"
phjs = PHJS.read_text(encoding="utf-8")
# On garde la section dans le HTML mais elle restera vide (aucun PENDING)

print()
print("=" * 60)
print("AUTO-APPROBATION DES PROFESSIONNELS ACTIVEE")
print("=" * 60)
print()
print("Nouveaux comportements :")
print("  - Un pro qui cree son profil -> statut APPROVED immediatement")
print("  - Peut commander sans attendre de validation")
print("  - Il peut modifier son profil a tout moment")
print("  - Le dashboard pharmacien ne verra plus de pros en attente")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print("  Ctrl+Shift+R sur l'iPhone")