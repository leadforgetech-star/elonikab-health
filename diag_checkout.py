# -*- coding: utf-8 -*-
"""Diagnostic checkout : ou injecter le badge vehicule ?"""
import os, re

STATIC = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie\static"
HTML = os.path.join(STATIC, "checkout.html")
JS = os.path.join(STATIC, "checkout.js")

print("=" * 78)
print("STRUCTURE checkout.html")
print("=" * 78)

html = open(HTML, "r", encoding="utf-8").read()
lines = html.split("\n")

# Chercher les sections "recap", "summary", "total", "livraison"
patterns = ["recap", "summary", "total", "fee", "livraison", "co-row", "row"]
print(f"\nOccurrences dans checkout.html ({len(lines)} lignes) :")
for p in patterns:
    matches = [(i+1, l) for i, l in enumerate(lines) if p.lower() in l.lower()]
    if matches:
        print(f"\n  [{p}] {len(matches)} occurrence(s) :")
        for ln, line in matches[:8]:
            print(f"    L{ln}: {line.strip()[:120]}")

# Afficher la structure complete du formulaire (body / main)
print("\n" + "=" * 78)
print("STRUCTURE COMPLETE (body) - 200 lignes max")
print("=" * 78)
body_start = html.find("<body")
if body_start > 0:
    body_content = html[body_start:]
    for i, line in enumerate(body_content.split("\n")[:200], 1):
        if line.strip():
            print(f"  {i:3d}| {line[:120]}")

print("\n\n" + "=" * 78)
print("FONCTION render() ou updateSummary() dans checkout.js")
print("=" * 78)

js = open(JS, "r", encoding="utf-8").read()

# Chercher les fonctions qui affichent le recapitulatif
for fn_name in ["renderSummary", "updateSummary", "renderRecap", "renderTotal", "render()"]:
    m = re.search(r"function\s+" + re.escape(fn_name.replace("()", "")) + r"\s*\(", js)
    if m:
        # Extraire 40 lignes
        start = m.start()
        chunk = js[start:start+2500]
        ln = js[:start].count("\n") + 1
        print(f"\n--- {fn_name} (L{ln}) ---")
        for i, line in enumerate(chunk.split("\n")[:50], ln):
            if line.strip():
                print(f"  {i:3d}| {line[:120]}")
        break

# Chercher les selecteurs utilises dans le JS (getElementById)
print("\n" + "=" * 78)
print("IDs utilises dans checkout.js (getElementById)")
print("=" * 78)
ids = re.findall(r'getElementById\(["\']([^"\']+)["\']\)', js)
print(f"  IDs trouves : {sorted(set(ids))}")

# Chercher les querySelector
sels = re.findall(r'querySelector(?:All)?\(["\']([^"\']+)["\']\)', js)
print(f"  Selecteurs CSS : {sorted(set(sels))}")

# Chercher ou le fee est affiche
print("\n" + "=" * 78)
print("Où le fee livraison est AFFICHE (innerHTML / textContent)")
print("=" * 78)
for m in re.finditer(r'(\.innerHTML|\.textContent)\s*=\s*[^;]{0,200}', js):
    ctx = js[max(0,m.start()-300):m.end()]
    if any(k in ctx.lower() for k in ["fee", "livraison", "total", "somme"]):
        ln = js[:m.start()].count("\n") + 1
        line = js[ln-1].strip()
        print(f"  L{ln}: {line[:120]}")