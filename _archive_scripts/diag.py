import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
conn = sqlite3.connect(BASE / "database.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=== Test direct de la requete SQL (meme logique que le backend) ===")
for test_q in ["do", "d", "dol", "amo", "x"]:
    like = "%%" + test_q + "%%"
    rows = cur.execute(
        "SELECT name FROM products"
        " WHERE name LIKE ? OR description LIKE ? OR presentation LIKE ?"
        " ORDER BY name COLLATE NOCASE",
        (like, like, like),
    ).fetchall()
    noms = [r["name"] for r in rows]
    print("  q = %-6s -> %d resultat(s) : %s" % (repr(test_q), len(noms), noms))

print()
print("=== Contenu complet de la table products ===")
for r in cur.execute("SELECT id, name, price FROM products ORDER BY id"):
    print("  id=%-3d price=%-8s %s" % (r["id"], r["price"], r["name"]))

conn.close()