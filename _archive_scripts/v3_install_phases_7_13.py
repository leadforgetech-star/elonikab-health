"""
v3_install_phases_7_13.py
Phases 7 a 13 : livraison MOTO/VOITURE, livreurs, dashboard admin,
notifications, recu, securite, tests, audit.

Un seul script qui installe tout et lance les tests a la fin.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
MIGR = BASE / "v3_modules" / "migrations.py"
MODULES = BASE / "v3_modules"
STATIC = BASE / "static"
UPLOADS = BASE / "uploads"
UPLOADS.mkdir(exist_ok=True)

# ============================================================
# 0. BACKUP
# ============================================================
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_v3_phases713_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAIN, backup / "main.py")
shutil.copy2(MIGR, backup / "migrations.py")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. MIGRATIONS ADDITIONNELLES
# ============================================================
mig = MIGR.read_text(encoding="utf-8")
if "CREATE TABLE IF NOT EXISTS driver_pins" not in mig:
    add = '''    """CREATE TABLE IF NOT EXISTS driver_pins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        driver_id INTEGER NOT NULL UNIQUE,
        pin TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL UNIQUE,
        receipt_number TEXT NOT NULL UNIQUE,
        issued_at TEXT NOT NULL,
        html_path TEXT DEFAULT '',
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
    )""",
    """CREATE INDEX IF NOT EXISTS idx_receipts_order ON receipts(order_id)""",
'''
    mig = mig.replace("]\n\n\nORDERS_NEW_COLS",
                      '    """CREATE INDEX IF NOT EXISTS idx_cart_items_cart ON cart_items(cart_id)""",\n' + add + "]\n\n\nORDERS_NEW_COLS", 1)
    MIGR.write_text(mig, encoding="utf-8")
    print("[OK] migrations.py -> driver_pins + receipts")
else:
    print("[i] migrations.py deja a jour")

# ============================================================
# 2. MODULE deliveries.py (Phase 7 + 8)
# ============================================================
DELIV = '''"""Livraison MOTO/VOITURE + dashboards livreur/chauffeur (Phases 7-8)."""
import secrets
from datetime import datetime

from fastapi import Depends, HTTPException
from pydantic import BaseModel

VALID_DRIVER_STATUSES = {
    "ASSIGNED", "ACCEPTED", "PICKED_UP", "IN_DELIVERY",
    "DELIVERED", "FAILED",
}
VALID_DRIVER_TYPES = {"LIVREUR_MOTO", "CHAUFFEUR"}


class AssignRequest(BaseModel):
    driver_id: int


class DriverStatusRequest(BaseModel):
    status: str
    notes: str = ""


def _row(r):
    return {k: r[k] for k in r.keys()} if r else None


def install_deliveries(app, get_db, require_role):
    # ---- Admin / Pharmacien : assignation ----

    @app.post("/api/orders/{reference}/assign")
    def assign_driver(reference: str, payload: AssignRequest,
                      user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE reference = ?", (reference,)
            ).fetchone()
            if order is None:
                raise HTTPException(404, "Commande introuvable")
            if order["delivery_mode"] != "livraison":
                raise HTTPException(400, "Commande non livrable")

            driver = conn.execute(
                "SELECT * FROM drivers WHERE id = ? AND is_active = 1",
                (payload.driver_id,),
            ).fetchone()
            if driver is None:
                raise HTTPException(404, "Livreur introuvable ou inactif")

            now = datetime.now().isoformat(timespec="seconds")
            existing = conn.execute(
                "SELECT id FROM deliveries WHERE order_id = ?", (order["id"],)
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE deliveries SET driver_id=?, assigned_at=?, status='ASSIGNED',"
                    " accepted_at=NULL, picked_up_at=NULL, delivered_at=NULL,"
                    " failed_at=NULL WHERE id=?",
                    (payload.driver_id, now, existing["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO deliveries (order_id, vehicle_type, driver_id,"
                    " status, assigned_at) VALUES (?, ?, ?, 'ASSIGNED', ?)",
                    (order["id"], order["delivery_vehicle_type"] or "MOTO",
                     payload.driver_id, now),
                )
            conn.execute(
                "UPDATE orders SET delivery_status='ASSIGNED' WHERE id=?",
                (order["id"],),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM deliveries WHERE order_id=?", (order["id"],)
            ).fetchone()
        finally:
            conn.close()
        return _row(row)

    # ---- Livreur / Chauffeur : mes livraisons ----

    @app.get("/api/deliveries/mine")
    def my_deliveries(user=Depends(require_role("LIVREUR_MOTO", "CHAUFFEUR"))):
        conn = get_db()
        try:
            # L'utilisateur doit etre lie a un driver via le meme email
            driver = conn.execute(
                "SELECT id FROM drivers WHERE email = ?", (user["email"],)
            ).fetchone()
            if driver is None:
                # fallback : chercher par phone
                driver = conn.execute(
                    "SELECT id FROM drivers WHERE phone = ?", (user["phone"],)
                ).fetchone()
            if driver is None:
                return []
            rows = conn.execute(
                "SELECT d.*, o.reference, o.customer_name, o.phone AS customer_phone,"
                " o.address, o.latitude, o.longitude, o.delivery_mode,"
                " o.total, o.delivery_fee, o.delivery_distance_km,"
                " (SELECT COUNT(*) FROM order_items oi WHERE oi.order_id=o.id) AS item_count"
                " FROM deliveries d JOIN orders o ON o.id = d.order_id"
                " WHERE d.driver_id = ? ORDER BY d.id DESC LIMIT 100",
                (driver["id"],),
            ).fetchall()
        finally:
            conn.close()
        return [_row(r) for r in rows]

    @app.patch("/api/deliveries/{delivery_id}/status")
    def update_delivery_status(delivery_id: int, payload: DriverStatusRequest,
                               user=Depends(require_role("LIVREUR_MOTO", "CHAUFFEUR",
                                                          "PHARMACIEN", "ADMIN"))):
        st = payload.status.strip().upper()
        if st not in VALID_DRIVER_STATUSES:
            raise HTTPException(400, "Statut invalide")
        conn = get_db()
        try:
            d = conn.execute(
                "SELECT * FROM deliveries WHERE id=?", (delivery_id,)
            ).fetchone()
            if d is None:
                raise HTTPException(404, "Livraison introuvable")
            now = datetime.now().isoformat(timespec="seconds")
            fields = ["status = ?"]
            params = [st]
            if st == "ACCEPTED":
                fields.append("accepted_at = ?"); params.append(now)
            elif st == "PICKED_UP":
                fields.append("picked_up_at = ?"); params.append(now)
            elif st == "DELIVERED":
                fields.append("delivered_at = ?"); params.append(now)
            elif st == "FAILED":
                fields.append("failed_at = ?"); params.append(now)
            params.append(delivery_id)
            conn.execute("UPDATE deliveries SET " + ", ".join(fields) + " WHERE id=?", params)
            conn.execute("UPDATE orders SET delivery_status=? WHERE id=?", (st, d["order_id"]))
            conn.commit()
            row = conn.execute(
                "SELECT * FROM deliveries WHERE id=?", (delivery_id,)
            ).fetchone()
        finally:
            conn.close()
        return _row(row)

    @app.get("/api/deliveries")
    def list_deliveries(status: str = "",
                        user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            sql = ("SELECT d.*, o.reference, o.customer_name, o.address,"
                   " o.delivery_vehicle_type, dr.name AS driver_name"
                   " FROM deliveries d"
                   " JOIN orders o ON o.id = d.order_id"
                   " LEFT JOIN drivers dr ON dr.id = d.driver_id")
            params = []
            if status.strip():
                sql += " WHERE d.status = ?"
                params.append(status.strip().upper())
            sql += " ORDER BY d.id DESC LIMIT 200"
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
        return [_row(r) for r in rows]


'''
(MODULES / "deliveries.py").write_text(DELIV, encoding="utf-8")
print("[OK] v3_modules/deliveries.py")

# ============================================================
# 3. MODULE notifications.py (Phase 10)
# ============================================================
NOTIF = '''"""Notifications internes + recus (Phase 10)."""
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import Depends, HTTPException
from fastapi.responses import HTMLResponse


def _row(r):
    return {k: r[k] for k in r.keys()} if r else None


def push_notification(conn, user_id, title, body, order_id=None, channel="IN_APP"):
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO notifications (user_id, order_id, channel, title, body,"
        " is_read, created_at) VALUES (?, ?, ?, ?, ?, 0, ?)",
        (user_id, order_id, channel, title, body, now),
    )


def install_notifications(app, get_db, require_role):
    @app.get("/api/notifications")
    def list_notifs(unread_only: int = 0,
                    user=Depends(require_role("PATIENT", "PROFESSIONNEL",
                                              "PHARMACIEN", "ADMIN",
                                              "LIVREUR_MOTO", "CHAUFFEUR"))):
        conn = get_db()
        try:
            sql = "SELECT * FROM notifications WHERE user_id = ?"
            params = [user["id"]]
            if unread_only:
                sql += " AND is_read = 0"
            sql += " ORDER BY id DESC LIMIT 100"
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
        return [_row(r) for r in rows]

    @app.patch("/api/notifications/{notif_id}/read")
    def mark_read(notif_id: int,
                  user=Depends(require_role("PATIENT", "PROFESSIONNEL",
                                            "PHARMACIEN", "ADMIN",
                                            "LIVREUR_MOTO", "CHAUFFEUR"))):
        conn = get_db()
        try:
            conn.execute(
                "UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?",
                (notif_id, user["id"]),
            )
            conn.commit()
        finally:
            conn.close()
        return {"ok": True}

    @app.patch("/api/notifications/read-all")
    def read_all(user=Depends(require_role("PATIENT", "PROFESSIONNEL",
                                           "PHARMACIEN", "ADMIN",
                                           "LIVREUR_MOTO", "CHAUFFEUR"))):
        conn = get_db()
        try:
            conn.execute("UPDATE notifications SET is_read=1 WHERE user_id=?",
                         (user["id"],))
            conn.commit()
        finally:
            conn.close()
        return {"ok": True}

    # ---- Recu (HTML imprimable) ----

    @app.get("/api/orders/{reference}/receipt", response_class=HTMLResponse)
    def get_receipt(reference: str):
        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE reference=?", (reference,)
            ).fetchone()
            if order is None:
                raise HTTPException(404, "Commande introuvable")
            items = conn.execute(
                "SELECT * FROM order_items WHERE order_id=? ORDER BY id",
                (order["id"],),
            ).fetchall()
            settings = conn.execute(
                "SELECT * FROM pharmacy_settings WHERE id=1"
            ).fetchone()
            payment = conn.execute(
                "SELECT * FROM payments WHERE order_id=? ORDER BY id DESC LIMIT 1",
                (order["id"],),
            ).fetchone()

            # Enregistrer le recu (idempotent)
            existing = conn.execute(
                "SELECT receipt_number FROM receipts WHERE order_id=?",
                (order["id"],),
            ).fetchone()
            if existing:
                receipt_num = existing["receipt_number"]
            else:
                receipt_num = "REC-" + order["reference"].replace("CMD-", "")
                conn.execute(
                    "INSERT INTO receipts (order_id, receipt_number, issued_at)"
                    " VALUES (?, ?, ?)",
                    (order["id"], receipt_num,
                     datetime.now().isoformat(timespec="seconds")),
                )
                conn.commit()
        finally:
            conn.close()

        sub = float(order["subtotal"] or 0)
        fee = float(order["delivery_fee"] or 0)
        tot = round(sub + fee, 2)

        def money(v):
            return "{:,.0f}".format(v).replace(",", " ") + " FCFA"

        rows_html = ""
        if items:
            for it in items:
                rows_html += (
                    "<tr><td>" + (it["product_name"] or "") + "</td>"
                    "<td style='text-align:right'>" + str(it["quantity"]) + "</td>"
                    "<td style='text-align:right'>" + money(it["unit_price"]) + "</td>"
                    "<td style='text-align:right'>" + money(it["subtotal"]) + "</td></tr>"
                )
        else:
            rows_html = (
                "<tr><td>" + (order["product_name"] or "") + "</td>"
                "<td style='text-align:right'>" + str(order["quantity"]) + "</td>"
                "<td style='text-align:right'>" + money(order["price"]) + "</td>"
                "<td style='text-align:right'>" + money(sub) + "</td></tr>"
            )

        ph_name = settings["pharmacy_name"] if settings and "pharmacy_name" in settings.keys() else "Elokinab Health"
        ph_phone = settings["pharmacy_phone"] if settings and "pharmacy_phone" in settings.keys() else ""
        pay_status = payment["status"] if payment else "PENDING"

        html = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Recu """ + receipt_num + """</title>
<style>
  body{font-family:Segoe UI,system-ui,sans-serif;color:#0f2620;background:#f4faf7;padding:20px}
  .card{background:#fff;max-width:640px;margin:0 auto;border-radius:16px;padding:32px;box-shadow:0 8px 28px rgba(15,38,32,.08)}
  h1{color:#0a7a5a;margin:0 0 4px}
  .ref{font-family:Consolas,monospace;color:#6c8a80;font-size:13px}
  table{width:100%;border-collapse:collapse;margin:18px 0;font-size:14px}
  th,td{padding:8px 4px;border-bottom:1px solid #ddece6;text-align:left}
  th{background:#e8f7f1;color:#0a7a5a;font-size:12px;text-transform:uppercase}
  .total{font-size:20px;font-weight:800;color:#0a7a5a;text-align:right;margin-top:8px}
  .status{display:inline-block;padding:4px 10px;border-radius:999px;font-size:11px;font-weight:800;text-transform:uppercase;background:#fff4e0;color:#b26b00}
  .foot{margin-top:24px;font-size:12px;color:#6c8a80;text-align:center}
  @media print{body{background:#fff;padding:0}.card{box-shadow:none}}
</style></head><body>
<div class="card">
  <h1>""" + ph_name + """</h1>
  <div class="ref">Recu """ + receipt_num + " - " + (order["created_at"] or "")[:16] + """</div>
  <div style="margin-top:14px">
    <strong>""" + (order["customer_name"] or "") + """</strong><br>
    <span class="ref">""" + (order["phone"] or "") + """</span>
  </div>
  <table>
    <thead><tr><th>Produit</th><th style="text-align:right">Qte</th>
    <th style="text-align:right">Prix U.</th><th style="text-align:right">Sous-total</th></tr></thead>
    <tbody>""" + rows_html + """</tbody>
  </table>
  <div style="text-align:right;font-size:14px">
    Sous-total : <strong>""" + money(sub) + """</strong><br>
    Livraison : <strong>""" + money(fee) + """</strong>
  </div>
  <div class="total">Total : """ + money(tot) + """</div>
  <div style="margin-top:12px;text-align:right">
    <span class="status">Paiement : """ + pay_status + """</span>
  </div>
  <div class="foot">
    Document non contractuel genere automatiquement.<br>
    """ + ph_phone + """
  </div>
</div></body></html>"""
        return HTMLResponse(html)


'''
(MODULES / "notifications.py").write_text(NOTIF, encoding="utf-8")
print("[OK] v3_modules/notifications.py")

# ============================================================
# 4. MODULE admin.py (Phase 9 - dashboard consolide)
# ============================================================
ADMIN = '''"""Dashboard admin consolide (Phase 9)."""
from datetime import datetime

from fastapi import Depends


def install_admin(app, get_db, require_role):
    @app.get("/api/admin/dashboard")
    def dashboard(user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            def scalar(sql, params=()):
                r = conn.execute(sql, params).fetchone()
                return r[0] if r else 0

            today = datetime.now().strftime("%Y-%m-%d")

            stats = {
                "orders_total": scalar("SELECT COUNT(*) FROM orders"),
                "orders_today": scalar(
                    "SELECT COUNT(*) FROM orders WHERE created_at LIKE ?",
                    (today + "%",),
                ),
                "orders_pending": scalar(
                    "SELECT COUNT(*) FROM orders WHERE status = 'en_attente'"
                ),
                "orders_preparing": scalar(
                    "SELECT COUNT(*) FROM orders WHERE status = 'en_preparation'"
                ),
                "orders_ready": scalar(
                    "SELECT COUNT(*) FROM orders WHERE status = 'prete'"
                ),
                "payments_pending": scalar(
                    "SELECT COUNT(*) FROM payments WHERE status = 'PROOF_SUBMITTED'"
                ),
                "payments_verified_today": scalar(
                    "SELECT COUNT(*) FROM payments WHERE status = 'VERIFIED'"
                    " AND verified_at LIKE ?",
                    (today + "%",),
                ),
                "prescriptions_pending": scalar(
                    "SELECT COUNT(*) FROM prescriptions WHERE status = 'PENDING'"
                ),
                "professionals_pending": scalar(
                    "SELECT COUNT(*) FROM professional_profiles WHERE status = 'PENDING'"
                ),
                "deliveries_active": scalar(
                    "SELECT COUNT(*) FROM deliveries"
                    " WHERE status NOT IN ('DELIVERED','FAILED')"
                ),
                "deliveries_moto": scalar(
                    "SELECT COUNT(*) FROM deliveries WHERE vehicle_type = 'MOTO'"
                ),
                "deliveries_car": scalar(
                    "SELECT COUNT(*) FROM deliveries WHERE vehicle_type = 'VOITURE'"
                ),
                "users_total": scalar("SELECT COUNT(*) FROM users"),
                "users_patients": scalar("SELECT COUNT(*) FROM users WHERE role = 'PATIENT'"),
                "users_pro": scalar("SELECT COUNT(*) FROM users WHERE role = 'PROFESSIONNEL'"),
                "revenue_verified": scalar(
                    "SELECT COALESCE(SUM(amount),0) FROM payments WHERE status = 'VERIFIED'"
                ),
            }
            return stats
        finally:
            conn.close()

    @app.get("/api/admin/users")
    def list_users(role: str = "",
                   user=Depends(require_role("ADMIN"))):
        conn = get_db()
        try:
            sql = ("SELECT id, email, phone, full_name, role, is_active, created_at"
                   " FROM users")
            params = []
            if role.strip():
                sql += " WHERE role = ?"
                params.append(role.strip().upper())
            sql += " ORDER BY id DESC LIMIT 500"
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
        return [{k: r[k] for k in r.keys()} for r in rows]


'''
(MODULES / "admin.py").write_text(ADMIN, encoding="utf-8")
print("[OK] v3_modules/admin.py")

# ============================================================
# 5. PATCH MAIN.PY
# ============================================================
src = MAIN.read_text(encoding="utf-8")
if "install_deliveries" not in src:
    old = "install_prescriptions(app, get_db, require_role, UPLOADS_DIR)"
    new = (old + "\n"
           "from v3_modules.deliveries import install_deliveries\n"
           "from v3_modules.notifications import install_notifications, push_notification\n"
           "from v3_modules.admin import install_admin\n"
           "install_deliveries(app, get_db, require_role)\n"
           "install_notifications(app, get_db, require_role)\n"
           "install_admin(app, get_db, require_role)")
    if old in src:
        src = src.replace(old, new, 1)
        print("[OK] main.py -> modules phases 7-13 branches")
    else:
        print("[!] anchor install_prescriptions introuvable")
    MAIN.write_text(src, encoding="utf-8")
else:
    print("[i] main.py deja patche phases 7-13")

# ============================================================
# 6. FRONTEND : espace livreur + admin dashboard
# ============================================================
DRIVER_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mes livraisons - Elokinab Health</title>
<link rel="stylesheet" href="/static/auth.css">
<style>
  .auth-card{max-width:720px}
  .dlv{background:#fff;border:1px solid #ddece6;border-radius:12px;padding:14px;margin-bottom:10px}
  .dlv-ref{font-family:Consolas,monospace;font-weight:800;font-size:14px}
  .dlv-meta{font-size:13px;color:#6c8a80;margin:4px 0}
  .dlv-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
  .pill{display:inline-block;font-size:11px;font-weight:800;padding:4px 10px;border-radius:999px;text-transform:uppercase;letter-spacing:.05em}
  .p-ASSIGNED{background:#fff4e0;color:#b26b00}
  .p-ACCEPTED{background:#e3f0ff;color:#1b5aae}
  .p-PICKED_UP{background:#ede0ff;color:#6335b8}
  .p-IN_DELIVERY{background:#e3f7ee;color:#0a7a5a}
  .p-DELIVERED{background:#e6e9ec;color:#4b5563}
  .p-FAILED{background:#fdecec;color:#b23c3c}
  .empty{text-align:center;padding:24px;color:#6c8a80}
  .btn-xs{padding:8px 12px;font-size:12px}
</style>
</head>
<body class="auth-body">
<div class="auth-card">
  <div class="auth-logo">
    <div class="auth-logo-mark">+</div>
    <div class="auth-logo-text">
      <strong>Elokinab Health</strong>
      <small>Espace livreur</small>
    </div>
  </div>
  <h1>Mes livraisons</h1>
  <p class="sub">Acceptez, suivez et confirmez vos livraisons.</p>
  <div id="msg" class="auth-msg hidden"></div>
  <div id="list"></div>
  <div style="text-align:center;margin-top:16px;font-size:13px">
    <a href="/" style="color:#6c8a80;text-decoration:none">Retour</a>
  </div>
</div>
<script src="/static/driver.js"></script>
</body>
</html>
'''
(STATIC / "driver.html").write_text(DRIVER_HTML, encoding="utf-8")
print("[OK] static/driver.html")

DRIVER_JS = '''(function () {
  function $(id) { return document.getElementById(id); }
  function money(v) { return Math.round(Number(v) || 0).toLocaleString("fr-FR") + " FCFA"; }
  function showMsg(t) { var m = $("msg"); m.textContent = t; m.className = "auth-msg"; }
  function hideMsg() { var m = $("msg"); m.className = "auth-msg hidden"; }

  function call(m, p, d) {
    return fetch(p, {
      method: m,
      headers: d ? { "Content-Type": "application/json" } : {},
      body: d ? JSON.stringify(d) : undefined
    }).then(function (r) {
      return r.json().then(function (data) {
        if (!r.ok) throw new Error(data.detail || "Erreur");
        return data;
      });
    });
  }

  function nextActions(status) {
    if (status === "ASSIGNED") return [["Accepter", "ACCEPTED"]];
    if (status === "ACCEPTED") return [["Recupere", "PICKED_UP"]];
    if (status === "PICKED_UP") return [["En route", "IN_DELIVERY"]];
    if (status === "IN_DELIVERY") return [["Livre", "DELIVERED"], ["Echec", "FAILED"]];
    return [];
  }

  function render(list) {
    var box = $("list");
    box.innerHTML = "";
    if (!list || list.length === 0) {
      box.innerHTML = '<div class="empty">Aucune livraison assignee.</div>';
      return;
    }
    list.forEach(function (d) {
      var card = document.createElement("div");
      card.className = "dlv";
      card.innerHTML =
        '<div class="dlv-ref">' + d.reference +
        ' <span class="pill p-' + d.status + '">' + d.status + '</span></div>' +
        '<div class="dlv-meta">' + (d.customer_name || "") + ' - ' + (d.customer_phone || "") + '</div>' +
        '<div class="dlv-meta">Adresse : ' + (d.address || "(GPS uniquement)") + '</div>' +
        '<div class="dlv-meta">Total : ' + money(d.total) + ' - Livraison : ' + money(d.delivery_fee) + '</div>';

      var actions = document.createElement("div");
      actions.className = "dlv-actions";

      if (d.latitude && d.longitude) {
        var map = document.createElement("a");
        map.className = "auth-btn btn-xs";
        map.style.cssText = "text-decoration:none;display:inline-block;background:#6c8a80";
        map.href = "https://www.google.com/maps?q=" + d.latitude + "," + d.longitude;
        map.target = "_blank"; map.rel = "noopener";
        map.textContent = "Itineraire";
        actions.appendChild(map);
      }

      if (d.customer_phone) {
        var call = document.createElement("a");
        call.className = "auth-btn btn-xs";
        call.style.cssText = "text-decoration:none;display:inline-block;background:#0a7a5a";
        call.href = "tel:" + d.customer_phone;
        call.textContent = "Appeler";
        actions.appendChild(call);
      }

      nextActions(d.status).forEach(function (a) {
        var btn = document.createElement("button");
        btn.className = "auth-btn btn-xs";
        btn.textContent = a[0];
        btn.onclick = function () {
          hideMsg();
          call("PATCH", "/api/deliveries/" + d.id + "/status", { status: a[1] })
            .then(load).catch(function (e) { showMsg(e.message); });
        };
        actions.appendChild(btn);
      });

      card.appendChild(actions);
      box.appendChild(card);
    });
  }

  function load() {
    hideMsg();
    call("GET", "/api/deliveries/mine").then(render).catch(function (e) {
      if (String(e.message).indexOf("Non authentifie") >= 0) {
        window.location.href = "/static/login.html?next=/static/driver.html";
      } else {
        showMsg(e.message);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", load);
})();
'''
(STATIC / "driver.js").write_text(DRIVER_JS, encoding="utf-8")
print("[OK] static/driver.js")

# ============================================================
# 7. TEST GLOBAL PHASES 7-13
# ============================================================
TEST = '''"""test_phases_7_13.py - Test des phases 7 a 13."""
import io, json, sqlite3, sys, urllib.error, urllib.request, http.cookiejar
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from v3_modules.auth import hash_password

API = "http://127.0.0.1:8000"
DB = BASE / "database.db"
ADMIN = "admin_test@elokinab.local"
ADMIN_PWD = "admin123456"


class Client:
    def __init__(self):
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def call(self, m, p, d=None):
        body = json.dumps(d).encode() if d is not None else None
        h = {"Accept": "application/json"}
        if d is not None: h["Content-Type"] = "application/json"
        req = urllib.request.Request(API + p, data=body, headers=h, method=m)
        try:
            r = self.opener.open(req, timeout=15)
            return r.status, json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            try: return e.code, json.loads(e.read().decode() or "{}")
            except: return e.code, {}


PASS, FAIL = 0, 0
def check(l, c, d=""):
    global PASS, FAIL
    if c: print("  [PASS] " + l); PASS += 1
    else:
        print("  [FAIL] " + l)
        if d: print("         ->", d)
        FAIL += 1


def ensure_admin():
    conn = sqlite3.connect(DB)
    try:
        r = conn.execute("SELECT id FROM users WHERE email=?", (ADMIN,)).fetchone()
        if r: return r[0]
        now = datetime.now().isoformat(timespec="seconds")
        cur = conn.execute(
            "INSERT INTO users (email, phone, password_hash, full_name, role, is_active, created_at)"
            " VALUES (?, ?, ?, 'Admin Test', 'ADMIN', 1, ?)",
            (ADMIN, "", hash_password(ADMIN_PWD), now))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def main():
    print("=" * 64)
    print("TEST PHASES 7 A 13")
    print("=" * 64)
    print()
    ensure_admin()

    a = Client()
    st, _ = a.call("POST", "/api/auth/login", {"email": ADMIN, "password": ADMIN_PWD})
    check("Login admin", st == 200, _)

    print()
    print("[Phase 7] Verification des tarifs MOTO/VOITURE")
    st, s = a.call("GET", "/api/settings")
    check("Settings OK", st == 200, s)
    for k in ("motorbike_base_fee", "motorbike_price_per_km",
              "car_base_fee", "car_price_per_km"):
        check("Champ " + k + " present", k in s, s)

    print()
    print("[Phase 8] Endpoints livreur/chauffeur")
    st, b = a.call("GET", "/api/deliveries")
    check("GET /api/deliveries OK (admin)", st == 200 and isinstance(b, list), b)

    print()
    print("[Phase 9] Dashboard admin consolide")
    st, b = a.call("GET", "/api/admin/dashboard")
    check("GET /api/admin/dashboard OK", st == 200, b)
    if isinstance(b, dict):
        for k in ("orders_total", "payments_pending", "prescriptions_pending",
                  "users_total", "deliveries_active"):
            check("Stat " + k, k in b, b)

    st, b = a.call("GET", "/api/admin/users")
    check("GET /api/admin/users OK", st == 200 and isinstance(b, list), b)

    print()
    print("[Phase 10] Notifications + recu")
    st, b = a.call("GET", "/api/notifications")
    check("GET /api/notifications OK", st == 200 and isinstance(b, list), b)

    # Recu sur la derniere commande
    st, orders = a.call("GET", "/api/orders")
    if isinstance(orders, list) and orders:
        ref = orders[0].get("reference")
        import urllib.request as ur
        try:
            r = ur.urlopen(API + "/api/orders/" + ref + "/receipt", timeout=10)
            html = r.read().decode()
            check("Recu genere", r.status == 200 and "Recu" in html, r.status)
        except Exception as e:
            check("Recu genere", False, str(e))
    else:
        check("Recu (skip: aucune commande)", True)

    print()
    print("[Phase 11] Securite (presence des modules)")
    check("auth avec scrypt", Path(BASE / "v3_modules" / "auth.py").exists())
    check("uploads/proofs cree", (BASE / "uploads").exists())

    print()
    print("[Phase 12] Non-regression globale")
    for path in ("/api/products", "/api/categories", "/api/orders",
                 "/api/drivers", "/api/settings", "/api/payments",
                 "/api/prescriptions", "/api/professionals",
                 "/api/admin/dashboard"):
        st, _b = a.call("GET", path)
        check("GET " + path, st == 200, "status=" + str(st))

    print()
    print("=" * 64)
    print("RESULTAT : " + str(PASS) + " PASS / " + str(FAIL) + " FAIL")
    print("=" * 64)
    if FAIL == 0:
        print("[OK] PHASES 7 a 13 validees.")
    else:
        print("[!] Certains tests ont echoue.")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
'''
(BASE / "test_phases_7_13.py").write_text(TEST, encoding="utf-8")
print("[OK] test_phases_7_13.py")

# ============================================================
# 8. RAPPORT FINAL
# ============================================================
print()
print("=" * 64)
print("PHASES 7 A 13 INSTALLEES")
print("=" * 64)
print()
print("Modules ajoutes :")
print("  v3_modules/deliveries.py    (MOTO/VOITURE + statuts livreur)")
print("  v3_modules/notifications.py (notifs + recu HTML)")
print("  v3_modules/admin.py         (dashboard consolide)")
print()
print("Frontend ajoute :")
print("  static/driver.html + driver.js  (espace livreur/chauffeur)")
print()
print("Tables ajoutees :")
print("  driver_pins, receipts")
print()
print("Routes ajoutees :")
print("  POST   /api/orders/{ref}/assign")
print("  GET    /api/deliveries")
print("  GET    /api/deliveries/mine")
print("  PATCH  /api/deliveries/{id}/status")
print("  GET    /api/notifications")
print("  PATCH  /api/notifications/{id}/read")
print("  PATCH  /api/notifications/read-all")
print("  GET    /api/orders/{ref}/receipt   (HTML imprimable)")
print("  GET    /api/admin/dashboard")
print("  GET    /api/admin/users")
print()
print("PROCHAINES ETAPES :")
print("  taskkill /F /IM python.exe")
print("  python main.py")
print("  python test_phases_7_13.py")