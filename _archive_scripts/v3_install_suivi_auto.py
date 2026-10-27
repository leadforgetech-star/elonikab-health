"""
v3_install_suivi_auto.py
- Endpoint /api/orders/mine (liste des commandes de l'utilisateur connecte)
- Page suivi : auto-liste les commandes si connecte
- Header : icone Suivi avec label texte
- Header : sticky renforce
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_suivi_auto_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAIN, backup / "main.py")
shutil.copy2(STATIC / "suivi.html", backup / "suivi.html")
shutil.copy2(STATIC / "suivi.js", backup / "suivi.js")
shutil.copy2(STATIC / "header.js", backup / "header.js")
shutil.copy2(STATIC / "header.css", backup / "header.css")
shutil.copy2(STATIC / "mobile.css", backup / "mobile.css")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. Ajouter GET /api/orders/mine dans main.py
# ============================================================
src = MAIN.read_text(encoding="utf-8")

if "/api/orders/mine" not in src:
    # Inserer la route apres GET /api/orders/{reference}
    anchor = '''@app.get("/api/orders/{reference}")
def get_order(reference: str):'''
    new_route = '''@app.get("/api/orders/mine")
def list_my_orders(session_token: str = Cookie(None, alias="elokinab_session")):
    """Liste des commandes de l'utilisateur connecte."""
    if not session_token:
        raise HTTPException(401, "Non authentifie")
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT u.id FROM sessions s JOIN users u ON u.id = s.user_id"
            " WHERE s.token = ? AND s.expires_at > ?",
            (session_token, datetime.now().isoformat(timespec="seconds")),
        ).fetchone()
        if user is None:
            raise HTTPException(401, "Session expiree")
        rows = conn.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 50",
            (user["id"],),
        ).fetchall()
    finally:
        conn.close()
    return [row_to_dict(r) for r in rows]


'''
    if anchor in src:
        # Ajouter Cookie aux imports si manquant
        if "from fastapi import" in src and "Cookie" not in src.split("from fastapi import")[1].split("\n")[0]:
            src = src.replace(
                "from fastapi import File, Form, HTTPException, UploadFile",
                "from fastapi import Cookie, File, Form, HTTPException, UploadFile",
                1,
            )
            print("[OK] main.py -> Cookie importe")
        src = src.replace(anchor, new_route + anchor, 1)
        MAIN.write_text(src, encoding="utf-8")
        print("[OK] main.py -> /api/orders/mine")
    else:
        print("[!] anchor GET /api/orders/{reference} introuvable")
else:
    print("[i] main.py -> /api/orders/mine deja present")

# ============================================================
# 2. Reecriture de suivi.html (auto-liste + formulaire optionnel)
# ============================================================
SUIVI_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Suivi de commandes - Elokinab Health</title>
<link rel="stylesheet" href="/static/style.css">
<link rel="stylesheet" href="/static/suivi.css">
<link rel="stylesheet" href="/static/header.css">
<link rel="stylesheet" href="/static/mobile.css">
<style>
  .my-orders{display:flex;flex-direction:column;gap:12px;margin-top:16px}
  .order-card-suivi{
    display:block;text-decoration:none;color:inherit;
    background:#fff;border:1px solid #ddece6;border-radius:14px;
    padding:16px;transition:.15s;
  }
  .order-card-suivi:hover{border-color:#0f9d76;box-shadow:0 6px 20px rgba(15,38,32,.08)}
  .order-card-suivi .ref{font-family:Consolas,monospace;font-weight:800;font-size:15px;color:#0f2620}
  .order-card-suivi .date{font-size:12px;color:#6c8a80;margin-top:2px}
  .order-card-suivi .row{display:flex;justify-content:space-between;align-items:center;margin-top:10px;gap:10px}
  .order-card-suivi .total{font-weight:800;color:#0a7a5a;font-size:15px}
  .order-card-suivi .status-badge{font-size:10px;padding:4px 9px;font-weight:800}
  .empty-orders{text-align:center;padding:40px 20px;color:#6c8a80}
  .empty-orders .big{font-size:38px;margin-bottom:8px}
  .login-cta{background:#e8f7f1;border:1px solid #c7e9dc;border-radius:12px;padding:16px;margin-top:12px;text-align:center}
  .login-cta a{color:#0a7a5a;font-weight:700;text-decoration:none}
  .manual-toggle{background:none;border:0;padding:8px 0;color:#6c8a80;font-size:13px;text-decoration:underline;cursor:pointer;font-family:inherit}
  .manual-toggle:hover{color:#0a7a5a}
</style>
</head>
<body>

<header class="topbar">
  <div class="container topbar-inner">
    <a class="brand" href="/">
      <span class="brand-logo">+</span>
      <span class="brand-text">
        <strong>Elokinab Health</strong>
        <small>Suivi de commandes</small>
      </span>
    </a>
    <nav class="topnav">
      <a href="/">Accueil</a>
      <a href="/static/cart.html">Panier</a>
      <a href="/suivi" class="active">Mes commandes</a>
    </nav>
  </div>
</header>

<main class="container">
  <div class="page-head">
    <h1>Mes commandes</h1>
    <p class="muted" id="subtitle">Suivez l'etat de vos commandes en temps reel.</p>
  </div>

  <!-- Zone utilisateur connecte : liste auto -->
  <section id="my-orders-section">
    <div id="my-orders-list" class="my-orders">
      <div class="empty-orders">
        <div class="big">&#8987;</div>
        <div>Chargement...</div>
      </div>
    </div>
  </section>

  <!-- Zone de recherche manuelle (repliable) -->
  <section style="margin-top:20px">
    <button type="button" class="manual-toggle" id="manual-toggle">
      Vous avez un numero de commande ? Cliquez ici
    </button>
    <form id="track-form" class="track-form card hidden" style="margin-top:10px">
      <div class="form-row">
        <label for="ref-input">Numero de demande</label>
        <input type="text" id="ref-input" placeholder="Ex : CMD-260927-75D3A8" autocomplete="off">
      </div>
      <button type="submit" class="btn btn-primary">Rechercher ma commande</button>
      <p id="track-error" class="alert hidden"></p>
    </form>
  </section>

  <!-- Resultat detaille (apparait apres selection) -->
  <section id="track-result" class="hidden" style="margin-top:20px">
    <button type="button" class="link-back" id="back-to-list">&#8592; Retour a mes commandes</button>

    <div class="card track-header">
      <div class="track-header-left">
        <span class="muted small">Numero de demande</span>
        <strong id="track-ref"></strong>
        <span class="muted small" id="track-date"></span>
      </div>
      <span class="status-badge" id="track-status-badge"></span>
    </div>

    <div class="card">
      <h2 class="track-section-title">Progression</h2>
      <div id="timeline" class="timeline"></div>
      <p id="track-refused" class="alert alert-danger hidden">
        Votre demande a ete refusee. Contactez la pharmacie pour plus d'informations.
      </p>
    </div>

    <div class="card">
      <h2 class="track-section-title">Detail de la commande</h2>
      <dl id="track-summary" class="summary"></dl>
    </div>

    <div class="track-actions">
      <button type="button" class="btn btn-ghost" id="track-refresh">Actualiser</button>
      <a class="btn btn-primary" id="track-pay" href="#" style="display:none">Payer maintenant</a>
    </div>
    <p class="muted small" id="track-last-refresh"></p>
  </section>
</main>

<script src="/static/header.js"></script>
<script src="/static/suivi.js"></script>
</body>
</html>
'''
(STATIC / "suivi.html").write_text(SUIVI_HTML, encoding="utf-8")
print("[OK] suivi.html reecrit")

# ============================================================
# 3. Reecriture de suivi.js
# ============================================================
SUIVI_JS = r'''var API = "/api";

var STATUS_ORDER = ["en_attente", "confirmee", "en_preparation", "prete", "terminee"];

var STATUS_INFO = {
  en_attente:      { label: "En attente",     hint: "Votre demande a bien ete recue. La pharmacie va l'examiner." },
  confirmee:       { label: "Confirmee",      hint: "La pharmacie a valide votre demande." },
  en_preparation:  { label: "En preparation", hint: "Votre commande est en cours de preparation." },
  prete:           { label: "Prete",          hint: "Votre commande est prete. Retrait ou livraison imminente." },
  terminee:        { label: "Terminee",       hint: "Votre commande a ete remise ou livree." },
  refusee:         { label: "Refusee",        hint: "La pharmacie n'a pas pu donner suite a cette demande." }
};

var PAYMENT_LABELS = {
  NONE: "Non initie",
  PENDING: "En attente de preuve",
  PROOF_SUBMITTED: "Preuve en verification",
  VERIFIED: "Paiement verifie",
  REJECTED: "Paiement refuse"
};

var currentRef = null;
var trackTimer = null;

function $(sel) { return document.querySelector(sel); }

function el(tag, cls, txt) {
  var n = document.createElement(tag);
  if (cls) n.className = cls;
  if (txt !== undefined && txt !== null) n.textContent = txt;
  return n;
}

function money(v) {
  var n = Math.round(Number(v) || 0);
  return n.toLocaleString("fr-FR") + " FCFA";
}

function fmtDate(iso) {
  if (!iso) return "";
  var d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  var pad = function (n) { return n < 10 ? "0" + n : "" + n; };
  return pad(d.getDate()) + "/" + pad(d.getMonth()+1) + "/" + d.getFullYear()
    + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
}

function showError(msg) {
  var box = $("#track-error");
  if (!box) return;
  box.textContent = msg;
  box.classList.remove("hidden");
}
function clearError() {
  var box = $("#track-error");
  if (box) { box.classList.add("hidden"); box.textContent = ""; }
}

// ============ LISTE AUTO ============

function renderMyOrders(list) {
  var box = $("#my-orders-list");
  if (!box) return;
  box.innerHTML = "";
  if (!list || list.length === 0) {
    box.innerHTML =
      '<div class="empty-orders">' +
      '<div class="big">&#128230;</div>' +
      '<div>Aucune commande pour le moment.</div>' +
      '<div style="margin-top:12px"><a class="btn btn-primary" href="/">Voir le catalogue</a></div>' +
      '</div>';
    return;
  }
  list.forEach(function (o) {
    var card = document.createElement("a");
    card.className = "order-card-suivi";
    card.href = "#";
    card.addEventListener("click", function (ev) {
      ev.preventDefault();
      showOrderDetail(o.reference);
    });

    var top = document.createElement("div");
    top.appendChild(el("div", "ref", o.reference));
    top.appendChild(el("div", "date", fmtDate(o.created_at)));
    card.appendChild(top);

    var row = document.createElement("div");
    row.className = "row";

    var left = document.createElement("div");
    var st = el("span", "status-badge status-" + o.status,
                (STATUS_INFO[o.status] && STATUS_INFO[o.status].label) || o.status);
    left.appendChild(st);

    // paiement en attente ?
    if (o.payment_status === "PENDING" || o.payment_status === "REJECTED") {
      left.appendChild(el("span", "muted small", " - Paiement " +
        (PAYMENT_LABELS[o.payment_status] || o.payment_status)));
    }

    var right = document.createElement("div");
    right.className = "total";
    right.textContent = money(o.subtotal);

    row.appendChild(left);
    row.appendChild(right);
    card.appendChild(row);

    box.appendChild(card);
  });
}

function loadMyOrders() {
  return fetch(API + "/orders/mine", { credentials: "same-origin" })
    .then(function (r) {
      if (r.status === 401) return null;
      if (!r.ok) throw new Error("Erreur");
      return r.json();
    })
    .then(function (list) {
      if (list === null) {
        // Non connecte : message d'invitation
        $("#my-orders-list").innerHTML =
          '<div class="empty-orders">' +
          '<div class="big">&#128274;</div>' +
          '<div>Connectez-vous pour voir vos commandes.</div>' +
          '<div class="login-cta"><a href="/static/login.html?next=/suivi">Se connecter</a> ' +
          '&nbsp;ou&nbsp; <a href="/static/register.html">Creer un compte</a></div>' +
          '</div>';
        return;
      }
      renderMyOrders(list);
      // Si ref dans l'URL, ouvrir directement
      var params = new URLSearchParams(window.location.search);
      var ref = params.get("ref");
      if (ref) showOrderDetail(ref);
    })
    .catch(function (e) {
      $("#my-orders-list").innerHTML =
        '<div class="empty-orders"><div>Erreur de chargement.</div></div>';
    });
}

// ============ DETAIL ============

function loadOrder(reference) {
  return fetch(API + "/orders/" + encodeURIComponent(reference)).then(function (r) {
    if (r.status === 404) throw new Error("Aucune commande trouvee avec ce numero.");
    if (!r.ok) throw new Error("Erreur serveur.");
    return r.json();
  });
}

function renderStatusBadge(status) {
  var b = $("#track-status-badge");
  b.className = "status-badge status-" + status;
  b.textContent = (STATUS_INFO[status] && STATUS_INFO[status].label) || status;
}

function renderTimeline(currentStatus) {
  var box = $("#timeline");
  box.innerHTML = "";
  var refused = currentStatus === "refusee";
  var currentIdx = STATUS_ORDER.indexOf(currentStatus);
  STATUS_ORDER.forEach(function (status, idx) {
    var step = el("div", "tl-step");
    var done = !refused && idx < currentIdx;
    var current = !refused && idx === currentIdx;
    if (done) step.classList.add("done");
    if (current) step.classList.add("current");
    var dot = el("div", "tl-dot");
    if (done) dot.textContent = "\u2713"; else dot.textContent = String(idx + 1);
    var info = el("div", "tl-info");
    info.appendChild(el("div", "tl-label", STATUS_INFO[status].label));
    if (current) info.appendChild(el("div", "tl-hint", STATUS_INFO[status].hint));
    step.appendChild(dot); step.appendChild(info);
    box.appendChild(step);
  });
  if (refused) $("#track-refused").classList.remove("hidden");
  else $("#track-refused").classList.add("hidden");
}

function renderSummary(o) {
  var dl = $("#track-summary");
  dl.innerHTML = "";
  function row(label, value) {
    dl.appendChild(el("dt", null, label));
    dl.appendChild(el("dd", null, value));
  }
  var qty = Number(o.quantity) || 1;
  var price = Number(o.price) || 0;
  var subtotal = (o.subtotal !== undefined && o.subtotal !== null) ? Number(o.subtotal) : (price * qty);
  var fee = Number(o.delivery_fee) || 0;
  var total = (o.total !== undefined && o.total !== null) ? Number(o.total) : (subtotal + fee);

  row("Client", o.customer_name || "");
  row("Produit", (o.product_name || "") + " (x" + qty + ")");
  row("Sous-total", money(subtotal));
  row("Livraison", money(fee));
  if (o.delivery_distance_km !== null && o.delivery_distance_km !== undefined) {
    row("Distance", Number(o.delivery_distance_km).toFixed(1) + " km");
  }
  row("Total", money(total));
  row("Mode", o.delivery_mode === "livraison" ? "Livraison a domicile" : "Retrait en pharmacie");
  if (o.address) row("Adresse", o.address);
  row("Ordonnance", o.prescription_file ? "Jointe" : "Non jointe");
  row("Paiement", PAYMENT_LABELS[o.payment_status] || o.payment_status || "Non initie");
}

function renderOrder(o) {
  $("#track-result").classList.remove("hidden");
  $("#my-orders-section").classList.add("hidden");
  $("#track-ref").textContent = o.reference;
  $("#track-date").textContent = "Creee le " + fmtDate(o.created_at);
  renderStatusBadge(o.status);
  renderTimeline(o.status);
  renderSummary(o);

  // Bouton Payer maintenant
  var payBtn = $("#track-pay");
  if (payBtn) {
    if (o.payment_status === "VERIFIED") {
      payBtn.style.display = "none";
    } else {
      payBtn.style.display = "inline-block";
      payBtn.href = "/static/payment.html?ref=" + encodeURIComponent(o.reference);
    }
  }

  var now = new Date();
  var pad = function (n) { return n < 10 ? "0" + n : "" + n; };
  var lr = $("#track-last-refresh");
  if (lr) lr.textContent = "Derniere actualisation : " +
    pad(now.getHours()) + ":" + pad(now.getMinutes()) + ":" + pad(now.getSeconds());
  window.scrollTo(0, 0);
}

function showOrderDetail(reference) {
  clearError();
  currentRef = reference;
  // maj URL
  try {
    var url = new URL(window.location.href);
    url.searchParams.set("ref", reference);
    window.history.replaceState({}, "", url.toString());
  } catch (e) {}

  loadOrder(reference).then(function (o) {
    renderOrder(o);
    startAutoRefresh(reference);
  }).catch(function (e) {
    showError(e.message);
  });
}

function backToList() {
  currentRef = null;
  if (trackTimer) { clearInterval(trackTimer); trackTimer = null; }
  try {
    var url = new URL(window.location.href);
    url.searchParams.delete("ref");
    window.history.replaceState({}, "", url.toString());
  } catch (e) {}
  $("#track-result").classList.add("hidden");
  $("#my-orders-section").classList.remove("hidden");
  loadMyOrders();
}

function refreshCurrent() {
  if (!currentRef) return;
  loadOrder(currentRef).then(renderOrder).catch(function () {});
}

function startAutoRefresh(reference) {
  if (trackTimer) clearInterval(trackTimer);
  trackTimer = setInterval(function () {
    loadOrder(reference).then(renderOrder).catch(function () {});
  }, 15000);
}

// ============ INIT ============

function init() {
  loadMyOrders();

  // Toggle formulaire manuel
  var toggle = $("#manual-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var form = $("#track-form");
      form.classList.toggle("hidden");
      if (!form.classList.contains("hidden")) {
        toggle.textContent = "Masquer la recherche manuelle";
        $("#ref-input").focus();
      } else {
        toggle.textContent = "Vous avez un numero de commande ? Cliquez ici";
      }
    });
  }

  // Form submit
  var form = $("#track-form");
  if (form) {
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var ref = $("#ref-input").value.trim().toUpperCase();
      if (!ref) { showError("Entrez un numero de demande."); return; }
      showOrderDetail(ref);
    });
  }

  // Back
  var back = $("#back-to-list");
  if (back) back.addEventListener("click", backToList);

  // Refresh
  var rf = $("#track-refresh");
  if (rf) rf.addEventListener("click", refreshCurrent);
}

document.addEventListener("DOMContentLoaded", init);
'''
(STATIC / "suivi.js").write_text(SUIVI_JS, encoding="utf-8")
print("[OK] suivi.js reecrit")

# ============================================================
# 4. header.js : icone Suivi avec label texte
# ============================================================
HJ = STATIC / "header.js"
js = HJ.read_text(encoding="utf-8")

old_track = '''    // Lien Suivi toujours visible
    var track = el("a", "eh-icon-btn");
    track.href = "/suivi";
    track.title = "Suivre ma commande";
    track.innerHTML = "\\uD83D\\uDCE6";
    wrap.appendChild(track);'''

new_track = '''    // Lien Suivi toujours visible avec label
    var track = el("a", "eh-link-btn eh-track-btn");
    track.href = "/suivi";
    track.title = "Suivre mes commandes";
    track.innerHTML = '&#128230; Suivi';
    wrap.appendChild(track);'''

if old_track in js:
    js = js.replace(old_track, new_track, 1)
    HJ.write_text(js, encoding="utf-8")
    print("[OK] header.js -> bouton Suivi avec label")
else:
    print("[i] header.js -> bouton Suivi deja patche ou pattern introuvable")

# ============================================================
# 5. header.css : style du bouton Suivi
# ============================================================
HC = STATIC / "header.css"
hcss = HC.read_text(encoding="utf-8")

if ".eh-track-btn" not in hcss:
    hcss += '''
/* --- Bouton Suivi avec label --- */
.eh-track-btn{
  display: inline-flex !important;
  align-items: center;
  gap: 5px;
  padding: 8px 12px !important;
  font-size: 13px !important;
  font-weight: 700;
  background: #e8f7f1 !important;
  color: #0a7a5a !important;
  border: 1px solid #c7e9dc !important;
  border-radius: 10px;
  text-decoration: none;
  white-space: nowrap;
}
.eh-track-btn:hover{
  background: #0f9d76 !important;
  color: #fff !important;
  border-color: #0f9d76 !important;
}

/* --- Header vraiment sticky --- */
.topbar{
  position: sticky !important;
  top: 0 !important;
  z-index: 999 !important;
  background: #fff !important;
  box-shadow: 0 2px 10px rgba(15,38,32,.08);
  will-change: transform;
}
.eh-mini-bar{
  position: sticky !important;
  top: 0 !important;
  z-index: 999 !important;
  background: #fff !important;
  box-shadow: 0 2px 10px rgba(15,38,32,.08);
}
/* Eviter que le parent du topbar casse le sticky */
body > .topbar, body > .eh-mini-bar{
  position: sticky;
}
@media (max-width: 500px){
  .eh-track-btn{
    padding: 7px 10px !important;
    font-size: 12px !important;
  }
}
'''
    HC.write_text(hcss, encoding="utf-8")
    print("[OK] header.css -> bouton Suivi + sticky renforce")
else:
    print("[i] header.css -> deja patche")

# ============================================================
# 6. mobile.css : enlever tout overflow qui casse sticky
# ============================================================
css = MOBILE.read_text(encoding="utf-8")
if "sticky-safe" not in css:
    css = css.replace(
        "html, body {\n  max-width: 100vw;\n  overflow-x: hidden;\n}",
        "html, body {\n  max-width: 100vw;\n  overflow-x: hidden;\n}\n/* sticky-safe : ne pas mettre overflow:hidden sur body (casse position:sticky) */\nbody { overflow-y: auto; }",
        1,
    )
    MOBILE.write_text(css, encoding="utf-8")
    print("[OK] mobile.css -> sticky-safe")

print()
print("=" * 60)
print("SUIVI AUTO + HEADER STICKY RENFORCE")
print("=" * 60)
print()
print("Nouveautes :")
print("  1. GET /api/orders/mine -> commandes de l'utilisateur connecte")
print("  2. Page /suivi : liste auto de MES commandes (si connecte)")
print("  3. Formulaire de recherche manuelle caché par defaut")
print("  4. Bouton 'Suivi' avec label dans le header (au lieu d'une icone)")
print("  5. Header sticky renforce (position + z-index)")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  python main.py")
print("  Ctrl+Shift+R sur iPhone (ou navigation privee)")