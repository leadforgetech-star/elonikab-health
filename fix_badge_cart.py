# -*- coding: utf-8 -*-
"""Fix : le badge panier ne doit pas disparaitre apres une erreur."""
import os, re, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
APP = os.path.join(ROOT, "static", "app.js")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_badgecart_{TS}")
os.makedirs(BAK, exist_ok=True)
shutil.copy2(APP, os.path.join(BAK, "app.js"))

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]"}[k]
    print(p, m)

print("=" * 78)
print(f"FIX BADGE CART - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

src = open(APP, "r", encoding="utf-8").read()

# Diagnostiquer : ou est le badge panier ?
patterns = ["loadCartBadge", "cartBadge", "cart-badge", "pt-cart-badge", "refreshCartBadge"]
print("Patterns trouves dans app.js :")
for p in patterns:
    n = src.count(p)
    if n > 0:
        print(f"  '{p}': {n} occurrence(s)")

# Trouver la fonction addToCartQty et son catch
idx = src.find("function addToCartQty(")
if idx < 0:
    log("addToCartQty introuvable", "ERR")
    sys.exit(1)

# Chercher la fin de la fonction
end = src.find("\nfunction ", idx + 10)
if end < 0:
    end = idx + 3000

fn = src[idx:end]
print(f"\nFonction addToCartQty ({len(fn)} caracteres)")
print("=" * 78)
print(fn[:2000])
print("=" * 78)

# Verifier si loadCartBadge est appele dans le catch
if "loadCartBadge" in fn:
    print("\n[OK] loadCartBadge est appele dans addToCartQty")
else:
    print("\n[!!] loadCartBadge n'est PAS appele dans addToCartQty")
    print("     -> C'est probablement pour ca que le badge disparait")

# Chercher la fonction loadCartBadge
idx_badge = src.find("function loadCartBadge")
if idx_badge < 0:
    idx_badge = src.find("loadCartBadge =")
if idx_badge > 0:
    end_badge = src.find("\nfunction ", idx_badge + 10)
    if end_badge < 0:
        end_badge = idx_badge + 1500
    print(f"\nFonction loadCartBadge ({end_badge - idx_badge} caracteres)")
    print("=" * 78)
    print(src[idx_badge:end_badge][:1500])
    print("=" * 78)