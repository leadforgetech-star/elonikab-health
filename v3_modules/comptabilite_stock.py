# -*- coding: utf-8 -*-
"""Elonikab Health - Comptabilite & Stock avance (Sprint B + C)"""
import csv
import io
import uuid
from datetime import datetime
from typing import Optional
from fastapi import HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel


# === SCHEMAS ===
class ExpenseCreate(BaseModel):
    category: str
    label: str
    amount: float
    expense_date: str
    payment_method: str = ""
    supplier_name: str = ""
    reference: str = ""
    notes: str = ""


class SupplierCreate(BaseModel):
    name: str
    contact_name: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    notes: str = ""


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    notes: str = ""


class PurchaseOrderItemAdd(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    lot_number: str = ""
    expiry_date: Optional[str] = None


class ReceivePayload(BaseModel):
    update_stock: bool = True
    create_lots: bool = True


def install_comptabilite_stock(app, get_db, require_role):
    """Installe les routes compta + stock avance."""

    def _row(r):
        return {k: r[k] for k in r.keys()}

    def _log(conn, uid, action, target_type, tid, details=""):
        try:
            conn.execute(
                "INSERT INTO audit_logs (user_id, action, target_type, target_id,"
                " details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (uid, action, target_type, str(tid) if tid else None,
                 details, datetime.now().isoformat(timespec="seconds"))
            )
        except Exception:
            pass

    # ============================================================
    # DEPENSES
    # ============================================================
    @app.get("/api/compta/expenses")
    def list_expenses(month: Optional[str] = None,
                      category: Optional[str] = None,
                      user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            sql = "SELECT * FROM expenses WHERE 1=1"
            params = []
            if month:
                sql += " AND substr(expense_date, 1, 7) = ?"
                params.append(month)
            if category:
                sql += " AND category = ?"
                params.append(category)
            sql += " ORDER BY expense_date DESC, id DESC LIMIT 500"
            rows = conn.execute(sql, params).fetchall()
            return [_row(r) for r in rows]
        finally:
            conn.close()

    @app.post("/api/compta/expenses")
    def create_expense(payload: ExpenseCreate,
                       user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        if payload.amount <= 0:
            raise HTTPException(400, "Montant doit etre positif")
        if not (payload.label or "").strip():
            raise HTTPException(400, "Libelle obligatoire")
        if not (payload.category or "").strip():
            raise HTTPException(400, "Categorie obligatoire")

        now = datetime.now().isoformat(timespec="seconds")
        conn = get_db()
        try:
            cur = conn.execute(
                "INSERT INTO expenses (category, label, amount, expense_date,"
                " payment_method, supplier_name, reference, notes, created_by, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (payload.category.strip(), payload.label.strip(), float(payload.amount),
                 payload.expense_date, payload.payment_method.strip(),
                 payload.supplier_name.strip(), payload.reference.strip(),
                 payload.notes.strip(), user["id"], now)
            )
            exp_id = cur.lastrowid
            conn.execute(
                "INSERT INTO cash_journal (type, amount, label, reference,"
                " source_type, source_id, created_by, created_at)"
                " VALUES ('OUT', ?, ?, ?, 'expense', ?, ?, ?)",
                (float(payload.amount), payload.label.strip(),
                 payload.reference.strip() or ("EXP-" + str(exp_id)),
                 exp_id, user["id"], now)
            )
            _log(conn, user["id"], "compta.expense.create", "expense", exp_id,
                 f"{payload.category} {payload.amount}")
            conn.commit()
            row = conn.execute("SELECT * FROM expenses WHERE id = ?",
                              (exp_id,)).fetchone()
            return _row(row)
        finally:
            conn.close()

    @app.delete("/api/compta/expenses/{expense_id}")
    def delete_expense(expense_id: int,
                      user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            row = conn.execute("SELECT * FROM expenses WHERE id = ?",
                              (expense_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Depense introuvable")
            conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            conn.execute("DELETE FROM cash_journal WHERE source_type='expense' AND source_id=?",
                        (expense_id,))
            _log(conn, user["id"], "compta.expense.delete", "expense", expense_id, "")
            conn.commit()
            return {"ok": True}
        finally:
            conn.close()

    # ============================================================
    # BILAN MENSUEL
    # ============================================================
    @app.get("/api/compta/summary")
    def compta_summary(month: Optional[str] = None,
                       user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        if not month:
            month = datetime.now().strftime("%Y-%m")

        conn = get_db()
        try:
            # Recettes : commandes terminees ce mois
            recettes = conn.execute(
                "SELECT COALESCE(SUM(subtotal + delivery_fee), 0) AS t, COUNT(*) AS n"
                " FROM orders WHERE substr(created_at,1,7)=? AND status='terminee'",
                (month,)
            ).fetchone()
            recettes_total = float(recettes["t"] or 0)
            recettes_count = int(recettes["n"] or 0)

            # Depenses
            depenses = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) AS t, COUNT(*) AS n"
                " FROM expenses WHERE substr(expense_date,1,7)=?",
                (month,)
            ).fetchone()
            depenses_total = float(depenses["t"] or 0)
            depenses_count = int(depenses["n"] or 0)

            # Depenses par categorie
            by_cat = {}
            for r in conn.execute(
                "SELECT category, SUM(amount) AS s FROM expenses"
                " WHERE substr(expense_date,1,7)=? GROUP BY category ORDER BY s DESC",
                (month,)
            ).fetchall():
                by_cat[r["category"]] = float(r["s"] or 0)

            # Marges : produits vendus ce mois
            marges = 0.0
            for r in conn.execute(
                "SELECT oi.quantity, p.purchase_price, oi.unit_price"
                " FROM order_items oi"
                " LEFT JOIN products p ON p.id = oi.product_id"
                " JOIN orders o ON o.id = oi.order_id"
                " WHERE substr(o.created_at,1,7)=? AND o.status='terminee'"
                "   AND p.purchase_price IS NOT NULL",
                (month,)
            ).fetchall():
                marge = (float(r["unit_price"] or 0) - float(r["purchase_price"] or 0)) * int(r["quantity"] or 0)
                marges += marge

            benefice = recettes_total - depenses_total

            return {
                "month": month,
                "recettes": recettes_total,
                "recettes_count": recettes_count,
                "depenses": depenses_total,
                "depenses_count": depenses_count,
                "benefice": round(benefice, 2),
                "marge_estimee": round(marges, 2),
                "marge_pct": round((marges / recettes_total * 100), 1) if recettes_total > 0 else 0,
                "depenses_par_categorie": by_cat,
            }
        finally:
            conn.close()

    # ============================================================
    # JOURNAL DE CAISSE
    # ============================================================
    @app.get("/api/compta/journal")
    def compta_journal(month: Optional[str] = None, limit: int = 200,
                      user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            if month:
                rows = conn.execute(
                    "SELECT * FROM cash_journal WHERE substr(created_at,1,7)=?"
                    " ORDER BY id DESC LIMIT ?",
                    (month, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM cash_journal ORDER BY id DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [_row(r) for r in rows]
        finally:
            conn.close()

    # ============================================================
    # EXPORT CSV
    # ============================================================
    @app.get("/api/compta/export.csv")
    def compta_export(month: Optional[str] = None,
                     user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        if not month:
            month = datetime.now().strftime("%Y-%m")
        conn = get_db()
        try:
            buf = io.StringIO()
            w = csv.writer(buf, delimiter=";")
            w.writerow(["Type", "Date", "Reference", "Libelle", "Categorie", "Montant"])
            # Recettes
            for r in conn.execute(
                "SELECT reference, created_at, customer_name, subtotal + delivery_fee AS total"
                " FROM orders WHERE substr(created_at,1,7)=? AND status='terminee'",
                (month,)
            ).fetchall():
                w.writerow(["RECETTE", r["created_at"], r["reference"],
                           r["customer_name"], "Vente", r["total"]])
            # Depenses
            for r in conn.execute(
                "SELECT * FROM expenses WHERE substr(expense_date,1,7)=?",
                (month,)
            ).fetchall():
                w.writerow(["DEPENSE", r["expense_date"], r["reference"],
                           r["label"], r["category"], -abs(r["amount"])])
            return Response(
                content=buf.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=compta_{month}.csv"}
            )
        finally:
            conn.close()

    # ============================================================
    # STOCK AVANCE : VALORISATION
    # ============================================================
    @app.get("/api/admin/stock/valuation")
    def stock_valuation(user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT id, name, stock_quantity, purchase_price, price"
                " FROM products WHERE is_active = 1"
            ).fetchall()
            total_purchase = 0.0
            total_sell = 0.0
            items = []
            for r in rows:
                sq = int(r["stock_quantity"] or 0)
                pp = float(r["purchase_price"] or 0)
                sp = float(r["price"] or 0)
                total_purchase += sq * pp
                total_sell += sq * sp
                items.append({
                    "id": r["id"], "name": r["name"],
                    "quantity": sq,
                    "purchase_price": pp,
                    "sell_price": sp,
                    "value_purchase": round(sq * pp, 2),
                    "value_sell": round(sq * sp, 2),
                })
            return {
                "total_purchase": round(total_purchase, 2),
                "total_sell": round(total_sell, 2),
                "potential_margin": round(total_sell - total_purchase, 2),
                "items": items,
            }
        finally:
            conn.close()

    # ============================================================
    # STOCK AVANCE : PREVISIONS
    # ============================================================
    @app.get("/api/admin/stock/forecast")
    def stock_forecast(days: int = 30,
                      user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        """Previsions basees sur les ventes des N derniers jours."""
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
        conn = get_db()
        try:
            rows = conn.execute("""
                SELECT p.id, p.name, p.stock_quantity, p.stock_min_threshold,
                       COALESCE(SUM(oi.quantity), 0) AS sold
                FROM products p
                LEFT JOIN order_items oi ON oi.product_id = p.id
                LEFT JOIN orders o ON o.id = oi.order_id AND o.created_at >= ?
                WHERE p.is_active = 1
                GROUP BY p.id
                ORDER BY sold DESC
            """, (cutoff,)).fetchall()
            forecast = []
            for r in rows:
                sold = int(r["sold"] or 0)
                sq = int(r["stock_quantity"] or 0)
                daily_speed = sold / max(days, 1)
                days_left = int(sq / daily_speed) if daily_speed > 0 else None
                threshold = int(r["stock_min_threshold"] or 5)
                reorder = None
                if daily_speed > 0:
                    target_30d = int(daily_speed * 30)
                    reorder = max(0, target_30d - sq)
                forecast.append({
                    "id": r["id"], "name": r["name"],
                    "stock": sq, "threshold": threshold,
                    "sold_period": sold,
                    "daily_speed": round(daily_speed, 2),
                    "days_left": days_left,
                    "reorder_qty": reorder,
                    "urgent": days_left is not None and days_left <= 7,
                })
            return {"period_days": days, "items": forecast}
        finally:
            conn.close()

    # ============================================================
    # FOURNISSEURS
    # ============================================================
    @app.get("/api/admin/suppliers")
    def list_suppliers(include_inactive: int = 0,
                      user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            sql = "SELECT * FROM suppliers"
            if not include_inactive:
                sql += " WHERE is_active = 1"
            sql += " ORDER BY name COLLATE NOCASE"
            return [_row(r) for r in conn.execute(sql).fetchall()]
        finally:
            conn.close()

    @app.post("/api/admin/suppliers")
    def create_supplier(payload: SupplierCreate,
                       user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        name = (payload.name or "").strip()
        if not name or len(name) < 2:
            raise HTTPException(400, "Nom obligatoire")
        now = datetime.now().isoformat(timespec="seconds")
        conn = get_db()
        try:
            cur = conn.execute(
                "INSERT INTO suppliers (name, contact_name, phone, email, address, notes,"
                " is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
                (name, payload.contact_name.strip(), payload.phone.strip(),
                 payload.email.strip(), payload.address.strip(),
                 payload.notes.strip(), now)
            )
            sid = cur.lastrowid
            _log(conn, user["id"], "supplier.create", "supplier", sid, name)
            conn.commit()
            row = conn.execute("SELECT * FROM suppliers WHERE id = ?",
                              (sid,)).fetchone()
            return _row(row)
        finally:
            conn.close()

    @app.delete("/api/admin/suppliers/{supplier_id}")
    def archive_supplier(supplier_id: int,
                        user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            row = conn.execute("SELECT * FROM suppliers WHERE id = ?",
                              (supplier_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Fournisseur introuvable")
            conn.execute("UPDATE suppliers SET is_active = 0 WHERE id = ?",
                        (supplier_id,))
            _log(conn, user["id"], "supplier.archive", "supplier", supplier_id, "")
            conn.commit()
            return {"ok": True}
        finally:
            conn.close()

    # ============================================================
    # COMMANDES D'ACHAT
    # ============================================================
    @app.get("/api/admin/purchase-orders")
    def list_purchase_orders(status: Optional[str] = None,
                            user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            sql = ("SELECT po.*, s.name AS supplier_name"
                   " FROM purchase_orders po LEFT JOIN suppliers s ON s.id = po.supplier_id")
            params = []
            if status:
                sql += " WHERE po.status = ?"
                params.append(status)
            sql += " ORDER BY po.id DESC LIMIT 200"
            return [_row(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    @app.post("/api/admin/purchase-orders")
    def create_purchase_order(payload: PurchaseOrderCreate,
                            user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            sup = conn.execute("SELECT * FROM suppliers WHERE id = ?",
                              (payload.supplier_id,)).fetchone()
            if not sup:
                raise HTTPException(404, "Fournisseur introuvable")
            ref = "PO-" + datetime.now().strftime("%y%m%d") + "-" + uuid.uuid4().hex[:6].upper()
            now = datetime.now().isoformat(timespec="seconds")
            cur = conn.execute(
                "INSERT INTO purchase_orders (reference, supplier_id, status,"
                " total_amount, notes, created_by, created_at)"
                " VALUES (?, ?, 'draft', 0, ?, ?, ?)",
                (ref, payload.supplier_id, payload.notes.strip(), user["id"], now)
            )
            po_id = cur.lastrowid
            _log(conn, user["id"], "purchase_order.create", "purchase_order", po_id, ref)
            conn.commit()
            return {"id": po_id, "reference": ref}
        finally:
            conn.close()

    @app.post("/api/admin/purchase-orders/{po_id}/items")
    def add_purchase_order_item(po_id: int, payload: PurchaseOrderItemAdd,
                                user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            po = conn.execute("SELECT * FROM purchase_orders WHERE id = ?",
                             (po_id,)).fetchone()
            if not po:
                raise HTTPException(404, "Commande d'achat introuvable")
            if po["status"] != "draft":
                raise HTTPException(400, "Commande ne peut plus etre modifiee")
            if payload.quantity <= 0:
                raise HTTPException(400, "Quantite positive obligatoire")
            if payload.unit_price < 0:
                raise HTTPException(400, "Prix invalide")
            prod = conn.execute("SELECT * FROM products WHERE id = ?",
                               (payload.product_id,)).fetchone()
            if not prod:
                raise HTTPException(404, "Produit introuvable")
            conn.execute(
                "INSERT INTO purchase_order_items (purchase_order_id, product_id,"
                " quantity, unit_price, lot_number, expiry_date)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (po_id, payload.product_id, payload.quantity,
                 payload.unit_price, payload.lot_number.strip(),
                 payload.expiry_date)
            )
            total = conn.execute(
                "SELECT COALESCE(SUM(quantity * unit_price), 0) FROM purchase_order_items"
                " WHERE purchase_order_id = ?",
                (po_id,)
            ).fetchone()[0]
            conn.execute("UPDATE purchase_orders SET total_amount = ? WHERE id = ?",
                        (float(total), po_id))
            conn.commit()
            return {"ok": True, "total": float(total)}
        finally:
            conn.close()

    @app.patch("/api/admin/purchase-orders/{po_id}/receive")
    def receive_purchase_order(po_id: int, payload: ReceivePayload = None,
                              user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        if payload is None:
            payload = ReceivePayload()
        conn = get_db()
        try:
            po = conn.execute("SELECT * FROM purchase_orders WHERE id = ?",
                             (po_id,)).fetchone()
            if not po:
                raise HTTPException(404, "Commande introuvable")
            if po["status"] != "draft":
                raise HTTPException(400, "Seules les commandes en brouillon peuvent etre recues")
            items = conn.execute(
                "SELECT * FROM purchase_order_items WHERE purchase_order_id = ?",
                (po_id,)
            ).fetchall()
            if not items:
                raise HTTPException(400, "Aucun article a recevoir")
            now = datetime.now().isoformat(timespec="seconds")
            if payload.update_stock:
                for it in items:
                    conn.execute(
                        "INSERT INTO stock_movements (product_id, type, quantity,"
                        " reason, reference, user_id, created_at)"
                        " VALUES (?, 'IN', ?, ?, ?, ?, ?)",
                        (it["product_id"], int(it["quantity"]),
                         f"Reception commande achat {po['reference']}",
                         po["reference"], user["id"], now)
                    )
                    conn.execute(
                        "UPDATE products SET stock_quantity = COALESCE(stock_quantity, 0) + ?"
                        " WHERE id = ?",
                        (int(it["quantity"]), it["product_id"])
                    )
                    # Mettre a jour purchase_price
                    conn.execute(
                        "UPDATE products SET purchase_price = ? WHERE id = ?",
                        (float(it["unit_price"]), it["product_id"])
                    )
                    # Creer un lot
                    if payload.create_lots and (it["lot_number"] or it["expiry_date"]):
                        conn.execute(
                            "INSERT INTO stock_lots (product_id, lot_number, expiry_date,"
                            " quantity, created_at) VALUES (?, ?, ?, ?, ?)",
                            (it["product_id"], it["lot_number"] or "",
                             it["expiry_date"], int(it["quantity"]), now)
                        )
            conn.execute(
                "UPDATE purchase_orders SET status='received', received_at=? WHERE id=?",
                (now, po_id)
            )
            # Ecriture de la depense
            conn.execute(
                "INSERT INTO cash_journal (type, amount, label, reference, source_type,"
                " source_id, created_by, created_at)"
                " VALUES ('OUT', ?, ?, ?, 'purchase_order', ?, ?, ?)",
                (float(po["total_amount"]), f"Achat fournisseur {po['reference']}",
                 po["reference"], po_id, user["id"], now)
            )
            _log(conn, user["id"], "purchase_order.receive", "purchase_order", po_id,
                 f"total={po['total_amount']}")
            conn.commit()
            return {"ok": True, "received": len(items)}
        finally:
            conn.close()

    # ============================================================
    # VUE DIRECTION
    # ============================================================
    @app.get("/api/compta/dashboard")
    def compta_dashboard(user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        month = datetime.now().strftime("%Y-%m")
        conn = get_db()
        try:
            rec = conn.execute(
                "SELECT COALESCE(SUM(subtotal + delivery_fee), 0) FROM orders"
                " WHERE substr(created_at,1,7)=? AND status='terminee'",
                (month,)
            ).fetchone()[0]
            dep = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM expenses"
                " WHERE substr(expense_date,1,7)=?",
                (month,)
            ).fetchone()[0]
            val = conn.execute(
                "SELECT COALESCE(SUM(stock_quantity * COALESCE(purchase_price, 0)), 0)"
                " FROM products WHERE is_active = 1"
            ).fetchone()[0]
            dormant = conn.execute("""
                SELECT COUNT(*) FROM products p WHERE p.is_active = 1
                AND p.id NOT IN (
                    SELECT DISTINCT oi.product_id FROM order_items oi
                    JOIN orders o ON o.id = oi.order_id
                    WHERE o.created_at >= datetime('now', '-60 days')
                )
            """).fetchone()[0]
            return {
                "month": month,
                "recettes": float(rec or 0),
                "depenses": float(dep or 0),
                "benefice": round(float(rec or 0) - float(dep or 0), 2),
                "stock_value": round(float(val or 0), 2),
                "dormant_products": int(dormant or 0),
            }
        finally:
            conn.close()

    print("[comptabilite_stock] Routes installees")
