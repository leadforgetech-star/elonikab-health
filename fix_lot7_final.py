# -*- coding: utf-8 -*-
"""
Lot 7 - Fix final : stock negatif + limite quantite client + affichage statut
"""
import os, re, sqlite3, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
MAIN = os.path.join(ROOT, "main.py")
CART = os.path.join(ROOT, "v3_modules", "cart.py")
APPJS = os.path.join(ROOT, "static", "app.js")
DB = os.path.join(ROOT, "database.db")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_lot7final_{TS}")
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

for p, n in [(MAIN, "main.py"), (CART, "cart.py"), (APPJS, "app.js"), (DB, "database.db")]:
    if os.path.isfile(p):
        shutil.copy2(p, os.path.join(BAK, n))

print("=" * 78)
print(f"LOT 7 FINAL - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

# ============================================================
# PHASE 1 : Corriger les stocks negatifs existants
# ============================================================
log("PHASE 1 : Correction stocks negatifs", "STEP")

conn = sqlite3.connect(DB)
cur = conn.cursor()
negatives = cur.execute("SELECT id, name, stock_quantity FROM products WHERE stock_quantity < 0").fetchall()
print(f"  {len(negatives)} produit(s) avec stock negatif :")
for pid, name, sq in negatives:
    print(f"    id={pid} '{name}' stock={sq}")

if negatives:
    cur.execute("UPDATE products SET stock_quantity = 0 WHERE stock_quantity < 0")
    conn.commit()
    log(f"{len(negatives)} produit(s) corrige(s) a 0", "OK")
else:
    log("Aucun stock negatif", "OK")

conn.close()

# ============================================================
# PHASE 2 : Limite quantite client (cart.py)
# ============================================================
log("PHASE 2 : Limite quantite client", "STEP")

if not os.path.isfile(CART):
    log("cart.py introuvable", "ERR")
else:
    cart_src = open(CART, "r", encoding="utf-8").read()

    # Etape A : enrichir le SELECT pour recuperer stock_quantity
    if "stock_quantity, availability FROM products" not in cart_src:
        # SELECT deja enrichi ?
        old_sel = 'SELECT id, is_active FROM products WHERE id = ?'
        new_sel = 'SELECT id, is_active, stock_quantity, availability FROM products WHERE id = ?'
        if old_sel in cart_src:
            cart_src = cart_src.replace(old_sel, new_sel, 1)
            log("SELECT enrichi (stock_quantity)", "OK")

    # Etape B : ajouter le check de quantite max
    OLD_CHECK = '''            if prod["is_active"] == 0:
                raise HTTPException(400, "Produit indisponible")

            # LOT 7 : refus si rupture
            _avail = (prod["availability"] or "").lower()
            _sq = prod["stock_quantity"]
            if _avail == "rupture":
                raise HTTPException(400, "Produit en rupture de stock")
            if _sq is not None and _sq <= 0:
                raise HTTPException(400, "Produit en rupture de stock")

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

            cart = _get_or_create_cart(conn, user["id"])

            # LOT 7 : verifier que la quantite totale ne depasse pas le stock
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

    if "Quantite insuffisante" in cart_src:
        log("Check quantite deja present", "WARN")
    elif OLD_CHECK in cart_src:
        cart_src = cart_src.replace(OLD_CHECK, NEW_CHECK, 1)
        open(CART, "w", encoding="utf-8").write(cart_src)
        ok, err = syntax_ok(CART)
        if not ok:
            log(f"cart.py ERREUR : {err}", "ERR")
            shutil.copy2(os.path.join(BAK, "cart.py"), CART)
        else:
            log("Check quantite max ajoute", "OK")
    else:
        log("Pattern check introuvable", "WARN")

    # Etape C : check aussi sur PATCH update_item
    if "PATCH" not in cart_src or "Quantite insuffisante" not in open(CART, "r", encoding="utf-8").read():
        log("PATCH a patcher manuellement (skip)", "WARN")

# ============================================================
# PHASE 3 : Frontend - badge + limite input
# ============================================================
log("PHASE 3 : Frontend badge + limite", "STEP")

if not os.path.isfile(APPJS):
    log("app.js introuvable", "ERR")
else:
    app_src = open(APPJS, "r", encoding="utf-8").read()

    # Injecter un helper global qui :
    # 1. Rend le badge de dispo
    # 2. Bloque l'ajout si rupture
    # 3. Limite la quantite
    HELPER = '''
/* ============================================================
   LOT 7 : Gestion disponibilite produit (rupture / stock)
   ============================================================ */
(function(){
  if (window.__ehLot7Installed) return;
  window.__ehLot7Installed = true;

  // Helper : produit commandable ?
  window.ehProductAvailable = function(p){
    if (!p) return true;
    if (p.can_order === false) return false;
    if (p.client_availability === "rupture") return false;
    if (p.is_active === 0) return false;
    var sq = p.stock_quantity;
    if (sq !== null && sq !== undefined && sq <= 0) return false;
    return true;
  };

  // Helper : libelle du badge
  window.ehProductBadge = function(p){
    if (!p) return null;
    if (p.is_active === 0) return { label: "Indisponible", cls: "eh-badge-muted" };
    if (p.client_availability === "rupture") return { label: "Rupture de stock", cls: "eh-badge-danger" };
    var sq = p.stock_quantity;
    if (sq !== null && sq !== undefined && sq <= 5) return { label: "Stock faible (" + sq + ")", cls: "eh-badge-warn" };
    return { label: "Disponible", cls: "eh-badge-ok" };
  };

  // Intercepte les clics sur les boutons "Ajouter au panier" pour produits en rupture
  document.addEventListener("click", function(ev){
    var btn = ev.target.closest ? ev.target.closest("[data-add-cart], [data-add]") : null;
    if (!btn) return;
    var pid = btn.getAttribute("data-add-cart") || btn.getAttribute("data-add");
    if (!pid) return;
    // Charger le produit pour verifier
    fetch("/api/products/" + pid, { credentials: "same-origin" })
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(p){
        if (!p) return;
        if (!window.ehProductAvailable(p)) {
          ev.preventDefault();
          ev.stopPropagation();
          var msg = (p.client_availability === "rupture") ? "Produit en rupture de stock" : "Produit indisponible";
          if (window.EHModal) window.EHModal.alert("Indisponible", msg, "danger");
          else alert(msg);
        }
      })
      .catch(function(){});
  }, true);

  // Intercepte les inputs de quantite pour ne pas depasser le stock
  document.addEventListener("input", function(ev){
    var inp = ev.target;
    if (!inp || inp.tagName !== "INPUT") return;
    var max = parseInt(inp.getAttribute("data-max-qty") || "0", 10);
    if (!max) return;
    var val = parseInt(inp.value || "0", 10);
    if (val > max) {
      inp.value = String(max);
      if (window.EHModal) window.EHModal.alert("Quantite limitee", "Maximum : " + max + " (stock disponible)", "warn");
      else alert("Maximum : " + max);
    }
  });

  // CSS pour badges
  var style = document.createElement("style");
  style.textContent = [
    ".eh-badge{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.04em}",
    ".eh-badge-ok{background:#E6F7F1;color:#0A7A5A}",
    ".eh-badge-warn{background:#FFF4E0;color:#B26B00}",
    ".eh-badge-danger{background:#FDECEC;color:#B23C3C}",
    ".eh-badge-muted{background:#E2E8F0;color:#475569}",
    ".eh-product-unavailable{opacity:.55;filter:grayscale(.3)}",
    ".eh-product-unavailable .btn-primary, .eh-product-unavailable [data-add-cart], .eh-product-unavailable [data-add]{display:none !important}"
  ].join("");
  document.head.appendChild(style);
})();
'''

    if "__ehLot7Installed" in app_src:
        log("Frontend helper deja present", "WARN")
    else:
        # Inserer au debut
        app_src = HELPER + "\n" + app_src
        open(APPJS, "w", encoding="utf-8").write(app_src)
        log("Helper frontend injecte dans app.js", "OK")

# ============================================================
# Verification
# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)

conn = sqlite3.connect(DB)
n_neg = conn.execute("SELECT COUNT(*) FROM products WHERE stock_quantity < 0").fetchone()[0]
n_zero = conn.execute("SELECT COUNT(*) FROM products WHERE stock_quantity = 0").fetchone()[0]
n_pos = conn.execute("SELECT COUNT(*) FROM products WHERE stock_quantity > 0").fetchone()[0]
n_null = conn.execute("SELECT COUNT(*) FROM products WHERE stock_quantity IS NULL").fetchone()[0]
conn.close()

final_cart = open(CART, "r", encoding="utf-8").read() if os.path.isfile(CART) else ""
final_app = open(APPJS, "r", encoding="utf-8").read() if os.path.isfile(APPJS) else ""

checks = [
    ("Plus de stock negatif",        n_neg == 0),
    (f"Stock=0 : {n_zero}",           True),
    (f"Stock>0 : {n_pos}",            True),
    (f"Stock NULL : {n_null}",        True),
    ("cart.py : check quantite",      "Quantite insuffisante" in final_cart),
    ("cart.py syntaxe OK",            syntax_ok(CART)[0] if os.path.isfile(CART) else False),
    ("app.js : helper ehProduct",     "ehProductAvailable" in final_app),
    ("app.js : badge helper",         "ehProductBadge" in final_app),
    ("app.js : blocage rupture",      "Produit en rupture de stock" in final_app),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

print()
print(f"[BACKUP] {BAK}")
print()
print("[CMD] Restart Uvicorn (reload actif) :")
print("  Ctrl+C dans le terminal Uvicorn, puis relancer :")
print("  python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir v3_modules --reload-dir static")
print()
print("[TEST]")
print("  1) /api/products : stock negatif disparu, badges presents")
print("  2) Patient : essayer commande de 10 sur produit stock=3 -> erreur")
print("  3) Patient : produit rupture -> bouton masque")
print()
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\main.py" "{MAIN}"')
print(f'  copy "{BAK}\\cart.py" "{CART}"')
print(f'  copy "{BAK}\\app.js" "{APPJS}"')
print(f'  copy "{BAK}\\database.db" "{DB}"')