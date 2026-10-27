# -*- coding: utf-8 -*-
# inspect_cart_status.py
# Dump cart.py complet + zone PATCH /status (pour patcher proprement)
import os

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
CART = os.path.join(ROOT, "v3_modules", "cart.py")
MAIN = os.path.join(ROOT, "main.py")

# ============================================================
# 1. cart.py complet
# ============================================================
print("=" * 78)
print("FICHIER : v3_modules/cart.py")
print("=" * 78)
src = open(CART, "r", encoding="utf-8").read()
for i, l in enumerate(src.split("\n"), 1):
    print(f"{i:4}  {l.rstrip()}")

# ============================================================
# 2. main.py — zone PATCH /status
# ============================================================
print("\n" + "=" * 78)
print("FICHIER : main.py — zone PATCH /status (lignes 513-555)")
print("=" * 78)
main = open(MAIN, "r", encoding="utf-8").read()
lines = main.split("\n")
for i in range(512, min(len(lines), 555)):
    print(f"{i+1:4}  {lines[i].rstrip()}")

print("\n" + "=" * 78)
print("FIN — colle tout ca")
print("=" * 78)