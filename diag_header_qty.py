# -*- coding: utf-8 -*-
# diag_header_qty.py
# 1) Audit du header pt-mini-header
# 2) Audit structure de la carte produit + qty selector
import os, re

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
STATIC = os.path.join(ROOT, "static")
INDEX = os.path.join(STATIC, "index.html")
CSS_COMMON = os.path.join(STATIC, "patient_common.css")

def sep(t):
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)

# ============================================================
# 1. HEADER - HTML structure
# ============================================================
sep("[1] HEADER - Structure HTML dans index.html")

html = open(INDEX, "r", encoding="utf-8").read()

# Chercher <header class="pt-mini-header">
m = re.search(r'<header[^>]*class="[^"]*pt-mini-header[^"]*"[^>]*>[\s\S]*?</header>', html)
if m:
    print(m.group(0))
else:
    print("  [!!] pt-mini-header introuvable")

# Verifier la position dans le body
body_start = html.find("<body")
header_pos = html.find("pt-mini-header")
print(f"\n  [INFO] Position du header dans index.html : caractere {header_pos}")
print(f"  [INFO] Le body commence a : caractere {body_start}")

# Y a-t-il un wrapper parent ?
if header_pos > 0:
    before = html[:header_pos]
    # Chercher le dernier element ouvert avant le header
    last_open = re.findall(r'<(div|main|section|article)[^>]*>', before)
    print(f"  [INFO] Balises ouvrantes avant le header (10 dernieres) :")
    for tag in last_open[-10:]:
        print(f"    {tag[:100]}")

# ============================================================
# 2. HEADER - CSS regles
# ============================================================
sep("[2] HEADER - Regles CSS")

css = open(CSS_COMMON, "r", encoding="utf-8").read()

# Chercher toutes les regles .pt-mini-header*
print("\n### .pt-mini-header et enfants ###")
for m in re.finditer(
    r'([^\n{}]*\.pt-mini-header[^\n{}]*)\{([^}]*)\}',
    css, re.MULTILINE
):
    sel = m.group(1).strip()
    rules = m.group(2).strip()
    print(f"\n  Selecteur : {sel}")
    for line in rules.split(";"):
        line = line.strip()
        if line:
            print(f"    {line}")

# Chercher aussi les regles .pt-mini-header dans les autres CSS
for fname in ["patient_home.css", "patient_nav.css", "mobile.css", "style.css"]:
    p = os.path.join(STATIC, fname)
    if not os.path.exists(p):
        continue
    c = open(p, "r", encoding="utf-8").read()
    matches = list(re.finditer(
        r'([^\n{}]*\.pt-mini-header[^\n{}]*)\{([^}]*)\}',
        c, re.MULTILINE
    ))
    if matches:
        print(f"\n### Dans {fname} ###")
        for m in matches:
            print(f"  {m.group(1).strip()}")
            print(f"    {m.group(2).strip()[:200]}")

# ============================================================
# 3. Verifier les regles globales sur header
# ============================================================
sep("[3] Regles globales sur 'header'")

for m in re.finditer(
    r'(?:^|\n)\s*(header[^,{}]*)\{([^}]*)\}',
    css, re.MULTILINE
):
    sel = m.group(1).strip()
    rules = m.group(2).strip()
    if "pt-mini" not in sel and "topbar" not in sel:
        print(f"\n  {sel}")
        for line in rules.split(";"):
            line = line.strip()
            if line and any(k in line for k in ["width", "display", "max", "min", "margin", "padding"]):
                print(f"    {line}")

# ============================================================
# 4. CARTE PRODUIT - Structure JS
# ============================================================
sep("[4] CARTE PRODUIT - Structure dans app.js")

js = open(os.path.join(STATIC, "app.js"), "r", encoding="utf-8").read()

# Chercher productCard
m = re.search(r'function productCard\(p\)\s*\{[\s\S]*?\n\}', js)
if m:
    print(m.group(0))
else:
    print("  [!!] function productCard introuvable")

# ============================================================
# 5. QTY SELECTOR - CSS
# ============================================================
sep("[5] QTY SELECTOR - CSS actuel")

for sel in [".pt-qty", ".pt-qty-btn", ".pt-qty-input", ".pt-add-row"]:
    print(f"\n### {sel} ###")
    for m in re.finditer(
        re.escape(sel) + r'\{([^}]*)\}',
        css
    ):
        for line in m.group(1).split(";"):
            line = line.strip()
            if line:
                print(f"  {line}")
        print()

    # Chercher dans les media queries
    for m in re.finditer(
        r'@media[^{]*\{[^@]*' + re.escape(sel) + r'\{([^}]*)\}',
        css
    ):
        print(f"  [media]")
        for line in m.group(1).split(";"):
            line = line.strip()
            if line:
                print(f"    {line}")

print("\n" + "=" * 78)
print("FIN")
print("=" * 78)