# -*- coding: utf-8 -*-
"""Dump cart.py pour trouver le bon point d'insertion."""
import os, re

CART = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie\v3_modules\cart.py"
src = open(CART, "r", encoding="utf-8").read()

print("=" * 78)
print(f"FICHIER cart.py ({len(src)} caracteres)")
print("=" * 78)

# Trouver toutes les fonctions @app.post("/api/cart/items")
matches = list(re.finditer(r'@app\.(post|patch|put|delete)\s*\(\s*["\']([^"\']+)["\']', src))
print(f"\n{len(matches)} endpoint(s) trouve(s) :\n")
for m in matches:
    line_no = src[:m.start()].count("\n") + 1
    print(f"  L{line_no}: {m.group(1).upper()} {m.group(2)}")

# Afficher la fonction POST /api/cart/items avec 40 lignes de contexte
print("\n" + "=" * 78)
print("DETAIL : fonction qui ajoute un item au panier")
print("=" * 78)

idx = src.find('@app.post("/api/cart/items")')
if idx < 0:
    idx = src.find('@app.post("/api/cart/items')
if idx < 0:
    # Chercher une fonction qui contient "cart_items"
    idx = src.find("cart_items")

if idx >= 0:
    # Trouver le debut de la ligne
    line_start = src.rfind("\n", 0, idx) + 1
    line_no = src[:line_start].count("\n") + 1
    # Afficher 60 lignes
    lines = src[line_start:].split("\n")[:60]
    for i, line in enumerate(lines, line_no):
        print(f"{i:4d}| {line}")
else:
    print("[!!] Fonction introuvable")

print("\n" + "=" * 78)
print("RECHERCHE : toutes les occurrences de 'product = conn.execute'")
print("=" * 78)
for m in re.finditer(r'product\s*=\s*conn\.execute\([\s\S]{0,250}', src):
    line_no = src[:m.start()].count("\n") + 1
    txt = m.group(0).replace("\n", " ")[:180]
    print(f"  L{line_no}: {txt}")