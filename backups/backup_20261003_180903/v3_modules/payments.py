"""Paiement manuel + preuve (Phase 5)."""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

# push_notification importe dynamiquement (evite import circulaire)

ALLOWED_PROOF_TYPES = {
    "image/jpeg", "image/png", "image/webp",
    "application/pdf",
}
MAX_PROOF_MB = 10

VALID_STATUSES = {"PENDING", "PROOF_SUBMITTED", "VERIFIED", "REJECTED"}


class PaymentInitRequest(BaseModel):
    payment_method: str = "MANUAL"  # MANUAL | MIXX | OTHER


class PaymentRejectRequest(BaseModel):
    rejection_reason: str


def _row(r):
    return {k: r[k] for k in r.keys()} if r else None


def install_payments(app, get_db, require_role, uploads_dir):
    UPLOAD_DIR = Path(uploads_dir) / "proofs"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # ---- Cote client ----

    @app.post("/api/orders/{reference}/payment")
    def init_payment(reference: str, payload: PaymentInitRequest,
                     user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        method = payload.payment_method.strip().upper()
        if method not in {"MANUAL", "MIXX", "OTHER"}:
            raise HTTPException(400, "Methode de paiement invalide")

        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE reference = ? AND user_id = ?",
                (reference, user["id"]),
            ).fetchone()
            if order is None:
                raise HTTPException(404, "Commande introuvable")

            existing = conn.execute(
                "SELECT * FROM payments WHERE order_id = ? AND status IN ('PENDING', 'PROOF_SUBMITTED')",
                (order["id"],),
            ).fetchone()
            if existing:
                return _row(existing)

            settings = conn.execute(
                "SELECT payment_number, payment_name FROM pharmacy_settings WHERE id = 1"
            ).fetchone()
            payment_number = settings["payment_number"] if settings else ""
            payment_name = settings["payment_name"] if settings else ""

            # total n'est pas une colonne SQL : on le reconstruit
            subtotal = float(order["subtotal"] or 0)
            delivery_fee = float(order["delivery_fee"] or 0)
            total_amount = round(subtotal + delivery_fee, 2)

            now = datetime.now().isoformat(timespec="seconds")
            cur = conn.execute(
                "INSERT INTO payments (order_id, amount, payment_method,"
                " payment_number, payment_name, status, created_at)"
                " VALUES (?, ?, ?, ?, ?, 'PENDING', ?)",
                (order["id"], total_amount, method,
                 payment_number, payment_name, now),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM payments WHERE id = ?", (cur.lastrowid,)).fetchone()
        finally:
            conn.close()
        return _row(row)

    @app.get("/api/orders/{reference}/payment")
    def get_payment(reference: str, user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE reference = ? AND user_id = ?",
                (reference, user["id"]),
            ).fetchone()
            if order is None:
                raise HTTPException(404, "Commande introuvable")
            row = conn.execute(
                "SELECT * FROM payments WHERE order_id = ? ORDER BY id DESC LIMIT 1",
                (order["id"],),
            ).fetchone()
        finally:
            conn.close()
        if row:
            return _row(row)
        subtotal = float(order["subtotal"] or 0)
        delivery_fee = float(order["delivery_fee"] or 0)
        return {"status": "NONE", "amount": round(subtotal + delivery_fee, 2)}

    @app.post("/api/orders/{reference}/payment/proof")
    async def upload_proof(reference: str,
                           file: UploadFile = File(...),
                           user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE reference = ? AND user_id = ?",
                (reference, user["id"]),
            ).fetchone()
            if order is None:
                raise HTTPException(404, "Commande introuvable")

            payment = conn.execute(
                "SELECT * FROM payments WHERE order_id = ? ORDER BY id DESC LIMIT 1",
                (order["id"],),
            ).fetchone()
            if payment is None:
                raise HTTPException(400, "Initialisez le paiement d'abord")
            if payment["status"] == "VERIFIED":
                raise HTTPException(400, "Paiement deja verifie")
            if payment["status"] == "REJECTED":
                # Reinitialiser pour permettre un nouvel essai
                conn.execute(
                    "UPDATE payments SET status='PENDING', rejection_reason='' WHERE id=?",
                    (payment["id"],),
                )

            ctype = (file.content_type or "").lower()
            if ctype not in ALLOWED_PROOF_TYPES:
                raise HTTPException(400, "Format non accepte (JPG, PNG, WEBP, PDF)")

            data = await file.read()
            if len(data) > MAX_PROOF_MB * 1024 * 1024:
                raise HTTPException(400, "Fichier trop volumineux (max " + str(MAX_PROOF_MB) + " Mo)")

            ext = Path(file.filename or "proof").suffix.lower() or ".jpg"
            if ext not in {".jpg", ".jpeg", ".png", ".webp", ".pdf"}:
                ext = ".jpg"
            fname = uuid.uuid4().hex + ext
            target = UPLOAD_DIR / fname
            target.write_bytes(data)

            now = datetime.now().isoformat(timespec="seconds")
            conn.execute(
                "UPDATE payments SET proof_file=?, status='PROOF_SUBMITTED', submitted_at=? WHERE id=?",
                ("/uploads/proofs/" + fname, now, payment["id"]),
            )
            conn.execute(
                "UPDATE orders SET payment_status='PROOF_SUBMITTED' WHERE id=?",
                (order["id"],),
            )
            conn.commit()
            updated = conn.execute(
                "SELECT * FROM payments WHERE id = ?", (payment["id"],)
            ).fetchone()
        finally:
            conn.close()
        return _row(updated)

    # ---- Cote pharmacien / admin ----

    @app.get("/api/payments")
    def list_payments(status: str = "",
                      user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            sql = ("SELECT p.*, o.reference AS order_reference,"
                   " o.customer_name, o.phone, o.user_id,"
                   " (COALESCE(o.subtotal,0) + COALESCE(o.delivery_fee,0)) AS total"
                   " FROM payments p JOIN orders o ON o.id = p.order_id")
            params = []
            if status.strip():
                sql += " WHERE p.status = ?"
                params.append(status.strip().upper())
            sql += " ORDER BY p.id DESC LIMIT 200"
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
        return [_row(r) for r in rows]

    @app.get("/api/payments/{payment_id}")
    def get_payment_admin(payment_id: int,
                          user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT p.*, o.reference AS order_reference, o.customer_name,"
                " o.phone, (COALESCE(o.subtotal,0) + COALESCE(o.delivery_fee,0)) AS total"
                " FROM payments p JOIN orders o ON o.id = p.order_id WHERE p.id = ?",
                (payment_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            raise HTTPException(404, "Paiement introuvable")
        return _row(row)

    @app.patch("/api/payments/{payment_id}/verify")
    def verify_payment(payment_id: int,
                       user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            pay = conn.execute(
                "SELECT * FROM payments WHERE id = ?", (payment_id,)
            ).fetchone()
            if pay is None:
                raise HTTPException(404, "Paiement introuvable")
            if pay["status"] != "PROOF_SUBMITTED":
                raise HTTPException(400, "Paiement non soumis a verification")
            now = datetime.now().isoformat(timespec="seconds")
            conn.execute(
                "UPDATE payments SET status='VERIFIED', verified_at=?, verified_by=?"
                " WHERE id=?",
                (now, user["id"], payment_id),
            )
            conn.execute(
                "UPDATE orders SET payment_status='VERIFIED' WHERE id=?",
                (pay["order_id"],),
            )
            try:
                from v3_modules.notifications import push_notification
                o = conn.execute("SELECT user_id, reference FROM orders WHERE id=?",
                                 (pay["order_id"],)).fetchone()
                if o and o["user_id"]:
                    push_notification(
                        conn, o["user_id"],
                        "Paiement verifie",
                        "Votre paiement pour la commande " + (o["reference"] or "") + " a ete confirme.",
                        order_id=pay["order_id"],
                    )
            except Exception:
                pass
            conn.commit()
            updated = conn.execute(
                "SELECT * FROM payments WHERE id = ?", (payment_id,)
            ).fetchone()
        finally:
            conn.close()
        return _row(updated)

    @app.patch("/api/payments/{payment_id}/reject")
    def reject_payment(payment_id: int, payload: PaymentRejectRequest,
                       user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        if not payload.rejection_reason.strip():
            raise HTTPException(400, "Motif de refus obligatoire")
        conn = get_db()
        try:
            pay = conn.execute(
                "SELECT * FROM payments WHERE id = ?", (payment_id,)
            ).fetchone()
            if pay is None:
                raise HTTPException(404, "Paiement introuvable")
            conn.execute(
                "UPDATE payments SET status='REJECTED', rejection_reason=?,"
                " verified_at=?, verified_by=? WHERE id=?",
                (payload.rejection_reason.strip(),
                 datetime.now().isoformat(timespec="seconds"),
                 user["id"], payment_id),
            )
            conn.execute(
                "UPDATE orders SET payment_status='REJECTED' WHERE id=?",
                (pay["order_id"],),
            )
            conn.commit()
            updated = conn.execute(
                "SELECT * FROM payments WHERE id = ?", (payment_id,)
            ).fetchone()
        finally:
            conn.close()
        return _row(updated)


