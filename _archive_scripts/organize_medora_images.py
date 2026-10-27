"""
organize_medora_images.py

Range les photos Medora par ordre numerique.
- Photos attendues : photos_medora/001.jpg a 053.jpg (peu importe l'extension)
- Ordre maitre : 53 produits (voir MASTER ci-dessous)
- Dry-run par defaut, --commit pour appliquer

Regles :
  - Refuse le commit si le nombre de photos != 53
  - Refuse le commit si un numero est manquant ou en double
  - Refuse le commit si un produit n'est pas retrouve en base
  - Mise a jour uniquement du champ image_url, dans une transaction SQLite
"""
import argparse
import re
import shutil
import sqlite3
import sys
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parent
SRC_DIR = BASE / "photos_medora"
DST_DIR = BASE / "static" / "images" / "products" / "medora"
DB_PATH = BASE / "database.db"

VALID_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# ============================================================
# ORDRE MAITRE DES 53 PRODUITS
# ============================================================
# Pour chaque entree : (name, presentation_ou_None)
# presentation_ou_None = None -> recherche par name seul
# presentation precise -> recherche par (name, presentation) [pour les 2 Ibuprofene]
MASTER = [
    ("Laino Savon de Marseille", None),
    ("Laino Savon d'Alep", None),
    ("Moustidose", None),
    ("Fedate sirop", None),
    ("Fedate gélules", None),
    ("Dazel kit", None),
    ("Hepafyt", None),
    ("Ridmal", None),
    ("Azibact cp 50 mg (Azithromycine)", None),
    ("Zerodol CR (Aceclofenac 200 mg)", None),
    ("Stericef 1 g injectable (Ceftrie)", None),
    ("Larinate 60 mg (Artesunate injectable)", None),
    ("CALCHEK 10 mg (Amlodipine)", None),
    ("Metagard CR (Trimetazidine 35 mg)", None),
    ("UBI Acide fusidique crème 2%", None),
    ("UBI Amoxicilline 125 MG", None),
    ("UBI Amoxicilline 250MG", None),
    ("UBI Amoxicilline 500MG", None),
    ("UBI Ampicilline IM INJ 1G", None),
    ("UBI Ampicilline 500MG", None),
    ("UBI Benzatine benzylpenicilline 2,4 MUI", None),
    ("UBI Ciprofloxacine 100MG/50ML", None),
    ("UBI Ciprofloxacine 750MG", None),
    ("UBI Cotrimoxazole 480MG/5ML", None),
    ("UBI Cotrimoxazole 480MG", None),
    ("UBI Cotrimoxazole Fort 960MG", None),
    ("UBI Tribioderm pommade dermique", None),
    ("UBI Oxacilline 250MG/5ML", None),
    ("UBI Oxacilline 500MG", None),
    ("UBI Desloratadine 0,5MG/ML", None),
    ("UBI Nystatine 100.000UI/ml", None),
    ("UBI Clotrimazole 200MG", None),
    ("UBI Fer (Ferrique Citrate d'ammonium, Vit B9, Vit B12, Cu, Mn)", None),
    ("UBI Oméprazole 20MG", None),
    ("UBI Esomeprazole 40MG", None),
    ("UBI Artemether 80mg", None),
    ("UBI Artemether 40mg", None),
    ("UBI Artemether 20mg", None),
    ("UBI Lidocaïne 2%", None),
    ("UBI Ibuprofène 400MG", "Comprimés · 2 BL 10"),
    ("UBI Ibuprofène 400MG", "Comprimés · 10 BL 10"),
    ("UBI Kétoprofène 100MG", None),
    ("UBI Diclofénac 50MG", None),
    ("UBI Diclofénac sodique 75MG", None),
    ("UBI Acide Acétyle salicylique 500MG", None),
    ("UBI Paracétamol 120MG/5ML", None),
    ("UBI Paracétamol 500MG", None),
    ("UBI Albendazole 400MG", None),
    ("UBI Mébendazole 100MG", None),
    ("UBI Mébendazole 100MG/5ML", None),
    ("UBI Métronidazole 125MG/5ML", None),
    ("UBI Métronidazole 250MG", None),
    ("UBI Métronidazole 500MG/100ML", None),
]

EXPECTED_COUNT = len(MASTER)  # doit valoir 53


def slugify(s):
    """Retire les accents, met en minuscules, remplace tout sauf alphanumerique par tiret."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def scan_photos():
    """Retourne {numero: Path} pour les fichiers valides dans photos_medora/."""
    if not SRC_DIR.exists():
        return {}
    found = {}
    duplicates = []
    for p in SRC_DIR.iterdir():
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext not in VALID_EXTS:
            continue
        m = re.match(r"^(\d+)\.[A-Za-z]+$", p.name)
        if not m:
            continue
        num = int(m.group(1))
        if num in found:
            duplicates.append((num, p.name, found[num].name))
        else:
            found[num] = p
    return found, duplicates


def find_product_id(conn, name, presentation):
    cur = conn.cursor()
    if presentation is None:
        rows = cur.execute(
            "SELECT id FROM products WHERE name = ? AND is_demo = 0",
            (name,),
        ).fetchall()
        if len(rows) == 1:
            return rows[0][0], None
        if len(rows) == 0:
            return None, "Produit introuvable (nom = '" + name + "')"
        return None, "Plusieurs produits is_demo=0 avec le nom '" + name + "' (" + str(len(rows)) + ")"
    else:
        row = cur.execute(
            "SELECT id FROM products WHERE name = ? AND presentation = ? AND is_demo = 0",
            (name, presentation),
        ).fetchone()
        if row:
            return row[0], None
        return None, "Produit introuvable (nom + presentation) : " + name + " / " + presentation


def main():
    ap = argparse.ArgumentParser(description="Rangement des photos Medora par numero.")
    ap.add_argument("--commit", action="store_true", help="Execute reellement (sinon dry-run).")
    args = ap.parse_args()

    print("=" * 40)
    print("MEDORA IMAGE ORGANIZER")
    print("=" * 40)
    print()
    print("Dossier source    :", SRC_DIR)
    print("Dossier cible     :", DST_DIR)
    print("Photos attendues  :", EXPECTED_COUNT)
    print("Mode              :", "COMMIT" if args.commit else "DRY-RUN")
    print()

    result = scan_photos()
    if isinstance(result, dict):
        photos, duplicates = result, []
    else:
        photos, duplicates = result

    print("Photos trouvees   :", len(photos))
    if duplicates:
        print()
        print("[ERREUR] Doublons de numero :")
        for num, n1, n2 in duplicates:
            print("   numero " + str(num) + " : " + n1 + "  /  " + n2)
    print()

    # --- Verifications bloquantes ---
    errors = []
    if duplicates:
        errors.append("Doublons de numero detectes.")
    if len(photos) != EXPECTED_COUNT:
        errors.append(
            "Nombre de photos incorrect : " + str(len(photos)) +
            " (attendu " + str(EXPECTED_COUNT) + ")"
        )
    missing = [n for n in range(1, EXPECTED_COUNT + 1) if n not in photos]
    if missing:
        errors.append("Numeros manquants : " + ", ".join(str(n).zfill(3) for n in missing))

    if errors and args.commit:
        print("[ERREUR] Impossible de committer :")
        for e in errors:
            print("   -", e)
        print()
        print("COMMIT ANNULE.")
        sys.exit(1)

    # --- Connexion DB ---
    if not DB_PATH.exists():
        print("[ERREUR] Base introuvable :", DB_PATH)
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # --- Construire les associations ---
    associations = []
    db_errors = []
    for idx, (name, presentation) in enumerate(MASTER, start=1):
        entry = {
            "num": idx,
            "name": name,
            "presentation": presentation,
            "photo": photos.get(idx),
            "product_id": None,
            "error": None,
        }
        pid, err = find_product_id(conn, name, presentation)
        entry["product_id"] = pid
        entry["error"] = err
        associations.append(entry)
        if err:
            db_errors.append("[" + str(idx).zfill(3) + "] " + err)

    # --- Affichage des associations ---
    print("Associations :")
    for a in associations:
        num = str(a["num"]).zfill(3)
        photo_name = a["photo"].name if a["photo"] else "(manquant)"
        line = num + "  " + photo_name.ljust(15) + " -> " + a["name"]
        if a["presentation"]:
            line += "  [" + a["presentation"] + "]"
        if a["error"]:
            line += "  [ERREUR: " + a["error"] + "]"
        print(line)
    print()

    if db_errors:
        print("[ERREUR] Problemes de base :")
        for e in db_errors:
            print("   -", e)
        if args.commit:
            print()
            print("COMMIT ANNULE.")
            conn.close()
            sys.exit(1)

    # --- Si dry-run, on s'arrete ici ---
    if not args.commit:
        print("=" * 40)
        print("DRY-RUN - aucune modification effectuee.")
        print("Pour appliquer : python organize_medora_images.py --commit")
        print("=" * 40)
        conn.close()
        return

    # --- Commit : on copie les fichiers et on met a jour en transaction ---
    DST_DIR.mkdir(parents=True, exist_ok=True)
    installed = 0
    updated = 0
    errors_runtime = []

    try:
        conn.execute("BEGIN")
        for a in associations:
            if a["photo"] is None or a["product_id"] is None:
                raise RuntimeError("Entree incomplete pour le numero " + str(a["num"]))

            # Nom cible : 001_laino-savon-de-marseille.jpg
            ext = a["photo"].suffix.lower()
            slug = slugify(a["name"])
            if a["presentation"]:
                slug += "-" + slugify(a["presentation"])
            target_name = str(a["num"]).zfill(3) + "_" + slug + ext
            target_path = DST_DIR / target_name

            # Copie (remplace si existe deja)
            shutil.copy2(a["photo"], target_path)
            installed += 1

            # URL relative servie par FastAPI
            url = "/static/images/products/medora/" + target_name
            cur = conn.execute(
                "UPDATE products SET image_url = ? WHERE id = ? AND is_demo = 0",
                (url, a["product_id"]),
            )
            if cur.rowcount == 1:
                updated += 1
            else:
                raise RuntimeError(
                    "Mise a jour impossible pour product_id=" + str(a["product_id"])
                )
        conn.commit()
    except Exception as e:
        conn.rollback()
        errors_runtime.append(str(e))
        print("[ERREUR]", e)
        print("ROLLBACK EFFECTUE - aucune modification conservee.")
        conn.close()
        sys.exit(1)

    print("=" * 40)
    print("Photos installees :", installed)
    print("Produits mis a jour :", updated)
    print("Erreurs :", len(errors_runtime))
    print("=" * 40)
    print()
    print("Astuce : Ctrl+Shift+R dans le navigateur pour voir les images.")

    conn.close()


if __name__ == "__main__":
    main()