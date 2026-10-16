"""Panier multi-produits + commande multi-lignes (Phase 4)."""
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
                new_qty = existing["quantity"] + payload.quantity
                conn.execute(
                    "UPDATE cart_items SET quantity = ?, updated_at = ? WHERE id = ?",
                    (new_qty, now, existing["id"]),
                )
            else:
                new_qty = payload.quantity
                conn.execute(
                    "INSERT INTO cart_items (cart_id, product_id, quantity, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (cart["id"], payload.product_id, payload.quantity, now, now),
                )
            conn.execute("UPDATE carts SET updated_at = ? WHERE id = ?", (now, cart["id"]))
            conn.commit()
            # === OPTIMISATION : reponse minimale (1 seule requete COUNT) ===
            total = conn.execute(
                "SELECT COALESCE(SUM(quantity), 0) AS n FROM cart_items WHERE cart_id = ?",
                (cart["id"],),
            ).fetchone()["n"]
            return {"ok": True, "item_count": int(total or 0)}
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

            # SSE : notifier les pharmaciens/admins
            try:
                from v3_modules.notifications import push_notification
                _admins = conn.execute(
                    "SELECT id FROM users WHERE role IN ('PHARMACIEN', 'ADMIN')"
                ).fetchall()
                _cname = (payload.customer_name or user["full_name"] or "Client").strip()
                for _a in _admins:
                    push_notification(
                        conn, _a["id"],
                        "Nouvelle commande",
                        str(ref) + " - " + _cname,
                        order_id=order_id,
                    )
                conn.commit()
            except Exception:
                pass

            row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
            items = conn.execute(
                "SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,)
            ).fetchall()
        finally:
            conn.close()

        result = _row(row)
        result["items"] = [_row(i) for i in items]
        # total n'est pas une colonne SQL : on le calcule
        result["total"] = round(subtotal + delivery_fee, 2)
        result["delivery_fee"] = round(delivery_fee, 2)
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


