# -*- coding: utf-8 -*-
"""Dump la fonction update_order_status pour voir si le hook est bien la."""
import os, re, sqlite3

MAIN = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie\main.py"
DB = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie\database.db"

src = open(MAIN, "r", encoding="utf-8").read()

# Trouver la fonction update_order_status
idx = src.find("def update_order_status(")
if idx < 0:
    print("[!!] update_order_status introuvable")
    exit(1)

# Trouver la fin (prochaine def apres)
end = src.find("\ndef ", idx + 10)
if end < 0:
    end = idx + 4000

fn = src[idx:end]
line_start = src[:idx].count("\n") + 1

print("=" * 78)
print(f"FONCTION update_order_status (a partir de L{line_start})")
print("=" * 78)

# Afficher avec numeros de ligne
for i, line in enumerate(fn.split("\n"), line_start):
    print(f"{i:4d}| {line}")

print()
print("=" * 78)
print("CHECKS")
print("=" * 78)
print(f"  [_apply_order_stock]      : {'OUI' if '_apply_order_stock' in fn else 'NON'}")
print(f"  [if new_status == confirmee] : {'OUI' if 'new_status == \"confirmee\"' in fn else 'NON'}")
print(f"  [if new_status == refusee]   : {'OUI' if 'new_status == \"refusee\"' in fn else 'NON'}")
print(f"  [current_status definit]  : {'OUI' if 'current_status = row' in fn else 'NON'}")

# Verifier la commande CMD-261016-DF3AD9
print()
print("=" * 78)
print("COMMANDE CMD-261016-DF3AD9")
print("=" * 78)
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
o = cur.execute("SELECT * FROM orders WHERE reference = ?", ("CMD-261016-DF3AD9",)).fetchone()
if o:
    print(f"  id={o['id']}, status={o['status']}, product_id={o['product_id']}, qty={o['quantity']}")
    items = cur.execute("SELECT product_id, quantity FROM order_items WHERE order_id = ?", (o["id"],)).fetchall()
    print(f"  order_items : {len(items)} item(s)")
    for it in items:
        print(f"    - product_id={it['product_id']} qty={it['quantity']}")
else:
    print("  [!!] Commande introuvable")
conn.close()