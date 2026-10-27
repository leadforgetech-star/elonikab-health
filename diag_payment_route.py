# -*- coding: utf-8 -*-
# diag_payment_route.py - Verifie la route /payment.html dans main.py
import os, re

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
MAIN = os.path.join(ROOT, "main.py")

src = open(MAIN, "r", encoding="utf-8").read()

print("=" * 70)
print("[1] Routes HTML dans main.py")
print("=" * 70)
for m in re.finditer(r'@app\.(?:api_route|get)\("([^"]+)"[^)]*\)[\s\S]{0,200}?def\s+(\w+)', src):
    path = m.group(1)
    fn = m.group(2)
    if not path.startswith("/api/"):
        print(f"  {path:<45} -> {fn}()")

print("\n[2] Recherche 'payment' dans main.py :")
for i, line in enumerate(src.split("\n"), 1):
    if "payment" in line.lower():
        print(f"  {i}: {line.strip()[:100]}")

print("\n[3] Recherche 'FileResponse' dans main.py :")
for i, line in enumerate(src.split("\n"), 1):
    if "FileResponse" in line:
        print(f"  {i}: {line.strip()[:100]}")