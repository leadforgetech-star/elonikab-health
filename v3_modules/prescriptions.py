"""Workflow ordonnance (Phase 6)."""
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/webp",
    "application/pdf", "image/heic",
}
MAX_MB = 15

STATUSES = {"PENDING", "APPROVED", "REJECTED", "NEEDS_REVIEW"}


class ReviewRequest(BaseModel):
    status: str
    comment: str = ""


def _row(r):
    return {k: r[k] for k in r.keys()} if r else None


def install_prescriptions(app, get_db, require_role, uploads_dir):
    UP = Path(uploads_dir) / "prescriptions"
    UP.mkdir(parents=True, exist_ok=True)

    # ---- Cote patient ----

    @app.post("/api/orders/{reference}/prescription")
    async def upload_prescription(
        reference: str,
        file: UploadFile = File(...),
        user=Depends(require_role("PATIENT", "PROFESSIONNEL")),
    ):
        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE reference = ? AND user_id = ?",
                (reference, user["id"]),
            ).fetchone()
            if order is None:
                raise HTTPException(404, "Commande introuvable")

            ctype = (file.content_type or "").lower()
            if ctype not in ALLOWED_TYPES:
                raise HTTPException(400, "Format non accepte (JPG, PNG, WEBP, HEIC, PDF)")

            data = await file.read()
            if len(data) > MAX_MB * 1024 * 1024:
                raise HTTPException(400, "Fichier trop volumineux (max " + str(MAX_MB) + " Mo)")

            ext = Path(file.filename or "presc").suffix.lower() or ".jpg"
            if ext not in {".jpg", ".jpeg", ".png", ".webp", ".pdf", ".heic"}:
                ext = ".jpg"
            fname = uuid.uuid4().hex + ext
            target = UP / fname
            target.write_bytes(data)
            rel = "/api/files/prescriptions/" + fname

            now = datetime.now().isoformat(timespec="seconds")
            # Si une ordonnance PENDING existe deja, on la remplace
            existing = conn.execute(
                "SELECT id FROM prescriptions WHERE order_id = ? AND status IN ('PENDING','NEEDS_REVIEW')",
                (order["id"],),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE prescriptions SET file_path=?, status='PENDING',"
                    " comment='', reviewed_at=NULL, reviewed_by=NULL WHERE id=?",
                    (rel, existing["id"]),
                )
                pid = existing["id"]
            else:
                cur = conn.execute(
                    "INSERT INTO prescriptions (order_id, file_path, status, created_at)"
                    " VALUES (?, ?, 'PENDING', ?)",
                    (order["id"], rel, now),
                )
                pid = cur.lastrowid

            conn.execute(
                "UPDATE orders SET prescription_file=?, prescription_status='PENDING'"
                " WHERE id=?",
                (rel, order["id"]),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM prescriptions WHERE id=?", (pid,)
            ).fetchone()
        finally:
            conn.close()
        return _row(row)

    @app.get("/api/orders/{reference}/prescription")
    def get_prescription(reference: str,
                         user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE reference = ? AND user_id = ?",
                (reference, user["id"]),
            ).fetchone()
            if order is None:
                raise HTTPException(404, "Commande introuvable")
            row = conn.execute(
                "SELECT * FROM prescriptions WHERE order_id=?"
                " ORDER BY id DESC LIMIT 1",
                (order["id"],),
            ).fetchone()
        finally:
            conn.close()
        return _row(row) if row else {"status": "NONE"}

    # ---- Cote pharmacien ----

    @app.get("/api/prescriptions")
    def list_prescriptions(status: str = "",
                           user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            sql = ("SELECT pr.*, o.reference AS order_reference,"
                   " o.customer_name, o.phone FROM prescriptions pr"
                   " JOIN orders o ON o.id = pr.order_id")
            params = []
            if status.strip():
                sql += " WHERE pr.status = ?"
                params.append(status.strip().upper())
            sql += " ORDER BY pr.id DESC LIMIT 200"
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
        LABELS_FR = {
            "PENDING": "En attente",
            "NEEDS_REVIEW": "A verifier",
            "APPROVED": "Approuvee",
            "REJECTED": "Refusee",
        }
        out = []
        for r in rows:
            d = _row(r)
            d["status_label"] = LABELS_FR.get((d.get("status") or "").upper(), d.get("status"))
            out.append(d)
        return out

    @app.patch("/api/prescriptions/{presc_id}/review")
    def review_prescription(presc_id: int, payload: ReviewRequest,
                            user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        st = payload.status.strip().upper()
        if st not in STATUSES:
            raise HTTPException(400, "Statut invalide")
        if st == "REJECTED" and not payload.comment.strip():
            raise HTTPException(400, "Motif obligatoire pour refus")

        conn = get_db()
        try:
            p = conn.execute(
                "SELECT * FROM prescriptions WHERE id=?", (presc_id,)
            ).fetchone()
            if p is None:
                raise HTTPException(404, "Ordonnance introuvable")
            now = datetime.now().isoformat(timespec="seconds")
            conn.execute(
                "UPDATE prescriptions SET status=?, comment=?, reviewed_at=?,"
                " reviewed_by=? WHERE id=?",
                (st, payload.comment.strip(), now, user["id"], presc_id),
            )
            conn.execute(
                "UPDATE orders SET prescription_status=? WHERE id=?",
                (st, p["order_id"]),
            )
            try:
                from v3_modules.notifications import push_notification
                o = conn.execute("SELECT user_id, reference FROM orders WHERE id=?",
                                 (p["order_id"],)).fetchone()
                if o and o["user_id"]:
                    labels = {
                        "APPROVED": "Ordonnance approuvee",
                        "REJECTED": "Ordonnance refusee",
                        "NEEDS_REVIEW": "Ordonnance a renvoyer",
                    }
                    push_notification(
                        conn, o["user_id"],
                        labels.get(st, "Ordonnance mise a jour"),
                        "Commande " + (o["reference"] or "") + " : " + st,
                        order_id=p["order_id"],
                    )
            except Exception:
                pass
            conn.commit()
            try:
                from main import log_audit as _la
                _la(conn, user["id"] if user else None,
                    "prescription.review", "prescription", presc_id,
                    "status=" + str(st))
                conn.commit()
            except Exception:
                pass
            row = conn.execute(
                "SELECT * FROM prescriptions WHERE id=?", (presc_id,)
            ).fetchone()
        finally:
            conn.close()
        return _row(row)

    # ---- Helper : ordonnance requise pour une commande ----

    @app.get("/api/orders/{reference}/requires-prescription")
    def requires_prescription(reference: str):
        """Retourne True si au moins un produit de la commande exige une ordonnance."""
        conn = get_db()
        try:
            o = conn.execute(
                "SELECT id FROM orders WHERE reference=?", (reference,)
            ).fetchone()
            if o is None:
                raise HTTPException(404, "Commande introuvable")
            rows = conn.execute(
                "SELECT oi.product_id FROM order_items oi WHERE oi.order_id=?",
                (o["id"],),
            ).fetchall()
            if not rows:
                # commande V1 (pas d'order_items) : on regarde le product_id direct
                r = conn.execute(
                    "SELECT requires_prescription FROM products WHERE id="
                    "(SELECT product_id FROM orders WHERE id=?)",
                    (o["id"],),
                ).fetchone()
                req = bool(r and r["requires_prescription"])
            else:
                ids = [r["product_id"] for r in rows if r["product_id"]]
                if not ids:
                    req = False
                else:
                    qmarks = ",".join("?" for _ in ids)
                    r = conn.execute(
                        "SELECT COUNT(*) AS n FROM products"
                        " WHERE id IN (" + qmarks + ") AND requires_prescription=1",
                        ids,
                    ).fetchone()
                    req = r["n"] > 0
        finally:
            conn.close()
        return {"requires_prescription": req}


