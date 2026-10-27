# -*- coding: utf-8 -*-
# diag_layout.py - Diagnostic : header patient + grille catalogue PC
import os, re

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
STATIC = os.path.join(ROOT, "static")

# ============================================================
# 1. Regles .pt-product-grid + .pt-container dans patient_common.css
# ============================================================
print("=" * 78)
print("[1] Regles .pt-product-grid / .pt-container / .pt-cat-toolbar")
print("=" * 78)

css = open(os.path.join(STATIC, "patient_common.css"), "r", encoding="utf-8").read()

for sel in [".pt-product-grid", ".pt-container", ".pt-cat-toolbar"]:
    print(f"\n### {sel} ###")
    # Chercher toutes les occurrences
    for m in re.finditer(rf'([^}}{{]*{re.escape(sel)}[^{{}}]*\{{[^}}]*\}})', css):
        block = m.group(1).strip()
        # Afficher avec contexte (media queries)
        start = m.start()
        # Chercher si c'est dans un media query
        before = css[:start]
        last_media = before.rfind("@media")
        context = ""
        if last_media >= 0 and "@media" in before[last_media:]:
            media_line = before[last_media:].split("{")[0]
            # Verifier qu'on est bien encore dans le media (pas ferme)
            after_media = css[last_media:]
            # Simple : on prend la premiere ligne jusqu'a {
            context = media_line.strip() + "  "
        print(f"  {context}{block[:300]}")
        print()

# ============================================================
# 2. Structure HTML de view-catalog
# ============================================================
print("=" * 78)
print("[2] Structure view-catalog dans index.html")
print("=" * 78)

idx = open(os.path.join(STATIC, "index.html"), "r", encoding="utf-8").read()
m = re.search(r'<section id="view-catalog"[\s\S]*?</section>', idx)
if m:
    for line in m.group(0).split("\n")[:15]:
        print(f"  {line}")
    print()

# ============================================================
# 3. Header actuel dans index.html
# ============================================================
print("=" * 78)
print("[3] Header dans index.html")
print("=" * 78)

# Chercher <header> ou pt-mini-header
m = re.search(r'(<header[\s\S]*?</header>)', idx)
if m:
    for line in m.group(0).split("\n")[:20]:
        print(f"  {line}")
else:
    print("  (aucun <header> trouve)")

# Chercher le mini-header
if "pt-mini-header" in idx:
    print("\n  [INFO] pt-mini-header present dans index.html")
    m = re.search(r'<header class="pt-mini-header"[\s\S]*?</header>', idx)
    if m:
        for line in m.group(0).split("\n")[:15]:
            print(f"  {line}")

# ============================================================
# 4. Verifier ordre des CSS dans index.html
# ============================================================
print("=" * 78)
print("[4] Ordre des CSS dans index.html <head>")
print("=" * 78)

for m in re.finditer(r'<link[^>]*href="([^"]+\.css[^"]*)"[^>]*>', idx):
    print(f"  {m.group(1)}")

# ============================================================
# 5. Regles .pt-mini-header + .pt-mini-brand
# ============================================================
print("\n" + "=" * 78)
print("[5] Regles .pt-mini-header / .pt-mini-brand")
print("=" * 78)

css_home = open(os.path.join(STATIC, "patient_home.css"), "r", encoding="utf-8").read()
for sel in [".pt-mini-header", ".pt-mini-brand", ".pt-bell"]:
    print(f"\n### {sel} ###")
    for m in re.finditer(rf'({re.escape(sel)}[^{{}}]*\{{[^}}]*\}})', css_home):
        block = m.group(1).strip()
        print(f"  {block[:250]}")
        print()

# ============================================================
# 6. Verifier .pt-mini-header dans patient_common.css aussi
# ============================================================
print("=" * 78)
print("[6] .pt-mini-header dans patient_common.css ?")
print("=" * 78)

if ".pt-mini-header" in css:
    print("  [INFO] OUI, il y a aussi une regle dans patient_common.css")
    for m in re.finditer(r'(\.pt-mini-header[^{}]*\{[^}]*\})', css):
        print(f"  {m.group(1)[:250]}")
else:
    print("  [INFO] NON, uniquement dans patient_home.css")

print("\n" + "=" * 78)
print("FIN - Colle tout ce rapport")
print("=" * 78)