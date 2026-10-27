"""
auto_rename_photos.py
Scanne _inbox/, devine a quel produit chaque image correspond,
la copie au bon nom dans medora/.
Ne supprime rien de _inbox/.
"""
from pathlib import Path
import shutil
import re
import unicodedata

BASE = Path(__file__).resolve().parent
INBOX = BASE / "static" / "images" / "products" / "_inbox"
DEST = BASE / "static" / "images" / "products" / "medora"
DEST.mkdir(parents=True, exist_ok=True)
INBOX.mkdir(parents=True, exist_ok=True)

# Nom cible + mots-cles qui doivent apparaitre dans le nom du fichier source
RULES = [
    # (nom_fichier_cible, [mots-cles obligatoires (tous en lowercase, sans accents)])
    ("laino-savon-marseille.jpg",      ["laino", "marseille"]),
    ("laino-savon-alep.jpg",           ["laino", "alep"]),
    ("moustidose.jpg",                 ["moustidose"]),
    ("fedate-sirop.jpg",               ["fedate", "sirop"]),
    ("fedate-gelules.jpg",             ["fedate", "gelul"]),
    ("dazel-kit.jpg",                  ["dazel"]),
    ("hepafyt.jpg",                    ["hepafyt"]),
    ("ridmal.jpg",                     ["ridmal"]),
    ("calchek-10mg.jpg",               ["calchek"]),
    ("metagard-cr.jpg",                ["metagard"]),
    ("ubi-acide-fusidique-creme-2.jpg",["fusidique"]),
    ("ubi-amoxicilline-125mg.jpg",     ["amoxicilline", "125"]),
    ("ubi-amoxicilline-250mg.jpg",     ["amoxicilline", "250"]),
    ("ubi-amoxicilline-500mg.jpg",     ["amoxicilline", "500"]),
    ("ubi-ampicilline-1g.jpg",         ["ampicilline", "1g"]),
    ("ubi-ampicilline-1g.jpg",         ["ampicilline", "1 g"]),
    ("ubi-ampicilline-500mg.jpg",      ["ampicilline", "500"]),
    ("ubi-benzatine-2-4mui.jpg",       ["benzatine"]),
    ("ubi-ciprofloxacine-100mg.jpg",   ["ciprofloxacine", "100"]),
    ("ubi-ciprofloxacine-750mg.jpg",   ["ciprofloxacine", "750"]),
    ("ubi-cotrimoxazole-480mg-susp.jpg",["cotrimoxazole", "480", "5ml"]),
    ("ubi-cotrimoxazole-480mg-susp.jpg",["cotrimoxazole", "480", "susp"]),
    ("ubi-cotrimoxazole-480mg.jpg",    ["cotrimoxazole", "480"]),
    ("ubi-cotrimoxazole-fort-960mg.jpg",["cotrimoxazole", "960"]),
    ("ubi-tribioderm.jpg",             ["tribioderm"]),
    ("ubi-oxacilline-250mg.jpg",       ["oxacilline", "250"]),
    ("ubi-oxacilline-500mg.jpg",       ["oxacilline", "500"]),
    ("azibact-50mg.jpg",               ["azibact"]),
    ("stericef-1g.jpg",                ["stericef"]),
    ("ubi-desloratadine.jpg",          ["desloratadine"]),
    ("ubi-nystatine.jpg",              ["nystatine"]),
    ("ubi-clotrimazole-200mg.jpg",     ["clotrimazole"]),
    ("ubi-fer-sirop.jpg",              ["fer", "sirop"]),
    ("ubi-omeprazole-20mg.jpg",        ["omeprazole"]),
    ("ubi-esomeprazole-40mg.jpg",      ["esomeprazole"]),
    ("ubi-artemether-80mg.jpg",        ["artemether", "80"]),
    ("ubi-artemether-40mg.jpg",        ["artemether", "40"]),
    ("ubi-artemether-20mg.jpg",        ["artemether", "20"]),
    ("larinate-60mg.jpg",              ["larinate"]),
    ("ubi-lidocaine-2.jpg",            ["lidocaine"]),
    ("ubi-ibuprofene-400mg-2bl10.jpg", ["ibuprofene", "400", "2"]),
    ("ubi-ibuprofene-400mg-10bl10.jpg",["ibuprofene", "400", "10"]),
    ("ubi-ketoprofene-100mg.jpg",      ["ketoprofene"]),
    ("ubi-diclofenac-50mg.jpg",        ["diclofenac", "50"]),
    ("ubi-diclofenac-75mg.jpg",        ["diclofenac", "75"]),
    ("zerodol-cr.jpg",                 ["zerodol"]),
    ("ubi-acide-acetyle-salicylique-500mg.jpg",["acetyle"]),
    ("ubi-acide-acetyle-salicylique-500mg.jpg",["aspirine"]),
    ("ubi-paracetamol-120mg-susp.jpg", ["paracetamol", "120"]),
    ("ubi-paracetamol-500mg.jpg",      ["paracetamol", "500"]),
    ("ubi-albendazole-400mg.jpg",      ["albendazole"]),
    ("ubi-mebendazole-100mg.jpg",      ["mebendazole", "100"]),
    ("ubi-mebendazole-100mg-susp.jpg", ["mebendazole", "susp"]),
    ("ubi-mebendazole-100mg-susp.jpg", ["mebendazole", "5ml"]),
    ("ubi-metronidazole-125mg-susp.jpg",["metronidazole", "125"]),
    ("ubi-metronidazole-250mg.jpg",    ["metronidazole", "250"]),
    ("ubi-metronidazole-500mg-perf.jpg",["metronidazole", "500"]),
]

def normalize(s):
    s = s.lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s

def match(filename):
    n = normalize(filename)
    matches = []
    for target, kws in RULES:
        if all(k in n for k in kws):
            matches.append(target)
    return matches

def main():
    files = [p for p in INBOX.iterdir() if p.is_file() and p.suffix.lower() in
             (".jpg", ".jpeg", ".png", ".webp", ".heic")]
    if not files:
        print("[!] Aucun fichier image dans :", INBOX)
        print("    Depose tes photos dans ce dossier puis relance ce script.")
        return

    ok, ambiguous, unknown = 0, [], []
    for f in files:
        targets = set(match(f.name))
        if len(targets) == 1:
            target = targets.pop()
            dest = DEST / target
            shutil.copy2(f, dest)
            print("  [OK]   " + f.name + "  ->  " + target)
            ok += 1
        elif len(targets) > 1:
            ambiguous.append((f.name, sorted(targets)))
            print("  [AMBIGU] " + f.name + "  ->  " + str(sorted(targets)))
        else:
            unknown.append(f.name)
            print("  [INCONNU] " + f.name)

    print()
    print("=======================================================")
    print("  Copiees   :", ok)
    print("  Ambigues  :", len(ambiguous))
    print("  Inconnues :", len(unknown))
    print("=======================================================")
    if ambiguous:
        print()
        print("Fichiers ambigus (a renommer a la main) :")
        for name, targets in ambiguous:
            print("  " + name + " -> " + ", ".join(targets))
    if unknown:
        print()
        print("Fichiers inconnus (renomme-les avec des mots-cles du produit) :")
        for name in unknown:
            print("  " + name)
    print()
    print("Les fichiers sources dans _inbox ne sont PAS supprimes.")
    print("Une fois satisfait, tu peux lancer :")
    print("   python link_medora_photos.py --commit")

if __name__ == "__main__":
    main()