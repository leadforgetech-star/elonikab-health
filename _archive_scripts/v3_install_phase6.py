"""v3_install_phase6.py - Workflow ordonnance."""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
MODULES = BASE / "v3_modules"
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_v3_p6_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAIN, backup / "main.py")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. v3_modules/prescriptions.py
# ============================================================
PRESC = '''"""Workflow ordonnance (Phase 6)."""
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
            rel = "/uploads/prescriptions/" + fname

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
        return [_row(r) for r in rows]

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
            conn.commit()
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


'''
(MODULES / "prescriptions.py").write_text(PRESC, encoding="utf-8")
print("[OK] v3_modules/prescriptions.py")

# ============================================================
# 2. Patch main.py
# ============================================================
src = MAIN.read_text(encoding="utf-8")
if "install_prescriptions" not in src:
    old = "install_payments(app, get_db, require_role, UPLOADS_DIR)"
    new = (old + "\n"
           "from v3_modules.prescriptions import install_prescriptions\n"
           "install_prescriptions(app, get_db, require_role, UPLOADS_DIR)")
    if old in src:
        src = src.replace(old, new, 1)
        print("[OK] main.py -> install_prescriptions branche")
    else:
        print("[!] anchor install_payments introuvable")
    MAIN.write_text(src, encoding="utf-8")
else:
    print("[i] main.py deja patche Phase 6")

# ============================================================
# 3. Section admin dans pharmacien.html/js
# ============================================================
PHHTML = STATIC / "pharmacien.html"
html = PHHTML.read_text(encoding="utf-8")
section = '''  <section class="admin-section" id="prescriptions-section">
    <h2 class="admin-title">&#128203; Ordonnances a verifier</h2>
    <div id="prescriptions-admin-list" class="prescriptions-admin-list"></div>
  </section>

'''
anchor = '<section class="admin-section" id="payments-section">'
if anchor in html and "prescriptions-admin-list" not in html:
    html = html.replace(anchor, section + anchor, 1)
    PHHTML.write_text(html, encoding="utf-8")
    print("[OK] pharmacien.html -> section Ordonnances")
else:
    print("[i] pharmacien.html deja patche")

PHJS = STATIC / "pharmacien.js"
js = PHJS.read_text(encoding="utf-8")
admin = '''
// ====== V3 : Ordonnances ======
function loadPrescriptionsDashboard() {
  var box = document.getElementById("prescriptions-admin-list");
  if (!box) return;
  box.innerHTML = '<div class="muted small" style="padding:8px">Chargement...</div>';
  fetch(API + "/prescriptions?status=PENDING").then(function (r) {
    if (!r.ok) throw new Error();
    return r.json();
  }).then(function (list) {
    box.innerHTML = "";
    if (!list || list.length === 0) {
      box.appendChild(el("div", "muted small", "Aucune ordonnance en attente."));
      return;
    }
    list.forEach(function (p) { box.appendChild(prescAdminRow(p)); });
  }).catch(function () {
    box.innerHTML = '<div class="muted small" style="padding:8px">Erreur de chargement.</div>';
  });
}

function prescAdminRow(p) {
  var row = el("div", "presc-admin-row");
  var info = el("div", "presc-admin-info");
  info.appendChild(el("div", "presc-admin-ref", p.order_reference));
  info.appendChild(el("div", "presc-admin-meta", (p.customer_name || "") + " - " + (p.phone || "")));
  var link = el("a", "btn btn-ghost", "Voir l'ordonnance");
  link.href = p.file_path; link.target = "_blank"; link.rel = "noopener";
  var ok = el("button", "btn btn-primary", "Approuver");
  ok.type = "button";
  ok.addEventListener("click", function () {
    if (!confirm("Approuver cette ordonnance ?")) return;
    fetch(API + "/prescriptions/" + p.id + "/review", {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "APPROVED", comment: "" })
    }).then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(loadPrescriptionsDashboard).catch(function () { alert("Erreur"); });
  });
  var ko = el("button", "btn-danger", "Refuser");
  ko.type = "button";
  ko.addEventListener("click", function () {
    var reason = prompt("Motif du refus :");
    if (!reason) return;
    fetch(API + "/prescriptions/" + p.id + "/review", {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "REJECTED", comment: reason })
    }).then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(loadPrescriptionsDashboard).catch(function () { alert("Erreur"); });
  });
  var review = el("button", "btn btn-ghost", "A revoir");
  review.type = "button";
  review.addEventListener("click", function () {
    var reason = prompt("Message pour le patient :", "Merci de renvoyer une photo plus nette.");
    if (!reason) return;
    fetch(API + "/prescriptions/" + p.id + "/review", {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "NEEDS_REVIEW", comment: reason })
    }).then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(loadPrescriptionsDashboard).catch(function () { alert("Erreur"); });
  });
  var actions = el("div", "presc-admin-actions");
  actions.appendChild(link); actions.appendChild(ok);
  actions.appendChild(review); actions.appendChild(ko);
  row.appendChild(info); row.appendChild(actions);
  return row;
}

document.addEventListener("DOMContentLoaded", function () {
  setTimeout(loadPrescriptionsDashboard, 400);
});
'''
if "loadPrescriptionsDashboard" not in js:
    PHJS.write_text(js + "\n" + admin, encoding="utf-8")
    print("[OK] pharmacien.js -> loadPrescriptionsDashboard")

# Styles
PHCSS = STATIC / "pharmacien.css"
css = PHCSS.read_text(encoding="utf-8")
if ".presc-admin-row" not in css:
    css += '''
.prescriptions-admin-list{display:flex;flex-direction:column;gap:8px;margin-bottom:14px}
.presc-admin-row{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:12px 14px;background:var(--white);border:1px solid var(--line);border-radius:12px}
.presc-admin-info{flex:1;min-width:200px}
.presc-admin-ref{font-weight:700;font-size:14px;font-family:Consolas,monospace}
.presc-admin-meta{font-size:12px;color:var(--muted)}
.presc-admin-actions{display:flex;gap:8px;flex-wrap:wrap}
.presc-admin-actions .btn{padding:8px 14px;font-size:13px}
'''
    PHCSS.write_text(css, encoding="utf-8")
    print("[OK] pharmacien.css -> styles ordonnances")

print()
print("=" * 60)
print("PHASE 6 installee.")
print("=" * 60)
print("Routes :")
print("  POST   /api/orders/{ref}/prescription")
print("  GET    /api/orders/{ref}/prescription")
print("  GET    /api/prescriptions?status=")
print("  PATCH  /api/prescriptions/{id}/review")
print("  GET    /api/orders/{ref}/requires-prescription")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  python main.py")
print("  python test_phase6.py   (dans un autre CMD)")