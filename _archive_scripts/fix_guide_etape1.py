"""
fix_guide_etape1.py
Remplace uniquement le texte de l'etape 1 du guide.
"""
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent
JS = BASE / "static" / "professional_dashboard.js"
shutil.copy2(JS, JS.with_suffix(".js.bak"))
print("[OK] Backup ->", JS.with_suffix(".js.bak").name)

src = JS.read_text(encoding="utf-8")

# Texte actuel (issu de fix_guide_text.py)
old = ("Ajoutez des produits depuis le <strong>catalogue</strong> "
       "ou envoyez votre liste (photo, PDF, texte) via <strong>WhatsApp</strong>.")

# Nouveau texte clair
new = ("Ouvrez l'onglet <strong>+ Demande</strong>, puis choisissez : "
       "<strong>Catalogue</strong> (ajoutez vos produits un par un) "
       "ou <strong>WhatsApp</strong> (envoyez votre liste par texte, photo ou PDF).")

if old in src:
    src = src.replace(old, new, 1)
    JS.write_text(src, encoding="utf-8")
    print("[OK] Etape 1 reformulee")
else:
    print("[!] Texte etape 1 introuvable — debug :")
    idx = src.find("Ajoutez des produits")
    if idx > 0:
        print(src[max(0, idx - 80):idx + 250])
    else:
        idx = src.find("acc-guide-text")
        if idx > 0:
            print("Contexte acc-guide-text :")
            print(src[max(0, idx - 50):idx + 300])

print()
print("PROCHAINE ETAPE : Ctrl+Shift+R sur l'accueil pro")