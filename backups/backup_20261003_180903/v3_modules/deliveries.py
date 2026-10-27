"""Livraison MOTO/VOITURE + dashboards livreur/chauffeur (Phases 7-8)."""
import secrets
from datetime import datetime

from fastapi import Depends, HTTPException
from pydantic import BaseModel

VALID_DRIVER_STATUSES = {
    "ASSIGNED", "ACCEPTED", "PICKED_UP", "IN_DELIVERY",
    "DELIVERED", "FAILED",
}
VALID_DRIVER_TYPES = {"LIVREUR_MOTO", "CHAUFFEUR"}


class AssignRequest(BaseModel):
    driver_id: int


class DriverStatusRequest(BaseModel):
    status: str
    notes: str = ""


def _row(r):
    return {k: r[k] for k in r.keys()} if r else None


def install_deliveries(app, get_db, require_role):
    # ---- Admin / Pharmacien : assignation ----

    @app.post("/api/orders/{reference}/assign")
    def assign_driver(reference: str, payload: AssignRequest,
                      user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE reference = ?", (reference,)
            ).fetchone()
            if order is None:
                raise HTTPException(404, "Commande introuvable")
            if order["delivery_mode"] != "livraison":
                raise HTTPException(400, "Commande non livrable")

            driver = conn.execute(
                "SELECT * FROM drivers WHERE id = ? AND is_active = 1",
                (payload.driver_id,),
            ).fetchone()
            if driver is None:
                raise HTTPException(404, "Livreur introuvable ou inactif")

            now = datetime.now().isoformat(timespec="seconds")
            existing = conn.execute(
                "SELECT id FROM deliveries WHERE order_id = ?", (order["id"],)
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE deliveries SET driver_id=?, assigned_at=?, status='ASSIGNED',"
                    " accepted_at=NULL, picked_up_at=NULL, delivered_at=NULL,"
                    " failed_at=NULL WHERE id=?",
                    (payload.driver_id, now, existing["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO deliveries (order_id, vehicle_type, driver_id,"
                    " status, assigned_at) VALUES (?, ?, ?, 'ASSIGNED', ?)",
                    (order["id"], order["delivery_vehicle_type"] or "MOTO",
                     payload.driver_id, now),
                )
            conn.execute(
                "UPDATE orders SET delivery_status='ASSIGNED' WHERE id=?",
                (order["id"],),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM deliveries WHERE order_id=?", (order["id"],)
            ).fetchone()
        finally:
            conn.close()
        return _row(row)

    # ---- Livreur / Chauffeur : mes livraisons ----

    @app.get("/api/deliveries/mine")
    def my_deliveries(user=Depends(require_role("LIVREUR_MOTO", "CHAUFFEUR"))):
        conn = get_db()
        try:
            # L'utilisateur doit etre lie a un driver via le meme email
            driver = conn.execute(
                "SELECT id FROM drivers WHERE email = ?", (user["email"],)
            ).fetchone()
            if driver is None:
                # fallback : chercher par phone
                driver = conn.execute(
                    "SELECT id FROM drivers WHERE phone = ?", (user["phone"],)
                ).fetchone()
            if driver is None:
                return []
            rows = conn.execute(
                "SELECT d.*, o.reference, o.customer_name, o.phone AS customer_phone,"
                " o.address, o.latitude, o.longitude, o.delivery_mode,"
                " o.total, o.delivery_fee, o.delivery_distance_km,"
                " (SELECT COUNT(*) FROM order_items oi WHERE oi.order_id=o.id) AS item_count"
                " FROM deliveries d JOIN orders o ON o.id = d.order_id"
                " WHERE d.driver_id = ? ORDER BY d.id DESC LIMIT 100",
                (driver["id"],),
            ).fetchall()
        finally:
            conn.close()
        return [_row(r) for r in rows]

    @app.patch("/api/deliveries/{delivery_id}/status")
    def update_delivery_status(delivery_id: int, payload: DriverStatusRequest,
                               user=Depends(require_role("LIVREUR_MOTO", "CHAUFFEUR",
                                                          "PHARMACIEN", "ADMIN"))):
        st = payload.status.strip().upper()
        if st not in VALID_DRIVER_STATUSES:
            raise HTTPException(400, "Statut invalide")
        conn = get_db()
        try:
            d = conn.execute(
                "SELECT * FROM deliveries WHERE id=?", (delivery_id,)
            ).fetchone()
            if d is None:
                raise HTTPException(404, "Livraison introuvable")
            now = datetime.now().isoformat(timespec="seconds")
            fields = ["status = ?"]
            params = [st]
            if st == "ACCEPTED":
                fields.append("accepted_at = ?"); params.append(now)
            elif st == "PICKED_UP":
                fields.append("picked_up_at = ?"); params.append(now)
            elif st == "DELIVERED":
                fields.append("delivered_at = ?"); params.append(now)
            elif st == "FAILED":
                fields.append("failed_at = ?"); params.append(now)
            params.append(delivery_id)
            conn.execute("UPDATE deliveries SET " + ", ".join(fields) + " WHERE id=?", params)
            conn.execute("UPDATE orders SET delivery_status=? WHERE id=?", (st, d["order_id"]))
            try:
                from v3_modules.notifications import push_notification
                o = conn.execute("SELECT user_id, reference FROM orders WHERE id=?",
                                 (d["order_id"],)).fetchone()
                if o and o["user_id"]:
                    labels = {
                        "ACCEPTED": "Livreur en route",
                        "PICKED_UP": "Commande recuperee",
                        "IN_DELIVERY": "En cours de livraison",
                        "DELIVERED": "Commande livree",
                        "FAILED": "Livraison echouee",
                    }
                    push_notification(
                        conn, o["user_id"],
                        labels.get(st, "Livraison mise a jour"),
                        "Commande " + (o["reference"] or "") + " : " + st,
                        order_id=d["order_id"],
                    )
            except Exception:
                pass
            conn.commit()
            row = conn.execute(
                "SELECT * FROM deliveries WHERE id=?", (delivery_id,)
            ).fetchone()
        finally:
            conn.close()
        return _row(row)

    @app.get("/api/deliveries")
    def list_deliveries(status: str = "",
                        user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            sql = ("SELECT d.*, o.reference, o.customer_name, o.address,"
                   " o.delivery_vehicle_type, dr.name AS driver_name"
                   " FROM deliveries d"
                   " JOIN orders o ON o.id = d.order_id"
                   " LEFT JOIN drivers dr ON dr.id = d.driver_id")
            params = []
            if status.strip():
                sql += " WHERE d.status = ?"
                params.append(status.strip().upper())
            sql += " ORDER BY d.id DESC LIMIT 200"
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
        return [_row(r) for r in rows]


