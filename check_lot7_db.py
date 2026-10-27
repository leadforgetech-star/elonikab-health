# -*- coding: utf-8 -*-
"""Verifie les 3 nouvelles tables du Lot 7."""
import sqlite3, os

DB = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie\database.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 70)
print("VERIFICATION LOT 7 - ETAPE B")
print("=" * 70)

for tbl in ["stock_movements", "stock_lots", "product_images"]:
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({tbl})").fetchall()]
    n = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    print(f"\n[{tbl}]  {n} ligne(s)")
    print(f"  Colonnes : {', '.join(cols)}")

# Combien de produits ont une image primaire ?
n_prod = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
n_img = cur.execute("SELECT COUNT(DISTINCT product_id) FROM product_images WHERE is_primary = 1").fetchone()[0]
print(f"\n[Images]  {n_img}/{n_prod} produits avec image primaire migree")

conn.close()
print()
print("=" * 70)