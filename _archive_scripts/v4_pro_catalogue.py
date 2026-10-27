"""
v4_pro_catalogue.py
Catalogue B2B mobile-first : recherche, catégories, filtres, cartes produit,
badge flottant "Ma demande", gestion indisponibles, besoin personnalisé.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
MAIN = BASE / "main.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_pro_catalogue_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAIN, backup / "main.py")
for f in ("professional_catalogue.html", "professional.js"):
    p = STATIC / f
    if p.exists():
        shutil.copy2(p, backup / f)
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. Page catalogue B2B
# ============================================================
CAT_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Catalogue - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
:root{
  --blue:#1a4a7f;
  --blue-dark:#123258;
  --blue-soft:#eaf1f9;
  --green:#10a37f;
  --green-dark:#0a7a5a;
  --green-soft:#e6f7f1;
  --ink:#0f172a;
  --muted:#64748b;
  --line:#e6ebf1;
  --bg:#f7fafc;
  --warn:#f59e0b;
  --warn-soft:#fff7e6;
  --danger:#dc2626;
  --danger-soft:#fee2e2;
  --radius:14px;
  --shadow:0 1px 3px rgba(15,23,42,.06), 0 1px 2px rgba(15,23,42,.04);
  --shadow-card:0 2px 8px rgba(15,23,42,.06);
}
*,*::before,*::after{box-sizing:border-box}
html,body{overflow-x:clip;margin:0;padding:0}
body{
  font-family:-apple-system,"Segoe UI",system-ui,sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.5;font-size:15px;
  -webkit-font-smoothing:antialiased;padding-bottom:92px;
}
a{color:inherit;text-decoration:none}
button{font-family:inherit;cursor:pointer}
img{max-width:100%;display:block}
.hidden{display:none !important}

/* ---- Header ---- */
.cat-header{
  background:#fff;border-bottom:1px solid var(--line);
  position:sticky;top:0;z-index:50;
}
.cat-header-top{
  max-width:900px;margin:0 auto;padding:12px 16px 8px;
  display:flex;align-items:center;gap:12px;
}
.cat-back{
  width:36px;height:36px;border-radius:10px;
  border:1px solid var(--line);background:#fff;
  display:flex;align-items:center;justify-content:center;
  color:var(--ink);font-size:18px;text-decoration:none;
}
.cat-brand{
  display:flex;align-items:center;gap:8px;font-weight:800;font-size:15px;
}
.cat-brand-mark{
  width:30px;height:30px;border-radius:8px;
  background:linear-gradient(135deg,var(--blue),#2a6ba8);color:#fff;
  display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:800;
}
.cat-bell{
  margin-left:auto;width:36px;height:36px;border-radius:10px;
  border:1px solid var(--line);background:#fff;
  display:flex;align-items:center;justify-content:center;
  color:var(--ink);font-size:16px;position:relative;
}
.cat-bell-badge{
  position:absolute;top:-3px;right:-3px;background:var(--green);
  color:#fff;font-size:9px;font-weight:800;min-width:16px;
  height:16px;padding:0 4px;border-radius:999px;
  display:flex;align-items:center;justify-content:center;
}
.cat-search-wrap{
  max-width:900px;margin:0 auto;padding:0 16px 12px;
}
.cat-search{
  width:100%;padding:14px 16px 14px 44px;
  border:2px solid var(--line);border-radius:14px;
  font-family:inherit;font-size:16px;outline:none;background:#fff;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='11' cy='11' r='8'/><path d='m21 21-4.35-4.35'/></svg>");
  background-repeat:no-repeat;background-position:14px 50%;
  transition:.15s;
}
.cat-search:focus{border-color:var(--blue);box-shadow:0 0 0 4px var(--blue-soft)}
.cat-search::placeholder{color:#94a3b8}

/* ---- Catégories horizontales ---- */
.cat-cats-strip{
  background:#fff;border-bottom:1px solid var(--line);
  position:sticky;top:105px;z-index:40;
}
.cat-cats-scroll{
  max-width:900px;margin:0 auto;
  padding:10px 16px;display:flex;gap:8px;overflow-x:auto;
  scrollbar-width:none;
}
.cat-cats-scroll::-webkit-scrollbar{display:none}
.cat-chip{
  flex-shrink:0;padding:8px 16px;border-radius:999px;
  border:1px solid var(--line);background:#fff;color:var(--ink);
  font-size:13px;font-weight:700;white-space:nowrap;
  transition:.15s;cursor:pointer;
}
.cat-chip:hover{border-color:var(--blue);color:var(--blue)}
.cat-chip.active{
  background:var(--blue);border-color:var(--blue);color:#fff;
}

/* ---- Barre résultat + filtres ---- */
.cat-toolbar{
  max-width:900px;margin:0 auto;padding:14px 16px 8px;
  display:flex;align-items:center;justify-content:space-between;gap:12px;
  flex-wrap:wrap;
}
.cat-count{font-size:13px;color:var(--muted);font-weight:600}
.cat-count strong{color:var(--ink)}
.cat-filter-btn{
  padding:8px 14px;border:1px solid var(--line);background:#fff;
  border-radius:10px;font-size:13px;font-weight:700;color:var(--ink);
  display:flex;align-items:center;gap:6px;
}
.cat-filter-btn:hover{border-color:var(--blue);color:var(--blue)}
.cat-filter-btn.active{background:var(--blue);border-color:var(--blue);color:#fff}

/* ---- Filtres panneau ---- */
.cat-filters{
  max-width:900px;margin:0 auto 10px;padding:0 16px;
}
.cat-filters-inner{
  background:#fff;border:1px solid var(--line);border-radius:12px;
  padding:14px 16px;
}
.cat-filter-group{margin-bottom:12px}
.cat-filter-group:last-child{margin-bottom:0}
.cat-filter-group h4{
  font-size:11px;text-transform:uppercase;letter-spacing:.06em;
  color:var(--muted);margin:0 0 8px;font-weight:800;
}
.cat-filter-opts{display:flex;flex-wrap:wrap;gap:6px}
.cat-filter-opt{
  padding:6px 12px;border-radius:999px;border:1px solid var(--line);
  background:#fff;font-size:12px;font-weight:600;color:var(--ink);cursor:pointer;
}
.cat-filter-opt:hover{border-color:var(--blue)}
.cat-filter-opt.active{background:var(--blue-soft);border-color:var(--blue);color:var(--blue)}

/* ---- Grille produits ---- */
.cat-grid{
  max-width:900px;margin:0 auto;padding:0 16px;
  display:grid;gap:12px;
  grid-template-columns:repeat(2,1fr);
}
@media(min-width:640px){
  .cat-grid{grid-template-columns:repeat(3,1fr)}
}
@media(min-width:900px){
  .cat-grid{grid-template-columns:repeat(4,1fr)}
}

.cat-card{
  background:#fff;border:1px solid var(--line);border-radius:var(--radius);
  overflow:hidden;display:flex;flex-direction:column;
  box-shadow:var(--shadow);transition:.15s;
}
.cat-card:hover{box-shadow:var(--shadow-card);transform:translateY(-1px)}
.cat-card-img{
  aspect-ratio:1;
  background:linear-gradient(135deg,#f8fafc,#eef2f7);
  display:flex;align-items:center;justify-content:center;
  overflow:hidden;padding:12px;cursor:pointer;
}
.cat-card-img img{width:100%;height:100%;object-fit:contain}
.cat-card-img-placeholder{
  font-size:34px;font-weight:800;color:var(--blue);opacity:.35;
}
.cat-card-body{
  padding:10px 12px 12px;display:flex;flex-direction:column;gap:6px;flex:1;
}
.cat-card-name{
  font-size:13px;font-weight:800;line-height:1.25;
  margin:0;color:var(--ink);
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
  overflow:hidden;min-height:32px;
}
.cat-card-meta{
  font-size:11px;color:var(--muted);line-height:1.35;
  display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;
  overflow:hidden;
}
.cat-badge{
  display:inline-flex;align-items:center;gap:4px;
  font-size:10px;font-weight:800;padding:3px 8px;border-radius:999px;
  text-transform:uppercase;letter-spacing:.04em;align-self:flex-start;
}
.cat-badge::before{
  content:"";width:6px;height:6px;border-radius:50%;background:currentColor;
}
.cat-badge.dispo{background:var(--green-soft);color:var(--green-dark)}
.cat-badge.limite{background:var(--warn-soft);color:#8a5a00}
.cat-badge.confirmer{background:var(--warn-soft);color:#8a5a00}
.cat-badge.indispo{background:var(--danger-soft);color:var(--danger)}

.cat-card-price{
  font-size:14px;font-weight:800;color:var(--ink);margin-top:2px;
}
.cat-card-price.confirm{color:var(--muted);font-weight:700;font-size:12px}

.cat-card-qty{
  display:flex;align-items:center;gap:0;margin-top:6px;
  border:1px solid var(--line);border-radius:10px;overflow:hidden;
}
.cat-card-qty button{
  width:32px;height:34px;border:0;background:#f8fafc;
  color:var(--ink);font-size:16px;font-weight:700;
}
.cat-card-qty button:hover{background:var(--blue-soft);color:var(--blue)}
.cat-card-qty input{
  flex:1;min-width:0;border:0;text-align:center;
  font-family:inherit;font-size:13px;font-weight:700;
  padding:8px 4px;outline:none;background:#fff;color:var(--ink);
}

.cat-card-add{
  margin-top:6px;padding:10px;border:0;border-radius:10px;
  background:var(--blue);color:#fff;font-size:12px;font-weight:800;
  display:flex;align-items:center;justify-content:center;gap:5px;
  transition:.15s;
}
.cat-card-add:hover{background:var(--blue-dark)}
.cat-card-add.done{background:var(--green);}

/* ---- Empty state ---- */
.cat-empty{
  max-width:900px;margin:40px auto;padding:0 16px;text-align:center;
}
.cat-empty-icon{font-size:48px;opacity:.3;margin-bottom:12px}
.cat-empty h3{font-size:16px;margin:0 0 6px}
.cat-empty p{font-size:14px;color:var(--muted);margin:0 0 18px}

/* ---- Besoin personnalisé ---- */
.cat-custom{
  max-width:900px;margin:24px auto 0;padding:0 16px;
}
.cat-custom-card{
  background:#fff;border:1px dashed var(--blue);
  border-radius:var(--radius);padding:18px;
  display:flex;flex-direction:column;gap:12px;
}
.cat-custom-card h3{
  margin:0;font-size:15px;font-weight:800;color:var(--ink);
  display:flex;align-items:center;gap:8px;
}
.cat-custom-card p{
  font-size:13px;color:var(--muted);margin:0;
}
.cat-custom-field{
  display:flex;flex-direction:column;gap:6px;
}
.cat-custom-field label{font-size:12px;font-weight:700;color:var(--ink)}
.cat-custom-field input, .cat-custom-field textarea{
  padding:12px 14px;border:1px solid var(--line);border-radius:10px;
  font-family:inherit;font-size:14px;outline:none;background:#fff;width:100%;
  resize:vertical;
}
.cat-custom-field input:focus, .cat-custom-field textarea:focus{border-color:var(--blue)}
.cat-custom-btn{
  padding:13px;border:0;border-radius:11px;
  background:var(--blue);color:#fff;font-weight:800;font-size:14px;
}
.cat-custom-btn:hover{background:var(--blue-dark)}

/* ---- Badge flottant "Ma demande" ---- */
.cat-float{
  position:fixed;bottom:16px;left:50%;transform:translateX(-50%);
  z-index:200;
  background:var(--ink);color:#fff;border-radius:999px;
  padding:12px 20px 12px 16px;
  display:flex;align-items:center;gap:10px;
  box-shadow:0 10px 30px rgba(15,23,42,.25);
  font-weight:800;font-size:14px;text-decoration:none;
  border:0;cursor:pointer;
  max-width:calc(100vw - 32px);
  transition:.15s;
}
.cat-float:hover{transform:translateX(-50%) translateY(-2px);box-shadow:0 14px 36px rgba(15,23,42,.3)}
.cat-float-icon{font-size:18px;line-height:1}
.cat-float-count{
  background:var(--green);color:#fff;font-size:11px;font-weight:800;
  min-width:22px;height:22px;padding:0 7px;border-radius:999px;
  display:flex;align-items:center;justify-content:center;
  margin-left:2px;
}
.cat-float.empty{background:#94a3b8;cursor:default;pointer-events:none}
.cat-float.empty:hover{transform:translateX(-50%)}

/* ---- Toast ---- */
.cat-toast{
  position:fixed;left:50%;bottom:84px;transform:translateX(-50%);
  background:var(--green-dark);color:#fff;padding:11px 18px;
  border-radius:12px;font-size:13px;font-weight:700;z-index:300;
  box-shadow:0 10px 30px rgba(0,0,0,.2);
  max-width:calc(100vw - 32px);text-align:center;
  animation:toastIn .2s ease;
}
@keyframes toastIn{from{opacity:0;transform:translateX(-50%) translateY(8px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}

/* ---- Détail produit (panneau plein écran) ---- */
.cat-detail{
  position:fixed;inset:0;background:#fff;z-index:500;
  display:flex;flex-direction:column;
  animation:slideUp .25s ease;
}
@keyframes slideUp{from{transform:translateY(40px);opacity:.5}to{transform:translateY(0);opacity:1}}
.cat-detail.hidden{display:none}
.cat-detail-head{
  padding:12px 16px;border-bottom:1px solid var(--line);
  display:flex;align-items:center;gap:12px;background:#fff;
  position:sticky;top:0;z-index:10;
}
.cat-detail-close{
  width:36px;height:36px;border-radius:10px;border:1px solid var(--line);
  background:#fff;font-size:18px;color:var(--ink);
  display:flex;align-items:center;justify-content:center;
}
.cat-detail-body{flex:1;overflow-y:auto;padding-bottom:100px}
.cat-detail-img{
  aspect-ratio:1;background:linear-gradient(135deg,#f8fafc,#eef2f7);
  display:flex;align-items:center;justify-content:center;padding:24px;
}
.cat-detail-img img{max-width:100%;max-height:100%;object-fit:contain}
.cat-detail-img-placeholder{
  font-size:80px;font-weight:800;color:var(--blue);opacity:.3;
}
.cat-detail-info{padding:20px 20px 0}
.cat-detail-info h1{font-size:20px;margin:0 0 6px;line-height:1.2}
.cat-detail-meta{font-size:14px;color:var(--muted);margin:0 0 14px}
.cat-detail-price{font-size:22px;font-weight:800;color:var(--ink);margin:12px 0}
.cat-detail-price.confirm{font-size:15px;color:var(--muted);font-weight:700}
.cat-detail-section{margin-top:18px}
.cat-detail-section h4{
  font-size:11px;text-transform:uppercase;letter-spacing:.06em;
  color:var(--muted);margin:0 0 6px;font-weight:800;
}
.cat-detail-section p{font-size:14px;color:var(--ink);margin:0;line-height:1.55}
.cat-detail-presc{
  background:var(--warn-soft);border:1px solid #f2d9b3;
  border-radius:10px;padding:10px 12px;margin-top:14px;
  font-size:13px;color:#8a5a00;font-weight:600;
}
.cat-detail-actions{
  position:fixed;bottom:0;left:0;right:0;
  background:#fff;border-top:1px solid var(--line);
  padding:12px 16px calc(12px + env(safe-area-inset-bottom));
  display:flex;gap:10px;align-items:center;
  z-index:510;
}
.cat-detail-qty{
  display:flex;align-items:center;gap:0;border:1px solid var(--line);
  border-radius:11px;overflow:hidden;
}
.cat-detail-qty button{
  width:40px;height:46px;border:0;background:#f8fafc;
  color:var(--ink);font-size:18px;font-weight:700;
}
.cat-detail-qty button:hover{background:var(--blue-soft);color:var(--blue)}
.cat-detail-qty input{
  width:50px;border:0;text-align:center;
  font-family:inherit;font-size:15px;font-weight:700;
  padding:11px 4px;outline:none;color:var(--ink);
}
.cat-detail-add{
  flex:1;padding:14px;border:0;border-radius:11px;
  background:var(--blue);color:#fff;font-weight:800;font-size:14px;
}
.cat-detail-add:hover{background:var(--blue-dark)}
</style>
</head>
<body>

<header class="cat-header">
  <div class="cat-header-top">
    <a class="cat-back" href="/professionnel" aria-label="Retour">&#8592;</a>
    <div class="cat-brand">
      <span class="cat-brand-mark">+</span>
      Elokinab
    </div>
    <button class="cat-bell" type="button" id="bell" aria-label="Notifications">
      &#128276;
      <span class="cat-bell-badge hidden" id="bell-badge">0</span>
    </button>
  </div>
  <div class="cat-search-wrap">
    <input class="cat-search" id="search" type="search" placeholder="Rechercher un médicament, matériel, DCI..." autocomplete="off">
  </div>
</header>

<div class="cat-cats-strip">
  <div class="cat-cats-scroll" id="cats"></div>
</div>

<div class="cat-toolbar">
  <div class="cat-count" id="count">Chargement...</div>
  <button class="cat-filter-btn" id="filter-btn" type="button">
    <span>&#9881;&#65039;</span> Filtrer
  </button>
</div>

<div class="cat-filters hidden" id="filters">
  <div class="cat-filters-inner">
    <div class="cat-filter-group">
      <h4>Disponibilité</h4>
      <div class="cat-filter-opts" id="filter-avail"></div>
    </div>
    <div class="cat-filter-group">
      <h4>Catégorie</h4>
      <div class="cat-filter-opts" id="filter-cat"></div>
    </div>
  </div>
</div>

<div class="cat-grid" id="grid"></div>

<div class="cat-empty hidden" id="empty">
  <div class="cat-empty-icon">&#128269;</div>
  <h3>Aucun produit trouvé</h3>
  <p>Nous pouvons quand même rechercher ce produit pour vous.</p>
  <button class="cat-custom-btn" id="empty-custom-btn" type="button" style="padding:13px 20px;border-radius:11px;background:var(--blue);color:#fff;font-weight:800;border:0;font-size:14px;cursor:pointer">
    + Ajouter comme besoin
  </button>
</div>

<div class="cat-custom">
  <div class="cat-custom-card">
    <h3>&#10024; Vous ne trouvez pas votre produit ?</h3>
    <p>Décrivez votre besoin, nous chercherons pour vous.</p>
    <div class="cat-custom-field">
      <label for="custom-desc">Décrivez votre besoin</label>
      <textarea id="custom-desc" rows="2" placeholder="Ex : Seringues 10 ml avec aiguille"></textarea>
    </div>
    <div class="cat-custom-field">
      <label for="custom-qty">Quantité</label>
      <input id="custom-qty" type="text" placeholder="Ex : 50">
    </div>
    <button class="cat-custom-btn" id="custom-add" type="button">+ Ajouter à ma demande</button>
  </div>
</div>

<button class="cat-float empty" id="float" type="button">
  <span class="cat-float-icon">&#128221;</span>
  Ma demande
  <span class="cat-float-count" id="float-count">0</span>
</button>

<!-- Panneau détail produit -->
<div class="cat-detail hidden" id="detail">
  <div class="cat-detail-head">
    <button class="cat-detail-close" id="detail-close" type="button">&#8592;</button>
    <span style="font-size:14px;font-weight:700">Détail produit</span>
  </div>
  <div class="cat-detail-body" id="detail-body"></div>
  <div class="cat-detail-actions">
    <div class="cat-detail-qty">
      <button type="button" id="detail-minus">−</button>
      <input type="text" id="detail-qty" value="1">
      <button type="button" id="detail-plus">+</button>
    </div>
    <button class="cat-detail-add" id="detail-add" type="button">Ajouter à ma demande</button>
  </div>
</div>

<script src="/static/professional_catalogue.js"></script>
</body>
</html>
'''
(STATIC / "professional_catalogue.html").write_text(CAT_HTML, encoding="utf-8")
print("[OK] professional_catalogue.html")

# ============================================================
# 2. JS catalogue
# ============================================================
CAT_JS = r'''/* Elokinab Health - Catalogue B2B */
(function () {
  var API = "/api";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  var state = {
    products: [],
    filtered: [],
    categories: [],
    draft: null,
    draftItemsCount: 0,
    query: "",
    categoryFilter: "",
    availFilter: "",
    loading: false
  };

  // ============================================================
  // Utilitaires
  // ============================================================
  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }

  function toast(msg) {
    var t = document.createElement("div");
    t.className = "cat-toast";
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 2200);
  }

  function api(method, path, body) {
    var opts = {
      method: method,
      credentials: "same-origin",
      headers: { "Accept": "application/json" }
    };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(API + path, opts).then(function (r) {
      if (r.status === 401) {
        window.location.href = "/connexion?next=/professionnel/catalogue";
        throw new Error("Non authentifie");
      }
      return r.json().then(function (data) {
        if (!r.ok) throw new Error(data.detail || "Erreur");
        return data;
      });
    });
  }

  function normalize(s) {
    return String(s || "").toLowerCase()
      .replace(/[àâä]/g, "a").replace(/[éèêë]/g, "e")
      .replace(/[íîï]/g, "i").replace(/[óôö]/g, "o")
      .replace(/[ùûü]/g, "u").replace(/ç/g, "c");
  }

  function availabilityInfo(p) {
    var a = (p.availability || "").toLowerCase();
    if (a === "rupture" || a === "indisponible" || a === "indispo") {
      return { cls: "indispo", label: "Indisponible", price_hidden: false, still_addable: true };
    }
    if (a === "stock_limite" || a === "stock limité") {
      return { cls: "limite", label: "Stock limité", price_hidden: false, still_addable: true };
    }
    if (a === "a_confirmer" || a === "à confirmer") {
      return { cls: "confirmer", label: "À confirmer", price_hidden: true, still_addable: true };
    }
    return { cls: "dispo", label: "Disponible", price_hidden: false, still_addable: true };
  }

  function fmtPrice(v) {
    var n = Math.round(Number(v) || 0);
    return n.toLocaleString("fr-FR") + " F";
  }

  // ============================================================
  // Chargements
  // ============================================================
  function loadProducts() {
    return api("GET", "/products").then(function (list) {
      state.products = Array.isArray(list) ? list : [];
    });
  }

  function loadCategories() {
    return api("GET", "/categories").then(function (list) {
      state.categories = Array.isArray(list) ? list : [];
    });
  }

  function loadDraft() {
    return api("GET", "/pro/requests/draft").then(function (draft) {
      state.draft = draft;
      // recupere le nombre d'items
      return api("GET", "/pro/requests/" + draft.reference).then(function (full) {
        state.draftItemsCount = (full.items || []).length + (full.attachments || []).length;
        updateFloat();
      });
    });
  }

  // ============================================================
  // Rendu catégories
  // ============================================================
  function renderCategories() {
    var box = document.getElementById("cats");
    box.innerHTML = "";
    var all = document.createElement("button");
    all.type = "button";
    all.className = "cat-chip active";
    all.textContent = "Tous";
    all.setAttribute("data-cat", "");
    box.appendChild(all);

    state.categories.forEach(function (c) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "cat-chip";
      b.textContent = c.name + " (" + c.total + ")";
      b.setAttribute("data-cat", c.name);
      box.appendChild(b);
    });

    $$(".cat-chip", box).forEach(function (b) {
      b.addEventListener("click", function () {
        $$(".cat-chip", box).forEach(function (x) { x.classList.remove("active"); });
        b.classList.add("active");
        state.categoryFilter = b.getAttribute("data-cat") || "";
        applyFilters();
      });
    });
  }

  // ============================================================
  // Rendu filtres
  // ============================================================
  function renderFilters() {
    var avail = document.getElementById("filter-avail");
    avail.innerHTML = "";
    var AVAILS = [
      ["", "Toutes"],
      ["disponible", "Disponible"],
      ["stock_limite", "Stock limité"],
      ["a_confirmer", "À confirmer"],
      ["rupture", "Indisponible"]
    ];
    AVAILS.forEach(function (pair) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "cat-filter-opt" + (state.availFilter === pair[0] ? " active" : "");
      b.textContent = pair[1];
      b.addEventListener("click", function () {
        state.availFilter = pair[0];
        renderFilters();
        applyFilters();
      });
      avail.appendChild(b);
    });
  }

  // ============================================================
  // Filtrage
  // ============================================================
  function applyFilters() {
    var q = normalize(state.query);
    var cat = state.categoryFilter;
    var av = state.availFilter;

    state.filtered = state.products.filter(function (p) {
      if (cat && p.category !== cat) return false;
      if (av && (p.availability || "").toLowerCase() !== av) return false;
      if (q) {
        var hay = normalize(
          (p.name || "") + " " + (p.presentation || "") + " " +
          (p.description || "") + " " + (p.category || "")
        );
        if (hay.indexOf(q) === -1) return false;
      }
      return true;
    });

    renderGrid();
  }

  // ============================================================
  // Rendu grille
  // ============================================================
  function renderGrid() {
    var grid = document.getElementById("grid");
    var empty = document.getElementById("empty");
    var countEl = document.getElementById("count");

    grid.innerHTML = "";

    if (state.filtered.length === 0) {
      grid.classList.add("hidden");
      empty.classList.remove("hidden");
      countEl.textContent = state.query ? 'Aucun résultat pour "' + state.query + '"' : "0 produit";
      return;
    }
    grid.classList.remove("hidden");
    empty.classList.add("hidden");
    countEl.innerHTML = "<strong>" + state.filtered.length + "</strong> produit" + (state.filtered.length > 1 ? "s" : "");

    state.filtered.forEach(function (p) {
      grid.appendChild(productCard(p));
    });
  }

  function productCard(p) {
    var card = document.createElement("article");
    card.className = "cat-card";

    var avail = availabilityInfo(p);

    // Image
    var imgBox = document.createElement("div");
    imgBox.className = "cat-card-img";
    if (p.image_url) {
      var img = document.createElement("img");
      img.src = p.image_url;
      img.alt = p.name;
      img.loading = "lazy";
      img.onerror = function () {
        img.remove();
        imgBox.innerHTML = '<div class="cat-card-img-placeholder">' +
          escapeHtml((p.name || "?").charAt(0).toUpperCase()) + '</div>';
      };
      imgBox.appendChild(img);
    } else {
      imgBox.innerHTML = '<div class="cat-card-img-placeholder">' +
        escapeHtml((p.name || "?").charAt(0).toUpperCase()) + '</div>';
    }
    imgBox.addEventListener("click", function () { openDetail(p); });
    card.appendChild(imgBox);

    // Body
    var body = document.createElement("div");
    body.className = "cat-card-body";

    var name = document.createElement("h3");
    name.className = "cat-card-name";
    name.textContent = p.name || "";
    body.appendChild(name);

    var meta = document.createElement("div");
    meta.className = "cat-card-meta";
    meta.textContent = p.presentation || p.category || "";
    body.appendChild(meta);

    var badge = document.createElement("span");
    badge.className = "cat-badge " + avail.cls;
    badge.textContent = avail.label;
    body.appendChild(badge);

    var price = document.createElement("div");
    price.className = "cat-card-price" + (avail.price_hidden ? " confirm" : "");
    price.textContent = avail.price_hidden ? "Prix : à confirmer" : fmtPrice(p.price);
    body.appendChild(price);

    // Qty
    var qtyWrap = document.createElement("div");
    qtyWrap.className = "cat-card-qty";
    var minus = document.createElement("button");
    minus.type = "button"; minus.textContent = "−";
    var qtyIn = document.createElement("input");
    qtyIn.type = "text"; qtyIn.value = "1";
    var plus = document.createElement("button");
    plus.type = "button"; plus.textContent = "+";
    minus.addEventListener("click", function () {
      var v = parseInt(qtyIn.value) || 1;
      qtyIn.value = Math.max(1, v - 1);
    });
    plus.addEventListener("click", function () {
      var v = parseInt(qtyIn.value) || 1;
      qtyIn.value = v + 1;
    });
    qtyWrap.appendChild(minus); qtyWrap.appendChild(qtyIn); qtyWrap.appendChild(plus);
    body.appendChild(qtyWrap);

    // Add button
    var add = document.createElement("button");
    add.type = "button";
    add.className = "cat-card-add";
    add.innerHTML = "+ Ajouter à ma demande";
    add.addEventListener("click", function () {
      var q = parseInt(qtyIn.value) || 1;
      addToDraft(p, q, add);
    });
    body.appendChild(add);

    card.appendChild(body);
    return card;
  }

  // ============================================================
  // Ajout à la demande
  // ============================================================
  function addToDraft(product, qty, btn) {
    if (!state.draft) { toast("Demande indisponible"); return; }
    var desc = product.name + (product.presentation ? " — " + product.presentation : "");
    if (btn) { btn.disabled = true; btn.textContent = "Ajout..."; }

    api("POST", "/pro/requests/" + state.draft.reference + "/items", {
      product_id: product.id,
      description: desc,
      requested_quantity: qty
    }).then(function () {
      state.draftItemsCount += 1;
      updateFloat();
      if (btn) {
        btn.classList.add("done");
        btn.innerHTML = "&#10003; Ajouté";
        setTimeout(function () {
          btn.classList.remove("done");
          btn.disabled = false;
          btn.innerHTML = "+ Ajouter à ma demande";
        }, 1400);
      }
      toast("Ajouté à votre demande");
    }).catch(function (e) {
      toast(e.message);
      if (btn) { btn.disabled = false; btn.innerHTML = "+ Ajouter à ma demande"; }
    });
  }

  function updateFloat() {
    var f = document.getElementById("float");
    var c = document.getElementById("float-count");
    if (!f || !c) return;
    c.textContent = state.draftItemsCount;
    if (state.draftItemsCount > 0) f.classList.remove("empty");
    else f.classList.add("empty");
  }

  // ============================================================
  // Détail produit
  // ============================================================
  function openDetail(p) {
    var d = document.getElementById("detail");
    var body = document.getElementById("detail-body");
    body.innerHTML = "";

    var avail = availabilityInfo(p);

    var imgBox = document.createElement("div");
    imgBox.className = "cat-detail-img";
    if (p.image_url) {
      var img = document.createElement("img");
      img.src = p.image_url;
      img.alt = p.name;
      img.onerror = function () {
        img.remove();
        imgBox.innerHTML = '<div class="cat-detail-img-placeholder">' +
          escapeHtml((p.name || "?").charAt(0).toUpperCase()) + '</div>';
      };
      imgBox.appendChild(img);
    } else {
      imgBox.innerHTML = '<div class="cat-detail-img-placeholder">' +
        escapeHtml((p.name || "?").charAt(0).toUpperCase()) + '</div>';
    }
    body.appendChild(imgBox);

    var info = document.createElement("div");
    info.className = "cat-detail-info";

    var h1 = document.createElement("h1"); h1.textContent = p.name || "";
    info.appendChild(h1);

    var meta = document.createElement("p"); meta.className = "cat-detail-meta";
    meta.textContent = p.presentation || p.category || "";
    info.appendChild(meta);

    var badge = document.createElement("span");
    badge.className = "cat-badge " + avail.cls;
    badge.textContent = avail.label;
    info.appendChild(badge);

    var price = document.createElement("div");
    price.className = "cat-detail-price" + (avail.price_hidden ? " confirm" : "");
    price.textContent = avail.price_hidden ? "Prix : à confirmer" : fmtPrice(p.price);
    info.appendChild(price);

    if (p.requires_prescription) {
      var presc = document.createElement("div");
      presc.className = "cat-detail-presc";
      presc.textContent = "⚕ Prescription requise";
      info.appendChild(presc);
    }

    if (p.description) {
      var ds = document.createElement("div");
      ds.className = "cat-detail-section";
      ds.innerHTML = "<h4>Description</h4><p>" + escapeHtml(p.description) + "</p>";
      info.appendChild(ds);
    }

    if (p.category) {
      var cs = document.createElement("div");
      cs.className = "cat-detail-section";
      cs.innerHTML = "<h4>Catégorie</h4><p>" + escapeHtml(p.category) + "</p>";
      info.appendChild(cs);
    }

    body.appendChild(info);

    // Setup qty + add
    document.getElementById("detail-qty").value = "1";
    var addBtn = document.getElementById("detail-add");
    addBtn.disabled = false;
    addBtn.textContent = "Ajouter à ma demande";
    addBtn.onclick = function () {
      var q = parseInt(document.getElementById("detail-qty").value) || 1;
      addToDraft(p, q, addBtn);
    };

    d.classList.remove("hidden");
    document.body.style.overflow = "hidden";
  }

  function closeDetail() {
    document.getElementById("detail").classList.add("hidden");
    document.body.style.overflow = "";
  }

  // ============================================================
  // Besoin personnalisé
  // ============================================================
  function addCustom() {
    var desc = (document.getElementById("custom-desc").value || "").trim();
    var qtyRaw = (document.getElementById("custom-qty").value || "").trim();
    if (!desc) { toast("Décrivez votre besoin"); return; }
    var qty = parseInt(qtyRaw) || 1;
    if (!state.draft) { toast("Demande indisponible"); return; }

    var btn = document.getElementById("custom-add");
    btn.disabled = true; btn.textContent = "Ajout...";
    api("POST", "/pro/requests/" + state.draft.reference + "/items", {
      product_id: null,
      description: desc,
      requested_quantity: qty
    }).then(function () {
      state.draftItemsCount += 1;
      updateFloat();
      document.getElementById("custom-desc").value = "";
      document.getElementById("custom-qty").value = "";
      toast("Besoin ajouté à votre demande");
    }).catch(function (e) { toast(e.message); })
      .then(function () {
        btn.disabled = false;
        btn.textContent = "+ Ajouter à ma demande";
      });
  }

  // ============================================================
  // Init
  // ============================================================
  function init() {
    // Recherche
    var s = document.getElementById("search");
    s.addEventListener("input", function () {
      state.query = s.value.trim();
      applyFilters();
    });

    // Filtre toggle
    document.getElementById("filter-btn").addEventListener("click", function () {
      var f = document.getElementById("filters");
      var b = document.getElementById("filter-btn");
      if (f.classList.contains("hidden")) {
        f.classList.remove("hidden");
        b.classList.add("active");
      } else {
        f.classList.add("hidden");
        b.classList.remove("active");
      }
    });

    // Détail
    document.getElementById("detail-close").addEventListener("click", closeDetail);
    document.getElementById("detail-minus").addEventListener("click", function () {
      var i = document.getElementById("detail-qty");
      i.value = Math.max(1, (parseInt(i.value) || 1) - 1);
    });
    document.getElementById("detail-plus").addEventListener("click", function () {
      var i = document.getElementById("detail-qty");
      i.value = (parseInt(i.value) || 1) + 1;
    });

    // Besoin perso
    document.getElementById("custom-add").addEventListener("click", addCustom);
    document.getElementById("empty-custom-btn").addEventListener("click", function () {
      document.querySelector(".cat-custom").scrollIntoView({ behavior: "smooth" });
      setTimeout(function () { document.getElementById("custom-desc").focus(); }, 400);
    });

    // Float -> retour à la demande
    document.getElementById("float").addEventListener("click", function () {
      window.location.href = "/professionnel";
    });

    // Badge notifications
    fetch(API + "/notifications?unread_only=1", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (list) {
        var n = Array.isArray(list) ? list.length : 0;
        var b = document.getElementById("bell-badge");
        if (b && n > 0) { b.textContent = n > 99 ? "99+" : String(n); b.classList.remove("hidden"); }
      }).catch(function () {});

    // Chargement
    Promise.all([loadCategories(), loadProducts()])
      .then(function () {
        renderCategories();
        renderFilters();
        applyFilters();
        return loadDraft();
      })
      .catch(function (e) {
        var count = document.getElementById("count");
        if (count) count.textContent = "Erreur de chargement";
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
'''
(STATIC / "professional_catalogue.js").write_text(CAT_JS, encoding="utf-8")
print("[OK] professional_catalogue.js")

# ============================================================
# 3. Route : verifier /professionnel/catalogue
# ============================================================
src = MAIN.read_text(encoding="utf-8")
if '"/professionnel/catalogue"' not in src:
    routes = '''

@app.get("/professionnel/catalogue", include_in_schema=False)
def page_pro_catalogue():
    return FileResponse(STATIC_DIR / "professional_catalogue.html")

'''
    anchor = "\ninit_db()\n"
    if anchor in src:
        src = src.replace(anchor, routes + anchor, 1)
        MAIN.write_text(src, encoding="utf-8")
        print("[OK] main.py -> route /professionnel/catalogue")
else:
    print("[i] route deja presente")

print()
print("=" * 60)
print("CATALOGUE B2B LIVRE")
print("=" * 60)
print()
print("Fichiers :")
print("  static/professional_catalogue.html")
print("  static/professional_catalogue.js")
print()
print("URL : /professionnel/catalogue")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print()
print("Puis teste : https://URL.trycloudflare.com/professionnel/catalogue")