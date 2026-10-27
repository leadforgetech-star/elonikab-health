"""
v4_b2b_complete.py
Backend + Frontend B2B complet.
- Routes /api/pro/* (organisations, demandes, items, pièces jointes)
- Page /professionnel refondue avec demande en cours
- Navigation mobile basse : Accueil | Catalogue | + Demande | Commandes | Établissement
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
MODULES = BASE / "v3_modules"
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_b2b_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAIN, backup / "main.py")
for f in ("professional.html", "professional.js", "header.js"):
    p = STATIC / f
    if p.exists():
        shutil.copy2(p, backup / f)
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. MODULE BACKEND : v3_modules/b2b_requests.py
# ============================================================
B2B = '''"""Routes API B2B : organisations, demandes, items, pieces jointes."""
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
    """Recupere l'organization_id du user (cree une org si pro sans org)."""
    user = conn.execute(
        "SELECT id, organization_id, role FROM users WHERE id=?", (user_id,)
    ).fetchone()
    if user is None:
        raise HTTPException(401, "Utilisateur inconnu")

    if user["organization_id"]:
        return user["organization_id"]

    # Chercher un professional_profile existant
    prof = conn.execute(
        "SELECT id, structure_name, structure_type, manager_name, phone, email,"
        " address, latitude, longitude, delivery_address, delivery_instructions"
        " FROM professional_profiles WHERE user_id=?", (user_id,)
    ).fetchone()

    # Creer une organisation
    name = (prof["structure_name"] if prof else "") or "Organisation"
    otype = (prof["structure_type"] if prof else "AUTRE")
    cur = conn.execute(
        "INSERT INTO professional_profiles"
        " (user_id, structure_name, structure_type, manager_name, phone, email,"
        "  address, latitude, longitude, status, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'APPROVED', ?)",
        (user_id, name, otype,
         (prof["manager_name"] if prof else "") or "",
         (prof["phone"] if prof else "") or "",
         (prof["email"] if prof else "") or "",
         (prof["address"] if prof else "") or "",
         (prof["latitude"] if prof else None),
         (prof["longitude"] if prof else None),
         _now()),
    )
    org_id = cur.lastrowid
    conn.execute(
        "UPDATE users SET organization_id=? WHERE id=?", (org_id, user_id)
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
            lines.append("\U0001F4CB *Demande de produits \u2014 Elokinab Health*")
            lines.append("")
            lines.append("\U0001F194 R\u00e9f\u00e9rence : " + req["reference"])
            if org and org["structure_name"]:
                lines.append("\U0001F3E5 \u00c9tablissement : " + org["structure_name"])
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
                        qs = " \u00D7 " + str(int(qty) if float(qty).is_integer() else qty)
                    elif qty and float(qty) == 1:
                        qs = " \u00D7 1"
                    lines.append("\u2022 " + it["description"] + qs)
                lines.append("")
            if atts:
                lines.append("Pi\u00e8ces jointes :")
                for a in atts:
                    lines.append("\u2022 " + a["type"].upper() + " \u2014 " + (a["original_filename"] or a["storage_path"]))
                lines.append("")
                lines.append("(Je joins les fichiers dans WhatsApp apr\u00e8s ouverture.)")
                lines.append("")
            if req["notes"]:
                lines.append("\U0001F4DD Notes : " + req["notes"])
                lines.append("")
            lines.append("Merci de nous communiquer la disponibilit\u00e9 et les informations correspondantes.")
            lines.append("")
            lines.append("Cordialement,")
            if org and org["structure_name"]:
                lines.append(org["structure_name"])

            message = "\\n".join(lines)

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
            "whatsapp_url": "https://wa.me/" + digits + "?text=" + message.replace(" ", "%20").replace("\\n", "%0A"),
            "phone": digits,
        }


'''
(MODULES / "b2b_requests.py").write_text(B2B, encoding="utf-8")
print("[OK] v3_modules/b2b_requests.py")

# ============================================================
# 2. PATCH MAIN.PY
# ============================================================
src = MAIN.read_text(encoding="utf-8")
if "install_b2b" not in src:
    old = "install_pro_features(app, get_db, require_role)"
    new = (old + "\n"
           "from v3_modules.b2b_requests import install_b2b\n"
           "install_b2b(app, get_db, require_role, UPLOADS_DIR)")
    if old in src:
        src = src.replace(old, new, 1)
        MAIN.write_text(src, encoding="utf-8")
        print("[OK] main.py -> install_b2b branche")
    else:
        print("[!] anchor install_pro_features introuvable")
else:
    print("[i] main.py deja patche B2B")

# Ajouter route /professionnel/catalogue si absente
if '"/professionnel/catalogue"' not in src:
    routes = '''

@app.get("/professionnel/catalogue", include_in_schema=False)
def page_pro_catalogue():
    return FileResponse(STATIC_DIR / "professional_catalogue.html")


@app.get("/professionnel/commandes", include_in_schema=False)
def page_pro_commandes():
    return FileResponse(STATIC_DIR / "professional_commandes.html")


'''
    anchor = "\ninit_db()\n"
    if anchor in src:
        src = src.replace(anchor, routes + anchor, 1)
        MAIN.write_text(src, encoding="utf-8")
        print("[OK] main.py -> routes /professionnel/catalogue et /commandes")
else:
    print("[i] routes pro supplementaires deja presentes")

# ============================================================
# 3. FRONTEND : page principale /professionnel
# ============================================================
PRO_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Espace professionnel - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
:root{
  --green:#0f9d76;--green-dark:#0a7a5a;--green-soft:#e8f7f1;
  --ink:#0f2620;--muted:#6c8a80;--line:#e4ede9;--bg:#f7fbf9;
  --radius:14px;--shadow:0 2px 12px rgba(15,38,32,.05);
  --warn:#f59e0b;--warn-soft:#fff4e0;--danger:#b23c3c;--danger-soft:#fdecec;
}
*,*::before,*::after{box-sizing:border-box}
html,body{overflow-x:clip;margin:0;padding:0}
body{
  font-family:-apple-system,"Segoe UI",system-ui,sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.5;font-size:15px;
  -webkit-font-smoothing:antialiased;padding-bottom:76px;
}
a{color:inherit;text-decoration:none}
button{font-family:inherit;cursor:pointer}
.hidden{display:none !important}
img{max-width:100%;display:block}

.pro-header{
  background:#fff;border-bottom:1px solid var(--line);
  position:sticky;top:0;z-index:100;
}
.pro-header-inner{
  max-width:900px;margin:0 auto;padding:12px 16px;
  display:flex;align-items:center;gap:12px;
}
.pro-brand{display:flex;align-items:center;gap:9px;font-weight:800;font-size:15px}
.pro-brand-mark{
  width:32px;height:32px;border-radius:9px;background:var(--green);color:#fff;
  display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:800;
}
.pro-org{margin-left:auto;font-size:13px;color:var(--muted);text-align:right;min-width:0;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:180px}
.pro-org strong{color:var(--ink);display:block;font-weight:700}

.pro-main{max-width:900px;margin:0 auto;padding:20px 16px 40px}

.pro-hero{margin-bottom:22px}
.pro-hero h1{font-size:26px;line-height:1.2;margin:0 0 8px;letter-spacing:-.02em}
.pro-hero p{font-size:14px;color:var(--muted);margin:0 0 18px;max-width:56ch}

.pro-card{
  background:#fff;border:1px solid var(--line);border-radius:var(--radius);
  padding:18px;margin-bottom:14px;
}
.pro-card-title{
  font-size:11px;font-weight:800;text-transform:uppercase;
  letter-spacing:.08em;color:var(--muted);margin:0 0 12px;
}

/* --- Demande en cours --- */
.pro-draft-head{
  display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;
  margin-bottom:14px;
}
.pro-draft-ref{
  font-family:Consolas,monospace;font-size:13px;color:var(--muted);font-weight:700;
}
.pro-draft-count{
  font-size:12px;background:var(--green-soft);color:var(--green-dark);
  padding:4px 10px;border-radius:999px;font-weight:800;
}
.pro-item{
  display:flex;align-items:flex-start;gap:10px;padding:10px 0;
  border-bottom:1px solid var(--line);
}
.pro-item:last-child{border-bottom:0}
.pro-item-info{flex:1;min-width:0}
.pro-item-name{font-size:14px;font-weight:700;margin:0 0 2px;word-break:break-word}
.pro-item-meta{font-size:12px;color:var(--muted)}
.pro-item-actions{display:flex;gap:6px;flex-shrink:0}
.pro-item-btn{
  width:30px;height:30px;border:1px solid var(--line);border-radius:8px;
  background:#fff;font-size:14px;line-height:1;display:flex;
  align-items:center;justify-content:center;color:var(--ink);
}
.pro-item-btn:hover{border-color:var(--green);color:var(--green-dark)}
.pro-item-btn.del:hover{border-color:var(--danger);color:var(--danger);background:var(--danger-soft)}

.pro-add-row{
  display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px;
}
.pro-add-btn{
  padding:14px;border:1px dashed var(--green);background:var(--green-soft);
  color:var(--green-dark);font-weight:800;font-size:13px;border-radius:12px;
  display:flex;align-items:center;justify-content:center;gap:6px;
}
.pro-add-btn:hover{background:#d6efe6}
.pro-add-btn.solid{border-style:solid;background:var(--green);color:#fff;border-color:var(--green)}
.pro-add-btn.solid:hover{background:var(--green-dark)}

.pro-empty{
  text-align:center;padding:22px 12px;color:var(--muted);font-size:14px;
}

.pro-notes{
  width:100%;padding:11px 13px;border:1px solid var(--line);border-radius:10px;
  font-family:inherit;font-size:14px;background:#fff;outline:none;
  resize:vertical;min-height:60px;
}
.pro-notes:focus{border-color:var(--green)}

.pro-actions-bottom{
  display:flex;gap:10px;margin-top:14px;flex-wrap:wrap;
}
.pro-send{
  flex:1;min-width:180px;padding:14px;border:0;border-radius:12px;
  background:#25d366;color:#fff;font-weight:800;font-size:15px;
  display:flex;align-items:center;justify-content:center;gap:8px;
}
.pro-send:hover{background:#1da851}
.pro-send:disabled{background:#c9e5d4;cursor:not-allowed}
.pro-clear{
  padding:14px 18px;border:1px solid var(--line);background:#fff;border-radius:12px;
  font-weight:700;font-size:14px;color:var(--muted);
}

/* --- Attachments --- */
.pro-att{
  display:flex;align-items:center;gap:10px;padding:10px 12px;
  border:1px solid var(--line);border-radius:10px;margin-top:8px;
}
.pro-att-icon{
  width:36px;height:36px;border-radius:9px;background:var(--green-soft);
  color:var(--green-dark);display:flex;align-items:center;justify-content:center;
  font-size:16px;flex-shrink:0;
}
.pro-att-body{flex:1;min-width:0}
.pro-att-name{font-size:13px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pro-att-meta{font-size:11px;color:var(--muted)}
.pro-att-del{background:none;border:0;color:var(--danger);font-size:18px;cursor:pointer;padding:4px}

/* --- Historique --- */
.pro-history-item{
  display:flex;align-items:center;gap:10px;padding:10px 0;
  border-bottom:1px solid var(--line);
}
.pro-history-item:last-child{border-bottom:0}
.pro-history-body{flex:1;min-width:0;cursor:pointer}
.pro-history-title{font-size:14px;font-weight:700;margin:0 0 2px}
.pro-history-meta{font-size:12px;color:var(--muted)}
.pro-badge{
  font-size:10px;font-weight:800;padding:3px 9px;border-radius:999px;
  text-transform:uppercase;letter-spacing:.05em;background:var(--green-soft);
  color:var(--green-dark);flex-shrink:0;
}
.pro-badge.DRAFT{background:#fff4e0;color:#b26b00}
.pro-badge.SUBMITTED{background:#e3f0ff;color:#1b5aae}
.pro-badge.CONFIRMED{background:#e3f7ee;color:#0a7a5a}
.pro-badge.PARTIALLY_CONFIRMED{background:#ede0ff;color:#6335b8}
.pro-badge.REJECTED{background:var(--danger-soft);color:var(--danger)}

/* --- Navigation mobile basse --- */
.pro-navbar{
  position:fixed;bottom:0;left:0;right:0;z-index:200;
  background:#fff;border-top:1px solid var(--line);
  display:grid;grid-template-columns:1fr 1fr 76px 1fr 1fr;
  padding:6px 6px calc(6px + env(safe-area-inset-bottom)) 6px;
  box-shadow:0 -2px 12px rgba(15,38,32,.06);
}
.pro-navbar a{
  padding:8px 4px;text-align:center;font-size:10px;font-weight:700;
  color:var(--muted);display:flex;flex-direction:column;align-items:center;gap:3px;
  text-decoration:none;
}
.pro-navbar a .ico{font-size:18px;line-height:1}
.pro-navbar a.active{color:var(--green-dark)}
.pro-navbar .central{
  margin-top:-22px;background:var(--green);color:#fff;border-radius:50%;
  width:64px;height:64px;justify-self:center;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  font-size:22px;font-weight:800;box-shadow:0 6px 20px rgba(15,157,118,.4);
  border:4px solid var(--bg);
}
.pro-navbar .central .lbl{font-size:9px;font-weight:700;margin-top:-2px}

/* --- Modale --- */
.pro-modal{position:fixed;inset:0;z-index:900;display:flex;align-items:flex-end;justify-content:center}
.pro-modal.hidden{display:none}
.pro-modal-bg{position:absolute;inset:0;background:rgba(15,38,32,.55)}
.pro-modal-panel{
  position:relative;background:#fff;width:100%;max-width:600px;
  max-height:92vh;border-radius:20px 20px 0 0;
  display:flex;flex-direction:column;overflow:hidden;
  animation:slideUp .22s ease;
}
@keyframes slideUp{from{transform:translateY(30px);opacity:.4}to{transform:translateY(0);opacity:1}}
.pro-modal-head{
  padding:16px 20px;border-bottom:1px solid var(--line);
  display:flex;align-items:center;justify-content:space-between;
}
.pro-modal-head h3{margin:0;font-size:16px}
.pro-modal-close{background:none;border:0;font-size:26px;color:var(--muted);cursor:pointer;padding:0 4px}
.pro-modal-body{padding:18px 20px;overflow-y:auto;flex:1}
.pro-modal-foot{
  padding:14px 20px;border-top:1px solid var(--line);background:var(--bg);
  display:flex;gap:10px;
}
.pro-modal-foot button{flex:1;padding:13px;border:0;border-radius:11px;font-weight:800;font-size:14px}

.pro-choice{
  display:flex;align-items:center;gap:14px;padding:16px;
  border:1px solid var(--line);border-radius:14px;background:#fff;
  width:100%;text-align:left;margin-bottom:10px;cursor:pointer;
  transition:.15s;
}
.pro-choice:hover{border-color:var(--green);background:#fafdfb}
.pro-choice-icon{
  width:46px;height:46px;border-radius:12px;background:var(--green-soft);
  color:var(--green-dark);display:flex;align-items:center;justify-content:center;
  font-size:22px;flex-shrink:0;
}
.pro-choice-body{flex:1;min-width:0}
.pro-choice-title{font-size:15px;font-weight:800;margin:0 0 3px}
.pro-choice-desc{font-size:12px;color:var(--muted);margin:0}
.pro-choice-arrow{color:var(--muted);font-size:20px;flex-shrink:0}

.pro-field{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.pro-field label{font-size:13px;font-weight:700}
.pro-field input,.pro-field select,.pro-field textarea{
  padding:12px 14px;border:1px solid var(--line);border-radius:11px;
  font-family:inherit;font-size:15px;outline:none;background:#fff;width:100%;
}
.pro-field input:focus,.pro-field select:focus,.pro-field textarea:focus{border-color:var(--green)}

.pro-upload{
  border:2px dashed var(--line);border-radius:12px;padding:22px 14px;
  text-align:center;background:#fafdfb;cursor:pointer;display:block;
}
.pro-upload:hover{border-color:var(--green);background:var(--green-soft)}
.pro-upload input{display:none}
.pro-upload-icon{font-size:30px;margin-bottom:6px}
.pro-upload-title{font-size:14px;font-weight:700;margin:0 0 4px}
.pro-upload-hint{font-size:12px;color:var(--muted);margin:0}

.pro-err{margin-top:10px;padding:10px 12px;background:var(--danger-soft);
  color:var(--danger);border:1px solid #f6d2d2;border-radius:10px;font-size:13px}
.pro-info{margin-top:10px;padding:10px 12px;background:var(--warn-soft);
  color:#8a5a00;border:1px solid #f2d9b3;border-radius:10px;font-size:12px}
.pro-info strong{color:#6b4400}

.pro-toast{
  position:fixed;left:50%;bottom:96px;transform:translateX(-50%);
  background:var(--ink);color:#fff;padding:12px 18px;border-radius:12px;
  font-size:13px;font-weight:600;z-index:1000;
  box-shadow:0 10px 30px rgba(0,0,0,.2);max-width:calc(100vw - 32px);
  text-align:center;
}
.pro-toast.ok{background:var(--green-dark)}

.pro-catalogue-item{
  display:flex;gap:12px;padding:12px 0;border-bottom:1px solid var(--line);
  align-items:center;
}
.pro-catalogue-item:last-child{border-bottom:0}
.pro-catalogue-thumb{
  width:48px;height:48px;border-radius:10px;background:var(--green-soft);
  flex-shrink:0;overflow:hidden;display:flex;align-items:center;justify-content:center;
  color:var(--green-dark);font-weight:800;font-size:16px;
}
.pro-catalogue-thumb img{width:100%;height:100%;object-fit:contain;background:#fff}
.pro-catalogue-body{flex:1;min-width:0}
.pro-catalogue-name{font-size:14px;font-weight:700;margin:0 0 2px;word-break:break-word}
.pro-catalogue-meta{font-size:12px;color:var(--muted)}
.pro-qty{display:flex;align-items:center;gap:6px;flex-shrink:0}
.pro-qty input{
  width:56px;padding:8px;text-align:center;border:1px solid var(--line);
  border-radius:8px;font-family:inherit;font-size:14px;
}

.pro-search{
  width:100%;padding:12px 14px;border:1px solid var(--line);border-radius:11px;
  font-family:inherit;font-size:15px;outline:none;background:#fff;
}
.pro-search:focus{border-color:var(--green)}

@media(max-width:520px){
  .pro-hero h1{font-size:22px}
  .pro-add-row{grid-template-columns:1fr}
}
</style>
</head>
<body>

<header class="pro-header">
  <div class="pro-header-inner">
    <div class="pro-brand">
      <span class="pro-brand-mark">+</span>
      <span>Elokinab</span>
    </div>
    <div class="pro-org">
      <strong id="org-name">Mon établissement</strong>
      <span id="org-type">Professionnel de santé</span>
    </div>
  </div>
</header>

<main class="pro-main">

  <!-- HERO -->
  <section class="pro-hero">
    <h1>Commandez simplement.</h1>
    <p>Préparez votre demande avec toutes vos sources : catalogue, saisie libre, PDF ou photo. Puis envoyez-la sur WhatsApp.</p>
  </section>

  <!-- DEMANDE EN COURS -->
  <section class="pro-card" id="draft-card">
    <div class="pro-draft-head">
      <div>
        <h2 class="pro-card-title" style="margin:0">Demande en cours</h2>
        <div class="pro-draft-ref" id="draft-ref">—</div>
      </div>
      <span class="pro-draft-count" id="draft-count">0 élément</span>
    </div>

    <div id="draft-items"></div>
    <div id="draft-attachments"></div>

    <div class="pro-add-row">
      <button class="pro-add-btn" id="add-from-catalogue">
        <span>&#128722;</span> Depuis le catalogue
      </button>
      <button class="pro-add-btn" id="add-manual">
        <span>&#9997;&#65039;</span> Saisir une ligne
      </button>
      <button class="pro-add-btn" id="add-pdf">
        <span>&#128196;</span> Importer un PDF
      </button>
      <button class="pro-add-btn" id="add-photo">
        <span>&#128247;</span> Ajouter une photo
      </button>
    </div>

    <div style="margin-top:14px">
      <label style="font-size:12px;font-weight:700;color:var(--muted)">Notes (facultatif)</label>
      <textarea class="pro-notes" id="draft-notes" placeholder="Instructions particulières, délai souhaité..."></textarea>
    </div>

    <div class="pro-actions-bottom">
      <button class="pro-send" id="send-whatsapp" disabled>
        <span>&#128172;</span> Envoyer sur WhatsApp
      </button>
      <button class="pro-clear" id="clear-draft">Vider</button>
    </div>
  </section>

  <!-- HISTORIQUE -->
  <section class="pro-card">
    <h2 class="pro-card-title">Mes demandes récentes</h2>
    <div id="history"></div>
  </section>

</main>

<!-- NAVBAR MOBILE -->
<nav class="pro-navbar">
  <a href="/professionnel" class="active">
    <span class="ico">&#127968;</span> Accueil
  </a>
  <a href="/professionnel/catalogue">
    <span class="ico">&#128722;</span> Catalogue
  </a>
  <a href="#" class="central" id="nav-new">
    <span>+</span><span class="lbl">Demande</span>
  </a>
  <a href="/professionnel/commandes">
    <span class="ico">&#128230;</span> Commandes
  </a>
  <a href="#" id="nav-etab">
    <span class="ico">&#127970;</span> Établ.
  </a>
</nav>

<!-- MODALE : choix source -->
<div id="m-source" class="pro-modal hidden">
  <div class="pro-modal-bg" data-close-modal></div>
  <div class="pro-modal-panel">
    <div class="pro-modal-head">
      <h3>Ajouter à ma demande</h3>
      <button class="pro-modal-close" data-close-modal>&times;</button>
    </div>
    <div class="pro-modal-body">
      <button class="pro-choice" data-source="manual">
        <span class="pro-choice-icon">&#9997;&#65039;</span>
        <span class="pro-choice-body">
          <span class="pro-choice-title">Saisir une ligne</span>
          <span class="pro-choice-desc">Ajoutez un produit et sa quantité</span>
        </span>
        <span class="pro-choice-arrow">›</span>
      </button>
      <button class="pro-choice" data-source="catalogue">
        <span class="pro-choice-icon">&#128722;</span>
        <span class="pro-choice-body">
          <span class="pro-choice-title">Depuis le catalogue</span>
          <span class="pro-choice-desc">Parcourez nos produits disponibles</span>
        </span>
        <span class="pro-choice-arrow">›</span>
      </button>
      <button class="pro-choice" data-source="pdf">
        <span class="pro-choice-icon">&#128196;</span>
        <span class="pro-choice-body">
          <span class="pro-choice-title">Importer un PDF</span>
          <span class="pro-choice-desc">Liste enregistrée au format PDF</span>
        </span>
        <span class="pro-choice-arrow">›</span>
      </button>
      <button class="pro-choice" data-source="photo">
        <span class="pro-choice-icon">&#128247;</span>
        <span class="pro-choice-body">
          <span class="pro-choice-title">Ajouter une photo</span>
          <span class="pro-choice-desc">Photographiez ou sélectionnez une image</span>
        </span>
        <span class="pro-choice-arrow">›</span>
      </button>
    </div>
  </div>
</div>

<!-- MODALE : saisie manuelle -->
<div id="m-manual" class="pro-modal hidden">
  <div class="pro-modal-bg" data-close-modal></div>
  <div class="pro-modal-panel">
    <div class="pro-modal-head">
      <h3>Saisir une ligne</h3>
      <button class="pro-modal-close" data-close-modal>&times;</button>
    </div>
    <div class="pro-modal-body">
      <div class="pro-field">
        <label for="m-manual-desc">Produit</label>
        <input type="text" id="m-manual-desc" placeholder="Ex : Gants d'examen taille M">
      </div>
      <div class="pro-field">
        <label for="m-manual-qty">Quantité</label>
        <input type="text" id="m-manual-qty" placeholder="Ex : 10 boîtes">
      </div>
      <div id="m-manual-err" class="pro-err hidden"></div>
    </div>
    <div class="pro-modal-foot">
      <button class="pro-clear" data-close-modal>Annuler</button>
      <button class="pro-send" id="m-manual-add" style="background:var(--green)">Ajouter</button>
    </div>
  </div>
</div>

<!-- MODALE : catalogue -->
<div id="m-catalogue" class="pro-modal hidden">
  <div class="pro-modal-bg" data-close-modal></div>
  <div class="pro-modal-panel">
    <div class="pro-modal-head">
      <h3>Catalogue</h3>
      <button class="pro-modal-close" data-close-modal>&times;</button>
    </div>
    <div class="pro-modal-body">
      <input type="search" class="pro-search" id="m-cat-search" placeholder="Rechercher un produit...">
      <div id="m-cat-list" style="margin-top:12px"></div>
    </div>
  </div>
</div>

<!-- MODALE : PDF -->
<div id="m-pdf" class="pro-modal hidden">
  <div class="pro-modal-bg" data-close-modal></div>
  <div class="pro-modal-panel">
    <div class="pro-modal-head">
      <h3>Importer un PDF</h3>
      <button class="pro-modal-close" data-close-modal>&times;</button>
    </div>
    <div class="pro-modal-body">
      <label class="pro-upload" for="pdf-file">
        <input type="file" id="pdf-file" accept="application/pdf,.pdf">
        <div class="pro-upload-icon">&#128196;</div>
        <p class="pro-upload-title">Choisir un fichier PDF</p>
        <p class="pro-upload-hint">Format PDF uniquement · 15 Mo max</p>
      </label>
      <div id="m-pdf-err" class="pro-err hidden"></div>
    </div>
  </div>
</div>

<!-- MODALE : PHOTO -->
<div id="m-photo" class="pro-modal hidden">
  <div class="pro-modal-bg" data-close-modal></div>
  <div class="pro-modal-panel">
    <div class="pro-modal-head">
      <h3>Ajouter une photo</h3>
      <button class="pro-modal-close" data-close-modal>&times;</button>
    </div>
    <div class="pro-modal-body">
      <label class="pro-upload" for="photo-file">
        <input type="file" id="photo-file" accept="image/*" capture="environment">
        <div class="pro-upload-icon">&#128247;</div>
        <p class="pro-upload-title">Prendre ou choisir une photo</p>
        <p class="pro-upload-hint">JPG, PNG, WEBP · 15 Mo max</p>
      </label>
      <div id="m-photo-err" class="pro-err hidden"></div>
    </div>
  </div>
</div>

<script src="/static/professional.js"></script>
</body>
</html>
'''
(STATIC / "professional.html").write_text(PRO_HTML, encoding="utf-8")
print("[OK] professional.html")

# ============================================================
# 4. FRONTEND JS
# ============================================================
PRO_JS = r'''/* Elokinab Health - Espace professionnel B2B */
(function () {
  var API = "/api";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  var state = {
    org: null,
    draft: null,
    items: [],
    attachments: [],
    history: [],
    catalogue: []
  };

  function toast(msg, ok) {
    var t = document.createElement("div");
    t.className = "pro-toast" + (ok ? " ok" : "");
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.style.opacity = "0"; t.style.transition = "opacity .3s"; }, 2200);
    setTimeout(function () { t.remove(); }, 2600);
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }

  function api(method, path, body) {
    var opts = {
      method: method,
      credentials: "same-origin",
      headers: { "Accept": "application/json" }
    };
    if (body instanceof FormData) {
      opts.body = body;
    } else if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(API + path, opts).then(function (r) {
      if (r.status === 401) {
        window.location.href = "/connexion?next=/professionnel";
        throw new Error("Non authentifie");
      }
      return r.json().then(function (data) {
        if (!r.ok) throw new Error(data.detail || "Erreur");
        return data;
      });
    });
  }

  // ============================================================
  // ORGANISATION
  // ============================================================
  function loadOrg() {
    return api("GET", "/pro/organizations/me").then(function (org) {
      state.org = org;
      renderOrg();
    });
  }

  function renderOrg() {
    if (!state.org) return;
    var nameEl = document.getElementById("org-name");
    var typeEl = document.getElementById("org-type");
    if (nameEl) nameEl.textContent = state.org.structure_name || "Mon établissement";
    if (typeEl) {
      var map = {
        CLINIQUE: "Clinique", HOPITAL: "Hôpital",
        CABINET_MEDICAL: "Cabinet médical", LABORATOIRE: "Laboratoire",
        CENTRE_SANTE: "Centre de santé", AUTRE: "Établissement"
      };
      typeEl.textContent = map[state.org.structure_type] || "Professionnel de santé";
    }
  }

  // ============================================================
  // DRAFT (demande en cours)
  // ============================================================
  function loadDraft() {
    return api("GET", "/pro/requests/draft").then(function (draft) {
      state.draft = draft;
      return reloadDraftContent();
    });
  }

  function reloadDraftContent() {
    if (!state.draft) return Promise.resolve();
    return api("GET", "/pro/requests/" + state.draft.reference).then(function (full) {
      state.items = full.items || [];
      state.attachments = full.attachments || [];
      renderDraft();
      return full;
    });
  }

  function renderDraft() {
    var refEl = document.getElementById("draft-ref");
    var countEl = document.getElementById("draft-count");
    var itemsBox = document.getElementById("draft-items");
    var attsBox = document.getElementById("draft-attachments");
    var sendBtn = document.getElementById("send-whatsapp");

    if (refEl) refEl.textContent = state.draft ? state.draft.reference : "—";
    var total = state.items.length + state.attachments.length;
    if (countEl) countEl.textContent = total + " élément" + (total > 1 ? "s" : "");

    // Notes
    if (state.draft && document.getElementById("draft-notes")) {
      var notesEl = document.getElementById("draft-notes");
      if (!notesEl.matches(":focus") && notesEl.value !== (state.draft.notes || "")) {
        notesEl.value = state.draft.notes || "";
      }
    }

    // Items
    itemsBox.innerHTML = "";
    if (state.items.length === 0) {
      itemsBox.innerHTML =
        '<div class="pro-empty">Aucun produit pour le moment.<br>' +
        'Utilisez les boutons ci-dessous.</div>';
    } else {
      state.items.forEach(function (it) {
        var row = document.createElement("div");
        row.className = "pro-item";
        var qty = it.requested_quantity;
        var qs = (qty && qty != 1) ? " × " + (Math.round(qty * 100) / 100) : (qty == 1 ? " × 1" : "");
        row.innerHTML =
          '<div class="pro-item-info">' +
            '<div class="pro-item-name">' + escapeHtml(it.description) + '</div>' +
            '<div class="pro-item-meta">' + (qs || "quantité à préciser") +
            (it.product_id ? " · depuis catalogue" : " · saisi manuellement") +
            '</div>' +
          '</div>' +
          '<div class="pro-item-actions">' +
            '<button class="pro-item-btn" data-edit="' + it.id + '" title="Modifier">✏️</button>' +
            '<button class="pro-item-btn del" data-del="' + it.id + '" title="Supprimer">✕</button>' +
          '</div>';
        itemsBox.appendChild(row);
      });

      // Handlers
      $$("[data-del]", itemsBox).forEach(function (b) {
        b.addEventListener("click", function () {
          var id = b.getAttribute("data-del");
          api("DELETE", "/pro/requests/" + state.draft.reference + "/items/" + id)
            .then(reloadDraftContent).catch(function (e) { toast(e.message); });
        });
      });
      $$("[data-edit]", itemsBox).forEach(function (b) {
        b.addEventListener("click", function () {
          var id = parseInt(b.getAttribute("data-edit"));
          var it = state.items.filter(function (x) { return x.id === id; })[0];
          if (!it) return;
          openManual(it);
        });
      });
    }

    // Attachments
    attsBox.innerHTML = "";
    state.attachments.forEach(function (a) {
      var row = document.createElement("div");
      row.className = "pro-att";
      var ico = a.type === "pdf" ? "📄" : "📷";
      row.innerHTML =
        '<div class="pro-att-icon">' + ico + '</div>' +
        '<div class="pro-att-body">' +
          '<div class="pro-att-name">' + escapeHtml(a.original_filename || a.storage_path) + '</div>' +
          '<div class="pro-att-meta">' + (a.type === "pdf" ? "PDF" : "Photo") +
          ' · ' + Math.round((a.size_bytes || 0) / 1024) + ' Ko</div>' +
        '</div>' +
        '<button class="pro-att-del" data-del-att="' + a.id + '" title="Supprimer">✕</button>';
      attsBox.appendChild(row);
    });
    $$("[data-del-att]", attsBox).forEach(function (b) {
      b.addEventListener("click", function () {
        var id = b.getAttribute("data-del-att");
        api("DELETE", "/pro/requests/" + state.draft.reference + "/attachments/" + id)
          .then(reloadDraftContent).catch(function (e) { toast(e.message); });
      });
    });

    // Bouton envoyer
    if (sendBtn) sendBtn.disabled = total === 0;
  }

  // Enregistrer les notes automatiquement (debounce)
  var notesTimer = null;
  function attachNotesHandler() {
    var el = document.getElementById("draft-notes");
    if (!el) return;
    el.addEventListener("input", function () {
      if (!state.draft) return;
      if (notesTimer) clearTimeout(notesTimer);
      notesTimer = setTimeout(function () {
        api("PATCH", "/pro/requests/" + state.draft.reference, { notes: el.value })
          .then(function (r) { state.draft.notes = r.notes; })
          .catch(function () {});
      }, 800);
    });
  }

  // ============================================================
  // AJOUT ITEM
  // ============================================================
  function addItem(desc, qty, productId) {
    if (!state.draft) return Promise.reject(new Error("Aucune demande"));
    return api("POST", "/pro/requests/" + state.draft.reference + "/items", {
      product_id: productId || null,
      description: desc,
      requested_quantity: qty
    }).then(function () { return reloadDraftContent(); });
  }

  function updateItem(id, desc, qty) {
    return api("PATCH", "/pro/requests/" + state.draft.reference + "/items/" + id, {
      description: desc,
      requested_quantity: qty
    }).then(function () { return reloadDraftContent(); });
  }

  // ============================================================
  // UPLOAD ATTACHMENTS
  // ============================================================
  function uploadAttachment(file, type) {
    var fd = new FormData();
    fd.append("file", file);
    return api("POST", "/pro/requests/" + state.draft.reference + "/attachments", fd)
      .then(function () { return reloadDraftContent(); });
  }

  // ============================================================
  // WHATSAPP
  // ============================================================
  function sendWhatsapp() {
    if (!state.draft) return;
    var btn = document.getElementById("send-whatsapp");
    if (btn) { btn.disabled = true; btn.textContent = "Préparation..."; }
    api("GET", "/pro/requests/" + state.draft.reference + "/whatsapp").then(function (d) {
      window.open(d.whatsapp_url, "_blank");
      toast("WhatsApp ouvert. Joignez les fichiers si nécessaire.", true);
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span>💬</span> Envoyer sur WhatsApp';
      }
      // Rafraichir l'historique
      loadHistory();
    }).catch(function (e) {
      toast(e.message);
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span>💬</span> Envoyer sur WhatsApp';
      }
    });
  }

  // ============================================================
  // HISTORIQUE
  // ============================================================
  function loadHistory() {
    return api("GET", "/pro/requests").then(function (list) {
      state.history = list;
      renderHistory();
    });
  }

  function renderHistory() {
    var box = document.getElementById("history");
    box.innerHTML = "";
    var list = (state.history || []).filter(function (r) { return r.status !== "DRAFT"; });
    if (list.length === 0) {
      box.innerHTML = '<div class="pro-empty">Vous n\\'avez encore envoyé aucune demande.</div>';
      return;
    }
    list.slice(0, 20).forEach(function (r) {
      var d = new Date(r.created_at);
      var dateStr = isNaN(d) ? "" : d.toLocaleDateString("fr-FR", {
        day: "2-digit", month: "short", year: "numeric"
      });
      var row = document.createElement("div");
      row.className = "pro-history-item";
      row.innerHTML =
        '<div class="pro-history-body">' +
          '<div class="pro-history-title">' + r.items_count + ' produit' + (r.items_count > 1 ? "s" : "") +
          (r.attachments_count ? " + " + r.attachments_count + " pièce" + (r.attachments_count > 1 ? "s" : "") : "") +
          '</div>' +
          '<div class="pro-history-meta">' + (dateStr || "") + ' · ' + escapeHtml(r.reference) + '</div>' +
        '</div>' +
        '<span class="pro-badge ' + r.status + '">' + statusLabel(r.status) + '</span>';
      box.appendChild(row);
    });
  }

  function statusLabel(s) {
    var m = {
      DRAFT: "Brouillon", SUBMITTED: "Envoyée",
      UNDER_REVIEW: "En cours", CONFIRMED: "Confirmée",
      PARTIALLY_CONFIRMED: "Partielle", REJECTED: "Refusée"
    };
    return m[s] || s;
  }

  // ============================================================
  // CATALOGUE
  // ============================================================
  function loadCatalogue() {
    return api("GET", "/products").then(function (list) {
      state.catalogue = list || [];
    });
  }

  function renderCatalogue(query) {
    var box = document.getElementById("m-cat-list");
    box.innerHTML = "";
    var q = (query || "").trim().toLowerCase();
    var list = state.catalogue.filter(function (p) {
      if (!q) return true;
      return (p.name || "").toLowerCase().indexOf(q) >= 0 ||
             (p.presentation || "").toLowerCase().indexOf(q) >= 0 ||
             (p.category || "").toLowerCase().indexOf(q) >= 0;
    }).slice(0, 40);

    if (list.length === 0) {
      box.innerHTML = '<div class="pro-empty">Aucun produit trouvé.</div>';
      return;
    }

    list.forEach(function (p) {
      var row = document.createElement("div");
      row.className = "pro-catalogue-item";
      var thumb = p.image_url
        ? '<img src="' + escapeHtml(p.image_url) + '" alt="" onerror="this.remove();this.parentNode.textContent=\'' + escapeHtml((p.name || "?").charAt(0)) + '\'">'
        : escapeHtml((p.name || "?").charAt(0));
      var avail = {
        disponible: "Disponible", rupture: "Indisponible",
        stock_limite: "Stock limité"
      }[p.availability] || "À confirmer";

      row.innerHTML =
        '<div class="pro-catalogue-thumb">' + thumb + '</div>' +
        '<div class="pro-catalogue-body">' +
          '<div class="pro-catalogue-name">' + escapeHtml(p.name) + '</div>' +
          '<div class="pro-catalogue-meta">' + escapeHtml(p.presentation || "") + '</div>' +
          '<div class="pro-catalogue-meta">' + avail + '</div>' +
        '</div>' +
        '<div class="pro-qty">' +
          '<input type="text" placeholder="Qté" data-qty="' + p.id + '">' +
          '<button class="pro-add-btn" style="padding:8px 12px;font-size:12px" data-add="' + p.id + '">+</button>' +
        '</div>';
      box.appendChild(row);
    });

    $$("[data-add]", box).forEach(function (b) {
      b.addEventListener("click", function () {
        var pid = parseInt(b.getAttribute("data-add"));
        var input = box.querySelector('[data-qty="' + pid + '"]');
        var qty = input && input.value ? input.value : "1";
        var p = state.catalogue.filter(function (x) { return x.id === pid; })[0];
        if (!p) return;
        var desc = p.name + (p.presentation ? " — " + p.presentation : "");
        var qtyNum = parseFloat(qty);
        addItem(desc, isNaN(qtyNum) ? 1 : qtyNum, pid)
          .then(function () {
            toast("Ajouté : " + p.name, true);
            if (input) input.value = "";
          })
          .catch(function (e) { toast(e.message); });
      });
    });
  }

  // ============================================================
  // MODALES
  // ============================================================
  function openModal(id) {
    document.getElementById(id).classList.remove("hidden");
    document.body.style.overflow = "hidden";
  }
  function closeModals() {
    $$(".pro-modal").forEach(function (m) { m.classList.add("hidden"); });
    document.body.style.overflow = "";
  }

  function openSourceChoice() {
    openModal("m-source");
  }

  function openManual(item) {
    closeModals();
    var d = document.getElementById("m-manual-desc");
    var q = document.getElementById("m-manual-qty");
    d.value = item ? item.description : "";
    q.value = item ? (item.requested_quantity || "") : "";
    document.getElementById("m-manual-err").classList.add("hidden");
    d.dataset.editId = item ? item.id : "";
    openModal("m-manual");
    setTimeout(function () { d.focus(); }, 100);
  }

  function submitManual() {
    var d = document.getElementById("m-manual-desc").value.trim();
    var qv = document.getElementById("m-manual-qty").value.trim();
    var editId = document.getElementById("m-manual-desc").dataset.editId;
    var errBox = document.getElementById("m-manual-err");

    if (!d) {
      errBox.textContent = "Le nom du produit est obligatoire.";
      errBox.classList.remove("hidden");
      return;
    }
    var qty = parseFloat(qv);
    if (isNaN(qty) || qty <= 0) qty = 1;

    var p = editId
      ? updateItem(parseInt(editId), d, qty)
      : addItem(d, qty, null);

    p.then(function () {
      closeModals();
      toast(editId ? "Ligne mise à jour" : "Ligne ajoutée", true);
    }).catch(function (e) {
      errBox.textContent = e.message;
      errBox.classList.remove("hidden");
    });
  }

  function openCatalogue() {
    closeModals();
    openModal("m-catalogue");
    var s = document.getElementById("m-cat-search");
    s.value = "";
    renderCatalogue("");
    setTimeout(function () { s.focus(); }, 100);
  }

  function openPdf() {
    closeModals();
    document.getElementById("pdf-file").value = "";
    document.getElementById("m-pdf-err").classList.add("hidden");
    openModal("m-pdf");
  }
  function openPhoto() {
    closeModals();
    document.getElementById("photo-file").value = "";
    document.getElementById("m-photo-err").classList.add("hidden");
    openModal("m-photo");
  }

  function onPdfChosen(input) {
    var f = input.files && input.files[0];
    var err = document.getElementById("m-pdf-err");
    if (!f) return;
    if (!/\.pdf$/i.test(f.name) && f.type !== "application/pdf") {
      err.textContent = "Ce fichier n'est pas compatible. Veuillez sélectionner un PDF.";
      err.classList.remove("hidden");
      return;
    }
    if (f.size > 15 * 1024 * 1024) {
      err.textContent = "Fichier trop volumineux (max 15 Mo).";
      err.classList.remove("hidden");
      return;
    }
    uploadAttachment(f, "pdf").then(function () {
      closeModals();
      toast("PDF ajouté à la demande", true);
    }).catch(function (e) {
      err.textContent = e.message;
      err.classList.remove("hidden");
    });
  }

  function onPhotoChosen(input) {
    var f = input.files && input.files[0];
    var err = document.getElementById("m-photo-err");
    if (!f) return;
    if (!/^image\//.test(f.type)) {
      err.textContent = "Cette image n'est pas compatible. Veuillez choisir un JPG, PNG ou WEBP.";
      err.classList.remove("hidden");
      return;
    }
    if (f.size > 15 * 1024 * 1024) {
      err.textContent = "Fichier trop volumineux (max 15 Mo).";
      err.classList.remove("hidden");
      return;
    }
    uploadAttachment(f, "photo").then(function () {
      closeModals();
      toast("Photo ajoutée à la demande", true);
    }).catch(function (e) {
      err.textContent = e.message;
      err.classList.remove("hidden");
    });
  }

  // ============================================================
  // INIT
  // ============================================================
  function init() {
    // Boutons ajout
    document.getElementById("add-from-catalogue").addEventListener("click", openCatalogue);
    document.getElementById("add-manual").addEventListener("click", function () { openManual(null); });
    document.getElementById("add-pdf").addEventListener("click", openPdf);
    document.getElementById("add-photo").addEventListener("click", openPhoto);
    document.getElementById("nav-new").addEventListener("click", function (e) {
      e.preventDefault();
      document.getElementById("draft-card").scrollIntoView({ behavior: "smooth" });
    });

    // Send
    document.getElementById("send-whatsapp").addEventListener("click", sendWhatsapp);

    // Clear (vide la demande en cours)
    document.getElementById("clear-draft").addEventListener("click", function () {
      if (!state.draft || !confirm("Vider la demande en cours ?")) return;
      var items = state.items.slice();
      var atts = state.attachments.slice();
      var p = Promise.resolve();
      items.forEach(function (it) {
        p = p.then(function () {
          return api("DELETE", "/pro/requests/" + state.draft.reference + "/items/" + it.id);
        });
      });
      atts.forEach(function (a) {
        p = p.then(function () {
          return api("DELETE", "/pro/requests/" + state.draft.reference + "/attachments/" + a.id);
        });
      });
      p.then(reloadDraftContent).catch(function (e) { toast(e.message); });
    });

    // Modal source
    $$("#m-source .pro-choice").forEach(function (b) {
      b.addEventListener("click", function () {
        var s = b.getAttribute("data-source");
        if (s === "manual") openManual(null);
        else if (s === "catalogue") openCatalogue();
        else if (s === "pdf") openPdf();
        else if (s === "photo") openPhoto();
      });
    });

    // Close modals
    $$("[data-close-modal]").forEach(function (b) {
      b.addEventListener("click", closeModals);
    });

    // Manual add
    document.getElementById("m-manual-add").addEventListener("click", submitManual);

    // Catalogue search
    var catSearch = document.getElementById("m-cat-search");
    if (catSearch) {
      catSearch.addEventListener("input", function () {
        renderCatalogue(catSearch.value);
      });
    }

    // File inputs
    document.getElementById("pdf-file").addEventListener("change", function () {
      onPdfChosen(this);
    });
    document.getElementById("photo-file").addEventListener("change", function () {
      onPhotoChosen(this);
    });

    // Notes
    attachNotesHandler();

    // Charger les donnees
    loadOrg()
      .then(loadCatalogue)
      .then(loadDraft)
      .then(loadHistory)
      .catch(function (e) { toast(e.message); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
'''
(STATIC / "professional.js").write_text(PRO_JS, encoding="utf-8")
print("[OK] professional.js")

# ============================================================
# 5. PAGE CATALOGUE PRO (simple redirection)
# ============================================================
CAT_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Catalogue - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
body{margin:0;font-family:-apple-system,"Segoe UI",system-ui,sans-serif;background:#f7fbf9;color:#0f2620;padding:24px;text-align:center}
.card{max-width:480px;margin:40px auto;background:#fff;border:1px solid #e4ede9;border-radius:16px;padding:28px}
h1{font-size:22px;margin:0 0 8px}
p{color:#6c8a80;font-size:14px;margin:0 0 20px}
a{display:inline-block;padding:13px 20px;background:#0f9d76;color:#fff;border-radius:11px;text-decoration:none;font-weight:800}
</style>
</head>
<body>
<div class="card">
  <h1>Catalogue</h1>
  <p>Ajoutez des produits depuis votre demande en cours.</p>
  <a href="/professionnel">← Retour à ma demande</a>
</div>
</body>
</html>
'''
(STATIC / "professional_catalogue.html").write_text(CAT_HTML, encoding="utf-8")
print("[OK] professional_catalogue.html")

# ============================================================
# 6. PAGE COMMANDES PRO
# ============================================================
CMD_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mes commandes - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
body{margin:0;font-family:-apple-system,"Segoe UI",system-ui,sans-serif;background:#f7fbf9;color:#0f2620;padding:24px;text-align:center}
.card{max-width:480px;margin:40px auto;background:#fff;border:1px solid #e4ede9;border-radius:16px;padding:28px}
h1{font-size:22px;margin:0 0 8px}
p{color:#6c8a80;font-size:14px;margin:0 0 20px}
a{display:inline-block;padding:13px 20px;background:#0f9d76;color:#fff;border-radius:11px;text-decoration:none;font-weight:800}
</style>
</head>
<body>
<div class="card">
  <h1>Mes commandes</h1>
  <p>Retrouvez l'historique de vos demandes depuis votre espace.</p>
  <a href="/professionnel">← Retour à ma demande</a>
</div>
</body>
</html>
'''
(STATIC / "professional_commandes.html").write_text(CMD_HTML, encoding="utf-8")
print("[OK] professional_commandes.html")

print()
print("=" * 60)
print("B2B COMPLET INSTALLE")
print("=" * 60)
print()
print("Backend :")
print("  v3_modules/b2b_requests.py")
print("  Routes :")
print("    GET    /api/pro/organizations/me")
print("    PATCH  /api/pro/organizations/me")
print("    GET    /api/pro/requests")
print("    GET    /api/pro/requests/draft")
print("    GET    /api/pro/requests/{ref}")
print("    PATCH  /api/pro/requests/{ref}")
print("    POST   /api/pro/requests/{ref}/items")
print("    PATCH  /api/pro/requests/{ref}/items/{id}")
print("    DELETE /api/pro/requests/{ref}/items/{id}")
print("    POST   /api/pro/requests/{ref}/attachments")
print("    DELETE /api/pro/requests/{ref}/attachments/{id}")
print("    POST   /api/pro/requests/{ref}/submit")
print("    GET    /api/pro/requests/{ref}/whatsapp")
print()
print("Frontend :")
print("  /professionnel             (page principale)")
print("  /professionnel/catalogue   (renvoi vers demande)")
print("  /professionnel/commandes   (renvoi vers demande)")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print()
print("Puis teste : https://URL.trycloudflare.com/professionnel")