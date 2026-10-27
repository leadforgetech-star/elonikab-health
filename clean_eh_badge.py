# -*- coding: utf-8 -*-
"""Supprime la branche 'stock faible' du helper ehProductBadge inutilise."""
import os, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
APP = os.path.join(ROOT, "static", "app.js")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_cleanbadge_{TS}")
os.makedirs(BAK, exist_ok=True)
shutil.copy2(APP, os.path.join(BAK, "app.js"))

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]"}[k]
    print(p, m)

print("=" * 78)
print(f"CLEAN EH BADGE - {TS}")
print("=" * 78)

src = open(APP, "r", encoding="utf-8").read()

OLD = '''    var sq = p.stock_quantity;
    if (sq !== null && sq !== undefined && sq <= 5) return { label: "Stock faible (" + sq + ")", cls: "eh-badge-warn" };
    return { label: "Disponible", cls: "eh-badge-ok" };'''

NEW = '''    return { label: "Disponible", cls: "eh-badge-ok" };'''

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    open(APP, "w", encoding="utf-8").write(src)
    log("Branche 'stock faible' retiree", "OK")
elif "Stock faible" not in src:
    log("Deja nettoye", "WARN")
else:
    log("Pattern introuvable", "WARN")

# Verification
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)
final = open(APP, "r", encoding="utf-8").read()
checks = [
    ("Plus de 'Stock faible'", "Stock faible" not in final),
    ("Disponible conserve",    '"Disponible"' in final),
    ("Rupture conservee",      "Rupture de stock" in final),
    ("Accolades OK",           final.count("{") == final.count("}")),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

print()
print("[CMD] Pas de restart Uvicorn.")
print("[TEST] F12 > Clear site data + Ctrl+Shift+R")
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\app.js" "{APP}"')