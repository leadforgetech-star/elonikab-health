"""
v6_refonte_suivi.py
- Table order_status_history + backfill (idempotent)
- Hook dans PATCH /api/orders/{ref}/status
- Route GET /api/orders/{ref}/timeline
- Refonte suivi.html (bleu, 2 blocs, timeline dynamique, details)
- Refonte professional_commandes.html (liste compacte bleue)
"""
from pathlib import Path
import datetime
import re
import shutil
import sqlite3

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
MAIN = BASE / "main.py"
MODULES = BASE / "v3_modules"
DB = BASE / "database.db"

# ============================================================
# 0. BACKUP
# ============================================================
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_v6_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(DB, backup / "database.db")
shutil.copy2(MAIN, backup / "main.py")
for f in ("suivi.html", "suivi.js", "suivi.css",
          "professional_commandes.html"):
    p = STATIC / f
    if p.exists():
        shutil.copy2(p, backup / f)
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. MIGRATION : table order_status_history + BACKFILL
# ============================================================
conn = sqlite3.connect(DB)
conn.execute("""
    CREATE TABLE IF NOT EXISTS order_status_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        from_status TEXT,
        to_status TEXT NOT NULL,
        changed_at TEXT NOT NULL,
        changed_by INTEGER,
        note TEXT DEFAULT '',
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
    )
""")
conn.execute("CREATE INDEX IF NOT EXISTS idx_osh_order ON order_status_history(order_id)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_osh_changed ON order_status_history(changed_at)")
conn.commit()

# Backfill : pour chaque commande, si aucun historique, inserer la creation
rows = conn.execute("""
    SELECT o.id, o.status, o.created_at
    FROM orders o
    LEFT JOIN order_status_history h ON h.order_id = o.id
    WHERE h.id IS NULL
""").fetchall()

inserted = 0
for oid, status, created_at in rows:
    if not created_at:
        created_at = datetime.datetime.now().isoformat(timespec="seconds")
    # Evenement initial
    conn.execute(
        "INSERT INTO order_status_history (order_id, from_status, to_status,"
        " changed_at, changed_by, note)"
        " VALUES (?, NULL, 'created', ?, NULL, 'Creation de la commande')",
        (oid, created_at)
    )
    # Si le statut actuel n'est pas le statut initial, ajouter un evenement
    # "statut actuel connu" avec la date de creation (pas de vraie date dispo)
    if status and status != "en_attente":
        conn.execute(
            "INSERT INTO order_status_history (order_id, from_status, to_status,"
            " changed_at, changed_by, note)"
            " VALUES (?, 'en_attente', ?, ?, NULL, 'Statut actuel (date estimee)')",
            (oid, status, created_at)
        )
    inserted += 1
conn.commit()
conn.close()
print(f"[OK] Migration + backfill : {inserted} commandes initialisees")

# ============================================================
# 2. MODULE : order_timeline.py
# ============================================================
TIMELINE_MODULE = '''"""Timeline dynamique d'une commande (V6)."""
from fastapi import Depends, HTTPException


STATUS_LABELS = {
    "en_attente": "En attente",
    "confirmee": "Confirmee",
    "en_preparation": "En preparation",
    "prete": "Prete",
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
                "hint": "Votre demande a ete enregistree par Elokinab Health.",
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
                "payment_status_label": PAYMENT_STATUS_LABELS.get(payment_status, payment_status),
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


'''
(MODULES / "order_timeline.py").write_text(TIMELINE_MODULE, encoding="utf-8")
print("[OK] v3_modules/order_timeline.py")

# ============================================================
# 3. PATCH main.py : installer order_timeline + hook statut
# ============================================================
src = MAIN.read_text(encoding="utf-8")

if "install_order_timeline" not in src:
    old = "install_b2b(app, get_db, require_role, UPLOADS_DIR)"
    new = (old + "\n"
           "from v3_modules.order_timeline import install_order_timeline\n"
           "install_order_timeline(app, get_db, require_role)")
    if old in src:
        src = src.replace(old, new, 1)
        print("[OK] main.py -> install_order_timeline")

# Hook dans update_order_status
old_hook = '''    conn.execute("UPDATE orders SET status = ? WHERE reference = ?", (new_status, reference))
    conn.commit()'''
new_hook = '''    conn.execute("UPDATE orders SET status = ? WHERE reference = ?", (new_status, reference))
    # V6 : enregistrer dans l'historique
    try:
        conn.execute(
            "INSERT INTO order_status_history (order_id, from_status, to_status,"
            " changed_at, changed_by, note)"
            " VALUES (?, ?, ?, ?, ?, '')",
            (row["id"], row["status"], new_status,
             datetime.now().isoformat(timespec="seconds"), user["id"] if user else None)
        )
    except Exception:
        pass
    conn.commit()'''
if old_hook in src and "order_status_history" not in src.split(old_hook)[1][:300]:
    src = src.replace(old_hook, new_hook, 1)
    print("[OK] main.py -> hook historique statut")
elif "order_status_history" in src:
    print("[i] main.py -> hook deja en place")

MAIN.write_text(src, encoding="utf-8")

# ============================================================
# 4. REFONTE SUIVI.HTML (bleu, 2 blocs, timeline)
# ============================================================
SUIVI_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Suivi de commande - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<link rel="stylesheet" href="/static/suivi.css">
</head>
<body>

<header class="sv-header">
  <div class="sv-header-inner">
    <a class="sv-back" href="/professionnel/commandes" aria-label="Retour">&#8592;</a>
    <span class="sv-title">Ma commande</span>
    <span class="sv-ref" id="page-ref">—</span>
  </div>
</header>

<main class="sv-main" id="main">
  <div class="sv-loading">Chargement...</div>
</main>

<script src="/static/safe_locale.js"></script>
<script src="/static/suivi.js"></script>
</body>
</html>
'''
(STATIC / "suivi.html").write_text(SUIVI_HTML, encoding="utf-8")
print("[OK] suivi.html reecrit")

# ============================================================
# 5. SUIVI.CSS (bleu, cartes, timeline)
# ============================================================
SUIVI_CSS = '''/* Elokinab Health - Suivi de commande */
:root{
  --blue:#1a4a7f;--blue-dark:#123258;--blue-soft:#eaf1f9;
  --wa:#25d366;--wa-dark:#1da851;
  --ink:#0f172a;--muted:#64748b;--line:#e6ebf1;--bg:#f7fafc;
  --ok:#0a7a5a;--warn:#8a5a00;--danger:#b23c3c;
  --radius:14px;
}
*,*::before,*::after{box-sizing:border-box}
html,body{overflow-x:clip;margin:0;padding:0}
body{
  font-family:-apple-system,"Segoe UI",system-ui,sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.5;font-size:15px;
  -webkit-font-smoothing:antialiased;padding-bottom:40px;
}
a{color:inherit;text-decoration:none}
button{font-family:inherit;cursor:pointer}
.hidden{display:none !important}

.sv-header{
  background:#fff;border-bottom:1px solid var(--line);
  position:sticky;top:0;z-index:50;
}
.sv-header-inner{
  max-width:640px;margin:0 auto;padding:12px 16px;
  display:flex;align-items:center;gap:12px;
}
.sv-back{
  width:36px;height:36px;border-radius:10px;border:1px solid var(--line);
  background:#fff;color:var(--ink);font-size:18px;
  display:flex;align-items:center;justify-content:center;text-decoration:none;
}
.sv-title{font-size:15px;font-weight:800;flex:1}
.sv-ref{margin-left:auto;font-family:Consolas,monospace;font-size:11px;color:var(--muted)}

.sv-main{max-width:640px;margin:0 auto;padding:18px 16px}
.sv-loading{text-align:center;padding:40px;color:var(--muted)}

/* En-tete */
.sv-head{
  background:#fff;border:1px solid var(--line);border-radius:var(--radius);
  padding:16px;margin-bottom:14px;
}
.sv-head-ref{
  font-family:Consolas,monospace;font-weight:800;
  font-size:15px;color:var(--blue-dark);margin:0 0 4px;
}
.sv-head-date{font-size:12px;color:var(--muted);margin:0}

/* Blocs */
.sv-block{
  background:#fff;border:1px solid var(--line);border-radius:var(--radius);
  padding:16px;margin-bottom:14px;
}
.sv-block-title{
  font-size:11px;font-weight:800;color:var(--muted);
  text-transform:uppercase;letter-spacing:.08em;
  margin:0 0 12px;display:flex;align-items:center;gap:8px;
}
.sv-block-title .ico{font-size:14px}

.sv-status-pill{
  display:inline-flex;align-items:center;gap:6px;
  padding:5px 12px;border-radius:999px;
  font-size:11px;font-weight:800;
  text-transform:uppercase;letter-spacing:.05em;
}
.sv-status-pill::before{
  content:"";width:7px;height:7px;border-radius:50%;background:currentColor;
}
.pill-pending{background:#fff7e6;color:var(--warn)}
.pill-submitted{background:var(--blue-soft);color:var(--blue-dark)}
.pill-verified{background:#e6f7f1;color:var(--ok)}
.pill-rejected{background:#fee2e2;color:var(--danger)}
.pill-none{background:#e2e8f0;color:#475569}
.pill-confirmed{background:#e6f7f1;color:var(--ok)}
.pill-preparing{background:#f3e8ff;color:#6335b8}
.pill-ready{background:#e6f7f1;color:var(--ok)}
.pill-done{background:#e2e8f0;color:#475569}
.pill-refused{background:#fee2e2;color:var(--danger)}

.sv-status-hint{
  font-size:13px;color:var(--muted);margin:10px 0 0;line-height:1.5;
}

.sv-amounts{
  display:flex;justify-content:space-between;align-items:center;
  font-size:14px;margin-top:12px;padding-top:12px;
  border-top:1px solid var(--line);
}
.sv-amounts .lbl{color:var(--muted)}
.sv-amounts .val{font-weight:800;font-family:Consolas,monospace;color:var(--ink)}

.sv-rejection{
  background:#fee2e2;color:var(--danger);border:1px solid #f6d2d2;
  border-radius:10px;padding:10px 12px;font-size:13px;margin-top:12px;
}

/* Timeline */
.sv-timeline{
  display:flex;flex-direction:column;gap:0;
  padding-left:4px;
}
.sv-step{
  display:flex;gap:14px;position:relative;
  padding-bottom:18px;
}
.sv-step:last-child{padding-bottom:0}
.sv-step::before{
  content:"";position:absolute;
  left:11px;top:24px;bottom:0;
  width:2px;background:var(--line);
}
.sv-step:last-child::before{display:none}
.sv-step.done::before{background:var(--blue)}
.sv-step.current::before{background:linear-gradient(var(--blue),var(--line))}
.sv-step.error::before{background:var(--danger)}

.sv-dot{
  width:24px;height:24px;border-radius:50%;
  background:#fff;border:2px solid var(--line);
  display:flex;align-items:center;justify-content:center;
  font-size:11px;font-weight:800;color:var(--muted);
  flex-shrink:0;z-index:1;
}
.sv-step.done .sv-dot{background:var(--blue);border-color:var(--blue);color:#fff}
.sv-step.current .sv-dot{
  background:#fff;border-color:var(--blue);color:var(--blue);
  box-shadow:0 0 0 4px var(--blue-soft);
}
.sv-step.error .sv-dot{background:var(--danger);border-color:var(--danger);color:#fff}
.sv-step.pending .sv-dot{background:#fff;border-color:var(--line);color:#94a3b8}

.sv-info{display:flex;flex-direction:column;gap:3px;padding-top:2px;flex:1;min-width:0}
.sv-label{font-size:14px;font-weight:700;color:var(--ink);line-height:1.3}
.sv-step.pending .sv-label{color:#94a3b8;font-weight:600}
.sv-hint{font-size:12px;color:var(--muted);line-height:1.4}
.sv-date{font-size:11px;color:var(--muted);font-family:Consolas,monospace;margin-top:2px}

/* Items */
.sv-item{
  display:flex;align-items:flex-start;gap:12px;
  padding:12px 0;border-bottom:1px solid var(--line);
}
.sv-item:last-child{border-bottom:0}
.sv-item-body{flex:1;min-width:0}
.sv-item-name{font-size:14px;font-weight:700;margin:0 0 2px;word-break:break-word}
.sv-item-meta{font-size:12px;color:var(--muted);font-family:Consolas,monospace}
.sv-item-price{
  font-size:14px;font-weight:800;font-family:Consolas,monospace;
  color:var(--ink);white-space:nowrap;
}

.sv-totals{
  margin-top:8px;padding-top:12px;border-top:1px solid var(--line);
}
.sv-totals-line{
  display:flex;justify-content:space-between;
  padding:6px 0;font-size:14px;
}
.sv-totals-line .lbl{color:var(--muted)}
.sv-totals-line .val{font-weight:700;font-family:Consolas,monospace;color:var(--ink)}
.sv-totals-line.total{
  border-top:1px solid var(--line);
  margin-top:6px;padding-top:12px;
  font-size:16px;font-weight:800;
}
.sv-totals-line.total .val{color:var(--blue-dark);font-size:18px}

/* Boutons */
.sv-actions{
  display:flex;flex-direction:column;gap:10px;
  margin-top:14px;padding-top:14px;
  border-top:1px solid var(--line);
}
.sv-btn{
  display:flex;align-items:center;justify-content:center;gap:8px;
  padding:14px;border:0;border-radius:12px;
  font-weight:800;font-size:14px;text-decoration:none;
  transition:.15s;width:100%;
}
.sv-btn-primary{background:var(--blue);color:#fff}
.sv-btn-primary:hover{background:var(--blue-dark)}
.sv-btn-wa{background:var(--wa);color:#fff}
.sv-btn-wa:hover{background:var(--wa-dark)}
.sv-btn-ghost{
  background:#fff;color:var(--ink);border:1px solid var(--line);
}
.sv-btn-ghost:hover{border-color:var(--blue);color:var(--blue)}

/* Empty */
.sv-empty{
  text-align:center;padding:40px 16px;color:var(--muted);
}
.sv-empty-icon{font-size:48px;opacity:.3;margin-bottom:12px}
.sv-empty h3{font-size:16px;color:var(--ink);margin:0 0 6px}
.sv-empty p{font-size:14px;margin:0 0 20px}

/* Form de recherche */
.sv-search-form{
  background:#fff;border:1px solid var(--line);border-radius:var(--radius);
  padding:16px;margin-bottom:14px;display:flex;flex-direction:column;gap:12px;
}
.sv-search-form input{
  padding:12px 14px;border:1px solid var(--line);border-radius:11px;
  font-family:Consolas,monospace;font-size:15px;
  text-transform:uppercase;letter-spacing:.05em;outline:none;
}
.sv-search-form input:focus{border-color:var(--blue)}

.sv-error{
  background:#fee2e2;color:var(--danger);border:1px solid #f6d2d2;
  border-radius:12px;padding:12px 14px;font-size:13px;margin-bottom:14px;
}

/* Wrapper */
.sv-wrapper{max-width:640px;margin:0 auto}

@media (max-width:400px){
  .sv-head-ref{font-size:13px}
}
'''
(STATIC / "suivi.css").write_text(SUIVI_CSS, encoding="utf-8")
print("[OK] suivi.css reecrit")

# ============================================================
# 6. SUIVI.JS (dynamique, base sur timeline API)
# ============================================================
SUIVI_JS = r'''/* Elokinab Health - Suivi de commande */
(function () {
  var API = "/api";
  var $ = function (id) { return document.getElementById(id); };

  var STATUS_PILLS = {
    en_attente: "pill-pending",
    confirmee: "pill-confirmed",
    en_preparation: "pill-preparing",
    prete: "pill-ready",
    terminee: "pill-done",
    refusee: "pill-refused",
  };

  var PAYMENT_PILLS = {
    NONE: "pill-none",
    PENDING: "pill-pending",
    PROOF_SUBMITTED: "pill-submitted",
    VERIFIED: "pill-verified",
    REJECTED: "pill-rejected",
  };

  function escapeHtml(s) {
    try {
      return String(s == null ? "" : s)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    } catch (e) { return ""; }
  }

  function money(v) {
    var n = Math.round(Number(v) || 0);
    try { return n.toLocaleString("fr-FR") + " FCFA"; }
    catch (e) {
      var s = String(n), out = "";
      for (var i = 0; i < s.length; i++) {
        if (i > 0 && (s.length - i) % 3 === 0) out += " ";
        out += s.charAt(i);
      }
      return out + " FCFA";
    }
  }

  function fmtDate(iso) {
    if (!iso) return "";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return String(iso);
      var day = d.getDate();
      var month = ["janv.","fevr.","mars","avr.","mai","juin",
                   "juil.","aout","sept.","oct.","nov.","dec."][d.getMonth()];
      var h = ("0" + d.getHours()).slice(-2);
      var m = ("0" + d.getMinutes()).slice(-2);
      return day + " " + month + " " + d.getFullYear() + " a " + h + ":" + m;
    } catch (e) { return String(iso); }
  }

  function fmtQty(q) {
    var n = Number(q) || 0;
    return (n === Math.floor(n)) ? String(n) : n.toFixed(2);
  }

  function renderNotFound() {
    $("main").innerHTML = '' +
      '<div class="sv-search-form">' +
        '<label for="ref-input" style="font-size:13px;font-weight:700">Numero de commande</label>' +
        '<input type="text" id="ref-input" placeholder="Ex : CMD-261006-XXXXXX" autocomplete="off">' +
        '<button class="sv-btn sv-btn-primary" id="ref-submit" type="button">Rechercher</button>' +
      '</div>' +
      '<div class="sv-empty">' +
        '<div class="sv-empty-icon">&#128230;</div>' +
        '<h3>Suivez votre commande</h3>' +
        '<p>Entrez votre numero de commande pour voir son avancement.</p>' +
      '</div>';

    var submit = $("ref-submit");
    var input = $("ref-input");
    if (submit) {
      submit.addEventListener("click", function () {
        var v = (input.value || "").trim().toUpperCase();
        if (!v) return;
        window.location.href = "/suivi?ref=" + encodeURIComponent(v);
      });
    }
    if (input) {
      input.addEventListener("keypress", function (e) {
        if (e.key === "Enter") submit.click();
      });
    }
  }

  function render(tl) {
    $("page-ref").textContent = tl.reference;

    var html = '';

    // En-tete
    html += '<div class="sv-head">' +
              '<div class="sv-head-ref">' + escapeHtml(tl.reference) + '</div>' +
              '<div class="sv-head-date">Creee le ' + escapeHtml(fmtDate(tl.created_at)) + '</div>' +
            '</div>';

    // Bloc Paiement
    var payPill = PAYMENT_PILLS[tl.payment_status] || "pill-none";
    html += '<div class="sv-block">' +
              '<div class="sv-block-title"><span class="ico">&#128179;</span> Paiement</div>' +
              '<span class="sv-status-pill ' + payPill + '">' +
                escapeHtml(tl.payment_status_label) +
              '</span>' +
              '<div class="sv-amounts">' +
                '<span class="lbl">Montant</span>' +
                '<span class="val">' + money(tl.total) + '</span>' +
              '</div>';

    if (tl.payment_status === "REJECTED" && tl.payment && tl.payment.rejection_reason) {
      html += '<div class="sv-rejection">Motif du refus : ' + escapeHtml(tl.payment.rejection_reason) + '</div>';
    }

    if (tl.can_pay) {
      html += '<div class="sv-actions">' +
                '<a class="sv-btn sv-btn-primary" href="/static/payment.html?ref=' +
                  encodeURIComponent(tl.reference) + '">' +
                  '<span>&#128179;</span> Aller au paiement' +
                '</a>' +
              '</div>';
    }
    html += '</div>';

    // Bloc Commande
    var ordPill = STATUS_PILLS[tl.status] || "pill-none";
    html += '<div class="sv-block">' +
              '<div class="sv-block-title"><span class="ico">&#128230;</span> Commande</div>' +
              '<span class="sv-status-pill ' + ordPill + '">' +
                escapeHtml(tl.status_label) +
              '</span>';

    // Hint selon statut
    var hints = {
      en_attente: "Votre demande a ete recue. La pharmacie va l'examiner.",
      confirmee: "La pharmacie a valide votre commande.",
      en_preparation: "Votre commande est en cours de preparation.",
      prete: "Votre commande est prete.",
      terminee: "Votre commande a ete remise ou livree.",
      refusee: "La pharmacie n'a pas pu donner suite a cette demande.",
    };
    if (hints[tl.status]) {
      html += '<div class="sv-status-hint">' + escapeHtml(hints[tl.status]) + '</div>';
    }
    html += '</div>';

    // Timeline
    if (tl.events && tl.events.length > 0) {
      html += '<div class="sv-block">' +
                '<div class="sv-block-title"><span class="ico">&#128200;</span> Progression</div>' +
                '<div class="sv-timeline">';

      tl.events.forEach(function (ev) {
        var state = ev.state || "done";
        var stateClass = state === "error" ? "error" : (state === "current" ? "current" : "done");
        var symbol = state === "error" ? "&#10005;" : (state === "current" ? "&#9679;" : "&#10003;");
        html += '<div class="sv-step ' + stateClass + '">' +
                  '<div class="sv-dot">' + symbol + '</div>' +
                  '<div class="sv-info">' +
                    '<div class="sv-label">' + escapeHtml(ev.label) + '</div>' +
                    (ev.hint ? '<div class="sv-hint">' + escapeHtml(ev.hint) + '</div>' : '') +
                    (ev.at ? '<div class="sv-date">' + escapeHtml(fmtDate(ev.at)) + '</div>' : '') +
                  '</div>' +
                '</div>';
      });

      html += '</div></div>';
    }

    // Detail produits
    if (tl.items && tl.items.length > 0) {
      html += '<div class="sv-block">' +
                '<div class="sv-block-title"><span class="ico">&#128138;</span> Details</div>';

      tl.items.forEach(function (it) {
        var qty = Number(it.quantity) || 0;
        var unit = Number(it.unit_price) || 0;
        var line = Number(it.subtotal) || (unit * qty);
        html += '<div class="sv-item">' +
                  '<div class="sv-item-body">' +
                    '<div class="sv-item-name">' + escapeHtml(it.product_name || "") + '</div>' +
                    '<div class="sv-item-meta">x ' + fmtQty(qty) + ' - ' + money(unit) + '</div>' +
                  '</div>' +
                  '<div class="sv-item-price">' + money(line) + '</div>' +
                '</div>';
      });

      // Totaux
      html += '<div class="sv-totals">' +
                '<div class="sv-totals-line">' +
                  '<span class="lbl">Sous-total</span>' +
                  '<span class="val">' + money(tl.subtotal) + '</span>' +
                '</div>' +
                '<div class="sv-totals-line">' +
                  '<span class="lbl">Frais de livraison</span>' +
                  '<span class="val">' +
                    (tl.delivery_mode === "retrait" ? "0 FCFA" : money(tl.delivery_fee)) +
                  '</span>' +
                '</div>' +
                '<div class="sv-totals-line total">' +
                  '<span>Total</span>' +
                  '<span class="val">' + money(tl.total) + '</span>' +
                '</div>' +
              '</div>';

      html += '</div>';
    }

    // Infos livraison
    if (tl.delivery_mode === "livraison" && tl.address) {
      html += '<div class="sv-block">' +
                '<div class="sv-block-title"><span class="ico">&#128205;</span> Livraison</div>' +
                '<div style="font-size:14px;line-height:1.6">' + escapeHtml(tl.address) + '</div>' +
                (tl.delivery_distance_km !== null && tl.delivery_distance_km !== undefined
                  ? '<div style="font-size:12px;color:#64748b;margin-top:6px">Distance : ' +
                    Number(tl.delivery_distance_km).toFixed(1) + ' km</div>'
                  : '') +
              '</div>';
    }

    // Actions
    html += '<div class="sv-block">' +
              '<div class="sv-actions">' +
                '<a class="sv-btn sv-btn-wa" href="https://wa.me/22871039904?text=' +
                  encodeURIComponent("Bonjour, j'ai une question sur ma commande " + tl.reference) +
                  '" target="_blank" rel="noopener">' +
                  '<span>&#128172;</span> Contacter la pharmacie' +
                '</a>' +
                '<a class="sv-btn sv-btn-ghost" href="/professionnel/commandes">' +
                  'Retour a mes commandes' +
                '</a>' +
              '</div>' +
            '</div>';

    $("main").innerHTML = html;
  }

  function load() {
    var params = new URLSearchParams(window.location.search);
    var ref = params.get("ref");
    if (!ref) { renderNotFound(); return; }

    fetch(API + "/orders/" + encodeURIComponent(ref) + "/timeline", {
      credentials: "same-origin"
    }).then(function (r) {
      if (r.status === 404) {
        $("main").innerHTML = '<div class="sv-error">Commande introuvable : ' +
          escapeHtml(ref) + '</div>';
        var back = document.createElement("a");
        back.className = "sv-btn sv-btn-ghost";
        back.href = "/professionnel/commandes";
        back.textContent = "Retour a mes commandes";
        $("main").appendChild(back);
        return null;
      }
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    }).then(function (tl) {
      if (tl) render(tl);
    }).catch(function (e) {
      $("main").innerHTML = '<div class="sv-error">Erreur : ' +
        escapeHtml(e.message) + '</div>';
    });
  }

  document.addEventListener("DOMContentLoaded", load);
})();
'''
(STATIC / "suivi.js").write_text(SUIVI_JS, encoding="utf-8")
print("[OK] suivi.js reecrit")

# ============================================================
# 7. REFONTE professional_commandes.html (liste compacte bleue)
# ============================================================
CMD_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Mes commandes - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
:root{
  --blue:#1a4a7f;--blue-dark:#123258;--blue-soft:#eaf1f9;
  --ink:#0f172a;--muted:#64748b;--line:#e6ebf1;--bg:#f7fafc;
  --ok:#0a7a5a;--warn:#8a5a00;--danger:#b23c3c;
}
*,*::before,*::after{box-sizing:border-box}
html,body{overflow-x:clip;margin:0;padding:0}
body{
  font-family:-apple-system,"Segoe UI",system-ui,sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.5;font-size:15px;
  -webkit-font-smoothing:antialiased;padding-bottom:100px;
}
a{color:inherit;text-decoration:none}
button{font-family:inherit;cursor:pointer}
.hidden{display:none !important}

.cm-header{
  background:#fff;border-bottom:1px solid var(--line);
  position:sticky;top:0;z-index:50;
}
.cm-header-inner{
  max-width:900px;margin:0 auto;padding:12px 16px;
  display:flex;align-items:center;gap:12px;
}
.cm-brand{display:flex;align-items:center;gap:9px;font-weight:800;font-size:15px}
.cm-brand-mark{
  width:32px;height:32px;border-radius:9px;
  background:linear-gradient(135deg,var(--blue),#2a6ba8);color:#fff;
  display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:800;
}
.cm-title{font-size:15px;font-weight:800;flex:1}
.cm-bell{
  width:36px;height:36px;border-radius:10px;border:1px solid var(--line);
  background:#fff;color:var(--ink);font-size:16px;
  display:flex;align-items:center;justify-content:center;position:relative;
}
.cm-bell-badge{
  position:absolute;top:-3px;right:-3px;background:var(--danger);
  color:#fff;font-size:9px;font-weight:800;min-width:16px;
  height:16px;padding:0 4px;border-radius:999px;
  display:flex;align-items:center;justify-content:center;
}

.cm-main{max-width:900px;margin:0 auto;padding:18px 16px}

.cm-h1{font-size:22px;font-weight:800;letter-spacing:-.02em;margin:0 0 4px}
.cm-sub{font-size:14px;color:var(--muted);margin:0 0 20px}

.cm-list{display:flex;flex-direction:column;gap:10px}
.cm-card{
  display:block;background:#fff;border:1px solid var(--line);
  border-radius:14px;padding:14px 16px;
  transition:.15s;text-decoration:none;color:inherit;
}
.cm-card:hover{border-color:var(--blue);box-shadow:0 4px 14px rgba(26,74,127,.08)}

.cm-card-head{
  display:flex;align-items:center;justify-content:space-between;
  gap:10px;margin-bottom:8px;
}
.cm-card-ref{
  font-family:Consolas,monospace;font-weight:800;font-size:14px;
  color:var(--ink);
}
.cm-card-date{font-size:12px;color:var(--muted)}
.cm-card-body{font-size:13px;color:var(--muted);margin-bottom:10px}
.cm-card-foot{
  display:flex;align-items:center;justify-content:space-between;
  gap:10px;flex-wrap:wrap;
}
.cm-card-pills{display:flex;gap:6px;flex-wrap:wrap}
.cm-card-total{
  font-weight:800;color:var(--blue-dark);
  font-family:Consolas,monospace;font-size:15px;
}

.cm-pill{
  display:inline-flex;align-items:center;gap:5px;
  padding:4px 10px;border-radius:999px;
  font-size:10px;font-weight:800;
  text-transform:uppercase;letter-spacing:.05em;
}
.cm-pill::before{
  content:"";width:6px;height:6px;border-radius:50%;background:currentColor;
}
.pill-pending{background:#fff7e6;color:var(--warn)}
.pill-confirmed{background:#e6f7f1;color:var(--ok)}
.pill-preparing{background:#f3e8ff;color:#6335b8}
.pill-ready{background:#e6f7f1;color:var(--ok)}
.pill-done{background:#e2e8f0;color:#475569}
.pill-refused{background:#fee2e2;color:var(--danger)}
.pill-submitted{background:var(--blue-soft);color:var(--blue-dark)}
.pill-verified{background:#e6f7f1;color:var(--ok)}
.pill-rejected{background:#fee2e2;color:var(--danger)}
.pill-none{background:#e2e8f0;color:#475569}

.cm-empty{
  text-align:center;padding:60px 20px;color:var(--muted);
  background:#fff;border:1px dashed var(--line);border-radius:14px;
}
.cm-empty-icon{font-size:48px;opacity:.3;margin-bottom:12px}
.cm-empty h3{color:var(--ink);font-size:16px;margin:0 0 6px}

.cm-btn{
  display:inline-flex;align-items:center;justify-content:center;gap:8px;
  padding:13px 20px;border:0;border-radius:12px;
  background:var(--blue);color:#fff;font-weight:800;font-size:14px;
  text-decoration:none;margin-top:16px;
}
.cm-btn:hover{background:var(--blue-dark)}

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
.pro-navbar a.active{color:var(--blue-dark)}
.pro-navbar .central{
  margin-top:-22px;background:var(--blue);color:#fff;border-radius:50%;
  width:64px;height:64px;justify-self:center;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  font-size:22px;font-weight:800;
  box-shadow:0 6px 20px rgba(26,74,127,.35);
  border:4px solid var(--bg);position:relative;
}
.pro-navbar .central .lbl{font-size:9px;font-weight:700;margin-top:-2px}
</style>
</head>
<body>

<header class="cm-header">
  <div class="cm-header-inner">
    <a class="cm-brand" href="/professionnel">
      <span class="cm-brand-mark">+</span>
      Elokinab
    </a>
    <span class="cm-title">Mes commandes</span>
  </div>
</header>

<main class="cm-main">
  <h1 class="cm-h1">Mes commandes</h1>
  <p class="cm-sub">Suivez l'etat de vos commandes et de vos paiements.</p>

  <div id="list" class="cm-list">
    <div style="text-align:center;padding:40px;color:#64748b">Chargement...</div>
  </div>
</main>

<nav class="pro-navbar">
  <a href="/professionnel"><span class="ico">&#127968;</span> Accueil</a>
  <a href="/professionnel/catalogue"><span class="ico">&#128722;</span> Catalogue</a>
  <a href="/professionnel/demande" class="central">
    <span>+</span><span class="lbl">Demande</span>
  </a>
  <a href="/professionnel/commandes" class="active"><span class="ico">&#128230;</span> Commandes</a>
  <a href="/professionnel/etablissement"><span class="ico">&#9701;</span> Etabl.</a>
</nav>

<script src="/static/safe_locale.js"></script>
<script>
(function () {
  var API = "/api";

  function escapeHtml(s) {
    try {
      return String(s == null ? "" : s)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    } catch (e) { return ""; }
  }

  function money(v) {
    var n = Math.round(Number(v) || 0);
    try { return n.toLocaleString("fr-FR") + " FCFA"; }
    catch (e) {
      var s = String(n), out = "";
      for (var i = 0; i < s.length; i++) {
        if (i > 0 && (s.length - i) % 3 === 0) out += " ";
        out += s.charAt(i);
      }
      return out + " FCFA";
    }
  }

  function fmtDate(iso) {
    if (!iso) return "";
    try {
      var d = new Date(iso);
      if (isNaN(d)) return String(iso);
      var day = d.getDate();
      var m = ["janv.","fevr.","mars","avr.","mai","juin",
               "juil.","aout","sept.","oct.","nov.","dec."][d.getMonth()];
      return day + " " + m + " " + d.getFullYear();
    } catch (e) { return String(iso); }
  }

  var STATUS_PILLS = {
    en_attente: "pill-pending", confirmee: "pill-confirmed",
    en_preparation: "pill-preparing", prete: "pill-ready",
    terminee: "pill-done", refusee: "pill-refused",
  };
  var STATUS_LABELS = {
    en_attente: "En attente", confirmee: "Confirmee",
    en_preparation: "En preparation", prete: "Prete",
    terminee: "Terminee", refusee: "Refusee",
  };
  var PAYMENT_PILLS = {
    NONE: "pill-none", PENDING: "pill-pending",
    PROOF_SUBMITTED: "pill-submitted",
    VERIFIED: "pill-verified", REJECTED: "pill-rejected",
  };
  var PAYMENT_LABELS = {
    NONE: "Paiement non initie", PENDING: "Paiement a effectuer",
    PROOF_SUBMITTED: "Preuve en verification",
    VERIFIED: "Paiement verifie", REJECTED: "Paiement refuse",
  };

  function render(list) {
    var box = document.getElementById("list");
    if (!list || list.length === 0) {
      box.innerHTML = '<div class="cm-empty">' +
        '<div class="cm-empty-icon">&#128230;</div>' +
        '<h3>Aucune commande pour le moment</h3>' +
        '<p>Vos futures commandes apparaitront ici.</p>' +
        '<a class="cm-btn" href="/professionnel/catalogue">Parcourir le catalogue</a>' +
        '</div>';
      return;
    }

    box.innerHTML = "";
    list.forEach(function (o) {
      var card = document.createElement("a");
      card.className = "cm-card";
      card.href = "/suivi?ref=" + encodeURIComponent(o.reference);

      var statusPill = STATUS_PILLS[o.status] || "pill-none";
      var statusLbl = STATUS_LABELS[o.status] || o.status;
      var payPill = PAYMENT_PILLS[o.payment_status] || "pill-none";
      var payLbl = PAYMENT_LABELS[o.payment_status] || o.payment_status;
      var subtotal = Number(o.subtotal) || 0;
      var fee = Number(o.delivery_fee) || 0;
      var total = subtotal + fee;

      card.innerHTML =
        '<div class="cm-card-head">' +
          '<span class="cm-card-ref">' + escapeHtml(o.reference) + '</span>' +
          '<span class="cm-card-date">' + escapeHtml(fmtDate(o.created_at)) + '</span>' +
        '</div>' +
        '<div class="cm-card-body">' +
          (o.items_count || 0) + ' produit' + ((o.items_count || 0) > 1 ? 's' : '') +
          ' - ' + (o.delivery_mode === "livraison" ? "Livraison" : "Retrait") +
        '</div>' +
        '<div class="cm-card-foot">' +
          '<div class="cm-card-pills">' +
            '<span class="cm-pill ' + statusPill + '">' + escapeHtml(statusLbl) + '</span>' +
            '<span class="cm-pill ' + payPill + '">' + escapeHtml(payLbl) + '</span>' +
          '</div>' +
          '<span class="cm-card-total">' + money(total) + '</span>' +
        '</div>';

      box.appendChild(card);
    });
  }

  function load() {
    // Utilise /api/orders/mine (deja existant) et enrichit avec les infos
    fetch(API + "/orders/mine", { credentials: "same-origin" })
      .then(function (r) {
        if (r.status === 401) {
          window.location.href = "/connexion?next=/professionnel/commandes";
          return [];
        }
        return r.ok ? r.json() : [];
      })
      .then(function (list) {
        // Filtrer les brouillons et enrichir avec items_count
        var promises = (list || []).map(function (o) {
          return fetch(API + "/orders/" + encodeURIComponent(o.reference) + "/timeline", {
            credentials: "same-origin"
          }).then(function (r) {
            if (!r.ok) return o;
            return r.json();
          }).catch(function () { return o; });
        });
        return Promise.all(promises);
      })
      .then(function (enriched) {
        // Mapper vers format compact
        var out = enriched.map(function (tl) {
          var items = tl.items || [];
          return {
            reference: tl.reference,
            status: tl.status,
            payment_status: tl.payment_status,
            delivery_mode: tl.delivery_mode,
            created_at: tl.created_at,
            subtotal: tl.subtotal,
            delivery_fee: tl.delivery_fee,
            items_count: items.length,
          };
        });
        render(out);
      })
      .catch(function (e) {
        document.getElementById("list").innerHTML =
          '<div class="cm-empty"><h3>Erreur de chargement</h3><p>' +
          escapeHtml(e.message || "") + '</p></div>';
      });
  }

  document.addEventListener("DOMContentLoaded", load);
})();
</script>
</body>
</html>
'''
(STATIC / "professional_commandes.html").write_text(CMD_HTML, encoding="utf-8")
print("[OK] professional_commandes.html reecrit")

print()
print("=" * 60)
print("REFONTE V6 LIVREE")
print("=" * 60)
print()
print("Base de donnees :")
print("  - Table order_status_history (idempotent)")
print("  - Backfill : evenements initiaux pour commandes existantes")
print("  - Hook : chaque changement de statut enregistre")
print()
print("Backend :")
print("  - Route GET /api/orders/{ref}/timeline")
print()
print("Frontend :")
print("  - suivi.html + suivi.css + suivi.js (bleu, 2 blocs, timeline)")
print("  - professional_commandes.html (liste compacte bleue)")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print()
print("Puis teste sur iPhone :")
print("  /suivi?ref=CMD-XXXXXX")
print("  /professionnel/commandes")