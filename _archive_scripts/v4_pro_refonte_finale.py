"""
v4_pro_refonte_finale.py
- Fix bug SQL pro_features.py (phone -> pharmacy_phone)
- Force numero WhatsApp +22871039904 partout
- Nouvelle page /professionnel (route propre)
- Refonte HTML + JS de l'espace professionnel
- Design sobre medical, mobile-first
"""
from pathlib import Path
import datetime
import shutil
import sqlite3

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
STATIC = BASE / "static"
DB = BASE / "database.db"
PRO_FEAT = BASE / "v3_modules" / "pro_features.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_pro_refonte_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(DB, backup / "database.db")
shutil.copy2(MAIN, backup / "main.py")
if PRO_FEAT.exists():
    shutil.copy2(PRO_FEAT, backup / "pro_features.py")
for f in ("professional.html", "professional.js"):
    p = STATIC / f
    if p.exists():
        shutil.copy2(p, backup / f)
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. Fix SQL dans pro_features.py
# ============================================================
if PRO_FEAT.exists():
    src = PRO_FEAT.read_text(encoding="utf-8")
    changed = False
    if "whatsapp_number, phone FROM pharmacy_settings" in src:
        src = src.replace(
            "whatsapp_number, phone FROM pharmacy_settings",
            "whatsapp_number, pharmacy_phone FROM pharmacy_settings",
        )
        changed = True
    if 'settings["phone"]' in src:
        src = src.replace('settings["phone"]', 'settings["pharmacy_phone"]')
        changed = True
    # Forcer le numero 22871039904 si vide
    if "WHATSAPP_FALLBACK" not in src:
        src = src.replace(
            'whatsapp = (settings["pharmacy_phone"] or "").strip()',
            'whatsapp = (settings["whatsapp_number"] or "").strip()\n'
            '                if not whatsapp:\n'
            '                    whatsapp = (settings["pharmacy_phone"] or "").strip()\n'
            '                if not whatsapp:\n'
            '                    whatsapp = "+22871039904"',
        )
        changed = True
    if changed:
        PRO_FEAT.write_text(src, encoding="utf-8")
        print("[OK] pro_features.py corrige (SQL + fallback numero)")
    else:
        print("[i] pro_features.py deja correct")

# ============================================================
# 2. Force le numero dans la base
# ============================================================
conn = sqlite3.connect(DB)
conn.execute("""
    UPDATE pharmacy_settings SET
      whatsapp_number = '+22871039904',
      pharmacy_phone = COALESCE(NULLIF(pharmacy_phone,''), '+22871039904')
    WHERE id = 1
""")
conn.commit()
conn.close()
print("[OK] Numero WhatsApp force : +22871039904")

# ============================================================
# 3. Route /professionnel dans main.py
# ============================================================
src = MAIN.read_text(encoding="utf-8")
if '"/professionnel"' not in src:
    route = '''

@app.get("/professionnel", include_in_schema=False)
def page_professionnel():
    return FileResponse(STATIC_DIR / "professional.html")

'''
    anchor = "\ninit_db()\n"
    if anchor in src:
        src = src.replace(anchor, route + anchor, 1)
        MAIN.write_text(src, encoding="utf-8")
        print("[OK] main.py -> route /professionnel")
    else:
        print("[!] anchor init_db() introuvable")
else:
    print("[i] route /professionnel deja presente")

# ============================================================
# 4. professional.html - refonte complete
# ============================================================
PRO_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Espace professionnel - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
:root{
  --green:#0f9d76;
  --green-dark:#0a7a5a;
  --green-soft:#e8f7f1;
  --ink:#0f2620;
  --muted:#6c8a80;
  --line:#e4ede9;
  --bg:#f7fbf9;
  --radius:14px;
  --shadow:0 2px 12px rgba(15,38,32,.05);
}
*,*::before,*::after{box-sizing:border-box}
html,body{overflow-x:clip;margin:0;padding:0}
body{
  font-family:-apple-system,"Segoe UI",system-ui,Roboto,Helvetica,Arial,sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.5;
  font-size:15px;-webkit-font-smoothing:antialiased;
}
a{color:inherit;text-decoration:none}
button{font-family:inherit;cursor:pointer}
.hidden{display:none !important}

/* -------- HEADER -------- */
.pro-header{
  background:#fff;border-bottom:1px solid var(--line);
  position:-webkit-sticky;position:sticky;top:0;z-index:100;
}
.pro-header-inner{
  max-width:960px;margin:0 auto;padding:12px 16px;
  display:flex;align-items:center;gap:14px;
}
.pro-brand{display:flex;align-items:center;gap:9px;font-weight:800;font-size:15px}
.pro-brand-mark{
  width:32px;height:32px;border-radius:9px;
  background:var(--green);color:#fff;
  display:flex;align-items:center;justify-content:center;
  font-size:18px;font-weight:800;
}
.pro-nav{display:flex;gap:4px;margin-left:auto}
.pro-nav a{
  padding:8px 12px;border-radius:9px;font-size:13px;
  font-weight:600;color:var(--muted);
}
.pro-nav a:hover{background:var(--green-soft);color:var(--green-dark)}
.pro-nav a.active{background:var(--green-soft);color:var(--green-dark)}
.pro-user{
  display:flex;align-items:center;gap:6px;
  padding:7px 10px;border-radius:9px;border:1px solid var(--line);
  font-size:13px;font-weight:700;cursor:pointer;background:#fff;
  max-width:170px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.pro-user:hover{border-color:var(--green)}
@media(max-width:640px){
  .pro-nav{gap:0}
  .pro-nav a{padding:7px 9px;font-size:12px}
  .pro-user{max-width:110px;font-size:12px}
}

/* -------- MAIN -------- */
.pro-main{max-width:960px;margin:0 auto;padding:24px 16px 60px}

/* -------- HERO -------- */
.pro-hero{margin-bottom:26px}
.pro-hero h1{
  font-size:28px;line-height:1.15;margin:0 0 10px;letter-spacing:-.02em;
}
.pro-hero p{
  font-size:15px;color:var(--muted);margin:0 0 20px;max-width:56ch;
}
.pro-hero-cta{
  display:inline-flex;align-items:center;gap:10px;
  padding:15px 22px;border-radius:13px;border:0;
  background:var(--green);color:#fff;
  font-size:15px;font-weight:800;
  box-shadow:0 6px 20px rgba(15,157,118,.28);
  transition:.15s;
}
.pro-hero-cta:hover{background:var(--green-dark);transform:translateY(-1px)}
.pro-hero-cta-icon{font-size:19px}
@media(max-width:500px){
  .pro-hero h1{font-size:24px}
  .pro-hero-cta{width:100%;justify-content:center;padding:16px}
}

/* -------- CARTES GENERALES -------- */
.pro-card{
  background:#fff;border:1px solid var(--line);border-radius:var(--radius);
  padding:20px;margin-bottom:16px;
}
.pro-card-title{
  font-size:12px;font-weight:800;text-transform:uppercase;
  letter-spacing:.06em;color:var(--muted);
  margin:0 0 14px;
}

/* -------- ETABLISSEMENT -------- */
.pro-etab-row{
  display:grid;grid-template-columns:auto 1fr;gap:6px 18px;
  font-size:14px;
}
.pro-etab-row dt{color:var(--muted);font-weight:600}
.pro-etab-row dd{margin:0;font-weight:700;color:var(--ink)}
.pro-etab-edit{
  display:inline-flex;align-items:center;gap:6px;margin-top:14px;
  font-size:13px;font-weight:700;color:var(--green-dark);
  background:none;border:0;padding:0;
}
.pro-etab-edit:hover{text-decoration:underline}

/* -------- CHOIX METHODE -------- */
.pro-choices{margin-top:6px}
.pro-choice{
  display:flex;align-items:center;gap:16px;
  padding:18px;border:1px solid var(--line);border-radius:var(--radius);
  background:#fff;width:100%;text-align:left;
  margin-bottom:10px;transition:.15s;cursor:pointer;
}
.pro-choice:hover{border-color:var(--green);box-shadow:0 4px 16px rgba(15,157,118,.08)}
.pro-choice-icon{
  width:48px;height:48px;border-radius:12px;
  background:var(--green-soft);color:var(--green-dark);
  display:flex;align-items:center;justify-content:center;
  font-size:22px;flex-shrink:0;
}
.pro-choice-body{flex:1;min-width:0}
.pro-choice-title{font-size:15px;font-weight:800;color:var(--ink);margin:0 0 3px}
.pro-choice-desc{font-size:13px;color:var(--muted);margin:0;line-height:1.4}
.pro-choice-arrow{color:var(--muted);font-size:18px;flex-shrink:0}

/* -------- PANNEAU (SAISIE / PDF / PHOTO) -------- */
.pro-panel{
  background:#fff;border:1px solid var(--line);border-radius:var(--radius);
  padding:20px;margin-top:4px;
}
.pro-panel-head{
  display:flex;align-items:center;justify-content:space-between;
  margin-bottom:16px;gap:10px;
}
.pro-panel-title{font-size:16px;font-weight:800;margin:0}
.pro-panel-back{
  background:none;border:0;color:var(--muted);font-size:13px;
  font-weight:700;padding:6px 10px;border-radius:8px;
}
.pro-panel-back:hover{background:var(--bg);color:var(--ink)}

/* Saisie structuree */
.pro-line{display:grid;grid-template-columns:1fr 110px 36px;gap:8px;margin-bottom:8px}
.pro-line input{
  padding:11px 12px;border:1px solid var(--line);border-radius:10px;
  font-family:inherit;font-size:14px;background:#fff;outline:none;
}
.pro-line input:focus{border-color:var(--green)}
.pro-line-del{
  background:#fdecec;border:0;border-radius:10px;
  color:#b23c3c;font-size:16px;line-height:1;
}
.pro-line-del:hover{background:#f8dcdc}
.pro-add-line{
  margin-top:4px;background:var(--green-soft);color:var(--green-dark);
  border:1px dashed var(--green);padding:11px;border-radius:10px;
  width:100%;font-weight:700;font-size:13px;
}

/* Upload zone */
.pro-upload{
  border:2px dashed var(--line);border-radius:12px;
  padding:28px 16px;text-align:center;background:#fafdfb;
  cursor:pointer;transition:.15s;
}
.pro-upload:hover{border-color:var(--green);background:var(--green-soft)}
.pro-upload input{display:none}
.pro-upload-icon{font-size:32px;margin-bottom:8px}
.pro-upload-title{font-size:14px;font-weight:700;color:var(--ink);margin:0 0 4px}
.pro-upload-hint{font-size:12px;color:var(--muted);margin:0}
.pro-file-info{
  margin-top:12px;padding:10px 12px;background:var(--green-soft);
  border:1px solid #c7e9dc;border-radius:10px;
  font-size:13px;color:var(--green-dark);font-weight:700;
  display:flex;align-items:center;gap:8px;
}
.pro-file-info .icon{font-size:16px}

/* Apercu photo */
.pro-photo-preview{
  margin-top:12px;border-radius:12px;overflow:hidden;
  border:1px solid var(--line);max-height:220px;
  display:flex;align-items:center;justify-content:center;background:#000;
}
.pro-photo-preview img{max-width:100%;max-height:220px;display:block}

/* Apercu message */
.pro-msg-preview{
  background:var(--bg);border:1px solid var(--line);border-radius:10px;
  padding:14px;margin-top:14px;font-size:13px;color:var(--ink);
  white-space:pre-wrap;font-family:-apple-system,"Segoe UI",system-ui,sans-serif;
  line-height:1.55;max-height:220px;overflow-y:auto;
}
.pro-msg-label{
  font-size:11px;font-weight:800;color:var(--muted);
  text-transform:uppercase;letter-spacing:.06em;margin:16px 0 6px;
}

/* Bouton principal d'envoi */
.pro-send{
  width:100%;padding:15px;border:0;border-radius:12px;
  background:#25d366;color:#fff;font-size:15px;font-weight:800;
  margin-top:16px;transition:.15s;
  display:flex;align-items:center;justify-content:center;gap:8px;
}
.pro-send:hover{background:#1da851}
.pro-send:disabled{background:#c9e5d4;cursor:not-allowed}

/* Info contextuelle */
.pro-note{
  margin-top:12px;padding:11px 13px;border-radius:10px;
  background:#fff4e0;border:1px solid #f2d9b3;
  font-size:12px;color:#8a5a00;line-height:1.5;
}
.pro-note strong{color:#6b4400}

/* Messages d'erreur */
.pro-error{
  margin-top:12px;padding:11px 13px;border-radius:10px;
  background:#fdecec;border:1px solid #f6d2d2;
  font-size:13px;color:#b23c3c;font-weight:600;
}

/* -------- DEMANDES RECENTES -------- */
.pro-history-item{
  display:flex;align-items:center;gap:12px;
  padding:12px 0;border-bottom:1px solid var(--line);
}
.pro-history-item:last-child{border-bottom:0}
.pro-history-icon{
  width:36px;height:36px;border-radius:10px;
  background:var(--green-soft);color:var(--green-dark);
  display:flex;align-items:center;justify-content:center;
  font-size:16px;flex-shrink:0;
}
.pro-history-body{flex:1;min-width:0}
.pro-history-title{font-size:14px;font-weight:700;color:var(--ink);margin:0 0 2px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pro-history-meta{font-size:12px;color:var(--muted)}
.pro-history-badge{
  font-size:10px;font-weight:800;padding:3px 9px;border-radius:999px;
  background:var(--green-soft);color:var(--green-dark);
  text-transform:uppercase;letter-spacing:.05em;
}
.pro-empty{
  text-align:center;padding:22px 10px;color:var(--muted);font-size:14px;
}

/* -------- TOAST -------- */
.pro-toast{
  position:fixed;left:50%;bottom:24px;transform:translateX(-50%);
  background:var(--ink);color:#fff;padding:12px 18px;border-radius:12px;
  font-size:13px;font-weight:600;z-index:1000;box-shadow:0 10px 30px rgba(0,0,0,.2);
  max-width:calc(100vw - 32px);text-align:center;
}
.pro-toast.ok{background:var(--green-dark)}

/* -------- MODAL PROFIL -------- */
.pro-modal{position:fixed;inset:0;z-index:900;display:flex;align-items:flex-end;justify-content:center}
.pro-modal.hidden{display:none}
.pro-modal-bg{position:absolute;inset:0;background:rgba(15,38,32,.5)}
.pro-modal-panel{
  position:relative;background:#fff;width:100%;max-width:560px;
  max-height:92vh;border-radius:18px 18px 0 0;
  display:flex;flex-direction:column;overflow:hidden;
  animation:slideUp .22s ease;
}
@keyframes slideUp{from{transform:translateY(30px);opacity:.5}to{transform:translateY(0);opacity:1}}
.pro-modal-head{
  padding:16px 20px;border-bottom:1px solid var(--line);
  display:flex;align-items:center;justify-content:space-between;
}
.pro-modal-head h3{margin:0;font-size:16px}
.pro-modal-close{background:none;border:0;font-size:24px;color:var(--muted);cursor:pointer;padding:0 4px}
.pro-modal-body{padding:18px 20px;overflow-y:auto;flex:1}
.pro-modal-field{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.pro-modal-field label{font-size:13px;font-weight:700}
.pro-modal-field input,.pro-modal-field select{
  padding:12px 14px;border:1px solid var(--line);border-radius:10px;
  font-family:inherit;font-size:15px;outline:none;background:#fff;
}
.pro-modal-field input:focus,.pro-modal-field select:focus{border-color:var(--green)}
.pro-modal-foot{
  padding:14px 20px;border-top:1px solid var(--line);background:var(--bg);
  display:flex;gap:10px;
}
.pro-modal-foot button{flex:1;padding:13px;border:0;border-radius:11px;font-weight:800;font-size:14px}
.pro-btn-ghost{background:#fff;border:1px solid var(--line);color:var(--ink)}
.pro-btn-primary{background:var(--green);color:#fff}
.pro-btn-primary:hover{background:var(--green-dark)}
</style>
</head>
<body>

<header class="pro-header">
  <div class="pro-header-inner">
    <a class="pro-brand" href="/professionnel">
      <span class="pro-brand-mark">+</span>
      Elokinab Health
    </a>
    <nav class="pro-nav">
      <a href="/professionnel" class="active">Accueil</a>
      <a href="#demandes">Mes demandes</a>
      <a href="#" id="nav-etab">Mon établissement</a>
    </nav>
    <button class="pro-user" id="user-btn">
      <span id="user-name">Mon compte</span>
      <span style="color:var(--muted)">▾</span>
    </button>
  </div>
</header>

<main class="pro-main">

  <!-- HERO -->
  <section class="pro-hero">
    <h1>Commandez vos produits de santé simplement.</h1>
    <p>Envoyez votre liste de produits à Elokinab Health. Nous vous répondons sur WhatsApp avec les informations disponibles.</p>
    <button class="pro-hero-cta" id="hero-cta">
      <span class="pro-hero-cta-icon">&#128203;</span>
      Envoyer une liste sur WhatsApp
    </button>
  </section>

  <!-- ETABLISSEMENT -->
  <section class="pro-card" id="etab-card">
    <h2 class="pro-card-title">Votre établissement</h2>
    <dl class="pro-etab-row">
      <dt>Nom</dt><dd id="etab-name">—</dd>
      <dt>Type</dt><dd id="etab-type">—</dd>
      <dt>Téléphone</dt><dd id="etab-phone">—</dd>
      <dt>Adresse</dt><dd id="etab-address">—</dd>
    </dl>
    <button class="pro-etab-edit" id="etab-edit">Modifier mes informations →</button>
  </section>

  <!-- SECTION METHODES -->
  <section class="pro-card" id="methodes">
    <h2 class="pro-card-title">Envoyer une demande</h2>

    <!-- Etape 1 : choix -->
    <div id="step-choice">
      <p style="margin:0 0 14px;font-size:14px;color:var(--muted)">
        Choisissez l'option qui vous convient. Votre demande sera ensuite envoyée à Elokinab Health sur WhatsApp.
      </p>

      <button class="pro-choice" data-mode="text">
        <span class="pro-choice-icon">&#9997;&#65039;</span>
        <span class="pro-choice-body">
          <span class="pro-choice-title">Saisir ma liste</span>
          <span class="pro-choice-desc">Ajoutez directement les produits et les quantités.</span>
        </span>
        <span class="pro-choice-arrow">›</span>
      </button>

      <button class="pro-choice" data-mode="pdf">
        <span class="pro-choice-icon">&#128196;</span>
        <span class="pro-choice-body">
          <span class="pro-choice-title">Importer un PDF</span>
          <span class="pro-choice-desc">Envoyez une liste enregistrée au format PDF.</span>
        </span>
        <span class="pro-choice-arrow">›</span>
      </button>

      <button class="pro-choice" data-mode="photo">
        <span class="pro-choice-icon">&#128247;</span>
        <span class="pro-choice-body">
          <span class="pro-choice-title">Ajouter une photo</span>
          <span class="pro-choice-desc">Photographiez votre liste ou sélectionnez une image.</span>
        </span>
        <span class="pro-choice-arrow">›</span>
      </button>
    </div>

    <!-- Etape 2A : saisie -->
    <div id="step-text" class="pro-panel hidden">
      <div class="pro-panel-head">
        <h3 class="pro-panel-title">Saisir ma liste</h3>
        <button class="pro-panel-back" data-back>← Retour</button>
      </div>

      <div id="lines"></div>
      <button class="pro-add-line" id="add-line">+ Ajouter un produit</button>

      <div class="pro-msg-label">Aperçu du message</div>
      <div class="pro-msg-preview" id="msg-preview-text"></div>

      <button class="pro-send" id="send-text" disabled>
        <span>&#128172;</span> Envoyer sur WhatsApp
      </button>
      <div id="err-text" class="pro-error hidden"></div>
    </div>

    <!-- Etape 2B : PDF -->
    <div id="step-pdf" class="pro-panel hidden">
      <div class="pro-panel-head">
        <h3 class="pro-panel-title">Importer un PDF</h3>
        <button class="pro-panel-back" data-back>← Retour</button>
      </div>

      <label class="pro-upload" for="file-pdf">
        <input type="file" id="file-pdf" accept="application/pdf,.pdf">
        <div class="pro-upload-icon">&#128196;</div>
        <p class="pro-upload-title">Glissez votre PDF ici</p>
        <p class="pro-upload-hint">ou cliquez pour choisir un fichier · PDF uniquement</p>
      </label>
      <div id="file-pdf-info" class="pro-file-info hidden"></div>

      <div class="pro-msg-label">Aperçu du message</div>
      <div class="pro-msg-preview" id="msg-preview-pdf"></div>

      <div class="pro-note">
        <strong>Important :</strong> WhatsApp va s'ouvrir. Joignez ensuite votre PDF dans la conversation <em>avant</em> d'envoyer le message.
      </div>

      <button class="pro-send" id="send-pdf" disabled>
        <span>&#128172;</span> Envoyer sur WhatsApp
      </button>
      <div id="err-pdf" class="pro-error hidden"></div>
    </div>

    <!-- Etape 2C : Photo -->
    <div id="step-photo" class="pro-panel hidden">
      <div class="pro-panel-head">
        <h3 class="pro-panel-title">Ajouter une photo</h3>
        <button class="pro-panel-back" data-back>← Retour</button>
      </div>

      <label class="pro-upload" for="file-photo">
        <input type="file" id="file-photo" accept="image/*" capture="environment">
        <div class="pro-upload-icon">&#128247;</div>
        <p class="pro-upload-title">Photographiez ou sélectionnez une photo</p>
        <p class="pro-upload-hint">JPG, PNG, WEBP · cliquez pour ouvrir l'appareil photo ou vos fichiers</p>
      </label>
      <div id="file-photo-info" class="pro-file-info hidden"></div>
      <div id="photo-preview" class="pro-photo-preview hidden"></div>

      <div class="pro-msg-label">Aperçu du message</div>
      <div class="pro-msg-preview" id="msg-preview-photo"></div>

      <div class="pro-note">
        <strong>Important :</strong> WhatsApp va s'ouvrir. Joignez ensuite votre photo dans la conversation <em>avant</em> d'envoyer le message.
      </div>

      <button class="pro-send" id="send-photo" disabled>
        <span>&#128172;</span> Envoyer sur WhatsApp
      </button>
      <div id="err-photo" class="pro-error hidden"></div>
    </div>

  </section>

  <!-- DEMANDES RECENTES -->
  <section class="pro-card" id="demandes">
    <h2 class="pro-card-title">Mes demandes récentes</h2>
    <div id="history"></div>
  </section>

</main>

<!-- MODAL PROFIL -->
<div id="modal-profil" class="pro-modal hidden">
  <div class="pro-modal-bg" data-close-modal></div>
  <div class="pro-modal-panel">
    <div class="pro-modal-head">
      <h3>Mon établissement</h3>
      <button class="pro-modal-close" data-close-modal>&times;</button>
    </div>
    <div class="pro-modal-body">
      <div class="pro-modal-field">
        <label for="m-structure-name">Nom de l'établissement</label>
        <input type="text" id="m-structure-name" required>
      </div>
      <div class="pro-modal-field">
        <label for="m-structure-type">Type</label>
        <select id="m-structure-type">
          <option value="CLINIQUE">Clinique</option>
          <option value="HOPITAL">Hôpital</option>
          <option value="CABINET_MEDICAL">Cabinet médical</option>
          <option value="LABORATOIRE">Laboratoire</option>
          <option value="CENTRE_SANTE">Centre de santé</option>
          <option value="AUTRE">Autre</option>
        </select>
      </div>
      <div class="pro-modal-field">
        <label for="m-manager-name">Responsable</label>
        <input type="text" id="m-manager-name" required>
      </div>
      <div class="pro-modal-field">
        <label for="m-phone">Téléphone</label>
        <input type="tel" id="m-phone" required>
      </div>
      <div class="pro-modal-field">
        <label for="m-email">Email de contact</label>
        <input type="email" id="m-email">
      </div>
      <div class="pro-modal-field">
        <label for="m-address">Adresse</label>
        <input type="text" id="m-address">
      </div>
      <div class="pro-modal-field">
        <label>Position GPS (facultatif)</label>
        <div style="display:flex;gap:8px">
          <input type="number" id="m-lat" step="0.00001" placeholder="Latitude" style="flex:1">
          <input type="number" id="m-lon" step="0.00001" placeholder="Longitude" style="flex:1">
        </div>
        <button type="button" class="pro-add-line" id="m-gps" style="margin-top:8px">📍 Utiliser ma position</button>
      </div>
      <div id="modal-msg" class="pro-error hidden"></div>
    </div>
    <div class="pro-modal-foot">
      <button class="pro-btn-ghost" data-close-modal>Annuler</button>
      <button class="pro-btn-primary" id="modal-save">Enregistrer</button>
    </div>
  </div>
</div>

<script src="/static/professional.js"></script>
</body>
</html>
'''
(STATIC / "professional.html").write_text(PRO_HTML, encoding="utf-8")
print("[OK] professional.html refondu")

# ============================================================
# 5. professional.js - nouvelle logique
# ============================================================
PRO_JS = r'''/* Elokinab Health - Espace professionnel */
(function () {
  var API = "/api";
  var WHATSAPP_FALLBACK = "+22871039904";
  var WHATSAPP_PHARMACY_NAME = "Elokinab Health";

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  var state = {
    mode: null,
    lines: [{ name: "", qty: "" }],
    pdf: null,
    photo: null,
    user: null,
    profile: null,
    whatsapp: WHATSAPP_FALLBACK,
    history: []
  };

  /* ---------- Utilitaires ---------- */

  function toast(msg, ok) {
    var t = document.createElement("div");
    t.className = "pro-toast" + (ok ? " ok" : "");
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () {
      t.style.transition = "opacity .3s";
      t.style.opacity = "0";
      setTimeout(function () { t.remove(); }, 320);
    }, 2400);
  }

  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }

  function showErr(id, msg) {
    var el = document.getElementById(id);
    if (!el) return;
    el.textContent = msg;
    el.classList.remove("hidden");
  }
  function hideErr(id) {
    var el = document.getElementById(id);
    if (el) el.classList.add("hidden");
  }

  function fmtDate(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    var mois = ["janv.", "févr.", "mars", "avr.", "mai", "juin",
                "juil.", "août", "sept.", "oct.", "nov.", "déc."];
    return d.getDate() + " " + mois[d.getMonth()] + " " + d.getFullYear();
  }

  /* ---------- Chargement profil + WhatsApp ---------- */

  function loadUser() {
    return fetch(API + "/auth/me", { credentials: "same-origin" })
      .then(function (r) {
        if (r.status === 401) { window.location.href = "/connexion?next=/professionnel"; return null; }
        return r.ok ? r.json() : null;
      })
      .then(function (u) {
        state.user = u;
        if (!u) return;
        var el = document.getElementById("user-name");
        if (el) el.textContent = (u.full_name || u.email || "Mon compte").slice(0, 20);
        // Si pas professionnel -> rediriger vers /
        if (u.role !== "PROFESSIONNEL") {
          toast("Accès réservé aux professionnels.");
          setTimeout(function () { window.location.href = "/"; }, 900);
        }
      });
  }

  function loadProfile() {
    return fetch(API + "/professionals/me", { credentials: "same-origin" })
      .then(function (r) {
        if (r.status === 404) return null;
        return r.ok ? r.json() : null;
      })
      .then(function (p) {
        state.profile = p;
        renderProfile();
      });
  }

  function renderProfile() {
    var p = state.profile || {};
    var mapType = {
      CLINIQUE: "Clinique",
      HOPITAL: "Hôpital",
      CABINET_MEDICAL: "Cabinet médical",
      LABORATOIRE: "Laboratoire",
      CENTRE_SANTE: "Centre de santé",
      AUTRE: "Autre"
    };
    $("#etab-name").textContent = p.structure_name || "À compléter";
    $("#etab-type").textContent = mapType[p.structure_type] || "—";
    $("#etab-phone").textContent = p.phone || "—";
    $("#etab-address").textContent = p.address || "—";
  }

  function loadWaInfo() {
    return fetch(API + "/pro/whatsapp-info", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (d && d.whatsapp_number) state.whatsapp = d.whatsapp_number;
        if (!state.whatsapp) state.whatsapp = WHATSAPP_FALLBACK;
      })
      .catch(function () { state.whatsapp = WHATSAPP_FALLBACK; });
  }

  /* ---------- Construction du message WhatsApp ---------- */

  function structureName() {
    return (state.profile && state.profile.structure_name) || "Établissement";
  }

  function buildTextMessage() {
    var valid = state.lines.filter(function (l) { return (l.name || "").trim(); });
    var out = [];
    out.push("\uD83D\uDCCB *Demande de produits — " + WHATSAPP_PHARMACY_NAME + "*");
    out.push("");
    out.push("\uD83C\uDFE5 Établissement : " + structureName());
    out.push("");
    out.push("Bonjour " + WHATSAPP_PHARMACY_NAME + ",");
    out.push("");
    out.push("Nous souhaitons obtenir les produits suivants :");
    out.push("");
    valid.forEach(function (l) {
      out.push("\u2022 " + l.name.trim() + (l.qty ? " — " + String(l.qty).trim() : ""));
    });
    out.push("");
    out.push("Merci de nous communiquer la disponibilité et les informations correspondantes.");
    out.push("");
    out.push("Cordialement,");
    out.push(structureName());
    return out.join("\n");
  }

  function buildFileMessage(kind) {
    var intro = kind === "pdf"
      ? "Veuillez trouver ci-joint notre liste de produits."
      : "Veuillez trouver ci-joint une photo de notre liste de produits.";
    var out = [];
    out.push("\uD83D\uDCCB *Demande de produits — " + WHATSAPP_PHARMACY_NAME + "*");
    out.push("");
    out.push("\uD83C\uDFE5 Établissement : " + structureName());
    out.push("");
    out.push("Bonjour " + WHATSAPP_PHARMACY_NAME + ",");
    out.push("");
    out.push(intro);
    out.push("");
    out.push("Merci de nous communiquer la disponibilité et les informations correspondantes.");
    out.push("");
    out.push("Cordialement,");
    out.push(structureName());
    return out.join("\n");
  }

  function waPhone() {
    var raw = String(state.whatsapp || WHATSAPP_FALLBACK);
    var digits = raw.replace(/\D/g, "");
    if (!digits) digits = "22871039904";
    // Toujours préfixe Togo 228
    if (digits.indexOf("228") !== 0) digits = "228" + digits;
    return digits;
  }

  function openWhatsapp(message) {
    var phone = waPhone();
    var url = "https://wa.me/" + phone + "?text=" + encodeURIComponent(message);
    window.open(url, "_blank");
  }

  /* ---------- Etapes UI ---------- */

  function showStep(name) {
    ["step-choice", "step-text", "step-pdf", "step-photo"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.classList.add("hidden");
    });
    var target = document.getElementById("step-" + name);
    if (target) target.classList.remove("hidden");
  }

  function resetAll() {
    state.mode = null;
    state.lines = [{ name: "", qty: "" }];
    state.pdf = null;
    state.photo = null;
    var fPdf = document.getElementById("file-pdf");
    if (fPdf) fPdf.value = "";
    var fPhoto = document.getElementById("file-photo");
    if (fPhoto) fPhoto.value = "";
    document.getElementById("file-pdf-info").classList.add("hidden");
    document.getElementById("file-photo-info").classList.add("hidden");
    document.getElementById("photo-preview").classList.add("hidden");
    document.getElementById("photo-preview").innerHTML = "";
    hideErr("err-text"); hideErr("err-pdf"); hideErr("err-photo");
    renderLines();
  }

  /* ---------- Saisie structuree ---------- */

  function renderLines() {
    var box = document.getElementById("lines");
    box.innerHTML = "";
    state.lines.forEach(function (ln, idx) {
      var row = document.createElement("div");
      row.className = "pro-line";

      var name = document.createElement("input");
      name.type = "text";
      name.placeholder = "Nom du produit";
      name.value = ln.name;
      name.setAttribute("aria-label", "Produit " + (idx + 1));
      name.addEventListener("input", function () {
        state.lines[idx].name = name.value;
        updatePreviewText();
      });

      var qty = document.createElement("input");
      qty.type = "text";
      qty.placeholder = "Qté";
      qty.value = ln.qty;
      qty.setAttribute("aria-label", "Quantité " + (idx + 1));
      qty.addEventListener("input", function () {
        state.lines[idx].qty = qty.value;
        updatePreviewText();
      });

      var del = document.createElement("button");
      del.type = "button";
      del.className = "pro-line-del";
      del.innerHTML = "&times;";
      del.setAttribute("aria-label", "Supprimer la ligne " + (idx + 1));
      del.addEventListener("click", function () {
        if (state.lines.length <= 1) { state.lines[0] = { name: "", qty: "" }; renderLines(); return; }
        state.lines.splice(idx, 1);
        renderLines();
      });

      row.appendChild(name); row.appendChild(qty); row.appendChild(del);
      box.appendChild(row);
    });
    updatePreviewText();
  }

  function updatePreviewText() {
    var pv = document.getElementById("msg-preview-text");
    if (!pv) return;
    pv.textContent = buildTextMessage();
    var valid = state.lines.filter(function (l) { return (l.name || "").trim(); });
    document.getElementById("send-text").disabled = valid.length === 0;
  }

  /* ---------- PDF ---------- */

  function onPdfChange(input) {
    hideErr("err-pdf");
    var f = input.files && input.files[0];
    if (!f) {
      state.pdf = null;
      document.getElementById("file-pdf-info").classList.add("hidden");
      document.getElementById("send-pdf").disabled = true;
      document.getElementById("msg-preview-pdf").textContent = "";
      return;
    }
    if (!/\.pdf$/i.test(f.name) && f.type !== "application/pdf") {
      showErr("err-pdf", "Ce fichier n'est pas compatible. Veuillez sélectionner un PDF.");
      state.pdf = null;
      document.getElementById("send-pdf").disabled = true;
      return;
    }
    var maxMb = 15;
    if (f.size > maxMb * 1024 * 1024) {
      showErr("err-pdf", "Fichier trop volumineux (max " + maxMb + " Mo).");
      state.pdf = null;
      document.getElementById("send-pdf").disabled = true;
      return;
    }
    state.pdf = f;
    var info = document.getElementById("file-pdf-info");
    info.innerHTML = '<span class="icon">📄</span>' + escapeHtml(f.name) +
                     ' · ' + Math.round(f.size / 1024) + ' Ko';
    info.classList.remove("hidden");
    document.getElementById("msg-preview-pdf").textContent = buildFileMessage("pdf");
    document.getElementById("send-pdf").disabled = false;
  }

  /* ---------- Photo ---------- */

  function onPhotoChange(input) {
    hideErr("err-photo");
    var f = input.files && input.files[0];
    if (!f) {
      state.photo = null;
      document.getElementById("file-photo-info").classList.add("hidden");
      document.getElementById("photo-preview").classList.add("hidden");
      document.getElementById("send-photo").disabled = true;
      return;
    }
    if (!/^image\//.test(f.type) && !/\.(jpe?g|png|webp)$/i.test(f.name)) {
      showErr("err-photo", "Cette image n'est pas compatible. Veuillez choisir une photo JPG, PNG ou WEBP.");
      state.photo = null;
      document.getElementById("send-photo").disabled = true;
      return;
    }
    var maxMb = 15;
    if (f.size > maxMb * 1024 * 1024) {
      showErr("err-photo", "Fichier trop volumineux (max " + maxMb + " Mo).");
      state.photo = null;
      document.getElementById("send-photo").disabled = true;
      return;
    }
    state.photo = f;
    var info = document.getElementById("file-photo-info");
    info.innerHTML = '<span class="icon">📷</span>' + escapeHtml(f.name) +
                     ' · ' + Math.round(f.size / 1024) + ' Ko';
    info.classList.remove("hidden");

    // Apercu
    var pv = document.getElementById("photo-preview");
    var url = URL.createObjectURL(f);
    pv.innerHTML = "";
    var img = document.createElement("img");
    img.src = url;
    img.alt = "Apercu de la photo";
    img.onload = function () { URL.revokeObjectURL(url); };
    pv.appendChild(img);
    pv.classList.remove("hidden");

    document.getElementById("msg-preview-photo").textContent = buildFileMessage("photo");
    document.getElementById("send-photo").disabled = false;
  }

  /* ---------- Envoi ---------- */

  function sendText() {
    hideErr("err-text");
    var valid = state.lines.filter(function (l) { return (l.name || "").trim(); });
    if (valid.length === 0) {
      showErr("err-text", "Ajoutez au moins un produit.");
      return;
    }
    var msg = buildTextMessage();
    openWhatsapp(msg);
    toast("WhatsApp ouvert.", true);
    saveHistory({ type: "text", label: "Liste de produits", items: valid.length });
  }

  function sendPdf() {
    hideErr("err-pdf");
    if (!state.pdf) {
      showErr("err-pdf", "Sélectionnez un fichier PDF.");
      return;
    }
    var msg = buildFileMessage("pdf");
    openWhatsapp(msg);
    toast("WhatsApp ouvert. Joignez le PDF avant d'envoyer.", true);
    saveHistory({ type: "pdf", label: "PDF — " + state.pdf.name });
  }

  function sendPhoto() {
    hideErr("err-photo");
    if (!state.photo) {
      showErr("err-photo", "Sélectionnez une photo.");
      return;
    }
    var msg = buildFileMessage("photo");
    openWhatsapp(msg);
    toast("WhatsApp ouvert. Joignez la photo avant d'envoyer.", true);
    saveHistory({ type: "photo", label: "Photo — " + state.photo.name });
  }

  /* ---------- Historique local (navigateur) ---------- */

  function historyKey() {
    var uid = state.user && state.user.id ? state.user.id : "anon";
    return "eh_pro_history_" + uid;
  }

  function loadHistory() {
    try {
      var raw = localStorage.getItem(historyKey());
      state.history = raw ? JSON.parse(raw) : [];
    } catch (e) { state.history = []; }
    if (!Array.isArray(state.history)) state.history = [];
    renderHistory();
  }

  function saveHistory(entry) {
    var now = new Date().toISOString();
    state.history.unshift({ at: now, type: entry.type, label: entry.label });
    if (state.history.length > 20) state.history = state.history.slice(0, 20);
    try { localStorage.setItem(historyKey(), JSON.stringify(state.history)); } catch (e) {}
    renderHistory();
  }

  function renderHistory() {
    var box = document.getElementById("history");
    if (!state.history || state.history.length === 0) {
      box.innerHTML =
        '<div class="pro-empty">Vous n\\'avez encore envoyé aucune demande.' +
        '<div style="margin-top:12px">' +
        '<button class="pro-add-line" style="max-width:260px;margin:auto" id="first-cta">' +
        'Envoyer ma première liste</button></div></div>';
      var fc = document.getElementById("first-cta");
      if (fc) fc.addEventListener("click", function () { document.getElementById("hero-cta").click(); });
      return;
    }
    box.innerHTML = "";
    state.history.forEach(function (h) {
      var row = document.createElement("div");
      row.className = "pro-history-item";
      var iconChar = h.type === "pdf" ? "📄" : (h.type === "photo" ? "📷" : "📋");
      row.innerHTML =
        '<div class="pro-history-icon">' + iconChar + '</div>' +
        '<div class="pro-history-body">' +
          '<div class="pro-history-title">' + escapeHtml(h.label || "Demande") + '</div>' +
          '<div class="pro-history-meta">' + fmtDate(h.at) + ' · Envoyée sur WhatsApp</div>' +
        '</div>' +
        '<span class="pro-history-badge">Envoyée</span>';
      box.appendChild(row);
    });
  }

  /* ---------- Modal profil ---------- */

  function openModal() {
    var p = state.profile || {};
    $("#m-structure-name").value = p.structure_name || "";
    $("#m-structure-type").value = p.structure_type || "CLINIQUE";
    $("#m-manager-name").value = p.manager_name || "";
    $("#m-phone").value = p.phone || "";
    $("#m-email").value = p.email || "";
    $("#m-address").value = p.address || "";
    $("#m-lat").value = p.latitude || "";
    $("#m-lon").value = p.longitude || "";
    var errBox = document.getElementById("modal-msg");
    if (errBox) errBox.classList.add("hidden");
    document.getElementById("modal-profil").classList.remove("hidden");
    document.body.style.overflow = "hidden";
  }
  function closeModal() {
    document.getElementById("modal-profil").classList.add("hidden");
    document.body.style.overflow = "";
  }

  function saveProfile() {
    var body = {
      structure_name: $("#m-structure-name").value.trim(),
      structure_type: $("#m-structure-type").value,
      manager_name: $("#m-manager-name").value.trim(),
      phone: $("#m-phone").value.trim(),
      email: $("#m-email").value.trim(),
      address: $("#m-address").value.trim(),
      notes: ""
    };
    if (!body.structure_name || !body.manager_name || !body.phone) {
      var errBox = document.getElementById("modal-msg");
      errBox.textContent = "Nom de l'établissement, responsable et téléphone sont obligatoires.";
      errBox.classList.remove("hidden");
      return;
    }
    var lat = parseFloat($("#m-lat").value);
    var lon = parseFloat($("#m-lon").value);
    if (!isNaN(lat) && !isNaN(lon)) { body.latitude = lat; body.longitude = lon; }

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
    }).then(function (p) {
      state.profile = p;
      renderProfile();
      closeModal();
      toast("Informations enregistrées.", true);
    }).catch(function (e) {
      var errBox = document.getElementById("modal-msg");
      errBox.textContent = e.message || "Erreur";
      errBox.classList.remove("hidden");
    });
  }

  function modalGps() {
    if (!navigator.geolocation) { toast("GPS indisponible"); return; }
    var btn = document.getElementById("m-gps");
    btn.disabled = true; btn.textContent = "Localisation...";
    navigator.geolocation.getCurrentPosition(function (pos) {
      $("#m-lat").value = pos.coords.latitude.toFixed(5);
      $("#m-lon").value = pos.coords.longitude.toFixed(5);
      btn.disabled = false; btn.textContent = "📍 Utiliser ma position";
    }, function () {
      btn.disabled = false; btn.textContent = "📍 Utiliser ma position";
      toast("Position introuvable");
    }, { enableHighAccuracy: true, timeout: 15000 });
  }

  /* ---------- Init ---------- */

  function init() {
    // Hero CTA
    var hero = document.getElementById("hero-cta");
    if (hero) hero.addEventListener("click", function () {
      resetAll();
      showStep("choice");
      document.getElementById("methodes").scrollIntoView({ behavior: "smooth", block: "start" });
    });

    // Choix methode
    $$(".pro-choice").forEach(function (b) {
      b.addEventListener("click", function () {
        state.mode = b.getAttribute("data-mode");
        if (state.mode === "text") { renderLines(); showStep("text"); }
        if (state.mode === "pdf") { showStep("pdf"); }
        if (state.mode === "photo") { showStep("photo"); }
      });
    });

    // Retour
    $$("[data-back]").forEach(function (b) {
      b.addEventListener("click", function () {
        resetAll();
        showStep("choice");
      });
    });

    // Saisie
    var add = document.getElementById("add-line");
    if (add) add.addEventListener("click", function () {
      state.lines.push({ name: "", qty: "" });
      renderLines();
    });

    // Fichiers
    var fPdf = document.getElementById("file-pdf");
    if (fPdf) fPdf.addEventListener("change", function () { onPdfChange(fPdf); });

    var fPhoto = document.getElementById("file-photo");
    if (fPhoto) fPhoto.addEventListener("change", function () { onPhotoChange(fPhoto); });

    // Envoi
    var sT = document.getElementById("send-text");
    if (sT) sT.addEventListener("click", sendText);
    var sP = document.getElementById("send-pdf");
    if (sP) sP.addEventListener("click", sendPdf);
    var sPh = document.getElementById("send-photo");
    if (sPh) sPh.addEventListener("click", sendPhoto);

    // Modal profil
    var etabEdit = document.getElementById("etab-edit");
    if (etabEdit) etabEdit.addEventListener("click", openModal);
    var navEtab = document.getElementById("nav-etab");
    if (navEtab) navEtab.addEventListener("click", function (e) { e.preventDefault(); openModal(); });
    var userBtn = document.getElementById("user-btn");
    if (userBtn) userBtn.addEventListener("click", openModal);

    $$("[data-close-modal]").forEach(function (b) {
      b.addEventListener("click", closeModal);
    });
    var mSave = document.getElementById("modal-save");
    if (mSave) mSave.addEventListener("click", saveProfile);
    var mGps = document.getElementById("m-gps");
    if (mGps) mGps.addEventListener("click", modalGps);

    // Deconnexion (menu contextuel sur le user button, clic long)
    if (userBtn) {
      userBtn.addEventListener("contextmenu", function (e) {
        e.preventDefault();
        if (confirm("Se déconnecter ?")) {
          fetch(API + "/auth/logout", { method: "POST", credentials: "same-origin" })
            .then(function () { window.location.href = "/"; });
        }
      });
    }

    // Chargement initial
    loadUser().then(function () {
      return loadProfile();
    }).then(function () {
      return loadWaInfo();
    }).then(function () {
      loadHistory();
    });

    // Reset l'etat au demarrage
    renderLines();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
'''
(STATIC / "professional.js").write_text(PRO_JS, encoding="utf-8")
print("[OK] professional.js refondu")

print()
print("=" * 60)
print("REFONTE ESPACE PROFESSIONNEL LIVREE")
print("=" * 60)
print()
print("Fichiers touches :")
print("  v3_modules/pro_features.py  (fix SQL phone -> pharmacy_phone)")
print("  main.py                     (route /professionnel)")
print("  static/professional.html    (refonte complete)")
print("  static/professional.js      (nouvelle logique)")
print("  database.db                 (numero +22871039904 force)")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print()
print("Puis sur iPhone : /professionnel")