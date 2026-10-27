"""
v6_accueil_pro.py
Refonte accueil pro : action requise + reprendre commande + activite recente
+ support WhatsApp + guide de demarrage (nouveaux seulement).
Pas de stats, pas de produits frequents.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_accueil_pro_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(STATIC / "professional.html", backup / "professional.html")
shutil.copy2(STATIC / "professional_dashboard.js", backup / "professional_dashboard.js")
print("[OK] Backup ->", backup.name)

# ============================================================
# PROFESSIONAL_ACCUEIL.CSS (design system reutilisable)
# ============================================================
ACCUEIL_CSS = '''/* Elokinab Health - Design System Pro (V6) */

:root{
  /* Couleurs */
  --blue:#1a4a7f;
  --blue-dark:#123258;
  --blue-soft:#eaf1f9;
  --blue-line:#cddff0;

  --wa:#25d366;
  --wa-dark:#1da851;

  --ok:#0a7a5a;
  --ok-soft:#e6f7f1;

  --warn:#8a5a00;
  --warn-soft:#fff7e6;
  --warn-line:#f2d9b3;

  --danger:#b23c3c;
  --danger-soft:#fee2e2;
  --danger-line:#f6d2d2;

  --ink:#0f172a;
  --ink-soft:#1e293b;
  --muted:#64748b;
  --muted-soft:#94a3b8;

  --line:#e6ebf1;
  --line-soft:#f1f5f9;

  --bg:#f7fafc;
  --white:#ffffff;

  --radius:14px;
  --radius-sm:10px;
  --radius-lg:18px;

  --shadow-sm:0 1px 2px rgba(15,23,42,.04);
  --shadow:0 1px 3px rgba(15,23,42,.06), 0 1px 2px rgba(15,23,42,.04);
  --shadow-md:0 4px 12px rgba(15,23,42,.06), 0 2px 4px rgba(15,23,42,.04);
}

/* Reset local */
*,*::before,*::after{box-sizing:border-box}
html,body{overflow-x:clip;margin:0;padding:0}
body{
  font-family:-apple-system,"Segoe UI",system-ui,Roboto,Helvetica,Arial,sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.5;font-size:15px;
  -webkit-font-smoothing:antialiased;padding-bottom:100px;
}
a{color:inherit;text-decoration:none}
button{font-family:inherit;cursor:pointer}
.hidden{display:none !important}
img{max-width:100%;display:block}

/* -------- Header -------- */
.acc-header{
  background:#fff;border-bottom:1px solid var(--line);
  position:sticky;top:0;z-index:50;
}
.acc-header-inner{
  max-width:720px;margin:0 auto;padding:12px 18px;
  display:flex;align-items:center;gap:12px;
}
.acc-brand{
  display:flex;align-items:center;gap:9px;
  font-weight:800;font-size:15px;letter-spacing:-.01em;
}
.acc-brand-mark{
  width:32px;height:32px;border-radius:9px;
  background:linear-gradient(135deg,var(--blue),#2a6ba8);color:#fff;
  display:flex;align-items:center;justify-content:center;
  font-size:16px;font-weight:800;
}
.acc-bell{
  margin-left:auto;
  width:38px;height:38px;border-radius:10px;border:1px solid var(--line);
  background:#fff;color:var(--ink);font-size:16px;
  display:flex;align-items:center;justify-content:center;
  position:relative;
}
.acc-bell:hover{border-color:var(--blue);color:var(--blue)}
.acc-bell-badge{
  position:absolute;top:-4px;right:-4px;background:var(--danger);
  color:#fff;font-size:9px;font-weight:800;
  min-width:18px;height:18px;padding:0 5px;border-radius:999px;
  display:flex;align-items:center;justify-content:center;
  border:2px solid #fff;
}

/* -------- Main -------- */
.acc-main{
  max-width:720px;margin:0 auto;
  padding:22px 18px 32px;
}

/* -------- Bienvenue -------- */
.acc-welcome{margin:0 0 22px}
.acc-welcome h1{
  font-size:24px;font-weight:800;letter-spacing:-.02em;
  margin:0 0 6px;line-height:1.2;
}
.acc-welcome p{
  font-size:14px;color:var(--muted);margin:0;
  line-height:1.5;
}

/* -------- Bouton principal -------- */
.acc-btn-primary{
  display:flex;align-items:center;justify-content:center;gap:8px;
  width:100%;padding:16px;border:0;border-radius:var(--radius);
  background:var(--blue);color:#fff;
  font-size:15px;font-weight:800;
  box-shadow:0 4px 14px rgba(26,74,127,.18);
  transition:.15s;margin-bottom:22px;
}
.acc-btn-primary:hover{background:var(--blue-dark);transform:translateY(-1px)}
.acc-btn-primary .ico{font-size:18px}

/* -------- Section -------- */
.acc-section{margin-bottom:22px}
.acc-section-title{
  font-size:11px;font-weight:800;color:var(--muted);
  text-transform:uppercase;letter-spacing:.08em;
  margin:0 0 10px;
}

/* -------- Alerte action requise -------- */
.acc-alert{
  display:block;
  background:var(--warn-soft);
  border:1px solid var(--warn-line);
  border-left:4px solid var(--warn);
  border-radius:var(--radius);
  padding:16px;
  margin-bottom:22px;
  text-decoration:none;color:inherit;
  transition:.15s;
}
.acc-alert:hover{
  box-shadow:0 4px 14px rgba(138,90,0,.08);
  transform:translateY(-1px);
}
.acc-alert-head{
  display:flex;align-items:center;gap:8px;
  font-size:11px;font-weight:800;
  color:var(--warn);text-transform:uppercase;
  letter-spacing:.08em;margin-bottom:6px;
}
.acc-alert-title{
  font-size:15px;font-weight:800;color:var(--ink);
  margin:0 0 4px;line-height:1.3;
}
.acc-alert-desc{
  font-size:13px;color:#5c4a00;margin:0 0 10px;line-height:1.45;
}
.acc-alert-cta{
  display:inline-flex;align-items:center;gap:6px;
  font-size:13px;font-weight:800;color:var(--warn);
}
.acc-alert-arrow{transition:transform .15s}
.acc-alert:hover .acc-alert-arrow{transform:translateX(3px)}

/* -------- Carte generique -------- */
.acc-card{
  background:#fff;border:1px solid var(--line);
  border-radius:var(--radius);padding:16px;
  box-shadow:var(--shadow-sm);
}

/* -------- Reprendre commande -------- */
.acc-reorder{
  display:block;
  background:#fff;border:1px solid var(--line);
  border-radius:var(--radius);padding:16px;
  transition:.15s;text-decoration:none;color:inherit;
}
.acc-reorder:hover{
  border-color:var(--blue);
  box-shadow:var(--shadow-md);
  transform:translateY(-1px);
}
.acc-reorder-head{
  display:flex;align-items:center;gap:12px;
  margin-bottom:12px;
}
.acc-reorder-icon{
  width:44px;height:44px;border-radius:12px;
  background:var(--blue-soft);color:var(--blue);
  display:flex;align-items:center;justify-content:center;
  font-size:20px;flex-shrink:0;
}
.acc-reorder-body{flex:1;min-width:0}
.acc-reorder-label{
  font-size:11px;font-weight:800;color:var(--muted);
  text-transform:uppercase;letter-spacing:.08em;
  margin:0 0 3px;
}
.acc-reorder-title{
  font-size:15px;font-weight:800;color:var(--ink);
  margin:0;line-height:1.3;
}
.acc-reorder-foot{
  display:flex;align-items:center;justify-content:space-between;
  padding-top:12px;border-top:1px solid var(--line);
}
.acc-reorder-meta{
  font-size:12px;color:var(--muted);
  font-family:Consolas,monospace;
}
.acc-reorder-cta{
  font-size:13px;font-weight:800;color:var(--blue);
  display:flex;align-items:center;gap:5px;
}

/* -------- Guide demarrage -------- */
.acc-guide{
  background:#fff;border:1px solid var(--line);
  border-radius:var(--radius);padding:18px;
}
.acc-guide h3{
  font-size:14px;font-weight:800;color:var(--ink);
  margin:0 0 14px;
}
.acc-guide-steps{display:flex;flex-direction:column;gap:12px}
.acc-guide-step{
  display:flex;align-items:flex-start;gap:12px;
}
.acc-guide-num{
  width:28px;height:28px;border-radius:50%;
  background:var(--blue-soft);color:var(--blue);
  display:flex;align-items:center;justify-content:center;
  font-size:13px;font-weight:800;flex-shrink:0;
}
.acc-guide-text{
  font-size:13px;color:var(--ink-soft);
  line-height:1.5;padding-top:3px;
}

/* -------- Activite recente -------- */
.acc-activity{
  background:#fff;border:1px solid var(--line);
  border-radius:var(--radius);overflow:hidden;
}
.acc-activity-item{
  display:flex;align-items:center;gap:12px;
  padding:14px 16px;
  border-bottom:1px solid var(--line-soft);
  cursor:pointer;transition:.12s;
  text-decoration:none;color:inherit;
}
.acc-activity-item:last-child{border-bottom:0}
.acc-activity-item:hover{background:#fafbfc}

.acc-activity-body{flex:1;min-width:0}
.acc-activity-ref{
  font-family:Consolas,monospace;font-weight:800;
  font-size:13px;color:var(--ink);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.acc-activity-meta{
  font-size:11px;color:var(--muted);margin-top:3px;
}
.acc-pill{
  display:inline-flex;align-items:center;gap:5px;
  padding:4px 10px;border-radius:999px;
  font-size:10px;font-weight:800;
  text-transform:uppercase;letter-spacing:.05em;
  flex-shrink:0;
}
.acc-pill::before{
  content:"";width:6px;height:6px;border-radius:50%;background:currentColor;
}
.pill-pending{background:var(--warn-soft);color:var(--warn)}
.pill-confirmed{background:var(--ok-soft);color:var(--ok)}
.pill-preparing{background:#f3e8ff;color:#6335b8}
.pill-ready{background:var(--ok-soft);color:var(--ok)}
.pill-done{background:#e2e8f0;color:#475569}
.pill-refused{background:var(--danger-soft);color:var(--danger)}
.pill-submitted{background:var(--blue-soft);color:var(--blue-dark)}
.pill-verified{background:var(--ok-soft);color:var(--ok)}
.pill-rejected{background:var(--danger-soft);color:var(--danger)}
.pill-none{background:#e2e8f0;color:#475569}

.acc-activity-empty{
  padding:24px 16px;text-align:center;
  font-size:13px;color:var(--muted);
}

.acc-link-more{
  display:inline-flex;align-items:center;gap:5px;
  margin-top:10px;
  font-size:13px;font-weight:800;color:var(--blue);
}
.acc-link-more:hover{color:var(--blue-dark)}

/* -------- Support -------- */
.acc-support{
  display:flex;align-items:center;gap:12px;
  padding:14px 16px;
  background:#fff;border:1px solid var(--line);
  border-radius:var(--radius);
  transition:.15s;text-decoration:none;color:inherit;
  margin-top:22px;
}
.acc-support:hover{border-color:var(--wa)}
.acc-support-icon{
  width:36px;height:36px;border-radius:10px;
  background:#e6f9ee;color:var(--wa-dark);
  display:flex;align-items:center;justify-content:center;
  font-size:18px;flex-shrink:0;
}
.acc-support-body{flex:1;min-width:0}
.acc-support-title{
  font-size:13px;font-weight:800;color:var(--ink);
  margin:0;
}
.acc-support-desc{
  font-size:12px;color:var(--muted);margin:2px 0 0;
}

/* -------- Navbar -------- */
.pro-navbar{
  position:fixed;bottom:0;left:0;right:0;z-index:200;
  background:#fff;border-top:1px solid var(--line);
  display:grid;grid-template-columns:1fr 1fr 76px 1fr 1fr;
  padding:6px 6px calc(6px + env(safe-area-inset-bottom)) 6px;
  box-shadow:0 -2px 12px rgba(15,23,42,.06);
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
  border:4px solid var(--bg);
}

@media (max-width:400px){
  .acc-welcome h1{font-size:20px}
  .acc-main{padding:18px 14px 28px}
}
'''
(STATIC / "professional_accueil.css").write_text(ACCUEIL_CSS, encoding="utf-8")
print("[OK] professional_accueil.css")

# ============================================================
# PROFESSIONAL.HTML refondu
# ============================================================
PRO_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Espace professionnel - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<link rel="stylesheet" href="/static/professional_accueil.css">
</head>
<body>

<header class="acc-header">
  <div class="acc-header-inner">
    <a class="acc-brand" href="/professionnel">
      <span class="acc-brand-mark">+</span>
      Elokinab
    </a>
    <a class="acc-bell" href="/professionnel/commandes" aria-label="Notifications">
      &#128276;
      <span class="acc-bell-badge hidden" id="bell-badge">0</span>
    </a>
  </div>
</header>

<main class="acc-main">

  <!-- Bienvenue -->
  <div class="acc-welcome">
    <h1 id="hello">Bienvenue</h1>
    <p>Gerez vos demandes, commandes et paiements au meme endroit.</p>
  </div>

  <!-- Bouton nouvelle demande -->
  <button class="acc-btn-primary" id="new-request" type="button">
    <span class="ico">&#10133;</span> Nouvelle demande
  </button>

  <!-- Alerte action requise -->
  <div id="alert-block"></div>

  <!-- Reprendre une commande -->
  <div id="reorder-block"></div>

  <!-- Guide demarrage (nouveaux uniquement) -->
  <div id="guide-block"></div>

  <!-- Activite recente -->
  <section class="acc-section" id="activity-section">
    <h2 class="acc-section-title">Activite recente</h2>
    <div id="activity"></div>
  </section>

  <!-- Support WhatsApp -->
  <a class="acc-support"
     href="https://wa.me/22871039904?text=Bonjour%20Elokinab%20Health%2C%20j%27ai%20une%20question."
     target="_blank" rel="noopener">
    <span class="acc-support-icon">&#128172;</span>
    <span class="acc-support-body">
      <span class="acc-support-title">Besoin d'aide ?</span>
      <span class="acc-support-desc">Contacter Elokinab sur WhatsApp</span>
    </span>
  </a>

</main>

<nav class="pro-navbar">
  <a href="/professionnel" class="active"><span class="ico">&#127968;</span> Accueil</a>
  <a href="/professionnel/catalogue"><span class="ico">&#128722;</span> Catalogue</a>
  <a href="/professionnel/demande" class="central">
    <span>+</span>
  </a>
  <a href="/professionnel/commandes"><span class="ico">&#128230;</span> Commandes</a>
  <a href="/professionnel/etablissement"><span class="ico">&#127970;</span> Etabl.</a>
</nav>

<script src="/static/safe_locale.js"></script>
<script src="/static/professional_dashboard.js"></script>
</body>
</html>
'''
(STATIC / "professional.html").write_text(PRO_HTML, encoding="utf-8")
print("[OK] professional.html refondu")

# ============================================================
# PROFESSIONAL_DASHBOARD.JS refondu
# ============================================================
DASH_JS = r'''/* Elokinab Health - Accueil professionnel (V6) */
(function () {
  var API = "/api";
  var $ = function (id) { return document.getElementById(id); };

  var state = {
    org: null,
    orders: [],
    activity: [],
    stats: {
      orders_count: 0,
      has_pending_payment: false,
      has_rejected_proof: false,
      first_pending_order: null
    }
  };

  // ============================================================
  // Utilitaires
  // ============================================================
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

  function fmtDate(iso) {
    if (!iso) return "";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return String(iso);
      var day = d.getDate();
      var m = ["janv.","fevr.","mars","avr.","mai","juin",
               "juil.","aout","sept.","oct.","nov.","dec."][d.getMonth()];
      return day + " " + m + " " + d.getFullYear();
    } catch (e) { return String(iso); }
  }

  function api(path) {
    return fetch(API + path, { credentials: "same-origin" }).then(function (r) {
      if (r.status === 401) {
        window.location.href = "/connexion?next=/professionnel";
        throw new Error("Non authentifie");
      }
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    });
  }

  // ============================================================
  // Statuts
  // ============================================================
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

  // ============================================================
  // Chargement initial
  // ============================================================
  function load() {
    return Promise.all([
      api("/pro/organizations/me").catch(function () { return null; }),
      api("/orders/mine").catch(function () { return []; }),
      api("/notifications?unread_only=1").catch(function () { return []; })
    ]).then(function (r) {
      state.org = r[0];
      var orders = Array.isArray(r[1]) ? r[1] : [];
      var notifs = Array.isArray(r[2]) ? r[2] : [];

      // Filtrer les brouillons (DRAFT) — on ne garde que les commandes reelles
      state.orders = orders.filter(function (o) {
        return o.status !== "DRAFT" && o.status !== "draft";
      });

      renderBell(notifs.length);
      analyzeOrders();
      renderWelcome();
      renderAlert();
      renderReorder();
      renderGuide();
      renderActivity();
    }).catch(function (e) {
      console.error("load error:", e);
    });
  }

  function renderBell(n) {
    var b = $("bell-badge");
    if (!b) return;
    if (n > 0) {
      b.textContent = n > 99 ? "99+" : String(n);
      b.classList.remove("hidden");
    } else {
      b.classList.add("hidden");
    }
  }

  // ============================================================
  // Analyse des commandes
  // ============================================================
  function analyzeOrders() {
    var st = {
      orders_count: state.orders.length,
      has_pending_payment: false,
      has_rejected_proof: false,
      first_pending_order: null,
      first_rejected_order: null,
      last_order: null,
      has_activity: state.orders.length > 0
    };

    // Trier par date desc
    var sorted = state.orders.slice().sort(function (a, b) {
      return (b.created_at || "").localeCompare(a.created_at || "");
    });

    if (sorted.length > 0) st.last_order = sorted[0];

    sorted.forEach(function (o) {
      var ps = o.payment_status || "NONE";
      // Paiement a effectuer
      if (ps === "PENDING" && o.status !== "refusee" && !st.first_pending_order) {
        st.has_pending_payment = true;
        st.first_pending_order = o;
      }
      // Preuve refusee : priorite plus haute
      if (ps === "REJECTED" && !st.first_rejected_order) {
        st.has_rejected_proof = true;
        st.first_rejected_order = o;
      }
    });

    // Priorite : refusee > en attente de paiement
    if (st.first_rejected_order) {
      st.alert_type = "rejected";
      st.alert_order = st.first_rejected_order;
    } else if (st.first_pending_order) {
      st.alert_type = "pending";
      st.alert_order = st.first_pending_order;
    } else {
      st.alert_type = null;
    }

    state.stats = st;
  }

  // ============================================================
  // Bienvenue
  // ============================================================
  function renderWelcome() {
    var hello = $("hello");
    if (!hello) return;
    var name = "Professionnel";
    if (state.org && state.org.structure_name) {
      name = state.org.structure_name;
    }
    hello.textContent = "Bonjour, " + name;
  }

  // ============================================================
  // Alerte action requise
  // ============================================================
  function renderAlert() {
    var box = $("alert-block");
    if (!box) return;
    box.innerHTML = "";

    if (!state.stats.alert_type || !state.stats.alert_order) return;

    var o = state.stats.alert_order;
    var total = (Number(o.subtotal) || 0) + (Number(o.delivery_fee) || 0);

    var alertEl = document.createElement("a");
    alertEl.className = "acc-alert";
    alertEl.href = "/static/payment.html?ref=" + encodeURIComponent(o.reference);

    if (state.stats.alert_type === "rejected") {
      alertEl.innerHTML =
        '<div class="acc-alert-head">&#9888; Preuve refusee</div>' +
        '<h3 class="acc-alert-title">Votre preuve de paiement a ete refusee</h3>' +
        '<p class="acc-alert-desc">' +
          'Commande <strong>' + escapeHtml(o.reference) + '</strong> - ' + money(total) +
          '. Renvoyez une preuve valide pour continuer.</p>' +
        '<span class="acc-alert-cta">Renvoyer une preuve <span class="acc-alert-arrow">&#8594;</span></span>';
    } else {
      alertEl.innerHTML =
        '<div class="acc-alert-head">&#9888; Action requise</div>' +
        '<h3 class="acc-alert-title">Une commande attend votre paiement</h3>' +
        '<p class="acc-alert-desc">' +
          'Commande <strong>' + escapeHtml(o.reference) + '</strong> - ' + money(total) +
          '. Effectuez le transfert pour lancer la preparation.</p>' +
        '<span class="acc-alert-cta">Payer maintenant <span class="acc-alert-arrow">&#8594;</span></span>';
    }

    box.appendChild(alertEl);
  }

  // ============================================================
  // Reprendre une commande
  // ============================================================
  function renderReorder() {
    var box = $("reorder-block");
    if (!box) return;
    box.innerHTML = "";

    var last = state.stats.last_order;
    if (!last) return;

    var itemsCount = last.items_count || 0;
    // Si pas d'items_count, on en met un par defaut (au moins 1)
    if (!itemsCount && last.product_name) itemsCount = 1;

    var card = document.createElement("a");
    card.className = "acc-reorder";
    card.href = "/professionnel/commande/" + encodeURIComponent(last.reference) + "/reprendre";

    var subtotal = Number(last.subtotal) || 0;
    var fee = Number(last.delivery_fee) || 0;
    var total = subtotal + fee;

    card.innerHTML =
      '<div class="acc-reorder-head">' +
        '<div class="acc-reorder-icon">&#128257;</div>' +
        '<div class="acc-reorder-body">' +
          '<div class="acc-reorder-label">Reprendre une commande</div>' +
          '<h3 class="acc-reorder-title">' + escapeHtml(last.reference) + '</h3>' +
        '</div>' +
      '</div>' +
      '<div class="acc-reorder-foot">' +
        '<span class="acc-reorder-meta">' +
          escapeHtml(fmtDate(last.created_at)) + ' - ' + itemsCount + ' produit' + (itemsCount > 1 ? 's' : '') +
        '</span>' +
        '<span class="acc-reorder-cta">Reprendre <span>&#8594;</span></span>' +
      '</div>';

    box.appendChild(card);
  }

  // ============================================================
  // Guide demarrage (nouveaux)
  // ============================================================
  function renderGuide() {
    var box = $("guide-block");
    if (!box) return;
    box.innerHTML = "";

    // Afficher uniquement si aucune commande
    if (state.orders.length > 0) return;

    var guide = document.createElement("div");
    guide.className = "acc-guide";
    guide.innerHTML =
      '<h3>Comment commander sur Elokinab ?</h3>' +
      '<div class="acc-guide-steps">' +
        '<div class="acc-guide-step">' +
          '<div class="acc-guide-num">1</div>' +
          '<div class="acc-guide-text">Constituez votre demande depuis le <strong>catalogue</strong> ou via <strong>WhatsApp</strong>.</div>' +
        '</div>' +
        '<div class="acc-guide-step">' +
          '<div class="acc-guide-num">2</div>' +
          '<div class="acc-guide-text">Validez le recapitulatif et envoyez votre demande.</div>' +
        '</div>' +
        '<div class="acc-guide-step">' +
          '<div class="acc-guide-num">3</div>' +
          '<div class="acc-guide-text">Reglez par Mobile Money et envoyez la preuve.</div>' +
        '</div>' +
        '<div class="acc-guide-step">' +
          '<div class="acc-guide-num">4</div>' +
          '<div class="acc-guide-text">Recevez votre commande par voiture (livraison B2B).</div>' +
        '</div>' +
      '</div>';

    box.appendChild(guide);
  }

  // ============================================================
  // Activite recente
  // ============================================================
  function renderActivity() {
    var box = $("activity");
    if (!box) return;
    box.innerHTML = "";

    var sorted = state.orders.slice().sort(function (a, b) {
      return (b.created_at || "").localeCompare(a.created_at || "");
    }).slice(0, 5);

    if (sorted.length === 0) {
      box.innerHTML =
        '<div class="acc-activity"><div class="acc-activity-empty">' +
        'Vous n\'avez encore aucune commande.' +
        '</div></div>';
      return;
    }

    var wrap = document.createElement("div");
    wrap.className = "acc-activity";

    sorted.forEach(function (o) {
      var statusPill = STATUS_PILLS[o.status] || "pill-none";
      var statusLbl = STATUS_LABELS[o.status] || o.status;
      var payPill = PAYMENT_PILLS[o.payment_status || "NONE"] || "pill-none";

      var item = document.createElement("a");
      item.className = "acc-activity-item";
      item.href = "/suivi?ref=" + encodeURIComponent(o.reference);

      var subtotal = Number(o.subtotal) || 0;
      var fee = Number(o.delivery_fee) || 0;
      var total = subtotal + fee;

      item.innerHTML =
        '<div class="acc-activity-body">' +
          '<div class="acc-activity-ref">' + escapeHtml(o.reference) + '</div>' +
          '<div class="acc-activity-meta">' +
            escapeHtml(fmtDate(o.created_at)) + ' - ' + money(total) +
          '</div>' +
        '</div>' +
        '<span class="acc-pill ' + statusPill + '">' + escapeHtml(statusLbl) + '</span>';

      wrap.appendChild(item);
    });

    box.appendChild(wrap);

    // Lien "Voir tout"
    var more = document.createElement("a");
    more.className = "acc-link-more";
    more.href = "/professionnel/commandes";
    more.innerHTML = "Voir toute l'activite &#8594;";
    box.appendChild(more);
  }

  // ============================================================
  // Init
  // ============================================================
  function init() {
    var btn = $("new-request");
    if (btn) {
      btn.addEventListener("click", function () {
        window.location.href = "/professionnel/demande";
      });
    }

    load();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
'''
(STATIC / "professional_dashboard.js").write_text(DASH_JS, encoding="utf-8")
print("[OK] professional_dashboard.js refondu")

# ============================================================
# ROUTE : /professionnel/commande/{ref}/reprendre
# ============================================================
MAIN = BASE / "main.py"
src = MAIN.read_text(encoding="utf-8")
if '"/professionnel/commande/{reference}/reprendre"' not in src:
    route = '''

@app.get("/professionnel/commande/{reference}/reprendre", include_in_schema=False)
def page_pro_reprendre(reference: str):
    return FileResponse(STATIC_DIR / "professional_reprendre.html")

'''
    anchor = "\ninit_db()\n"
    if anchor in src:
        src = src.replace(anchor, route + anchor, 1)
        MAIN.write_text(src, encoding="utf-8")
        print("[OK] main.py -> route /professionnel/commande/{ref}/reprendre")

# ============================================================
# PAGE professional_reprendre.html
# ============================================================
REPRENDRE_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Reprendre une commande - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<link rel="stylesheet" href="/static/professional_accueil.css">
<style>
.rp-items{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:8px 16px;margin-top:12px}
.rp-item{display:flex;align-items:center;gap:12px;padding:14px 0;border-bottom:1px solid var(--line-soft)}
.rp-item:last-child{border-bottom:0}
.rp-item-check{
  width:22px;height:22px;border-radius:6px;border:2px solid var(--line);
  background:#fff;display:flex;align-items:center;justify-content:center;
  cursor:pointer;flex-shrink:0;transition:.15s;
}
.rp-item-check.on{background:var(--blue);border-color:var(--blue);color:#fff}
.rp-item-check.on::after{content:"\\2713";font-size:12px;font-weight:800}
.rp-item-body{flex:1;min-width:0}
.rp-item-name{font-size:14px;font-weight:700;color:var(--ink);margin:0 0 3px;word-break:break-word}
.rp-item-meta{font-size:11px;color:var(--muted);font-family:Consolas,monospace}
.rp-item-qty{display:flex;align-items:center;gap:6px;flex-shrink:0}
.rp-item-qty button{width:30px;height:30px;border:1px solid var(--line);border-radius:8px;background:#fff;font-size:14px;color:var(--ink);cursor:pointer}
.rp-item-qty button:hover{border-color:var(--blue);color:var(--blue)}
.rp-item-qty input{width:44px;text-align:center;padding:6px;border:1px solid var(--line);border-radius:8px;font-family:Consolas,monospace;font-size:14px}
.rp-item-qty input:focus{border-color:var(--blue);outline:none}
.rp-empty{padding:32px 16px;text-align:center;color:var(--muted);font-size:13px}
.rp-actions{display:flex;flex-direction:column;gap:10px;margin-top:20px}
.rp-btn{display:flex;align-items:center;justify-content:center;gap:8px;padding:15px;border:0;border-radius:13px;font-weight:800;font-size:15px;text-decoration:none;transition:.15s;width:100%;cursor:pointer;font-family:inherit}
.rp-btn-primary{background:var(--blue);color:#fff}
.rp-btn-primary:hover:not(:disabled){background:var(--blue-dark)}
.rp-btn-primary:disabled{background:#c7d5e3;cursor:not-allowed}
.rp-btn-ghost{background:#fff;color:var(--ink);border:1px solid var(--line)}
.rp-btn-ghost:hover{border-color:var(--blue);color:var(--blue)}
.rp-count{background:var(--blue-soft);color:var(--blue-dark);padding:3px 10px;border-radius:999px;font-size:11px;font-weight:800;margin-left:6px}
</style>
</head>
<body>

<header class="acc-header">
  <div class="acc-header-inner">
    <a class="acc-brand" href="/professionnel">
      <span class="acc-brand-mark">+</span>
      Elokinab
    </a>
  </div>
</header>

<main class="acc-main">
  <div class="acc-welcome">
    <h1>Reprendre une commande</h1>
    <p id="subtitle">Chargement...</p>
  </div>

  <div id="content">
    <div class="rp-empty">Chargement...</div>
  </div>

  <div class="rp-actions hidden" id="actions">
    <button class="rp-btn rp-btn-primary" id="confirm-btn" type="button">
      <span>&#10133;</span> Ajouter les produits a ma demande
    </button>
    <a class="rp-btn rp-btn-ghost" href="/professionnel">Annuler</a>
  </div>
</main>

<script src="/static/safe_locale.js"></script>
<script>
(function () {
  var API = "/api";
  var $ = function (id) { return document.getElementById(id); };

  var state = { source: null, items: [] };

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
    catch (e) { return String(n) + " F"; }
  }

  function getRef() {
    var parts = window.location.pathname.split("/");
    // /professionnel/commande/CMD-XXX/reprendre
    var idx = parts.indexOf("commande");
    if (idx >= 0 && parts[idx + 1]) return decodeURIComponent(parts[idx + 1]);
    return null;
  }

  function load() {
    var ref = getRef();
    if (!ref) {
      $("subtitle").textContent = "Reference manquante";
      $("content").innerHTML = '<div class="rp-empty">Aucune reference specifiee.</div>';
      return;
    }

    fetch(API + "/orders/" + encodeURIComponent(ref) + "/timeline", {
      credentials: "same-origin"
    }).then(function (r) {
      if (!r.ok) throw new Error("Commande introuvable");
      return r.json();
    }).then(function (tl) {
      state.source = tl;
      state.items = (tl.items || []).map(function (it) {
        return {
          product_id: it.product_id,
          product_name: it.product_name || it.description || "",
          unit_price: Number(it.unit_price) || 0,
          quantity: Math.max(1, parseInt(it.quantity) || 1),
          selected: true
        };
      });
      $("subtitle").textContent = "Commande " + tl.reference + " du " + (tl.created_at || "").slice(0, 10);
      render();
    }).catch(function (e) {
      $("content").innerHTML = '<div class="rp-empty">' + escapeHtml(e.message) + '</div>';
    });
  }

  function render() {
    var box = $("content");
    box.innerHTML = "";

    if (state.items.length === 0) {
      box.innerHTML = '<div class="rp-empty">Cette commande ne contient aucun produit.</div>';
      $("actions").classList.add("hidden");
      return;
    }

    var wrap = document.createElement("div");
    wrap.className = "rp-items";

    state.items.forEach(function (it, idx) {
      var row = document.createElement("div");
      row.className = "rp-item";

      var check = document.createElement("div");
      check.className = "rp-item-check" + (it.selected ? " on" : "");
      check.addEventListener("click", function () {
        it.selected = !it.selected;
        render();
      });

      var body = document.createElement("div");
      body.className = "rp-item-body";
      body.innerHTML =
        '<div class="rp-item-name">' + escapeHtml(it.product_name) + '</div>' +
        '<div class="rp-item-meta">' + money(it.unit_price) + ' / unite</div>';

      var qty = document.createElement("div");
      qty.className = "rp-item-qty";

      var minus = document.createElement("button");
      minus.type = "button";
      minus.textContent = "−";
      minus.addEventListener("click", function () {
        it.quantity = Math.max(1, it.quantity - 1);
        render();
      });

      var input = document.createElement("input");
      input.type = "number";
      input.min = "1";
      input.value = it.quantity;
      input.addEventListener("change", function () {
        it.quantity = Math.max(1, parseInt(input.value) || 1);
        render();
      });

      var plus = document.createElement("button");
      plus.type = "button";
      plus.textContent = "+";
      plus.addEventListener("click", function () {
        it.quantity = it.quantity + 1;
        render();
      });

      qty.appendChild(minus);
      qty.appendChild(input);
      qty.appendChild(plus);

      row.appendChild(check);
      row.appendChild(body);
      row.appendChild(qty);
      wrap.appendChild(row);
    });

    box.appendChild(wrap);
    $("actions").classList.remove("hidden");
    updateCount();
  }

  function updateCount() {
    var selected = state.items.filter(function (i) { return i.selected; });
    var btn = $("confirm-btn");
    if (selected.length === 0) {
      btn.disabled = true;
      btn.innerHTML = '<span>&#10133;</span> Selectionnez au moins un produit';
    } else {
      btn.disabled = false;
      btn.innerHTML = '<span>&#10133;</span> Ajouter ' + selected.length + ' produit' +
        (selected.length > 1 ? 's' : '') + ' a ma demande';
    }
  }

  function confirm() {
    var btn = $("confirm-btn");
    btn.disabled = true;
    btn.textContent = "Ajout en cours...";

    // 1. Recuperer ou creer le draft
    fetch(API + "/pro/requests/draft", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (draft) {
        if (!draft || !draft.reference) throw new Error("Demande indisponible");
        var ref = draft.reference;
        var toAdd = state.items.filter(function (i) { return i.selected; });

        // 2. Ajouter chaque item sequentiellement
        var chain = Promise.resolve();
        toAdd.forEach(function (it) {
          chain = chain.then(function () {
            return fetch(API + "/pro/requests/" + encodeURIComponent(ref) + "/items", {
              method: "POST",
              credentials: "same-origin",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                product_id: it.product_id || null,
                description: it.product_name,
                requested_quantity: it.quantity
              })
            }).then(function (r) {
              if (!r.ok) return r.json().then(function (d) { throw new Error(d.detail || "Erreur"); });
              return r.json();
            });
          });
        });
        return chain.then(function () { return ref; });
      })
      .then(function () {
        window.location.href = "/professionnel/demande";
      })
      .catch(function (e) {
        alert(e.message || "Erreur");
        btn.disabled = false;
        updateCount();
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    $("confirm-btn").addEventListener("click", confirm);
    load();
  });
})();
</script>
</body>
</html>
'''
(STATIC / "professional_reprendre.html").write_text(REPRENDRE_HTML, encoding="utf-8")
print("[OK] professional_reprendre.html")

print()
print("=" * 60)
print("ACCUEIL PRO REFONDU")
print("=" * 60)
print()
print("Elements livres :")
print("  A. Bienvenue personnalise (nom etablissement)")
print("  C. Action requise dynamique (paiement/refus)")
print("  D. Reprendre une commande (avec modif quantites)")
print("  F. Guide de demarrage (nouveaux uniquement)")
print("  G. Activite recente (5 dernieres commandes)")
print("  H. Support WhatsApp discret")
print()
print("Elements NON ajoutes (volontairement) :")
print("  B. Statistiques")
print("  E. Produits frequents")
print()
print("Nouveau fichier :")
print("  static/professional_accueil.css    (design system)")
print("  static/professional_reprendre.html (page reprendre)")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print()
print("Puis teste sur iPhone :")
print("  /professionnel")