from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
MAIN = BASE / "main.py"

# ==============================================================
# 1) PATCH main.py
# ==============================================================
src = MAIN.read_text(encoding="utf-8")
shutil.copy(MAIN, MAIN.with_suffix(".py.bak"))
print("[OK] sauvegarde ->", MAIN.with_suffix(".py.bak").name)

if "from pydantic import BaseModel" not in src:
    src = src.replace(
        "from fastapi.staticfiles import StaticFiles",
        "from fastapi.staticfiles import StaticFiles\nfrom pydantic import BaseModel",
        1,
    )
    print("[OK] main.py -> import BaseModel")

addition = '''# ============================================================
# V2.1 - Dashboard pharmacien
# ============================================================

VALID_STATUSES = {"en_attente", "confirmee", "en_preparation", "prete", "terminee", "refusee"}


class StatusUpdate(BaseModel):
    status: str


@app.get("/pharmacien")
def pharmacien_page():
    return FileResponse(STATIC_DIR / "pharmacien.html")


@app.patch("/api/orders/{reference}/status")
def update_order_status(reference: str, payload: StatusUpdate):
    new_status = payload.status.strip().lower()
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Statut invalide")
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE reference = ?", (reference,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Demande introuvable")
    conn.execute("UPDATE orders SET status = ? WHERE reference = ?", (new_status, reference))
    conn.commit()
    updated = conn.execute("SELECT * FROM orders WHERE reference = ?", (reference,)).fetchone()
    conn.close()
    return row_to_dict(updated)


'''

if "/pharmacien" not in src:
    marker = "\ninit_db()\n"
    if marker in src:
        src = src.replace(marker, "\n" + addition + "init_db()\n", 1)
        print("[OK] main.py -> routes V2.1 ajoutees")
    else:
        print("[!] marker 'init_db()' introuvable, patch annule")
else:
    print("[i] main.py deja patche V2.1")

MAIN.write_text(src, encoding="utf-8")

# ==============================================================
# 2) static/pharmacien.html
# ==============================================================
html = r'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Espace pharmacien - Demandes</title>
<link rel="stylesheet" href="/static/style.css">
<link rel="stylesheet" href="/static/pharmacien.css">
</head>
<body>

<header class="topbar">
  <div class="container topbar-inner">
    <a class="brand" href="/pharmacien">
      <span class="brand-logo">+</span>
      <span class="brand-text">
        <strong>Pharmacie du Parc</strong>
        <small>Espace pharmacien</small>
      </span>
    </a>
    <nav class="topnav">
      <a href="/" target="_blank" rel="noopener">Site patient</a>
      <a href="/docs" target="_blank" rel="noopener">API</a>
    </nav>
  </div>
</header>

<main class="container">
  <div class="page-head">
    <h1>Demandes recues</h1>
    <p class="muted" id="last-refresh">Chargement...</p>
  </div>

  <section class="stats">
    <div class="stat-card">
      <span class="stat-value" id="stat-pending">0</span>
      <span class="stat-label">En attente</span>
    </div>
    <div class="stat-card">
      <span class="stat-value" id="stat-preparing">0</span>
      <span class="stat-label">En preparation</span>
    </div>
    <div class="stat-card">
      <span class="stat-value" id="stat-ready">0</span>
      <span class="stat-label">Pretes</span>
    </div>
    <div class="stat-card">
      <span class="stat-value" id="stat-total">0</span>
      <span class="stat-label">Total</span>
    </div>
  </section>

  <div class="toolbar-row">
    <div id="status-filters" class="chips"></div>
    <button class="btn btn-ghost" id="refresh-btn" type="button">Actualiser</button>
  </div>

  <div id="orders-grid" class="orders-grid"></div>
  <p id="orders-empty" class="empty hidden">Aucune demande pour le moment.</p>
</main>

<script src="/static/pharmacien.js"></script>
</body>
</html>
'''
(STATIC / "pharmacien.html").write_text(html, encoding="utf-8")
print("[OK] static/pharmacien.html")

# ==============================================================
# 3) static/pharmacien.css
# ==============================================================
css = r'''/* V2.1 - Dashboard pharmacien */

.stats{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:14px;margin-bottom:22px;
}
.stat-card{
  background:var(--white);border:1px solid var(--line);
  border-radius:var(--radius);padding:18px;
  display:flex;flex-direction:column;gap:6px;
  box-shadow:var(--shadow);
}
.stat-value{font-size:30px;font-weight:800;color:var(--green-dark);line-height:1}
.stat-label{
  font-size:12px;color:var(--muted);font-weight:700;
  text-transform:uppercase;letter-spacing:.06em;
}

.toolbar-row{
  display:flex;justify-content:space-between;align-items:center;
  gap:12px;margin-bottom:18px;flex-wrap:wrap;
}

.orders-grid{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(340px,1fr));
  gap:16px;
}

.order-card{
  background:var(--white);border:1px solid var(--line);
  border-radius:var(--radius);padding:18px;
  display:flex;flex-direction:column;gap:12px;
  box-shadow:var(--shadow);
}

.order-head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.order-ref{font-weight:800;font-size:15px;letter-spacing:.03em}
.order-date{font-size:12px;color:var(--muted);margin-top:2px}

.status-badge{
  font-size:11px;font-weight:800;padding:5px 10px;border-radius:999px;
  text-transform:uppercase;letter-spacing:.05em;white-space:nowrap;
}
.status-en_attente{background:#fff4e0;color:#b26b00}
.status-confirmee{background:#e3f0ff;color:#1b5aae}
.status-en_preparation{background:#ede0ff;color:#6335b8}
.status-prete{background:#e3f7ee;color:#0a7a5a}
.status-terminee{background:#e6e9ec;color:#4b5563}
.status-refusee{background:#fdecec;color:#b23c3c}

.order-body{
  display:grid;grid-template-columns:auto 1fr;
  gap:6px 14px;font-size:14px;margin:0;
}
.order-body dt{color:var(--muted)}
.order-body dd{margin:0;font-weight:600;word-break:break-word}

.order-prescription{
  display:flex;align-items:center;gap:8px;
  padding-top:4px;border-top:1px dashed var(--line);
  margin-top:2px;
}
.order-prescription .btn{padding:7px 12px;font-size:13px}

.order-actions{
  display:flex;gap:8px;flex-wrap:wrap;
  margin-top:auto;padding-top:12px;border-top:1px solid var(--line);
}
.order-actions .btn{padding:8px 14px;font-size:13px}

.btn-danger{background:#b23c3c;color:#fff}
.btn-danger:hover{background:#8f2f2f}

@media (max-width:600px){
  .orders-grid{grid-template-columns:1fr}
  .order-body{grid-template-columns:1fr;gap:2px 0}
  .order-body dt{margin-top:6px;font-size:12px}
}
'''
(STATIC / "pharmacien.css").write_text(css, encoding="utf-8")
print("[OK] static/pharmacien.css")

# ==============================================================
# 4) static/pharmacien.js
# ==============================================================
js = r'''var API = "/api";

var STATUS_LABELS = {
  en_attente: "En attente",
  confirmee: "Confirmee",
  en_preparation: "En preparation",
  prete: "Prete",
  terminee: "Terminee",
  refusee: "Refusee"
};

var NEXT_ACTIONS = {
  en_attente: [
    { label: "Confirmer", next: "confirmee", kind: "primary" },
    { label: "Refuser", next: "refusee", kind: "danger" }
  ],
  confirmee: [
    { label: "Preparer", next: "en_preparation", kind: "primary" },
    { label: "Refuser", next: "refusee", kind: "danger" }
  ],
  en_preparation: [
    { label: "Prete", next: "prete", kind: "primary" },
    { label: "Refuser", next: "refusee", kind: "danger" }
  ],
  prete: [
    { label: "Terminee", next: "terminee", kind: "primary" }
  ],
  terminee: [],
  refusee: []
};

var state = { orders: [], filter: "" };

function $(sel){ return document.querySelector(sel); }

function el(tag, cls, txt){
  var n = document.createElement(tag);
  if (cls) n.className = cls;
  if (txt !== undefined && txt !== null) n.textContent = txt;
  return n;
}

function formatDate(iso){
  if (!iso) return "";
  var d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  var pad = function(n){ return n < 10 ? "0" + n : "" + n; };
  return pad(d.getDate()) + "/" + pad(d.getMonth()+1) + "/" + d.getFullYear()
    + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
}

function loadOrders(){
  return fetch(API + "/orders").then(function(r){
    if (!r.ok) throw new Error("Erreur serveur");
    return r.json();
  }).then(function(list){
    state.orders = list;
    render();
  });
}

function changeStatus(reference, newStatus){
  return fetch(API + "/orders/" + encodeURIComponent(reference) + "/status", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: newStatus })
  }).then(function(r){
    return r.json().then(function(body){
      if (!r.ok){
        var msg = typeof body.detail === "string" ? body.detail : "Mise a jour impossible";
        throw new Error(msg);
      }
      return body;
    });
  });
}

function computeStats(){
  var s = { en_attente:0, en_preparation:0, prete:0, total: state.orders.length };
  state.orders.forEach(function(o){
    if (o.status === "en_attente") s.en_attente++;
    else if (o.status === "en_preparation") s.en_preparation++;
    else if (o.status === "prete") s.prete++;
  });
  return s;
}

function renderStats(){
  var s = computeStats();
  $("#stat-pending").textContent = s.en_attente;
  $("#stat-preparing").textContent = s.en_preparation;
  $("#stat-ready").textContent = s.prete;
  $("#stat-total").textContent = s.total;
}

function renderFilters(){
  var box = $("#status-filters");
  box.innerHTML = "";
  var options = [["", "Toutes"]];
  Object.keys(STATUS_LABELS).forEach(function(k){
    options.push([k, STATUS_LABELS[k]]);
  });
  options.forEach(function(pair){
    var active = state.filter === pair[0] ? " chip-active" : "";
    var chip = el("button", "chip" + active, pair[1]);
    chip.type = "button";
    chip.addEventListener("click", function(){
      state.filter = pair[0];
      render();
    });
    box.appendChild(chip);
  });
}

function actionButton(label, nextStatus, kind, ref){
  var cls = "btn ";
  if (kind === "danger") cls += "btn-danger";
  else if (kind === "primary") cls += "btn-primary";
  else cls += "btn-ghost";
  var btn = el("button", cls, label);
  btn.type = "button";
  btn.addEventListener("click", function(){
    btn.disabled = true;
    btn.textContent = "...";
    changeStatus(ref, nextStatus).then(function(){
      return loadOrders();
    }).catch(function(err){
      alert(err.message || "Erreur");
      btn.disabled = false;
      btn.textContent = label;
    });
  });
  return btn;
}

function orderCard(o){
  var card = el("article", "order-card");

  var head = el("div", "order-head");
  var left = el("div");
  left.appendChild(el("div", "order-ref", o.reference));
  left.appendChild(el("div", "order-date", formatDate(o.created_at)));
  var badge = el("span", "status-badge status-" + o.status,
                 STATUS_LABELS[o.status] || o.status);
  head.appendChild(left);
  head.appendChild(badge);
  card.appendChild(head);

  var dl = el("dl", "order-body");
  function row(label, value){
    dl.appendChild(el("dt", null, label));
    dl.appendChild(el("dd", null, value));
  }
  row("Client", o.customer_name);
  row("Telephone", o.phone);
  row("Produit", o.product_name);
  row("Quantite", o.quantity);
  row("Mode", o.delivery_mode === "livraison" ? "Livraison" : "Retrait");
  if (o.delivery_mode === "livraison" && o.address) row("Adresse", o.address);
  card.appendChild(dl);

  var presc = el("div", "order-prescription");
  if (o.prescription_file){
    var link = el("a", "btn btn-ghost", "Voir l'ordonnance");
    link.href = "/uploads/" + o.prescription_file;
    link.target = "_blank";
    link.rel = "noopener";
    presc.appendChild(link);
  } else {
    presc.appendChild(el("span", "muted small", "Aucune ordonnance jointe"));
  }
  card.appendChild(presc);

  var actions = NEXT_ACTIONS[o.status] || [];
  if (actions.length > 0){
    var actBox = el("div", "order-actions");
    actions.forEach(function(a){
      actBox.appendChild(actionButton(a.label, a.next, a.kind, o.reference));
    });
    card.appendChild(actBox);
  }

  return card;
}

function render(){
  renderStats();
  renderFilters();
  var grid = $("#orders-grid");
  grid.innerHTML = "";
  var empty = $("#orders-empty");
  var list = state.orders;
  if (state.filter){
    list = list.filter(function(o){ return o.status === state.filter; });
  }
  if (list.length === 0){
    empty.classList.remove("hidden");
  } else {
    empty.classList.add("hidden");
    list.forEach(function(o){ grid.appendChild(orderCard(o)); });
  }
}

function setLastRefresh(){
  var now = new Date();
  var pad = function(n){ return n < 10 ? "0" + n : "" + n; };
  $("#last-refresh").textContent =
    "Derniere actualisation : "
    + pad(now.getHours()) + ":" + pad(now.getMinutes()) + ":" + pad(now.getSeconds());
}

function refresh(){
  return loadOrders().then(setLastRefresh);
}

function init(){
  $("#refresh-btn").addEventListener("click", function(){
    refresh().catch(function(){ alert("Actualisation impossible"); });
  });
  refresh().catch(function(){});
  setInterval(function(){ refresh().catch(function(){}); }, 30000);
}

document.addEventListener("DOMContentLoaded", init);
'''
(STATIC / "pharmacien.js").write_text(js, encoding="utf-8")
print("[OK] static/pharmacien.js")

print()
print("V2.1 installee.")
print("Redemarre le serveur (Ctrl+C puis python main.py), puis ouvre :")
print("   http://127.0.0.1:8000/pharmacien")