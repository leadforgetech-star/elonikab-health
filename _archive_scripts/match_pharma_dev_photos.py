"""
match_pharma_dev_photos.py

Matche les photos des 5 produits Pharma Developpement par mots-cles,
copie dans static/images/products/pharma_dev/ et met a jour image_url.

Usage :
    python match_pharma_dev_photos.py            # dry-run
    python match_pharma_dev_photos.py --commit   # applique
"""
import argparse
import re
import shutil
import sqlite3
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parent
SRC_DIR = BASE / "photos_pharma_dev"
DST_DIR = BASE / "static" / "images" / "products" / "pharma_dev"
DB_PATH = BASE / "database.db"

VALID_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# Mots-cles par produit (nom exact en base -> mots-cles obligatoires)
RULES = [
    ("HEMOFER Sirop",                       ["hemofer"]),
    ("HYDROSOL POLYVITAMINÉ Solution buvable", ["hydrosol"]),
    ("ALGESAL SURACTIVÉ Crème",             ["algesal", "suractive"]),
    ("ALGESAL BAUME Crème",                 ["algesal", "baume"]),
    ("A313 Pommade",                        ["a313"]),
]

IGNORE_TOKENS = {"de", "du", "des", "la", "le", "les", "et", "a", "d", "l"}


def strip_accents(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def norm(s):
    return strip_accents(s).lower()


def tokenize(s):
    return set(re.findall(r"[a-z0-9]+", norm(s)))


def file_keywords(path):
    return {t for t in tokenize(path.stem) if t not in IGNORE_TOKENS}


def slugify(s):
    s = strip_accents(s).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return re.sub(r"-+", "-", s)


def match_file(fk, rules):
    for name, keys in rules:
        if all(k in fk for k in keys):
            return name
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    print("=" * 64)
    print("MATCHING PHOTOS PHARMA DEVELOPPEMENT")
    print("=" * 64)
    print("Mode :", "COMMIT" if args.commit else "DRY-RUN")
    print("Source :", SRC_DIR)
    print("Cible  :", DST_DIR)
    print()

    if not SRC_DIR.exists():
        print("[ERREUR] Dossier source introuvable :", SRC_DIR)
        print("Cree-le et depose les photos dedans, puis relance.")
        return

    if not DB_PATH.exists():
        print("[ERREUR] Base introuvable :", DB_PATH)
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Charger les 5 produits Pharma Dev depuis la base
    names = [r[0] for r in RULES]
    placeholders = ",".join("?" for _ in names)
    rows = conn.execute(
        "SELECT id, name, presentation FROM products"
        " WHERE is_demo = 0 AND name IN (" + placeholders + ")",
        names,
    ).fetchall()

    if not rows:
        print("[ERREUR] Aucun produit Pharma Dev trouve en base.")
        print("Lance d'abord : python import_pharma_dev.py --commit")
        conn.close()
        return

    products = {}
    for r in rows:
        products[r["name"]] = {"id": r["id"], "presentation": r["presentation"] or ""}

    print(str(len(products)) + " produits Pharma Dev en base.")
    for n, p in products.items():
        print("  [" + str(p["id"]) + "] " + n)

    files = [f for f in sorted(SRC_DIR.iterdir())
             if f.is_file() and f.suffix.lower() in VALID_EXTS]
    print()
    print(str(len(files)) + " fichiers dans photos_pharma_dev/.")
    print()

    if not files:
        print("Aucun fichier a traiter.")
        conn.close()
        return

    matches = []
    unknown = []

    for f in files:
        fk = file_keywords(f)
        matched_name = match_file(fk, RULES)
        if matched_name and matched_name in products:
            matches.append((f, matched_name))
            print("  [OK]      " + f.name)
            print("            -> " + matched_name)
        else:
            unknown.append(f)
            print("  [INCONNU] " + f.name)

    print()
    print("=" * 64)
    print("  Matches clairs : " + str(len(matches)))
    print("  Inconnus       : " + str(len(unknown)))
    print("=" * 64)
    print()

    if not matches:
        print("Aucun match a appliquer.")
        conn.close()
        return

    print("Apercu :")
    for f, name in matches:
        slug = slugify(name)
        print("  " + f.name.ljust(35) + " -> " + slug + f.suffix.lower())
    print()

    if not args.commit:
        print("=" * 64)
        print("DRY-RUN : aucune modification.")
        print("Pour appliquer : python match_pharma_dev_photos.py --commit")
        print("=" * 64)
        conn.close()
        return

    DST_DIR.mkdir(parents=True, exist_ok=True)
    installed = 0
    updated = 0

    try:
        conn.execute("BEGIN")
        for f, name in matches:
            slug = slugify(name)
            ext = f.suffix.lower()
            target_name = slug + ext
            target_path = DST_DIR / target_name
            shutil.copy2(f, target_path)
            installed += 1
            url = "/static/images/products/pharma_dev/" + target_name
            cur = conn.execute(
                "UPDATE products SET image_url = ? WHERE id = ? AND is_demo = 0",
                (url, products[name]["id"]),
            )
            if cur.rowcount == 1:
                updated += 1
            else:
                raise RuntimeError("Update impossible pour " + name)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("[ERREUR]", e)
        print("ROLLBACK - aucune modification conservee.")
        conn.close()
        return

    conn.close()
    print("=" * 64)
    print("  Photos installees   : " + str(installed))
    print("  Produits mis a jour : " + str(updated))
    print("=" * 64)
    print()
    print("Ctrl+Shift+R dans le navigateur.")


if __name__ == "__main__":
    main()