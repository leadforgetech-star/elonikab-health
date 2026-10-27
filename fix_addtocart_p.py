# -*- coding: utf-8 -*-
"""Fix addToCartQty : passer le produit complet + revert badge + dump updateCartBadge."""
import os, re, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
APP = os.path.join(ROOT, "static", "app.js")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_addtocart_{TS}")
os.makedirs(BAK, exist_ok=True)
shutil.copy2(APP, os.path.join(BAK, "app.js"))

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]"}[k]
    print(p, m)

print("=" * 78)
print(f"FIX ADDTOCART - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

src = open(APP, "r", encoding="utf-8").read()

# ============================================================
# 1. Changer la signature : addToCartQty(p, qty, ...)
# ============================================================
log("Fix 1 : Signature addToCartQty", "INFO")

OLD_SIG = 'function addToCartQty(productId, qty, btn, qtyInput) {'
NEW_SIG = 'function addToCartQty(p, qty, btn, qtyInput) {\n  var productId = (typeof p === "object" && p) ? p.id : p;'

if "var productId = (typeof p === \"object\"" in src:
    log("Signature deja patchee", "WARN")
elif OLD_SIG in src:
    src = src.replace(OLD_SIG, NEW_SIG, 1)
    log("Signature changee", "OK")
else:
    log("Signature introuvable", "ERR")

# ============================================================
# 2. Fix le check _maxQty
# ============================================================
log("Fix 2 : check _maxQty", "INFO")

OLD_CHECK = '''  var _maxQty = 0;
  if (typeof p !== "undefined" && p && p.stock_quantity !== null && p.stock_quantity !== undefined) {
    _maxQty = p.stock_quantity;
  }'''

NEW_CHECK = '''  var _maxQty = 0;
  if (typeof p === "object" && p && p.stock_quantity !== null && p.stock_quantity !== undefined) {
    _maxQty = p.stock_quantity;
  }'''

if NEW_CHECK in src:
    log("Check deja patche", "WARN")
elif OLD_CHECK in src:
    src = src.replace(OLD_CHECK, NEW_CHECK, 1)
    log("Check _maxQty corrige", "OK")
else:
    log("Check pattern introuvable", "WARN")

# ============================================================
# 3. Fix les appels dans productCard + renderProduct
# ============================================================
log("Fix 3 : appels addToCartQty(p.id, ...) -> addToCartQty(p, ...)", "INFO")

n_calls = src.count("addToCartQty(p.id,")
if n_calls > 0:
    src = src.replace("addToCartQty(p.id,", "addToCartQty(p,")
    log(f"{n_calls} appel(s) corrige(s)", "OK")
else:
    log("Aucun appel addToCartQty(p.id) trouve", "WARN")

# Autre variante : avec espace
n2 = src.count("addToCartQty(p.id ,")
if n2 > 0:
    src = src.replace("addToCartQty(p.id ,", "addToCartQty(p ,")
    log(f"{n2} appel(s) corrige(s) (variante)", "OK")

# ============================================================
# 4. Fix revert badge en cas d'erreur
# ============================================================
log("Fix 4 : revert badge apres erreur", "INFO")

# Dans le catch du fetch, ajouter un loadCartBadge() pour resync
# Trouver le catch final de addToCartQty
idx = src.find("function addToCartQty(p,")
if idx < 0:
    idx = src.find("function addToCartQty(")
end = src.find("\nfunction ", idx + 10)
if end < 0:
    end = idx + 3500
fn = src[idx:end]

print("  --- Debut de la fonction (extrait) ---")
print(fn[:3500])
print("  --- Fin ---")

# Chercher le catch existant
if "loadCartBadge()" in fn:
    log("loadCartBadge deja appele dans addToCartQty", "WARN")
else:
    # Ajouter un loadCartBadge() a la fin de la fonction (dans le .catch final)
    # Chercher le pattern ".catch(function"
    last_catch = fn.rfind(".catch(function")
    if last_catch > 0:
        # Trouver la fin de ce catch
        sub = fn[last_catch:last_catch+500]
        # Insérer "loadCartBadge();" apres "{" du catch
        brace = sub.find("{")
        if brace > 0:
            new_sub = sub[:brace+1] + "\n      try { loadCartBadge(); } catch(e) {}" + sub[brace+1:]
            fn_new = fn[:last_catch] + new_sub + fn[last_catch+500:]
            src = src[:idx] + fn_new + src[end:]
            log("loadCartBadge() ajoute dans le catch final", "OK")
        else:
            log("Brace du catch introuvable", "WARN")
    else:
        log("Catch final introuvable", "WARN")

# Verification equilibre
braces = src.count("{") - src.count("}")
if braces != 0:
    log(f"app.js desequilibre ({braces}) - ROLLBACK", "ERR")
    shutil.copy2(os.path.join(BAK, "app.js"), APP)
    sys.exit(1)

open(APP, "w", encoding="utf-8").write(src)
log("app.js sauvegarde", "OK")

# ============================================================
# 5. Dump updateCartBadge
# ============================================================
print()
print("=" * 78)
print("DUMP : updateCartBadge")
print("=" * 78)

final = open(APP, "r", encoding="utf-8").read()
idx2 = final.find("function updateCartBadge")
if idx2 > 0:
    end2 = final.find("\nfunction ", idx2 + 10)
    if end2 < 0:
        end2 = idx2 + 1000
    print(final[idx2:end2])
else:
    print("  updateCartBadge introuvable")

# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)
checks = [
    ("Signature addToCartQty(p, ...)",   "function addToCartQty(p, qty" in final or "function addToCartQty(p," in final),
    ("var productId = p.id",             'var productId = (typeof p === "object"' in final),
    ("_maxQty corrige",                  'typeof p === "object" && p && p.stock_quantity' in final),
    ("Plus addToCartQty(p.id,",          "addToCartQty(p.id," not in final),
    ("loadCartBadge dans addToCart",     "loadCartBadge()" in final),
    ("Accolades OK",                     final.count("{") == final.count("}")),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

print()
print(f"[BACKUP] {BAK}")
print()
print("[CMD] Pas de restart Uvicorn (frontend only).")
print()
print("[TEST] Edge : F12 > Clear site data + Ctrl+Shift+R")
print("  1) Produit stock=3 -> demander 5 -> BLOQUE et message")
print("  2) Badge panier ne doit PAS disparaitre apres l'erreur")
print()
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\app.js" "{APP}"')