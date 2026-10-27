# -*- coding: utf-8 -*-
# inspect_pro_loaders.py - Dump fonctions de chargement des JS pro
import os, re

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
STATIC = os.path.join(ROOT, "static")

FILES = [
    "professional_dashboard.js",
    "professional_catalogue.js",
    "professional_demande.js",
]

for name in FILES:
    p = os.path.join(STATIC, name)
    if not os.path.exists(p):
        continue
    src = open(p, "r", encoding="utf-8").read()
    lines = src.split("\n")

    print("=" * 78)
    print(f"FICHIER : {name}  ({len(src)} octets, {len(lines)} lignes)")
    print("=" * 78)

    # 1. Fonctions de chargement
    print("\n[Fonctions 'load*', 'fetch*', 'refresh*', 'render*']")
    for i, l in enumerate(lines, 1):
        m = re.match(r'^\s*(?:async\s+)?(?:function\s+)?(\w+)\s*(?:\(|=)', l)
        if m:
            fn = m.group(1)
            if re.match(r'^(load|fetch|refresh|render|init|reload)', fn, re.I):
                print(f"  {i:4}  {l.strip()[:100]}")

    # 2. Endpoints API utilises
    print("\n[Endpoints API utilises]")
    seen = set()
    for i, l in enumerate(lines, 1):
        for m in re.finditer(r'["\'](/api/[^"\']+)["\']', l):
            ep = m.group(1)
            if ep not in seen:
                seen.add(ep)
                print(f"  {i:4}  {ep}")

    # 3. Event listeners existants
    print("\n[addEventListener existants]")
    for i, l in enumerate(lines, 1):
        if "addEventListener" in l:
            print(f"  {i:4}  {l.strip()[:120]}")

    # 4. Event listeners custom
    print("\n[CustomEvent / dispatchEvent]")
    for i, l in enumerate(lines, 1):
        if "CustomEvent" in l or "dispatchEvent" in l:
            print(f"  {i:4}  {l.strip()[:120]}")

    print("\n")

# ============================================================
# Inspect professional_commandes.html (JS inline ?)
# ============================================================
print("=" * 78)
print("professional_commandes.html - JS inline ?")
print("=" * 78)
p = os.path.join(STATIC, "professional_commandes.html")
if os.path.exists(p):
    html = open(p, "r", encoding="utf-8").read()
    # Chercher scripts inline
    inline = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', html, re.DOTALL)
    print(f"  {len(inline)} script(s) inline")
    for s in inline:
        print("  ---")
        for line in s.strip().split("\n")[:40]:
            print(f"    {line}")
    # Scripts externes
    print("\n  Scripts externes :")
    for m in re.finditer(r'<script[^>]*src=["\']([^"\']+)["\']', html):
        print(f"    {m.group(1)}")