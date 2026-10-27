"""
v4_pro_all_pages.py
- Uniformise la couleur (bleu) sur toutes les pages pro
- Ajoute la navbar sur /professionnel/commandes
- Cree /professionnel/etablissement avec navbar
- Ajuste les onglets actifs sur chaque page
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
MAIN = BASE / "main.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_all_pages_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
for f in ("professional.html", "professional.js", "professional_commandes.html", "professional_catalogue.html"):
    p = STATIC / f
    if p.exists():
        shutil.copy2(p, backup / f)
shutil.copy2(MAIN, backup / "main.py")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. Palette bleue partout (professional.html)
# ============================================================
PRO_HTML = STATIC / "professional.html"
html = PRO_HTML.read_text(encoding="utf-8")

# Remplacer les variables vertes par bleues
html = html.replace("--green:#0f9d76;", "--green:#1a4a7f;")
html = html.replace("--green-dark:#0a7a5a;", "--green-dark:#123258;")
html = html.replace("--green-soft:#e8f7f1;", "--green-soft:#eaf1f9;")
# Remplacer dans les usages inline
html = html.replace("linear-gradient(135deg,#0f9d76,#37c79c)", "linear-gradient(135deg,#1a4a7f,#2a6ba8)")
html = html.replace("var(--green)", "var(--green)")  # deja fait via variables
html = html.replace("background:#25d366;", "background:#10a37f;")  # WhatsApp vert -> vert plus fonce
print("[OK] professional.html -> palette bleue")

# Ajouter la route etablissement dans le lien
html = html.replace('id="nav-etab"', 'id="nav-etab" href="/professionnel/etablissement"')
# Attention : nav-etab est un <a href="#"> -> on remplace proprement
old_nav_etab = '<a href="#" id="nav-etab">'
new_nav_etab = '<a href="/professionnel/etablissement" id="nav-etab">'
if old_nav_etab in html:
    html = html.replace(old_nav_etab, new_nav_etab)
    print("[OK] nav-etab -> lien /professionnel/etablissement")

# Retirer le handler JS de nav-etab (qui ouvrait une modale) -> il devient un lien
PRO_JS = STATIC / "professional.js"
js = PRO_JS.read_text(encoding="utf-8")
old_nav_js = '''    var navEtab = document.getElementById("nav-etab");
    if (navEtab) navEtab.addEventListener("click", function (e) { e.preventDefault(); openModal(); });'''
if old_nav_js in js:
    js = js.replace(old_nav_js, "")
    print("[OK] professional.js -> handler nav-etab retire (devient un lien)")

# Retirer le handler user-btn -> il ouvre une modale, garder ca OK
PRO_JS.write_text(js, encoding="utf-8")
PRO_HTML.write_text(html, encoding="utf-8")

# ============================================================
# 2. Catalogue : retirer le lien actif navbar, corriger couleur
# ============================================================
CAT = STATIC / "professional_catalogue.html"
chtml = CAT.read_text(encoding="utf-8")
# Le catalogue utilise deja du bleu -> OK, juste verifier navbar
if '<nav class="pro-navbar">' not in chtml:
    NAVBAR = '''
<nav class="pro-navbar">
  <a href="/professionnel"><span class="ico">&#127968;</span> Accueil</a>
  <a href="/professionnel/catalogue" class="active"><span class="ico">&#128722;</span> Catalogue</a>
  <a href="/professionnel" class="central" id="nav-central">
    <span>+</span><span class="lbl">Demande</span>
    <span class="nav-count hidden" id="nav-count">0</span>
  </a>
  <a href="/professionnel/commandes"><span class="ico">&#128230;</span> Commandes</a>
  <a href="/professionnel/etablissement"><span class="ico">&#127970;</span> Établ.</a>
</nav>
'''
    chtml = chtml.replace("</body>", NAVBAR + "\n</body>")
    CAT.write_text(chtml, encoding="utf-8")
    print("[OK] catalogue -> navbar confirmee")

# ============================================================
# 3. Page Commandes : navbar + design
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
  --green:#1a4a7f;
  --green-dark:#123258;
  --green-soft:#eaf1f9;
  --ink:#0f172a;--muted:#64748b;--line:#e6ebf1;--bg:#f7fafc;
  --radius:14px;--shadow:0 1px 3px rgba(15,23,42,.06);
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
.pg-brand{
  display:flex;align-items:center;gap:8px;font-weight:800;font-size:15px;
}
.pg-brand-mark{
  width:30px;height:30px;border-radius:8px;
  background:linear-gradient(135deg,var(--green),#2a6ba8);color:#fff;
  display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:800;
}
.pg-main{max-width:900px;margin:0 auto;padding:20px 16px 40px}
.pg-title{font-size:22px;margin:0 0 6px;letter-spacing:-.02em}
.pg-sub{font-size:14px;color:var(--muted);margin:0 0 20px}

.pg-card{
  background:#fff;border:1px solid var(--line);border-radius:var(--radius);
  padding:16px;margin-bottom:12px;
}
.pg-order{
  display:block;background:#fff;border:1px solid var(--line);
  border-radius:var(--radius);padding:16px;margin-bottom:10px;
  text-decoration:none;color:inherit;transition:.15s;
}
.pg-order:hover{border-color:var(--green);box-shadow:var(--shadow)}
.pg-order-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:8px}
.pg-order-ref{font-family:Consolas,monospace;font-weight:800;font-size:14px;color:var(--ink)}
.pg-order-date{font-size:12px;color:var(--muted)}
.pg-order-body{font-size:13px;color:var(--muted);line-height:1.5}
.pg-order-foot{display:flex;align-items:center;justify-content:space-between;margin-top:10px;gap:10px}
.pg-order-total{font-weight:800;color:var(--green-dark);font-size:15px}
.pg-badge{
  font-size:10px;font-weight:800;padding:4px 10px;border-radius:999px;
  text-transform:uppercase;letter-spacing:.05em;
}
.pg-badge.draft{background:#fff7e6;color:#8a5a00}
.pg-badge.submitted{background:#e8eef7;color:#1a4a7f}
.pg-badge.confirmed{background:#e6f7f1;color:#0a7a5a}
.pg-badge.partially_confirmed{background:#f3e8ff;color:#6335b8}
.pg-badge.rejected{background:#fee2e2;color:#b23c3c}

.pg-empty{
  text-align:center;padding:40px 20px;color:var(--muted);
}
.pg-empty-icon{font-size:48px;opacity:.3;margin-bottom:12px}
.pg-empty h3{font-size:16px;color:var(--ink);margin:0 0 6px}
.pg-empty p{font-size:14px;margin:0 0 20px}

/* ---- Navbar basse ---- */
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
</style>
</head>
<body>

<header class="pg-header">
  <div class="pg-header-inner">
    <a class="pg-back" href="/professionnel" aria-label="Retour">&#8592;</a>
    <div class="pg-brand">
      <span class="pg-brand-mark">+</span>
      Elokinab
    </div>
  </div>
</header>

<main class="pg-main">
  <h1 class="pg-title">Mes commandes</h1>
  <p class="pg-sub">Historique de vos demandes et commandes.</p>

  <div id="orders-list"></div>

  <div class="pg-empty hidden" id="empty">
    <div class="pg-empty-icon">&#128230;</div>
    <h3>Aucune commande pour le moment</h3>
    <p>Vos futures demandes apparaitront ici.</p>
    <a href="/professionnel" style="display:inline-block;padding:13px 20px;background:var(--green);color:#fff;border-radius:11px;font-weight:800;text-decoration:none;font-size:14px">Nouvelle demande</a>
  </div>
</main>

<nav class="pro-navbar">
  <a href="/professionnel"><span class="ico">&#127968;</span> Accueil</a>
  <a href="/professionnel/catalogue"><span class="ico">&#128722;</span> Catalogue</a>
  <a href="/professionnel" class="central" id="nav-central">
    <span>+</span><span class="lbl">Demande</span>
    <span class="nav-count hidden" id="nav-count">0</span>
  </a>
  <a href="/professionnel/commandes" class="active"><span class="ico">&#128230;</span> Commandes</a>
  <a href="/professionnel/etablissement"><span class="ico">&#127970;</span> Établ.</a>
</nav>

<script>
(function () {
  var API = "/api";
  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }
  var STATUS = {
    DRAFT: ["draft", "Brouillon"],
    SUBMITTED: ["submitted", "En attente"],
    UNDER_REVIEW: ["submitted", "En cours"],
    CONFIRMED: ["confirmed", "Confirmee"],
    PARTIALLY_CONFIRMED: ["partially_confirmed", "Partielle"],
    REJECTED: ["rejected", "Refusee"]
  };

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

  function render(list) {
    var box = document.getElementById("orders-list");
    var empty = document.getElementById("empty");
    box.innerHTML = "";
    // Filtrer : on garde que les non-brouillons
    var real = list.filter(function (r) { return r.status !== "DRAFT"; });
    if (real.length === 0) {
      empty.classList.remove("hidden");
      return;
    }
    empty.classList.add("hidden");
    real.forEach(function (r) {
      var badge = STATUS[r.status] || ["draft", r.status];
      var a = document.createElement("a");
      a.className = "pg-order";
      a.href = "/suivi?ref=" + encodeURIComponent(r.reference);
      a.innerHTML =
        '<div class="pg-order-head">' +
          '<span class="pg-order-ref">' + escapeHtml(r.reference) + '</span>' +
          '<span class="pg-order-date">' + fmtDate(r.created_at) + '</span>' +
        '</div>' +
        '<div class="pg-order-body">' +
          (r.items_count || 0) + ' produit' + ((r.items_count || 0) > 1 ? 's' : '') +
          (r.attachments_count ? ' · ' + r.attachments_count + ' piece' + (r.attachments_count > 1 ? 's' : '') + ' jointe' + (r.attachments_count > 1 ? 's' : '') : '') +
        '</div>' +
        '<div class="pg-order-foot">' +
          '<span class="pg-badge ' + badge[0] + '">' + badge[1] + '</span>' +
        '</div>';
      box.appendChild(a);
    });
  }

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
            var c = document.getElementById("nav-count");
            if (c && n > 0) { c.textContent = n > 99 ? "99+" : String(n); c.classList.remove("hidden"); }
          });
      }).catch(function () {});
  }

  function loadOrders() {
    fetch(API + "/pro/requests", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (list) { render(list || []); })
      .catch(function () {});
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadOrders();
    loadNavCount();
  });
})();
</script>
</body>
</html>
'''
(STATIC / "professional_commandes.html").write_text(CMD_HTML, encoding="utf-8")
print("[OK] professional_commandes.html")

# ============================================================
# 4. Page Etablissement : navbar + design
# ============================================================
ETAB_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Mon etablissement - Elokinab Health</title>
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
  -webkit-font-smoothing:antialiased;padding-bottom:92px;
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
.pg-brand{
  display:flex;align-items:center;gap:8px;font-weight:800;font-size:15px;
}
.pg-brand-mark{
  width:30px;height:30px;border-radius:8px;
  background:linear-gradient(135deg,var(--green),#2a6ba8);color:#fff;
  display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:800;
}
.pg-main{max-width:700px;margin:0 auto;padding:20px 16px 40px}
.pg-title{font-size:22px;margin:0 0 6px}
.pg-sub{font-size:14px;color:var(--muted);margin:0 0 20px}

.pg-card{
  background:#fff;border:1px solid var(--line);border-radius:var(--radius);
  padding:20px;
}
.pg-field{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.pg-field label{font-size:13px;font-weight:700}
.pg-field input,.pg-field select,.pg-field textarea{
  padding:12px 14px;border:1px solid var(--line);border-radius:10px;
  font-family:inherit;font-size:15px;outline:none;background:#fff;width:100%;
}
.pg-field input:focus,.pg-field select:focus,.pg-field textarea:focus{border-color:var(--green)}
.pg-gps-row{display:flex;gap:8px}
.pg-gps-row input{flex:1}
.pg-save{
  width:100%;padding:14px;border:0;border-radius:11px;
  background:var(--green);color:#fff;font-weight:800;font-size:15px;
  margin-top:8px;
}
.pg-save:hover{background:var(--green-dark)}
.pg-msg{margin-top:12px;padding:10px 12px;border-radius:10px;font-size:13px}
.pg-msg.ok{background:var(--green-soft);color:var(--green-dark);border:1px solid #c7e9dc}
.pg-msg.err{background:#fee2e2;color:#b23c3c;border:1px solid #f6d2d2}

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
</style>
</head>
<body>

<header class="pg-header">
  <div class="pg-header-inner">
    <a class="pg-back" href="/professionnel" aria-label="Retour">&#8592;</a>
    <div class="pg-brand">
      <span class="pg-brand-mark">+</span>
      Elokinab
    </div>
  </div>
</header>

<main class="pg-main">
  <h1 class="pg-title">Mon etablissement</h1>
  <p class="pg-sub">Ces informations figurent sur vos commandes.</p>

  <div class="pg-card">
    <div class="pg-field">
      <label for="structure_name">Nom de l'etablissement</label>
      <input type="text" id="structure_name" required>
    </div>
    <div class="pg-field">
      <label for="structure_type">Type</label>
      <select id="structure_type">
        <option value="CLINIQUE">Clinique</option>
        <option value="HOPITAL">Hopital</option>
        <option value="CABINET_MEDICAL">Cabinet medical</option>
        <option value="LABORATOIRE">Laboratoire</option>
        <option value="CENTRE_SANTE">Centre de sante</option>
        <option value="AUTRE">Autre</option>
      </select>
    </div>
    <div class="pg-field">
      <label for="manager_name">Responsable</label>
      <input type="text" id="manager_name">
    </div>
    <div class="pg-field">
      <label for="phone">Telephone</label>
      <input type="tel" id="phone">
    </div>
    <div class="pg-field">
      <label for="email">Email</label>
      <input type="email" id="email">
    </div>
    <div class="pg-field">
      <label for="address">Adresse</label>
      <input type="text" id="address">
    </div>
    <div class="pg-field">
      <label for="delivery_address">Adresse de livraison</label>
      <input type="text" id="delivery_address">
    </div>
    <div class="pg-field">
      <label for="delivery_instructions">Instructions de livraison</label>
      <textarea id="delivery_instructions" rows="2"></textarea>
    </div>
    <div class="pg-field">
      <label>Position GPS</label>
      <div class="pg-gps-row">
        <input type="number" id="latitude" step="0.00001" placeholder="Latitude">
        <input type="number" id="longitude" step="0.00001" placeholder="Longitude">
      </div>
      <button type="button" class="pg-save" id="gps-btn" style="background:#64748b;margin-top:8px;padding:11px;font-size:13px">&#128205; Utiliser ma position</button>
    </div>
    <button class="pg-save" id="save">Enregistrer</button>
    <div id="msg" class="pg-msg hidden"></div>
  </div>
</main>

<nav class="pro-navbar">
  <a href="/professionnel"><span class="ico">&#127968;</span> Accueil</a>
  <a href="/professionnel/catalogue"><span class="ico">&#128722;</span> Catalogue</a>
  <a href="/professionnel" class="central" id="nav-central">
    <span>+</span><span class="lbl">Demande</span>
    <span class="nav-count hidden" id="nav-count">0</span>
  </a>
  <a href="/professionnel/commandes"><span class="ico">&#128230;</span> Commandes</a>
  <a href="/professionnel/etablissement" class="active"><span class="ico">&#127970;</span> Établ.</a>
</nav>

<script>
(function () {
  var API = "/api";
  function $(id) { return document.getElementById(id); }
  function showMsg(t, ok) {
    var m = $("msg");
    m.textContent = t;
    m.className = "pg-msg " + (ok ? "ok" : "err");
    m.classList.remove("hidden");
    if (ok) setTimeout(function () { m.classList.add("hidden"); }, 3500);
  }
  function hideMsg() { $("msg").classList.add("hidden"); }

  function load() {
    fetch(API + "/pro/organizations/me", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (o) {
        if (!o) return;
        $("structure_name").value = o.structure_name || "";
        $("structure_type").value = o.structure_type || "CLINIQUE";
        $("manager_name").value = o.manager_name || "";
        $("phone").value = o.phone || "";
        $("email").value = o.email || "";
        $("address").value = o.address || "";
        $("delivery_address").value = o.delivery_address || "";
        $("delivery_instructions").value = o.delivery_instructions || "";
        $("latitude").value = o.latitude || "";
        $("longitude").value = o.longitude || "";
      }).catch(function () {});
  }

  function save() {
    hideMsg();
    var body = {
      name: $("structure_name").value.trim(),
      type: $("structure_type").value,
      responsible: $("manager_name").value.trim(),
      phone: $("phone").value.trim(),
      email: $("email").value.trim(),
      address: $("address").value.trim(),
      delivery_address: $("delivery_address").value.trim(),
      delivery_instructions: $("delivery_instructions").value.trim()
    };
    var lat = parseFloat($("latitude").value);
    var lon = parseFloat($("longitude").value);
    if (!isNaN(lat) && !isNaN(lon)) { body.latitude = lat; body.longitude = lon; }
    if (!body.name) { showMsg("Le nom est obligatoire.", false); return; }

    fetch(API + "/pro/organizations/me", {
      method: "PATCH",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    }).then(function () {
      showMsg("Informations enregistrees.", true);
    }).catch(function (e) { showMsg(e.message, false); });
  }

  function gps() {
    if (!navigator.geolocation) { showMsg("GPS indisponible", false); return; }
    var b = $("gps-btn");
    b.disabled = true; b.textContent = "Localisation...";
    navigator.geolocation.getCurrentPosition(function (pos) {
      $("latitude").value = pos.coords.latitude.toFixed(5);
      $("longitude").value = pos.coords.longitude.toFixed(5);
      b.disabled = false; b.innerHTML = "&#128205; Utiliser ma position";
    }, function () {
      b.disabled = false; b.innerHTML = "&#128205; Utiliser ma position";
      showMsg("Position introuvable", false);
    }, { enableHighAccuracy: true, timeout: 15000 });
  }

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
            var c = document.getElementById("nav-count");
            if (c && n > 0) { c.textContent = n > 99 ? "99+" : String(n); c.classList.remove("hidden"); }
          });
      }).catch(function () {});
  }

  document.addEventListener("DOMContentLoaded", function () {
    load(); loadNavCount();
    $("save").addEventListener("click", save);
    $("gps-btn").addEventListener("click", gps);
  });
})();
</script>
</body>
</html>
'''
(STATIC / "professional_etablissement.html").write_text(ETAB_HTML, encoding="utf-8")
print("[OK] professional_etablissement.html")

# ============================================================
# 5. Route etablissement dans main.py
# ============================================================
src = MAIN.read_text(encoding="utf-8")
if '"/professionnel/etablissement"' not in src:
    routes = '''

@app.get("/professionnel/etablissement", include_in_schema=False)
def page_pro_etablissement():
    return FileResponse(STATIC_DIR / "professional_etablissement.html")

'''
    anchor = "\ninit_db()\n"
    if anchor in src:
        src = src.replace(anchor, routes + anchor, 1)
        MAIN.write_text(src, encoding="utf-8")
        print("[OK] main.py -> /professionnel/etablissement")
else:
    print("[i] route etablissement deja presente")

print()
print("=" * 60)
print("PAGES PRO UNIFIEES : COULEUR BLEUE + NAVBAR PARTOUT")
print("=" * 60)
print()
print("Pages mises a jour :")
print("  /professionnel              (bleu + navbar)")
print("  /professionnel/catalogue    (bleu + navbar)")
print("  /professionnel/commandes    (NEW - bleu + navbar)")
print("  /professionnel/etablissement (NEW - bleu + navbar)")
print()
print("Navbar identique partout :")
print("  Accueil | Catalogue | + Demande | Commandes | Etabl.")
print("  Compteur sur le bouton central '+'")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")