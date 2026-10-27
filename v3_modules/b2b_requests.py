"""Routes API B2B : organisations, demandes, items, pieces jointes."""
import re
import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

VALID_ITEM_AVAILABILITY = {"DISPONIBLE", "STOCK_LIMITE", "A_CONFIRMER", "INDISPONIBLE"}
VALID_REQUEST_STATUS = {
    "DRAFT", "SUBMITTED", "UNDER_REVIEW",
    "CONFIRMED", "PARTIALLY_CONFIRMED", "REJECTED"
}
ALLOWED_ATTACHMENT_TYPES = {
    "application/pdf": "pdf",
    "image/jpeg": "photo",
    "image/jpg": "photo",
    "image/png": "photo",
    "image/webp": "photo",
}
MAX_ATTACHMENT_MB = 15


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    responsible: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    delivery_address: Optional[str] = None
    delivery_instructions: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class RequestCreate(BaseModel):
    notes: str = ""


class RequestItemCreate(BaseModel):
    product_id: Optional[int] = None
    description: str
    requested_quantity: float = 1
    notes: str = ""


class SubmitRequestPayload(BaseModel):
    delivery_mode: str = "retrait"  # retrait | livraison
    address: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_accuracy: Optional[float] = None
    notes: str = ""


class RequestItemUpdate(BaseModel):
    description: Optional[str] = None
    requested_quantity: Optional[float] = None
    notes: Optional[str] = None




# ============================================================
# Helpers livraison (Haversine + tarifs VOITURE pour pros)
# ============================================================

def _haversine_km(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, asin, sqrt
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))


def _compute_delivery_fee_pro(conn, client_lat, client_lon, units=1, distinct_lines=1, amount=0.0):
    """Version PRO : utilise compute_delivery_fee_v2 (moto/voiture selon seuils).
    Retourne (fee, distance_km, source, vehicle_type).
    Compatible avec les appels existants mais retourne un 4e element.
    """
    try:
        # Importer la fonction v2 de main.py
        from main import compute_delivery_fee_v2
        fee, dist, vehicle, reason = compute_delivery_fee_v2(
            client_lat, client_lon, units, distinct_lines, amount
        )
        if vehicle is None:
            return None, dist, "no_vehicle", None
        # Source : "gps" si on a pu calculer, "no_gps" sinon
        source = "gps" if dist is not None else "no_gps"
        return fee, dist, source, vehicle
    except Exception as e:
        # Fallback : ancienne logique voiture uniquement
        print(f"[_compute_delivery_fee_pro] erreur v2 : {e}")
        s = conn.execute("SELECT * FROM pharmacy_settings WHERE id = 1").fetchone()
        if not s:
            return 0.0, None, "no_settings", "CAR"
        ph_lat = s["pharmacy_latitude"]
        ph_lon = s["pharmacy_longitude"]
        if client_lat is None or client_lon is None or ph_lat is None or ph_lon is None:
            return float(s["delivery_fee_default"] or 1000), None, "no_gps", "CAR"
        from math import radians, sin, cos, asin, sqrt
        R = 6371.0
        dlat = radians(float(client_lat) - float(ph_lat))
        dlon = radians(float(client_lon) - float(ph_lon))
        a = sin(dlat/2)**2 + cos(radians(float(ph_lat))) * cos(radians(float(client_lat))) * sin(dlon/2)**2
        dist = 2 * R * asin(sqrt(a))
        base = float(s["car_base_fee"] or 1000)
        per_km = float(s["car_price_per_km"] or 250)
        min_fee = float(s["car_minimum_fee"] or 1000)
        fee = base + dist * per_km
        if fee < min_fee:
            fee = min_fee
        fee = round(fee / 50.0) * 50
        return float(fee), round(dist, 2), "gps", "CAR"


def _row(r):
    return {k: r[k] for k in r.keys()} if r else None


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _gen_ref(conn):
    """Reference unique : DEM-YYMMDD-XXXXXX"""
    for _ in range(20):
        ref = "DEM-" + datetime.now().strftime("%y%m%d") + "-" + secrets.token_hex(3).upper()
        exists = conn.execute("SELECT id FROM requests WHERE reference=?", (ref,)).fetchone()
        if not exists:
            return ref
    raise RuntimeError("Impossible de generer une reference unique")


def _get_org_id(conn, user_id):
    """Recupere l'organization_id du user.
    - Si users.organization_id existe -> le retourne
    - Sinon, cherche un professional_profile existant -> l'utilise
    - Sinon, en cree un nouveau
    """
    user = conn.execute(
        "SELECT id, organization_id, role FROM users WHERE id=?", (user_id,)
    ).fetchone()
    if user is None:
        raise HTTPException(401, "Utilisateur inconnu")

    # Cas 1 : deja lie
    if user["organization_id"]:
        return user["organization_id"]

    # Cas 2 : chercher un profil existant pour ce user
    prof = conn.execute(
        "SELECT id FROM professional_profiles WHERE user_id=?", (user_id,)
    ).fetchone()

    if prof:
        # Profil existant : utiliser son id comme org_id et mettre a jour users
        org_id = prof["id"]
        conn.execute(
            "UPDATE users SET organization_id=? WHERE id=?",
            (org_id, user_id)
        )
        conn.commit()
        return org_id

    # Cas 3 : aucun profil -> en creer un
    now = _now()
    cur = conn.execute(
        "INSERT INTO professional_profiles"
        " (user_id, structure_name, structure_type, manager_name, phone, email,"
        "  address, latitude, longitude, status, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'APPROVED', ?)",
        (user_id, "Organisation", "AUTRE", "", "", "", "", None, None, now),
    )
    org_id = cur.lastrowid
    conn.execute(
        "UPDATE users SET organization_id=? WHERE id=?",
        (org_id, user_id)
    )
    conn.commit()
    return org_id


def install_b2b(app, get_db, require_role, uploads_dir):
    UPLOAD_DIR = Path(uploads_dir) / "requests"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # ============================================================
    # ORGANISATION
    # ============================================================

    @app.get("/api/pro/organizations/me")
    def get_org(user=Depends(require_role("PROFESSIONNEL"))):
        conn = get_db()
        try:
            oid = _get_org_id(conn, user["id"])
            row = conn.execute(
                "SELECT * FROM professional_profiles WHERE id=?", (oid,)
            ).fetchone()
        finally:
            conn.close()
        return _row(row)

    @app.patch("/api/pro/organizations/me")
    def update_org(payload: OrganizationUpdate,
                   user=Depends(require_role("PROFESSIONNEL"))):
        conn = get_db()
        try:
            oid = _get_org_id(conn, user["id"])
            fields = payload.dict(exclude_unset=True, exclude_none=True)
            if not fields:
                row = conn.execute(
                    "SELECT * FROM professional_profiles WHERE id=?", (oid,)
                ).fetchone()
                return _row(row)

            # Map organization fields -> professional_profiles columns
            column_map = {
                "name": "structure_name",
                "type": "structure_type",
                "responsible": "manager_name",
                "phone": "phone",
                "email": "email",
                "address": "address",
                "delivery_address": "delivery_address",
                "delivery_instructions": "delivery_instructions",
                "latitude": "latitude",
                "longitude": "longitude",
            }
            sets = []
            params = []
            for k, v in fields.items():
                col = column_map.get(k)
                if col:
                    sets.append(col + " = ?")
                    params.append(v)
            if sets:
                params.append(oid)
                conn.execute(
                    "UPDATE professional_profiles SET " + ", ".join(sets)
                    + " WHERE id=?", params
                )
                conn.commit()
            row = conn.execute(
                "SELECT * FROM professional_profiles WHERE id=?", (oid,)
            ).fetchone()
        finally:
            conn.close()
        return _row(row)

    # ============================================================
    # DEMANDES
    # ============================================================

    @app.get("/api/pro/requests")
    def list_requests(user=Depends(require_role("PROFESSIONNEL"))):
        conn = get_db()
        try:
            oid = _get_org_id(conn, user["id"])
            rows = conn.execute(
                "SELECT r.*,"
                " (SELECT COUNT(*) FROM request_items ri WHERE ri.request_id=r.id) AS items_count,"
                " (SELECT COUNT(*) FROM request_attachments ra WHERE ra.request_id=r.id) AS attachments_count"
                " FROM requests r WHERE r.organization_id=?"
                " ORDER BY r.id DESC LIMIT 100",
                (oid,),
            ).fetchall()
        finally:
            conn.close()
        return [_row(r) for r in rows]

    @app.get("/api/pro/requests/draft")
    def get_or_create_draft(user=Depends(require_role("PROFESSIONNEL"))):
        """Retourne la demande DRAFT en cours, ou en cree une."""
        conn = get_db()
        try:
            oid = _get_org_id(conn, user["id"])
            draft = conn.execute(
                "SELECT * FROM requests WHERE organization_id=? AND status='DRAFT'"
                " ORDER BY id DESC LIMIT 1",
                (oid,),
            ).fetchone()
            if draft is None:
                ref = _gen_ref(conn)
                cur = conn.execute(
                    "INSERT INTO requests (reference, organization_id, user_id,"
                    " status, notes, source_summary, created_at)"
                    " VALUES (?, ?, ?, 'DRAFT', '', '', ?)",
                    (ref, oid, user["id"], _now()),
                )
                conn.commit()
                draft = conn.execute(
                    "SELECT * FROM requests WHERE id=?", (cur.lastrowid,)
                ).fetchone()
            return _row(draft)
        finally:
            conn.close()

    @app.get("/api/pro/requests/{reference}")
    def get_request(reference: str, user=Depends(require_role("PROFESSIONNEL"))):
        conn = get_db()
        try:
            oid = _get_org_id(conn, user["id"])
            req = conn.execute(
                "SELECT * FROM requests WHERE reference=? AND organization_id=?",
                (reference, oid),
            ).fetchone()
            if req is None:
                raise HTTPException(404, "Demande introuvable")
            items = conn.execute(
                "SELECT * FROM request_items WHERE request_id=? ORDER BY id",
                (req["id"],),
            ).fetchall()
            attachments = conn.execute(
                "SELECT * FROM request_attachments WHERE request_id=? ORDER BY id",
                (req["id"],),
            ).fetchall()
            result = _row(req)
            result["items"] = [_row(i) for i in items]
            result["attachments"] = [_row(a) for a in attachments]
        finally:
            conn.close()
        return result

    @app.patch("/api/pro/requests/{reference}")
    def update_request(reference: str, payload: RequestCreate,
                       user=Depends(require_role("PROFESSIONNEL"))):
        conn = get_db()
        try:
            oid = _get_org_id(conn, user["id"])
            req = conn.execute(
                "SELECT id, status FROM requests WHERE reference=? AND organization_id=?",
                (reference, oid),
            ).fetchone()
            if req is None:
                raise HTTPException(404, "Demande introuvable")
            if req["status"] != "DRAFT":
                raise HTTPException(400, "Demande deja soumise")
            conn.execute(
                "UPDATE requests SET notes=?, updated_at=? WHERE id=?",
                (payload.notes, _now(), req["id"]),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM requests WHERE id=?", (req["id"],)).fetchone()
        finally:
            conn.close()
        return _row(row)

    # ============================================================
    # ITEMS
    # ============================================================

    @app.post("/api/pro/requests/{reference}/items")
    def add_item(reference: str, payload: RequestItemCreate,
                 user=Depends(require_role("PROFESSIONNEL"))):
        if not payload.description.strip():
            raise HTTPException(400, "Description obligatoire")
        conn = get_db()
        try:
            oid = _get_org_id(conn, user["id"])
            req = conn.execute(
                "SELECT id, status FROM requests WHERE reference=? AND organization_id=?",
                (reference, oid),
            ).fetchone()
            if req is None:
                raise HTTPException(404, "Demande introuvable")
            if req["status"] != "DRAFT":
                raise HTTPException(400, "Demande deja soumise")

            # Si product_id fourni, verifier
            if payload.product_id:
                p = conn.execute(
                    "SELECT id FROM products WHERE id=? AND is_active=1",
                    (payload.product_id,),
                ).fetchone()
                if p is None:
                    raise HTTPException(400, "Produit introuvable ou inactif")

            cur = conn.execute(
                "INSERT INTO request_items (request_id, product_id, description,"
                " requested_quantity, availability_status, notes, created_at)"
                " VALUES (?, ?, ?, ?, 'A_CONFIRMER', ?, ?)",
                (req["id"], payload.product_id, payload.description.strip(),
                 payload.requested_quantity, payload.notes.strip(), _now()),
            )
            conn.execute("UPDATE requests SET updated_at=? WHERE id=?", (_now(), req["id"]))
            conn.commit()
            row = conn.execute(
                "SELECT * FROM request_items WHERE id=?", (cur.lastrowid,)
            ).fetchone()
        finally:
            conn.close()
        return _row(row)

    @app.patch("/api/pro/requests/{reference}/items/{item_id}")
    def update_item(reference: str, item_id: int, payload: RequestItemUpdate,
                    user=Depends(require_role("PROFESSIONNEL"))):
        conn = get_db()
        try:
            oid = _get_org_id(conn, user["id"])
            req = conn.execute(
                "SELECT id, status FROM requests WHERE reference=? AND organization_id=?",
                (reference, oid),
            ).fetchone()
            if req is None:
                raise HTTPException(404, "Demande introuvable")
            if req["status"] != "DRAFT":
                raise HTTPException(400, "Demande deja soumise")

            item = conn.execute(
                "SELECT id FROM request_items WHERE id=? AND request_id=?",
                (item_id, req["id"]),
            ).fetchone()
            if item is None:
                raise HTTPException(404, "Article introuvable")

            sets = []
            params = []
            if payload.description is not None:
                sets.append("description = ?")
                params.append(payload.description.strip())
            if payload.requested_quantity is not None:
                sets.append("requested_quantity = ?")
                params.append(payload.requested_quantity)
            if payload.notes is not None:
                sets.append("notes = ?")
                params.append(payload.notes.strip())
            if sets:
                params.append(item_id)
                conn.execute(
                    "UPDATE request_items SET " + ", ".join(sets) + " WHERE id=?",
                    params,
                )
                conn.commit()
            row = conn.execute(
                "SELECT * FROM request_items WHERE id=?", (item_id,)
            ).fetchone()
        finally:
            conn.close()
        return _row(row)

    @app.delete("/api/pro/requests/{reference}/items/{item_id}")
    def delete_item(reference: str, item_id: int,
                    user=Depends(require_role("PROFESSIONNEL"))):
        conn = get_db()
        try:
            oid = _get_org_id(conn, user["id"])
            req = conn.execute(
                "SELECT id, status FROM requests WHERE reference=? AND organization_id=?",
                (reference, oid),
            ).fetchone()
            if req is None:
                raise HTTPException(404, "Demande introuvable")
            if req["status"] != "DRAFT":
                raise HTTPException(400, "Demande deja soumise")
            conn.execute(
                "DELETE FROM request_items WHERE id=? AND request_id=?",
                (item_id, req["id"]),
            )
            conn.commit()
        finally:
            conn.close()
        return {"ok": True}

    # ============================================================
    # PIECES JOINTES
    # ============================================================

    @app.post("/api/pro/requests/{reference}/attachments")
    async def upload_attachment(reference: str, file: UploadFile = File(...),
                                user=Depends(require_role("PROFESSIONNEL"))):
        conn = get_db()
        try:
            oid = _get_org_id(conn, user["id"])
            req = conn.execute(
                "SELECT id, status FROM requests WHERE reference=? AND organization_id=?",
                (reference, oid),
            ).fetchone()
            if req is None:
                raise HTTPException(404, "Demande introuvable")
            if req["status"] != "DRAFT":
                raise HTTPException(400, "Demande deja soumise")

            ctype = (file.content_type or "").lower()
            if ctype not in ALLOWED_ATTACHMENT_TYPES:
                raise HTTPException(
                    400, "Format non accepte (PDF, JPG, PNG, WEBP uniquement)"
                )

            data = await file.read()
            if len(data) > MAX_ATTACHMENT_MB * 1024 * 1024:
                raise HTTPException(
                    400, "Fichier trop volumineux (max " + str(MAX_ATTACHMENT_MB) + " Mo)"
                )

            ext = Path(file.filename or "file").suffix.lower()
            if not re.match(r"^\.[a-z0-9]{2,5}$", ext):
                ext = ".bin"
            fname = uuid.uuid4().hex + ext
            target = UPLOAD_DIR / fname
            target.write_bytes(data)

            atype = ALLOWED_ATTACHMENT_TYPES[ctype]
            cur = conn.execute(
                "INSERT INTO request_attachments (request_id, organization_id,"
                " type, original_filename, storage_path, mime_type, size_bytes, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (req["id"], oid, atype, file.filename or "",
                 "requests/" + fname, ctype, len(data), _now()),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM request_attachments WHERE id=?", (cur.lastrowid,)
            ).fetchone()
        finally:
            conn.close()
        return _row(row)

    @app.delete("/api/pro/requests/{reference}/attachments/{att_id}")
    def delete_attachment(reference: str, att_id: int,
                          user=Depends(require_role("PROFESSIONNEL"))):
        conn = get_db()
        try:
            oid = _get_org_id(conn, user["id"])
            req = conn.execute(
                "SELECT id, status FROM requests WHERE reference=? AND organization_id=?",
                (reference, oid),
            ).fetchone()
            if req is None:
                raise HTTPException(404, "Demande introuvable")
            if req["status"] != "DRAFT":
                raise HTTPException(400, "Demande deja soumise")
            att = conn.execute(
                "SELECT storage_path FROM request_attachments WHERE id=? AND request_id=?",
                (att_id, req["id"]),
            ).fetchone()
            if att is None:
                raise HTTPException(404, "Piece jointe introuvable")
            conn.execute("DELETE FROM request_attachments WHERE id=?", (att_id,))
            conn.commit()
            # Supprimer le fichier si present
            try:
                fpath = UPLOAD_DIR / Path(att["storage_path"]).name
                if fpath.exists():
                    fpath.unlink()
            except Exception:
                pass
        finally:
            conn.close()
        return {"ok": True}

    # ============================================================
    # SOUMISSION
    # ============================================================



    @app.get("/api/pro/requests/{reference}/summary")
    def get_request_summary(reference: str, user=Depends(require_role("PROFESSIONNEL"))):
        """Retourne la demande avec les prix actuels du catalogue et les totaux calcules."""
        conn = get_db()
        try:
            oid = _get_org_id(conn, user["id"])
            req = conn.execute(
                "SELECT * FROM requests WHERE reference=? AND organization_id=?",
                (reference, oid),
            ).fetchone()
            if req is None:
                raise HTTPException(404, "Demande introuvable")

            raw_items = conn.execute(
                "SELECT * FROM request_items WHERE request_id=? ORDER BY id",
                (req["id"],),
            ).fetchall()

            items = []
            subtotal = 0.0
            for it in raw_items:
                price = 0.0
                product_name = it["description"]
                if it["product_id"]:
                    p = conn.execute(
                        "SELECT price, name FROM products WHERE id=?",
                        (it["product_id"],),
                    ).fetchone()
                    if p:
                        price = float(p["price"] or 0)
                qty = float(it["requested_quantity"] or 0)
                line_total = round(price * qty, 2)
                subtotal += line_total
                items.append({
                    "id": it["id"],
                    "product_id": it["product_id"],
                    "description": it["description"],
                    "requested_quantity": qty,
                    "unit_price": price,
                    "line_total": line_total,
                    "confirmed_quantity": it["confirmed_quantity"],
                    "confirmed_unit_price": it["confirmed_unit_price"],
                    "notes": it["notes"] or "",
                })

            atts = conn.execute(
                "SELECT * FROM request_attachments WHERE request_id=? ORDER BY id",
                (req["id"],),
            ).fetchall()

            subtotal = round(subtotal, 2)

        finally:
            conn.close()

        return {
            "reference": reference,
            "status": req["status"],
            "notes": req["notes"] or "",
            "items": items,
            "items_count": len(items),
            "attachments_count": len(atts),
            "subtotal": subtotal,
            "delivery_fee": None,  # a confirmer par la pharmacie
            "total_estimate": subtotal,  # provisoire (livraison a confirmer)
            "message": "Sous-total base sur les prix actuels du catalogue. La pharmacie confirmera la disponibilite, les quantites et les prix finaux.",
        }



    @app.post("/api/pro/requests/{reference}/estimate-delivery")
    def estimate_delivery(reference: str, payload: SubmitRequestPayload,
                          user=Depends(require_role("PROFESSIONNEL"))):
        """Estime la distance et les frais de livraison selon la position GPS fournie."""
        if (payload.delivery_mode or "").lower() != "livraison":
            return {"distance_km": None, "delivery_fee": 0, "source": "retrait"}

        conn = get_db()
        try:
            oid = _get_org_id(conn, user["id"])
            req = conn.execute(
                "SELECT id FROM requests WHERE reference=? AND organization_id=?",
                (reference, oid),
            ).fetchone()
            if req is None:
                raise HTTPException(404, "Demande introuvable")

            # Calculer units, lines, amount depuis les items de la requete
            _items = conn.execute(
                "SELECT requested_quantity FROM request_items WHERE request_id=?",
                (req["id"],)
            ).fetchall()
            _units = sum(int(it["requested_quantity"] or 0) for it in _items)
            _lines = len(_items)
            _raw = conn.execute(
                "SELECT ri.requested_quantity, p.price"
                " FROM request_items ri"
                " LEFT JOIN products p ON p.id = ri.product_id"
                " WHERE ri.request_id=?",
                (req["id"],)
            ).fetchall()
            _amount = sum(float(r["price"] or 0) * float(r["requested_quantity"] or 0) for r in _raw)

            fee, dist, source, vehicle_type = _compute_delivery_fee_pro(
                conn, payload.latitude, payload.longitude,
                max(1, _units), max(1, _lines), _amount
            )
            if vehicle_type is None:
                raise HTTPException(400, "Aucun moyen de livraison disponible pour cette distance")

            # Calcul du sous-total pour info
            raw = conn.execute(
                "SELECT ri.requested_quantity, p.price"
                " FROM request_items ri"
                " LEFT JOIN products p ON p.id = ri.product_id"
                " WHERE ri.request_id=?",
                (req["id"],),
            ).fetchall()
            subtotal = 0.0
            for r in raw:
                if r["price"]:
                    subtotal += float(r["price"]) * float(r["requested_quantity"] or 0)
            subtotal = round(subtotal, 2)
        finally:
            conn.close()

        # Recuperer les tarifs utilises
        s = conn_settings = None
        try:
            conn_s = get_db()
            s = conn_s.execute(
                "SELECT car_base_fee, car_price_per_km, car_minimum_fee,"
                " delivery_fee_default"
                " FROM pharmacy_settings WHERE id=1"
            ).fetchone()
            conn_s.close()
        except Exception:
            s = None

        _v = vehicle_type if 'vehicle_type' in dir() else "CAR"
        if _v == "MOTO":
            rates = {
                "vehicle": "MOTO",
                "base_fee": float(s["motorbike_base_fee"] or 1200) if s else 1200,
                "price_per_km": float(s["motorbike_price_per_km"] or 100) if s else 100,
                "minimum_fee": float(s["motorbike_minimum_fee"] or 500) if s else 500,
                "fallback_fee": float(s["delivery_fee_default"] or 1000) if s else 1000,
                "rounding": 50,
            }
        else:
            rates = {
                "vehicle": "VOITURE",
                "base_fee": float(s["car_base_fee"] or 1000) if s else 1000,
                "price_per_km": float(s["car_price_per_km"] or 250) if s else 250,
                "minimum_fee": float(s["car_minimum_fee"] or 1000) if s else 1000,
                "fallback_fee": float(s["delivery_fee_default"] or 1000) if s else 1000,
                "rounding": 50,
            }

        return {
            "distance_km": dist,
            "delivery_fee": fee,
            "source": source,
            "vehicle_type": vehicle_type,
            "subtotal": subtotal,
            "total": round(subtotal + fee, 2) if source == "gps" else None,
            "rates": rates,
        }


    @app.post("/api/pro/requests/{reference}/submit")
    def submit_request(reference: str, payload: SubmitRequestPayload = None,
                       user=Depends(require_role("PROFESSIONNEL"))):
        if payload is None:
            payload = SubmitRequestPayload()

        import uuid
        import json as _json

        conn = get_db()
        try:
            oid = _get_org_id(conn, user["id"])
            req = conn.execute(
                "SELECT * FROM requests WHERE reference=? AND organization_id=?",
                (reference, oid),
            ).fetchone()
            if req is None:
                raise HTTPException(404, "Demande introuvable")
            if req["status"] != "DRAFT":
                raise HTTPException(400, "Demande deja soumise")

            items = conn.execute(
                "SELECT * FROM request_items WHERE request_id=? ORDER BY id",
                (req["id"],),
            ).fetchall()
            atts = conn.execute(
                "SELECT * FROM request_attachments WHERE request_id=? ORDER BY id",
                (req["id"],),
            ).fetchall()
            if len(items) == 0 and len(atts) == 0:
                raise HTTPException(400, "Ajoutez au moins un produit ou une piece jointe")

            mode = (payload.delivery_mode or "retrait").strip().lower()
            if mode not in ("retrait", "livraison"):
                raise HTTPException(400, "Mode de livraison invalide")
            if mode == "livraison" and not payload.address.strip() and payload.latitude is None:
                raise HTTPException(400, "Adresse ou GPS obligatoire pour la livraison")

            # Calcul frais livraison
            if mode == "livraison":
                delivery_fee, delivery_distance, _src, _vehicle = _compute_delivery_fee_pro(
                    conn, payload.latitude, payload.longitude
                , 1, 1, 0)
            else:
                delivery_fee, delivery_distance = 0.0, None

            # Sous-total (prix actuels du catalogue)
            subtotal = 0.0
            order_items = []
            first_product_id = None
            first_product_name = ""
            first_qty = 0
            first_price = 0.0
            for it in items:
                price = 0.0
                pname = it["description"]
                if it["product_id"]:
                    p = conn.execute(
                        "SELECT price, name FROM products WHERE id=?",
                        (it["product_id"],),
                    ).fetchone()
                    if p:
                        price = float(p["price"] or 0)
                        pname = it["description"] or p["name"]
                qty = float(it["requested_quantity"] or 0)
                line_total = round(price * qty, 2)
                subtotal += line_total
                order_items.append({
                    "product_id": it["product_id"],
                    "product_name": pname,
                    "unit_price": price,
                    "quantity": qty,
                    "subtotal": line_total,
                })
                if first_product_id is None:
                    first_product_id = it["product_id"]
                    first_product_name = pname
                    first_qty = qty
                    first_price = price

            subtotal = round(subtotal, 2)
            total = round(subtotal + delivery_fee, 2)

            # Recuperer les infos du client
            user_row = conn.execute(
                "SELECT full_name, phone FROM users WHERE id=?", (user["id"],)
            ).fetchone()
            prof = conn.execute(
                "SELECT structure_name, phone FROM professional_profiles WHERE id=?",
                (oid,),
            ).fetchone()

            customer_name = (prof["structure_name"] if prof else "") or (user_row["full_name"] if user_row else "")
            phone = (prof["phone"] if prof else "") or (user_row["phone"] if user_row else "")

            # Creer une commande (orders) a partir de la demande
            order_ref = "CMD-" + datetime.now().strftime("%y%m%d") + "-" + uuid.uuid4().hex[:6].upper()
            now = _now()

            cur = conn.execute(
                "INSERT INTO orders (reference, customer_name, phone, product_id,"
                " product_name, quantity, delivery_mode, address, prescription_file,"
                " status, created_at, latitude, longitude, location_accuracy,"
                " delivery_fee, delivery_distance_km, price, subtotal,"
                " user_id, customer_type, delivery_vehicle_type,"
                " payment_status, delivery_status, prescription_status,"
                " professional_id, request_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'en_attente', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,"
                " 'PENDING', 'NONE', 'NONE', ?, ?)",
                (
                    order_ref, customer_name, phone,
                    first_product_id, first_product_name or "Produit",
                    int(first_qty) or 1,
                    mode, payload.address.strip(), "",
                    now,
                    payload.latitude, payload.longitude, payload.location_accuracy,
                    delivery_fee, delivery_distance,
                    first_price, subtotal,
                    user["id"], "PROFESSIONNEL", "VOITURE",
                    oid, req["id"],
                ),
            )
            order_id = cur.lastrowid

            # Inserer les order_items
            for oi in order_items:
                conn.execute(
                    "INSERT INTO order_items (order_id, product_id, product_name,"
                    " unit_price, quantity, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
                    (order_id, oi["product_id"], oi["product_name"],
                     oi["unit_price"], oi["quantity"], oi["subtotal"]),
                )

            # Marquer la demande comme SUBMITTED
            summary = {
                "delivery_mode": mode,
                "address": payload.address.strip(),
                "latitude": payload.latitude,
                "longitude": payload.longitude,
                "order_ref": order_ref,
            }
            conn.execute(
                "UPDATE requests SET status='SUBMITTED', notes=?, source_summary=?, updated_at=?"
                " WHERE id=?",
                (payload.notes.strip(), _json.dumps(summary), now, req["id"]),
            )

            conn.commit()

            # Notifier la pharmacie
            try:
                from v3_modules.notifications import push_notification
                admins = conn.execute(
                    "SELECT id FROM users WHERE role IN ('PHARMACIEN', 'ADMIN')"
                ).fetchall()
                for a in admins:
                    push_notification(
                        conn, a["id"],
                        "Nouvelle commande pro",
                        order_ref + " — " + customer_name,
                    )
                conn.commit()
            except Exception:
                pass
        finally:
            conn.close()

        return {
            "request_reference": reference,
            "order_reference": order_ref,
            "delivery_mode": mode,
            "delivery_fee": delivery_fee,
            "delivery_distance_km": delivery_distance,
            "subtotal": subtotal,
            "total": total,
        }


    # ============================================================
    # WHATSAPP : generer le message
    # ============================================================

    @app.get("/api/pro/requests/{reference}/whatsapp")
    def whatsapp_message(reference: str, user=Depends(require_role("PROFESSIONNEL"))):
        conn = get_db()
        try:
            oid = _get_org_id(conn, user["id"])
            req = conn.execute(
                "SELECT * FROM requests WHERE reference=? AND organization_id=?",
                (reference, oid),
            ).fetchone()
            if req is None:
                raise HTTPException(404, "Demande introuvable")
            items = conn.execute(
                "SELECT * FROM request_items WHERE request_id=? ORDER BY id",
                (req["id"],),
            ).fetchall()
            atts = conn.execute(
                "SELECT * FROM request_attachments WHERE request_id=? ORDER BY id",
                (req["id"],),
            ).fetchall()
            org = conn.execute(
                "SELECT * FROM professional_profiles WHERE id=?", (oid,)
            ).fetchone()

            lines = []
            lines.append("📋 *Demande de produits — Elonikab Health*")
            lines.append("")
            lines.append("🆔 Référence : " + req["reference"])
            if org and org["structure_name"]:
                lines.append("🏥 Établissement : " + org["structure_name"])
            lines.append("")
            lines.append("Bonjour Elonikab Health,")
            lines.append("")
            if items:
                lines.append("Nous souhaitons obtenir les produits suivants :")
                lines.append("")
                for it in items:
                    qty = it["requested_quantity"]
                    qs = ""
                    if qty and float(qty) != 1:
                        qs = " × " + str(int(qty) if float(qty).is_integer() else qty)
                    elif qty and float(qty) == 1:
                        qs = " × 1"
                    lines.append("• " + it["description"] + qs)
                lines.append("")
            if atts:
                lines.append("Pièces jointes :")
                for a in atts:
                    lines.append("• " + a["type"].upper() + " — " + (a["original_filename"] or a["storage_path"]))
                lines.append("")
                lines.append("(Je joins les fichiers dans WhatsApp après ouverture.)")
                lines.append("")
            if req["notes"]:
                lines.append("📝 Notes : " + req["notes"])
                lines.append("")
            lines.append("Merci de nous communiquer la disponibilité et les informations correspondantes.")
            lines.append("")
            lines.append("Cordialement,")
            if org and org["structure_name"]:
                lines.append(org["structure_name"])

            message = "\n".join(lines)

            # Numero WhatsApp pharmacie (fallback)
            settings = conn.execute(
                "SELECT whatsapp_number, pharmacy_phone FROM pharmacy_settings WHERE id=1"
            ).fetchone()
            phone = ""
            if settings:
                phone = (settings["whatsapp_number"] or "").strip()
                if not phone:
                    phone = (settings["pharmacy_phone"] or "").strip()
            if not phone:
                phone = "+22871039904"
            digits = "".join(c for c in phone if c.isdigit())
            if not digits.startswith("228"):
                digits = "228" + digits
        finally:
            conn.close()

        return {
            "reference": reference,
            "message": message,
            "whatsapp_url": "https://wa.me/" + digits + "?text=" + message.replace(" ", "%20").replace("\n", "%0A"),
            "phone": digits,
        }


