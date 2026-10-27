from pathlib import Path
import json
import math

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
DATA.mkdir(parents=True, exist_ok=True)

# Prix source + arrondi au multiple de 25 par exces
def ceil_25(v):
    return int(math.ceil(v / 25.0) * 25)

SOURCES = [
    {
        "name": "HEMOFER Sirop",
        "presentation": "Flacon 200 ml",
        "price_source": 1665,
        "category": "Anti-anémique",
    },
    {
        "name": "HYDROSOL POLYVITAMINÉ Solution buvable",
        "presentation": "Solution buvable 20 ml",
        "price_source": 1205,
        "category": "Vitamines",
    },
    {
        "name": "ALGESAL SURACTIVÉ Crème",
        "presentation": "Tube 40-100 g",
        "price_source": 2445,
        "category": "Anti-inflammatoires",
    },
    {
        "name": "ALGESAL BAUME Crème",
        "presentation": "Tube 40-100 g",
        "price_source": 2065,
        "category": "Anti-inflammatoires",
    },
    {
        "name": "A313 Pommade",
        "presentation": "Tube 50 g",
        "price_source": 3215,
        "category": "Dermatologie",
    },
]

PRODUCTS = []
for s in SOURCES:
    PRODUCTS.append({
        "name": s["name"],
        "presentation": s["presentation"],
        "price": ceil_25(s["price_source"]),
        "price_source": s["price_source"],
        "category": s["category"],
        "requires_prescription": 0,
        "description": "",
        "image_url": "",
        "availability": "disponible",
        "is_demo": 0,
    })

json_path = DATA / "pharma_dev_products.json"
json_path.write_text(json.dumps(PRODUCTS, indent=2, ensure_ascii=False), encoding="utf-8")
print("[OK] " + str(json_path.relative_to(BASE)))
print()
print("Arrondis appliques :")
for p in PRODUCTS:
    print("  %-40s %5d -> %5d" % (p["name"][:40], p["price_source"], p["price"]))

# ============================================================
# Script d'import (identique, relit le JSON)
# ============================================================
IMPORT = '''"""
import_pharma_dev.py - Import des produits Pharma Developpement.
Idempotent, dry-run par defaut.
"""
import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "database.db"
JSON_PATH = BASE / "data" / "pharma_dev_products.json"


def load():
    if not JSON_PATH.exists():
        raise SystemExit("[ERREUR] " + str(JSON_PATH) + " introuvable.")
    return json.loads(JSON_PATH.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    products = load()
    print("[INFO] " + str(len(products)) + " produits lus.")
    print("[INFO] Mode :", "COMMIT" if args.commit else "DRY-RUN")
    print()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    before = cur.execute("SELECT COUNT(*) FROM products WHERE is_demo=0").fetchone()[0]
    print("[INFO] Produits reels avant :", before)
    print()

    created_at = datetime.now().isoformat(timespec="seconds")
    inserted = skipped = 0

    for p in products:
        name = p["name"].strip()
        pres = (p.get("presentation") or "").strip()
        row = cur.execute(
            "SELECT id FROM products WHERE name=? AND presentation=? LIMIT 1",
            (name, pres),
        ).fetchone()
        if row:
            print("  [SKIP]  " + name + "  (deja present, id=" + str(row["id"]) + ")")
            skipped += 1
            continue

        if args.commit:
            cur.execute(
                "INSERT INTO products (name, presentation, price, availability,"
                " description, category, requires_prescription, image_url, is_demo, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (name, pres, float(p["price"]), p.get("availability", "disponible"),
                 p.get("description", ""), p["category"],
                 int(p.get("requires_prescription", 0)), p.get("image_url", ""),
                 int(p.get("is_demo", 0)), created_at),
            )
            print("  [OK]    " + name + "  (id=" + str(cur.lastrowid) + ")")
        else:
            print("  [DRY]   " + name + "  (" + str(int(p["price"])) + " FCFA, " + p["category"] + ")")
        inserted += 1

    if args.commit:
        conn.commit()

    after = cur.execute("SELECT COUNT(*) FROM products WHERE is_demo=0").fetchone()[0]
    conn.close()

    print()
    print("=" * 50)
    print("  Inseres : " + str(inserted))
    print("  Ignores : " + str(skipped))
    print("  Avant   : " + str(before) + " produits reels")
    print("  Apres   : " + str(after) + " produits reels")
    print("=" * 50)
    if not args.commit:
        print()
        print("Pour appliquer : python import_pharma_dev.py --commit")


if __name__ == "__main__":
    main()
'''

script_path = BASE / "import_pharma_dev.py"
script_path.write_text(IMPORT, encoding="utf-8")
print()
print("[OK] " + str(script_path.relative_to(BASE)))
print()
print("Etape suivante :")
print("   python import_pharma_dev.py             (dry-run)")
print("   python import_pharma_dev.py --commit    (import reel)")