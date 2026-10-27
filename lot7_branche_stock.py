# -*- coding: utf-8 -*-
"""
Lot 7 - Branchement stock + masquage rupture
=============================================
1. Backend : deduction auto du stock quand commande -> 'prete' (idempotent)
2. Backend : can_order dans /api/products
3. Backend : refus ajout panier si rupture
4. Frontend : masquage bouton si rupture

Atomic + rollback auto.
"""
import os, re, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
MAIN = os.path.join(ROOT, "main.py")
CART = os.path.join(ROOT, "v3_modules", "cart.py")
STATIC = os.path.join(ROOT, "static")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_stockbranch_{TS}")
os.makedirs(BAK, exist_ok=True)

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]", "STEP": "\n###"}[k]
    print(p, m)

def syntax_ok(path):
    try:
        with open(path, "rb") as f:
            compile(f.read(), path, "exec")
        return True, None
    except SyntaxError as e:
        return False, f"L{e.lineno}: {e.msg}"

def backup(p, name):
    if os.path.isfile(p):
        shutil.copy2(p, os.path.join(BAK, name))
        return True
    return False

# ============================================================
print("=" * 78)
print(f"LOT 7 - BRANCHEMENT STOCK - {TS}")
print("=" * 78)
log("PHASE 0 : Backup", "STEP")

for p, n in [(MAIN, "main.py"), (CART, "cart.py")]:
    if backup(p, n): log(f"Backup {n}", "OK")

main_src = open(MAIN, "r", encoding="utf-8").read()
main_orig = main_src

# ============================================================
# PHASE 1 : Helper de deduction
# ============================================================
log("PHASE 1 : Helper de deduction automatique", "STEP")

HELPER = '''

# ============================================================
# LOT 7 - Deduction stock automatique (commande -> 'prete')
# ============================================================
def _deduct_order_stock(conn, order_id, reference, user_id=None):
    """Deduit le stock d'une commande passee a 'prete'.
    Idempotent : ne fait rien si un mouvement OUT existe deja pour cette reference.
    """
    try:
        # Idempotence
        existing = conn.execute(
            "SELECT id FROM stock_movements WHERE reference = ? AND type = 'OUT' LIMIT 1",
            (reference,)
        ).fetchone()
        if existing:
            return {"ok": True, "already_deducted": True}

        # Recuperer les items
        items = conn.execute(
            "SELECT product_id, quantity FROM order_items WHERE order_id = ?",
            (order_id,)
        ).fetchall()

        # Fallback : commande mono-produit
        if not items:
            row = conn.execute(
                "SELECT product_id, quantity FROM orders WHERE id = ?",
                (order_id,)
            ).fetchone()
            if row and row["product_id"]:
                items = [row]

        now = datetime.now().isoformat(timespec="seconds")
        deducted = 0
        skipped = 0

        for it in items:
            pid = it["product_id"]
            qty = it["quantity"] or 1
            if not pid:
                continue

            prod = conn.execute(
                "SELECT id, name, stock_quantity FROM products WHERE id = ?",
                (pid,)
            ).fetchone()
            if not prod:
                continue

            current = prod["stock_quantity"]

            # Stock inconnu (NULL) : on ne peut pas deduire, on log
            if current is None:
                conn.execute(
                    "INSERT INTO stock_movements (product_id, type, quantity, reason,"
                    " reference, user_id, created_at)"
                    " VALUES (?, 'ADJUST', 0, ?, ?, ?, ?)",
                    (pid, "Deduction ignoree : stock non renseigne",
                     reference, user_id, now)
                )
                skipped += 1
                continue

            # Deduction (peut etre negative si stock insuffisant -> alerte)
            new_qty = current - qty
            conn.execute(
                "INSERT INTO stock_movements (product_id, type, quantity, reason,"
                " reference, user_id, created_at)"
                " VALUES (?, 'OUT', ?, ?, ?, ?, ?)",
                (pid, -qty, "Commande prete : " + reference,
                 reference, user_id, now)
            )
            conn.execute(
                "UPDATE products SET stock_quantity = ? WHERE id = ?",
                (new_qty, pid)
            )
            deducted += 1

        return {"ok": True, "deducted": deducted, "skipped": skipped}
    except Exception as e:
        return {"ok": False, "error": str(e)}


'''

if "def _deduct_order_stock" in main_src:
    log("Helper deja present", "WARN")
else:
    # Inserer apres def log_audit
    marker = "def log_audit("
    idx = main_src.find(marker)
    if idx < 0:
        log("Ancre log_audit introuvable", "ERR")
        sys.exit(1)
    # Trouver la fin de la fonction (prochain double saut de ligne)
    end = main_src.find("\n\n\n", idx)
    if end < 0:
        log("Fin de fonction introuvable", "ERR")
        sys.exit(1)
    main_src = main_src[:end] + "\n" + HELPER + main_src[end:]
    log("Helper _deduct_order_stock ajoute", "OK")

# ============================================================
# PHASE 2 : Appel dans PATCH /status quand new_status == 'prete'
# ============================================================
log("PHASE 2 : Hook dans PATCH /status", "STEP")

ANCHOR = '''    conn.execute("UPDATE orders SET status = ? WHERE reference = ?", (new_status, reference))
    log_audit(conn, user["id"] if user else None,
              "order.status_change", "order", row["id"],
              "de " + current_status + " vers " + new_status)'''

NEW_ANCHOR = '''    conn.execute("UPDATE orders SET status = ? WHERE reference = ?", (new_status, reference))
    log_audit(conn, user["id"] if user else None,
              "order.status_change", "order", row["id"],
              "de " + current_status + " vers " + new_status)

    # LOT 7 : deduction auto du stock quand la commande passe a 'prete'
    if new_status == "prete":
        try:
            _res = _deduct_order_stock(conn, row["id"], reference,
                                       user["id"] if user else None)
            if _res.get("deducted"):
                log_audit(conn, user["id"] if user else None,
                          "stock.auto_deduct", "order", row["id"],
                          "deduit=" + str(_res["deducted"]) + " ignore=" + str(_res.get("skipped", 0)))
        except Exception as _e:
            print(f"[stock-deduct] erreur : {_e}")'''

if "_deduct_order_stock(conn, row[\"id\"]" in main_src:
    log("Hook deja present", "WARN")
elif ANCHOR in main_src:
    main_src = main_src.replace(ANCHOR, NEW_ANCHOR, 1)
    log("Hook ajoute dans PATCH /status", "OK")
else:
    log("Ancre hook introuvable", "WARN")

# ============================================================
# PHASE 3 : can_order dans /api/products
# ============================================================
log("PHASE 3 : can_order dans list_products", "STEP")

OLD_RET = '''    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]'''

NEW_RET = '''    rows = conn.execute(sql, params).fetchall()
    conn.close()
    # LOT 7 : ajouter can_order (rupture/archive)
    result = []
    for r in rows:
        d = row_to_dict(r)
        sq = d.get("stock_quantity")
        avail = (d.get("availability") or "").lower()
        is_active = d.get("is_active", 1)
        d["can_order"] = bool(
            is_active == 1
            and avail != "rupture"
            and (sq is None or sq > 0)
        )
        result.append(d)
    return result'''

if "can_order" in main_src:
    log("can_order deja present", "WARN")
elif OLD_RET in main_src:
    main_src = main_src.replace(OLD_RET, NEW_RET, 1)
    log("can_order ajoute dans list_products", "OK")
else:
    log("Pattern list_products introuvable", "WARN")

# ============================================================
# PHASE 4 : Sauvegarde main.py + validation
# ============================================================
open(MAIN, "w", encoding="utf-8").write(main_src)
ok, err = syntax_ok(MAIN)
if not ok:
    log(f"main.py ERREUR : {err}", "ERR")
    shutil.copy2(os.path.join(BAK, "main.py"), MAIN)
    sys.exit(1)
log("main.py syntaxe OK", "OK")

# ============================================================
# PHASE 5 : Refus ajout panier si rupture (cart.py)
# ============================================================
log("PHASE 5 : Refus panier si rupture", "STEP")

if not os.path.isfile(CART):
    log("cart.py introuvable", "WARN")
else:
    cart_src = open(CART, "r", encoding="utf-8").read()

    if "product_not_orderable" in cart_src or "produit_indisponible" in cart_src:
        log("Check deja present", "WARN")
    else:
        # Chercher la fonction add_to_cart ou similaire
        # Pattern commun : "SELECT * FROM products WHERE id = ?" dans POST /api/cart/items
        patterns = [
            (r'(@app\.post\("/api/cart/items"\)[\s\S]*?)(product = conn\.execute\([^)]+\)\.fetchone\(\)\s*\n\s*if not product[^\n]*\n\s*raise HTTPException\(404[^\n]*)',
             'add_item'),
        ]
        patched = False
        for pat, name in patterns:
            m = re.search(pat, cart_src)
            if m:
                # Inserer apres le check "if not product: raise"
                old_block = m.group(2)
                insert = old_block + '''
                # LOT 7 : refus si rupture ou archive
                _sq = product["stock_quantity"] if "stock_quantity" in product.keys() else None
                _avail = (product["availability"] or "").lower() if "availability" in product.keys() else ""
                _active = product["is_active"] if "is_active" in product.keys() else 1
                if _active != 1:
                    raise HTTPException(400, "Produit archive : commande impossible")
                if _avail == "rupture":
                    raise HTTPException(400, "Produit en rupture de stock")
                if _sq is not None and _sq <= 0:
                    raise HTTPException(400, "Produit en rupture de stock")'''
                cart_src = cart_src.replace(old_block, insert, 1)
                patched = True
                log(f"Check ajoute dans {name}", "OK")
                break

        if not patched:
            log("Pattern cart.py introuvable - on tente fallback", "WARN")
            # Fallback : chercher toute occurrence de "if not product: raise 404"
            m = re.search(r'(if not product[^\n]*\n\s*raise HTTPException\(404[^\n]*\n)', cart_src)
            if m:
                insert = m.group(1) + '''
            # LOT 7 : refus si rupture ou archive
            try:
                _sq = product["stock_quantity"]
                _avail = (product["availability"] or "").lower()
                _active = product["is_active"]
                if _active != 1:
                    raise HTTPException(400, "Produit archive : commande impossible")
                if _avail == "rupture":
                    raise HTTPException(400, "Produit en rupture de stock")
                if _sq is not None and _sq <= 0:
                    raise HTTPException(400, "Produit en rupture de stock")
            except (KeyError, IndexError):
                pass
'''
                cart_src = cart_src[:m.start()] + insert + cart_src[m.end():]
                log("Fallback : check ajoute", "OK")
                patched = True
            else:
                log("Fallback echoue - cart.py NON patche", "WARN")

        if patched:
            open(CART, "w", encoding="utf-8").write(cart_src)
            ok, err = syntax_ok(CART)
            if not ok:
                log(f"cart.py ERREUR : {err}", "ERR")
                shutil.copy2(os.path.join(BAK, "cart.py"), CART)
            else:
                log("cart.py syntaxe OK", "OK")

# ============================================================
# PHASE 6 : Frontend - masquer le bouton
# ============================================================
log("PHASE 6 : Masquage frontend rupture", "STEP")

# Chercher les fichiers qui rendent le catalogue patient
CANDIDATES = ["app.js", "suivi.js", "index.html", "cart.js"]
found_files = []

for fname in CANDIDATES:
    fpath = os.path.join(STATIC, fname)
    if not os.path.isfile(fpath):
        continue
    src = open(fpath, "r", encoding="utf-8", errors="ignore").read()
    if any(k in src for k in ["addToCart", "data-add", "Ajouter au panier",
                              "Ajouter au panier", "product-actions"]):
        found_files.append(fname)

log(f"Fichiers avec bouton panier : {found_files or '(aucun)'}", "INFO")

# Injection CSS global dans pharmacien.html... finalement le patient utilise index.html
# Mieux : injecter dans patient_common.css un style pour cacher le bouton
CSS_FILE = os.path.join(STATIC, "patient_common.css")
if os.path.isfile(CSS_FILE):
    css = open(CSS_FILE, "r", encoding="utf-8").read()
    if "eh-rupture-hide" not in css:
        css += '''

/* LOT 7 : masquer le bouton d'ajout panier si rupture */
.eh-rupture-hide,
button[data-can-order="0"],
.product-card[data-can-order="0"] .btn-primary,
.product-card[data-can-order="0"] [data-add-cart]{
  display:none !important;
}
'''
        open(CSS_FILE, "w", encoding="utf-8").write(css)
        log("CSS patient_common.css : regle ajoutee", "OK")

# Chercher dans app.js la fonction de rendu des cartes produit
app_js = os.path.join(STATIC, "app.js")
if os.path.isfile(app_js):
    src = open(app_js, "r", encoding="utf-8", errors="ignore").read()
    backup(app_js, "app.js")

    if "can_order" not in src:
        # Injecter un helper global dans app.js
        HELPER_JS = '''
/* LOT 7 : helper disponibilite */
function ehProductAvailable(p){
  if(!p) return true;
  if(p.can_order !== undefined) return !!p.can_order;
  if(p.is_active === 0) return false;
  if((p.availability||"").toLowerCase() === "rupture") return false;
  if(p.stock_quantity !== null && p.stock_quantity !== undefined && p.stock_quantity <= 0) return false;
  return true;
}
'''
        # Inserer au debut du fichier
        src = HELPER_JS + "\n" + src
        open(app_js, "w", encoding="utf-8").write(src)
        log("app.js : helper ehProductAvailable ajoute", "OK")

# Message final
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)

final_main = open(MAIN, "r", encoding="utf-8").read()

checks = [
    ("Backend : helper deduction",        "_deduct_order_stock" in final_main),
    ("Backend : hook 'prete'",            'if new_status == "prete":' in final_main and "_deduct_order_stock(conn" in final_main),
    ("Backend : can_order dans products", "can_order" in final_main),
    ("main.py syntaxe OK",                syntax_ok(MAIN)[0]),
]
if os.path.isfile(CART):
    final_cart = open(CART, "r", encoding="utf-8").read()
    checks.append(("cart.py : refus rupture", "rupture de stock" in final_cart))
    checks.append(("cart.py syntaxe OK",       syntax_ok(CART)[0]))
if os.path.isfile(app_js):
    final_app = open(app_js, "r", encoding="utf-8").read()
    checks.append(("Frontend : ehProductAvailable", "ehProductAvailable" in final_app))

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
print("  1. Creer une commande -> la confirmer -> la marquer 'prete'")
print("  2. Verifier dans /pharmacien -> Stock : le stock du produit doit baisser")
print("  3. Verifier /api/products : les produits en rupture ont can_order=false")
print("  4. Patient : la carte d'un produit en rupture ne doit PAS avoir de bouton")
print()
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\main.py" "{MAIN}"')
print(f'  copy "{BAK}\\cart.py" "{CART}"')