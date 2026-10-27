# -*- coding: utf-8 -*-
"""Fix cart.py : refus ajout panier si produit en rupture."""
import os, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
CART = os.path.join(ROOT, "v3_modules", "cart.py")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_cartfix_{TS}")
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
print("=" * 78)
print(f"FIX CART RUPTURE - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

src = open(CART, "r", encoding="utf-8").read()

# ============================================================
# Patch 1 : SELECT enrichi
# ============================================================
OLD_SELECT = '''            prod = conn.execute(
                "SELECT id, is_active FROM products WHERE id = ?",
                (payload.product_id,),
            ).fetchone()'''

NEW_SELECT = '''            prod = conn.execute(
                "SELECT id, is_active, stock_quantity, availability FROM products WHERE id = ?",
                (payload.product_id,),
            ).fetchone()'''

if "stock_quantity, availability FROM products WHERE id" in src:
    log("SELECT deja patche", "WARN")
elif OLD_SELECT in src:
    src = src.replace(OLD_SELECT, NEW_SELECT, 1)
    log("SELECT enrichi (stock_quantity, availability)", "OK")
else:
    log("SELECT pattern introuvable", "ERR")
    shutil.copy2(os.path.join(BAK, "cart.py"), CART)
    sys.exit(1)

# ============================================================
# Patch 2 : Check rupture apres is_active
# ============================================================
OLD_CHECK = '''            if prod["is_active"] == 0:
                raise HTTPException(400, "Produit indisponible")
            cart = _get_or_create_cart(conn, user["id"])'''

NEW_CHECK = '''            if prod["is_active"] == 0:
                raise HTTPException(400, "Produit indisponible")

            # LOT 7 : refus si rupture
            _avail = (prod["availability"] or "").lower()
            _sq = prod["stock_quantity"]
            if _avail == "rupture":
                raise HTTPException(400, "Produit en rupture de stock")
            if _sq is not None and _sq <= 0:
                raise HTTPException(400, "Produit en rupture de stock")

            cart = _get_or_create_cart(conn, user["id"])'''

if "Produit en rupture de stock" in src:
    log("Check rupture deja present", "WARN")
elif OLD_CHECK in src:
    src = src.replace(OLD_CHECK, NEW_CHECK, 1)
    log("Check rupture ajoute dans add_item", "OK")
else:
    log("Check pattern introuvable", "WARN")

# ============================================================
# Validation + sauvegarde
# ============================================================
braces = src.count("{") - src.count("}")
parens = src.count("(") - src.count(")")

if braces != 0 or parens != 0:
    log(f"Deséquilibre ({braces}, {parens}) - ROLLBACK", "ERR")
    shutil.copy2(os.path.join(BAK, "cart.py"), CART)
    sys.exit(1)

open(CART, "w", encoding="utf-8").write(src)
ok, err = syntax_ok(CART)
if not ok:
    log(f"cart.py ERREUR : {err}", "ERR")
    shutil.copy2(os.path.join(BAK, "cart.py"), CART)
    sys.exit(1)
log("cart.py syntaxe OK", "OK")

# ============================================================
# Verification
# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)

final = open(CART, "r", encoding="utf-8").read()
checks = [
    ("SELECT enrichi",       "stock_quantity, availability FROM products" in final),
    ("Check rupture",        "Produit en rupture de stock" in final),
    ("Check availability",   '_avail == "rupture"' in final),
    ("Check stock <= 0",     "_sq is not None and _sq <= 0" in final),
    ("Syntaxe OK",           syntax_ok(CART)[0]),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

print()
print(f"[BACKUP] {BAK}")
print()
print("[CMD] Restart Uvicorn OBLIGATOIRE :")
print("  taskkill /F /IM uvicorn.exe 2>nul")
print("  taskkill /F /IM python.exe 2>nul")
print("  python -m uvicorn main:app --host 0.0.0.0 --port 8000")
print()
print("[TEST] Apres restart :")
print("  Ajouter un produit en rupture au panier -> 400 'Produit en rupture de stock'")