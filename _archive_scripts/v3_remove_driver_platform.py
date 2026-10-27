"""
v3_remove_driver_platform.py
Retire la plateforme livreur (dashboard dedie) et garde
uniquement le bouton WhatsApp 'Envoyer au livreur' cote pharmacien.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_remove_driver_platform_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
print("[OK] Backup ->", backup.name)

for f in ("pharmacien.js", "pharmacien.html", "header.js", "register.html"):
    p = STATIC / f
    if p.exists():
        shutil.copy2(p, backup / f)

# ============================================================
# 1. pharmacien.js : retirer le bouton "Assigner"
# ============================================================
PHJS = STATIC / "pharmacien.js"
js = PHJS.read_text(encoding="utf-8")

# Retirer le bloc qui ajoute le bouton Assigner
old_assign = '''    var assignBtn = el("button", "btn btn-ghost", "\\uD83D\\uDC64 Assigner");
    assignBtn.type = "button";
    assignBtn.addEventListener("click", function () { openAssignModal(o); });
    driverBox.appendChild(assignBtn);'''
if old_assign in js:
    js = js.replace(old_assign, "", 1)
    print("[OK] pharmacien.js -> bouton Assigner retire")
elif "assignBtn" in js:
    # variante avec des guillemets differents
    import re
    js = re.sub(
        r'\s*var assignBtn = el\("button"[^;]*openAssignModal\(o\);[^}]*\}\);\s*driverBox\.appendChild\(assignBtn\);',
        "",
        js,
        count=1,
    )
    print("[i] pharmacien.js -> bouton Assigner (fallback)")
else:
    print("[i] pharmacien.js -> bouton Assigner deja absent")

PHJS.write_text(js, encoding="utf-8")

# ============================================================
# 2. header.js : retirer le lien "Mes livraisons"
# ============================================================
HJ = STATIC / "header.js"
hjs = HJ.read_text(encoding="utf-8")

old_driver_menu = '''      if (user.role === "LIVREUR_MOTO" || user.role === "CHAUFFEUR") {
        var a = el("a", null, "Mes livraisons");
        a.href = "/static/driver.html";
        dd.appendChild(a);
      }
'''
if old_driver_menu in hjs:
    hjs = hjs.replace(old_driver_menu, "", 1)
    HJ.write_text(hjs, encoding="utf-8")
    print("[OK] header.js -> lien Mes livraisons retire")
else:
    print("[i] header.js -> lien Mes livraisons deja absent ou pattern different")

# ============================================================
# 3. register.html : retirer LIVREUR et CHAUFFEUR des choix publics
# ============================================================
REG = STATIC / "register.html"
html = REG.read_text(encoding="utf-8")

# Le select ne devrait contenir que Particulier et Professionnel
# On verifie qu'il n'y a pas d'option LIVREUR / CHAUFFEUR
changed = False
if 'value="LIVREUR_MOTO"' in html or 'value="CHAUFFEUR"' in html:
    import re
    html = re.sub(r'<option[^>]*value="LIVREUR_MOTO"[^>]*>.*?</option>\s*', '', html)
    html = re.sub(r'<option[^>]*value="CHAUFFEUR"[^>]*>.*?</option>\s*', '', html)
    changed = True

if changed:
    REG.write_text(html, encoding="utf-8")
    print("[OK] register.html -> LIVREUR / CHAUFFEUR retires des choix")
else:
    print("[i] register.html -> deja sans LIVREUR / CHAUFFEUR")

# ============================================================
# 4. Blocage d'acces a /static/driver.html depuis le dashboard
# ============================================================
# On cache le fichier en le renommant (garde la possibilite de revenir)
DRIVER = STATIC / "driver.html"
if DRIVER.exists():
    hidden = STATIC / "_driver.html.disabled"
    if hidden.exists():
        hidden.unlink()
    DRIVER.rename(hidden)
    print("[OK] static/driver.html -> desactive (renomme en _driver.html.disabled)")

DRIVER_JS = STATIC / "driver.js"
if DRIVER_JS.exists():
    hidden_js = STATIC / "_driver.js.disabled"
    if hidden_js.exists():
        hidden_js.unlink()
    DRIVER_JS.rename(hidden_js)
    print("[OK] static/driver.js -> desactive")

# ============================================================
# 5. Retirer la reference dans pharmacien.html (assign modal)
# ============================================================
PH_HTML = STATIC / "pharmacien.html"
phtml = PH_HTML.read_text(encoding="utf-8")

# Retirer le modal d'assignation (s'il existe encore)
import re
new_html = re.sub(
    r'<div id="assign-modal".*?</div>\s*</div>\s*</div>\s*(?=<script)',
    '',
    phtml,
    flags=re.DOTALL,
)
if new_html != phtml:
    PH_HTML.write_text(new_html, encoding="utf-8")
    print("[OK] pharmacien.html -> modal d'assignation retire")
else:
    print("[i] pharmacien.html -> modal d'assignation deja absent")

# ============================================================
# 6. Info : le bouton WhatsApp reste en place
# ============================================================
print()
print("=" * 60)
print("PLATEFORME LIVREUR RETIREE")
print("=" * 60)
print()
print("Ce qui reste actif :")
print("  - Bouton 'Envoyer au livreur' (WhatsApp) dans le dashboard")
print("  - Liste des livreurs (gere depuis Parametres pharmacien)")
print("  - Numero WhatsApp pre-rempli avec la commande + GPS")
print()
print("Ce qui est retire :")
print("  - Bouton 'Assigner' (plateforme)")
print("  - Lien 'Mes livraisons' dans le menu")
print("  - Page /static/driver.html (renommee en .disabled)")
print("  - Role LIVREUR_MOTO / CHAUFFEUR a l'inscription")
print()
print("Pour reactiver plus tard : renommer _driver.html.disabled en driver.html")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur l'iPhone (ou navigation privee)")