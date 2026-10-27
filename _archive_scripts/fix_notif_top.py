"""
fix_notif_top.py
Deplace la section Notifications tout en haut de l'accueil pro.
Ordre final : Bienvenue -> Nouvelle demande -> Alertes -> Notifications
             -> Reprendre -> Guide -> Activite recente -> Support
"""
from pathlib import Path
import re
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
HTML = STATIC / "professional.html"

shutil.copy2(HTML, HTML.with_suffix(".html.bak"))
print("[OK] Backup ->", HTML.with_suffix(".html.bak").name)

src = HTML.read_text(encoding="utf-8")

# 1. Extraire le bloc Notifications
pattern = re.compile(
    r'  <!-- Notifications -->.*?</section>\s*',
    re.DOTALL,
)
match = pattern.search(src)
if not match:
    print("[!] Bloc Notifications introuvable")
    raise SystemExit(1)

notif_block = match.group(0)
print("[OK] Bloc Notifications trouve")

# 2. Retirer le bloc de sa position actuelle
src = src.replace(notif_block, "", 1)

# 3. Reinserer apres l'alerte (alert-block) et avant Reprendre
anchor = '  <!-- Reprendre une commande -->'
if anchor not in src:
    # Fallback : avant "Guide demarrage"
    anchor = '  <!-- Guide demarrage'

if anchor in src:
    src = src.replace(anchor, notif_block + anchor, 1)
    HTML.write_text(src, encoding="utf-8")
    print("[OK] Notifications deplacees en haut")
else:
    print("[!] Anchor introuvable pour la reinserer")
    print("    Verifie le fichier professional.html")

# 4. Verification
check = HTML.read_text(encoding="utf-8")
pos_notif = check.find('id="notifications-section"')
pos_reorder = check.find('id="reorder-block"')
pos_activity = check.find('id="activity-section"')

if pos_notif > 0 and pos_reorder > 0 and pos_activity > 0:
    print()
    print("Ordre final dans le HTML :")
    if pos_notif < pos_reorder:
        print("  [OK] Notifications AVANT Reprendre")
    else:
        print("  [!] Notifications APRES Reprendre (a verifier)")
    if pos_notif < pos_activity:
        print("  [OK] Notifications AVANT Activite")
    else:
        print("  [!] Notifications APRES Activite")

print()
print("=" * 60)
print("NOTIFICATIONS REMONTEES")
print("=" * 60)
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur iPhone (ou navigation privee)")
print("  Pas besoin de redemarrer Uvicorn")