# -*- coding: utf-8 -*-
# diag_bugs_pharm.py - Diagnostic : motif + boucle refresh
import os, re

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
JS = os.path.join(ROOT, "static", "pharmacien.js")

src = open(JS, "r", encoding="utf-8").read()
lines = src.split("\n")

print("=" * 78)
print("[1] Zone ligne 2010-2040 (erreur motif)")
print("=" * 78)
for i in range(2009, min(2040, len(lines))):
    marker = ">>>" if i+1 == 2021 else "   "
    print(f"{marker} {i+1:4}  {lines[i]}")

print("\n" + "=" * 78)
print("[2] Toutes les occurrences de 'motif'")
print("=" * 78)
for i, line in enumerate(lines, 1):
    if "motif" in line.lower():
        print(f"  L{i}: {line.strip()[:120]}")

print("\n" + "=" * 78)
print("[3] Toutes les occurrences de 'function refresh'")
print("=" * 78)
for i, line in enumerate(lines, 1):
    if "function refresh" in line:
        print(f"  L{i}: {line.strip()}")

print("\n" + "=" * 78)
print("[4] Toutes les occurrences de 'refresh()' (appels)")
print("=" * 78)
for i, line in enumerate(lines, 1):
    if re.search(r'\brefresh\(\)', line) and "function refresh" not in line:
        print(f"  L{i}: {line.strip()[:120]}")

print("\n" + "=" * 78)
print("[5] Occurrences eh:refresh listener")
print("=" * 78)
for i, line in enumerate(lines, 1):
    if "eh:refresh" in line:
        print(f"  L{i}: {line.strip()[:120]}")

print("\n" + "=" * 78)
print("[6] Toutes les occurrences de 'debouncedRefresh' / 'triggerRefresh'")
print("=" * 78)
for i, line in enumerate(lines, 1):
    if "debouncedRefresh" in line or "triggerRefresh" in line:
        print(f"  L{i}: {line.strip()[:120]}")

print("\n" + "=" * 78)
print("[7] Occurrences #refresh-btn dans le code")
print("=" * 78)
for i, line in enumerate(lines, 1):
    if "refresh-btn" in line:
        print(f"  L{i}: {line.strip()[:120]}")

print("\n" + "=" * 78)
print("[8] Le HTML charge quelle version de pharmacien.js ?")
print("=" * 78)
HTML = os.path.join(ROOT, "static", "pharmacien.html")
html = open(HTML, "r", encoding="utf-8").read()
for m in re.finditer(r'pharmacien\.js\?v=(\d+)', html):
    print(f"  HTML -> pharmacien.js?v={m.group(1)}")

print(f"\n[INFO] Fichier pharmacien.js : {len(lines)} lignes")