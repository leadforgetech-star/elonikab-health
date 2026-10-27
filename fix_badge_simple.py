# -*- coding: utf-8 -*-
"""Enleve le badge 'stock faible' : garde seulement Disponible / Rupture."""
import os, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
APP = os.path.join(ROOT, "static", "app.js")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_badgesimple_{TS}")
os.makedirs(BAK, exist_ok=True)
shutil.copy2(APP, os.path.join(BAK, "app.js"))

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]"}[k]
    print(p, m)

def brace_diff(s): return s.count("{") - s.count("}")

print("=" * 78)
print(f"FIX BADGE SIMPLE - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

src = open(APP, "r", encoding="utf-8").read()

# Remplacer availabilityTag : enlever le cas "stock faible"
OLD = '''  } else if (sq !== null && sq !== undefined && sq <= minThresh) {
    span.classList.add("tag-ok");
    span.style.background = "#FFF4E0";
    span.style.color = "#B26B00";
    span.textContent = "Stock faible (" + sq + ")";
    span.setAttribute("data-availability", "low");
  } else {'''

NEW = '''  } else {'''

if NEW in src and "Stock faible" not in src:
    log("Deja fait", "WARN"); sys.exit(0)

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    log("Badge stock faible retire", "OK")
else:
    log("Pattern introuvable", "WARN")

if brace_diff(src) != 0:
    log("Desequilibre - ROLLBACK", "ERR")
    shutil.copy2(os.path.join(BAK, "app.js"), APP)
    sys.exit(1)

open(APP, "w", encoding="utf-8").write(src)
log("app.js sauvegarde", "OK")

print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)
final = open(APP, "r", encoding="utf-8").read()
checks = [
    ("Plus de 'Stock faible'",  "Stock faible" not in final),
    ("Disponible conserve",     '"Disponible"' in final),
    ("Rupture conservee",       "Rupture de stock" in final),
    ("Accolades OK",            brace_diff(final) == 0),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

print()
print("[CMD] Pas de restart Uvicorn.")
print("[TEST] F12 > Clear site data + Ctrl+Shift+R")
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\app.js" "{APP}"')