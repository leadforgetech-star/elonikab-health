"""
fix_login_neutre.py
1. Login : texte neutre (particulier + pro)
2. Register : retire l'option "Pharmacie"
"""
from pathlib import Path
import re
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
LOGIN = STATIC / "login.html"
REGISTER = STATIC / "register.html"

shutil.copy2(LOGIN, LOGIN.with_suffix(".html.bak"))
shutil.copy2(REGISTER, REGISTER.with_suffix(".html.bak"))
print("[OK] Backups crees")

# ============================================================
# 1. Login : texte neutre
# ============================================================
src = LOGIN.read_text(encoding="utf-8")

replacements = [
    ("Connectez-vous a votre espace professionnel.",
     "Connectez-vous a votre espace."),
    ('Pas encore de compte ? <a href="/inscription">Creer un compte professionnel</a>',
     'Pas encore de compte ? <a href="/inscription">Creer un compte</a>'),
    ("Votre espace professionnel, protege et confidentiel.",
     "Votre espace personnel, protege et confidentiel."),
]

count = 0
for old, new in replacements:
    if old in src:
        src = src.replace(old, new)
        count += 1
        print("[OK] login : '" + old[:40] + "...'")

LOGIN.write_text(src, encoding="utf-8")
print(f"[OK] login.html : {count} remplacement(s)")

# ============================================================
# 2. Register : retirer le bouton Pharmacie
# ============================================================
rsrc = REGISTER.read_text(encoding="utf-8")

old_pharma = '''        <button type="button" class="type-btn" data-value="PHARMACIE">
          <span class="ico">&#128138;</span>Pharmacie
        </button>
'''
if old_pharma in rsrc:
    rsrc = rsrc.replace(old_pharma, "")
    REGISTER.write_text(rsrc, encoding="utf-8")
    print("[OK] register.html : bouton Pharmacie retire")
elif "Pharmacie" in rsrc:
    # Fallback : regex
    pattern = re.compile(
        r'\s*<button[^>]*data-value="PHARMACIE".*?</button>\s*',
        re.DOTALL,
    )
    rsrc = pattern.sub("", rsrc)
    REGISTER.write_text(rsrc, encoding="utf-8")
    print("[OK] register.html : bouton Pharmacie retire (fallback)")
else:
    print("[i] register.html : Pharmacie deja absent")

# Verifications
print()
login_check = LOGIN.read_text(encoding="utf-8")
if "espace professionnel" in login_check:
    print("[!] login : 'espace professionnel' encore present")
else:
    print("[OK] login : plus de mention 'espace professionnel'")

reg_check = REGISTER.read_text(encoding="utf-8")
if "PHARMACIE" in reg_check or "Pharmacie" in reg_check:
    print("[!] register : 'Pharmacie' encore present")
else:
    print("[OK] register : 'Pharmacie' retire")

print()
print("=" * 60)
print("FIX APPLIQUE")
print("=" * 60)
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur le navigateur (ou navigation privee)")
print("  Pas besoin de redemarrer Uvicorn")