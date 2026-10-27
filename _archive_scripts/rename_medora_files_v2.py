"""
rename_medora_files_v2.py
Renommage par SOUS-CHAINE pour éviter les problemes de caracteres speciaux.
"""
from pathlib import Path

BASE = Path(__file__).resolve().parent
SRC = BASE / "photos_medora"

# (sous-chaine a chercher (lowercase, sans accents), nouveau nom)
# L'ordre est important : les cas les plus specifiques d'abord.
RULES = [
    # PARTIELS
    ("buprof",              "ibuprofene 400 2bl10.jpg"),
    ("ciprofloxacine 750",  "ciprofloxacine 750 10bl10.jpg"),
    ("cotrimoxazole 480 mg","cotrimoxazole 480 cp 10bl10.jpg"),
    ("dazel",               "dazel kit.jpg"),
    ("laino savon alep",    "laino savon d alep.jpg"),
    ("tribioderm",          "tribioderm 144 pommade dermique.jpg"),

    # INCONNUS
    ("ampiciline 500",      "ampicilline 500mg gelules.jpg"),
    ("ampiciline im",       "ampicilline im inj 1g b50.jpg"),
    ("azibact",             "azibact 50 cp b3.jpg"),
    ("benzatine",           "benzatine 2 4 mui.jpg"),
    ("cal chek",            "calchek 10mg b30.jpg"),
    ("ciprofloxacine inj",  "ciprofloxacine 100mg 50ml sol inj.jpg"),
    ("metagard",            "metagard cr 35 mg b30.jpg"),
    ("zerodol",             "zerodol cr 200 mg b10.jpg"),

    # CAS MANUELS
    ("moustidose",          "moustidose-produit.jpg"),
]

def strip_accents(s):
    import unicodedata
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

def norm(s):
    return strip_accents(s).lower()

def main():
    if not SRC.exists():
        print("[ERREUR] Dossier introuvable :", SRC)
        return

    files = [p for p in SRC.iterdir() if p.is_file()]
    print("=" * 60)
    print("RENOMMAGE PAR SOUS-CHAINE")
    print("=" * 60)
    print(str(len(files)) + " fichiers dans le dossier.")
    print()

    renamed = 0
    not_matched = []

    for needle, new_name in RULES:
        # Chercher un fichier qui contient la sous-chaine
        matches = [f for f in files if needle in norm(f.name)]
        if not matches:
            not_matched.append(needle)
            continue
        # Prendre le premier match
        old_path = matches[0]
        new_path = SRC / new_name
        # Eviter collision avec un fichier deja renomme
        if new_path.exists() and old_path.resolve() != new_path.resolve():
            print("  [SKIP] " + old_path.name + " -> " + new_name + " (cible existe deja)")
            continue
        old_path.rename(new_path)
        print("  [OK] " + old_path.name)
        print("       -> " + new_name)
        renamed += 1
        files.remove(old_path)

    print()
    print("=" * 60)
    print("  Renommes    : " + str(renamed))
    print("  Non matche  : " + str(len(not_matched)))
    print("=" * 60)

    if not_matched:
        print()
        print("Sous-chaines non trouvees :")
        for n in not_matched:
            print("  -", n)

    # Lister les fichiers restants pour verification
    print()
    print("Fichiers restants dans photos_medora/ :")
    for f in sorted(SRC.iterdir()):
        if f.is_file():
            print("  " + f.name)

if __name__ == "__main__":
    main()