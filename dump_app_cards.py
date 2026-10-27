# -*- coding: utf-8 -*-
"""Dump la zone de rendu des cartes produit dans app.js."""
import os, re

APP = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie\static\app.js"
src = open(APP, "r", encoding="utf-8").read()

print("=" * 78)
print(f"app.js : {len(src)} caracteres, {src.count(chr(10))} lignes")
print("=" * 78)

# Chercher les patterns courants
patterns = [
    "product-card",
    "productCard",
    "renderProduct",
    "renderCatalog",
    "renderProducts",
    "displayProduct",
    "product-actions",
    "data-add-cart",
    "Ajouter au panier",
    "addToCart",
]

print("\nPatterns trouves :")
for p in patterns:
    count = src.count(p)
    if count > 0:
        print(f"  '{p}': {count} occurrence(s)")

# Afficher le contexte de "product-card" ou "product-actions"
targets = ["product-card", "product-actions", "data-add-cart", "Ajouter au panier"]
for target in targets:
    idx = src.find(target)
    if idx < 0:
        continue
    line_no = src[:idx].count("\n") + 1
    print(f"\n{'=' * 78}")
    print(f"CONTEXTE autour de '{target}' (L{line_no})")
    print("=" * 78)
    start = max(0, idx - 1500)
    end = min(len(src), idx + 2500)
    chunk = src[start:end]
    line_start = src[:start].count("\n") + 1
    for i, line in enumerate(chunk.split("\n"), line_start):
        print(f"{i:4d}| {line}")
    break  # Ne montrer que le premier

# Aussi chercher la fonction qui construit les cartes
print("\n" + "=" * 78)
print("FONCTIONS de rendu produit")
print("=" * 78)
for m in re.finditer(r"function\s+(\w*[Pp]roduct\w*|\w*[Cc]atalog\w*)\s*\(", src):
    line_no = src[:m.start()].count("\n") + 1
    print(f"  L{line_no}: {m.group(0)}")

for m in re.finditer(r"function\s+(render\w+|display\w+|load\w+)\s*\(", src):
    line_no = src[:m.start()].count("\n") + 1
    print(f"  L{line_no}: {m.group(0)}")