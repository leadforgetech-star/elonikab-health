"""
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
