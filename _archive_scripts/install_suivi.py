from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
MAIN = BASE / "main.py"
INDEX = STATIC / "index.html"
APPJS = STATIC / "app.js"
STYLECSS = STATIC / "style.css"

for f in (MAIN, INDEX, APPJS, STYLECSS):
    shutil.copy(f, f.with_suffix(f.suffix + ".bak"))
print("[OK] sauvegardes .bak creees")

# =================================================================
# 1) main.py : route /suivi
# =================================================================
src = MAIN.read_text(encoding="utf-8")

if '"/suivi"' not in src:
    route = '''

@app.get("/suivi")
def suivi_page():
    return FileResponse(STATIC_DIR / "suivi.html")

'''
    # Inserer juste avant init_db()
    pattern = "\ninit_db()\n"
    if pattern in src:
        src = src.replace(pattern, route + "\ninit_db()\n", 1)
        MAIN.write_text(src, encoding="utf-8")
        print("[OK] main.py -> route /suivi")
    else:
        print("[!] init_db() introuvable")
else:
    print("[i] main.py -> /suivi deja present")

# =================================================================
# 2) static/suivi.html
# =================================================================
html = r'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Suivi de ma commande</title>
<link rel="stylesheet" href="/static/style.css">
<link rel="stylesheet" href="/static/suivi.css">
</head>
<body>

<header class="topbar">
  <div class="container topbar-inner">
    <a class="brand" href="/">
      <span class="brand-logo">+</span>
      <span class="brand-text">
        <strong>Pharmacie du Parc</strong>
        <small>Prototype de demonstration</small>
      </span>
    </a>
    <nav class="topnav">
      <a href="/">Accueil</a>
      <a href="/#catalogue">Catalogue</a>
      <a href="/suivi" class="active">Suivre ma commande</a>
    </nav>
  </div>
</header>

<main class="container">
  <div class="page-head">
    <h1>Suivi de ma commande</h1>
    <p class="muted">Entrez le num&#233;ro de demande re&#231;u lors de votre commande.</p>
  </div>

  <form id="track-form" class="track-form card">
    <div class="form-row">
      <label for="ref-input">Num&#233;ro de demande</label>
      <input type="text" id="ref-input" name="reference" placeholder="Ex : CMD-260927-75D3A8" autocomplete="off">
    </div>
    <button type="submit" class="btn btn-primary">Rechercher ma commande</button>
    <p id="track-error" class="alert hidden"></p>
  </form>

  <section id="track-result" class="hidden">
    <div class="card track-header">
      <div class="track-header-left">
        <span class="muted small">Num&#233;ro de demande</span>
        <strong id="track-ref"></strong>
        <span class="muted small" id="track-date"></span>
      </div>
      <span class="status-badge" id="track-status-badge"></span>
    </div>

    <div class="card">
      <h2 class="track-section-title">Progression</h2>
      <div id="timeline" class="timeline"></div>
      <p id="track-refused" class="alert alert-danger hidden">
        Votre demande a &#233;t&#233; refus&#233;e. Contactez la pharmacie pour plus d&apos;informations.
      </p>
    </div>

    <div class="card">
      <h2 class="track-section-title">D&#233;tail de la commande</h2>
      <dl id="track-summary" class="summary"></dl>
    </div>

    <div class="track-actions">
      <button type="button" class="btn btn-ghost" id="track-refresh">Actualiser</button>
      <a class="btn btn-ghost" href="/">Retour &#224; l&apos;accueil</a>
    </div>
    <p class="muted small" id="track-last-refresh"></p>
  </section>
</main>

<script src="/static/suivi.js"></script>
</body>
</html>
'''
(STATIC / "suivi.html").write_text(html, encoding="utf-8")
print("[OK] static/suivi.html")

# =================================================================
# 3) static/suivi.css
# =================================================================
css = r'''/* Suivi de commande */

.track-form{
  max-width:520px;
  display:flex;flex-direction:column;gap:14px;margin-bottom:22px;
}
.track-form input{
  padding:12px 14px;border:1px solid var(--line);border-radius:11px;
  font-family:Consolas,monospace;font-size:15px;letter-spacing:.05em;
  text-transform:uppercase;background:var(--white);color:var(--ink);
  outline:none;width:100%;
}
.track-form input:focus{border-color:var(--green)}

.track-header{
  display:flex;justify-content:space-between;align-items:center;gap:14px;
  flex-wrap:wrap;margin-bottom:14px;
}
.track-header-left{
  display:flex;flex-direction:column;gap:2px;
}
.track-header-left strong{
  font-size:22px;letter-spacing:.05em;color:var(--green-dark);
  font-family:Consolas,monospace;
}

.track-section-title{
  font-size:14px;text-transform:uppercase;letter-spacing:.06em;
  color:var(--muted);margin:0 0 16px;font-weight:800;
}

.status-badge{
  font-size:11px;font-weight:800;padding:6px 12px;border-radius:999px;
  text-transform:uppercase;letter-spacing:.05em;
}
.status-en_attente{background:#fff4e0;color:#b26b00}
.status-confirmee{background:#e3f0ff;color:#1b5aae}
.status-en_preparation{background:#ede0ff;color:#6335b8}
.status-prete{background:#e3f7ee;color:#0a7a5a}
.status-terminee{background:#e6e9ec;color:#4b5563}
.status-refusee{background:#fdecec;color:#b23c3c}

/* --- Timeline verticale --- */
.timeline{
  display:flex;flex-direction:column;gap:0;
  padding:4px 0;
}
.tl-step{
  display:flex;gap:14px;position:relative;
  padding-bottom:22px;
}
.tl-step:last-child{padding-bottom:0}
.tl-step::before{
  content:"";
  position:absolute;
  left:15px;top:32px;bottom:0;
  width:2px;background:var(--line);
}
.tl-step:last-child::before{display:none}
.tl-step.done::before{background:var(--green)}
.tl-step.current::before{background:linear-gradient(var(--green),var(--line))}

.tl-dot{
  width:32px;height:32px;border-radius:50%;
  background:var(--white);border:2px solid var(--line);
  display:flex;align-items:center;justify-content:center;
  font-size:14px;font-weight:800;color:var(--muted);
  flex-shrink:0;z-index:1;
}
.tl-step.done .tl-dot{
  background:var(--green);border-color:var(--green);color:#fff;
}
.tl-step.current .tl-dot{
  background:var(--white);border-color:var(--green);
  color:var(--green);box-shadow:0 0 0 4px var(--green-soft);
}

.tl-info{display:flex;flex-direction:column;gap:2px;padding-top:5px}
.tl-label{font-weight:700;font-size:14px;color:var(--ink)}
.tl-step:not(.done):not(.current) .tl-label{color:var(--muted);font-weight:600}
.tl-hint{font-size:12px;color:var(--muted)}

.track-actions{
  display:flex;gap:10px;flex-wrap:wrap;margin-top:16px;
}

.alert-danger{background:#fdecec;color:#b23c3c;border:1px solid #f6d2d2}

@media (max-width:600px){
  .track-header{flex-direction:column;align-items:flex-start}
  .track-header-left strong{font-size:18px}
}
'''
(STATIC / "suivi.css").write_text(css, encoding="utf-8")
print("[OK] static/suivi.css")

# =================================================================
# 4) static/suivi.js
# =================================================================
js = r'''var API = "/api";

var STATUS_ORDER = ["en_attente", "confirmee", "en_preparation", "prete", "terminee"];

var STATUS_INFO = {
  en_attente:      { label: "En attente",     hint: "Votre demande a bien ete recue. La pharmacie va l'examiner." },
  confirmee:       { label: "Confirmee",      hint: "La pharmacie a valide votre demande." },
  en_preparation:  { label: "En preparation", hint: "Votre commande est en cours de preparation." },
  prete:           { label: "Prete",          hint: "Votre commande est prete. Retrait ou livraison imminente." },
  terminee:        { label: "Terminee",       hint: "Votre commande a ete remise ou livree." },
  refusee:         { label: "Refusee",        hint: "La pharmacie n'a pas pu donner suite a cette demande." }
};

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

function formatDate(iso) {
  if (!iso) return "";
  var d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  var pad = function(n) { return n < 10 ? "0" + n : "" + n; };
  return pad(d.getDate()) + "/" + pad(d.getMonth()+1) + "/" + d.getFullYear()
    + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
}

function showError(msg) {
  var box = $("#track-error");
  box.textContent = msg;
  box.classList.remove("hidden");
}

function clearError() {
  $("#track-error").classList.add("hidden");
  $("#track-error").textContent = "";
}

function loadOrder(reference) {
  return fetch(API + "/orders/" + encodeURIComponent(reference)).then(function(r) {
    if (r.status === 404) throw new Error("Aucune commande trouvee avec ce numero.");
    if (!r.ok) throw new Error("Erreur serveur.");
    return r.json();
  });
}

function renderStatusBadge(status) {
  var badge = $("#track-status-badge");
  badge.className = "status-badge status-" + status;
  badge.textContent = (STATUS_INFO[status] && STATUS_INFO[status].label) || status;
}

function renderTimeline(currentStatus) {
  var box = $("#timeline");
  box.innerHTML = "";
  var refused = currentStatus === "refusee";
  var currentIdx = STATUS_ORDER.indexOf(currentStatus);

  STATUS_ORDER.forEach(function(status, idx) {
    var step = el("div", "tl-step");
    var done = !refused && idx < currentIdx;
    var current = !refused && idx === currentIdx;
    if (done) step.classList.add("done");
    if (current) step.classList.add("current");

    var dot = el("div", "tl-dot");
    if (done) dot.textContent = "\u2713";
    else dot.textContent = String(idx + 1);

    var info = el("div", "tl-info");
    info.appendChild(el("div", "tl-label", STATUS_INFO[status].label));
    if (current) info.appendChild(el("div", "tl-hint", STATUS_INFO[status].hint));
    step.appendChild(dot);
    step.appendChild(info);
    box.appendChild(step);
  });

  if (refused) {
    $("#track-refused").classList.remove("hidden");
  } else {
    $("#track-refused").classList.add("hidden");
  }
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
}

function renderOrder(o) {
  $("#track-result").classList.remove("hidden");
  $("#track-ref").textContent = o.reference;
  $("#track-date").textContent = "Creee le " + formatDate(o.created_at);
  renderStatusBadge(o.status);
  renderTimeline(o.status);
  renderSummary(o);
  $("#ref-input").value = o.reference;

  var now = new Date();
  var pad = function(n) { return n < 10 ? "0" + n : "" + n; };
  $("#track-last-refresh").textContent =
    "Derniere actualisation : " + pad(now.getHours()) + ":" + pad(now.getMinutes()) + ":" + pad(now.getSeconds());
}

function fetchAndRender(reference) {
  clearError();
  return loadOrder(reference).then(function(o) {
    renderOrder(o);
    return o;
  }).catch(function(err) {
    $("#track-result").classList.add("hidden");
    showError(err.message || "Erreur");
    throw err;
  });
}

function setUrlRef(ref) {
  try {
    var url = new URL(window.location.href);
    if (ref) url.searchParams.set("ref", ref);
    else url.searchParams.delete("ref");
    window.history.replaceState({}, "", url.toString());
  } catch (e) {}
}

function startAutoRefresh(reference) {
  if (trackTimer) clearInterval(trackTimer);
  trackTimer = setInterval(function() {
    fetchAndRender(reference).catch(function() {});
  }, 30000);
}

function init() {
  var form = $("#track-form");
  var input = $("#ref-input");
  var refreshBtn = $("#track-refresh");

  form.addEventListener("submit", function(ev) {
    ev.preventDefault();
    var ref = input.value.trim().toUpperCase();
    if (!ref) { showError("Entrez un numero de demande."); return; }
    setUrlRef(ref);
    fetchAndRender(ref).then(function() {
      startAutoRefresh(ref);
    }).catch(function() {});
  });

  refreshBtn.addEventListener("click", function() {
    var ref = input.value.trim().toUpperCase();
    if (!ref) return;
    fetchAndRender(ref).catch(function() {});
  });

  // Si ?ref=XXX dans l'URL
  var params = new URLSearchParams(window.location.search);
  var refParam = params.get("ref");
  if (refParam) {
    input.value = refParam.toUpperCase();
    fetchAndRender(refParam.toUpperCase()).then(function() {
      startAutoRefresh(refParam.toUpperCase());
    }).catch(function() {});
  }
}

document.addEventListener("DOMContentLoaded", init);
'''
(STATIC / "suivi.js").write_text(js, encoding="utf-8")
print("[OK] static/suivi.js")

# =================================================================
# 5) index.html : lien "Suivre ma commande" dans la nav
# =================================================================
html = INDEX.read_text(encoding="utf-8")

old_nav = '''      <a href="#demande" data-nav="order">Ma demande</a>'''
new_nav = '''      <a href="#demande" data-nav="order">Ma demande</a>
      <a href="/suivi">Suivre ma commande</a>'''
if old_nav in html and "/suivi" not in html:
    html = html.replace(old_nav, new_nav, 1)
    INDEX.write_text(html, encoding="utf-8")
    print("[OK] index.html -> lien Suivre ma commande")
elif "/suivi" in html:
    print("[i] index.html -> lien deja present")
else:
    print("[!] anchor nav introuvable")

# =================================================================
# 6) app.js : bouton "Suivre ma commande" sur la confirmation
# =================================================================
js2 = APPJS.read_text(encoding="utf-8")

old_actions = '''  var actions = el("div", "confirm-actions");
  var b1 = el("button", "btn btn-primary", "Retour au catalogue");
  b1.addEventListener("click", function () { goCatalog(""); });
  var b2 = el("button", "btn btn-ghost", "Nouvelle demande");
  b2.addEventListener("click", function () { goOrder(null); });
  actions.appendChild(b1);
  actions.appendChild(b2);
  box.appendChild(actions);'''

new_actions = '''  var actions = el("div", "confirm-actions");
  var bTrack = el("a", "btn btn-primary", "Suivre ma commande");
  bTrack.href = "/suivi?ref=" + encodeURIComponent(o.reference);
  var b1 = el("button", "btn btn-ghost", "Retour au catalogue");
  b1.addEventListener("click", function () { goCatalog(""); });
  var b2 = el("button", "btn btn-ghost", "Nouvelle demande");
  b2.addEventListener("click", function () { goOrder(null); });
  actions.appendChild(bTrack);
  actions.appendChild(b1);
  actions.appendChild(b2);
  box.appendChild(actions);'''

if old_actions in js2 and "Suivre ma commande" not in js2:
    js2 = js2.replace(old_actions, new_actions, 1)
    APPJS.write_text(js2, encoding="utf-8")
    print("[OK] app.js -> bouton Suivre ma commande sur confirmation")
elif "Suivre ma commande" in js2:
    print("[i] app.js -> bouton deja present")
else:
    print("[!] bloc confirm-actions introuvable dans app.js")

# =================================================================
# 7) style.css : petites aides pour le lien nav actif
# =================================================================
css2 = STYLECSS.read_text(encoding="utf-8")
if ".topnav a.active" not in css2:
    css2 += '''

/* --- Lien nav actif --- */
.topnav a.active{background:var(--green-soft);color:var(--green-dark)}
'''
    STYLECSS.write_text(css2, encoding="utf-8")
    print("[OK] style.css -> style lien nav actif")

print()
print("=======================================================")
print("Suivi patient installe.")
print()
print("Redemarre le serveur (Ctrl+C puis python main.py)")
print("puis Ctrl+Shift+R dans le navigateur.")
print()
print("URLs :")
print("  /suivi                     -> formulaire de suivi")
print("  /suivi?ref=CMD-XXX-YYY     -> suivi direct")
print("=======================================================")