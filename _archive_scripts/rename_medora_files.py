"""
rename_medora_files.py
Renomme les fichiers problematiques dans photos_medora/ avant le matching.
"""
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
SRC = BASE / "photos_medora"

# Mapping exact : ancien nom -> nouveau nom
# (14 cas clairs + 2 cas a decider manuellement, laisses de cote)
RENAME_MAP = {
    # --- PARTIELS (6) ---
    "buprofène 400MG CPR 2BL10 — 1 650 F.jpg":         "ibuprofene 400 2bl10.jpg",
    "CIPROFLOXACINE 750MG.jpg":                        "ciprofloxacine 750 10bl10.jpg",
    "COTRIMOXAZOLE 480 MG.jpg":                        "cotrimoxazole 480 cp 10bl10.jpg",
    "dazel (1).jpg":                                   "dazel kit.jpg",
    "LAINO SAVON ALEP.jpg":                            "laino savon d alep.jpg",
    "Tribioderm pommade dermique.jpg":                 "tribioderm 144 pommade dermique.jpg",

    # --- INCONNUS (10) ---
    "ampiciline 500MG.jpg":                            "ampicilline 500mg gelules.jpg",
    "ampiciline im inj.jpg":                           "ampicilline im inj 1g b50.jpg",
    "AZIBACT.jpg":                                     "azibact 50 cp b3.jpg",
    "BENZATINE.jpg":                                   "benzatine 2 4 mui.jpg",
    "cal chek 10.jpg":                                 "calchek 10mg b30.jpg",
    "CIPROFLOXACINE INJ.jpg":                          "ciprofloxacine 100mg 50ml sol inj.jpg",
    "METAGARD.jpg":                                    "metagard cr 35 mg b30.jpg",
    "ZERODOL.jpg":                                     "zerodol cr 200 mg b10.jpg",

    # --- Cas ambigus : NON traites automatiquement ---
    # "laino.jpg"           -> A TOI DE CHOISIR (voir ci-dessous)
    # "MOUSTIDOSE.jpg"      -> A INVESTIGUER (voir ci-dessous)
}

def main():
    if not SRC.exists():
        print("[ERREUR] Dossier introuvable :", SRC)
        return

    existing = {p.name for p in SRC.iterdir() if p.is_file()}
    renamed = 0
    not_found = []
    conflicts = []

    print("=" * 60)
    print("RENOMMAGE DES FICHIERS MEDORA")
    print("=" * 60)
    print()

    for old_name, new_name in RENAME_MAP.items():
        if old_name not in existing:
            not_found.append(old_name)
            continue
        old_path = SRC / old_name
        new_path = SRC / new_name
        if new_path.exists():
            conflicts.append((old_name, new_name))
            continue
        old_path.rename(new_path)
        print("  [OK] " + old_name)
        print("       -> " + new_name)
        renamed += 1

    print()
    print("=" * 60)
    print("  Renommes   : " + str(renamed))
    print("  Introuvables: " + str(len(not_found)))
    print("  Conflits   : " + str(len(conflicts)))
    print("=" * 60)

    if not_found:
        print()
        print("Fichiers NON trouves (verifie les noms exacts) :")
        for n in not_found:
            print("  - " + n)
    if conflicts:
        print()
        print("Conflits (nouveau nom deja existant) :")
        for o, n in conflicts:
            print("  - " + o + " -> " + n)

    print()
    print("Lance ensuite : python match_and_link_photos.py")

if __name__ == "__main__":
    main()