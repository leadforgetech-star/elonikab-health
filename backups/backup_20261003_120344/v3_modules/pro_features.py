"""Fonctionnalites pro : WhatsApp + Reorder (V3 extension)."""
from datetime import datetime

from fastapi import Depends, HTTPException


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


def install_pro_features(app, get_db, require_role):
    """Enregistre les routes /api/pro/whatsapp-info et /api/orders/{ref}/reorder."""

    @app.get("/api/pro/whatsapp-info")
    def whatsapp_info(user=Depends(require_role("PROFESSIONNEL", "PATIENT", "ADMIN", "PHARMACIEN"))):
        """Retourne le numero WhatsApp config + le nom de la structure du user."""
        conn = get_db()
        try:
            settings = conn.execute(
                "SELECT pharmacy_name, whatsapp_number, pharmacy_phone FROM pharmacy_settings WHERE id = 1"
            ).fetchone()
            whatsapp = ""
            pharmacy_name = "Elokinab Health"
            if settings:
                whatsapp = (settings["whatsapp_number"] or "").strip()
                if not whatsapp:
                    whatsapp = (settings["whatsapp_number"] or "").strip()
                if not whatsapp:
                    whatsapp = (settings["pharmacy_phone"] or "").strip()
                if not whatsapp:
                    whatsapp = "+22871039904"
                if settings["pharmacy_name"]:
                    pharmacy_name = settings["pharmacy_name"]

            structure_name = ""
            if user["role"] == "PROFESSIONNEL":
                prof = conn.execute(
                    "SELECT structure_name FROM professional_profiles WHERE user_id = ?",
                    (user["id"],),
                ).fetchone()
                if prof:
                    structure_name = prof["structure_name"] or ""
            if not structure_name:
                structure_name = user.get("full_name") or ""
        finally:
            conn.close()
        return {
            "whatsapp_number": whatsapp,
            "pharmacy_name": pharmacy_name,
            "structure_name": structure_name,
        }

    @app.post("/api/orders/{reference}/reorder")
    def reorder(reference: str, user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        """Recharge le panier avec les produits d'une commande passee."""
        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE reference = ? AND user_id = ?",
                (reference, user["id"]),
            ).fetchone()
            if order is None:
                raise HTTPException(404, "Commande introuvable")

            # Recuperer les lignes
            items = conn.execute(
                "SELECT product_id, quantity FROM order_items WHERE order_id = ?",
                (order["id"],),
            ).fetchall()

            # Si pas d'order_items (commande V1), utiliser product_id direct
            if not items:
                if order["product_id"]:
                    items = [{"product_id": order["product_id"], "quantity": order["quantity"] or 1}]

            if not items:
                raise HTTPException(400, "Aucun produit dans cette commande")

            cart = _get_or_create_cart(conn, user["id"])
            now = datetime.now().isoformat(timespec="seconds")
            added = 0
            skipped = 0

            for it in items:
                pid = it["product_id"]
                qty = it["quantity"] or 1
                # Verifier produit actif et existant
                prod = conn.execute(
                    "SELECT id, is_active FROM products WHERE id = ?", (pid,)
                ).fetchone()
                if prod is None or prod["is_active"] == 0:
                    skipped += 1
                    continue

                existing = conn.execute(
                    "SELECT id, quantity FROM cart_items WHERE cart_id = ? AND product_id = ?",
                    (cart["id"], pid),
                ).fetchone()
                if existing:
                    conn.execute(
                        "UPDATE cart_items SET quantity = quantity + ?, updated_at = ?"
                        " WHERE id = ?",
                        (qty, now, existing["id"]),
                    )
                else:
                    conn.execute(
                        "INSERT INTO cart_items (cart_id, product_id, quantity,"
                        " created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                        (cart["id"], pid, qty, now, now),
                    )
                added += 1

            conn.execute("UPDATE carts SET updated_at = ? WHERE id = ?", (now, cart["id"]))
            conn.commit()

            # Retourner le panier a jour
            cart_data = conn.execute(
                "SELECT ci.id, ci.product_id, ci.quantity, p.name AS product_name,"
                " p.presentation, p.price, (ci.quantity * p.price) AS line_total"
                " FROM cart_items ci JOIN products p ON p.id = ci.product_id"
                " WHERE ci.cart_id = ? ORDER BY ci.id",
                (cart["id"],),
            ).fetchall()
            items_list = [_row(i) for i in cart_data]
            subtotal = sum((i["line_total"] or 0) for i in items_list)
        finally:
            conn.close()

        return {
            "added": added,
            "skipped": skipped,
            "cart": {
                "items": items_list,
                "item_count": sum(i["quantity"] for i in items_list),
                "subtotal": round(subtotal, 2),
            },
        }


