"""
v4_dashboard_split.py
Separe Accueil (dashboard) et + Demande (espace de travail).
- /professionnel              -> dashboard
- /professionnel/demande      -> espace de travail
- Navbar unifiee partout
- Catalogue : "Ajouter a ma demande" pointe vers la demande en cours
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
MAIN = BASE / "main.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_split_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
for f in ("professional.html", "professional.js", "professional_catalogue.html",
          "professional_commandes.html", "professional_etablissement.html"):
    p = STATIC / f
    if p.exists():
        shutil.copy2(p, backup / f)
shutil.copy2(MAIN, backup / "main.py")
print("[OK] Backup ->", backup.name)

# ============================================================
# NAVBAR COMMUNE (reutilisee dans toutes les pages)
# ============================================================
NAVBAR_CSS = '''
/* ---- Navbar basse commune ---- */
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
.pro-navbar a.active{color:var(--green-dark)}
.pro-navbar .central{
  margin-top:-22px;background:var(--green);color:#fff;border-radius:50%;
  width:64px;height:64px;justify-self:center;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  font-size:22px;font-weight:800;box-shadow:0 6px 20px rgba(26,74,127,.35);
  border:4px solid var(--bg);position:relative;
}
.pro-navbar .central .lbl{font-size:9px;font-weight:700;margin-top:-2px}
.pro-navbar .central .nav-count{
  position:absolute;top:-4px;right:-4px;
  min-width:22px;height:22px;padding:0 6px;
  background:#fff;color:var(--green-dark);
  border:2px solid var(--green);
  border-radius:999px;font-size:11px;font-weight:900;
  display:flex;align-items:center;justify-content:center;
}
.pro-navbar .central .nav-count.hidden{display:none}
.pro-navbar .central.active{background:var(--green-dark);}
'''

NAVBAR_JS = '''
(function () {
  function loadNavCount() {
    fetch("/api/pro/requests/draft", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) return;
        return fetch("/api/pro/requests/" + d.reference, { credentials: "same-origin" })
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (full) {
            if (!full) return;
            var n = (full.items || []).length + (full.attachments || []).length;
            var c = document.getElementById("nav-count");
            if (c && n > 0) { c.textContent = n > 99 ? "99+" : String(n); c.classList.remove("hidden"); }
          });
      }).catch(function () {});
  }
  document.addEventListener("DOMContentLoaded", loadNavCount);
})();
'''

def navbar(active):
    """Genere la navbar avec l'onglet actif."""
    def cls(name):
        return ' class="' + ("active" if active == name else "") + '"' if active == name else ""
    def cls_central():
        return ' class="central' + (" active" if active == "demande" else "") + '"'
    return '''
<nav class="pro-navbar">
  <a href="/professionnel"%s>
    <span class="ico">&#127968;</span> Accueil
  </a>
  <a href="/professionnel/catalogue"%s>
    <span class="ico">&#128722;</span> Catalogue
  </a>
  <a href="/professionnel/demande"%s id="nav-central">
    <span>+</span><span class="lbl">Demande</span>
    <span class="nav-count hidden" id="nav-count">0</span>
  </a>
  <a href="/professionnel/commandes"%s>
    <span class="ico">&#128230;</span> Commandes
  </a>
  <a href="/professionnel/etablissement"%s>
    <span class="ico">&#127970;</span> Etabl.
  </a>
</nav>
<script>%s</script>
''' % (cls("accueil"), cls("catalogue"), cls_central(), cls("commandes"), cls("etablissement"), NAVBAR_JS)

# ============================================================
# 1. DASHBOARD (/professionnel)
# ============================================================
DASH_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Accueil - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
:root{
  --green:#1a4a7f;--green-dark:#123258;--green-soft:#eaf1f9;
  --ink:#0f172a;--muted:#64748b;--line:#e6ebf1;--bg:#f7fafc;
  --radius:14px;--shadow:0 1px 3px rgba(15,23,42,.06);
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

.dash-header{
  background:#fff;border-bottom:1px solid var(--line);
  position:sticky;top:0;z-index:50;
}
.dash-header-inner{
  max-width:900px;margin:0 auto;padding:12px 16px;
  display:flex;align-items:center;gap:12px;
}
.dash-brand{display:flex;align-items:center;gap:8px;font-weight:800;font-size:15px}
.dash-brand-mark{
  width:30px;height:30px;border-radius:8px;
  background:linear-gradient(135deg,var(--green),#2a6ba8);color:#fff;
  display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:800;
}
.dash-bell{
  margin-left:auto;width:36px;height:36px;border-radius:10px;
  border:1px solid var(--line);background:#fff;
  display:flex;align-items:center;justify-content:center;
  color:var(--ink);font-size:16px;position:relative;
}
.dash-bell-badge{
  position:absolute;top:-3px;right:-3px;background:#dc2626;
  color:#fff;font-size:9px;font-weight:800;min-width:16px;
  height:16px;padding:0 4px;border-radius:999px;
  display:flex;align-items:center;justify-content:center;
}

.dash-main{max-width:900px;margin:0 auto;padding:20px 16px 40px}

.hero-hello{margin:0 0 6px;font-size:24px;letter-spacing:-.02em}
.hero-info{font-size:14px;color:var(--muted);margin:0 0 22px;display:flex;gap:6px;flex-wrap:wrap}
.hero-info span{display:inline-flex;align-items:center;gap:4px}

/* --- Carte demande en cours --- */
.draft-card{
  background:linear-gradient(135deg,#1a4a7f,#2a6ba8);color:#fff;
  border-radius:16px;padding:20px;margin-bottom:16px;
  box-shadow:0 4px 20px rgba(26,74,127,.25);
  cursor:pointer;
}
.draft-card:hover{transform:translateY(-1px);box-shadow:0 6px 24px rgba(26,74,127,.32)}
.draft-card-head{
  font-size:11px;text-transform:uppercase;letter-spacing:.08em;
  opacity:.8;font-weight:800;margin:0 0 8px;
}
.draft-card-ref{font-family:Consolas,monospace;font-size:14px;opacity:.9;margin:0 0 10px}
.draft-card-count{font-size:22px;font-weight:800;margin:0 0 14px}
.draft-card-cta{
  display:inline-flex;align-items:center;gap:6px;
  background:#fff;color:var(--green-dark);padding:10px 16px;
  border-radius:10px;font-weight:800;font-size:14px;
}

/* --- Bouton principal --- */
.btn-new{
  display:flex;align-items:center;justify-content:center;gap:8px;
  width:100%;padding:16px;border:0;border-radius:14px;
  background:var(--green);color:#fff;
  font-size:15px;font-weight:800;
  margin-bottom:22px;
  box-shadow:0 4px 14px rgba(26,74,127,.2);
  transition:.15s;
}
.btn-new:hover{background:var(--green-dark);transform:translateY(-1px)}

/* --- Section --- */
.section{margin-bottom:24px}
.section-title{
  font-size:11px;text-transform:uppercase;letter-spacing:.08em;
  color:var(--muted);font-weight:800;margin:0 0 10px;
}

/* --- Carte generique --- */
.card{
  background:#fff;border:1px solid var(--line);border-radius:var(--radius);
  padding:16px;
}

/* --- Commander a nouveau --- */
.reorder-card{
  display:flex;align-items:center;gap:14px;cursor:pointer;
  background:#fff;border:1px solid var(--line);border-radius:var(--radius);
  padding:16px;transition:.15s;
}
.reorder-card:hover{border-color:var(--green);box-shadow:var(--shadow)}
.reorder-icon{
  width:44px;height:44px;border-radius:12px;
  background:var(--green-soft);color:var(--green);
  display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;
}
.reorder-body{flex:1;min-width:0}
.reorder-title{font-size:14px;font-weight:800;margin:0 0 2px}
.reorder-meta{font-size:12px;color:var(--muted)}
.reorder-arrow{color:var(--muted);font-size:18px}

/* --- Activite recente --- */
.activity-list{background:#fff;border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}
.activity-item{
  display:flex;align-items:center;gap:12px;padding:14px 16px;
  border-bottom:1px solid var(--line);cursor:pointer;transition:.15s;
}
.activity-item:last-child{border-bottom:0}
.activity-item:hover{background:#fafbfc}
.activity-ref{font-family:Consolas,monospace;font-weight:800;font-size:13px;color:var(--ink)}
.activity-meta{font-size:11px;color:var(--muted);margin-top:2px}
.activity-body{flex:1;min-width:0}
.badge{
  font-size:10px;font-weight:800;padding:4px 9px;border-radius:999px;
  text-transform:uppercase;letter-spacing:.05em;flex-shrink:0;
}
.badge.draft{background:#fff7e6;color:#8a5a00}
.badge.submitted{background:#eaf1f9;color:#1a4a7f}
.badge.confirmed{background:#e6f7f1;color:#0a7a5a}
.badge.partially_confirmed{background:#f3e8ff;color:#6335b8}
.badge.rejected{background:#fee2e2;color:#b23c3c}
.badge.delivered{background:#e2e8f0;color:#475569}

.empty-state{
  text-align:center;padding:26px 16px;color:var(--muted);font-size:14px;
}
.empty-icon{font-size:36px;opacity:.3;margin-bottom:8px}

.link-more{
  display:inline-block;color:var(--green);font-weight:800;font-size:13px;
  margin-top:10px;
}
.link-more:hover{color:var(--green-dark)}

''' + NAVBAR_CSS + '''
</style>
</head>
<body>

<header class="dash-header">
  <div class="dash-header-inner">
    <div class="dash-brand">
      <span class="dash-brand-mark">+</span>
      Elokinab
    </div>
    <a class="dash-bell" href="/professionnel/commandes" aria-label="Commandes">
      &#128276;
      <span class="dash-bell-badge hidden" id="bell-badge">0</span>
    </a>
  </div>
</header>

<main class="dash-main">

  <h1 class="hero-hello" id="hello">Bonjour</h1>
  <div class="hero-info">
    <span id="org-type">&#127973; Etablissement</span>
    <span id="org-address">&#128205; Togo</span>
  </div>

  <!-- Demande en cours (si existe) -->
  <div id="draft-block"></div>

  <!-- Action principale -->
  <button class="btn-new" id="new-request" type="button">
    <span>&#10133;</span> Nouvelle demande
  </button>

  <!-- Commander a nouveau -->
  <div class="section" id="reorder-section">
    <h2 class="section-title">Commander a nouveau</h2>
    <div id="reorder-block"></div>
  </div>

  <!-- Activite recente -->
  <div class="section">
    <h2 class="section-title">Activite recente</h2>
    <div id="activity"></div>
    <a class="link-more" href="/professionnel/commandes">Voir toutes mes commandes &#8594;</a>
  </div>

</main>

''' + navbar("accueil") + '''
<script src="/static/professional_dashboard.js"></script>
</body>
</html>
'''
(STATIC / "professional.html").write_text(DASH_HTML, encoding="utf-8")
print("[OK] professional.html -> dashboard")

# ============================================================
# 2. ESPACE DEMANDE (/professionnel/demande)
# ============================================================
DEM_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Ma demande - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
:root{
  --green:#1a4a7f;--green-dark:#123258;--green-soft:#eaf1f9;
  --ink:#0f172a;--muted:#64748b;--line:#e6ebf1;--bg:#f7fafc;
  --radius:14px;--shadow:0 1px 3px rgba(15,23,42,.06);
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

.dem-header{
  background:#fff;border-bottom:1px solid var(--line);
  position:sticky;top:0;z-index:50;
}
.dem-header-inner{
  max-width:900px;margin:0 auto;padding:12px 16px;
  display:flex;align-items:center;gap:12px;
}
.dem-back{
  width:36px;height:36px;border-radius:10px;border:1px solid var(--line);
  background:#fff;color:var(--ink);font-size:18px;
  display:flex;align-items:center;justify-content:center;text-decoration:none;
}
.dem-title{font-size:15px;font-weight:800}
.dem-ref{margin-left:auto;font-family:Consolas,monospace;font-size:12px;color:var(--muted)}

.dem-main{max-width:900px;margin:0 auto;padding:16px}

.dem-head-card{
  background:#fff;border:1px solid var(--line);border-radius:var(--radius);
  padding:14px 16px;margin-bottom:14px;
  display:flex;align-items:center;justify-content:space-between;gap:10px;
}
.dem-head-ref{font-family:Consolas,monospace;font-weight:800;font-size:14px}
.dem-head-count{
  font-size:12px;background:var(--green-soft);color:var(--green-dark);
  padding:4px 10px;border-radius:999px;font-weight:800;
}

.section-title{
  font-size:11px;text-transform:uppercase;letter-spacing:.08em;
  color:var(--muted);font-weight:800;margin:18px 0 10px;
}

/* --- Sources --- */
.sources-grid{
  display:grid;grid-template-columns:1fr 1fr;gap:10px;
}
.source-btn{
  display:flex;flex-direction:column;align-items:flex-start;gap:8px;
  padding:14px;border:1px solid var(--line);border-radius:12px;
  background:#fff;color:var(--ink);text-align:left;cursor:pointer;
  transition:.15s;min-height:88px;
}
.source-btn:hover{border-color:var(--green);background:#fafdfb}
.source-icon{
  width:36px;height:36px;border-radius:10px;
  background:var(--green-soft);color:var(--green);
  display:flex;align-items:center;justify-content:center;font-size:18px;
}
.source-label{font-size:13px;font-weight:800;line-height:1.2}
.source-hint{font-size:11px;color:var(--muted);line-height:1.3}

/* --- Items --- */
.item-row{
  display:flex;align-items:flex-start;gap:10px;padding:12px 14px;
  background:#fff;border:1px solid var(--line);border-radius:12px;
  margin-bottom:8px;
}
.item-body{flex:1;min-width:0}
.item-name{font-size:14px;font-weight:700;margin:0 0 2px;word-break:break-word}
.item-meta{font-size:11px;color:var(--muted)}
.item-qty{
  font-family:Consolas,monospace;font-weight:800;color:var(--green-dark);
  font-size:14px;margin-right:4px;
}
.item-actions{display:flex;gap:4px;flex-shrink:0}
.item-btn{
  width:30px;height:30px;border:1px solid var(--line);border-radius:8px;
  background:#fff;font-size:14px;color:var(--ink);
  display:flex;align-items:center;justify-content:center;
}
.item-btn:hover{border-color:var(--green);color:var(--green-dark)}
.item-btn.del:hover{border-color:#dc2626;color:#dc2626;background:#fee2e2}

.att-row{
  display:flex;align-items:center;gap:10px;padding:10px 12px;
  background:#fff;border:1px solid var(--line);border-radius:10px;
  margin-bottom:6px;
}
.att-icon{
  width:32px;height:32px;border-radius:8px;
  background:var(--green-soft);color:var(--green);
  display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0;
}
.att-body{flex:1;min-width:0}
.att-name{font-size:13px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.att-meta{font-size:11px;color:var(--muted)}
.att-del{background:none;border:0;color:#dc2626;font-size:16px;cursor:pointer;padding:4px}

/* --- Notes --- */
.notes{
  width:100%;padding:12px 14px;border:1px solid var(--line);border-radius:12px;
  font-family:inherit;font-size:14px;background:#fff;outline:none;
  resize:vertical;min-height:70px;
}
.notes:focus{border-color:var(--green)}

/* --- Actions bas --- */
.dem-actions{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap}
.dem-send{
  flex:1;min-width:180px;padding:15px;border:0;border-radius:12px;
  background:#25d366;color:#fff;font-weight:800;font-size:15px;
  display:flex;align-items:center;justify-content:center;gap:8px;
}
.dem-send:hover{background:#1da851}
.dem-send:disabled{background:#c9e5d4;cursor:not-allowed}
.dem-clear{
  padding:15px 20px;border:1px solid var(--line);background:#fff;border-radius:12px;
  font-weight:700;font-size:14px;color:var(--muted);
}

/* --- Modales --- */
.modal{position:fixed;inset:0;z-index:900;display:flex;align-items:flex-end;justify-content:center}
.modal.hidden{display:none}
.modal-bg{position:absolute;inset:0;background:rgba(15,23,42,.55)}
.modal-panel{
  position:relative;background:#fff;width:100%;max-width:600px;
  max-height:92vh;border-radius:20px 20px 0 0;
  display:flex;flex-direction:column;overflow:hidden;
  animation:slideUp .22s ease;
}
@keyframes slideUp{from{transform:translateY(30px);opacity:.5}to{transform:translateY(0);opacity:1}}
.modal-head{
  padding:16px 20px;border-bottom:1px solid var(--line);
  display:flex;align-items:center;justify-content:space-between;
}
.modal-head h3{margin:0;font-size:16px}
.modal-close{background:none;border:0;font-size:26px;color:var(--muted);cursor:pointer;padding:0 4px}
.modal-body{padding:18px 20px;overflow-y:auto;flex:1}
.modal-foot{
  padding:14px 20px;border-top:1px solid var(--line);background:var(--bg);
  display:flex;gap:10px;
}
.modal-foot button{flex:1;padding:13px;border:0;border-radius:11px;font-weight:800;font-size:14px}

.field{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.field label{font-size:13px;font-weight:700}
.field input,.field textarea{
  padding:12px 14px;border:1px solid var(--line);border-radius:11px;
  font-family:inherit;font-size:15px;outline:none;background:#fff;width:100%;
}
.field input:focus,.field textarea:focus{border-color:var(--green)}

.upload{
  border:2px dashed var(--line);border-radius:12px;padding:22px 14px;
  text-align:center;background:#fafdfb;cursor:pointer;display:block;
}
.upload:hover{border-color:var(--green);background:var(--green-soft)}
.upload input{display:none}
.upload-icon{font-size:30px;margin-bottom:6px}
.upload-title{font-size:14px;font-weight:700;margin:0 0 4px}
.upload-hint{font-size:12px;color:var(--muted);margin:0}

.err{padding:10px 12px;background:#fee2e2;color:#b23c3c;border:1px solid #f6d2d2;
  border-radius:10px;font-size:13px;margin-top:10px}
.err.hidden{display:none}

/* --- Choice buttons dans modal --- */
.choice{
  display:flex;align-items:center;gap:14px;padding:14px;
  border:1px solid var(--line);border-radius:12px;background:#fff;
  width:100%;text-align:left;margin-bottom:10px;cursor:pointer;
}
.choice:hover{border-color:var(--green);background:#fafdfb}
.choice-icon{
  width:42px;height:42px;border-radius:11px;
  background:var(--green-soft);color:var(--green);
  display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;
}
.choice-body{flex:1;min-width:0}
.choice-title{font-size:14px;font-weight:800;margin:0 0 2px}
.choice-desc{font-size:12px;color:var(--muted);margin:0}
.choice-arrow{color:var(--muted);font-size:18px}

/* --- Catalogue dans modale --- */
.cat-search{
  width:100%;padding:12px 14px;border:1px solid var(--line);border-radius:11px;
  font-family:inherit;font-size:15px;outline:none;margin-bottom:12px;
}
.cat-search:focus{border-color:var(--green)}
.cat-item{
  display:flex;gap:12px;padding:10px 0;border-bottom:1px solid var(--line);
  align-items:center;
}
.cat-item:last-child{border-bottom:0}
.cat-thumb{
  width:44px;height:44px;border-radius:10px;background:var(--green-soft);
  flex-shrink:0;overflow:hidden;display:flex;align-items:center;justify-content:center;
  color:var(--green);font-weight:800;font-size:15px;
}
.cat-thumb img{width:100%;height:100%;object-fit:contain;background:#fff}
.cat-body{flex:1;min-width:0}
.cat-name{font-size:13px;font-weight:700;margin:0 0 2px}
.cat-meta{font-size:11px;color:var(--muted)}
.cat-add{
  padding:6px 12px;border:0;border-radius:8px;background:var(--green);
  color:#fff;font-weight:800;font-size:12px;
}

.toast{
  position:fixed;left:50%;bottom:100px;transform:translateX(-50%);
  background:#0f172a;color:#fff;padding:12px 18px;border-radius:12px;
  font-size:13px;font-weight:600;z-index:1000;
  box-shadow:0 10px 30px rgba(0,0,0,.2);max-width:calc(100vw - 32px);
  text-align:center;
}

''' + NAVBAR_CSS + '''
</style>
</head>
<body>

<header class="dem-header">
  <div class="dem-header-inner">
    <a class="dem-back" href="/professionnel" aria-label="Retour">&#8592;</a>
    <span class="dem-title">Ma demande</span>
    <span class="dem-ref" id="head-ref">—</span>
  </div>
</header>

<main class="dem-main">

  <div class="dem-head-card">
    <div>
      <div class="dem-head-ref" id="draft-ref">—</div>
      <div style="font-size:12px;color:var(--muted);margin-top:2px" id="draft-updated">Sauvegarde automatique</div>
    </div>
    <span class="dem-head-count" id="draft-count">0</span>
  </div>

  <h2 class="section-title">Ajouter a ma demande</h2>
  <div class="sources-grid">
    <button class="source-btn" id="src-catalogue" type="button">
      <div class="source-icon">&#128722;</div>
      <div class="source-label">Depuis le catalogue</div>
      <div class="source-hint">Rechercher un produit</div>
    </button>
    <button class="source-btn" id="src-manual" type="button">
      <div class="source-icon">&#9997;&#65039;</div>
      <div class="source-label">Saisir une ligne</div>
      <div class="source-hint">Produit + quantite</div>
    </button>
    <button class="source-btn" id="src-pdf" type="button">
      <div class="source-icon">&#128196;</div>
      <div class="source-label">Importer un PDF</div>
      <div class="source-hint">Liste enregistree</div>
    </button>
    <button class="source-btn" id="src-photo" type="button">
      <div class="source-icon">&#128247;</div>
      <div class="source-label">Ajouter une photo</div>
      <div class="source-hint">Photo de votre liste</div>
    </button>
  </div>

  <h2 class="section-title">Ma demande</h2>
  <div id="items"></div>
  <div id="attachments"></div>

  <h2 class="section-title">Notes (facultatif)</h2>
  <textarea class="notes" id="notes" placeholder="Instructions particulieres, delai souhaite..."></textarea>

  <div class="dem-actions">
    <button class="dem-send" id="send" type="button" disabled>
      <span>&#128172;</span> Envoyer sur WhatsApp
    </button>
    <button class="dem-clear" id="clear" type="button">Vider</button>
  </div>

</main>

<!-- Modale Catalogue -->
<div class="modal hidden" id="m-cat">
  <div class="modal-bg" data-close></div>
  <div class="modal-panel">
    <div class="modal-head">
      <h3>Depuis le catalogue</h3>
      <button class="modal-close" data-close>&times;</button>
    </div>
    <div class="modal-body">
      <input class="cat-search" id="cat-search" type="search" placeholder="Rechercher un produit...">
      <div id="cat-list"></div>
    </div>
  </div>
</div>

<!-- Modale Saisie libre -->
<div class="modal hidden" id="m-manual">
  <div class="modal-bg" data-close></div>
  <div class="modal-panel">
    <div class="modal-head">
      <h3 id="manual-title">Saisir une ligne</h3>
      <button class="modal-close" data-close>&times;</button>
    </div>
    <div class="modal-body">
      <div class="field">
        <label for="manual-desc">Produit</label>
        <input type="text" id="manual-desc" placeholder="Ex : Gants d'examen taille M">
      </div>
      <div class="field">
        <label for="manual-qty">Quantite</label>
        <input type="text" id="manual-qty" placeholder="Ex : 10 boites">
      </div>
      <div class="err hidden" id="manual-err"></div>
    </div>
    <div class="modal-foot">
      <button class="dem-clear" data-close>Annuler</button>
      <button class="dem-send" id="manual-add" style="background:var(--green)">Ajouter</button>
    </div>
  </div>
</div>

<!-- Modale PDF -->
<div class="modal hidden" id="m-pdf">
  <div class="modal-bg" data-close></div>
  <div class="modal-panel">
    <div class="modal-head">
      <h3>Importer un PDF</h3>
      <button class="modal-close" data-close>&times;</button>
    </div>
    <div class="modal-body">
      <label class="upload">
        <input type="file" id="pdf-file" accept="application/pdf,.pdf">
        <div class="upload-icon">&#128196;</div>
        <p class="upload-title">Choisir un fichier PDF</p>
        <p class="upload-hint">PDF uniquement · 15 Mo max</p>
      </label>
      <div class="err hidden" id="pdf-err"></div>
    </div>
  </div>
</div>

<!-- Modale Photo -->
<div class="modal hidden" id="m-photo">
  <div class="modal-bg" data-close></div>
  <div class="modal-panel">
    <div class="modal-head">
      <h3>Ajouter une photo</h3>
      <button class="modal-close" data-close>&times;</button>
    </div>
    <div class="modal-body">
      <label class="upload">
        <input type="file" id="photo-file" accept="image/*" capture="environment">
        <div class="upload-icon">&#128247;</div>
        <p class="upload-title">Prendre ou choisir une photo</p>
        <p class="upload-hint">JPG, PNG, WEBP · 15 Mo max</p>
      </label>
      <div class="err hidden" id="photo-err"></div>
    </div>
  </div>
</div>

''' + navbar("demande") + '''
<script src="/static/professional_demande.js"></script>
</body>
</html>
'''
(STATIC / "professional_demande.html").write_text(DEM_HTML, encoding="utf-8")
print("[OK] professional_demande.html")

# ============================================================
# 3. JS : dashboard
# ============================================================
DASH_JS = r'''/* Elokinab Health - Dashboard accueil */
(function () {
  var API = "/api";
  var $ = function (id) { return document.getElementById(id); };

  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }

  function fmtDate(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
  }

  function fmtPrice(v) {
    var n = Math.round(Number(v) || 0);
    return n.toLocaleString("fr-FR") + " F";
  }

  var STATUS = {
    DRAFT: ["draft", "Brouillon"],
    SUBMITTED: ["submitted", "Envoyee"],
    UNDER_REVIEW: ["submitted", "En cours"],
    CONFIRMED: ["confirmed", "Confirmee"],
    PARTIALLY_CONFIRMED: ["partially_confirmed", "Partielle"],
    REJECTED: ["rejected", "Refusee"]
  };

  function loadOrg() {
    return fetch(API + "/pro/organizations/me", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (org) {
        if (!org) return;
        var map = {
          CLINIQUE: "Clinique", HOPITAL: "Hopital",
          CABINET_MEDICAL: "Cabinet medical", LABORATOIRE: "Laboratoire",
          CENTRE_SANTE: "Centre de sante", AUTRE: "Etablissement"
        };
        $("hello").textContent = "Bonjour " + (org.structure_name || "Professionnel") + " 👋";
        $("org-type").innerHTML = "&#127973; " + (map[org.structure_type] || "Etablissement");
        $("org-address").innerHTML = "&#128205; " + (org.address || "Togo");
      }).catch(function () {});
  }

  function loadDraft() {
    return fetch(API + "/pro/requests/draft", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (draft) {
        if (!draft) return;
        return fetch(API + "/pro/requests/" + draft.reference, { credentials: "same-origin" })
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (full) {
            if (!full) return;
            var n = (full.items || []).length + (full.attachments || []).length;
            renderDraft(full, n);
          });
      }).catch(function () {});
  }

  function renderDraft(draft, n) {
    var box = $("draft-block");
    if (n === 0) {
      box.innerHTML = "";
      return;
    }
    box.innerHTML =
      '<div class="draft-card" id="draft-card">' +
        '<div class="draft-card-head">Demande en cours</div>' +
        '<div class="draft-card-ref">' + escapeHtml(draft.reference) + '</div>' +
        '<div class="draft-card-count">' + n + ' element' + (n > 1 ? 's' : '') + '</div>' +
        '<span class="draft-card-cta">Continuer &#8594;</span>' +
      '</div>';
    document.getElementById("draft-card").addEventListener("click", function () {
      window.location.href = "/professionnel/demande";
    });
  }

  function loadLastOrder() {
    return fetch(API + "/pro/requests", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (list) {
        var real = (list || []).filter(function (r) { return r.status !== "DRAFT"; });
        if (real.length === 0) {
          $("reorder-section").classList.add("hidden");
          return;
        }
        var last = real[0];
        var box = $("reorder-block");
        box.innerHTML =
          '<div class="reorder-card" id="reorder-card">' +
            '<div class="reorder-icon">&#128257;</div>' +
            '<div class="reorder-body">' +
              '<div class="reorder-title">Votre derniere demande</div>' +
              '<div class="reorder-meta">' + (last.items_count || 0) + ' produits · ' + fmtDate(last.created_at) + '</div>' +
            '</div>' +
            '<span class="reorder-arrow">&#8594;</span>' +
          '</div>';
        document.getElementById("reorder-card").addEventListener("click", function () {
          // Recharge les items dans la demande en cours
          copyFromRequest(last.reference);
        });
      }).catch(function () {});
  }

  function copyFromRequest(ref) {
    // 1. Recupere la demande passee
    fetch(API + "/pro/requests/" + ref, { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (src) {
        if (!src || !src.items) throw new Error("Commande introuvable");
        // 2. Recupere/cree la demande en cours
        return fetch(API + "/pro/requests/draft", { credentials: "same-origin" })
          .then(function (r) { return r.json(); })
          .then(function (draft) {
            // 3. Copie les items un par un
            var chain = Promise.resolve();
            src.items.forEach(function (it) {
              chain = chain.then(function () {
                return fetch(API + "/pro/requests/" + draft.reference + "/items", {
                  method: "POST",
                  credentials: "same-origin",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    product_id: it.product_id || null,
                    description: it.description,
                    requested_quantity: it.requested_quantity || 1
                  })
                });
              });
            });
            return chain;
          });
      })
      .then(function () {
        window.location.href = "/professionnel/demande";
      })
      .catch(function (e) { alert(e.message || "Erreur"); });
  }

  function loadActivity() {
    return fetch(API + "/pro/requests", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (list) {
        var real = (list || []).filter(function (r) { return r.status !== "DRAFT"; }).slice(0, 5);
        var box = $("activity");
        if (real.length === 0) {
          box.innerHTML = '<div class="card empty-state">' +
            '<div class="empty-icon">&#128230;</div>' +
            'Vous n\'avez encore envoye aucune demande.' +
            '</div>';
          return;
        }
        var html = '<div class="activity-list">';
        real.forEach(function (r) {
          var st = STATUS[r.status] || ["submitted", r.status];
          html += '<div class="activity-item" data-ref="' + escapeHtml(r.reference) + '">' +
            '<div class="activity-body">' +
              '<div class="activity-ref">' + escapeHtml(r.reference) + '</div>' +
              '<div class="activity-meta">' + fmtDate(r.created_at) +
              ' · ' + (r.items_count || 0) + ' produit' + ((r.items_count || 0) > 1 ? 's' : '') + '</div>' +
            '</div>' +
            '<span class="badge ' + st[0] + '">' + st[1] + '</span>' +
          '</div>';
        });
        html += '</div>';
        box.innerHTML = html;
        Array.prototype.forEach.call(box.querySelectorAll(".activity-item"), function (el) {
          el.addEventListener("click", function () {
            var ref = el.getAttribute("data-ref");
            window.location.href = "/suivi?ref=" + encodeURIComponent(ref);
          });
        });
      }).catch(function () {});
  }

  function init() {
    document.getElementById("new-request").addEventListener("click", function () {
      window.location.href = "/professionnel/demande";
    });
    loadOrg();
    loadDraft();
    loadLastOrder();
    loadActivity();
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
# 4. JS : demande (reprend l'ancien professional.js)
# ============================================================
old_js_path = STATIC / "professional.js"
if old_js_path.exists():
    old_js = old_js_path.read_text(encoding="utf-8")
    # Adapter les references aux ID de la nouvelle page
    # Les ID sont : src-catalogue, src-manual, src-pdf, src-photo, m-cat, m-manual, m-pdf, m-photo
    # L'ancien utilisait add-from-catalogue, add-manual, add-pdf, add-photo, m-source, m-catalogue, m-manual, m-pdf, m-photo

    new_js = old_js
    # Remplacer les IDs de boutons sources
    new_js = new_js.replace('document.getElementById("add-from-catalogue")', 'document.getElementById("src-catalogue")')
    new_js = new_js.replace('document.getElementById("add-manual")', 'document.getElementById("src-manual")')
    new_js = new_js.replace('document.getElementById("add-pdf")', 'document.getElementById("src-pdf")')
    new_js = new_js.replace('document.getElementById("add-photo")', 'document.getElementById("src-photo")')
    new_js = new_js.replace('document.getElementById("add-from-catalog")', 'document.getElementById("src-catalogue")')

    # Le catalogue : m-catalogue -> m-cat
    new_js = new_js.replace('"m-catalogue"', '"m-cat"')
    # Le bouton add-manual (submit) reste
    # La modale source n'existe plus -> retirer les handlers sur .pro-choice dans m-source
    # Mais garder les handlers des modales individuelles

    (STATIC / "professional_demande.js").write_text(new_js, encoding="utf-8")
    print("[OK] professional_demande.js (adapte)")
else:
    print("[!] professional.js introuvable")

# ============================================================
# 5. Routes main.py
# ============================================================
src = MAIN.read_text(encoding="utf-8")
routes_to_add = []
if '"/professionnel/demande"' not in src:
    routes_to_add.append('''
@app.get("/professionnel/demande", include_in_schema=False)
def page_pro_demande():
    return FileResponse(STATIC_DIR / "professional_demande.html")
''')
if routes_to_add:
    block = "\n" + "\n".join(routes_to_add) + "\n"
    anchor = "\ninit_db()\n"
    if anchor in src:
        src = src.replace(anchor, block + anchor, 1)
        MAIN.write_text(src, encoding="utf-8")
        print("[OK] main.py -> /professionnel/demande")

# ============================================================
# 6. Mise a jour navbar des pages existantes (catalogue, commandes, etablissement)
# ============================================================
import re

def update_navbar(html, active):
    """Remplace l'ancienne navbar par la nouvelle."""
    # Supprimer l'ancienne navbar
    new_nav = '''
<nav class="pro-navbar">
  <a href="/professionnel"%s><span class="ico">&#127968;</span> Accueil</a>
  <a href="/professionnel/catalogue"%s><span class="ico">&#128722;</span> Catalogue</a>
  <a href="/professionnel/demande"%s id="nav-central">
    <span>+</span><span class="lbl">Demande</span>
    <span class="nav-count hidden" id="nav-count">0</span>
  </a>
  <a href="/professionnel/commandes"%s><span class="ico">&#128230;</span> Commandes</a>
  <a href="/professionnel/etablissement"%s><span class="ico">&#127970;</span> Etabl.</a>
</nav>
<script>%s</script>
''' % (
        ' class="active"' if active == "accueil" else '',
        ' class="active"' if active == "catalogue" else '',
        ' class="central' + (' active' if active == "demande" else '') + '"',
        ' class="active"' if active == "commandes" else '',
        ' class="active"' if active == "etablissement" else '',
        NAVBAR_JS,
    )
    # Regex : remplacer tout <nav class="pro-navbar">...</nav>
    pattern = re.compile(r'<nav class="pro-navbar">.*?</nav>', re.DOTALL)
    if pattern.search(html):
        html = pattern.sub(new_nav, html, count=1)
    else:
        # Inserer avant </body>
        html = html.replace("</body>", new_nav + "\n</body>")
    return html

# Catalogue
cat = STATIC / "professional_catalogue.html"
if cat.exists():
    h = cat.read_text(encoding="utf-8")
    h = update_navbar(h, "catalogue")
    cat.write_text(h, encoding="utf-8")
    print("[OK] catalogue -> navbar mise a jour")

# Commandes
cmd = STATIC / "professional_commandes.html"
if cmd.exists():
    h = cmd.read_text(encoding="utf-8")
    h = update_navbar(h, "commandes")
    cmd.write_text(h, encoding="utf-8")
    print("[OK] commandes -> navbar mise a jour")

# Etablissement
etab = STATIC / "professional_etablissement.html"
if etab.exists():
    h = etab.read_text(encoding="utf-8")
    h = update_navbar(h, "etablissement")
    etab.write_text(h, encoding="utf-8")
    print("[OK] etablissement -> navbar mise a jour")

print()
print("=" * 60)
print("DECOUPAGE ACCUEIL / DEMANDE LIVRE")
print("=" * 60)
print()
print("Pages :")
print("  /professionnel              = Dashboard (accueil)")
print("  /professionnel/catalogue    = Catalogue (inchange)")
print("  /professionnel/demande      = Espace de travail (nouveau)")
print("  /professionnel/commandes    = Historique")
print("  /professionnel/etablissement = Profil etablissement")
print()
print("Dashboard affiche :")
print("  - Bonjour + nom etablissement")
print("  - Carte 'Demande en cours' (si existe)")
print("  - Bouton '+ Nouvelle demande'")
print("  - 'Commander a nouveau' (derniere demande)")
print("  - 'Activite recente' (5 dernieres)")
print("  - Lien 'Voir toutes mes commandes'")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")