"""
import_medora.py - Import du catalogue Medora dans la base SQLite.

Usage :
    python import_medora.py             # dry-run (aucune ecriture)
    python import_medora.py --commit    # import reel

Regles :
  - Lit data/medora_products.json
  - N'ecrase jamais un produit existant (name + presentation identiques)
  - Ne touche jamais aux produits is_demo = 1 (DEMO)
  - Ne touche jamais aux commandes
  - Insertion idempotente : les produits deja presents sont ignores
"""
import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "database.db"
JSON_PATH = BASE / "data" / "medora_products.json"

REQUIRED_FIELDS = ["name", "price", "category"]


def load_products():
    if not JSON_PATH.exists():
        raise SystemExit("[ERREUR] Fichier introuvable : " + str(JSON_PATH))
    raw = JSON_PATH.read_text(encoding="utf-8")
    try:
        products = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SystemExit("[ERREUR] JSON invalide : " + str(e))
    if not isinstance(products, list):
        raise SystemExit("[ERREUR] Le JSON doit etre un tableau.")
    for i, p in enumerate(products):
        for f in REQUIRED_FIELDS:
            if f not in p:
                raise SystemExit("[ERREUR] Produit #" + str(i) + " : champ manquant '" + f + "'")
    return products


def find_existing(conn, name, presentation):
    row = conn.execute(
        "SELECT id, is_demo FROM products WHERE name = ? AND presentation = ? LIMIT 1",
        (name, presentation),
    ).fetchone()
    return row


def main():
    ap = argparse.ArgumentParser(description="Import des produits Medora.")
    ap.add_argument("--commit", action="store_true",
                    help="Execute l'import reel (sinon dry-run).")
    args = ap.parse_args()

    if not DB_PATH.exists():
        raise SystemExit("[ERREUR] Base introuvable : " + str(DB_PATH))

    products = load_products()
    print("[INFO] " + str(len(products)) + " produits lus depuis " + JSON_PATH.name)
    print("[INFO] Base : " + str(DB_PATH))
    print("[INFO] Mode : " + ("COMMIT (ecriture reelle)" if args.commit else "DRY-RUN (aucune ecriture)"))
    print()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    total_before = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    demo_before = cur.execute("SELECT COUNT(*) FROM products WHERE is_demo = 1").fetchone()[0]
    real_before = cur.execute("SELECT COUNT(*) FROM products WHERE is_demo = 0").fetchone()[0]
    print("[INFO] Avant import : " + str(total_before) + " produits (" +
          str(demo_before) + " DEMO + " + str(real_before) + " reels)")
    print()

    created_at = datetime.now().isoformat(timespec="seconds")
    inserted = 0
    skipped = 0
    conflicts = 0

    for p in products:
        name = str(p["name"]).strip()
        presentation = str(p.get("presentation", "") or "").strip()
        existing = find_existing(conn, name, presentation)

        if existing:
            if existing["is_demo"] == 1:
                conflicts += 1
                print("  [CONFLIT] '" + name + "' existe deja en DEMO (id=" + str(existing["id"]) + ") - ignore")
            else:
                skipped += 1
                print("  [SKIP]    '" + name + "' deja present (id=" + str(existing["id"]) + ")")
            continue

        if args.commit:
            cur.execute(
                "INSERT INTO products (name, presentation, price, availability,"
                " description, category, requires_prescription, image_url, is_demo, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    name,
                    presentation,
                    float(p["price"]),
                    str(p.get("availability", "disponible")),
                    str(p.get("description", "")),
                    str(p["category"]),
                    int(p.get("requires_prescription", 0)),
                    str(p.get("image_url", "")),
                    int(p.get("is_demo", 0)),
                    created_at,
                ),
            )
            print("  [OK]      '" + name + "' insere (id=" + str(cur.lastrowid) + ")")
        else:
            print("  [DRY]     '" + name + "' serait insere")

        inserted += 1

    if args.commit:
        conn.commit()

    total_after = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    demo_after = cur.execute("SELECT COUNT(*) FROM products WHERE is_demo = 1").fetchone()[0]
    real_after = cur.execute("SELECT COUNT(*) FROM products WHERE is_demo = 0").fetchone()[0]
    conn.close()

    print()
    print("=" * 55)
    print("  Resume :")
    print("    Inseres  : " + str(inserted))
    print("    Ignores  : " + str(skipped))
    print("    Conflits : " + str(conflicts))
    print()
    print("  Avant : " + str(total_before) + " produits (" + str(demo_before) + " DEMO + " + str(real_before) + " reels)")
    print("  Apres : " + str(total_after) + " produits (" + str(demo_after) + " DEMO + " + str(real_after) + " reels)")
    print("=" * 55)

    if not args.commit:
        print()
        print("[INFO] Mode DRY-RUN - aucune donnee n'a ete ecrite.")
        print("       Pour executer l'import reel : python import_medora.py --commit")


if __name__ == "__main__":
    main()
