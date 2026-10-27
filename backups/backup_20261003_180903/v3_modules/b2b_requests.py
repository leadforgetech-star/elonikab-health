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


class RequestItemUpdate(BaseModel):
    description: Optional[str] = None
    requested_quantity: Optional[float] = None
    notes: Optional[str] = None


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

    @app.post("/api/pro/requests/{reference}/submit")
    def submit_request(reference: str, user=Depends(require_role("PROFESSIONNEL"))):
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

            n_items = conn.execute(
                "SELECT COUNT(*) FROM request_items WHERE request_id=?", (req["id"],)
            ).fetchone()[0]
            n_atts = conn.execute(
                "SELECT COUNT(*) FROM request_attachments WHERE request_id=?", (req["id"],)
            ).fetchone()[0]
            if n_items == 0 and n_atts == 0:
                raise HTTPException(
                    400, "Ajoutez au moins un produit ou une piece jointe"
                )

            conn.execute(
                "UPDATE requests SET status='SUBMITTED', updated_at=? WHERE id=?",
                (_now(), req["id"]),
            )
            conn.commit()

            # Notifier la pharmacie (notification interne)
            try:
                from v3_modules.notifications import push_notification
                admins = conn.execute(
                    "SELECT id FROM users WHERE role IN ('PHARMACIEN', 'ADMIN')"
                ).fetchall()
                for a in admins:
                    push_notification(
                        conn, a["id"],
                        "Nouvelle demande pro",
                        "Demande " + reference + " recue",
                    )
                conn.commit()
            except Exception:
                pass

            row = conn.execute("SELECT * FROM requests WHERE id=?", (req["id"],)).fetchone()
        finally:
            conn.close()
        return _row(row)

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
            lines.append("📋 *Demande de produits — Elokinab Health*")
            lines.append("")
            lines.append("🆔 Référence : " + req["reference"])
            if org and org["structure_name"]:
                lines.append("🏥 Établissement : " + org["structure_name"])
            lines.append("")
            lines.append("Bonjour Elokinab Health,")
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


