"""
v4_pro_rework.py
- Fix sauvegarde numero WhatsApp dans parametres pharmacie
- Configure 71039904 partout (payment, whatsapp, phone)
- Refonte professional.html : boutons en HAUT, visibles immediatement
- Nouveau flux WhatsApp liste : 3 options (Saisir / PDF / Photo)
- Champ structure : produit + quantite (liste dynamique)
"""
from pathlib import Path
import datetime
import shutil
import sqlite3

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
MAIN = BASE / "main.py"
DB = BASE / "database.db"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_pro_rework_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(DB, backup / "database.db")
shutil.copy2(MAIN, backup / "main.py")
for f in ("professional.html", "professional.js", "pharmacien.js", "pharmacien.html", "header.js"):
    p = STATIC / f
    if p.exists():
        shutil.copy2(p, backup / f)
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. Configurer le numero 71039904 dans la base
# ============================================================
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("""
    UPDATE pharmacy_settings SET
      whatsapp_number = COALESCE(NULLIF(whatsapp_number,''), '+22871039904'),
      payment_number = COALESCE(NULLIF(payment_number,''), '+22871039904'),
      pharmacy_phone = COALESCE(NULLIF(pharmacy_phone,''), '+22871039904')
    WHERE id = 1
""")
conn.commit()
row = cur.execute("SELECT whatsapp_number, payment_number, pharmacy_phone FROM pharmacy_settings WHERE id=1").fetchone()
print("[OK] Base -> config:")
print("     whatsapp_number :", row[0])
print("     payment_number  :", row[1])
print("     pharmacy_phone  :", row[2])
conn.close()

# ============================================================
# 2. Fix main.py : ajouter whatsapp_number + autres au SettingsUpdate
#    (verifier que la route PATCH /api/settings persiste bien)
# ============================================================
src = MAIN.read_text(encoding="utf-8")

# Verifier que SettingsUpdate contient whatsapp_number
if "whatsapp_number: Optional[str]" not in src:
    old_model_start = src.find("class SettingsUpdate(BaseModel):")
    if old_model_start != -1:
        # trouver la fin de la classe (ligne vide apres)
        old_model_end = src.find("\n\n", old_model_start)
        old_block = src[old_model_start:old_model_end]
        new_block = old_block.rstrip()
        if "whatsapp_number" not in old_block:
            new_block += "\n    whatsapp_number: Optional[str] = None"
        src = src[:old_model_start] + new_block + src[old_model_end:]
        MAIN.write_text(src, encoding="utf-8")
        print("[OK] main.py -> whatsapp_number ajoute au SettingsUpdate")
    else:
        print("[!] SettingsUpdate introuvable")
else:
    print("[i] whatsapp_number deja dans SettingsUpdate")

# ============================================================
# 3. professional.html : refonte complete avec boutons EN HAUT
# ============================================================
PRO_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Espace professionnel - Elokinab Health</title>
<link rel="stylesheet" href="/static/auth.css">
<link rel="stylesheet" href="/static/header.css">
<link rel="stylesheet" href="/static/mobile.css">
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
  body{background:#f4faf7;margin:0;font-family:"Segoe UI",system-ui,sans-serif;color:#0f2620}
  .pro-wrap{max-width:720px;margin:0 auto;padding:16px 14px 40px 14px}

  .pro-hero{
    background:linear-gradient(135deg,#0f9d76,#37c79c);
    color:#fff;border-radius:18px;padding:22px 20px;margin-bottom:18px;
    box-shadow:0 10px 30px rgba(15,157,118,.25);
  }
  .pro-hero h1{margin:0 0 4px;font-size:22px;line-height:1.2}
  .pro-hero p{margin:0;font-size:13px;opacity:.9}

  .pro-actions{
    display:grid;gap:12px;margin-bottom:22px;
  }
  .pro-action-card{
    display:flex;align-items:center;gap:14px;
    padding:18px;border-radius:16px;border:0;cursor:pointer;
    font-family:inherit;text-align:left;width:100%;
    transition:transform .15s, box-shadow .15s;
    box-shadow:0 4px 14px rgba(15,38,32,.06);
  }
  .pro-action-card:hover{transform:translateY(-2px);box-shadow:0 8px 22px rgba(15,38,32,.12)}
  .pro-action-card.wa{
    background:linear-gradient(135deg,#e8f7f1,#c9ead9);
    border:2px solid #0f9d76;
  }
  .pro-action-card.reorder{
    background:linear-gradient(135deg,#f4f0ff,#e4d8ff);
    border:2px solid #8b6fd8;
  }
  .pro-action-icon{
    font-size:30px;line-height:1;
    width:56px;height:56px;border-radius:14px;
    display:flex;align-items:center;justify-content:center;
    background:#fff;flex-shrink:0;
  }
  .pro-action-text{display:flex;flex-direction:column;gap:3px;flex:1;min-width:0}
  .pro-action-text strong{font-size:15px;color:#0f2620;font-weight:800}
  .pro-action-text small{font-size:12px;color:#6c8a80;line-height:1.3}

  /* Bloc profil (en bas, plus discret) */
  .pro-profile-card{
    background:#fff;border:1px solid #ddece6;border-radius:16px;
    padding:20px;margin-bottom:14px;
  }
  .pro-profile-card h2{
    margin:0 0 6px;font-size:16px;
  }
  .pro-profile-card p.sub{
    margin:0 0 16px;font-size:13px;color:#6c8a80;
  }
  .pro-field{display:flex;flex-direction:column;gap:6px;margin-bottom:12px}
  .pro-field label{font-size:13px;font-weight:700;color:#0f2620}
  .pro-field input, .pro-field select, .pro-field textarea{
    padding:12px 14px;border:1px solid #ddece6;border-radius:11px;
    font-family:inherit;font-size:15px;outline:none;box-sizing:border-box;width:100%;
    background:#fff;
  }
  .pro-field input:focus,.pro-field select:focus,.pro-field textarea:focus{border-color:#0f9d76}
  .pro-gps-row{display:flex;gap:8px}
  .pro-gps-row input{flex:1}
  .pro-submit{
    width:100%;padding:14px;border:0;border-radius:12px;
    background:#0f9d76;color:#fff;font-weight:800;font-size:15px;
    cursor:pointer;font-family:inherit;
  }
  .pro-submit:hover{background:#0a7a5a}

  /* Modal WhatsApp */
  .wa-modal{position:fixed;inset:0;z-index:9000;display:flex;align-items:flex-end;justify-content:center}
  .wa-modal.hidden{display:none}
  .wa-backdrop{position:absolute;inset:0;background:rgba(15,38,32,.5)}
  .wa-panel{
    position:relative;background:#fff;width:100%;max-width:520px;
    max-height:94vh;border-radius:20px 20px 0 0;
    display:flex;flex-direction:column;overflow:hidden;
    box-shadow:0 -10px 40px rgba(15,38,32,.25);
    animation:slideUp .25s ease;
  }
  @keyframes slideUp{from{transform:translateY(100%)}to{transform:translateY(0)}}
  .wa-head{
    padding:16px 18px;border-bottom:1px solid #ddece6;
    display:flex;align-items:center;justify-content:space-between;gap:10px;
  }
  .wa-head h3{margin:0;font-size:16px}
  .wa-close{background:none;border:0;font-size:26px;line-height:1;color:#6c8a80;cursor:pointer;padding:0 6px}
  .wa-body{padding:16px 18px;overflow-y:auto;flex:1}

  .wa-step-title{font-size:14px;font-weight:700;color:#0f2620;margin:0 0 12px}
  .wa-choice{
    display:flex;align-items:center;gap:14px;padding:16px;
    border:2px solid #ddece6;border-radius:14px;background:#fff;
    cursor:pointer;font-family:inherit;text-align:left;width:100%;
    margin-bottom:10px;transition:.15s;
  }
  .wa-choice:hover{border-color:#0f9d76;background:#f0faf6}
  .wa-choice-icon{font-size:26px;width:48px;height:48px;border-radius:12px;
    background:#e8f7f1;display:flex;align-items:center;justify-content:center;flex-shrink:0}
  .wa-choice-text{display:flex;flex-direction:column;gap:2px;flex:1;min-width:0}
  .wa-choice-text strong{font-size:14px;color:#0f2620}
  .wa-choice-text small{font-size:12px;color:#6c8a80}

  /* Liste structuree */
  .wa-list{margin-bottom:12px}
  .wa-row{
    display:flex;gap:8px;margin-bottom:8px;align-items:center;
  }
  .wa-row input[type=text]{
    flex:1;min-width:0;padding:11px 13px;border:1px solid #ddece6;
    border-radius:10px;font-family:inherit;font-size:14px;box-sizing:border-box;
  }
  .wa-row input[type=number]{
    width:70px;padding:11px 8px;border:1px solid #ddece6;text-align:center;
    border-radius:10px;font-family:inherit;font-size:14px;box-sizing:border-box;
  }
  .wa-row-del{
    width:32px;height:32px;border:0;background:#fdecec;color:#b23c3c;
    border-radius:8px;cursor:pointer;font-size:16px;line-height:1;
  }
  .wa-add{
    background:#e8f7f1;border:1px dashed #0f9d76;color:#0a7a5a;
    padding:10px;border-radius:10px;width:100%;font-family:inherit;
    font-weight:700;font-size:13px;cursor:pointer;margin-bottom:14px;
  }

  .wa-file-zone{
    border:2px dashed #ddece6;border-radius:14px;padding:24px 16px;
    text-align:center;background:#fafdfb;margin-bottom:14px;
  }
  .wa-file-zone input{display:none}
  .wa-file-zone label{
    display:inline-block;padding:12px 20px;background:#0f9d76;color:#fff;
    border-radius:10px;cursor:pointer;font-weight:700;font-size:14px;
    font-family:inherit;
  }
  .wa-file-name{margin-top:10px;font-size:13px;color:#0a7a5a;font-weight:700}

  .wa-preview{
    background:#f4faf7;border:1px solid #c7e9dc;border-radius:12px;
    padding:12px 14px;font-size:13px;color:#0f2620;white-space:pre-wrap;
    font-family:Consolas,monospace;line-height:1.5;margin-bottom:14px;
    max-height:200px;overflow-y:auto;
  }

  .wa-foot{
    padding:14px 18px;border-top:1px solid #ddece6;background:#f4faf7;
    display:flex;gap:10px;
  }
  .wa-foot button{flex:1;padding:14px;border-radius:12px;border:0;
    font-family:inherit;font-weight:800;font-size:15px;cursor:pointer}
  .wa-btn-back{background:#fff;color:#6c8a80;border:1px solid #ddece6 !important}
  .wa-btn-send{background:#25d366;color:#fff}
  .wa-btn-send:hover{background:#1da851}
  .wa-btn-send:disabled{background:#c9e5d4;cursor:not-allowed}
  .wa-info-line{font-size:12px;color:#6c8a80;margin:8px 0 0}

  .hidden{display:none !important}
</style>
</head>
<body>

<header class="topbar">
  <div class="container topbar-inner">
    <a class="brand" href="/">
      <span class="brand-logo">+</span>
      <span class="brand-text">
        <strong>Elokinab Health</strong>
        <small>Espace professionnel</small>
      </span>
    </a>
  </div>
</header>

<main class="pro-wrap">

  <!-- HERO -->
  <div class="pro-hero">
    <h1 id="hello">Bienvenue</h1>
    <p>Commandez pour votre etablissement en 2 clics.</p>
  </div>

  <!-- ACTIONS RAPIDES (EN HAUT, VISIBLES IMMEDIATEMENT) -->
  <div class="pro-actions">

    <button type="button" class="pro-action-card wa" id="wa-open">
      <span class="pro-action-icon">&#128203;</span>
      <span class="pro-action-text">
        <strong>Envoyer une liste sur WhatsApp</strong>
        <small>Ecrivez, importez un PDF ou ajoutez une photo</small>
      </span>
    </button>

    <button type="button" class="pro-action-card reorder" id="reorder-btn">
      <span class="pro-action-icon">&#128257;</span>
      <span class="pro-action-text">
        <strong>Recommander ma derniere commande</strong>
        <small>Recharger le panier en 1 clic</small>
      </span>
    </button>

    <a class="pro-action-card" href="/" style="background:#fff;border:1px solid #ddece6;text-decoration:none">
      <span class="pro-action-icon">&#128722;</span>
      <span class="pro-action-text">
        <strong>Parcourir le catalogue</strong>
        <small>Ajouter des produits au panier</small>
      </span>
    </a>

  </div>

  <!-- PROFIL (EN BAS) -->
  <div class="pro-profile-card">
    <h2>Mon etablissement</h2>
    <p class="sub">Ces informations figurent sur vos commandes et factures.</p>

    <div id="msg" class="auth-msg hidden"></div>

    <div class="pro-field">
      <label for="structure_name">Nom de l'etablissement</label>
      <input type="text" id="structure_name" required>
    </div>

    <div class="pro-field">
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

    <div class="pro-field">
      <label for="manager_name">Responsable</label>
      <input type="text" id="manager_name" required>
    </div>

    <div class="pro-field">
      <label for="phone">Telephone</label>
      <input type="tel" id="phone" required>
    </div>

    <div class="pro-field">
      <label for="email">Email de contact</label>
      <input type="email" id="email">
    </div>

    <div class="pro-field">
      <label for="address">Adresse</label>
      <input type="text" id="address">
    </div>

    <div class="pro-field">
      <label>Position GPS (facultatif)</label>
      <div class="pro-gps-row">
        <input type="number" id="latitude" step="0.00001" placeholder="Latitude">
        <input type="number" id="longitude" step="0.00001" placeholder="Longitude">
      </div>
      <button type="button" class="wa-add" id="gps-btn" style="margin-top:8px">&#128205; Utiliser ma position actuelle</button>
    </div>

    <button class="pro-submit" id="save-profile">Enregistrer mon profil</button>
  </div>

</main>

<!-- MODAL WHATSAPP -->
<div id="wa-modal" class="wa-modal hidden">
  <div class="wa-backdrop" data-close-wa></div>
  <div class="wa-panel">

    <div class="wa-head">
      <h3 id="wa-title">&#128203; Envoyer une liste sur WhatsApp</h3>
      <button type="button" class="wa-close" data-close-wa>&times;</button>
    </div>

    <div class="wa-body">

      <!-- ETAPE 1 : Choix -->
      <div id="wa-step-1">
        <p class="wa-step-title">Comment souhaitez-vous preparer votre liste ?</p>

        <button type="button" class="wa-choice" data-choice="text">
          <span class="wa-choice-icon">&#9997;&#65039;</span>
          <span class="wa-choice-text">
            <strong>Saisir ma liste</strong>
            <small>Ecrivez directement les produits et quantites</small>
          </span>
        </button>

        <button type="button" class="wa-choice" data-choice="pdf">
          <span class="wa-choice-icon">&#128196;</span>
          <span class="wa-choice-text">
            <strong>Importer un PDF</strong>
            <small>Ajoutez votre liste au format PDF</small>
          </span>
        </button>

        <button type="button" class="wa-choice" data-choice="photo">
          <span class="wa-choice-icon">&#128247;</span>
          <span class="wa-choice-text">
            <strong>Ajouter une photo</strong>
            <small>Photographiez ou selectionnez votre liste</small>
          </span>
        </button>
      </div>

      <!-- ETAPE 2A : Saisie structuree -->
      <div id="wa-step-text" class="hidden">
        <p class="wa-step-title">Saisissez vos produits</p>
        <div class="wa-list" id="wa-list"></div>
        <button type="button" class="wa-add" id="wa-add-row">+ Ajouter une ligne</button>
        <div class="wa-preview" id="wa-preview-text"></div>
      </div>

      <!-- ETAPE 2B : PDF -->
      <div id="wa-step-pdf" class="hidden">
        <p class="wa-step-title">Importez votre liste au format PDF</p>
        <div class="wa-file-zone">
          <input type="file" id="wa-file-pdf" accept="application/pdf">
          <label for="wa-file-pdf">Choisir un fichier PDF</label>
          <div class="wa-file-name hidden" id="wa-pdf-name"></div>
        </div>
        <p class="wa-info-line">Le fichier sera joint manuellement dans WhatsApp.</p>
      </div>

      <!-- ETAPE 2C : PHOTO -->
      <div id="wa-step-photo" class="hidden">
        <p class="wa-step-title">Ajoutez une photo de votre liste</p>
        <div class="wa-file-zone">
          <input type="file" id="wa-file-photo" accept="image/*" capture="environment">
          <label for="wa-file-photo">Prendre ou choisir une photo</label>
          <div class="wa-file-name hidden" id="wa-photo-name"></div>
        </div>
        <p class="wa-info-line">La photo sera jointe manuellement dans WhatsApp.</p>
      </div>

    </div>

    <div class="wa-foot">
      <button type="button" class="wa-btn-back" id="wa-back">Retour</button>
      <button type="button" class="wa-btn-send" id="wa-send" disabled>&#128172; Envoyer sur WhatsApp</button>
    </div>

  </div>
</div>

<script src="/static/header.js"></script>
<script src="/static/professional.js"></script>
</body>
</html>
'''
(STATIC / "professional.html").write_text(PRO_HTML, encoding="utf-8")
print("[OK] professional.html reecrit")

# ============================================================
# 4. professional.js : nouvelle logique
# ============================================================
PRO_JS = r'''(function () {
  var API = "/api";
  var $ = function(id) { return document.getElementById(id); };
  var state = {
    step: 1,
    mode: null,
    lines: [{ name: "", qty: 1 }],
    file: null,
    whatsapp: "",
    pharmacy: "Elokinab Health",
    structure: ""
  };

  function showMsg(t, ok) {
    var m = $("msg"); if (!m) return;
    m.textContent = t;
    m.className = "auth-msg" + (ok ? " ok" : "");
    m.classList.remove("hidden");
    if (ok) setTimeout(function () { m.classList.add("hidden"); }, 3500);
  }
  function hideMsg() { var m = $("msg"); if (m) m.classList.add("hidden"); }

  // ================= Profil =================

  function loadProfile() {
    return fetch(API + "/professionals/me", { credentials: "same-origin" })
      .then(function (r) {
        if (r.status === 401) { window.location.href = "/connexion?next=/static/professional.html"; return null; }
        if (r.status === 404) return null;
        if (!r.ok) return null;
        return r.json();
      })
      .then(function (p) {
        if (!p) return;
        if ($("structure_name")) $("structure_name").value = p.structure_name || "";
        if ($("structure_type")) $("structure_type").value = p.structure_type || "CLINIQUE";
        if ($("manager_name")) $("manager_name").value = p.manager_name || "";
        if ($("phone")) $("phone").value = p.phone || "";
        if ($("email")) $("email").value = p.email || "";
        if ($("address")) $("address").value = p.address || "";
        if ($("latitude")) $("latitude").value = p.latitude || "";
        if ($("longitude")) $("longitude").value = p.longitude || "";
        if ($("hello")) $("hello").textContent = "Bonjour " + (p.structure_name || "Professionnel");
        state.structure = p.structure_name || "";
      });
  }

  function saveProfile() {
    hideMsg();
    var body = {
      structure_name: ($("structure_name") || {}).value || "",
      structure_type: ($("structure_type") || {}).value || "CLINIQUE",
      manager_name: ($("manager_name") || {}).value || "",
      phone: ($("phone") || {}).value || "",
      email: ($("email") || {}).value || "",
      address: ($("address") || {}).value || "",
      notes: ""
    };
    var lat = ($("latitude") || {}).value;
    var lon = ($("longitude") || {}).value;
    if (lat) body.latitude = parseFloat(lat);
    if (lon) body.longitude = parseFloat(lon);

    fetch(API + "/professionals/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body)
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    }).then(function () {
      showMsg("Profil enregistre.", true);
    }).catch(function (e) {
      showMsg(e.message);
    });
  }

  function gps() {
    if (!navigator.geolocation) { showMsg("GPS indisponible"); return; }
    var b = $("gps-btn");
    b.disabled = true; b.textContent = "Localisation...";
    navigator.geolocation.getCurrentPosition(function (pos) {
      $("latitude").value = pos.coords.latitude.toFixed(5);
      $("longitude").value = pos.coords.longitude.toFixed(5);
      b.disabled = false; b.innerHTML = "&#128205; Utiliser ma position actuelle";
    }, function () {
      b.disabled = false; b.innerHTML = "&#128205; Utiliser ma position actuelle";
      showMsg("Position introuvable");
    }, { enableHighAccuracy: true, timeout: 15000 });
  }

  // ================= WhatsApp Modal =================

  function openWa() {
    state.step = 1;
    state.mode = null;
    state.file = null;
    state.lines = [{ name: "", qty: 1 }];
    renderWa();
    $("wa-modal").classList.remove("hidden");
    document.body.style.overflow = "hidden";
    loadWaInfo();
  }
  function closeWa() {
    $("wa-modal").classList.add("hidden");
    document.body.style.overflow = "";
  }

  function loadWaInfo() {
    fetch(API + "/pro/whatsapp-info", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) return;
        state.whatsapp = d.whatsapp_number || "";
        state.pharmacy = d.pharmacy_name || "Elokinab Health";
        state.structure = d.structure_name || state.structure;
      });
  }

  function renderWa() {
    // Steps
    var s1 = $("wa-step-1");
    var sT = $("wa-step-text");
    var sP = $("wa-step-pdf");
    var sPh = $("wa-step-photo");
    s1.classList.add("hidden");
    sT.classList.add("hidden");
    sP.classList.add("hidden");
    sPh.classList.add("hidden");

    if (state.step === 1) {
      s1.classList.remove("hidden");
      $("wa-back").classList.add("hidden");
      $("wa-send").classList.add("hidden");
    } else {
      $("wa-back").classList.remove("hidden");
      $("wa-send").classList.remove("hidden");
      if (state.mode === "text") sT.classList.remove("hidden");
      if (state.mode === "pdf") sP.classList.remove("hidden");
      if (state.mode === "photo") sPh.classList.remove("hidden");
    }

    // Send button state
    var canSend = false;
    if (state.mode === "text") {
      canSend = state.lines.some(function (l) { return (l.name || "").trim().length > 0; });
    } else if (state.mode === "pdf" || state.mode === "photo") {
      canSend = !!state.file;
    }
    $("wa-send").disabled = !canSend;

    if (state.mode === "text") renderTextLines();
  }

  function renderTextLines() {
    var box = $("wa-list");
    box.innerHTML = "";
    state.lines.forEach(function (ln, idx) {
      var row = document.createElement("div");
      row.className = "wa-row";

      var name = document.createElement("input");
      name.type = "text";
      name.placeholder = "Nom du produit";
      name.value = ln.name;
      name.addEventListener("input", function () {
        state.lines[idx].name = name.value;
        updatePreview();
        $("wa-send").disabled = !state.lines.some(function (l) { return (l.name || "").trim(); });
      });

      var qty = document.createElement("input");
      qty.type = "number";
      qty.min = "1";
      qty.placeholder = "Qte";
      qty.value = ln.qty;
      qty.addEventListener("input", function () {
        state.lines[idx].qty = parseInt(qty.value) || 1;
        updatePreview();
      });

      var del = document.createElement("button");
      del.type = "button";
      del.className = "wa-row-del";
      del.innerHTML = "&times;";
      del.addEventListener("click", function () {
        if (state.lines.length <= 1) return;
        state.lines.splice(idx, 1);
        renderTextLines();
        updatePreview();
      });

      row.appendChild(name);
      row.appendChild(qty);
      row.appendChild(del);
      box.appendChild(row);
    });
    updatePreview();
  }

  function buildMessage() {
    var lines = [];
    lines.push("\uD83D\uDCCB Demande de produits \u2014 " + state.pharmacy);
    lines.push("");
    lines.push("\uD83C\uDFE5 Structure : " + (state.structure || "................"));
    lines.push("");
    lines.push("Liste :");
    state.lines.forEach(function (l) {
      var n = (l.name || "").trim();
      if (!n) return;
      lines.push("\u2022 " + n + " \u00D7 " + (l.qty || 1));
    });
    lines.push("");
    lines.push("Merci de nous confirmer la disponibilite et le prix.");
    return lines.join("\n");
  }

  function updatePreview() {
    var pv = $("wa-preview-text");
    if (!pv) return;
    var msg = buildMessage();
    pv.textContent = msg;
  }

  function buildSimpleMessage() {
    if (state.mode === "pdf") {
      return "\uD83D\uDCCB Demande de produits \u2014 " + state.pharmacy + "\n\n" +
             "\uD83C\uDFE5 Structure : " + (state.structure || "................") + "\n\n" +
             "\uD83D\uDCC4 Ma liste est en piece jointe (PDF).\n\n" +
             "Merci de nous confirmer la disponibilite et le prix.";
    }
    if (state.mode === "photo") {
      return "\uD83D\uDCCB Demande de produits \u2014 " + state.pharmacy + "\n\n" +
             "\uD83C\uDFE5 Structure : " + (state.structure || "................") + "\n\n" +
             "\uD83D\uDCF7 Ma liste est en piece jointe (photo).\n\n" +
             "Merci de nous confirmer la disponibilite et le prix.";
    }
    return buildMessage();
  }

  function doSend() {
    if (!state.whatsapp) {
      alert("La pharmacie n'a pas encore configure son numero WhatsApp.");
      return;
    }
    var phone = String(state.whatsapp).replace(/\D/g, "");
    if (!phone) { alert("Numero WhatsApp invalide"); return; }

    var msg = buildSimpleMessage();

    // Si fichier joint et partage natif dispo -> tenter le partage
    if (state.file && navigator.canShare && navigator.share) {
      try {
        var shareData = { text: msg, files: [state.file] };
        if (navigator.canShare(shareData)) {
          navigator.share(shareData).then(function () {
            closeWa();
          }).catch(function () {
            // fallback : ouvrir WhatsApp sans piece jointe
            openWaUrl(phone, msg);
          });
          return;
        }
      } catch (e) {}
    }

    openWaUrl(phone, msg);
  }

  function openWaUrl(phone, msg) {
    var url = "https://wa.me/" + phone + "?text=" + encodeURIComponent(msg);
    window.open(url, "_blank");
    closeWa();
  }

  function handleFile(mode, input) {
    var f = input.files && input.files[0];
    if (!f) { state.file = null; }
    else { state.file = f; }
    var nameBox = mode === "pdf" ? $("wa-pdf-name") : $("wa-photo-name");
    if (nameBox) {
      if (f) {
        nameBox.textContent = "\u2713 " + f.name + " (" + Math.round(f.size/1024) + " Ko)";
        nameBox.classList.remove("hidden");
      } else {
        nameBox.classList.add("hidden");
      }
    }
    $("wa-send").disabled = !state.file;
  }

  // ================= Reorder =================

  function reorder() {
    var btn = $("reorder-btn");
    if (!btn) return;
    var orig = btn.querySelector(".pro-action-text strong");
    var oldTxt = orig ? orig.textContent : "";
    btn.disabled = true;
    if (orig) orig.textContent = "Recherche...";

    fetch(API + "/orders/mine", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (list) {
        if (!list || list.length === 0) {
          alert("Aucune commande precedente.");
          btn.disabled = false;
          if (orig) orig.textContent = oldTxt;
          return;
        }
        var ref = list[0].reference;
        return fetch(API + "/orders/" + encodeURIComponent(ref) + "/reorder", {
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

  // ================= Init =================

  document.addEventListener("DOMContentLoaded", function () {
    loadProfile();

    var sp = $("save-profile");
    if (sp) sp.addEventListener("click", saveProfile);

    var gb = $("gps-btn");
    if (gb) gb.addEventListener("click", gps);

    var wo = $("wa-open");
    if (wo) wo.addEventListener("click", openWa);

    var rb = $("reorder-btn");
    if (rb) rb.addEventListener("click", reorder);

    // Modal events
    var closers = document.querySelectorAll("[data-close-wa]");
    Array.prototype.forEach.call(closers, function (b) {
      b.addEventListener("click", closeWa);
    });

    var choices = document.querySelectorAll(".wa-choice");
    Array.prototype.forEach.call(choices, function (c) {
      c.addEventListener("click", function () {
        state.mode = c.getAttribute("data-choice");
        state.step = 2;
        renderWa();
      });
    });

    var back = $("wa-back");
    if (back) back.addEventListener("click", function () {
      state.step = 1;
      state.mode = null;
      state.file = null;
      renderWa();
    });

    var addRow = $("wa-add-row");
    if (addRow) addRow.addEventListener("click", function () {
      state.lines.push({ name: "", qty: 1 });
      renderTextLines();
    });

    var fPdf = $("wa-file-pdf");
    if (fPdf) fPdf.addEventListener("change", function () { handleFile("pdf", fPdf); });

    var fPhoto = $("wa-file-photo");
    if (fPhoto) fPhoto.addEventListener("change", function () { handleFile("photo", fPhoto); });

    var send = $("wa-send");
    if (send) send.addEventListener("click", doSend);
  });
})();
'''
(STATIC / "professional.js").write_text(PRO_JS, encoding="utf-8")
print("[OK] professional.js reecrit")

# ============================================================
# 5. Fix header.js : masquer "Mes livraisons" pour pros
# ============================================================
HJ = STATIC / "header.js"
hjs = HJ.read_text(encoding="utf-8")
# Deja fait dans un patch precedent normalement, mais on s'assure
if "LIVREUR_MOTO" in hjs and "Mes livraisons" in hjs:
    import re
    hjs = re.sub(
        r'if \(user\.role === "LIVREUR_MOTO".*?\}\n',
        "",
        hjs,
        count=1,
        flags=re.DOTALL,
    )
    HJ.write_text(hjs, encoding="utf-8")
    print("[OK] header.js -> Mes livraisons retire")

print()
print("=" * 60)
print("REFONTE PRO + WHATSAPP 3 OPTIONS LIVREE")
print("=" * 60)
print()
print("Changements :")
print("  1. Numero 71039904 configure dans la base")
print("     (whatsapp + payment + phone)")
print("  2. professional.html refondu :")
print("     - Hero + bienvenue personnalise")
print("     - 3 boutons EN HAUT visibles immediatement :")
print("       * Envoyer une liste sur WhatsApp")
print("       * Recommander ma derniere commande")
print("       * Parcourir le catalogue")
print("     - Profil structure en bas (moins prioritaire)")
print("  3. Nouveau flux WhatsApp liste :")
print("     - Choix : Saisir / Importer PDF / Ajouter photo")
print("     - Saisie structuree (produit + quantite)")
print("     - Apercu du message en direct")
print("     - Envoi WhatsApp avec message bien formate")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --host 0.0.0.0 --port 8000")
print("  (SANS --reload pour eviter les blocages SSE)")
print("  Ctrl+Shift+R sur iPhone")