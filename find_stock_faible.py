# -*- coding: utf-8 -*-
"""Trouve toutes les occurrences de 'Stock faible' dans app.js."""
import os

APP = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie\static\app.js"
src = open(APP, "r", encoding="utf-8").read()

print("=" * 78)
print("OCCURRENCES DE 'Stock faible' / 'stock faible' dans app.js")
print("=" * 78)

lines = src.split("\n")
count = 0
for i, line in enumerate(lines, 1):
    if "stock faible" in line.lower():
        count += 1
        print(f"  L{i}: {line}")

print(f"\n  Total : {count} occurrence(s)")

# Afficher le contexte (30 lignes avant/apres la 1ere)
if count > 0:
    first = next(i for i, l in enumerate(lines) if "stock faible" in l.lower())
    print(f"\n{'=' * 78}")
    print(f"CONTEXTE autour de la 1ere occurrence (L{first + 1})")
    print("=" * 78)
    start = max(0, first - 15)
    end = min(len(lines), first + 25)
    for i in range(start, end):
        marker = ">>>" if i == first else "   "
        print(f"{marker} {i+1:4d}| {lines[i]}")