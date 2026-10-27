from pathlib import Path
import shutil
import re

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"

src = MAIN.read_text(encoding="utf-8")
shutil.copy(MAIN, MAIN.with_suffix(".py.bak"))
print("[OK] sauvegarde ->", MAIN.with_suffix(".py.bak").name)

# 1) Localiser le message actuel
old_variants = [
    'raise HTTPException(status_code=400, detail="Adresse obligatoire pour la livraison")',
    'raise HTTPException(\n            status_code=400,\n            detail="Adresse obligatoire pour la livraison",\n        )',
]

found = None
for v in old_variants:
    if v in src:
        found = v
        break

if found is None:
    # Chercher le message brut
    idx = src.find("Adresse obligatoire pour la livraison")
    if idx == -1:
        print("[i] ancien message introuvable — le patch est peut-etre deja applique.")
        if "Adresse ou localisation GPS obligatoire" in src:
            print("[OK] le nouveau message est deja en place.")
        raise SystemExit(0)
    # Extraire la ligne entiere (du debut de la ligne jusqu'au retour a la ligne)
    line_start = src.rfind("\n", 0, idx) + 1
    line_end = src.find("\n", idx)
    found = src[line_start:line_end]
    print("[i] ligne exacte trouvee :")
    print("    " + found)

# 2) Construire le remplacement : insérer la vérif GPS avant
#    On remplace le bloc if existant par le nouveau
new_block = '''    has_gps = latitude is not None and longitude is not None
    if delivery_mode == "livraison" and not address.strip() and not has_gps:
        raise HTTPException(
            status_code=400,
            detail="Adresse ou localisation GPS obligatoire pour la livraison",
        )'''

# Remplacer par regex souple (cherche tout un if contenant le message)
pattern = re.compile(
    r'(\n[ \t]*if delivery_mode == "livraison"[^\n]*Adresse obligatoire pour la livraison[^\n]*\n(?:[ \t]+[^\n]*\n)*)',
)

if pattern.search(src):
    src = pattern.sub("\n" + new_block + "\n", src, count=1)
    MAIN.write_text(src, encoding="utf-8")
    print("[OK] main.py -> bloc remplace (adresse facultative si GPS)")
else:
    # Fallback : remplacer juste la ligne
    src = src.replace(found, new_block)
    MAIN.write_text(src, encoding="utf-8")
    print("[OK] main.py -> ligne remplacee (fallback)")

# 3) Verification
check = MAIN.read_text(encoding="utf-8")
if "Adresse ou localisation GPS obligatoire" in check:
    print("[OK] nouveau message present")
else:
    print("[!] nouveau message absent — patch a echoue")
if "Adresse obligatoire pour la livraison" in check:
    print("[!] ancien message encore present")
else:
    print("[OK] ancien message supprime")

# 4) Afficher le contexte pour verification
idx = check.find("Adresse ou localisation GPS obligatoire")
if idx > 0:
    print()
    print("--- Contexte du nouveau bloc ---")
    print(check[max(0, idx - 400): idx + 150])
    print("--- fin contexte ---")

print()
print("Fix applique.")
print("Redemarre le serveur (taskkill /F /IM python.exe puis python main.py).")
print("Puis Ctrl+Shift+R dans le navigateur.")