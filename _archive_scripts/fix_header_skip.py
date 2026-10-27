"""
fix_header_skip.py
Empeche header.js de s'injecter sur les pages a carte centree.
"""
from pathlib import Path
import datetime
import re
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_header_skip_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(STATIC / "header.js", backup / "header.js")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. Modifier header.js : ignorer les pages a carte centree
# ============================================================
HJ = STATIC / "header.js"
js = HJ.read_text(encoding="utf-8")

# Ajouter un early-return en haut de la fonction inject()
old_inject = """  function inject() {
    Promise.all(["""
new_inject = """  function inject() {
    // Ne PAS injecter sur les pages a carte centree (auth-body)
    var SKIP_PAGES = [
      "/static/login.html",
      "/static/register.html",
      "/static/payment.html",
      "/static/professional.html",
      "/static/notifications.html",
      "/static/driver.html"
    ];
    var path = window.location.pathname;
    for (var i = 0; i < SKIP_PAGES.length; i++) {
      if (path.indexOf(SKIP_PAGES[i]) === 0) return;
    }
    // Si la page a deja un .auth-body, on saute aussi
    if (document.body.classList.contains("auth-body")) return;

    Promise.all(["""

if old_inject in js:
    js = js.replace(old_inject, new_inject, 1)
    HJ.write_text(js, encoding="utf-8")
    print("[OK] header.js -> skip sur pages auth-body")
elif "SKIP_PAGES" in js:
    print("[i] header.js deja patche")
else:
    print("[!] anchor inject() introuvable")

# ============================================================
# 2. Verifier que la garde auth-body existe aussi
# ============================================================
check = HJ.read_text(encoding="utf-8")
if "auth-body" in check and "SKIP_PAGES" in check:
    print("[OK] header.js correctement patche")
else:
    print("[!] A verifier manuellement")

# ============================================================
# 3. Retirer header.js des pages a carte centree (au cas ou)
# ============================================================
PAGES_CARD = [
    "login.html", "register.html", "payment.html",
    "professional.html", "notifications.html", "driver.html",
]
for page in PAGES_CARD:
    p = STATIC / page
    if not p.exists():
        continue
    c = p.read_text(encoding="utf-8")
    changed = False

    # Retirer le script header.js
    if '<script src="/static/header.js"></script>' in c:
        c = c.replace('<script src="/static/header.js"></script>\n', '', 1)
        c = c.replace('<script src="/static/header.js"></script>', '', 1)
        changed = True

    if changed:
        p.write_text(c, encoding="utf-8")
        print("[OK] " + page + " -> header.js retire")

print()
print("=" * 60)
print("FIX HEADER SKIP APPLIQUE")
print("=" * 60)
print()
print("Effet :")
print("  - login, register, payment, professional, notifications, driver")
print("    n'auront plus de header injecte")
print("  - La carte reste seule et centree sur toute la largeur")
print("  - Les autres pages (accueil, panier, dashboard) gardent le header")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur l'iPhone (ou navigation privee)")