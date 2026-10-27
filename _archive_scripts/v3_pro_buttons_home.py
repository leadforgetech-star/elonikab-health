"""
v3_pro_buttons_home.py
Ajoute les boutons WhatsApp + Recommander sur la page d'accueil (/)
Visibles uniquement pour les utilisateurs PROFESSIONNEL connectes.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
INDEX = STATIC / "index.html"
APPJS = STATIC / "app.js"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_pro_home_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(INDEX, backup / "index.html")
shutil.copy2(APPJS, backup / "app.js")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. index.html : conteneur pour les boutons pro
# ============================================================
html = INDEX.read_text(encoding="utf-8")

if 'id="pro-quick-actions"' not in html:
    # Inserer juste apres la section hero (avant <h2 class="section-title">Categories</h2>)
    anchor = '<h2 class="section-title">Categories</h2>'
    block = '''<section id="pro-quick-actions" class="pro-quick hidden">
      <h2 class="section-title">Actions rapides pro</h2>
      <div class="pro-quick-grid">
        <button type="button" class="pro-quick-btn wa" id="home-wa-btn">
          <span class="pro-quick-icon">&#128242;</span>
          <span class="pro-quick-text">
            <strong>Envoyer ma liste WhatsApp</strong>
            <small>Commander rapidement via WhatsApp</small>
          </span>
        </button>
        <button type="button" class="pro-quick-btn reorder" id="home-reorder-btn">
          <span class="pro-quick-icon">&#128257;</span>
          <span class="pro-quick-text">
            <strong>Recommander ma derniere commande</strong>
            <small>Recharger le panier en 1 clic</small>
          </span>
        </button>
      </div>
    </section>

    <div id="home-wa-modal" class="pro-quick-modal hidden">
      <div class="pro-quick-backdrop" data-close-home-wa></div>
      <div class="pro-quick-modal-content">
        <header class="pro-quick-modal-head">
          <h3>&#128242; Liste WhatsApp</h3>
          <button type="button" class="pro-quick-close" data-close-home-wa>&times;</button>
        </header>
        <div class="pro-quick-modal-body">
          <p class="muted small">Modifiez la liste ci-dessous, puis cliquez sur "Ouvrir WhatsApp".</p>
          <textarea id="home-wa-text" rows="12" placeholder="Votre liste de produits..."></textarea>
          <div id="home-wa-info" class="muted small"></div>
        </div>
        <footer class="pro-quick-modal-foot">
          <button type="button" class="btn btn-ghost" data-close-home-wa>Annuler</button>
          <button type="button" class="btn btn-primary" id="home-wa-send">Ouvrir WhatsApp</button>
        </footer>
      </div>
    </div>

    '''
    if anchor in html:
        html = html.replace(anchor, block + anchor, 1)
        INDEX.write_text(html, encoding="utf-8")
        print("[OK] index.html -> boutons pro + modal")
    else:
        print("[!] anchor Categories introuvable")

    # Styles
    STYLE = '''<style>
      .pro-quick{margin-top:28px}
      .pro-quick.hidden{display:none}
      .pro-quick-grid{
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
        gap:12px;
      }
      .pro-quick-btn{
        display:flex;align-items:center;gap:14px;
        padding:16px 18px;border-radius:16px;border:1px solid #ddece6;
        background:#fff;cursor:pointer;font-family:inherit;text-align:left;
        transition:.15s;width:100%;
      }
      .pro-quick-btn:hover{border-color:#0f9d76;box-shadow:0 6px 20px rgba(15,157,118,.12);transform:translateY(-2px)}
      .pro-quick-btn.wa{background:linear-gradient(135deg,#e8f7f1,#d6efe6);border-color:#c7e9dc}
      .pro-quick-btn.reorder{background:linear-gradient(135deg,#f4f0ff,#e9e0ff);border-color:#d6c8ff}
      .pro-quick-icon{
        font-size:28px;line-height:1;
        width:52px;height:52px;border-radius:14px;
        display:flex;align-items:center;justify-content:center;
        background:#fff;flex-shrink:0;
      }
      .pro-quick-text{display:flex;flex-direction:column;gap:3px;flex:1;min-width:0}
      .pro-quick-text strong{font-size:15px;color:#0f2620}
      .pro-quick-text small{font-size:12px;color:#6c8a80}

      .pro-quick-modal{position:fixed;inset:0;z-index:200;display:flex;align-items:center;justify-content:center;padding:14px}
      .pro-quick-modal.hidden{display:none}
      .pro-quick-backdrop{position:absolute;inset:0;background:rgba(15,38,32,.45)}
      .pro-quick-modal-content{
        position:relative;background:#fff;border-radius:16px;
        width:100%;max-width:520px;max-height:90vh;display:flex;flex-direction:column;
        box-shadow:0 20px 60px rgba(15,38,32,.25);overflow:hidden;
      }
      .pro-quick-modal-head{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid #ddece6}
      .pro-quick-modal-head h3{margin:0;font-size:16px}
      .pro-quick-close{background:none;border:0;font-size:24px;line-height:1;color:#6c8a80;cursor:pointer;padding:0 4px}
      .pro-quick-modal-body{padding:14px 18px;overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:10px}
      .pro-quick-modal-body textarea{
        width:100%;padding:12px 14px;border:1px solid #ddece6;border-radius:11px;
        font-family:inherit;font-size:14px;resize:vertical;outline:none;box-sizing:border-box;
      }
      .pro-quick-modal-body textarea:focus{border-color:#0f9d76}
      .pro-quick-modal-foot{display:flex;gap:10px;padding:14px 18px;border-top:1px solid #ddece6;background:#f4faf7}
      .pro-quick-modal-foot .btn{flex:1;padding:12px;font-size:14px}

      @media (max-width:600px){
        .pro-quick-grid{grid-template-columns:1fr}
        .pro-quick-icon{width:44px;height:44px;font-size:22px}
        .pro-quick-text strong{font-size:14px}
      }
    </style>
    '''
    if ".pro-quick{" not in html:
        html = html.replace("</head>", STYLE + "</head>", 1)
        INDEX.write_text(html, encoding="utf-8")
        print("[OK] index.html -> styles ajoutes")
else:
    print("[i] index.html deja patche")

# ============================================================
# 2. app.js : logique (verifie le role, affiche/cache, gere clic)
# ============================================================
js = APPJS.read_text(encoding="utf-8")

PRO_JS = '''

// ====== Boutons pro sur l'accueil ======
(function () {
  var state = { whatsapp: "", structure: "", pharmacy: "Elokinab Health", user: null };

  function $(id) { return document.getElementById(id); }

  function showProButtons(user) {
    var box = $("pro-quick-actions");
    if (!box) return;
    if (user && user.role === "PROFESSIONNEL") {
      box.classList.remove("hidden");
    } else {
      box.classList.add("hidden");
    }
  }

  function loadInfo() {
    return fetch("/api/pro/whatsapp-info", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) return;
        state.whatsapp = d.whatsapp_number || "";
        state.structure = d.structure_name || "";
        state.pharmacy = d.pharmacy_name || "Elokinab Health";
        var info = $("home-wa-info");
        if (info) {
          if (state.whatsapp) {
            info.textContent = "Destinataire WhatsApp : " + state.whatsapp;
          } else {
            info.textContent = "Numero WhatsApp non configure. Contactez la pharmacie.";
          }
        }
      });
  }

  function buildDefaultList() {
    return [
      "Bonjour " + state.pharmacy + " \\uD83D\\uDC4B",
      "",
      "Nous souhaitons passer une commande pour notre structure.",
      "",
      "\\uD83C\\uDFE5 Structure : " + (state.structure || "................"),
      "",
      "\\uD83D\\uDCCB Liste :",
      "- ................... (quantite)",
      "- ................... (quantite)",
      "- ................... (quantite)",
      "",
      "Merci de nous confirmer la disponibilite, les prix et le delai de livraison."
    ].join("\\n");
  }

  function openWa() {
    var ta = $("home-wa-text");
    if (ta && !ta.value) ta.value = buildDefaultList();
    var m = $("home-wa-modal");
    if (m) { m.classList.remove("hidden"); document.body.style.overflow = "hidden"; }
    loadInfo();
  }
  function closeWa() {
    var m = $("home-wa-modal");
    if (m) { m.classList.add("hidden"); document.body.style.overflow = ""; }
  }
  function sendWa() {
    if (!state.whatsapp) {
      alert("La pharmacie n'a pas encore configure son numero WhatsApp.");
      return;
    }
    var phone = String(state.whatsapp).replace(/\\D/g, "");
    if (!phone) { alert("Numero WhatsApp invalide"); return; }
    var msg = ($("home-wa-text") || {}).value || "";
    window.open("https://wa.me/" + phone + "?text=" + encodeURIComponent(msg), "_blank");
    closeWa();
  }

  function reorder() {
    var btn = $("home-reorder-btn");
    if (!btn) return;
    var orig = btn.querySelector(".pro-quick-text strong");
    var oldTxt = orig ? orig.textContent : "";
    btn.disabled = true;
    if (orig) orig.textContent = "Recherche...";

    fetch("/api/orders/mine", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (list) {
        if (!list || list.length === 0) {
          alert("Aucune commande precedente.");
          btn.disabled = false;
          if (orig) orig.textContent = oldTxt;
          return;
        }
        var ref = list[0].reference;
        return fetch("/api/orders/" + encodeURIComponent(ref) + "/reorder", {
          method: "POST", credentials: "same-origin"
        }).then(function (r) {
          return r.json().then(function (d) {
            if (!r.ok) throw new Error(d.detail || "Erreur");
            return d;
          });
        }).then(function (d) {
          alert(d.added + " produit(s) ajoute(s) au panier." +
                (d.skipped > 0 ? " " + d.skipped + " indisponible(s)." : ""));
          window.location.href = "/static/cart.html";
        });
      })
      .catch(function (e) {
        alert(e.message || "Erreur");
        btn.disabled = false;
        if (orig) orig.textContent = oldTxt;
      });
  }

  function init() {
    // Detecter le role via /api/auth/me (utilise le cache header.js si dispo)
    fetch("/api/auth/me", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (user) {
        state.user = user;
        showProButtons(user);
      })
      .catch(function () { showProButtons(null); });

    var waBtn = $("home-wa-btn");
    if (waBtn) waBtn.addEventListener("click", openWa);
    var rdBtn = $("home-reorder-btn");
    if (rdBtn) rdBtn.addEventListener("click", reorder);

    var closes = document.querySelectorAll("[data-close-home-wa]");
    Array.prototype.forEach.call(closes, function (b) {
      b.addEventListener("click", closeWa);
    });
    var sendBtn = $("home-wa-send");
    if (sendBtn) sendBtn.addEventListener("click", sendWa);

    // Reagir au login/logout : ecoute les changements de page
    window.addEventListener("focus", function () {
      fetch("/api/auth/me", { credentials: "same-origin" })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(showProButtons)
        .catch(function () { showProButtons(null); });
    });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
'''

if "home-wa-btn" not in js and "Boutons pro sur l'accueil" not in js:
    js = js + PRO_JS
    APPJS.write_text(js, encoding="utf-8")
    print("[OK] app.js -> boutons pro sur l'accueil")
else:
    print("[i] app.js deja patche")

print()
print("=" * 60)
print("BOUTONS PRO SUR L'ACCUEIL INSTALLES")
print("=" * 60)
print()
print("Comportement :")
print("  - Utilisateur PROFESSIONNEL connecte -> voit 2 gros boutons")
print("    sous le hero de la page d'accueil")
print("  - Autre role (patient, pharmacien, admin) -> ne voit rien")
print("  - Non connecte -> ne voit rien")
print()
print("  - Bouton WhatsApp : ouvre un modal avec liste editable")
print("  - Bouton Recommander : recharge le panier avec la derniere commande")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur l'iPhone (ou navigation privee)")