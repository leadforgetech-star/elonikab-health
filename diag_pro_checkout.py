# -*- coding: utf-8 -*-
"""Diagnostic checkout PRO : computeEstimate + render + endpoint b2b."""
import os, re

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
STATIC = os.path.join(ROOT, "static")
V3 = os.path.join(ROOT, "v3_modules")

JS = os.path.join(STATIC, "professional_demande_confirmer.js")
B2B = os.path.join(V3, "b2b_requests.py")

print("=" * 78)
print("1. computeEstimate() dans professional_demande_confirmer.js")
print("=" * 78)

js = open(JS, "r", encoding="utf-8").read()

# Trouver computeEstimate
m = re.search(r"function computeEstimate\(\)[\s\S]*?(?=\nfunction |\n// )", js)
if m:
    ln = js[:m.start()].count("\n") + 1
    print(f"\n--- computeEstimate (L{ln}) ---")
    for i, line in enumerate(m.group(0).split("\n"), ln):
        print(f"  {i:3d}| {line}")

# Trouver render()
print("\n" + "=" * 78)
print("2. render() - zone d'affichage du recapitulatif")
print("=" * 78)

m = re.search(r"function render\(\)[\s\S]*?(?=\nfunction |\n// )", js)
if m:
    ln = js[:m.start()].count("\n") + 1
    print(f"\n--- render (L{ln}) ---")
    # Afficher les 100 premieres lignes
    for i, line in enumerate(m.group(0).split("\n")[:120], ln):
        if line.strip():
            print(f"  {i:3d}| {line}")

# Zone spécifique : où delivery_fee est affiché
print("\n" + "=" * 78)
print("3. Zone : où fee et total sont affichés")
print("=" * 78)
for m in re.finditer(r'delivery_fee|Frais de livraison', js):
    start = max(0, m.start() - 200)
    end = min(len(js), m.start() + 400)
    ln = js[:start].count("\n") + 1
    print(f"\n--- Contexte L{ln} ---")
    for i, line in enumerate(js[start:end].split("\n"), ln):
        if line.strip():
            print(f"  {i:3d}| {line}")
    print()

# Endpoint backend
print("=" * 78)
print("4. Endpoint /api/pro/requests/{ref}/estimate-delivery (b2b_requests.py)")
print("=" * 78)

if os.path.isfile(B2B):
    b2b = open(B2B, "r", encoding="utf-8").read()
    m = re.search(r"@app\.(post|get)\([\"'][^\"']*estimate-delivery[\"'][\s\S]*?(?=\n@app\.|\nclass |\Z)", b2b)
    if m:
        ln = b2b[:m.start()].count("\n") + 1
        print(f"\n--- Endpoint (L{ln}) ---")
        for i, line in enumerate(m.group(0).split("\n")[:80], ln):
            print(f"  {i:3d}| {line}")
    else:
        print("  [!!] Endpoint estimate-delivery introuvable")

    # Cherche compute_delivery_fee ou compute_delivery_fee_v2
    print("\nRecherche compute_delivery_fee dans b2b_requests.py :")
    for m in re.finditer(r"compute_delivery_fee\w*", b2b):
        ln = b2b[:m.start()].count("\n") + 1
        line = b2b.split("\n")[ln - 1].strip()[:120]
        print(f"  L{ln}: {line}")
else:
    print("  [!!] b2b_requests.py introuvable")