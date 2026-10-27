"""
v3_install_phase4.py - Panier multi-produits.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
MIGR = BASE / "v3_modules" / "migrations.py"
MODULES = BASE / "v3_modules"
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_v3_p4_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAIN, backup / "main.py")
shutil.copy2(MIGR, backup / "migrations.py")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. Ajout des tables carts / cart_items dans migrations.py
# ============================================================
mig = MIGR.read_text(encoding="utf-8")
if "CREATE TABLE IF NOT EXISTS carts" not in mig:
    add = '''    """CREATE TABLE IF NOT EXISTS carts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS cart_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cart_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id),
        UNIQUE (cart_id, product_id)
    )""",
    """CREATE INDEX IF NOT EXISTS idx_cart_items_cart ON cart_items(cart_id)""",
'''
    mig = mig.replace("]\n\n\nORDERS_NEW_COLS", add + "]\n\n\nORDERS_NEW_COLS", 1)
    if "CREATE TABLE IF NOT EXISTS carts" not in mig:
        # fallback : insere avant la fermeture de SCHEMA_V3
        mig = mig.replace('    """CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)""",\n]',
                          '    """CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)""",\n' + add + ']', 1)
    MIGR.write_text(mig, encoding="utf-8")
    print("[OK] migrations.py -> carts + cart_items")
else:
    print("[i] migrations.py deja a jour")

# ============================================================
# 2. v3_modules/cart.py
# ============================================================
CART = '''"""Panier multi-produits + commande multi-lignes (Phase 4)."""
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel


class AddItemRequest(BaseModel):
    product_id: int
    quantity: int = 1


class UpdateItemRequest(BaseModel):
    quantity: int


class OrderFromCartRequest(BaseModel):
    delivery_mode: str  # "retrait" | "livraison"
    address: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_accuracy: Optional[float] = None
    prescription_file: str = ""
    customer_name: str = ""
    phone: str = ""


def _row(r):
    return {k: r[k] for k in r.keys()} if r else None


def _get_or_create_cart(conn, user_id):
    row = conn.execute("SELECT * FROM carts WHERE user_id = ?", (user_id,)).fetchone()
    if row:
        return row
    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        "INSERT INTO carts (user_id, created_at, updated_at) VALUES (?, ?, ?)",
        (user_id, now, now),
    )
    conn.commit()
    return conn.execute("SELECT * FROM carts WHERE id = ?", (cur.lastrowid,)).fetchone()


def _cart_payload(conn, cart_id):
    items = conn.execute(
        "SELECT ci.id, ci.product_id, ci.quantity,"
        " p.name AS product_name, p.presentation, p.price,"
        " p.availability, p.image_url, p.is_active,"
        " (ci.quantity * p.price) AS line_total"
        " FROM cart_items ci JOIN products p ON p.id = ci.product_id"
        " WHERE ci.cart_id = ? ORDER BY ci.id",
        (cart_id,),
    ).fetchall()
    items_list = [_row(i) for i in items]
    subtotal = sum((i["line_total"] or 0) for i in items_list)
    return {
        "items": items_list,
        "item_count": sum(i["quantity"] for i in items_list),
        "subtotal": round(subtotal, 2),
    }


def install_cart(app, get_db, require_role, compute_delivery_fee):
    """Install cart + order-from-cart routes."""

    # ---- Routes panier ----

    @app.get("/api/cart")
    def get_cart(user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        conn = get_db()
        try:
            cart = _get_or_create_cart(conn, user["id"])
            return _cart_payload(conn, cart["id"])
        finally:
            conn.close()

    @app.post("/api/cart/items")
    def add_item(payload: AddItemRequest,
                 user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        if payload.quantity < 1:
            raise HTTPException(400, "Quantite invalide")
        conn = get_db()
        try:
            prod = conn.execute(
                "SELECT id, is_active FROM products WHERE id = ?",
                (payload.product_id,),
            ).fetchone()
            if prod is None:
                raise HTTPException(404, "Produit introuvable")
            if prod["is_active"] == 0:
                raise HTTPException(400, "Produit indisponible")
            cart = _get_or_create_cart(conn, user["id"])
            now = datetime.now().isoformat(timespec="seconds")
            existing = conn.execute(
                "SELECT id, quantity FROM cart_items WHERE cart_id = ? AND product_id = ?",
                (cart["id"], payload.product_id),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE cart_items SET quantity = quantity + ?, updated_at = ? WHERE id = ?",
                    (payload.quantity, now, existing["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO cart_items (cart_id, product_id, quantity, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (cart["id"], payload.product_id, payload.quantity, now, now),
                )
            conn.execute("UPDATE carts SET updated_at = ? WHERE id = ?", (now, cart["id"]))
            conn.commit()
            return _cart_payload(conn, cart["id"])
        finally:
            conn.close()

    @app.patch("/api/cart/items/{item_id}")
    def update_item(item_id: int, payload: UpdateItemRequest,
                    user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        if payload.quantity < 0:
            raise HTTPException(400, "Quantite invalide")
        conn = get_db()
        try:
            cart = _get_or_create_cart(conn, user["id"])
            row = conn.execute(
                "SELECT id FROM cart_items WHERE id = ? AND cart_id = ?",
                (item_id, cart["id"]),
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Article introuvable")
            now = datetime.now().isoformat(timespec="seconds")
            if payload.quantity == 0:
                conn.execute("DELETE FROM cart_items WHERE id = ?", (item_id,))
            else:
                conn.execute(
                    "UPDATE cart_items SET quantity = ?, updated_at = ? WHERE id = ?",
                    (payload.quantity, now, item_id),
                )
            conn.execute("UPDATE carts SET updated_at = ? WHERE id = ?", (now, cart["id"]))
            conn.commit()
            return _cart_payload(conn, cart["id"])
        finally:
            conn.close()

    @app.delete("/api/cart/items/{item_id}")
    def delete_item(item_id: int,
                    user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        conn = get_db()
        try:
            cart = _get_or_create_cart(conn, user["id"])
            conn.execute(
                "DELETE FROM cart_items WHERE id = ? AND cart_id = ?",
                (item_id, cart["id"]),
            )
            conn.commit()
            return _cart_payload(conn, cart["id"])
        finally:
            conn.close()

    @app.delete("/api/cart")
    def clear_cart(user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        conn = get_db()
        try:
            cart = _get_or_create_cart(conn, user["id"])
            conn.execute("DELETE FROM cart_items WHERE cart_id = ?", (cart["id"],))
            conn.commit()
            return _cart_payload(conn, cart["id"])
        finally:
            conn.close()

    # ---- Commande depuis le panier ----

    @app.post("/api/orders/v2")
    def create_order_from_cart(payload: OrderFromCartRequest,
                               user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        import uuid
        if payload.delivery_mode not in ("retrait", "livraison"):
            raise HTTPException(400, "Mode invalide")

        conn = get_db()
        try:
            cart = _get_or_create_cart(conn, user["id"])
            cart_data = _cart_payload(conn, cart["id"])
            if not cart_data["items"]:
                raise HTTPException(400, "Panier vide")

            # Un professionnel doit avoir un profil approuve
            if user["role"] == "PROFESSIONNEL":
                pro = conn.execute(
                    "SELECT status FROM professional_profiles WHERE user_id = ?",
                    (user["id"],),
                ).fetchone()
                if pro is None or pro["status"] != "APPROVED":
                    raise HTTPException(403, "Compte professionnel non approuve")

            # Verifier produits actifs
            for it in cart_data["items"]:
                if it["is_active"] == 0:
                    raise HTTPException(400, "Produit inactif : " + it["product_name"])

            has_gps = payload.latitude is not None and payload.longitude is not None
            if payload.delivery_mode == "livraison" and not payload.address.strip() and not has_gps:
                raise HTTPException(400, "Adresse ou GPS obligatoire pour la livraison")

            # Frais
            if payload.delivery_mode == "livraison":
                delivery_fee, delivery_distance = compute_delivery_fee(
                    payload.latitude, payload.longitude
                )
            else:
                delivery_fee, delivery_distance = 0.0, None

            subtotal = round(cart_data["subtotal"], 2)
            total = round(subtotal + delivery_fee, 2)

            customer_type = "PROFESSIONNEL" if user["role"] == "PROFESSIONNEL" else "PARTICULIER"
            vehicle_type = "VOITURE" if customer_type == "PROFESSIONNEL" else "MOTO"

            ref = "CMD-" + datetime.now().strftime("%y%m%d") + "-" + uuid.uuid4().hex[:6].upper()
            now = datetime.now().isoformat(timespec="seconds")

            # Ligne "resume" dans orders (compat V1/V2)
            first = cart_data["items"][0]
            cur = conn.execute(
                "INSERT INTO orders (reference, customer_name, phone, product_id,"
                " product_name, quantity, delivery_mode, address, prescription_file,"
                " status, created_at, latitude, longitude, location_accuracy,"
                " delivery_fee, delivery_distance_km, price, subtotal,"
                " user_id, customer_type, delivery_vehicle_type)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'en_attente', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ref,
                    (payload.customer_name or user["full_name"] or "Client").strip(),
                    (payload.phone or user["phone"] or "").strip(),
                    first["product_id"], first["product_name"],
                    first["quantity"],
                    payload.delivery_mode, payload.address.strip(),
                    payload.prescription_file,
                    now,
                    payload.latitude, payload.longitude, payload.location_accuracy,
                    delivery_fee, delivery_distance,
                    first["price"], subtotal,
                    user["id"], customer_type, vehicle_type,
                ),
            )
            order_id = cur.lastrowid

            for it in cart_data["items"]:
                conn.execute(
                    "INSERT INTO order_items (order_id, product_id, product_name,"
                    " unit_price, quantity, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
                    (order_id, it["product_id"], it["product_name"],
                     it["price"], it["quantity"], it["line_total"]),
                )

            conn.execute("DELETE FROM cart_items WHERE cart_id = ?", (cart["id"],))
            conn.commit()

            row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
            items = conn.execute(
                "SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,)
            ).fetchall()
        finally:
            conn.close()

        result = _row(row)
        result["items"] = [_row(i) for i in items]
        return result

    @app.get("/api/orders/{reference}/items")
    def get_order_items(reference: str):
        conn = get_db()
        try:
            o = conn.execute(
                "SELECT id FROM orders WHERE reference = ?", (reference,)
            ).fetchone()
            if o is None:
                raise HTTPException(404, "Commande introuvable")
            items = conn.execute(
                "SELECT * FROM order_items WHERE order_id = ? ORDER BY id",
                (o["id"],),
            ).fetchall()
        finally:
            conn.close()
        return [_row(i) for i in items]


'''
(MODULES / "cart.py").write_text(CART, encoding="utf-8")
print("[OK] v3_modules/cart.py")

# ============================================================
# 3. Patch main.py
# ============================================================
src = MAIN.read_text(encoding="utf-8")
if "install_cart" not in src:
    old = "install_professionals(app, get_db, require_role)"
    new = (old + "\n"
           "from v3_modules.cart import install_cart\n"
           "install_cart(app, get_db, require_role, compute_delivery_fee)")
    if old in src:
        src = src.replace(old, new, 1)
        print("[OK] main.py -> install_cart branche")
    else:
        print("[!] anchor install_professionals introuvable")
    MAIN.write_text(src, encoding="utf-8")
else:
    print("[i] main.py deja patche Phase 4")

# ============================================================
# 4. Frontend panier
# ============================================================
CART_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mon panier - Elokinab Health</title>
<link rel="stylesheet" href="/static/auth.css">
<style>
  .auth-card{max-width:640px}
  .cart-item{
    display:flex;gap:12px;align-items:center;padding:12px;
    border:1px solid #ddece6;border-radius:12px;margin-bottom:10px;
  }
  .cart-thumb{
    width:56px;height:56px;border-radius:10px;background:#f0f7f3;
    display:flex;align-items:center;justify-content:center;
    color:#0f9d76;font-weight:800;overflow:hidden;flex-shrink:0;
  }
  .cart-thumb img{width:100%;height:100%;object-fit:contain}
  .cart-info{flex:1;min-width:0}
  .cart-name{font-weight:700;font-size:14px}
  .cart-meta{font-size:12px;color:#6c8a80}
  .cart-price{font-weight:700;color:#0a7a5a;font-size:13px;margin-top:4px}
  .qty{
    display:flex;align-items:center;gap:6px;
  }
  .qty button{
    width:28px;height:28px;border:1px solid #ddece6;border-radius:8px;
    background:#fff;cursor:pointer;font-weight:700;
  }
  .qty input{
    width:44px;text-align:center;padding:6px;border:1px solid #ddece6;
    border-radius:8px;font-family:inherit;
  }
  .cart-actions{display:flex;gap:8px;margin-top:16px;flex-wrap:wrap}
  .btn-ghost{
    background:#fff;border:1px solid #ddece6;color:#0f2620;padding:10px 16px;
    border-radius:10px;font-weight:700;cursor:pointer;text-decoration:none;
    display:inline-block;font-size:14px;
  }
  .btn-ghost:hover{border-color:#0f9d76;color:#0a7a5a}
  .cart-total{
    background:#e8f7f1;border:1px solid #c7e9dc;border-radius:12px;
    padding:14px;margin-top:14px;font-weight:700;font-size:15px;color:#0a7a5a;
    display:flex;justify-content:space-between;
  }
  .empty-cart{text-align:center;padding:30px;color:#6c8a80}
</style>
</head>
<body class="auth-body">
<div class="auth-card">
  <div class="auth-logo">
    <div class="auth-logo-mark">+</div>
    <div class="auth-logo-text">
      <strong>Elokinab Health</strong>
      <small>Mon panier</small>
    </div>
  </div>
  <h1>Mon panier</h1>
  <p class="sub">Ajoutez, modifiez ou retirez des produits.</p>
  <div id="msg" class="auth-msg hidden"></div>
  <div id="cart-body"></div>
  <div id="cart-total" class="cart-total hidden">
    <span>Sous-total</span><span id="subtotal">0 FCFA</span>
  </div>
  <div class="cart-actions">
    <a class="btn-ghost" href="/">← Continuer mes achats</a>
    <button class="auth-btn" id="checkout" style="flex:1;min-width:160px">Commander</button>
  </div>
</div>
<script src="/static/cart.js"></script>
</body>
</html>
'''
(STATIC / "cart.html").write_text(CART_HTML, encoding="utf-8")
print("[OK] static/cart.html")

CART_JS = '''(function () {
  function $(id) { return document.getElementById(id); }
  function money(v) { return Math.round(Number(v) || 0).toLocaleString("fr-FR") + " FCFA"; }
  function showMsg(t) { var m = $("msg"); m.textContent = t; m.className = "auth-msg"; }
  function hideMsg() { var m = $("msg"); m.className = "auth-msg hidden"; }

  function call(method, path, body) {
    return fetch(path, {
      method: method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    });
  }

  function render(data) {
    var box = $("cart-body");
    box.innerHTML = "";
    if (!data.items || data.items.length === 0) {
      box.innerHTML = '<div class="empty-cart">Votre panier est vide.</div>';
      $("cart-total").classList.add("hidden");
      return;
    }
    data.items.forEach(function (it) {
      var card = document.createElement("div");
      card.className = "cart-item";

      var thumb = document.createElement("div");
      thumb.className = "cart-thumb";
      if (it.image_url) {
        var img = document.createElement("img");
        img.src = it.image_url;
        img.alt = it.product_name;
        img.onerror = function () { img.remove(); thumb.textContent = it.product_name.charAt(0); };
        thumb.appendChild(img);
      } else {
        thumb.textContent = it.product_name.charAt(0);
      }

      var info = document.createElement("div");
      info.className = "cart-info";
      info.innerHTML = '<div class="cart-name">' + it.product_name + '</div>' +
        '<div class="cart-meta">' + (it.presentation || "") + '</div>' +
        '<div class="cart-price">' + money(it.price) + ' × ' + it.quantity +
        ' = ' + money(it.line_total) + '</div>';

      var qty = document.createElement("div");
      qty.className = "qty";
      var minus = document.createElement("button"); minus.textContent = "−";
      var input = document.createElement("input"); input.type = "number";
      input.value = it.quantity; input.min = "1";
      var plus = document.createElement("button"); plus.textContent = "+";
      minus.onclick = function () { setQty(it.id, Math.max(1, it.quantity - 1)); };
      plus.onclick = function () { setQty(it.id, it.quantity + 1); };
      input.onchange = function () { setQty(it.id, Math.max(1, parseInt(input.value) || 1)); };

      var del = document.createElement("button");
      del.textContent = "✕";
      del.style.cssText = "background:none;border:0;color:#b23c3c;font-size:18px;cursor:pointer;padding:0 4px";
      del.onclick = function () { removeItem(it.id); };

      qty.appendChild(minus); qty.appendChild(input); qty.appendChild(plus);

      card.appendChild(thumb);
      card.appendChild(info);
      card.appendChild(qty);
      card.appendChild(del);
      box.appendChild(card);
    });
    $("subtotal").textContent = money(data.subtotal);
    $("cart-total").classList.remove("hidden");
  }

  function load() {
    hideMsg();
    call("GET", "/api/cart").then(render).catch(function (e) {
      if (String(e.message).indexOf("Non authentifie") >= 0) {
        window.location.href = "/static/login.html";
      } else {
        showMsg(e.message);
      }
    });
  }

  function setQty(id, q) {
    call("PATCH", "/api/cart/items/" + id, { quantity: q }).then(render).catch(function (e) {
      showMsg(e.message);
    });
  }

  function removeItem(id) {
    call("DELETE", "/api/cart/items/" + id).then(render).catch(function (e) {
      showMsg(e.message);
    });
  }

  function checkout() {
    var mode = prompt("Mode de livraison ? Tapez : retrait ou livraison", "retrait");
    if (!mode) return;
    mode = mode.trim().toLowerCase();
    if (mode !== "retrait" && mode !== "livraison") {
      showMsg("Mode invalide");
      return;
    }
    var payload = { delivery_mode: mode };
    if (mode === "livraison") {
      var addr = prompt("Adresse de livraison ?", "");
      payload.address = (addr || "").trim();
      if (!payload.address) {
        var gps = confirm("Pas d'adresse. Utiliser votre GPS actuel ?");
        if (gps && navigator.geolocation) {
          navigator.geolocation.getCurrentPosition(function (pos) {
            payload.latitude = pos.coords.latitude;
            payload.longitude = pos.coords.longitude;
            payload.location_accuracy = pos.coords.accuracy;
            sendOrder(payload);
          }, function () { showMsg("GPS indisponible"); });
          return;
        }
        showMsg("Adresse ou GPS obligatoire");
        return;
      }
    }
    sendOrder(payload);
  }

  function sendOrder(payload) {
    call("POST", "/api/orders/v2", payload).then(function (o) {
      alert("Commande creee : " + o.reference);
      window.location.href = "/suivi?ref=" + encodeURIComponent(o.reference);
    }).catch(function (e) {
      showMsg(e.message);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    load();
    $("checkout").addEventListener("click", checkout);
  });
})();
'''
(STATIC / "cart.js").write_text(CART_JS, encoding="utf-8")
print("[OK] static/cart.js")

print()
print("=" * 60)
print("PHASE 4 installee.")
print("=" * 60)
print("Routes ajoutees :")
print("  GET    /api/cart")
print("  POST   /api/cart/items")
print("  PATCH  /api/cart/items/{id}")
print("  DELETE /api/cart/items/{id}")
print("  DELETE /api/cart")
print("  POST   /api/orders/v2          (commande multi-lignes)")
print("  GET    /api/orders/{ref}/items")
print()
print("Frontend : /static/cart.html")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  python main.py")
print("  python test_phase4.py   (dans un autre CMD)")