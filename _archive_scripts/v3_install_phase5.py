"""
v3_install_phase5.py - Paiement manuel avec preuve.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
MODULES = BASE / "v3_modules"
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_v3_p5_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAIN, backup / "main.py")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. v3_modules/payments.py
# ============================================================
PAY = '''"""Paiement manuel + preuve (Phase 5)."""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

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

            now = datetime.now().isoformat(timespec="seconds")
            cur = conn.execute(
                "INSERT INTO payments (order_id, amount, payment_method,"
                " payment_number, payment_name, status, created_at)"
                " VALUES (?, ?, ?, ?, ?, 'PENDING', ?)",
                (order["id"], float(order["total"] or 0), method,
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
        return _row(row) if row else {"status": "NONE", "amount": order["total"]}

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
                   " o.customer_name, o.phone, o.total, o.user_id"
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
                " o.phone, o.total FROM payments p"
                " JOIN orders o ON o.id = p.order_id WHERE p.id = ?",
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


'''
(MODULES / "payments.py").write_text(PAY, encoding="utf-8")
print("[OK] v3_modules/payments.py")

# ============================================================
# 2. Patch main.py
# ============================================================
src = MAIN.read_text(encoding="utf-8")
if "install_payments" not in src:
    old = "install_cart(app, get_db, require_role, compute_delivery_fee)"
    new = (old + "\n"
           "from v3_modules.payments import install_payments\n"
           "install_payments(app, get_db, require_role, UPLOADS_DIR)")
    if old in src:
        src = src.replace(old, new, 1)
        print("[OK] main.py -> install_payments branche")
    else:
        print("[!] anchor install_cart introuvable")
    MAIN.write_text(src, encoding="utf-8")
else:
    print("[i] main.py deja patche Phase 5")

# ============================================================
# 3. Frontend client : payment.html
# ============================================================
PAY_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paiement - Elokinab Health</title>
<link rel="stylesheet" href="/static/auth.css">
<style>
  .pay-amount{
    background:#e8f7f1;border:1px solid #c7e9dc;border-radius:14px;
    padding:18px;margin:14px 0;text-align:center;
  }
  .pay-amount .label{font-size:12px;color:#6c8a80;text-transform:uppercase;letter-spacing:.06em;font-weight:700}
  .pay-amount .value{font-size:30px;font-weight:800;color:#0a7a5a;margin-top:4px}
  .pay-number{
    background:#fff;border:2px dashed #0f9d76;border-radius:14px;
    padding:18px;margin:14px 0;text-align:center;
  }
  .pay-number .label{font-size:12px;color:#6c8a80;text-transform:uppercase;letter-spacing:.06em;font-weight:700}
  .pay-number .value{font-size:22px;font-weight:800;color:#0f2620;margin-top:4px;font-family:Consolas,monospace}
  .pay-number .name{font-size:13px;color:#6c8a80;margin-top:2px}
  .copy-btn{
    margin-top:8px;background:#0f9d76;color:#fff;border:0;
    padding:8px 16px;border-radius:9px;font-weight:700;cursor:pointer;
  }
  .status-pill{display:inline-block;font-size:11px;font-weight:800;padding:5px 10px;border-radius:999px;text-transform:uppercase;letter-spacing:.05em}
  .status-PENDING{background:#fff4e0;color:#b26b00}
  .status-PROOF_SUBMITTED{background:#e3f0ff;color:#1b5aae}
  .status-VERIFIED{background:#e3f7ee;color:#0a7a5a}
  .status-REJECTED{background:#fdecec;color:#b23c3c}
  .steps{font-size:13px;color:#6c8a80;margin:14px 0;padding-left:18px}
  .steps li{margin-bottom:6px}
  .proof-link{display:inline-block;color:#0a7a5a;font-weight:700;margin-top:6px;font-size:13px}
  .auth-card input[type=file]{padding:10px;border:1px dashed #ddece6;border-radius:11px;background:#fafdfb;width:100%}
</style>
</head>
<body class="auth-body">
<div class="auth-card">
  <div class="auth-logo">
    <div class="auth-logo-mark">+</div>
    <div class="auth-logo-text">
      <strong>Elokinab Health</strong>
      <small>Paiement</small>
    </div>
  </div>
  <h1>Paiement de la commande</h1>
  <p class="sub" id="ref">Reference : ...</p>
  <div id="msg" class="auth-msg hidden"></div>
  <div id="status-pill-wrap"></div>
  <div class="pay-amount">
    <div class="label">Montant a payer</div>
    <div class="value" id="amount">0 FCFA</div>
  </div>
  <div class="pay-number">
    <div class="label">Effectuez le transfert au numero</div>
    <div class="value" id="pay-number">-</div>
    <div class="name" id="pay-name"></div>
    <button class="copy-btn" id="copy-btn" type="button">Copier le numero</button>
  </div>
  <ol class="steps">
    <li>Effectuez le transfert du montant exact.</li>
    <li>Prenez une capture d'ecran du recu.</li>
    <li>Chargez la capture ci-dessous.</li>
  </ol>
  <div class="auth-field">
    <label for="proof">Preuve de paiement (JPG / PNG / PDF)</label>
    <input type="file" id="proof" accept="image/*,application/pdf">
  </div>
  <button class="auth-btn" id="upload-btn" type="button">Envoyer la preuve</button>
  <div id="proof-view"></div>
  <div class="auth-alt"><a href="/suivi" id="track-link">Suivre ma commande</a></div>
</div>
<script src="/static/payment.js"></script>
</body>
</html>
'''
(STATIC / "payment.html").write_text(PAY_HTML, encoding="utf-8")
print("[OK] static/payment.html")

PAY_JS = '''(function () {
  function $(id) { return document.getElementById(id); }
  function money(v) { return Math.round(Number(v) || 0).toLocaleString("fr-FR") + " FCFA"; }
  function showMsg(t, ok) { var m = $("msg"); m.textContent = t; m.className = "auth-msg" + (ok ? " ok" : ""); }
  function hideMsg() { var m = $("msg"); m.className = "auth-msg hidden"; }

  var LABELS = {
    NONE: "Non initie",
    PENDING: "En attente de preuve",
    PROOF_SUBMITTED: "Preuve en verification",
    VERIFIED: "Paiement verifie",
    REJECTED: "Paiement refuse"
  };

  var ref = new URLSearchParams(window.location.search).get("ref");
  if (!ref) {
    showMsg("Reference de commande manquante");
    return;
  }

  $("ref").textContent = "Reference : " + ref;
  $("track-link").href = "/suivi?ref=" + encodeURIComponent(ref);

  function load() {
    fetch("/api/orders/" + encodeURIComponent(ref) + "/payment").then(function (r) {
      if (r.status === 401) { window.location.href = "/static/login.html?next=/static/payment.html?ref=" + encodeURIComponent(ref); return null; }
      if (!r.ok) return null;
      return r.json();
    }).then(function (p) {
      if (!p) return;
      $("amount").textContent = money(p.amount);
      $("pay-number").textContent = p.payment_number || "(non configure)";
      $("pay-name").textContent = p.payment_name || "";
      var status = p.status || "NONE";
      $("status-pill-wrap").innerHTML = '<span class="status-pill status-' + status + '">' +
        (LABELS[status] || status) + '</span>';
      if (p.proof_file) {
        $("proof-view").innerHTML = '<a class="proof-link" target="_blank" rel="noopener" href="' +
          p.proof_file + '">Voir la preuve envoyee</a>';
      }
      if (status === "VERIFIED") {
        $("upload-btn").disabled = true;
        $("upload-btn").textContent = "Paiement verifie ✓";
      }
    });
  }

  function ensurePayment() {
    return fetch("/api/orders/" + encodeURIComponent(ref) + "/payment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payment_method: "MANUAL" })
    }).then(function (r) {
      if (r.status === 401) { window.location.href = "/static/login.html"; return null; }
      return r.json();
    });
  }

  function upload() {
    hideMsg();
    var f = $("proof").files[0];
    if (!f) { showMsg("Choisissez un fichier."); return; }
    var btn = $("upload-btn");
    btn.disabled = true;
    btn.textContent = "Envoi...";

    ensurePayment().then(function () {
      var fd = new FormData();
      fd.append("file", f);
      return fetch("/api/orders/" + encodeURIComponent(ref) + "/payment/proof", {
        method: "POST",
        body: fd
      });
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    }).then(function () {
      showMsg("Preuve envoyee. La pharmacie va verifier.", true);
      load();
      btn.disabled = false;
      btn.textContent = "Envoyer la preuve";
    }).catch(function (e) {
      showMsg(e.message);
      btn.disabled = false;
      btn.textContent = "Envoyer la preuve";
    });
  }

  function copyNumber() {
    var n = $("pay-number").textContent;
    if (!n || n === "-" || n === "(non configure)") { showMsg("Aucun numero configure"); return; }
    if (navigator.clipboard) {
      navigator.clipboard.writeText(n).then(function () {
        showMsg("Numero copie", true);
        setTimeout(hideMsg, 1500);
      });
    } else {
      showMsg("Copiez manuellement : " + n, true);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    load();
    $("upload-btn").addEventListener("click", upload);
    $("copy-btn").addEventListener("click", copyNumber);
  });
})();
'''
(STATIC / "payment.js").write_text(PAY_JS, encoding="utf-8")
print("[OK] static/payment.js")

# ============================================================
# 4. Frontend pharmacien : ajouter une section paiements
# ============================================================
PHJS = STATIC / "pharmacien.js"
js = PHJS.read_text(encoding="utf-8")

admin = '''
// ====== V3 : Paiements ======
function loadPaymentsDashboard() {
  var box = document.getElementById("payments-admin-list");
  if (!box) return;
  box.innerHTML = '<div class="muted small" style="padding:8px">Chargement...</div>';
  fetch(API + "/payments?status=PROOF_SUBMITTED").then(function (r) {
    if (!r.ok) throw new Error("payments");
    return r.json();
  }).then(function (list) {
    box.innerHTML = "";
    if (!list || list.length === 0) {
      box.appendChild(el("div", "muted small", "Aucune preuve en attente."));
      return;
    }
    list.forEach(function (p) { box.appendChild(paymentAdminRow(p)); });
  }).catch(function () {
    box.innerHTML = '<div class="muted small" style="padding:8px">Erreur de chargement.</div>';
  });
}

function paymentAdminRow(p) {
  var row = el("div", "payment-admin-row");
  var info = el("div", "payment-admin-info");
  info.appendChild(el("div", "payment-admin-ref", p.order_reference));
  info.appendChild(el("div", "payment-admin-meta",
    (p.customer_name || "") + " - " + Math.round(p.total || 0).toLocaleString("fr-FR") + " FCFA"));
  info.appendChild(el("div", "payment-admin-method", p.payment_method));
  var link = el("a", "btn btn-ghost", "Voir preuve");
  link.href = p.proof_file;
  link.target = "_blank"; link.rel = "noopener";
  var ok = el("button", "btn btn-primary", "Valider");
  ok.type = "button";
  ok.addEventListener("click", function () {
    if (!confirm("Confirmer que le paiement de " + p.order_reference + " a bien ete recu ?")) return;
    fetch(API + "/payments/" + p.id + "/verify", { method: "PATCH" })
      .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(loadPaymentsDashboard).catch(function () { alert("Erreur"); });
  });
  var ko = el("button", "btn-danger", "Refuser");
  ko.type = "button";
  ko.addEventListener("click", function () {
    var reason = prompt("Motif du refus :");
    if (!reason) return;
    fetch(API + "/payments/" + p.id + "/reject", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rejection_reason: reason })
    }).then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(loadPaymentsDashboard).catch(function () { alert("Erreur"); });
  });
  var actions = el("div", "payment-admin-actions");
  actions.appendChild(link);
  actions.appendChild(ok);
  actions.appendChild(ko);
  row.appendChild(info);
  row.appendChild(actions);
  return row;
}

document.addEventListener("DOMContentLoaded", function () {
  setTimeout(loadPaymentsDashboard, 300);
});
'''

if "loadPaymentsDashboard" not in js:
    js = js + "\n" + admin
    PHJS.write_text(js, encoding="utf-8")
    print("[OK] pharmacien.js -> loadPaymentsDashboard")
else:
    print("[i] pharmacien.js deja patche")

# ============================================================
# 5. pharmacien.html : ajouter la section
# ============================================================
PHHTML = STATIC / "pharmacien.html"
html = PHHTML.read_text(encoding="utf-8")

section = '''  <section class="admin-section" id="payments-section">
    <h2 class="admin-title">&#128176; Paiements en attente</h2>
    <div id="payments-admin-list" class="payments-admin-list"></div>
  </section>

'''

anchor = '<section class="admin-section" id="drivers-section">'
if anchor in html and "payments-admin-list" not in html:
    html = html.replace(anchor, section + anchor, 1)
    PHHTML.write_text(html, encoding="utf-8")
    print("[OK] pharmacien.html -> section Paiements")
else:
    print("[i] pharmacien.html deja patche ou anchor introuvable")

# ============================================================
# 6. styles admin paiements
# ============================================================
PHCSS = STATIC / "pharmacien.css"
css = PHCSS.read_text(encoding="utf-8")
if ".payment-admin-row" not in css:
    css += '''
/* --- Paiements admin --- */
.payments-admin-list{display:flex;flex-direction:column;gap:8px;margin-bottom:14px}
.payment-admin-row{
  display:flex;align-items:center;gap:12px;flex-wrap:wrap;
  padding:12px 14px;background:var(--white);
  border:1px solid var(--line);border-radius:12px;
}
.payment-admin-info{flex:1;min-width:200px}
.payment-admin-ref{font-weight:700;font-size:14px;font-family:Consolas,monospace}
.payment-admin-meta{font-size:12px;color:var(--muted)}
.payment-admin-method{font-size:11px;font-weight:800;color:var(--green-dark);letter-spacing:.05em}
.payment-admin-actions{display:flex;gap:8px;flex-wrap:wrap}
.payment-admin-actions .btn{padding:8px 14px;font-size:13px}
.btn-danger{background:#b23c3c;color:#fff;border:0;padding:8px 14px;border-radius:10px;font-weight:700;cursor:pointer;font-size:13px}
.btn-danger:hover{background:#8f2f2f}
'''
    PHCSS.write_text(css, encoding="utf-8")
    print("[OK] pharmacien.css -> styles paiements")

print()
print("=" * 60)
print("PHASE 5 installee.")
print("=" * 60)
print()
print("Cote patient :")
print("  GET  /api/orders/{ref}/payment")
print("  POST /api/orders/{ref}/payment")
print("  POST /api/orders/{ref}/payment/proof")
print("  Page /static/payment.html?ref=CMD-XXX")
print()
print("Cote pharmacien :")
print("  GET   /api/payments")
print("  GET   /api/payments/{id}")
print("  PATCH /api/payments/{id}/verify")
print("  PATCH /api/payments/{id}/reject")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  python main.py")
print("  python test_phase5.py   (dans un autre CMD)")