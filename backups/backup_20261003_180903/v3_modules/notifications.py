"""Notifications internes + recus (Phase 10)."""
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import Depends, HTTPException
from fastapi.responses import HTMLResponse


def _row(r):
    return {k: r[k] for k in r.keys()} if r else None


def push_notification(conn, user_id, title, body, order_id=None, channel="IN_APP"):
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO notifications (user_id, order_id, channel, title, body,"
        " is_read, created_at) VALUES (?, ?, ?, ?, ?, 0, ?)",
        (user_id, order_id, channel, title, body, now),
    )


def install_notifications(app, get_db, require_role):
    @app.get("/api/notifications")
    def list_notifs(unread_only: int = 0,
                    user=Depends(require_role("PATIENT", "PROFESSIONNEL",
                                              "PHARMACIEN", "ADMIN",
                                              "LIVREUR_MOTO", "CHAUFFEUR"))):
        conn = get_db()
        try:
            sql = "SELECT * FROM notifications WHERE user_id = ?"
            params = [user["id"]]
            if unread_only:
                sql += " AND is_read = 0"
            sql += " ORDER BY id DESC LIMIT 100"
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
        return [_row(r) for r in rows]

    @app.patch("/api/notifications/{notif_id}/read")
    def mark_read(notif_id: int,
                  user=Depends(require_role("PATIENT", "PROFESSIONNEL",
                                            "PHARMACIEN", "ADMIN",
                                            "LIVREUR_MOTO", "CHAUFFEUR"))):
        conn = get_db()
        try:
            conn.execute(
                "UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?",
                (notif_id, user["id"]),
            )
            conn.commit()
        finally:
            conn.close()
        return {"ok": True}

    @app.patch("/api/notifications/read-all")
    def read_all(user=Depends(require_role("PATIENT", "PROFESSIONNEL",
                                           "PHARMACIEN", "ADMIN",
                                           "LIVREUR_MOTO", "CHAUFFEUR"))):
        conn = get_db()
        try:
            conn.execute("UPDATE notifications SET is_read=1 WHERE user_id=?",
                         (user["id"],))
            conn.commit()
        finally:
            conn.close()
        return {"ok": True}

    # ---- Recu (HTML imprimable) ----

    @app.get("/api/orders/{reference}/receipt", response_class=HTMLResponse)
    def get_receipt(reference: str):
        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE reference=?", (reference,)
            ).fetchone()
            if order is None:
                raise HTTPException(404, "Commande introuvable")
            items = conn.execute(
                "SELECT * FROM order_items WHERE order_id=? ORDER BY id",
                (order["id"],),
            ).fetchall()
            settings = conn.execute(
                "SELECT * FROM pharmacy_settings WHERE id=1"
            ).fetchone()
            payment = conn.execute(
                "SELECT * FROM payments WHERE order_id=? ORDER BY id DESC LIMIT 1",
                (order["id"],),
            ).fetchone()

            # Enregistrer le recu (idempotent)
            existing = conn.execute(
                "SELECT receipt_number FROM receipts WHERE order_id=?",
                (order["id"],),
            ).fetchone()
            if existing:
                receipt_num = existing["receipt_number"]
            else:
                receipt_num = "REC-" + order["reference"].replace("CMD-", "")
                conn.execute(
                    "INSERT INTO receipts (order_id, receipt_number, issued_at)"
                    " VALUES (?, ?, ?)",
                    (order["id"], receipt_num,
                     datetime.now().isoformat(timespec="seconds")),
                )
                conn.commit()
        finally:
            conn.close()

        sub = float(order["subtotal"] or 0)
        fee = float(order["delivery_fee"] or 0)
        tot = round(sub + fee, 2)

        def money(v):
            return "{:,.0f}".format(v).replace(",", " ") + " FCFA"

        rows_html = ""
        if items:
            for it in items:
                rows_html += (
                    "<tr><td>" + (it["product_name"] or "") + "</td>"
                    "<td style='text-align:right'>" + str(it["quantity"]) + "</td>"
                    "<td style='text-align:right'>" + money(it["unit_price"]) + "</td>"
                    "<td style='text-align:right'>" + money(it["subtotal"]) + "</td></tr>"
                )
        else:
            rows_html = (
                "<tr><td>" + (order["product_name"] or "") + "</td>"
                "<td style='text-align:right'>" + str(order["quantity"]) + "</td>"
                "<td style='text-align:right'>" + money(order["price"]) + "</td>"
                "<td style='text-align:right'>" + money(sub) + "</td></tr>"
            )

        ph_name = settings["pharmacy_name"] if settings and "pharmacy_name" in settings.keys() else "Elokinab Health"
        ph_phone = settings["pharmacy_phone"] if settings and "pharmacy_phone" in settings.keys() else ""
        pay_status = payment["status"] if payment else "PENDING"

        html = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Recu """ + receipt_num + """</title>
<style>
  body{font-family:Segoe UI,system-ui,sans-serif;color:#0f2620;background:#f4faf7;padding:20px}
  .card{background:#fff;max-width:640px;margin:0 auto;border-radius:16px;padding:32px;box-shadow:0 8px 28px rgba(15,38,32,.08)}
  h1{color:#0a7a5a;margin:0 0 4px}
  .ref{font-family:Consolas,monospace;color:#6c8a80;font-size:13px}
  table{width:100%;border-collapse:collapse;margin:18px 0;font-size:14px}
  th,td{padding:8px 4px;border-bottom:1px solid #ddece6;text-align:left}
  th{background:#e8f7f1;color:#0a7a5a;font-size:12px;text-transform:uppercase}
  .total{font-size:20px;font-weight:800;color:#0a7a5a;text-align:right;margin-top:8px}
  .status{display:inline-block;padding:4px 10px;border-radius:999px;font-size:11px;font-weight:800;text-transform:uppercase;background:#fff4e0;color:#b26b00}
  .foot{margin-top:24px;font-size:12px;color:#6c8a80;text-align:center}
  @media print{body{background:#fff;padding:0}.card{box-shadow:none}}
</style></head><body>
<div class="card">
  <h1>""" + ph_name + """</h1>
  <div class="ref">Recu """ + receipt_num + " - " + (order["created_at"] or "")[:16] + """</div>
  <div style="margin-top:14px">
    <strong>""" + (order["customer_name"] or "") + """</strong><br>
    <span class="ref">""" + (order["phone"] or "") + """</span>
  </div>
  <table>
    <thead><tr><th>Produit</th><th style="text-align:right">Qte</th>
    <th style="text-align:right">Prix U.</th><th style="text-align:right">Sous-total</th></tr></thead>
    <tbody>""" + rows_html + """</tbody>
  </table>
  <div style="text-align:right;font-size:14px">
    Sous-total : <strong>""" + money(sub) + """</strong><br>
    Livraison : <strong>""" + money(fee) + """</strong>
  </div>
  <div class="total">Total : """ + money(tot) + """</div>
  <div style="margin-top:12px;text-align:right">
    <span class="status">Paiement : """ + pay_status + """</span>
  </div>
  <div class="foot">
    Document non contractuel genere automatiquement.<br>
    """ + ph_phone + """
  </div>
</div></body></html>"""
        return HTMLResponse(html)


