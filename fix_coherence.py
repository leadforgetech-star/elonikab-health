# -*- coding: utf-8 -*-
"""
LOT 2 p2 - FIX COHERENCE FRONT/BACK
====================================
Ajoute les actions manquantes dans buildQuickActions :
  - confirmee -> +Refuser
  - en_preparation -> +Refuser
  - prete -> +Terminee (en plus de En livraison)
Atomic, rollback auto si erreur.
"""
import os, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
JS   = os.path.join(ROOT, "static", "pharmacien.js")

TS  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, "_backup_coherence_" + TS)
os.makedirs(BAK, exist_ok=True)

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]"}[k]
    print(p, m)

def brace_diff(s): return s.count("{") - s.count("}")

shutil.copy2(JS, os.path.join(BAK, "pharmacien.js"))
print("=" * 78)
print("FIX COHERENCE - " + TS)
print("=" * 78)
print("[BACKUP] " + BAK + "\n")

src = open(JS, "r", encoding="utf-8").read()

OLD = '''  function buildQuickActions(o) {
    var actions = [];
    if (o.status === "en_attente") {
      actions.push({ label: "Confirmer", kind: "primary", act: "confirm" });
      actions.push({ label: "Refuser", kind: "danger", act: "refuse" });
    } else if (o.status === "confirmee") {
      actions.push({ label: "Preparer", kind: "primary", act: "prepare" });
    } else if (o.status === "en_preparation") {
      actions.push({ label: "Prete", kind: "primary", act: "ready" });
    } else if (o.status === "prete") {
      actions.push({ label: "En livraison", kind: "primary", act: "shipped" });
    } else if (o.status === "en_livraison") {
      actions.push({ label: "Terminee", kind: "primary", act: "complete" });
    }
    return actions;
  }'''

NEW = '''  function buildQuickActions(o) {
    var actions = [];
    if (o.status === "en_attente") {
      actions.push({ label: "Confirmer", kind: "primary", act: "confirm" });
      actions.push({ label: "Refuser", kind: "danger", act: "refuse" });
    } else if (o.status === "confirmee") {
      actions.push({ label: "Preparer", kind: "primary", act: "prepare" });
      actions.push({ label: "Refuser", kind: "danger", act: "refuse" });
    } else if (o.status === "en_preparation") {
      actions.push({ label: "Prete", kind: "primary", act: "ready" });
      actions.push({ label: "Refuser", kind: "danger", act: "refuse" });
    } else if (o.status === "prete") {
      actions.push({ label: "En livraison", kind: "primary", act: "shipped" });
      actions.push({ label: "Terminee", kind: "primary", act: "complete" });
    } else if (o.status === "en_livraison") {
      actions.push({ label: "Terminee", kind: "primary", act: "complete" });
    }
    return actions;
  }'''

if NEW.split("\n")[4].strip() in src and "Refuser\", kind: \"danger\", act: \"refuse\" });\n    } else if (o.status === \"en_preparation\")" in src:
    log("buildQuickActions deja patche", "WARN")
    sys.exit(0)

if OLD not in src:
    log("Ancien buildQuickActions introuvable", "ERR")
    sys.exit(1)

src = src.replace(OLD, NEW, 1)
log("buildQuickActions : actions ajoutees (Refuser x2, Terminee x1)", "OK")

if brace_diff(src) != 0:
    log("Accolades desequilibrees - ROLLBACK", "ERR")
    shutil.copy2(os.path.join(BAK, "pharmacien.js"), JS)
    sys.exit(1)

open(JS, "w", encoding="utf-8").write(src)
log("pharmacien.js sauvegarde", "OK")

print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)

final = open(JS, "r", encoding="utf-8").read()
m = __import__("re").search(r"function buildQuickActions[\s\S]*?\n  \}", final)
if m:
    block = m.group(0)
    checks = [
        ("confirmee : Refuser",        'if (o.status === "confirmee")' in block and "Refuser" in block.split('if (o.status === "confirmee")')[1].split("else")[0]),
        ("en_preparation : Refuser",   'if (o.status === "en_preparation")' in block and "Refuser" in block.split('if (o.status === "en_preparation")')[1].split("else")[0]),
        ("prete : Terminee",           'if (o.status === "prete")' in block and "Terminee" in block.split('if (o.status === "prete")')[1].split("else")[0]),
        ("en_livraison : Terminee",    'if (o.status === "en_livraison")' in block and "Terminee" in block.split('if (o.status === "en_livraison")')[1]),
    ]
    for label, ok in checks:
        print("  [" + ("OK" if ok else "!!") + "] " + label)
else:
    print("  [!!] buildQuickActions introuvable apres patch")

print()
print("[BACKUP] " + BAK)
print()
print("[CMD] Pas de restart Uvicorn (JS only).")
print()
print("[TEST] Edge : F12 > Application > Clear site data + Disable cache + Ctrl+Shift+R")
print("  1) /pharmacien -> Commandes")
print("  2) Commande 'confirmee' -> boutons : Preparer + Refuser (2 boutons)")
print("  3) Commande 'en_preparation' -> boutons : Prete + Refuser")
print("  4) Commande 'prete' -> boutons : En livraison + Terminee")
print()
print("[ROLLBACK] :")
print('  copy "' + BAK + '\\pharmacien.js" "' + JS + '"')