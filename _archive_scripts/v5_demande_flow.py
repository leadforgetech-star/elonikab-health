"""
v5_demande_flow.py
Refonte du flux demande B2B :
- Page /professionnel/demande : gateway si vide, review si items
- Page /professionnel/demande/confirmer : mode + adresse + notes + submit
- Backend : GET /api/pro/requests/{ref}/summary + submit étendu
"""
from pathlib import Path
import datetime
import shutil
import re

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
MAIN = BASE / "main.py"
B2B = BASE / "v3_modules" / "b2b_requests.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_v5_flow_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAIN, backup / "main.py")
shutil.copy2(B2B, backup / "b2b_requests.py")
for f in ("professional_demande.html", "professional_demande.js"):
    p = STATIC / f
    if p.exists():
        shutil.copy2(p, backup / f)
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. BACKEND : ajouter GET summary + étendre submit
# ============================================================
src = B2B.read_text(encoding="utf-8")

# 1.1 Ajouter le modèle SubmitRequestPayload
if "class SubmitRequestPayload" not in src:
    src = src.replace(
        "class RequestItemUpdate(BaseModel):",
        '''class SubmitRequestPayload(BaseModel):
    delivery_mode: str = "retrait"  # retrait | livraison
    address: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_accuracy: Optional[float] = None
    notes: str = ""


class RequestItemUpdate(BaseModel):''',
        1,
    )
    print("[OK] b2b_requests.py -> SubmitRequestPayload ajoute")

# 1.2 Ajouter l'endpoint summary AVANT le bloc submit
summary_ep = '''

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


'''
if "/summary" not in src:
    # Inserer avant la route submit
    anchor = "    @app.post(\"/api/pro/requests/{reference}/submit\")"
    if anchor in src:
        src = src.replace(anchor, summary_ep + anchor, 1)
        print("[OK] b2b_requests.py -> endpoint /summary ajoute")

# 1.3 Remplacer la fonction submit par une version étendue
old_submit = re.compile(
    r'    @app\.post\("/api/pro/requests/\{reference\}/submit"\).*?(?=\n    #|\n\nclass |\ndef |\Z)',
    re.DOTALL
)
new_submit = '''    @app.post("/api/pro/requests/{reference}/submit")
    def submit_request(reference: str, payload: SubmitRequestPayload = None,
                       user=Depends(require_role("PROFESSIONNEL"))):
        if payload is None:
            payload = SubmitRequestPayload()
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
                raise HTTPException(400, "Ajoutez au moins un produit ou une piece jointe")

            mode = (payload.delivery_mode or "retrait").strip().lower()
            if mode not in ("retrait", "livraison"):
                raise HTTPException(400, "Mode de livraison invalide")
            if mode == "livraison" and not payload.address.strip() and payload.latitude is None:
                raise HTTPException(400, "Adresse ou GPS obligatoire pour la livraison")

            # Construire un resume stockable dans source_summary (JSON simple)
            import json as _json
            summary = {
                "delivery_mode": mode,
                "address": payload.address.strip(),
                "latitude": payload.latitude,
                "longitude": payload.longitude,
                "location_accuracy": payload.location_accuracy,
            }

            conn.execute(
                "UPDATE requests SET status='SUBMITTED', notes=?, source_summary=?, updated_at=?"
                " WHERE id=?",
                (payload.notes.strip(), _json.dumps(summary), _now(), req["id"]),
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

'''
if old_submit.search(src):
    src = old_submit.sub(new_submit, src, count=1)
    print("[OK] b2b_requests.py -> submit etendu")

B2B.write_text(src, encoding="utf-8")

# ============================================================
# 2. ROUTES main.py
# ============================================================
mainsrc = MAIN.read_text(encoding="utf-8")
if '"/professionnel/demande/confirmer"' not in mainsrc:
    route = '''

@app.get("/professionnel/demande/confirmer", include_in_schema=False)
def page_pro_demande_confirmer():
    return FileResponse(STATIC_DIR / "professional_demande_confirmer.html")

'''
    anchor = "\ninit_db()\n"
    if anchor in mainsrc:
        mainsrc = mainsrc.replace(anchor, route + anchor, 1)
        MAIN.write_text(mainsrc, encoding="utf-8")
        print("[OK] main.py -> route /professionnel/demande/confirmer")

# ============================================================
# 3. STYLES COMMUNS + HEADERS (utilises dans les 2 pages)
# ============================================================
COMMON_CSS = '''/* Elokinab Health - Pro pages communes */
:root{
  --blue:#1a4a7f;--blue-dark:#123258;--blue-soft:#eaf1f9;
  --wa:#25d366;--wa-dark:#1da851;
  --ink:#0f172a;--muted:#64748b;--line:#e6ebf1;--bg:#f7fafc;
  --radius:14px;
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

.pg-header{
  background:#fff;border-bottom:1px solid var(--line);
  position:sticky;top:0;z-index:50;
}
.pg-header-inner{
  max-width:900px;margin:0 auto;padding:12px 16px;
  display:flex;align-items:center;gap:12px;
}
.pg-back{
  width:36px;height:36px;border-radius:10px;border:1px solid var(--line);
  background:#fff;color:var(--ink);font-size:18px;
  display:flex;align-items:center;justify-content:center;text-decoration:none;
}
.pg-title{font-size:15px;font-weight:800;flex:1}
.pg-ref{margin-left:auto;font-family:Consolas,monospace;font-size:11px;color:var(--muted)}

.pg-main{max-width:900px;margin:0 auto;padding:18px 16px 40px}

.pg-section-title{
  font-size:11px;text-transform:uppercase;letter-spacing:.08em;
  color:var(--muted);font-weight:800;
  margin:22px 0 10px;display:flex;align-items:center;gap:8px;
}
.pg-count{
  background:var(--blue);color:#fff;
  font-size:10px;font-weight:800;
  padding:2px 8px;border-radius:999px;
}

/* Items dans la demande */
.it-row{
  display:flex;align-items:flex-start;gap:12px;
  padding:14px;background:#fff;
  border:1px solid var(--line);border-radius:12px;
  margin-bottom:8px;
}
.it-body{flex:1;min-width:0}
.it-name{
  font-size:14px;font-weight:700;margin:0 0 3px;
  word-break:break-word;line-height:1.35;
}
.it-qty{
  font-size:12px;color:var(--muted);
  font-family:Consolas,monospace;
}
.it-price{
  font-size:14px;font-weight:800;color:var(--ink);
  white-space:nowrap;flex-shrink:0;
  font-family:Consolas,monospace;
  text-align:right;
}
.it-price small{
  display:block;font-size:11px;
  color:var(--muted);font-weight:600;
}
.it-del{
  width:30px;height:30px;border:0;border-radius:8px;
  background:transparent;color:var(--muted);font-size:16px;
  display:flex;align-items:center;justify-content:center;
  flex-shrink:0;cursor:pointer;transition:.15s;
}
.it-del:hover{background:#fee2e2;color:#dc2626}

/* Totaux */
.totals-card{
  background:#fff;border:1px solid var(--line);border-radius:14px;
  padding:16px;margin-top:12px;
}
.totals-line{
  display:flex;justify-content:space-between;align-items:center;
  padding:8px 0;font-size:14px;
}
.totals-line .lbl{color:var(--muted)}
.totals-line .val{
  font-weight:700;font-family:Consolas,monospace;color:var(--ink);
}
.totals-line.total{
  border-top:1px solid var(--line);
  margin-top:6px;padding-top:14px;
  font-size:16px;font-weight:800;
}
.totals-line.total .val{color:var(--blue-dark);font-size:18px}
.totals-line .val.confirm{color:var(--muted);font-weight:600;font-size:13px}

/* Notes */
.notes-block{margin-top:18px}
.notes-block label{
  font-size:12px;font-weight:800;color:var(--muted);
  text-transform:uppercase;letter-spacing:.06em;
  display:block;margin-bottom:6px;
}
.notes{
  width:100%;padding:12px 14px;
  border:1px solid var(--line);border-radius:12px;
  font-family:inherit;font-size:14px;background:#fff;
  outline:none;resize:vertical;min-height:64px;
  color:var(--ink);
}
.notes:focus{border-color:var(--blue)}

/* Boutons */
.btn{
  display:flex;align-items:center;justify-content:center;gap:8px;
  padding:15px;border:0;border-radius:13px;
  font-weight:800;font-size:15px;
  transition:.15s;text-decoration:none;cursor:pointer;
  width:100%;
}
.btn-primary{background:var(--blue);color:#fff}
.btn-primary:hover:not(:disabled){background:var(--blue-dark);transform:translateY(-1px)}
.btn-primary:disabled{background:#c7d5e3;cursor:not-allowed;color:#fff}
.btn-ghost{
  background:#fff;color:var(--ink);
  border:1px solid var(--line);
}
.btn-ghost:hover{border-color:var(--blue);color:var(--blue)}
.btn-danger{
  background:#fff;color:#dc2626;
  border:1px solid #fee2e2;
}
.btn-danger:hover{background:#fee2e2}

.pg-actions{
  margin-top:20px;padding-top:18px;
  border-top:1px solid var(--line);
  display:flex;flex-direction:column;gap:10px;
}

.pg-info{
  background:var(--blue-soft);border:1px solid #cddff0;
  border-radius:12px;padding:12px 14px;
  font-size:12.5px;color:var(--blue-dark);
  margin-top:14px;line-height:1.5;
}
.pg-info strong{font-weight:800}

/* Gateway cards */
.gw-hero{margin:0 0 24px;text-align:center}
.gw-hero h1{
  font-size:23px;font-weight:800;line-height:1.2;
  letter-spacing:-.02em;margin:0 0 8px;
}
.gw-hero p{font-size:14px;color:var(--muted);margin:0}

.gw-cards{display:flex;flex-direction:column;gap:14px;margin:24px 0}
.gw-card{
  display:block;background:#fff;
  border:1px solid var(--line);border-radius:18px;
  padding:20px;cursor:pointer;
  transition:all .18s;text-decoration:none;color:inherit;
  position:relative;
}
.gw-card:hover{
  border-color:var(--blue);transform:translateY(-2px);
  box-shadow:0 10px 28px rgba(26,74,127,.10);
}
.gw-card-icon{
  width:50px;height:50px;border-radius:14px;
  display:flex;align-items:center;justify-content:center;
  font-size:22px;margin-bottom:14px;
}
.gw-card.cat .gw-card-icon{background:var(--blue-soft);color:var(--blue)}
.gw-card.wa .gw-card-icon{background:#e6f9ee;color:var(--wa)}
.gw-card-title{
  font-size:16px;font-weight:800;letter-spacing:-.01em;
  margin:0 0 5px;line-height:1.25;
}
.gw-card-desc{font-size:13px;color:var(--muted);line-height:1.5;margin:0 0 14px}
.gw-card-foot{
  display:flex;align-items:center;justify-content:space-between;
  padding-top:12px;border-top:1px solid var(--line);
}
.gw-card-cta{font-size:13.5px;font-weight:800}
.gw-card.cat .gw-card-cta{color:var(--blue)}
.gw-card.wa .gw-card-cta{color:var(--wa-dark)}
.gw-card-arrow{font-size:18px;line-height:1;transition:transform .18s}
.gw-card:hover .gw-card-arrow{transform:translateX(4px)}
.gw-or{
  display:flex;align-items:center;gap:14px;margin:2px 0;
  color:var(--muted);font-size:12px;font-weight:800;
  text-transform:uppercase;letter-spacing:.15em;
}
.gw-or::before,.gw-or::after{content:"";flex:1;height:1px;background:var(--line)}

/* Navbar */
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
.pro-navbar .central .nav-count{
  position:absolute;top:-4px;right:-4px;
  min-width:22px;height:22px;padding:0 6px;
  background:#fff;color:var(--blue-dark);
  border:2px solid var(--blue);
  border-radius:999px;font-size:11px;font-weight:900;
  display:flex;align-items:center;justify-content:center;
}
.pro-navbar .central .nav-count.hidden{display:none}
.pro-navbar .central.active{background:var(--blue-dark)}

/* Toast */
.pg-toast{
  position:fixed;left:50%;bottom:100px;transform:translateX(-50%);
  background:#0f172a;color:#fff;padding:12px 18px;border-radius:12px;
  font-size:13px;font-weight:600;z-index:1000;
  box-shadow:0 10px 30px rgba(0,0,0,.2);
  max-width:calc(100vw - 32px);text-align:center;
}
'''

(STATIC / "professional_common.css").write_text(COMMON_CSS, encoding="utf-8")
print("[OK] professional_common.css")

# ============================================================
# 4. PAGE DEMANDE (review ou gateway)
# ============================================================
DEM_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Ma demande - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<link rel="stylesheet" href="/static/professional_common.css">
</head>
<body>

<header class="pg-header">
  <div class="pg-header-inner">
    <a class="pg-back" href="/professionnel" aria-label="Retour">&#8592;</a>
    <span class="pg-title" id="page-title">Ma demande</span>
    <span class="pg-ref" id="page-ref">—</span>
  </div>
</header>

<main class="pg-main" id="main">
  <div style="text-align:center;padding:40px;color:#64748b">Chargement...</div>
</main>

<nav class="pro-navbar">
  <a href="/professionnel"><span class="ico">&#127968;</span> Accueil</a>
  <a href="/professionnel/catalogue"><span class="ico">&#128722;</span> Catalogue</a>
  <a href="/professionnel/demande" class="central active" id="nav-central">
    <span>+</span><span class="lbl">Demande</span>
    <span class="nav-count hidden" id="nav-count">0</span>
  </a>
  <a href="/professionnel/commandes"><span class="ico">&#128230;</span> Commandes</a>
  <a href="/professionnel/etablissement"><span class="ico">&#127970;</span> Etabl.</a>
</nav>

<script src="/static/safe_locale.js"></script>
<script src="/static/professional_demande.js"></script>
</body>
</html>
'''
(STATIC / "professional_demande.html").write_text(DEM_HTML, encoding="utf-8")
print("[OK] professional_demande.html")

# ============================================================
# 5. PAGE CONFIRMATION
# ============================================================
CONF_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Confirmer ma demande - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<link rel="stylesheet" href="/static/professional_common.css">
<style>
.mode-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:10px 0 18px}
.mode-btn{
  padding:18px 12px;border:2px solid var(--line);border-radius:14px;
  background:#fff;font-family:inherit;font-size:14px;font-weight:800;
  color:var(--ink);cursor:pointer;text-align:center;
  transition:.15s;display:flex;flex-direction:column;align-items:center;gap:6px;
}
.mode-btn:hover{border-color:var(--blue)}
.mode-btn.active{border-color:var(--blue);background:var(--blue-soft);color:var(--blue-dark)}
.mode-btn .ico{font-size:24px}

.field{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.field label{font-size:12px;font-weight:800;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
.field input,.field textarea{
  padding:12px 14px;border:1px solid var(--line);border-radius:12px;
  font-family:inherit;font-size:15px;outline:none;background:#fff;color:var(--ink);
  width:100%;
}
.field input:focus,.field textarea:focus{border-color:var(--blue)}

.gps-btn{
  padding:11px 14px;border:1px solid var(--line);border-radius:12px;
  background:#fff;color:var(--ink);font-family:inherit;font-size:13px;font-weight:700;
  cursor:pointer;margin-top:6px;width:100%;
}
.gps-btn:hover{border-color:var(--blue);color:var(--blue)}
.gps-status{font-size:12px;color:var(--muted);margin-top:6px}

.success-box{
  background:var(--blue-soft);border:1px solid #cddff0;border-radius:14px;
  padding:24px;text-align:center;margin:20px 0;
}
.success-icon{
  width:64px;height:64px;border-radius:50%;
  background:var(--blue);color:#fff;
  display:flex;align-items:center;justify-content:center;
  font-size:32px;margin:0 auto 14px;
}
.success-box h2{margin:0 0 6px;font-size:18px}
.success-box p{color:var(--blue-dark);font-size:14px;margin:0 0 14px}
.success-ref{
  background:#fff;border:1px dashed var(--line);
  border-radius:10px;padding:12px;font-family:Consolas,monospace;
  font-weight:800;color:var(--blue-dark);font-size:14px;
}
</style>
</head>
<body>

<header class="pg-header">
  <div class="pg-header-inner">
    <a class="pg-back" href="/professionnel/demande" aria-label="Retour">&#8592;</a>
    <span class="pg-title">Confirmer ma demande</span>
    <span class="pg-ref" id="page-ref">—</span>
  </div>
</header>

<main class="pg-main" id="main">
  <div style="text-align:center;padding:40px;color:#64748b">Chargement...</div>
</main>

<script src="/static/safe_locale.js"></script>
<script src="/static/professional_demande_confirmer.js"></script>
</body>
</html>
'''
(STATIC / "professional_demande_confirmer.html").write_text(CONF_HTML, encoding="utf-8")
print("[OK] professional_demande_confirmer.html")

# ============================================================
# 6. JS PAGE DEMANDE
# ============================================================
DEM_JS = r'''/* Elokinab Health - Page demande */
(function () {
  var API = "/api";
  var $ = function (id) { return document.getElementById(id); };

  var state = { draft: null, summary: null };

  function escapeHtml(s) {
    try {
      return String(s == null ? "" : s)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    } catch (e) { return ""; }
  }

  function money(v) {
    var n = Math.round(Number(v) || 0);
    try { return n.toLocaleString("fr-FR") + " F"; }
    catch (e) {
      var s = String(n), out = "";
      for (var i = 0; i < s.length; i++) {
        if (i > 0 && (s.length - i) % 3 === 0) out += " ";
        out += s.charAt(i);
      }
      return out + " F";
    }
  }

  function qtyLabel(q) {
    var n = Number(q) || 0;
    if (n === Math.floor(n)) return String(n);
    return n.toFixed(2);
  }

  function api(method, path, body) {
    var opts = {
      method: method, credentials: "same-origin",
      headers: { "Accept": "application/json" }
    };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(API + path, opts).then(function (r) {
      if (r.status === 401) {
        window.location.href = "/connexion?next=/professionnel/demande";
        throw new Error("Non authentifie");
      }
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    });
  }

  function toast(msg) {
    var t = document.createElement("div");
    t.className = "pg-toast";
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 2400);
  }

  // ============================================================
  // Chargement
  // ============================================================
  function loadDraft() {
    return api("GET", "/pro/requests/draft").then(function (d) {
      state.draft = d;
      return api("GET", "/pro/requests/" + encodeURIComponent(d.reference) + "/summary");
    }).then(function (sum) {
      state.summary = sum;
      render();
    }).catch(function (e) {
      $("main").innerHTML = '<div style="text-align:center;padding:40px;color:#dc2626">Erreur : ' +
        escapeHtml(e.message) + '</div>';
    });
  }

  // ============================================================
  // Rendu
  // ============================================================
  function render() {
    var sum = state.summary;
    if (!sum) return;

    $("page-ref").textContent = sum.reference;
    var navCount = $("nav-count");
    if (sum.items_count > 0) {
      navCount.textContent = sum.items_count > 99 ? "99+" : String(sum.items_count);
      navCount.classList.remove("hidden");
    } else {
      navCount.classList.add("hidden");
    }

    if (sum.items_count === 0 && sum.attachments_count === 0) {
      renderGateway();
    } else {
      renderReview();
    }
  }

  function renderGateway() {
    $("page-title").textContent = "Nouvelle demande";
    $("main").innerHTML = '' +
      '<div class="gw-hero">' +
        '<h1>Comment souhaitez-vous<br>passer votre demande ?</h1>' +
        '<p>Choisissez une methode selon votre besoin.</p>' +
      '</div>' +
      '<div class="gw-cards">' +
        '<a class="gw-card cat" href="/professionnel/catalogue">' +
          '<div class="gw-card-icon">&#128269;</div>' +
          '<h2 class="gw-card-title">Depuis le catalogue</h2>' +
          '<p class="gw-card-desc">Choisissez vos produits, quantites, et finalisez votre demande.</p>' +
          '<div class="gw-card-foot">' +
            '<span class="gw-card-cta">Parcourir le catalogue</span>' +
            '<span class="gw-card-arrow">&#8594;</span>' +
          '</div>' +
        '</a>' +
        '<div class="gw-or">ou</div>' +
        '<a class="gw-card wa" target="_blank" rel="noopener" ' +
           'href="https://wa.me/22871039904?text=Bonjour%20Elokinab%20Health%2C%20je%20souhaite%20passer%20une%20commande.%20Voici%20ma%20liste%20%3A%0A%0A">' +
          '<div class="gw-card-icon">&#128172;</div>' +
          '<h2 class="gw-card-title">Via WhatsApp</h2>' +
          '<p class="gw-card-desc">Envoyez votre liste, photo, PDF, message ou vocal directement.</p>' +
          '<div class="gw-card-foot">' +
            '<span class="gw-card-cta">Ouvrir WhatsApp</span>' +
            '<span class="gw-card-arrow">&#8594;</span>' +
          '</div>' +
        '</a>' +
      '</div>' +
      '<div class="pg-info">' +
        '<strong>Conseil :</strong> utilisez le catalogue pour les produits que vous connaissez, WhatsApp pour les listes libres ou les produits non references.' +
      '</div>';
  }

  function renderReview() {
    $("page-title").textContent = "Ma demande";
    var items = sum_items_render(state.summary);
    var atts = state.summary.attachments_count > 0
      ? '<div class="pg-info">' + state.summary.attachments_count +
        ' piece(s) jointe(s) dans votre demande.</div>'
      : '';

    var html = '' +
      '<h2 class="pg-section-title">' +
        'Ma demande <span class="pg-count">' + state.summary.items_count + '</span>' +
      '</h2>' +
      items +
      atts +
      '<div class="totals-card">' +
        '<div class="totals-line">' +
          '<span class="lbl">Sous-total</span>' +
          '<span class="val">' + money(state.summary.subtotal) + '</span>' +
        '</div>' +
        '<div class="totals-line">' +
          '<span class="lbl">Livraison</span>' +
          '<span class="val confirm">A confirmer</span>' +
        '</div>' +
        '<div class="totals-line total">' +
          '<span>Total</span>' +
          '<span class="val">' + money(state.summary.subtotal) + ' + livraison</span>' +
        '</div>' +
      '</div>' +
      '<div class="pg-info">' +
        '<strong>Prochaine etape :</strong> votre demande sera transmise a la pharmacie ' +
        'qui confirmera la disponibilite, les quantites et les prix finaux. ' +
        'Vous recevrez une confirmation avant paiement.' +
      '</div>' +
      '<div class="pg-actions">' +
        '<a class="btn btn-ghost" href="/professionnel/catalogue">+ Ajouter des produits</a>' +
        '<a class="btn btn-primary" href="/professionnel/demande/confirmer">Continuer &#8594;</a>' +
        '<button class="btn btn-danger" id="btn-clear" type="button">Vider ma demande</button>' +
      '</div>';

    $("main").innerHTML = html;

    // Handlers
    Array.prototype.forEach.call($("main").querySelectorAll("[data-del]"), function (b) {
      b.addEventListener("click", function () {
        var id = b.getAttribute("data-del");
        api("DELETE", "/pro/requests/" + state.draft.reference + "/items/" + id)
          .then(loadDraft).catch(function (e) { toast(e.message); });
      });
    });
    var clearBtn = $("btn-clear");
    if (clearBtn) clearBtn.addEventListener("click", clearAll);
  }

  function sum_items_render(sum) {
    if (!sum.items || sum.items.length === 0) {
      return '<div style="text-align:center;padding:24px;color:#64748b">Aucun produit.</div>';
    }
    return sum.items.map(function (it) {
      var priceHtml = it.unit_price > 0
        ? money(it.line_total) + '<small>' + money(it.unit_price) + ' / unite</small>'
        : '<small>Prix a confirmer</small>';
      return '<div class="it-row">' +
        '<div class="it-body">' +
          '<div class="it-name">' + escapeHtml(it.description) + '</div>' +
          '<div class="it-qty">x ' + qtyLabel(it.requested_quantity) + '</div>' +
        '</div>' +
        '<div class="it-price">' + priceHtml + '</div>' +
        '<button class="it-del" data-del="' + it.id + '" title="Retirer">&times;</button>' +
      '</div>';
    }).join("");
  }

  function clearAll() {
    if (!state.summary || !state.summary.items) return;
    if (!confirm("Vider toute votre demande ?")) return;
    var chain = Promise.resolve();
    state.summary.items.forEach(function (it) {
      chain = chain.then(function () {
        return api("DELETE", "/pro/requests/" + state.draft.reference + "/items/" + it.id);
      });
    });
    chain.then(loadDraft).catch(function (e) { toast(e.message); });
  }

  document.addEventListener("DOMContentLoaded", loadDraft);
})();
'''
(STATIC / "professional_demande.js").write_text(DEM_JS, encoding="utf-8")
print("[OK] professional_demande.js")

# ============================================================
# 7. JS PAGE CONFIRMATION
# ============================================================
CONF_JS = r'''/* Elokinab Health - Page confirmation demande */
(function () {
  var API = "/api";
  var $ = function (id) { return document.getElementById(id); };

  var state = {
    draft: null,
    summary: null,
    mode: "retrait",
    lat: null, lon: null, acc: null,
    submitted: false
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
    try { return n.toLocaleString("fr-FR") + " F"; }
    catch (e) {
      var s = String(n), out = "";
      for (var i = 0; i < s.length; i++) {
        if (i > 0 && (s.length - i) % 3 === 0) out += " ";
        out += s.charAt(i);
      }
      return out + " F";
    }
  }

  function qtyLabel(q) {
    var n = Number(q) || 0;
    if (n === Math.floor(n)) return String(n);
    return n.toFixed(2);
  }

  function api(method, path, body) {
    var opts = {
      method: method, credentials: "same-origin",
      headers: { "Accept": "application/json" }
    };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(API + path, opts).then(function (r) {
      if (r.status === 401) {
        window.location.href = "/connexion?next=/professionnel/demande";
        throw new Error("Non authentifie");
      }
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    });
  }

  function toast(msg) {
    var t = document.createElement("div");
    t.className = "pg-toast";
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 2400);
  }

  // ============================================================
  // Chargement
  // ============================================================
  function load() {
    return api("GET", "/pro/requests/draft").then(function (d) {
      state.draft = d;
      return api("GET", "/pro/requests/" + encodeURIComponent(d.reference) + "/summary");
    }).then(function (sum) {
      state.summary = sum;
      if (sum.items_count === 0 && sum.attachments_count === 0) {
        window.location.href = "/professionnel/demande";
        return;
      }
      render();
    }).catch(function (e) {
      $("main").innerHTML = '<div style="text-align:center;padding:40px;color:#dc2626">Erreur : ' +
        escapeHtml(e.message) + '</div>';
    });
  }

  // ============================================================
  // Rendu
  // ============================================================
  function render() {
    if (state.submitted) { renderSuccess(); return; }

    $("page-ref").textContent = state.summary.reference;

    var html = '' +
      '<h2 class="pg-section-title">Recapitulatif</h2>' +
      itemsRender() +
      '<div class="totals-card">' +
        '<div class="totals-line">' +
          '<span class="lbl">Sous-total</span>' +
          '<span class="val">' + money(state.summary.subtotal) + '</span>' +
        '</div>' +
        '<div class="totals-line">' +
          '<span class="lbl">Livraison</span>' +
          '<span class="val confirm" id="delivery-val">A confirmer</span>' +
        '</div>' +
        '<div class="totals-line total">' +
          '<span>Total</span>' +
          '<span class="val" id="total-val">' + money(state.summary.subtotal) + ' + livraison</span>' +
        '</div>' +
      '</div>' +

      '<h2 class="pg-section-title">Mode de recuperation</h2>' +
      '<div class="mode-grid">' +
        '<button class="mode-btn ' + (state.mode === "retrait" ? "active" : "") + '" data-mode="retrait" type="button">' +
          '<span class="ico">&#127968;</span>Retrait' +
        '</button>' +
        '<button class="mode-btn ' + (state.mode === "livraison" ? "active" : "") + '" data-mode="livraison" type="button">' +
          '<span class="ico">&#128666;</span>Livraison' +
        '</button>' +
      '</div>' +

      '<div id="delivery-fields"' + (state.mode === "retrait" ? ' class="hidden"' : '') + '>' +
        '<div class="field">' +
          '<label for="address">Adresse de livraison</label>' +
          '<textarea id="address" rows="2" placeholder="Quartier, rue, repere..."></textarea>' +
        '</div>' +
        '<button type="button" class="gps-btn" id="gps-btn">&#128205; Utiliser ma position GPS</button>' +
        '<div class="gps-status" id="gps-status"></div>' +
      '</div>' +

      '<div class="notes-block">' +
        '<label for="notes">Notes (facultatif)</label>' +
        '<textarea class="notes" id="notes" placeholder="Instructions particulieres, delai souhaite..."></textarea>' +
      '</div>' +

      '<div class="pg-actions">' +
        '<button class="btn btn-primary" id="submit-btn" type="button">Envoyer ma demande</button>' +
        '<a class="btn btn-ghost" href="/professionnel/demande">Retour</a>' +
      '</div>' +

      '<div class="pg-info">' +
        '<strong>Que se passe-t-il ensuite ?</strong> Votre demande sera transmise a Elokinab Health. ' +
        'La pharmacie verifiera la disponibilite, les quantites et les prix, puis vous enverra une confirmation ' +
        'avant tout paiement.' +
      '</div>';

    $("main").innerHTML = html;
    bindEvents();
  }

  function itemsRender() {
    if (!state.summary.items || state.summary.items.length === 0) {
      return '<div class="pg-info">Aucun produit. ' +
        '<a href="/professionnel/catalogue" style="color:var(--blue);font-weight:800">Ajouter des produits</a></div>';
    }
    return state.summary.items.map(function (it) {
      var priceHtml = it.unit_price > 0
        ? money(it.line_total) + '<small>' + money(it.unit_price) + ' / unite</small>'
        : '<small>Prix a confirmer</small>';
      return '<div class="it-row">' +
        '<div class="it-body">' +
          '<div class="it-name">' + escapeHtml(it.description) + '</div>' +
          '<div class="it-qty">x ' + qtyLabel(it.requested_quantity) + '</div>' +
        '</div>' +
        '<div class="it-price">' + priceHtml + '</div>' +
      '</div>';
    }).join("");
  }

  // ============================================================
  // Evenements
  // ============================================================
  function bindEvents() {
    // Mode
    Array.prototype.forEach.call(document.querySelectorAll(".mode-btn"), function (b) {
      b.addEventListener("click", function () {
        state.mode = b.getAttribute("data-mode");
        render();
      });
    });

    // GPS
    var gpsBtn = $("gps-btn");
    if (gpsBtn) gpsBtn.addEventListener("click", askGPS);

    // Submit
    var sub = $("submit-btn");
    if (sub) sub.addEventListener("click", submit);
  }

  function askGPS() {
    if (!navigator.geolocation) {
      $("gps-status").textContent = "GPS indisponible.";
      return;
    }
    var b = $("gps-btn");
    b.disabled = true;
    b.textContent = "Localisation...";
    navigator.geolocation.getCurrentPosition(function (pos) {
      state.lat = pos.coords.latitude;
      state.lon = pos.coords.longitude;
      state.acc = pos.coords.accuracy;
      b.disabled = false;
      b.innerHTML = "&#128205; Actualiser ma position";
      $("gps-status").innerHTML = "&#10003; Position : " +
        state.lat.toFixed(4) + ", " + state.lon.toFixed(4) +
        " (&plusmn; " + Math.round(state.acc) + " m)";
    }, function () {
      b.disabled = false;
      b.innerHTML = "&#128205; Utiliser ma position GPS";
      $("gps-status").textContent = "Position introuvable. Vous pouvez saisir l'adresse.";
    }, { enableHighAccuracy: true, timeout: 15000 });
  }

  function submit() {
    var notes = $("notes") ? $("notes").value.trim() : "";
    var address = $("address") ? $("address").value.trim() : "";

    if (state.mode === "livraison" && !address && state.lat === null) {
      toast("Adresse ou GPS obligatoire pour la livraison");
      return;
    }

    var payload = {
      delivery_mode: state.mode,
      address: address,
      notes: notes
    };
    if (state.lat !== null && state.lon !== null) {
      payload.latitude = state.lat;
      payload.longitude = state.lon;
      payload.location_accuracy = state.acc;
    }

    var btn = $("submit-btn");
    btn.disabled = true;
    btn.textContent = "Envoi...";

    api("POST", "/pro/requests/" + state.draft.reference + "/submit", payload)
      .then(function () {
        state.submitted = true;
        render();
      })
      .catch(function (e) {
        toast(e.message);
        btn.disabled = false;
        btn.textContent = "Envoyer ma demande";
      });
  }

  function renderSuccess() {
    $("page-title").textContent = "Demande envoyee";
    $("page-ref").textContent = state.summary.reference;
    $("main").innerHTML = '' +
      '<div class="success-box">' +
        '<div class="success-icon">&#10003;</div>' +
        '<h2>Demande transmise</h2>' +
        '<p>Votre demande a bien ete envoyee a Elokinab Health.</p>' +
        '<div class="success-ref">' + escapeHtml(state.summary.reference) + '</div>' +
      '</div>' +
      '<div class="pg-info">' +
        '<strong>Prochaine etape :</strong> la pharmacie va verifier la disponibilite, ' +
        'confirmer les quantites et les prix finaux. Vous serez notifie des que la ' +
        'confirmation sera prete.' +
      '</div>' +
      '<div class="pg-actions">' +
        '<a class="btn btn-primary" href="/professionnel/commandes">Voir mes commandes</a>' +
        '<a class="btn btn-ghost" href="/professionnel">Retour a l\'accueil</a>' +
      '</div>';
  }

  document.addEventListener("DOMContentLoaded", load);
})();
'''
(STATIC / "professional_demande_confirmer.js").write_text(CONF_JS, encoding="utf-8")
print("[OK] professional_demande_confirmer.js")

print()
print("=" * 60)
print("NOUVEAU FLUX DEMANDE LIVRE")
print("=" * 60)
print()
print("Backend :")
print("  GET  /api/pro/requests/{ref}/summary    (items + totaux)")
print("  POST /api/pro/requests/{ref}/submit     (etendu : mode, adresse, GPS, notes)")
print()
print("Pages :")
print("  /professionnel/demande            -> gateway si vide / review si items")
print("  /professionnel/demande/confirmer  -> mode + adresse + notes + envoi")
print()
print("Le parcours :")
print("  Catalogue -> + Demande -> Review -> Confirmer -> Envoyer")
print("                                   -> Statut SUBMITTED")
print("                                   -> Pharmacie verifie")
print("                                   -> Confirmation puis paiement")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")