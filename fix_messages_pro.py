# -*- coding: utf-8 -*-
"""Applique le message pro 'Disponibilité limitée' partout."""
import os, re, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
CART = os.path.join(ROOT, "v3_modules", "cart.py")
APP = os.path.join(ROOT, "static", "app.js")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_msgpro_{TS}")
os.makedirs(BAK, exist_ok=True)

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]"}[k]
    print(p, m)

def syntax_ok(path):
    try:
        with open(path, "rb") as f:
            compile(f.read(), path, "exec")
        return True, None
    except SyntaxError as e:
        return False, f"L{e.lineno}: {e.msg}"

shutil.copy2(CART, os.path.join(BAK, "cart.py"))
shutil.copy2(APP, os.path.join(BAK, "app.js"))

print("=" * 78)
print(f"MESSAGES PRO - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

# ============================================================
# 1. BACKEND : messages pro dans cart.py
# ============================================================
log("PHASE 1 : Backend (cart.py)", "INFO")

cart_src = open(CART, "r", encoding="utf-8").read()

OLD_BK = '''            if _sq is not None and _sq >= 0:
                _available = max(0, _sq - _existing_qty)
                if payload.quantity > _sq:
                    raise HTTPException(
                        400,
                        f"Stock insuffisant. Vous demandez {payload.quantity} mais il ne reste que {_sq} en stock."
                    )
                if _total_requested > _sq:
                    raise HTTPException(
                        400,
                        f"Stock insuffisant. Vous demandez {payload.quantity} mais il ne reste que {_available} disponible (déjà {_existing_qty} au panier)."
                    )'''

NEW_BK = '''            if _sq is not None and _sq >= 0:
                _available = max(0, _sq - _existing_qty)
                if payload.quantity > _sq:
                    if _sq == 0:
                        raise HTTPException(
                            400,
                            "Ce produit est actuellement en rupture de stock."
                        )
                    elif _sq == 1:
                        raise HTTPException(
                            400,
                            "Ce produit n'est actuellement disponible qu'en 1 unité. Veuillez ajuster votre quantité."
                        )
                    else:
                        raise HTTPException(
                            400,
                            f"Ce produit n'est actuellement disponible qu'en {_sq} unités. Veuillez ajuster votre quantité."
                        )
                if _total_requested > _sq:
                    if _available == 0:
                        raise HTTPException(
                            400,
                            f"Vous avez déjà {_existing_qty} unité(s) de ce produit dans votre panier, soit la totalité du stock disponible."
                        )
                    elif _available == 1:
                        raise HTTPException(
                            400,
                            f"Il ne reste qu'1 unité disponible (sur {_sq} en stock, {_existing_qty} déjà dans votre panier). Veuillez ajuster votre quantité."
                        )
                    else:
                        raise HTTPException(
                            400,
                            f"Il ne reste que {_available} unités disponibles (sur {_sq} en stock, {_existing_qty} déjà dans votre panier). Veuillez ajuster votre quantité."
                        )'''

if "Ce produit n'est actuellement disponible qu'en" in cart_src:
    log("Backend deja patche", "WARN")
elif OLD_BK in cart_src:
    cart_src = cart_src.replace(OLD_BK, NEW_BK, 1)
    open(CART, "w", encoding="utf-8").write(cart_src)
    ok, err = syntax_ok(CART)
    if not ok:
        log(f"ERREUR : {err}", "ERR")
        shutil.copy2(os.path.join(BAK, "cart.py"), CART)
    else:
        log("Backend : messages pro appliques", "OK")
else:
    log("Pattern backend introuvable", "WARN")

# ============================================================
# 2. FRONTEND : bouton + et change listener
# ============================================================
log("PHASE 2 : Frontend (app.js)", "INFO")

app_src = open(APP, "r", encoding="utf-8").read()

# 2a. Bouton +
OLD_PLUS = '''      if (n > _max2) {
        n = _max2;
        if (window.EHModal) {
          window.EHModal.alert("Quantité limitée",
            "Maximum disponible en stock : " + _max2, "warn");
        }
      }'''

NEW_PLUS = '''      if (n > _max2) {
        n = _max2;
        if (window.EHModal) {
          var _msgPlus = (_max2 === 1)
            ? "Ce produit n'est actuellement disponible qu'en 1 unité."
            : "Ce produit n'est actuellement disponible qu'en " + _max2 + " unités.";
          window.EHModal.alert("Disponibilité limitée", _msgPlus, "warn");
        }
      }'''

if "Disponibilité limitée" in app_src and "_msgPlus" in app_src:
    log("Bouton + deja patche", "WARN")
elif OLD_PLUS in app_src:
    app_src = app_src.replace(OLD_PLUS, NEW_PLUS, 1)
    log("Bouton + : message pro", "OK")
else:
    log("Bouton + pattern introuvable", "WARN")

# 2b. Change listener (saisie manuelle)
OLD_CHG = '''      if (v > _max3) {
        qtyInput.value = String(_max3);
        if (window.EHModal) {
          window.EHModal.alert("Quantité limitée",
            "Maximum disponible en stock : " + _max3 + "\\nVotre saisie (" + v + ") a été corrigée.",
            "warn");
        }
      }'''

NEW_CHG = '''      if (v > _max3) {
        qtyInput.value = String(_max3);
        if (window.EHModal) {
          var _msgChg = (_max3 === 1)
            ? "Ce produit n'est actuellement disponible qu'en 1 unité. Votre quantité a été ajustée."
            : "Ce produit n'est actuellement disponible qu'en " + _max3 + " unités. Votre quantité a été ajustée.";
          window.EHModal.alert("Disponibilité limitée", _msgChg, "warn");
        }
      }'''

if "_msgChg" in app_src:
    log("Change listener deja patche", "WARN")
elif OLD_CHG in app_src:
    app_src = app_src.replace(OLD_CHG, NEW_CHG, 1)
    log("Change listener : message pro", "OK")
else:
    log("Change listener pattern introuvable", "WARN")

# 2c. addToCartQty pre-check
OLD_PRE = '''  if (_maxQty > 0 && qty > _maxQty) {
    if (window.EHModal) window.EHModal.alert("Stock insuffisant",
      "Vous demandez " + qty + " mais il ne reste que " + _maxQty + " en stock.", "danger");
    return Promise.reject(new Error("Stock insuffisant"));
  }'''

NEW_PRE = '''  if (_maxQty > 0 && qty > _maxQty) {
    if (window.EHModal) {
      var _msgPre = (_maxQty === 1)
        ? "Ce produit n'est actuellement disponible qu'en 1 unité. Veuillez ajuster votre quantité."
        : "Ce produit n'est actuellement disponible qu'en " + _maxQty + " unités. Veuillez ajuster votre quantité.";
      window.EHModal.alert("Disponibilité limitée", _msgPre, "warn");
    }
    return Promise.reject(new Error("Disponibilité limitée"));
  }'''

if "_msgPre" in app_src:
    log("addToCartQty deja patche", "WARN")
elif OLD_PRE in app_src:
    app_src = app_src.replace(OLD_PRE, NEW_PRE, 1)
    log("addToCartQty : message pro", "OK")
else:
    log("addToCartQty pattern introuvable", "WARN")

# Equilibre accolades
braces = app_src.count("{") - app_src.count("}")
if braces != 0:
    log(f"app.js desequilibre ({braces}) - ROLLBACK", "ERR")
    shutil.copy2(os.path.join(BAK, "app.js"), APP)
else:
    open(APP, "w", encoding="utf-8").write(app_src)
    log("app.js sauvegarde", "OK")

# ============================================================
# Verification
# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)

fc = open(CART, "r", encoding="utf-8").read()
fa = open(APP, "r", encoding="utf-8").read()

checks = [
    ("Backend : 'Disponibilité limitée'",     "Ce produit n'est actuellement disponible qu'en" in fc),
    ("Backend : cas rupture",                 "actuellement en rupture de stock" in fc),
    ("Backend : cas panier deja plein",       "soit la totalité du stock disponible" in fc),
    ("Frontend : bouton + (_msgPlus)",        "_msgPlus" in fa),
    ("Frontend : input (_msgChg)",            "_msgChg" in fa),
    ("Frontend : pre-check (_msgPre)",        "_msgPre" in fa),
    ("Titre 'Disponibilité limitée'",         "Disponibilité limitée" in fa),
    ("cart.py syntaxe OK",                    syntax_ok(CART)[0]),
    ("app.js equilibre",                      fa.count("{") == fa.count("}")),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

print()
print(f"[BACKUP] {BAK}")
print()
print("[CMD] Restart Uvicorn OBLIGATOIRE :")
print("  taskkill /F /IM uvicorn.exe 2>nul")
print("  taskkill /F /IM python.exe 2>nul")
print("  python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir v3_modules --reload-dir static")
print()
print("[TEST] Edge : F12 > Clear site data + Ctrl+Shift+R")
print("  - Produit stock=3 : tenter + au-dela de 3 -> 'Disponibilité limitée / Ce produit n'est actuellement disponible qu'en 3 unités.'")
print("  - Saisir 5 dans input -> corrige a 3 + meme message")
print()
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\cart.py" "{CART}"')
print(f'  copy "{BAK}\\app.js" "{APP}"')