# -*- coding: utf-8 -*-
"""Trouve L658 et diagnostique l'erreur."""
import os

MAIN = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie\main.py"

src = open(MAIN, "r", encoding="utf-8").read()
lines = src.split("\n")

print("=" * 78)
print("LIGNES 650-680 de main.py")
print("=" * 78)
for i in range(649, min(680, len(lines))):
    marker = ">>>" if i == 657 else "   "
    print(marker + " " + str(i+1) + "| " + lines[i])

print()
print("=" * 78)
print("RECHERCHE de TOUS les patterns 'transition refusee'")
print("=" * 78)
for i, line in enumerate(lines, 1):
    if "transition refusee" in line or "delivery_mode" in line and "livraison" in line:
        print(f"  L{i}: {line}")

print()
print("=" * 78)
print("RECHERCHE de 'current_status = row'")
print("=" * 78)
for i, line in enumerate(lines, 1):
    if "current_status" in line:
        print(f"  L{i}: {line.strip()}")