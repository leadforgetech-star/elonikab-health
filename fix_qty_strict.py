# -*- coding: utf-8 -*-
"""
Fix strict quantite :
1. Backend : refus explicite si qty > stock (cart.py)
2. Frontend : blocage input qty + message d'erreur visible
"""
import os, re, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
CART = os.path.join(ROOT, "v3_modules", "cart.py")
APP = os.path.join(ROOT, "static", "app.js")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_qty_{TS}")
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

for p, n in [(CART, "cart.py"), (APP, "app.js")]:
    shutil.copy2(p, os.path.join(BAK, n))

print("=" * 78)
print(f"FIX QTY STRICT - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

# ============================================================
# PHASE 1 : Backend - refus explicite si qty > stock
# ============================================================
log("PHASE 1 : Backend refus explicite", "INFO")

cart_src = open(CART, "r", encoding="utf-8").read()

# Le message actuel a peut-etre ete tronque ou mal insere
# On cherche la logique existante et on la renforce

OLD_CHECK = '''            # LOT 7 : verifier que la quantite totale ne depasse pas le stock
            _existing = conn.execute(
                "SELECT quantity FROM cart_items WHERE cart_id = ? AND product_id = ?",
                (cart["id"], payload.product_id),
            ).fetchone()
            _existing_qty = _existing["quantity"] if _existing else 0
            _total_requested = _existing_qty + payload.quantity
            if _sq is not None and _total_requested > _sq:
                _available = max(0, _sq - _existing_qty)
                raise HTTPException(
                    400,
                    f"Quantite insuffisante. Disponible : {_available} (vous en avez deja {_existing_qty} au panier)"
                )'''

NEW_CHECK = '''            # LOT 7 : verifier que la quantite totale ne depasse pas le stock
            _existing = conn.execute(
                "SELECT quantity FROM cart_items WHERE cart_id = ? AND product_id = ?",
                (cart["id"], payload.product_id),
            ).fetchone()
            _existing_qty = _existing["quantity"] if _existing else 0
            _total_requested = _existing_qty + payload.quantity
            if _sq is not None and _sq >= 0:
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

if "Stock insuffisant. Vous demandez" in cart_src:
    log("Backend deja patche", "WARN")
elif OLD_CHECK in cart_src:
    cart_src = cart_src.replace(OLD_CHECK, NEW_CHECK, 1)
    open(CART, "w", encoding="utf-8").write(cart_src)
    ok, err = syntax_ok(CART)
    if not ok:
        log(f"cart.py ERREUR : {err}", "ERR")
        shutil.copy2(os.path.join(BAK, "cart.py"), CART)
    else:
        log("Backend : message explicite ajoute", "OK")
else:
    log("Pattern backend introuvable", "WARN")

# ============================================================
# PHASE 2 : Frontend - blocage strict input qty
# ============================================================
log("PHASE 2 : Frontend blocage strict", "INFO")

app_src = open(APP, "r", encoding="utf-8").read()

# 2a. Ajouter max sur le bouton "+"
OLD_PLUS = '''    btnPlus.addEventListener("click", function () {
      var n = getQty() + 1;
      if (n > 99) n = 99;
      qtyInput.value = String(n);
    });'''

NEW_PLUS = '''    btnPlus.addEventListener("click", function () {
      var n = getQty() + 1;
      var _max2 = parseInt(qtyInput.max || "99", 10) || 99;
      if (n > _max2) {
        n = _max2;
        if (window.EHModal) {
          window.EHModal.alert("Quantité limitée",
            "Maximum disponible en stock : " + _max2, "warn");
        }
      }
      qtyInput.value = String(n);
    });'''

if "Maximum disponible en stock : " in app_src:
    log("Bouton + deja patche", "WARN")
elif OLD_PLUS in app_src:
    app_src = app_src.replace(OLD_PLUS, NEW_PLUS, 1)
    log("Bouton + : blocage strict", "OK")
else:
    log("Bouton + pattern introuvable", "WARN")

# 2b. Blocage direct sur input (empeche la saisie manuelle > max)
OLD_BLUR = '''    qtyInput.addEventListener("blur", function () { getQty(); });'''

NEW_BLUR = '''    qtyInput.addEventListener("blur", function () { getQty(); });
    qtyInput.addEventListener("change", function () {
      var v = parseInt(qtyInput.value, 10);
      var _max3 = parseInt(qtyInput.max || "99", 10) || 99;
      if (isNaN(v) || v < 1) { qtyInput.value = "1"; return; }
      if (v > _max3) {
        qtyInput.value = String(_max3);
        if (window.EHModal) {
          window.EHModal.alert("Quantité limitée",
            "Maximum disponible en stock : " + _max3 + "\\nVotre saisie (" + v + ") a été corrigée.",
            "warn");
        }
      }
    });'''

if 'qtyInput.addEventListener("change"' in app_src:
    log("Change listener deja present", "WARN")
elif OLD_BLUR in app_src:
    app_src = app_src.replace(OLD_BLUR, NEW_BLUR, 1)
    log("Change listener ajoute", "OK")
else:
    log("Blur listener introuvable", "WARN")

# 2c. Renforcer addToCartQty : refuser AVANT appel API si qty > stock
# Chercher la fonction
idx = app_src.find("function addToCartQty(")
if idx > 0:
    # Trouver la fin de la fonction (prochaine "function" ou "}" au bon niveau)
    end = app_src.find("\nfunction ", idx + 10)
    if end < 0:
        end = idx + 2000
    fn = app_src[idx:end]
    
    if "Verifier qty vs stock" not in fn:
        # Injecter au debut de la fonction
        # Trouver le premier {
        brace_idx = fn.find("{")
        if brace_idx > 0:
            inject = '''{
  // LOT 7 : Verifier qty vs stock AVANT l'appel API
  var _maxQty = 0;
  if (typeof p !== "undefined" && p && p.stock_quantity !== null && p.stock_quantity !== undefined) {
    _maxQty = p.stock_quantity;
  }
  if (_maxQty > 0 && qty > _maxQty) {
    if (window.EHModal) window.EHModal.alert("Stock insuffisant",
      "Vous demandez " + qty + " mais il ne reste que " + _maxQty + " en stock.", "danger");
    return Promise.reject(new Error("Stock insuffisant"));
  }
'''
            fn_new = fn[:brace_idx] + inject + fn[brace_idx+1:]
            app_src = app_src[:idx] + fn_new + app_src[end:]
            log("addToCartQty : check pre-API", "OK")
        else:
            log("addToCartQty : brace introuvable", "WARN")
    else:
        log("addToCartQty deja patche", "WARN")
else:
    log("addToCartQty introuvable (peut etre normal)", "WARN")

# Verification equilibre
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
final_cart = open(CART, "r", encoding="utf-8").read()
final_app = open(APP, "r", encoding="utf-8").read()

checks = [
    ("Backend : message 'Stock insuffisant'", "Stock insuffisant. Vous demandez" in final_cart),
    ("Frontend : bouton + bloque",            "Maximum disponible en stock :" in final_app),
    ("Frontend : change listener",            'qtyInput.addEventListener("change"' in final_app),
    ("cart.py syntaxe OK",                    syntax_ok(CART)[0]),
    ("app.js equilibre",                      final_app.count("{") == final_app.count("}")),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

print()
print(f"[BACKUP] {BAK}")
print()
print("[CMD] Restart Uvicorn OBLIGATOIRE :")
print("  Ctrl+C dans le terminal Uvicorn, puis :")
print("  python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir v3_modules --reload-dir static")
print()
print("[TEST] Edge : F12 > Application > Clear site data + Ctrl+Shift+R")
print("  1) Produit stock=3 : cliquer + jusqu'a depasser -> message 'Maximum 3'")
print("  2) Saisir 5 dans input -> corrige a 3 + message")
print("  3) Ajouter -> backend refuse si qty > stock")
print()
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\cart.py" "{CART}"')
print(f'  copy "{BAK}\\app.js" "{APP}"')