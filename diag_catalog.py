# -*- coding: utf-8 -*-
# diag_catalog.py - Diagnostic complet du catalogue
import os, re

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
STATIC = os.path.join(ROOT, "static")
INDEX = os.path.join(STATIC, "index.html")

print("=" * 78)
print("DIAGNOSTIC CATALOGUE")
print("=" * 78)

# ============================================================
# 1. Etat actuel de view-catalog dans index.html
# ============================================================
idx = open(INDEX, "r", encoding="utf-8").read()

print("\n[1] view-catalog actuel")
m = re.search(r'<section id="view-catalog"[\s\S]*?</section>', idx)
if m:
    for line in m.group(0).split("\n"):
        print(f"  {line}")
    print(f"\n  -> Classes detectees :")
    print(f"     pt-cat-toolbar   : {'OUI' if 'pt-cat-toolbar' in m.group(0) else 'NON'}")
    print(f"     pt-product-grid  : {'OUI' if 'pt-product-grid' in m.group(0) else 'NON'}")
    print(f"     pt-cat-chips     : {'OUI' if 'pt-cat-chips' in m.group(0) else 'NON'}")

# ============================================================
# 2. CSS patient_common.css
# ============================================================
print("\n[2] patient_common.css")
PC = os.path.join(STATIC, "patient_common.css")
if os.path.exists(PC):
    css = open(PC, "r", encoding="utf-8").read()
    print(f"  Taille : {len(css)} octets")
    print(f"  .pt-product-grid    : {'OUI' if '.pt-product-grid' in css else 'NON'}")
    print(f"  .pt-product-card    : {'OUI' if '.pt-product-card' in css else 'NON'}")
    print(f"  .pt-cat-toolbar     : {'OUI' if '.pt-cat-toolbar' in css else 'NON'}")
    print(f"  .pt-cat-chip        : {'OUI' if '.pt-cat-chip' in css else 'NON'}")
else:
    print("  [!!] ABSENT")

# CSS lie dans index.html ?
print(f"  Lie dans index.html : {'OUI' if 'patient_common.css' in idx else 'NON'}")

# ============================================================
# 3. app.js : classes utilisees
# ============================================================
print("\n[3] app.js classes utilisees")
app = open(os.path.join(STATIC, "app.js"), "r", encoding="utf-8").read()

# Chercher les classes dans les el() et createElement
classes_found = set()
for m in re.finditer(r'el\("[^"]+",\s*"([^"]+)"', app):
    classes_found.add(m.group(1))
for m in re.finditer(r'className\s*=\s*"([^"]+)"', app):
    classes_found.add(m.group(1))

# Filtrer celles interessantes
interesting = [c for c in sorted(classes_found) if any(
    k in c for k in ["product", "pt-", "catalog", "chip", "grid"]
)]
print(f"  Classes produit/catalogue :")
for c in interesting:
    print(f"    - {c}")

# Verifier si pt-product-card est utilise
print(f"\n  pt-product-card dans app.js : {'OUI' if 'pt-product-card' in app else 'NON'}")
print(f"  product-card dans app.js    : {'OUI' if 'product-card' in app else 'NON'}")
print(f"  pt-product-grid dans app.js : {'OUI' if 'pt-product-grid' in app else 'NON'}")

# ============================================================
# 4. Versions cache-bust
# ============================================================
print("\n[4] Versions dans index.html")
for m in re.finditer(r'<script[^>]*src=["\']([^"\']+)["\']', idx):
    print(f"  {m.group(1)}")
for m in re.finditer(r'<link[^>]*href=["\']([^"\']*\.css[^"\']*)["\']', idx):
    print(f"  CSS : {m.group(1)}")

# ============================================================
# 5. showView / goCatalog
# ============================================================
print("\n[5] Fonction goCatalog / showView dans app.js")
for i, line in enumerate(app.split("\n"), 1):
    if "function goCatalog" in line or "function showView" in line or "view-catalog" in line:
        print(f"  {i}: {line.strip()[:120]}")

print("\n" + "=" * 78)
print("Colle-moi tout ce rapport")
print("=" * 78)