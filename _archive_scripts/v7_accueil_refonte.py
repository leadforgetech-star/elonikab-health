"""
v7_accueil_refonte.py
1. Refonte complete de l'accueil pro (structure + design)
2. Fix definitif du bouton central de la navbar
3. CSS unifie sur toutes les pages pro
"""
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

# Backups
for f in ("professional.html", "professional_dashboard.js", "professional_accueil.css",
          "professional_demande.html", "professional_commandes.html",
          "professional_etablissement.html", "professional_catalogue.html",
          "professional_reprendre.html"):
    p = STATIC / f
    if p.exists():
        shutil.copy2(p, p.with_suffix(p.suffix + ".v7bak"))
print("[OK] Backups crees")

# ============================================================
# 1. CSS UNIFIE (navbar + accueil + toutes pages pro)
# ============================================================
COMMON_CSS = '''/* ============================================================
   ELOKINAB HEALTH - Design System Pro V7
   ============================================================ */
:root{
  --blue:#1A4A7E;
  --blue-dark:#0F3457;
  --blue-soft:#E8F0F8;
  --blue-line:#CDD9E8;
  --wa:#25D366;
  --wa-dark:#1DA851;
  --ok:#0A7A5A;
  --ok-soft:#E6F7F1;
  --warn:#8A5A00;
  --warn-soft:#FFF7E6;
  --warn-line:#F2D9B3;
  --danger:#B23C3C;
  --danger-soft:#FDE8E8;
  --ink:#0F172A;
  --ink-soft:#1E293B;
  --muted:#64748B;
  --muted-soft:#94A3B8;
  --line:#E2E8F0;
  --line-soft:#F1F5F9;
  --bg:#F5F8FC;
  --white:#FFFFFF;
  --radius:16px;
  --radius-sm:10px;
  --radius-lg:20px;
  --shadow-sm:0 1px 2px rgba(15,23,42,.04);
  --shadow:0 1px 3px rgba(15,23,42,.06), 0 1px 2px rgba(15,23,42,.04);
  --shadow-md:0 4px 16px rgba(15,23,42,.08);
  --shadow-lg:0 12px 40px rgba(15,23,42,.1);
}
*,*::before,*::after{box-sizing:border-box}
html,body{overflow-x:clip;margin:0;padding:0}
body{
  font-family:-apple-system,"Segoe UI",system-ui,Roboto,Helvetica,Arial,sans-serif;
  background:var(--bg);color:var(--ink);
  line-height:1.5;font-size:15px;
  -webkit-font-smoothing:antialiased;
  padding-bottom:110px;
}
a{color:inherit;text-decoration:none}
button{font-family:inherit;cursor:pointer}
.hidden{display:none !important}
img{max-width:100%;display:block}

/* ============================================================
   HEADER
   ============================================================ */
.pro-header{
  background:#fff;border-bottom:1px solid var(--line);
  position:sticky;top:0;z-index:50;
}
.pro-header-inner{
  max-width:720px;margin:0 auto;padding:14px 20px;
  display:flex;align-items:center;gap:12px;
}
.pro-brand{
  display:flex;align-items:center;gap:10px;
  font-weight:800;font-size:16px;letter-spacing:-.01em;
}
.pro-brand-mark{
  width:34px;height:34px;border-radius:10px;
  background:linear-gradient(135deg,var(--blue),#2A6BA8);color:#fff;
  display:flex;align-items:center;justify-content:center;
  font-size:18px;font-weight:800;
}
.pro-bell{
  margin-left:auto;
  width:40px;height:40px;border-radius:12px;
  border:1px solid var(--line);background:#fff;
  color:var(--ink);font-size:17px;
  display:flex;align-items:center;justify-content:center;
  position:relative;
}
.pro-bell:hover{border-color:var(--blue);color:var(--blue)}
.pro-bell-badge{
  position:absolute;top:-4px;right:-4px;
  background:var(--danger);color:#fff;
  font-size:9px;font-weight:800;
  min-width:18px;height:18px;padding:0 5px;border-radius:999px;
  display:flex;align-items:center;justify-content:center;
  border:2px solid #fff;
}

/* ============================================================
   LAYOUT
   ============================================================ */
.pro-main{
  max-width:720px;margin:0 auto;
  padding:24px 20px 40px;
}

/* ============================================================
   WELCOME
   ============================================================ */
.welcome{margin:0 0 24px}
.welcome h1{
  font-size:26px;font-weight:800;letter-spacing:-.02em;
  margin:0 0 4px;line-height:1.15;color:var(--ink);
}
.welcome .sub{
  font-size:14px;color:var(--muted);margin:0;
  line-height:1.5;
}

/* ============================================================
   CTA PRINCIPAL
   ============================================================ */
.cta-new{
  display:flex;align-items:center;justify-content:center;gap:10px;
  width:100%;padding:17px;border:0;border-radius:var(--radius);
  background:var(--blue);color:#fff;
  font-size:15px;font-weight:800;
  box-shadow:0 6px 20px rgba(26,74,126,.25);
  transition:all .15s;margin-bottom:24px;
}
.cta-new:hover{background:var(--blue-dark);transform:translateY(-1px);box-shadow:0 8px 24px rgba(26,74,126,.32)}
.cta-new:active{transform:translateY(0)}
.cta-new .ico{font-size:20px;font-weight:300;line-height:1}

/* ============================================================
   SECTION
   ============================================================ */
.section{margin-bottom:24px}
.section-title{
  font-size:11px;font-weight:800;color:var(--muted);
  text-transform:uppercase;letter-spacing:.08em;
  margin:0 0 12px;display:flex;align-items:center;
  justify-content:space-between;
}

/* ============================================================
   ALERT
   ============================================================ */
.alert-action{
  display:flex;align-items:flex-start;gap:14px;
  background:var(--warn-soft);border:1px solid var(--warn-line);
  border-left:4px solid var(--warn);
  border-radius:var(--radius);padding:16px;margin-bottom:20px;
  transition:.15s;text-decoration:none;color:inherit;
}
.alert-action:hover{transform:translateY(-1px);box-shadow:0 4px 14px rgba(138,90,0,.08)}
.alert-action.rejected{
  background:var(--danger-soft);border-color:#F6D2D2;
  border-left-color:var(--danger);
}
.alert-ico{
  width:38px;height:38px;border-radius:11px;
  background:#fff;color:var(--warn);
  display:flex;align-items:center;justify-content:center;
  font-size:18px;flex-shrink:0;
}
.alert-action.rejected .alert-ico{color:var(--danger)}
.alert-body{flex:1;min-width:0}
.alert-title{font-size:14px;font-weight:800;margin:0 0 3px;color:var(--ink)}
.alert-desc{font-size:12.5px;color:var(--muted);margin:0 0 8px;line-height:1.45}
.alert-cta{font-size:13px;font-weight:800;color:var(--warn)}
.alert-action.rejected .alert-cta{color:var(--danger)}

/* ============================================================
   REPRENDRE
   ============================================================ */
.reorder-card{
  display:flex;align-items:center;gap:14px;
  background:#fff;border:1px solid var(--line);
  border-radius:var(--radius);padding:16px;
  transition:.15s;text-decoration:none;color:inherit;
}
.reorder-card:hover{border-color:var(--blue);box-shadow:var(--shadow-md);transform:translateY(-1px)}
.reorder-icon{
  width:46px;height:46px;border-radius:13px;
  background:var(--blue-soft);color:var(--blue);
  display:flex;align-items:center;justify-content:center;
  font-size:20px;flex-shrink:0;
}
.reorder-body{flex:1;min-width:0}
.reorder-label{
  font-size:10px;font-weight:800;color:var(--muted);
  text-transform:uppercase;letter-spacing:.08em;margin:0 0 2px;
}
.reorder-ref{
  font-family:Consolas,monospace;font-weight:800;
  font-size:14px;color:var(--ink);margin:0 0 2px;
}
.reorder-meta{font-size:12px;color:var(--muted)}
.reorder-arrow{color:var(--muted);font-size:20px;flex-shrink:0}

/* ============================================================
   GUIDE
   ============================================================ */
.guide{
  background:#fff;border:1px solid var(--line);
  border-radius:var(--radius);padding:22px;
}
.guide h3{
  font-size:15px;font-weight:800;color:var(--ink);
  margin:0 0 18px;letter-spacing:-.01em;
}
.guide-steps{display:flex;flex-direction:column;gap:16px}
.guide-step{
  display:flex;align-items:flex-start;gap:14px;
}
.guide-num{
  width:32px;height:32px;border-radius:50%;
  background:var(--blue-soft);color:var(--blue);
  display:flex;align-items:center;justify-content:center;
  font-size:13px;font-weight:800;flex-shrink:0;
  border:2px solid #fff;box-shadow:0 2px 6px rgba(26,74,126,.1);
}
.guide-body{flex:1;min-width:0;padding-top:5px}
.guide-text{
  font-size:13.5px;color:var(--ink-soft);line-height:1.5;margin:0;
}
.guide-sub{
  font-size:12px;color:var(--muted);margin:6px 0 0;line-height:1.6;
  padding-left:2px;
}
.guide-sub .item{display:block}
.guide-sub strong{color:var(--ink-soft)}

/* ============================================================
   ACTIVITE
   ============================================================ */
.activity-list{
  background:#fff;border:1px solid var(--line);
  border-radius:var(--radius);overflow:hidden;
}
.activity-item{
  display:flex;align-items:center;gap:12px;
  padding:14px 16px;
  border-bottom:1px solid var(--line-soft);
  cursor:pointer;transition:.12s;text-decoration:none;color:inherit;
}
.activity-item:last-child{border-bottom:0}
.activity-item:hover{background:#FAFCFE}
.activity-body{flex:1;min-width:0}
.activity-ref{
  font-family:Consolas,monospace;font-weight:800;
  font-size:13px;color:var(--ink);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  margin:0 0 3px;
}
.activity-meta{font-size:11.5px;color:var(--muted)}
.pill{
  display:inline-flex;align-items:center;gap:5px;
  padding:4px 10px;border-radius:999px;
  font-size:10px;font-weight:800;
  text-transform:uppercase;letter-spacing:.05em;
  flex-shrink:0;
}
.pill::before{
  content:"";width:6px;height:6px;border-radius:50%;background:currentColor;
}
.pill-pending{background:var(--warn-soft);color:var(--warn)}
.pill-confirmed{background:var(--ok-soft);color:var(--ok)}
.pill-preparing{background:#F3E8FF;color:#6335B8}
.pill-ready{background:var(--ok-soft);color:var(--ok)}
.pill-done{background:#E2E8F0;color:#475569}
.pill-refused{background:var(--danger-soft);color:var(--danger)}
.pill-submitted{background:var(--blue-soft);color:var(--blue-dark)}
.pill-verified{background:var(--ok-soft);color:var(--ok)}
.pill-rejected{background:var(--danger-soft);color:var(--danger)}
.pill-none{background:#E2E8F0;color:#475569}

.empty-state{
  padding:28px 20px;text-align:center;
  font-size:13.5px;color:var(--muted);
  background:#fff;border:1px dashed var(--line);
  border-radius:var(--radius);
}
.empty-state .icon{font-size:32px;opacity:.4;margin-bottom:8px}

.link-more{
  display:inline-flex;align-items:center;gap:5px;
  margin-top:10px;font-size:13px;font-weight:800;
  color:var(--blue);
}
.link-more:hover{color:var(--blue-dark)}

/* ============================================================
   SUPPORT
   ============================================================ */
.support-card{
  display:flex;align-items:center;gap:14px;
  padding:16px;
  background:#fff;border:1px solid var(--line);
  border-radius:var(--radius);
  transition:.15s;text-decoration:none;color:inherit;
  margin-top:8px;
}
.support-card:hover{border-color:var(--wa);box-shadow:0 4px 14px rgba(37,211,102,.1)}
.support-icon{
  width:42px;height:42px;border-radius:12px;
  background:#E6F9EE;color:var(--wa-dark);
  display:flex;align-items:center;justify-content:center;
  font-size:20px;flex-shrink:0;
}
.support-body{flex:1;min-width:0}
.support-title{font-size:14px;font-weight:800;color:var(--ink);margin:0 0 2px}
.support-desc{font-size:12px;color:var(--muted);margin:0}

/* ============================================================
   NOTIFICATIONS
   ============================================================ */
.notif-list{
  background:#fff;border:1px solid var(--line);
  border-radius:var(--radius);overflow:hidden;
}
.notif-item{
  display:flex;align-items:flex-start;gap:12px;
  padding:14px 16px;
  border-bottom:1px solid var(--line-soft);
  cursor:pointer;transition:.12s;text-decoration:none;color:inherit;
}
.notif-item:last-child{border-bottom:0}
.notif-item:hover{background:#FAFCFE}
.notif-icon{
  width:34px;height:34px;border-radius:9px;
  display:flex;align-items:center;justify-content:center;
  font-size:15px;flex-shrink:0;
}
.notif-icon.payment{background:var(--ok-soft);color:var(--ok)}
.notif-icon.order{background:var(--blue-soft);color:var(--blue)}
.notif-icon.prescription{background:#F3E8FF;color:#6335B8}
.notif-icon.default{background:var(--line-soft);color:var(--muted)}
.notif-body{flex:1;min-width:0}
.notif-title{font-size:13px;font-weight:800;color:var(--ink);margin:0 0 3px;line-height:1.35}
.notif-text{font-size:12px;color:var(--muted);margin:0;line-height:1.4}
.notif-date{
  font-size:10.5px;color:var(--muted-soft);
  font-family:Consolas,monospace;margin-top:4px;
}
.mark-read{
  background:none;border:0;padding:4px 8px;border-radius:6px;
  font-size:10.5px;font-weight:800;color:var(--blue);
  text-transform:none;letter-spacing:0;cursor:pointer;font-family:inherit;
}
.mark-read:hover{background:var(--blue-soft);color:var(--blue-dark)}

/* ============================================================
   NAVBAR BASSE — bouton central propre
   ============================================================ */
.pro-navbar{
  position:fixed;bottom:0;left:0;right:0;z-index:200;
  background:#fff;border-top:1px solid var(--line);
  display:grid;
  grid-template-columns:1fr 1fr 84px 1fr 1fr;
  align-items:end;
  padding:8px 8px calc(8px + env(safe-area-inset-bottom)) 8px;
  box-shadow:0 -2px 12px rgba(15,23,42,.06);
}
.pro-navbar a{
  padding:8px 4px;text-align:center;
  font-size:10px;font-weight:700;
  color:var(--muted);
  display:flex;flex-direction:column;align-items:center;gap:3px;
  text-decoration:none;
  transition:.12s;
}
.pro-navbar a:hover{color:var(--blue-dark)}
.pro-navbar a.active{color:var(--blue-dark)}
.pro-navbar a .ico{
  font-size:20px;line-height:1;
  display:block;margin-bottom:2px;
}
.pro-navbar a.active .ico{transform:scale(1.05)}

/* --- BOUTON CENTRAL --- */
.pro-navbar .central{
  width:68px;
  height:68px;
  border-radius:50%;
  background:var(--blue);
  color:#fff !important;
  display:flex !important;
  flex-direction:column !important;
  align-items:center !important;
  justify-content:center !important;
  gap:0 !important;
  margin:0 auto !important;
  margin-top:-30px !important;
  padding:0 !important;
  border:4px solid var(--bg) !important;
  box-shadow:0 6px 18px rgba(26,74,126,.4);
  align-self:flex-start;
  transition:.15s;
  position:relative;
}
.pro-navbar .central:hover{
  background:var(--blue-dark);
  transform:translateY(-2px);
  box-shadow:0 10px 22px rgba(26,74,126,.45);
}
.pro-navbar .central .ico{
  font-size:26px !important;
  line-height:1 !important;
  font-weight:300 !important;
  color:#fff !important;
  margin:0 !important;
  padding:0 !important;
  height:26px !important;
  display:block !important;
}
.pro-navbar .central .lbl{
  font-size:9px !important;
  font-weight:700 !important;
  line-height:1 !important;
  color:#fff !important;
  margin:2px 0 0 0 !important;
  padding:0 !important;
  letter-spacing:.02em !important;
  display:block !important;
  text-transform:none !important;
}
.pro-navbar .central .nav-count{
  position:absolute;top:-4px;right:-4px;
  min-width:20px;height:20px;padding:0 5px;
  background:#fff;color:var(--blue-dark);
  border:2px solid var(--blue);
  border-radius:999px;
  font-size:10px;font-weight:900;
  display:flex;align-items:center;justify-content:center;
  box-sizing:border-box;
}
.pro-navbar .central .nav-count.hidden{display:none !important}

@media (max-width:400px){
  .pro-navbar{grid-template-columns:1fr 1fr 76px 1fr 1fr}
  .pro-navbar .central{width:62px;height:62px}
  .pro-navbar .central .ico{font-size:24px !important;height:24px !important}
}
'''

(STATIC / "professional_common.css").write_text(COMMON_CSS, encoding="utf-8")
print("[OK] professional_common.css")

# ============================================================
# 2. ACCUEIL PRO — structure + design
# ============================================================
PRO_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Espace professionnel - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<link rel="stylesheet" href="/static/professional_common.css">
</head>
<body>
<header class="pro-header">
  <div class="pro-header-inner">
    <a class="pro-brand" href="/professionnel">
      <span class="pro-brand-mark">+</span>
      Elokinab
    </a>
    <a class="pro-bell" href="/professionnel/commandes" aria-label="Notifications">
      &#128276;
      <span class="pro-bell-badge hidden" id="bell-badge">0</span>
    </a>
  </div>
</header>

<main class="pro-main">

  <!-- WELCOME -->
  <section class="welcome">
    <h1 id="hello">Bonjour</h1>
    <p class="sub">Gerez vos commandes, paiements et livraisons depuis un seul endroit.</p>
  </section>

  <!-- ALERTE ACTION -->
  <div id="alert-block"></div>

  <!-- CTA PRINCIPAL -->
  <button class="cta-new" id="new-request" type="button">
    <span class="ico">+</span> Nouvelle demande
  </button>

  <!-- NOTIFICATIONS -->
  <section class="section hidden" id="notifications-section">
    <h2 class="section-title">
      Notifications
      <button type="button" class="mark-read" id="mark-all-read">Tout marquer lu</button>
    </h2>
    <div id="notifications"></div>
  </section>

  <!-- REPRENDRE -->
  <section class="section hidden" id="reorder-section">
    <h2 class="section-title">Reprendre une commande</h2>
    <div id="reorder-block"></div>
  </section>

  <!-- GUIDE -->
  <section class="section hidden" id="guide-section">
    <h2 class="section-title">Comment commander</h2>
    <div class="guide" id="guide-block"></div>
  </section>

  <!-- ACTIVITE -->
  <section class="section" id="activity-section">
    <h2 class="section-title">Activite recente</h2>
    <div id="activity"></div>
  </section>

  <!-- SUPPORT -->
  <a class="support-card"
     href="https://wa.me/22871039904?text=Bonjour%20Elokinab%20Health%2C%20j%27ai%20une%20question."
     target="_blank" rel="noopener">
    <span class="support-icon">&#128172;</span>
    <span class="support-body">
      <span class="support-title">Besoin d'aide ?</span>
      <span class="support-desc">Contacter Elokinab sur WhatsApp</span>
    </span>
  </a>

</main>

<!-- NAVBAR -->
<nav class="pro-navbar">
  <a href="/professionnel" class="active">
    <span class="ico">&#127968;</span>
    Accueil
  </a>
  <a href="/professionnel/catalogue">
    <span class="ico">&#128722;</span>
    Catalogue
  </a>
  <a href="/professionnel/demande" class="central" id="nav-central" aria-label="Nouvelle demande">
    <span class="ico">+</span>
    <span class="lbl">Demande</span>
    <span class="nav-count hidden" id="nav-count">0</span>
  </a>
  <a href="/professionnel/commandes">
    <span class="ico">&#128230;</span>
    Commandes
  </a>
  <a href="/professionnel/etablissement">
    <span class="ico">&#127970;</span>
    Etabl.
  </a>
</nav>

<script src="/static/safe_locale.js"></script>
<script src="/static/professional_dashboard.js"></script>
</body>
</html>
'''
(STATIC / "professional.html").write_text(PRO_HTML, encoding="utf-8")
print("[OK] professional.html")

# ============================================================
# 3. JS accueil pro
# ============================================================
DASH_JS = r'''/* Elokinab Health - Accueil professionnel V7 */
(function () {
  "use strict";
  var API = "/api";
  var $ = function (id) { return document.getElementById(id); };

  var state = {
    org: null,
    orders: [],
    stats: {
      total: 0,
      last_order: null,
      alert_type: null,
      alert_order: null
    }
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

  var STATUS_PILLS = {
    en_attente: "pill-pending", confirmee: "pill-confirmed",
    en_preparation: "pill-preparing", prete: "pill-ready",
    terminee: "pill-done", refusee: "pill-refused"
  };
  var STATUS_LABELS = {
    en_attente: "En attente", confirmee: "Confirmee",
    en_preparation: "En preparation", prete: "Prete",
    terminee: "Terminee", refusee: "Refusee"
  };
  var PAYMENT_PILLS = {
    NONE: "pill-none", PENDING: "pill-pending",
    PROOF_SUBMITTED: "pill-submitted",
    VERIFIED: "pill-verified", REJECTED: "pill-rejected"
  };

  // ============================================================
  // LOAD
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

      state.orders = orders.filter(function (o) {
        return o.status !== "DRAFT" && o.status !== "draft";
      });

      renderBell(notifs.length);
      analyze();
      renderWelcome();
      renderAlert();
      renderReorder();
      renderGuide();
      renderActivity();
      loadNotifications();
    }).catch(function (e) {
      console.error("[accueil] load error", e);
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

  function analyze() {
    var st = { total: state.orders.length, last_order: null,
               alert_type: null, alert_order: null };
    var sorted = state.orders.slice().sort(function (a, b) {
      return (b.created_at || "").localeCompare(a.created_at || "");
    });
    if (sorted.length > 0) st.last_order = sorted[0];

    var rejected = null, pending = null;
    sorted.forEach(function (o) {
      var ps = o.payment_status || "NONE";
      if (ps === "REJECTED" && !rejected) rejected = o;
      if (ps === "PENDING" && o.status !== "refusee" && !pending) pending = o;
    });
    if (rejected) { st.alert_type = "rejected"; st.alert_order = rejected; }
    else if (pending) { st.alert_type = "pending"; st.alert_order = pending; }

    state.stats = st;
  }

  // ============================================================
  // RENDERS
  // ============================================================
  function renderWelcome() {
    var h = $("hello");
    if (!h) return;
    var name = (state.org && state.org.structure_name) || "Professionnel";
    h.textContent = "Bonjour, " + name;
  }

  function renderAlert() {
    var box = $("alert-block");
    if (!box) return;
    box.innerHTML = "";
    if (!state.stats.alert_type || !state.stats.alert_order) return;

    var o = state.stats.alert_order;
    var total = (Number(o.subtotal) || 0) + (Number(o.delivery_fee) || 0);
    var isRejected = state.stats.alert_type === "rejected";

    var a = document.createElement("a");
    a.className = "alert-action" + (isRejected ? " rejected" : "");
    a.href = "/static/payment.html?ref=" + encodeURIComponent(o.reference);

    if (isRejected) {
      a.innerHTML =
        '<div class="alert-ico">&#9888;</div>' +
        '<div class="alert-body">' +
        '<h3 class="alert-title">Preuve de paiement refusee</h3>' +
        '<p class="alert-desc">Commande <strong>' + escapeHtml(o.reference) + '</strong> - ' + money(total) + '. Renvoyez une preuve valide.</p>' +
        '<span class="alert-cta">Renvoyer une preuve &#8594;</span>' +
        '</div>';
    } else {
      a.innerHTML =
        '<div class="alert-ico">&#9200;</div>' +
        '<div class="alert-body">' +
        '<h3 class="alert-title">Paiement en attente</h3>' +
        '<p class="alert-desc">Commande <strong>' + escapeHtml(o.reference) + '</strong> - ' + money(total) + '. Effectuez le transfert pour lancer la preparation.</p>' +
        '<span class="alert-cta">Payer maintenant &#8594;</span>' +
        '</div>';
    }
    box.appendChild(a);
  }

  function renderReorder() {
    var section = $("reorder-section");
    var box = $("reorder-block");
    if (!section || !box) return;
    var last = state.stats.last_order;
    if (!last) { section.classList.add("hidden"); return; }

    section.classList.remove("hidden");
    var itemsCount = last.items_count || 1;
    var a = document.createElement("a");
    a.className = "reorder-card";
    a.href = "/professionnel/commande/" + encodeURIComponent(last.reference) + "/reprendre";
    a.innerHTML =
      '<div class="reorder-icon">&#128257;</div>' +
      '<div class="reorder-body">' +
      '<div class="reorder-label">Derniere commande</div>' +
      '<div class="reorder-ref">' + escapeHtml(last.reference) + '</div>' +
      '<div class="reorder-meta">' + escapeHtml(fmtDate(last.created_at)) + ' - ' + itemsCount + ' produit' + (itemsCount > 1 ? 's' : '') + '</div>' +
      '</div>' +
      '<span class="reorder-arrow">&#8594;</span>';
    box.innerHTML = "";
    box.appendChild(a);
  }

  function renderGuide() {
    var section = $("guide-section");
    var box = $("guide-block");
    if (!section || !box) return;
    if (state.orders.length > 0) { section.classList.add("hidden"); return; }

    section.classList.remove("hidden");
    box.innerHTML =
      '<h3>Comment commander sur Elokinab ?</h3>' +
      '<div class="guide-steps">' +
        '<div class="guide-step">' +
          '<div class="guide-num">1</div>' +
          '<div class="guide-body">' +
            '<p class="guide-text">Ouvrez l\u2019onglet <strong>+ Demande</strong> puis choisissez votre methode :</p>' +
            '<p class="guide-sub">' +
              '<span class="item">&#8226; <strong>Catalogue</strong> : ajoutez vos produits un par un</span>' +
              '<span class="item">&#8226; <strong>WhatsApp</strong> : envoyez votre liste (texte, photo ou PDF)</span>' +
            '</p>' +
          '</div>' +
        '</div>' +
        '<div class="guide-step">' +
          '<div class="guide-num">2</div>' +
          '<div class="guide-body"><p class="guide-text">Validez le recapitulatif et envoyez votre demande.</p></div>' +
        '</div>' +
        '<div class="guide-step">' +
          '<div class="guide-num">3</div>' +
          '<div class="guide-body"><p class="guide-text">Reglez par <strong>Mixx</strong> ou <strong>Flooz</strong>, puis envoyez la preuve de paiement.</p></div>' +
        '</div>' +
        '<div class="guide-step">' +
          '<div class="guide-num">4</div>' +
          '<div class="guide-body"><p class="guide-text">Recevez votre commande apres validation de la pharmacie.</p></div>' +
        '</div>' +
      '</div>';
  }

  function renderActivity() {
    var box = $("activity");
    if (!box) return;

    var sorted = state.orders.slice().sort(function (a, b) {
      return (b.created_at || "").localeCompare(a.created_at || "");
    }).slice(0, 5);

    if (sorted.length === 0) {
      box.innerHTML =
        '<div class="empty-state">' +
          '<div class="icon">&#128230;</div>' +
          'Aucune commande pour le moment.<br>' +
          'Vos futures commandes apparaitront ici.' +
        '</div>';
      return;
    }

    var wrap = document.createElement("div");
    wrap.className = "activity-list";
    sorted.forEach(function (o) {
      var pill = STATUS_PILLS[o.status] || "pill-none";
      var lbl = STATUS_LABELS[o.status] || o.status;
      var total = (Number(o.subtotal) || 0) + (Number(o.delivery_fee) || 0);

      var a = document.createElement("a");
      a.className = "activity-item";
      a.href = "/suivi?ref=" + encodeURIComponent(o.reference);
      a.innerHTML =
        '<div class="activity-body">' +
          '<div class="activity-ref">' + escapeHtml(o.reference) + '</div>' +
          '<div class="activity-meta">' + escapeHtml(fmtDate(o.created_at)) + ' - ' + money(total) + '</div>' +
        '</div>' +
        '<span class="pill ' + pill + '">' + escapeHtml(lbl) + '</span>';
      wrap.appendChild(a);
    });
    box.innerHTML = "";
    box.appendChild(wrap);

    if (state.orders.length > 5) {
      var more = document.createElement("a");
      more.className = "link-more";
      more.href = "/professionnel/commandes";
      more.innerHTML = "Voir toute l\u2019activite &#8594;";
      box.appendChild(more);
    }
  }

  // ============================================================
  // NOTIFICATIONS
  // ============================================================
  function notifIcon(type) {
    if (type === "payment") return { cls: "payment", char: "\uD83D\uDCB0" };
    if (type === "order") return { cls: "order", char: "\uD83D\uDCE6" };
    if (type === "prescription") return { cls: "prescription", char: "\u2695\uFE0F" };
    return { cls: "default", char: "\uD83D\uDD14" };
  }
  function notifTypeFromData(n) {
    var t = String(n.title || "").toLowerCase();
    if (t.indexOf("paiement") >= 0) return "payment";
    if (t.indexOf("commande") >= 0) return "order";
    if (t.indexOf("ordonnance") >= 0) return "prescription";
    return "default";
  }

  function loadNotifications() {
    return api("/notifications?unread_only=1")
      .then(function (list) { renderNotifications(Array.isArray(list) ? list : []); })
      .catch(function () { renderNotifications([]); });
  }

  function renderNotifications(list) {
    var section = $("notifications-section");
    var box = $("notifications");
    if (!section || !box) return;

    if (!list || list.length === 0) {
      section.classList.add("hidden");
      box.innerHTML = "";
      return;
    }
    section.classList.remove("hidden");

    var wrap = document.createElement("div");
    wrap.className = "notif-list";

    list.slice(0, 4).forEach(function (n) {
      var icon = notifIcon(notifTypeFromData(n));
      var target = "/suivi";
      var m = String(n.body || "").match(/CMD-[0-9]{6}-[A-Z0-9]+/);
      if (m) target = "/suivi?ref=" + encodeURIComponent(m[0]);
      else if (n.order_id) target = "#";

      var dateStr = "";
      try {
        var d = new Date(n.created_at);
        if (!isNaN(d.getTime())) {
          var pad = function (x) { return x < 10 ? "0" + x : "" + x; };
          dateStr = pad(d.getDate()) + "/" + pad(d.getMonth() + 1) +
                    " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
        }
      } catch (e) {}

      var a = document.createElement("a");
      a.className = "notif-item";
      a.href = target;
      a.setAttribute("data-notif-id", String(n.id));
      a.innerHTML =
        '<div class="notif-icon ' + icon.cls + '">' + icon.char + '</div>' +
        '<div class="notif-body">' +
          '<div class="notif-title">' + escapeHtml(n.title || "Notification") + '</div>' +
          '<div class="notif-text">' + escapeHtml(n.body || "") + '</div>' +
          '<div class="notif-date">' + escapeHtml(dateStr) + '</div>' +
        '</div>';
      a.addEventListener("click", function () {
        var id = a.getAttribute("data-notif-id");
        if (!id) return;
        fetch(API + "/notifications/" + id + "/read", {
          method: "PATCH", credentials: "same-origin"
        }).catch(function () {});
      });
      wrap.appendChild(a);
    });

    box.innerHTML = "";
    box.appendChild(wrap);

    var btn = $("mark-all-read");
    if (btn) {
      var newBtn = btn.cloneNode(true);
      btn.parentNode.replaceChild(newBtn, btn);
      newBtn.addEventListener("click", function (ev) {
        ev.preventDefault();
        fetch(API + "/notifications/read-all", {
          method: "PATCH", credentials: "same-origin"
        }).then(function () {
          renderNotifications([]);
          renderBell(0);
        }).catch(function () {});
      });
    }
  }

  // ============================================================
  // NAV COUNT
  // ============================================================
  function loadNavCount() {
    fetch(API + "/pro/requests/draft", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) return;
        return fetch(API + "/pro/requests/" + d.reference, { credentials: "same-origin" })
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (full) {
            if (!full) return;
            var n = (full.items || []).length + (full.attachments || []).length;
            var c = $("nav-count");
            if (c && n > 0) {
              c.textContent = n > 99 ? "99+" : String(n);
              c.classList.remove("hidden");
            }
          });
      }).catch(function () {});
  }

  // ============================================================
  // INIT
  // ============================================================
  function init() {
    var btn = $("new-request");
    if (btn) {
      btn.addEventListener("click", function () {
        window.location.href = "/professionnel/demande";
      });
    }
    load();
    loadNavCount();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
'''
(STATIC / "professional_dashboard.js").write_text(DASH_JS, encoding="utf-8")
print("[OK] professional_dashboard.js")

# ============================================================
# 4. Mettre a jour la navbar des AUTRES pages pro
# ============================================================
NAVBAR_HTML = '''<nav class="pro-navbar">
  <a href="/professionnel"%s><span class="ico">&#127968;</span>Accueil</a>
  <a href="/professionnel/catalogue"%s><span class="ico">&#128722;</span>Catalogue</a>
  <a href="/professionnel/demande" class="central" id="nav-central"%s aria-label="Nouvelle demande">
    <span class="ico">+</span>
    <span class="lbl">Demande</span>
    <span class="nav-count hidden" id="nav-count">0</span>
  </a>
  <a href="/professionnel/commandes"%s><span class="ico">&#128230;</span>Commandes</a>
  <a href="/professionnel/etablissement"%s><span class="ico">&#127970;</span>Etabl.</a>
</nav>
'''

import re as _re

def update_navbar(page_name, active):
    p = STATIC / page_name
    if not p.exists(): return
    html = p.read_text(encoding="utf-8")

    # Retirer ancien CSS navbar specifique s'il existe
    html = _re.sub(
        r"\.pro-navbar\s*\{[^}]*\}",
        "",
        html
    )
    html = _re.sub(
        r"\.pro-navbar\s+\.central[^}]*\}",
        "",
        html, flags=_re.DOTALL
    )
    html = _re.sub(
        r"\.pro-navbar\s+a\s*\{[^}]*\}",
        "",
        html
    )

    # Remplacer le link CSS pour pointer vers le CSS commun
    if 'href="/static/professional_common.css"' not in html:
        if "</head>" in html:
            html = html.replace(
                "</head>",
                '<link rel="stylesheet" href="/static/professional_common.css">\n</head>',
                1
            )

    new_navbar = NAVBAR_HTML % (
        ' class="active"' if active == "accueil" else '',
        ' class="active"' if active == "catalogue" else '',
        ' class="active"' if active == "demande" else '',
        ' class="active"' if active == "commandes" else '',
        ' class="active"' if active == "etablissement" else '',
    )

    pattern = _re.compile(r'<nav class="pro-navbar">.*?</nav>', _re.DOTALL)
    if pattern.search(html):
        html = pattern.sub(new_navbar, html, count=1)
    else:
        html = html.replace("</body>", new_navbar + "\n</body>", 1)

    p.write_text(html, encoding="utf-8")
    print(f"[OK] {page_name} -> navbar mise a jour")

update_navbar("professional_demande.html", "demande")
update_navbar("professional_commandes.html", "commandes")
update_navbar("professional_etablissement.html", "etablissement")
update_navbar("professional_catalogue.html", "catalogue")

# ============================================================
# 5. Verification
# ============================================================
print()
print("=" * 60)
print("REFONTE ACCUEIL PRO V7 LIVREE")
print("=" * 60)
print()
print("Accueil :")
print("  - Bienvenue propre")
print("  - Alerte action (si besoin)")
print("  - CTA principal (+ Nouvelle demande)")
print("  - Notifications (si non lues)")
print("  - Reprendre une commande")
print("  - Guide (nouveaux seulement)")
print("  - Activite recente")
print("  - Support WhatsApp")
print()
print("Navbar :")
print("  - Bouton central 68x68 rond, + / Demande empiles")
print("  - CSS unifie dans professional_common.css")
print("  - Applique sur toutes les pages pro")
print()
print("=" * 60)
print("PROCHAINE ETAPE :")
print("  1. Ctrl+Shift+Suppr -> vider le cache Edge")
print("  2. Ctrl+Shift+R sur /professionnel")
print("=" * 60)