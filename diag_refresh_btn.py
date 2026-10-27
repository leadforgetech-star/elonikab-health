# -*- coding: utf-8 -*-
import os, re
ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
P = os.path.join(ROOT, "static", "pharmacien.js")
src = open(P, "r", encoding="utf-8").read()

print("=" * 78)
print("Fonction refresh() + init()")
print("=" * 78)

lines = src.split("\n")
for name in ["function refresh", "function init", "refresh-btn"]:
    print(f"\n### Recherche de '{name}' ###")
    for i, line in enumerate(lines, 1):
        if name in line:
            start = max(0, i - 3)
            end = min(len(lines), i + 15)
            for j in range(start, end):
                marker = ">>>" if j == i - 1 else "   "
                print(f"{marker} {j+1:4}  {lines[j]}")
            print()
            break