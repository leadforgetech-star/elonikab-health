"""
remove_ubi_prefix.py
Retire le prefixe "UBI " du nom des produits en base.
Dry-run par defaut, --commit pour appliquer.
Ne touche pas aux produits DEMO.
Ne touche pas a image_url.
"""
import argparse
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "database.db"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT id, name FROM products"
        " WHERE is_demo = 0 AND name LIKE 'UBI %'"
        " ORDER BY id"
    ).fetchall()

    print("=" * 60)
    print("RETRAIT DU PREFIXE UBI")
    print("=" * 60)
    print("Mode :", "COMMIT" if args.commit else "DRY-RUN")
    print(str(len(rows)) + " produits a renommer.")
    print()

    updates = []
    for r in rows:
        old = r["name"]
        new = old[4:].strip()  # enleve "UBI "
        updates.append((r["id"], old, new))
        print("  [" + str(r["id"]).rjust(3) + "] " + old + "  ->  " + new)

    print()

    if not args.commit:
        print("DRY-RUN : aucune modification.")
        print("Pour appliquer : python remove_ubi_prefix.py --commit")
        conn.close()
        return

    try:
        conn.execute("BEGIN")
        for pid, old, new in updates:
            conn.execute(
                "UPDATE products SET name = ? WHERE id = ? AND is_demo = 0",
                (new, pid),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("[ERREUR]", e)
        print("ROLLBACK - aucune modification conservee.")
        conn.close()
        return

    conn.close()
    print("=" * 60)
    print("  " + str(len(updates)) + " produits renommes.")
    print("=" * 60)
    print()
    print("Les URLs d'images existantes sont inchangees.")
    print("Ctrl+Shift+R dans le navigateur.")


if __name__ == "__main__":
    main()