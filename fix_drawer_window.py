# -*- coding: utf-8 -*-
"""Expose drawerRefreshIfOpen sur window."""
import os, re, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
JS = os.path.join(ROOT, "static", "pharmacien.js")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_windowfix_{TS}")
os.makedirs(BAK, exist_ok=True)
shutil.copy2(JS, os.path.join(BAK, "pharmacien.js"))

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]"}[k]
    print(p, m)

print("=" * 78)
print(f"FIX WINDOW - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

src = open(JS, "r", encoding="utf-8").read()

# Deja exposée ?
if "window.drawerRefreshIfOpen = drawerRefreshIfOpen" in src:
    log("Deja exposee sur window", "WARN")
    sys.exit(0)

# Trouver la definition
m = re.search(r"function drawerRefreshIfOpen\s*\(\s*\)\s*\{", src)
if not m:
    log("Definition introuvable", "ERR")
    sys.exit(1)

# Trouver la fin de la fonction : matching braces
start = m.start()
brace_start = m.end() - 1  # position du {
depth = 0
end = None
for i in range(brace_start, len(src)):
    if src[i] == "{": depth += 1
    elif src[i] == "}":
        depth -= 1
        if depth == 0:
            end = i + 1
            break

if end is None:
    log("Fin de fonction introuvable", "ERR")
    sys.exit(1)

print(f"Fonction trouvee : L{src[:start].count(chr(10)) + 1} a L{src[:end].count(chr(10)) + 1}")

# Inserer l'exposition juste apres la fonction
injection = "\n\nwindow.drawerRefreshIfOpen = drawerRefreshIfOpen;\n"
src = src[:end] + injection + src[end:]

# Verification equilibre
braces = src.count("{") - src.count("}")
if braces != 0:
    log(f"Deséquilibre ({braces}) - ROLLBACK", "ERR")
    shutil.copy2(os.path.join(BAK, "pharmacien.js"), JS)
    sys.exit(1)

open(JS, "w", encoding="utf-8").write(src)
log("Exposition window ajoutee", "OK")

# Verification
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)
final = open(JS, "r", encoding="utf-8").read()
checks = [
    ("Fonction definie",       "function drawerRefreshIfOpen()" in final),
    ("Exposee sur window",     "window.drawerRefreshIfOpen = drawerRefreshIfOpen" in final),
    ("Accolades OK",           final.count("{") == final.count("}")),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

print()
print(f"[BACKUP] {BAK}")
print("[CMD] Pas de restart Uvicorn.")
print("[TEST] F12 > Clear site data + Ctrl+Shift+R sur /pharmacien")
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\pharmacien.js" "{JS}"')