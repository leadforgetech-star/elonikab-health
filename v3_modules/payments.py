"""Paiement manuel + preuve (Phase 5)."""
import base64
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel


def _notify_admins_proof(conn, order_row, reference):
    """Notifie PHARMACIEN + ADMIN qu'une preuve de paiement a ete soumise."""
    try:
        from v3_modules.notifications import push_notification
        admins = conn.execute(
            "SELECT id FROM users WHERE role IN ('PHARMACIEN', 'ADMIN')"
        ).fetchall()
        customer = (order_row["customer_name"] if order_row else "") or "Client"
        for a in admins:
            push_notification(
                conn, a["id"],
                "Nouvelle preuve de paiement",
                customer + " a soumis une preuve pour " + (reference or ""),
                order_id=(order_row["id"] if order_row else None),
            )
        conn.commit()
    except Exception:
        pass




# push_notification importe dynamiquement (evite import circulaire)

ALLOWED_PROOF_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
    "application/pdf",
    "application/octet-stream",  # fallback iPhone
}
MAX_PROOF_MB = 25

VALID_STATUSES = {"PENDING", "PROOF_SUBMITTED", "VERIFIED", "REJECTED"}


class PaymentInitRequest(BaseModel):
    payment_method: str = "MANUAL"  # MANUAL | MIXX | OTHER


class ChunkInit(BaseModel):
    filename: str = "proof.jpg"
    content_type: str = "image/jpeg"
    total_chunks: int = 1
    total_bytes: int = 0


class ChunkData(BaseModel):
    upload_id: str
    index: int
    data_base64: str  # morceau encode en base64


class ChunkFinalize(BaseModel):
    upload_id: str


class ProofUpload(BaseModel):
    filename: str = "proof.jpg"
    content_type: str = "image/jpeg"
    data_base64: str  # Donnees encodees en base64 (sans prefixe data:)


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

            # ETAPE 3.6 : bloquer les commandes refusees
            if order["status"] == "refusee":
                raise HTTPException(400, "Commande refusee : paiement impossible")

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

            # Recuperer le paiement le plus recent (s'il existe)
            row = conn.execute(
                "SELECT * FROM payments WHERE order_id = ? ORDER BY id DESC LIMIT 1",
                (order["id"],),
            ).fetchone()

            # Recuperer les infos de config pharmacie
            settings = conn.execute(
                "SELECT payment_number, payment_name, whatsapp_number, pharmacy_phone"
                " FROM pharmacy_settings WHERE id = 1"
            ).fetchone()

            payment_number = ""
            payment_name = ""
            if settings:
                payment_number = (settings["payment_number"] or "").strip()
                payment_name = (settings["payment_name"] or "").strip()
                if not payment_number:
                    # Fallback : utiliser whatsapp ou phone
                    payment_number = (settings["whatsapp_number"] or "").strip()
                    if not payment_number:
                        payment_number = (settings["pharmacy_phone"] or "").strip()

            # Montant = subtotal + delivery_fee
            subtotal = float(order["subtotal"] or 0)
            delivery_fee = float(order["delivery_fee"] or 0)
            amount = round(subtotal + delivery_fee, 2)

            # Si un paiement existe, retourner ses donnees
            if row:
                result = _row(row)
                # Completer avec les infos de config au cas ou
                if not result.get("payment_number"):
                    result["payment_number"] = payment_number
                if not result.get("payment_name"):
                    result["payment_name"] = payment_name
                return result

            # Sinon : retourner un paiement virtuel avec toutes les infos
            return {
                "status": "NONE",
                "amount": amount,
                "refused": order["status"] == "refusee",
                "payment_number": payment_number,
                "payment_name": payment_name,
                "payment_method": "MANUAL",
            }
        finally:
            conn.close()



    @app.post("/api/orders/{reference}/payment/proof-json")
    def upload_proof_json(reference: str, payload: ProofUpload,
                          user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        """Upload de la preuve de paiement via JSON + base64.
        Contourne les problemes de HTTP/2 avec multipart sur les tunnels."""
        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE reference = ? AND user_id = ?",
                (reference, user["id"]),
            ).fetchone()
            if order is None:
                raise HTTPException(404, "Commande introuvable")

            # === Check commande refusee ===
            if order["status"] == "refusee":
                raise HTTPException(400, "Commande refusee : impossible de soumettre une preuve")

            payment = conn.execute(
                "SELECT * FROM payments WHERE order_id = ? ORDER BY id DESC LIMIT 1",
                (order["id"],),
            ).fetchone()
            if payment is None:
                raise HTTPException(400, "Initialisez le paiement d'abord")
            if payment["status"] == "VERIFIED":
                raise HTTPException(400, "Paiement deja verifie")
            if payment["status"] == "REJECTED":
                conn.execute(
                    "UPDATE payments SET status='PENDING', rejection_reason='' WHERE id=?",
                    (payment["id"],),
                )

                if order["status"] == "refusee":
                    raise HTTPException(400, "Commande refusee : impossible de soumettre une preuve")

            # Decoder le base64
            try:
                raw = payload.data_base64
                # Retirer un eventuel prefixe data:...
                if "," in raw and raw.strip().startswith("data:"):
                    raw = raw.split(",", 1)[1]
                data = base64.b64decode(raw)
            except Exception:
                raise HTTPException(400, "Donnees image invalides")

            if len(data) > MAX_PROOF_MB * 1024 * 1024:
                raise HTTPException(
                    400, "Fichier trop volumineux (max " + str(MAX_PROOF_MB) + " Mo)"
                )

            ext = Path(payload.filename or "proof").suffix.lower()
            if ext not in (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".pdf"):
                ext = ".jpg"
            fname = uuid.uuid4().hex + ext
            target = UPLOAD_DIR / fname
            target.write_bytes(data)

            now = datetime.now().isoformat(timespec="seconds")
            conn.execute(
                "UPDATE payments SET proof_file=?, status='PROOF_SUBMITTED', submitted_at=? WHERE id=?",
                ("/api/files/proofs/" + fname, now, payment["id"]),
            )
            conn.execute(
                "UPDATE orders SET payment_status='PROOF_SUBMITTED' WHERE id=?",
                (order["id"],),
            )
            conn.commit()
            # SSE : notifier PHARMACIEN + ADMIN qu'une preuve a ete soumise
            _notify_admins_proof(conn, order, reference)

            updated = conn.execute(
                "SELECT * FROM payments WHERE id = ?", (payment["id"],)
            ).fetchone()
        finally:
            conn.close()
        return _row(updated)



    @app.post("/api/orders/{reference}/payment/proof-binary")
    async def upload_proof_binary(reference: str, request: Request,
                                  user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        """Upload binaire direct : un seul POST, pas de base64, pas de multipart."""
        import base64
        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE reference = ? AND user_id = ?",
                (reference, user["id"]),
            ).fetchone()
            if order is None:
                raise HTTPException(404, "Commande introuvable")

            # === Check commande refusee ===
            if order["status"] == "refusee":
                raise HTTPException(400, "Commande refusee : impossible de soumettre une preuve")

            payment = conn.execute(
                "SELECT * FROM payments WHERE order_id = ? ORDER BY id DESC LIMIT 1",
                (order["id"],),
            ).fetchone()
            if payment is None:
                raise HTTPException(400, "Initialisez le paiement d'abord")
            if payment["status"] == "VERIFIED":
                raise HTTPException(400, "Paiement deja verifie")
            if payment["status"] == "REJECTED":
                conn.execute(
                    "UPDATE payments SET status='PENDING', rejection_reason='' WHERE id=?",
                    (payment["id"],),
                )

                if order["status"] == "refusee":
                    raise HTTPException(400, "Commande refusee : impossible de soumettre une preuve")

            # Lire les donnees brutes
            data = await request.body()
            if len(data) == 0:
                raise HTTPException(400, "Fichier vide")
            if len(data) > MAX_PROOF_MB * 1024 * 1024:
                raise HTTPException(
                    400, "Fichier trop volumineux (max " + str(MAX_PROOF_MB) + " Mo)"
                )

            # Nom du fichier : header X-Filename (base64 pour eviter les problemes d'encoding)
            raw_name = request.headers.get("x-filename", "")
            try:
                filename = base64.b64decode(raw_name).decode("utf-8") if raw_name else "proof.jpg"
            except Exception:
                filename = "proof.jpg"

            ext = Path(filename).suffix.lower()
            if ext not in (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".pdf"):
                ext = ".jpg"
            fname = uuid.uuid4().hex + ext
            target = UPLOAD_DIR / fname
            target.write_bytes(data)

            now = datetime.now().isoformat(timespec="seconds")
            conn.execute(
                "UPDATE payments SET proof_file=?, status='PROOF_SUBMITTED', submitted_at=? WHERE id=?",
                ("/api/files/proofs/" + fname, now, payment["id"])
            )
            conn.execute(
                "UPDATE orders SET payment_status='PROOF_SUBMITTED' WHERE id=?",
                (order["id"],)
            )
            conn.commit()
            # SSE : notifier PHARMACIEN + ADMIN qu'une preuve a ete soumise
            _notify_admins_proof(conn, order, reference)

            updated = conn.execute(
                "SELECT * FROM payments WHERE id = ?", (payment["id"],)
            ).fetchone()
        finally:
            conn.close()
        return _row(updated)

    @app.post("/api/orders/{reference}/payment/proof-chunked/init")
    def chunked_init(reference: str, payload: ChunkInit,
                     user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        """Demarre un upload par morceaux."""
        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE reference = ? AND user_id = ?",
                (reference, user["id"]),
            ).fetchone()
            if order is None:
                raise HTTPException(404, "Commande introuvable")

            # === Check commande refusee ===
            if order["status"] == "refusee":
                raise HTTPException(400, "Commande refusee : impossible de soumettre une preuve")

            payment = conn.execute(
                "SELECT * FROM payments WHERE order_id = ? ORDER BY id DESC LIMIT 1",
                (order["id"],),
            ).fetchone()
            if payment is None:
                raise HTTPException(400, "Initialisez le paiement d'abord")
            if payment["status"] == "VERIFIED":
                raise HTTPException(400, "Paiement deja verifie")
            if payment["status"] == "REJECTED":
                conn.execute(
                    "UPDATE payments SET status='PENDING', rejection_reason='' WHERE id=?",
                    (payment["id"],),
                )

            # Limiter la taille totale
            if payload.total_bytes > MAX_PROOF_MB * 1024 * 1024:
                raise HTTPException(
                    400, "Fichier trop volumineux (max " + str(MAX_PROOF_MB) + " Mo)"
                )

            upload_id = uuid.uuid4().hex
            now = datetime.now().isoformat(timespec="seconds")
            conn.execute(
                "INSERT INTO pending_uploads (id, order_id, payment_id, user_id,"
                " filename, content_type, total_chunks, received_chunks, data_base64, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, 0, '', ?)",
                (upload_id, order["id"], payment["id"], user["id"],
                 payload.filename, payload.content_type,
                 max(1, payload.total_chunks), now)
            )
            conn.commit()
        finally:
            conn.close()
        return {"upload_id": upload_id}


    @app.post("/api/orders/{reference}/payment/proof-chunked/chunk")
    def chunked_upload(reference: str, payload: ChunkData,
                       user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        """Recoit un morceau."""
        conn = get_db()
        try:
            up = conn.execute(
                "SELECT * FROM pending_uploads WHERE id=? AND user_id=?",
                (payload.upload_id, user["id"]),
            ).fetchone()
            if up is None:
                raise HTTPException(404, "Upload introuvable")

            # === Check commande refusee ===
            _ord = conn.execute(
                "SELECT status FROM orders WHERE id = ?",
                (up["order_id"],),
            ).fetchone()
            if _ord and _ord["status"] == "refusee":
                raise HTTPException(400, "Commande refusee : impossible de soumettre une preuve")

            # Concatener le morceau
            new_data = (up["data_base64"] or "") + payload.data_base64
            # Limiter la taille totale en memoire
            if len(new_data) > MAX_PROOF_MB * 2 * 1024 * 1024:
                raise HTTPException(400, "Fichier trop volumineux")

            conn.execute(
                "UPDATE pending_uploads SET data_base64=?, received_chunks=received_chunks+1"
                " WHERE id=?",
                (new_data, payload.upload_id)
            )
            conn.commit()
            received = up["received_chunks"] + 1
            total = up["total_chunks"]
        finally:
            conn.close()
        return {"received": received, "total": total}


    @app.post("/api/orders/{reference}/payment/proof-chunked/finalize")
    def chunked_finalize(reference: str, payload: ChunkFinalize,
                         user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        """Assemble les morceaux et enregistre la preuve."""
        conn = get_db()
        try:
            up = conn.execute(
                "SELECT * FROM pending_uploads WHERE id=? AND user_id=?",
                (payload.upload_id, user["id"]),
            ).fetchone()
            if up is None:
                raise HTTPException(404, "Upload introuvable")

            # === Check commande refusee ===
            _ord = conn.execute(
                "SELECT status FROM orders WHERE id = ?",
                (up["order_id"],),
            ).fetchone()
            if _ord and _ord["status"] == "refusee":
                raise HTTPException(400, "Commande refusee : impossible de soumettre une preuve")

            # Decoder le base64 complet
            try:
                raw = up["data_base64"] or ""
                data = base64.b64decode(raw)
            except Exception:
                raise HTTPException(400, "Donnees invalides")

            if len(data) == 0:
                raise HTTPException(400, "Fichier vide")
            if len(data) > MAX_PROOF_MB * 1024 * 1024:
                raise HTTPException(400, "Fichier trop volumineux")

            ext = Path(up["filename"] or "proof").suffix.lower()
            if ext not in (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".pdf"):
                ext = ".jpg"
            fname = uuid.uuid4().hex + ext
            target = UPLOAD_DIR / fname
            target.write_bytes(data)

            now = datetime.now().isoformat(timespec="seconds")
            conn.execute(
                "UPDATE payments SET proof_file=?, status='PROOF_SUBMITTED', submitted_at=? WHERE id=?",
                ("/api/files/proofs/" + fname, now, up["payment_id"])
            )
            conn.execute(
                "UPDATE orders SET payment_status='PROOF_SUBMITTED' WHERE id=?",
                (up["order_id"],)
            )
            # Supprimer l'upload temporaire
            conn.execute("DELETE FROM pending_uploads WHERE id=?", (payload.upload_id,))
            conn.commit()
            updated = conn.execute(
                "SELECT * FROM payments WHERE id=?", (up["payment_id"],)
            ).fetchone()
        finally:
            conn.close()
        return _row(updated)


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
            fname_lower = (file.filename or "").lower()
            # Accepter si le MIME est OK OU si l'extension est reconnue
            ext_ok = any(fname_lower.endswith(e) for e in
                         (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".pdf"))
            if ctype not in ALLOWED_PROOF_TYPES and not ext_ok:
                raise HTTPException(
                    400,
                    "Format non accepte. Utilisez JPG, PNG, WEBP, HEIC ou PDF."
                )

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
                ("/api/files/proofs/" + fname, now, payment["id"]),
            )
            conn.execute(
                "UPDATE orders SET payment_status='PROOF_SUBMITTED' WHERE id=?",
                (order["id"],),
            )
            conn.commit()
            # SSE : notifier PHARMACIEN + ADMIN qu'une preuve a ete soumise
            _notify_admins_proof(conn, order, reference)

            updated = conn.execute(
                "SELECT * FROM payments WHERE id = ?", (payment["id"],)
            ).fetchone()
        finally:
            conn.close()
        return _row(updated)

    

    @app.patch("/api/payments/{payment_id}/refund")
    def mark_refunded(payment_id: int,
                      user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        """Marque un paiement REFUND_REQUIRED comme rembourse (manuel)."""
        conn = get_db()
        try:
            pay = conn.execute(
                "SELECT * FROM payments WHERE id = ?", (payment_id,)
            ).fetchone()
            if pay is None:
                raise HTTPException(404, "Paiement introuvable")
            if pay["status"] != "REFUND_REQUIRED":
                raise HTTPException(400, "Paiement non en attente de remboursement")
            now = datetime.now().isoformat(timespec="seconds")
            conn.execute(
                "UPDATE payments SET status='REFUNDED', verified_at=?, verified_by=?,"
                " rejection_reason=COALESCE(rejection_reason,'') || ' | Rembourse le ' || ?"
                " WHERE id=?",
                (now, user["id"], now, payment_id),
            )
            conn.execute(
                "UPDATE orders SET payment_status='REFUNDED' WHERE id=?",
                (pay["order_id"],),
            )
            try:
                from main import log_audit as _la
                _la(conn, user["id"], "payment.refund", "payment", payment_id, "")
            except Exception:
                pass
            conn.commit()
            updated = conn.execute(
                "SELECT * FROM payments WHERE id = ?", (payment_id,)
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
                raise HTTPException(400,
            "Ce paiement a deja ete traite (statut actuel : " + pay["status"] + ")."
            " Rafraichissez la page pour voir l'etat actuel.")

            # ETAPE 4 : verifier que la commande n'est pas refusee
            _order_check = conn.execute(
                "SELECT status FROM orders WHERE id = ?", (pay["order_id"],)
            ).fetchone()
            if _order_check and _order_check["status"] == "refusee":
                raise HTTPException(400, "Commande refusee : impossible de valider le paiement")
            now = datetime.now().isoformat(timespec="seconds")
            conn.execute(
                "UPDATE payments SET status='VERIFIED', verified_at=?, verified_by=?"
                " WHERE id=?",
                (now, user["id"], payment_id),
            )
            try:
                from main import log_audit as _la
                _la(conn, user["id"], "payment.verify", "payment", payment_id, "")
            except Exception:
                pass
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
            try:
                from main import log_audit as _la
                _la(conn, user["id"], "payment.reject", "payment", payment_id,
                    payload.rejection_reason.strip()[:200])
            except Exception:
                pass
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


