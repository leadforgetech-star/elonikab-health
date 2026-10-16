"""Timeline dynamique d'une commande (V6)."""
from fastapi import Depends, HTTPException

# Mapping FR pour les statuts paiement
PAYMENT_LABELS_FR = {
    "NONE": "Aucun",
    "PENDING": "En attente",
    "PROOF_SUBMITTED": "Preuve soumise",
    "VERIFIED": "Verifie",
    "REJECTED": "Refuse",
    "REFUND_REQUIRED": "Remboursement requis",
    "REFUNDED": "Rembourse",
}


def _pay_label_fr(status):
    if not status:
        return "Aucun"
    return PAYMENT_LABELS_FR.get(str(status).upper(), status)




STATUS_LABELS = {
    "en_attente": "En attente",
    "confirmee": "Confirmee",
    "en_preparation": "En preparation",
    "prete": "Prete",
    "en_livraison": "En livraison",
    "terminee": "Terminee",
    "refusee": "Refusee",
    "created": "Demande recue",
}

PAYMENT_STATUS_LABELS = {
    "NONE": "Non initie",
    "PENDING": "Paiement a effectuer",
    "PROOF_SUBMITTED": "Preuve en verification",
    "VERIFIED": "Paiement verifie",
    "REJECTED": "Paiement refuse",
}

PRESCRIPTION_STATUS_LABELS = {
    "NONE": "Aucune ordonnance",
    "PENDING": "Ordonnance a verifier",
    "UNDER_REVIEW": "Ordonnance en cours de revue",
    "APPROVED": "Ordonnance approuvee",
    "NEEDS_REVIEW": "Ordonnance a completer",
    "REJECTED": "Ordonnance refusee",
}


def _row(r):
    return {k: r[k] for k in r.keys()} if r else None


def install_order_timeline(app, get_db, require_role):
    @app.get("/api/orders/{reference}/timeline")
    def get_timeline(reference: str):
        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE reference=?", (reference,)
            ).fetchone()
            if order is None:
                raise HTTPException(404, "Commande introuvable")

            # Events depuis order_status_history
            history = conn.execute(
                "SELECT * FROM order_status_history WHERE order_id=?"
                " ORDER BY changed_at ASC, id ASC",
                (order["id"],)
            ).fetchall()

            # Paiement
            payment = conn.execute(
                "SELECT * FROM payments WHERE order_id=?"
                " ORDER BY id DESC LIMIT 1",
                (order["id"],)
            ).fetchone()

            # Ordonnance
            prescription = conn.execute(
                "SELECT * FROM prescriptions WHERE order_id=?"
                " ORDER BY id DESC LIMIT 1",
                (order["id"],)
            ).fetchone()

            # Items
            items = conn.execute(
                "SELECT * FROM order_items WHERE order_id=? ORDER BY id",
                (order["id"],)
            ).fetchall()
            if not items:
                # Commande V1 mono-produit
                if order["product_name"]:
                    items = [{
                        "id": 0,
                        "product_id": order["product_id"],
                        "product_name": order["product_name"],
                        "unit_price": order["price"] or 0,
                        "quantity": order["quantity"] or 1,
                        "subtotal": (order["price"] or 0) * (order["quantity"] or 1),
                    }]

            # Construire la timeline
            events = []

            # 1. Creation
            events.append({
                "key": "created",
                "label": "Demande recue",
                "hint": "Votre demande a ete enregistree par Elonikab Health.",
                "at": order["created_at"],
                "state": "done",
            })

            # 2. Paiement initie (si existe)
            if payment and payment["created_at"]:
                events.append({
                    "key": "payment_init",
                    "label": "Paiement initie",
                    "hint": "Les informations de paiement ont ete preparees.",
                    "at": payment["created_at"],
                    "state": "done",
                })

            # 3. Preuve envoyee
            if payment and payment["submitted_at"]:
                events.append({
                    "key": "payment_proof",
                    "label": "Preuve envoyee",
                    "hint": "Votre preuve de paiement est en cours de verification.",
                    "at": payment["submitted_at"],
                    "state": "done",
                })

            # 4. Paiement verifie / refuse
            if payment and payment["verified_at"]:
                if payment["status"] == "VERIFIED":
                    events.append({
                        "key": "payment_verified",
                        "label": "Paiement verifie",
                        "hint": "Votre paiement a ete confirme.",
                        "at": payment["verified_at"],
                        "state": "done",
                    })
                elif payment["status"] == "REJECTED":
                    events.append({
                        "key": "payment_rejected",
                        "label": "Paiement refuse",
                        "hint": payment["rejection_reason"] or "Motif non precise",
                        "at": payment["verified_at"],
                        "state": "error",
                    })

            # 5. Ordonnance (si applicable)
            if prescription:
                events.append({
                    "key": "prescription",
                    "label": PRESCRIPTION_STATUS_LABELS.get(prescription["status"], prescription["status"]),
                    "hint": "",
                    "at": prescription["reviewed_at"] or prescription["created_at"],
                    "state": "done" if prescription["status"] == "APPROVED" else (
                        "error" if prescription["status"] == "REJECTED" else "current"
                    ),
                })

            # 6. Evenements de statut depuis l'historique
            for h in history:
                if h["to_status"] == "created":
                    continue  # deja affiche
                events.append({
                    "key": "status_" + str(h["id"]),
                    "label": STATUS_LABELS.get(h["to_status"], h["to_status"]),
                    "hint": h["note"] or "",
                    "at": h["changed_at"],
                    "state": "done" if h["to_status"] != order["status"] else "current",
                })

            # Trier par date (les None en dernier)
            events.sort(key=lambda e: e["at"] or "9999")

            # Determiner l'etape actuelle
            current_status = order["status"]
            payment_status = order["payment_status"] or "PENDING"

            return {
                "reference": order["reference"],
                "status": current_status,
                "status_label": STATUS_LABELS.get(current_status, current_status),
                "payment_status": payment_status,
                "payment_status_label": _pay_label_fr(payment_status),
                "prescription_status": order["prescription_status"] or "NONE",
                "delivery_mode": order["delivery_mode"],
                "delivery_vehicle_type": order["delivery_vehicle_type"],
                "customer_name": order["customer_name"],
                "phone": order["phone"],
                "address": order["address"] or "",
                "created_at": order["created_at"],
                "subtotal": float(order["subtotal"] or 0),
                "delivery_fee": float(order["delivery_fee"] or 0),
                "delivery_distance_km": order["delivery_distance_km"],
                "total": round(float(order["subtotal"] or 0) + float(order["delivery_fee"] or 0), 2),
                "items": [_row(i) for i in items],
                "events": events,
                "payment": _row(payment) if payment else None,
                "can_pay": payment_status in ("PENDING", "REJECTED") and current_status != "refusee",
                "can_reorder": True,
            }
        finally:
            conn.close()


