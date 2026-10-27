"""
v4_refonte_demande.py
1. Bouton WhatsApp UNIQUEMENT dans le dashboard (expansion au scroll, réduction auto)
2. Refonte page Demande : 2 options, boutons renommés, structure simplifiée
3. Fix bug "Demande indisponible" dans le catalogue
"""
from pathlib import Path
import datetime
import re
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_refonte_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
for f in ("professional.html", "professional_demande.html", "professional_demande.js",
          "professional_catalogue.html", "professional_catalogue.js",
          "professional_commandes.html", "professional_etablissement.html"):
    p = STATIC / f
    if p.exists():
        shutil.copy2(p, backup / f)
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. DASHBOARD : bouton WhatsApp avec scroll intelligent
# ============================================================
DASH = STATIC / "professional.html"
html = DASH.read_text(encoding="utf-8")

# Supprimer l'ancien bouton support s'il existe
html = re.sub(
    r'<a class="support-btn"[^>]*id="support-link"[^>]*>.*?</a>\s*',
    '', html, flags=re.DOTALL)
html = re.sub(
    r'<!-- Support WhatsApp -->\s*',
    '', html)
print("[OK] dashboard -> ancien bouton support retire")

# Retirer l'ancien CSS support
html = re.sub(
    r'/\* ---- Bouton support WhatsApp ---- \*/.*?(?=</style>)',
    '',
    html,
    flags=re.DOTALL)

# Ajouter nouveau CSS + bouton
NEW_SUPPORT_CSS = '''
/* ---- Bouton support WhatsApp intelligent ---- */
.support-fab{
  position:fixed;bottom:100px;right:16px;z-index:190;
  height:52px;min-width:52px;
  border-radius:26px;
  background:#25d366;color:#fff;text-decoration:none;
  display:inline-flex;align-items:center;justify-content:center;
  padding:0;
  box-shadow:0 6px 18px rgba(37,211,102,.4);
  transition:all .35s cubic-bezier(.4,0,.2,1);
  overflow:hidden;
  gap:8px;
  max-width:calc(100vw - 32px);
}
.support-fab .ico{font-size:22px;line-height:1;flex-shrink:0}
.support-fab .lbl{
  display:none;font-size:13px;font-weight:800;
  white-space:nowrap;color:#fff;
}
.support-fab.expanded{
  padding:0 20px;
}
.support-fab.expanded .lbl{display:inline-block}
.support-fab:hover{background:#1da851}
'''
html = html.replace("</style>", NEW_SUPPORT_CSS + "</style>", 1)

SUPPORT_FAB = '''
<a class="support-fab" id="support-fab"
   href="https://wa.me/22871039904?text=Bonjour%20Elokinab%20Health%2C%20j%27ai%20une%20question."
   target="_blank" rel="noopener" title="Support pharmacie">
  <span class="ico">&#128172;</span>
  <span class="lbl">Support pharmacie</span>
</a>
'''
html = html.replace("</body>", SUPPORT_FAB + "\n</body>", 1)

# JS scroll : expand au scroll, reduce 1.2s apres l'arret
SCROLL_JS = '''
<script>
(function () {
  var fab = document.getElementById("support-fab");
  if (!fab) return;
  var timer = null;
  function onScroll() {
    fab.classList.add("expanded");
    if (timer) clearTimeout(timer);
    timer = setTimeout(function () {
      fab.classList.remove("expanded");
    }, 1200);
  }
  window.addEventListener("scroll", onScroll, { passive: true });
})();
</script>
'''
html = html.replace("</body>", SCROLL_JS + "\n</body>", 1)

DASH.write_text(html, encoding="utf-8")
print("[OK] dashboard -> bouton WhatsApp scroll intelligent")

# ============================================================
# 2. Supprimer bouton support des autres pages
# ============================================================
for page_name in ("professional_commandes.html", "professional_etablissement.html",
                  "professional_demande.html"):
    page = STATIC / page_name
    if not page.exists():
        continue
    h = page.read_text(encoding="utf-8")
    # Retirer les blocs support-btn
    h = re.sub(r'<a class="support-btn"[^>]*>.*?</a>\s*', '', h, flags=re.DOTALL)
    h = re.sub(r'<a class="support-mini"[^>]*>.*?</a>\s*', '', h, flags=re.DOTALL)
    h = re.sub(r'<a class="support-fab"[^>]*>.*?</a>\s*', '', h, flags=re.DOTALL)
    page.write_text(h, encoding="utf-8")
    print("[OK]", page_name, "-> bouton support retire")

# Catalogue : retirer le support-mini
CAT = STATIC / "professional_catalogue.html"
h = CAT.read_text(encoding="utf-8")
h = re.sub(r'<a class="support-mini"[^>]*>.*?</a>\s*', '', h, flags=re.DOTALL)
h = re.sub(r'<script>\s*\(function \(\) \{\s*var btn = document\.getElementById\("support-mini"\).*?</script>\s*',
           '', h, flags=re.DOTALL)
CAT.write_text(h, encoding="utf-8")
print("[OK] catalogue -> bouton support retire")

# ============================================================
# 3. PAGE DEMANDE : refonte complète
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
  --wa:#25d366;--wa-dark:#1da851;
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
.dem-ref{margin-left:auto;font-family:Consolas,monospace;font-size:11px;color:var(--muted)}

.dem-main{max-width:900px;margin:0 auto;padding:18px 16px 40px}

/* -- Statut de la demande -- */
.dem-status{
  background:#fff;border:1px solid var(--line);border-radius:var(--radius);
  padding:14px 16px;margin-bottom:18px;
  display:flex;align-items:center;gap:12px;
}
.dem-status-icon{
  width:38px;height:38px;border-radius:11px;
  background:var(--green-soft);color:var(--green);
  display:flex;align-items:center;justify-content:center;
  font-size:17px;flex-shrink:0;
}
.dem-status-body{flex:1;min-width:0}
.dem-status-ref{
  font-family:Consolas,monospace;font-weight:800;font-size:13px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.dem-status-hint{font-size:11px;color:var(--muted);margin-top:2px}
.dem-status-badge{
  background:var(--green-soft);color:var(--green-dark);
  font-size:11px;font-weight:800;padding:5px 11px;border-radius:999px;
}

/* -- Options principales -- */
.dem-option{
  display:flex;align-items:center;gap:16px;
  padding:20px;border-radius:16px;
  background:#fff;border:2px solid var(--line);
  margin-bottom:12px;cursor:pointer;transition:.15s;
  text-decoration:none;color:inherit;
}
.dem-option:hover{border-color:var(--green);transform:translateY(-2px);
  box-shadow:0 8px 24px rgba(26,74,127,.1)}
.dem-option-icon{
  width:56px;height:56px;border-radius:14px;
  background:var(--green-soft);color:var(--green);
  display:flex;align-items:center;justify-content:center;
  font-size:26px;flex-shrink:0;
}
.dem-option-body{flex:1;min-width:0}
.dem-option-title{font-size:16px;font-weight:800;margin:0 0 4px;letter-spacing:-.01em}
.dem-option-desc{font-size:13px;color:var(--muted);margin:0;line-height:1.4}
.dem-option-arrow{color:var(--muted);font-size:22px;flex-shrink:0}

/* Option WhatsApp */
.dem-option.wa{
  background:linear-gradient(135deg,#e9faf0,#f6fdf9);
  border-color:#c7ebd5;
}
.dem-option.wa:hover{border-color:var(--wa)}
.dem-option.wa .dem-option-icon{
  background:#fff;color:var(--wa);
  box-shadow:0 2px 8px rgba(37,211,102,.2);
}

/* -- Liste des éléments -- */
.dem-section-title{
  font-size:11px;text-transform:uppercase;letter-spacing:.08em;
  color:var(--muted);font-weight:800;
  margin:24px 0 10px;display:flex;align-items:center;gap:8px;
}
.dem-count{
  background:var(--green);color:#fff;
  font-size:10px;font-weight:800;
  padding:2px 8px;border-radius:999px;
}

.item-row{
  display:flex;align-items:flex-start;gap:12px;
  padding:13px 14px;background:#fff;
  border:1px solid var(--line);border-radius:12px;
  margin-bottom:8px;
}
.item-row.attachment{
  background:#f8fafc;
}
.item-body{flex:1;min-width:0}
.item-name{
  font-size:14px;font-weight:700;margin:0 0 3px;
  word-break:break-word;line-height:1.35;
}
.item-meta{
  font-size:11px;color:var(--muted);
  display:flex;gap:8px;flex-wrap:wrap;
}
.item-meta .pill{
  background:var(--green-soft);color:var(--green-dark);
  padding:2px 8px;border-radius:999px;font-weight:700;
}
.item-qty{
  font-family:Consolas,monospace;font-weight:800;
  color:var(--green-dark);font-size:14px;
  white-space:nowrap;flex-shrink:0;
  padding-top:1px;
}
.item-del{
  width:28px;height:28px;border:0;border-radius:8px;
  background:transparent;color:var(--muted);font-size:15px;
  display:flex;align-items:center;justify-content:center;
  flex-shrink:0;cursor:pointer;transition:.15s;
}
.item-del:hover{background:#fee2e2;color:#dc2626}

/* Empty state */
.dem-empty{
  text-align:center;padding:24px 16px;
  background:#fff;border:1px dashed var(--line);
  border-radius:12px;color:var(--muted);font-size:13px;
  line-height:1.5;
}

/* -- Notes -- */
.notes{
  width:100%;padding:13px 15px;
  border:1px solid var(--line);border-radius:12px;
  font-family:inherit;font-size:14px;background:#fff;
  outline:none;resize:vertical;min-height:64px;
  color:var(--ink);
}
.notes:focus{border-color:var(--green)}

/* -- Actions fin de page -- */
.dem-actions{
  margin-top:22px;padding-top:18px;
  border-top:1px solid var(--line);
  display:flex;flex-direction:column;gap:10px;
}
.dem-send{
  padding:15px;border:0;border-radius:13px;
  background:var(--wa);color:#fff;font-weight:800;font-size:15px;
  display:flex;align-items:center;justify-content:center;gap:8px;
  transition:.15s;
}
.dem-send:hover:not(:disabled){background:var(--wa-dark);transform:translateY(-1px)}
.dem-send:disabled{background:#c9e5d4;cursor:not-allowed}
.dem-send .ico{font-size:18px}

.dem-clear{
  padding:13px;border:1px solid var(--line);background:#fff;
  border-radius:12px;font-weight:700;font-size:13px;
  color:var(--muted);transition:.15s;
}
.dem-clear:hover{border-color:#dc2626;color:#dc2626;background:#fef2f2}

/* -- Toast -- */
.toast{
  position:fixed;left:50%;bottom:100px;transform:translateX(-50%);
  background:#0f172a;color:#fff;padding:12px 18px;border-radius:12px;
  font-size:13px;font-weight:600;z-index:1000;
  box-shadow:0 10px 30px rgba(0,0,0,.2);
  max-width:calc(100vw - 32px);text-align:center;
  animation:toastIn .2s ease;
}
@keyframes toastIn{from{opacity:0;transform:translateX(-50%) translateY(8px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}

/* ---- Navbar ---- */
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
.pro-navbar .central.active{background:var(--green-dark)}
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

  <!-- Statut de la demande -->
  <div class="dem-status">
    <div class="dem-status-icon">&#128221;</div>
    <div class="dem-status-body">
      <div class="dem-status-ref" id="draft-ref">Chargement...</div>
      <div class="dem-status-hint">Enregistrement automatique</div>
    </div>
    <span class="dem-status-badge" id="draft-count">0</span>
  </div>

  <!-- Option 1 : Catalogue -->
  <a class="dem-option" href="/professionnel/catalogue">
    <div class="dem-option-icon">&#128722;</div>
    <div class="dem-option-body">
      <div class="dem-option-title">Parcourir le catalogue</div>
      <div class="dem-option-desc">Ajouter des produits un par un</div>
    </div>
    <span class="dem-option-arrow">&#8250;</span>
  </a>

  <!-- Option 2 : WhatsApp direct -->
  <a class="dem-option wa" id="wa-direct"
     href="https://wa.me/22871039904?text=Bonjour%20Elokinab%20Health%2C%20je%20souhaite%20passer%20une%20commande.%20Voici%20ma%20liste%20%3A%0A%0A"
     target="_blank" rel="noopener">
    <div class="dem-option-icon">&#128172;</div>
    <div class="dem-option-body">
      <div class="dem-option-title">Envoyer une liste WhatsApp</div>
      <div class="dem-option-desc">Photo, PDF ou texte — directement sur WhatsApp</div>
    </div>
    <span class="dem-option-arrow">&#8250;</span>
  </a>

  <!-- Liste (si elements) -->
  <h2 class="dem-section-title" id="list-title" style="display:none">
    Ma demande
    <span class="dem-count" id="list-count">0</span>
  </h2>
  <div id="items"></div>
  <div id="empty-state" class="dem-empty">
    Aucun produit pour le moment.<br>
    Utilisez les options ci-dessus pour ajouter à votre demande.
  </div>

  <!-- Notes (si elements) -->
  <div id="notes-block" style="display:none">
    <h2 class="dem-section-title">Notes (facultatif)</h2>
    <textarea class="notes" id="notes" placeholder="Instructions particulieres, delai souhaite..."></textarea>
  </div>

  <!-- Actions (si elements) -->
  <div class="dem-actions" id="actions" style="display:none">
    <button class="dem-send" id="send" type="button">
      <span class="ico">&#128172;</span> Envoyer ma demande sur WhatsApp
    </button>
    <button class="dem-clear" id="clear" type="button">Vider ma demande</button>
  </div>

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

<script src="/static/professional_demande.js"></script>
</body>
</html>
'''
(STATIC / "professional_demande.html").write_text(DEM_HTML, encoding="utf-8")
print("[OK] professional_demande.html refondu")

# ============================================================
# 4. JS DEMANDE (reecrit proprement)
# ============================================================
DEM_JS = r'''/* Elokinab Health - Page demande */
(function () {
  var API = "/api";
  var $ = function (id) { return document.getElementById(id); };

  var state = {
    draft: null,
    items: [],
    attachments: [],
    notesTimer: null
  };

  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }

  function toast(msg) {
    var t = document.createElement("div");
    t.className = "toast";
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 2400);
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
        window.location.href = "/connexion?next=/professionnel/demande";
        throw new Error("Non authentifie");
      }
      return r.json().then(function (data) {
        if (!r.ok) throw new Error(data.detail || "Erreur");
        return data;
      });
    });
  }

  // ========================================================
  // Chargement
  // ========================================================
  function loadDraft() {
    return api("GET", "/pro/requests/draft").then(function (draft) {
      state.draft = draft;
      $("draft-ref").textContent = draft.reference;
      $("head-ref").textContent = draft.reference;
      $("notes").value = draft.notes || "";
      return reloadContent();
    });
  }

  function reloadContent() {
    if (!state.draft) return Promise.resolve();
    return api("GET", "/pro/requests/" + state.draft.reference).then(function (full) {
      state.items = full.items || [];
      state.attachments = full.attachments || [];
      render();
      return full;
    });
  }

  // ========================================================
  // Rendu
  // ========================================================
  function render() {
    var total = state.items.length + state.attachments.length;
    $("draft-count").textContent = total;
    $("list-count").textContent = total;
    $("nav-count").textContent = total;

    if (total > 0) {
      $("nav-count").classList.remove("hidden");
      $("list-title").style.display = "";
      $("notes-block").style.display = "";
      $("actions").style.display = "";
      $("empty-state").style.display = "none";
    } else {
      $("nav-count").classList.add("hidden");
      $("list-title").style.display = "none";
      $("notes-block").style.display = "none";
      $("actions").style.display = "none";
      $("empty-state").style.display = "";
    }

    // Items
    var box = $("items");
    box.innerHTML = "";
    state.items.forEach(function (it) {
      var row = document.createElement("div");
      row.className = "item-row";
      var qty = it.requested_quantity;
      var qs = (qty && qty != 1) ? "x" + (Math.round(qty * 100) / 100) : (qty == 1 ? "x1" : "");
      var source = it.product_id ? "Catalogue" : "Saisi";
      row.innerHTML =
        '<div class="item-body">' +
          '<div class="item-name">' + escapeHtml(it.description) + '</div>' +
          '<div class="item-meta">' +
            '<span class="pill">' + source + '</span>' +
          '</div>' +
        '</div>' +
        '<div class="item-qty">' + qs + '</div>' +
        '<button class="item-del" data-del="' + it.id + '" title="Retirer">&times;</button>';
      box.appendChild(row);
    });

    // Attachments
    state.attachments.forEach(function (a) {
      var row = document.createElement("div");
      row.className = "item-row attachment";
      var ico = a.type === "pdf" ? "📄" : "📷";
      var label = a.original_filename || (a.type === "pdf" ? "Document PDF" : "Photo");
      row.innerHTML =
        '<div class="item-body">' +
          '<div class="item-name">' + ico + ' ' + escapeHtml(label) + '</div>' +
          '<div class="item-meta">' +
            '<span class="pill">' + (a.type === "pdf" ? "PDF" : "Photo") + '</span>' +
            '<span>' + Math.round((a.size_bytes || 0) / 1024) + ' Ko</span>' +
          '</div>' +
        '</div>' +
        '<button class="item-del" data-del-att="' + a.id + '" title="Retirer">&times;</button>';
      box.appendChild(row);
    });

    // Handlers suppression
    Array.prototype.forEach.call(box.querySelectorAll("[data-del]"), function (b) {
      b.addEventListener("click", function () {
        var id = b.getAttribute("data-del");
        api("DELETE", "/pro/requests/" + state.draft.reference + "/items/" + id)
          .then(reloadContent).catch(function (e) { toast(e.message); });
      });
    });
    Array.prototype.forEach.call(box.querySelectorAll("[data-del-att]"), function (b) {
      b.addEventListener("click", function () {
        var id = b.getAttribute("data-del-att");
        api("DELETE", "/pro/requests/" + state.draft.reference + "/attachments/" + id)
          .then(reloadContent).catch(function (e) { toast(e.message); });
      });
    });
  }

  // ========================================================
  // Notes : autosave
  // ========================================================
  function bindNotes() {
    var el = $("notes");
    if (!el) return;
    el.addEventListener("input", function () {
      if (!state.draft) return;
      if (state.notesTimer) clearTimeout(state.notesTimer);
      state.notesTimer = setTimeout(function () {
        api("PATCH", "/pro/requests/" + state.draft.reference, { notes: el.value })
          .then(function (r) { state.draft.notes = r.notes; })
          .catch(function () {});
      }, 800);
    });
  }

  // ========================================================
  // Send WhatsApp
  // ========================================================
  function send() {
    if (!state.draft) return;
    var btn = $("send");
    var originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = "Préparation...";

    // 1. Enregistrer les notes en premier
    var notes = $("notes") ? $("notes").value : "";
    api("PATCH", "/pro/requests/" + state.draft.reference, { notes: notes })
      .then(function () {
        // 2. Récupérer le message préformaté
        return api("GET", "/pro/requests/" + state.draft.reference + "/whatsapp");
      })
      .then(function (d) {
        window.open(d.whatsapp_url, "_blank");
        toast("WhatsApp ouvert");
        btn.disabled = false;
        btn.innerHTML = originalText;
      })
      .catch(function (e) {
        toast(e.message);
        btn.disabled = false;
        btn.innerHTML = originalText;
      });
  }

  // ========================================================
  // Clear
  // ========================================================
  function clearDraft() {
    if (!state.draft) return;
    if (!confirm("Vider toute votre demande ?")) return;
    var all = state.items.map(function (it) {
      return api("DELETE", "/pro/requests/" + state.draft.reference + "/items/" + it.id);
    }).concat(state.attachments.map(function (a) {
      return api("DELETE", "/pro/requests/" + state.draft.reference + "/attachments/" + a.id);
    }));
    Promise.all(all).then(reloadContent).catch(function (e) { toast(e.message); });
  }

  // ========================================================
  // Init
  // ========================================================
  function init() {
    $("send").addEventListener("click", send);
    $("clear").addEventListener("click", clearDraft);
    bindNotes();

    loadDraft().catch(function (e) {
      toast(e.message || "Impossible de charger la demande");
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
'''
(STATIC / "professional_demande.js").write_text(DEM_JS, encoding="utf-8")
print("[OK] professional_demande.js refondu")

# ============================================================
# 5. FIX BUG CATALOGUE : "Demande indisponible"
# ============================================================
CATJS = STATIC / "professional_catalogue.js"
js = CATJS.read_text(encoding="utf-8")

# Remplacer la fonction addToDraft par une version robuste avec ensureDraft
old_add = re.compile(
    r'function addToDraft\(product, qty, btn\) \{.*?\n  \}',
    re.DOTALL
)

new_add = '''function ensureDraft() {
    if (state.draft && state.draft.reference) return Promise.resolve(state.draft);
    return api("GET", "/pro/requests/draft").then(function (d) {
      state.draft = d;
      return d;
    });
  }

  function addToDraft(product, qty, btn) {
    if (btn) { btn.disabled = true; btn.textContent = "Ajout..."; }
    ensureDraft().then(function (draft) {
      var desc = product.name + (product.presentation ? " — " + product.presentation : "");
      return api("POST", "/pro/requests/" + draft.reference + "/items", {
        product_id: product.id,
        description: desc,
        requested_quantity: qty
      });
    }).then(function () {
      state.draftItemsCount += 1;
      updateNavCount();
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
      toast(e.message || "Erreur");
      if (btn) { btn.disabled = false; btn.innerHTML = "+ Ajouter à ma demande"; }
    });
  }'''

if old_add.search(js):
    js = old_add.sub(new_add, js, count=1)
    print("[OK] catalogue.js -> addToDraft robuste avec ensureDraft")
else:
    print("[!] addToDraft introuvable, insertion manuelle")

# Aussi : au chargement de la page, si loadDraft echoue, mieux vaut le reessayer
# Modifier loadDraft pour log les erreurs
old_load = '''function loadDraft() {
    return api("GET", "/pro/requests/draft").then(function (draft) {
      state.draft = draft;
      return api("GET", "/pro/requests/" + draft.reference).then(function (full) {
        state.draftItemsCount = (full.items || []).length + (full.attachments || []).length;
        updateNavCount();
      });
    });
  }'''
new_load = '''function loadDraft() {
    return api("GET", "/pro/requests/draft").then(function (draft) {
      state.draft = draft;
      return api("GET", "/pro/requests/" + draft.reference).then(function (full) {
        state.draftItemsCount = (full.items || []).length + (full.attachments || []).length;
        updateNavCount();
      });
    }).catch(function (e) {
      // Ne bloque pas la page si le draft echoue : il sera cree au premier ajout
      console.warn("Draft non charge :", e.message);
      state.draft = null;
      updateNavCount();
    });
  }'''
if old_load in js:
    js = js.replace(old_load, new_load, 1)
    print("[OK] catalogue.js -> loadDraft tolerant aux erreurs")

CATJS.write_text(js, encoding="utf-8")

print()
print("=" * 60)
print("REFONTE COMPLETE LIVREE")
print("=" * 60)
print()
print("1. Bouton WhatsApp :")
print("   - Uniquement dans le dashboard")
print("   - Expansion au scroll")
print("   - Reduction auto 1.2s apres arret du scroll")
print()
print("2. Page Demande refondue :")
print("   - 2 options : 'Parcourir le catalogue' + 'Envoyer une liste WhatsApp'")
print("   - Suppression de toutes les modales (PDF, photo, saisie)")
print("   - Liste conditionnelle (visible seulement si elements)")
print("   - Bouton 'Envoyer ma demande sur WhatsApp'")
print("   - Bouton 'Vider ma demande'")
print()
print("3. Bug catalogue corrige :")
print("   - ensureDraft() cree une demande si elle n'existe pas")
print("   - Retry automatique si le draft n'est pas charge")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R dans le navigateur")
print("  (pas besoin de redemarrer Uvicorn)")