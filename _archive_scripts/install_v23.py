from pathlib import Path
import re
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
MAIN = BASE / "main.py"
PH_HTML = STATIC / "pharmacien.html"
PH_JS = STATIC / "pharmacien.js"
PH_CSS = STATIC / "pharmacien.css"
INDEX = STATIC / "index.html"
APPJS = STATIC / "app.js"

for f in (MAIN, PH_HTML, PH_JS, PH_CSS, INDEX, APPJS):
    shutil.copy(f, f.with_suffix(f.suffix + ".bak"))
print("[OK] sauvegardes .bak creees")

# =================================================================
# 1) main.py
# =================================================================
src = MAIN.read_text(encoding="utf-8")

# 1a) Table pharmacy_settings + ligne initiale + colonne orders.delivery_fee
if "CREATE TABLE IF NOT EXISTS pharmacy_settings" not in src:
    anchor = '    cur.execute("SELECT COUNT(*) AS total FROM products")'
    block = '''    cur.execute(
        "CREATE TABLE IF NOT EXISTS pharmacy_settings ("
        " id INTEGER PRIMARY KEY,"
        " delivery_fee_default REAL NOT NULL DEFAULT 0"
        ")"
    )
    cur.execute(
        "INSERT OR IGNORE INTO pharmacy_settings (id, delivery_fee_default) VALUES (1, 500)"
    )
    orders_cols = {row[1] for row in cur.execute("PRAGMA table_info(orders)").fetchall()}
    if "delivery_fee" not in orders_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN delivery_fee REAL NOT NULL DEFAULT 0")

'''
    if anchor in src:
        src = src.replace(anchor, block + anchor, 1)
        print("[OK] main.py -> pharmacy_settings + orders.delivery_fee")
    else:
        print("[!] anchor products-count introuvable")

# 1b) POST /api/orders : calculer delivery_fee
old_has_gps = '''    has_gps = latitude is not None and longitude is not None
    if delivery_mode == "livraison" and not address.strip() and not has_gps:'''
new_has_gps = '''    has_gps = latitude is not None and longitude is not None
    if delivery_mode == "livraison" and not address.strip() and not has_gps:'''
# (unchanged)

# Recuperer la ligne de calcul du INSERT
old_insert = '''    cur = conn.execute(
        "INSERT INTO orders (reference, customer_name, phone, product_id, product_name,"
        " quantity, delivery_mode, address, prescription_file, status, created_at,"
        " latitude, longitude, location_accuracy)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'en_attente', ?, ?, ?, ?)",
        (reference, name, phone_clean, product["id"], product["name"], quantity,
         delivery_mode, address.strip(), saved_file, created_at,
         latitude, longitude, location_accuracy),
    )'''
new_insert = '''    if delivery_mode == "livraison":
        settings_row = conn.execute(
            "SELECT delivery_fee_default FROM pharmacy_settings WHERE id = 1"
        ).fetchone()
        delivery_fee = float(settings_row["delivery_fee_default"]) if settings_row else 0.0
    else:
        delivery_fee = 0.0

    cur = conn.execute(
        "INSERT INTO orders (reference, customer_name, phone, product_id, product_name,"
        " quantity, delivery_mode, address, prescription_file, status, created_at,"
        " latitude, longitude, location_accuracy, delivery_fee)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'en_attente', ?, ?, ?, ?, ?)",
        (reference, name, phone_clean, product["id"], product["name"], quantity,
         delivery_mode, address.strip(), saved_file, created_at,
         latitude, longitude, location_accuracy, delivery_fee),
    )'''
if old_insert in src and "delivery_fee)" not in src.split("INSERT INTO orders")[1][:400]:
    src = src.replace(old_insert, new_insert, 1)
    print("[OK] main.py -> INSERT delivery_fee")
elif "delivery_fee" in src and "INSERT INTO orders" in src:
    print("[i] main.py -> INSERT deja patche ?")

# 1c) Reponse JSON de create_order : ajouter subtotal + delivery_fee + corriger total
old_ret = '''        "prescription_file": saved_file,
        "price": product["price"],
        "total": round(product["price"] * quantity, 2),
        "latitude": latitude,
        "longitude": longitude,
        "location_accuracy": location_accuracy,
    }'''
new_ret = '''        "prescription_file": saved_file,
        "price": product["price"],
        "subtotal": round(product["price"] * quantity, 2),
        "delivery_fee": delivery_fee,
        "total": round(product["price"] * quantity + delivery_fee, 2),
        "latitude": latitude,
        "longitude": longitude,
        "location_accuracy": location_accuracy,
    }'''
if old_ret in src:
    src = src.replace(old_ret, new_ret, 1)
    print("[OK] main.py -> reponse JSON subtotal + delivery_fee")
elif '"subtotal":' in src:
    print("[i] main.py -> reponse deja patchee")
else:
    print("[!] dict de reponse introuvable")

# 1d) Routes /api/settings
settings_block = '''
# ============================================================
# V2.3 - Parametres pharmacie
# ============================================================

class SettingsUpdate(BaseModel):
    delivery_fee_default: float


@app.get("/api/settings")
def get_settings():
    conn = get_db()
    row = conn.execute("SELECT * FROM pharmacy_settings WHERE id = 1").fetchone()
    conn.close()
    if row is None:
        return {"delivery_fee_default": 0}
    return row_to_dict(row)


@app.patch("/api/settings")
def update_settings(payload: SettingsUpdate):
    value = float(payload.delivery_fee_default)
    if value < 0:
        raise HTTPException(status_code=400, detail="Le montant doit etre positif")
    if value > 1000000:
        raise HTTPException(status_code=400, detail="Montant trop eleve")
    conn = get_db()
    conn.execute(
        "INSERT INTO pharmacy_settings (id, delivery_fee_default) VALUES (1, ?)"
        " ON CONFLICT(id) DO UPDATE SET delivery_fee_default = excluded.delivery_fee_default",
        (value,),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM pharmacy_settings WHERE id = 1").fetchone()
    conn.close()
    return row_to_dict(row)


'''
if "/api/settings" not in src:
    pattern = re.compile(r'\ninit_db\(\)\n')
    m = pattern.search(src)
    if m:
        src = src[:m.start()] + settings_block + "init_db()\n" + src[m.end():]
        print("[OK] main.py -> routes /api/settings")
    else:
        print("[!] init_db() niveau module introuvable")

MAIN.write_text(src, encoding="utf-8")

# =================================================================
# 2) index.html - affichage des frais de livraison (patient)
# =================================================================
html = INDEX.read_text(encoding="utf-8")
if 'id="delivery-fee-info"' not in html:
    # Inserer juste apres <div class="form-row hidden" id="address-row"> puis <label...>GPS
    # On cible la premiere balise apres address-row (le label adresse ou le bloc geo)
    anchor = '<div class="form-row hidden" id="address-row">'
    insert = anchor + '''
          <div id="delivery-fee-info" class="delivery-fee-info"></div>'''
    if anchor in html:
        html = html.replace(anchor, insert, 1)
        INDEX.write_text(html, encoding="utf-8")
        print("[OK] index.html -> delivery-fee-info")
    else:
        print("[!] anchor address-row introuvable")
else:
    print("[i] index.html -> delivery-fee-info deja present")

# =================================================================
# 3) app.js - charger settings + afficher les frais
# =================================================================
js = APPJS.read_text(encoding="utf-8")

if "pharmacySettings" not in js:
    settings_js = r'''
var pharmacySettings = { delivery_fee_default: 0 };

function loadSettings() {
  return fetch(API + "/settings").then(function (r) {
    if (!r.ok) throw new Error("settings");
    return r.json();
  }).then(function (s) {
    pharmacySettings = s || { delivery_fee_default: 0 };
    return pharmacySettings;
  }).catch(function () {
    pharmacySettings = { delivery_fee_default: 0 };
    return pharmacySettings;
  });
}

function updateDeliveryFeeDisplay() {
  var box = document.getElementById("delivery-fee-info");
  if (!box) return;
  var checked = document.querySelector("input[name=delivery_mode]:checked");
  var isDelivery = checked && checked.value === "livraison";
  if (!isDelivery) {
    box.classList.add("hidden");
    box.innerHTML = "";
    return;
  }
  var fee = Math.round(Number(pharmacySettings.delivery_fee_default) || 0);
  box.innerHTML = "&#128666; Frais de livraison : <strong>" +
                  fee.toLocaleString("fr-FR") + " FCFA</strong>" +
                  "<br><span class='muted small'>Ajoutes au total, definis par la pharmacie.</span>";
  box.classList.remove("hidden");
}

'''
    anchor = "function init() {"
    if anchor in js:
        js = js.replace(anchor, settings_js + anchor, 1)
        print("[OK] app.js -> pharmacySettings + updateDeliveryFeeDisplay")
    else:
        print("[!] anchor init() introuvable")

# Brancher dans init()
if "initDeliveryFeeDisplay();" not in js:
    # Ajouter apres initGeolocation();
    anchor = "  initGeolocation();"
    if anchor in js:
        js = js.replace(anchor, anchor + "\n  initDeliveryFeeDisplay();", 1)
        print("[OK] app.js -> initDeliveryFeeDisplay branche")

# Definit initDeliveryFeeDisplay
if "function initDeliveryFeeDisplay" not in js:
    init_fn = '''
function initDeliveryFeeDisplay() {
  var radios = document.querySelectorAll("input[name=delivery_mode]");
  Array.prototype.forEach.call(radios, function (r) {
    r.addEventListener("change", updateDeliveryFeeDisplay);
  });
  loadSettings().then(updateDeliveryFeeDisplay);
}

'''
    anchor = "function init() {"
    if anchor in js:
        js = js.replace(anchor, init_fn + anchor, 1)
        print("[OK] app.js -> initDeliveryFeeDisplay definie")

APPJS.write_text(js, encoding="utf-8")

# =================================================================
# 4) pharmacien.html - sections admin + modal ajout livreur
# =================================================================
html = PH_HTML.read_text(encoding="utf-8")

if 'id="drivers-section"' not in html:
    sections = '''  <section class="admin-section" id="drivers-section">
    <h2 class="admin-title">&#128666; Livreurs</h2>
    <div id="drivers-admin-list" class="drivers-admin-list"></div>
    <button type="button" class="btn btn-primary" id="add-driver-btn">
      + Ajouter un livreur
    </button>
  </section>

  <section class="admin-section" id="settings-section">
    <h2 class="admin-title">&#9881;&#65039; Parametres de livraison</h2>
    <form id="settings-form" class="settings-form">
      <label for="delivery-fee-input">Frais de livraison par defaut</label>
      <div class="settings-row">
        <input type="number" id="delivery-fee-input" min="0" step="50" required>
        <span class="muted">FCFA</span>
        <button type="submit" class="btn btn-primary">Enregistrer</button>
      </div>
      <span id="settings-status" class="muted small"></span>
    </form>
  </section>

  <div id="add-driver-modal" class="modal hidden">
    <div class="modal-backdrop" data-close-add-driver></div>
    <div class="modal-content">
      <header class="modal-head">
        <h2>&#128666; Ajouter un livreur</h2>
        <button type="button" class="modal-close" data-close-add-driver aria-label="Fermer">&times;</button>
      </header>
      <form id="add-driver-form" class="add-driver-form">
        <div class="form-row">
          <label for="new-driver-name">Nom du livreur</label>
          <input type="text" id="new-driver-name" required placeholder="Ex : Kossi">
        </div>
        <div class="form-row">
          <label for="new-driver-phone">Telephone WhatsApp</label>
          <input type="tel" id="new-driver-phone" required placeholder="Ex : 90 12 34 56">
          <small class="muted">Numero local (le code pays sera ajoute automatiquement).</small>
        </div>
        <div id="add-driver-error" class="alert hidden"></div>
        <footer class="modal-foot">
          <button type="button" class="btn btn-ghost" data-close-add-driver>Annuler</button>
          <button type="submit" class="btn btn-primary">Ajouter</button>
        </footer>
      </form>
    </div>
  </div>

'''
    anchor = '<script src="/static/pharmacien.js"></script>'
    if anchor in html:
        html = html.replace(anchor, sections + anchor, 1)
        PH_HTML.write_text(html, encoding="utf-8")
        print("[OK] pharmacien.html -> sections admin + modal ajout")
    else:
        print("[!] anchor script introuvable")
else:
    print("[i] pharmacien.html -> sections deja presentes")

# =================================================================
# 5) pharmacien.css - styles admin
# =================================================================
css = PH_CSS.read_text(encoding="utf-8")

if ".admin-section" not in css:
    admin_css = '''
/* --- Sections admin dashboard V2.3 --- */
.admin-section{
  margin-top:36px;padding-top:24px;
  border-top:1px solid var(--line);
}
.admin-title{
  margin:0 0 16px;font-size:18px;
}
.drivers-admin-list{
  display:flex;flex-direction:column;gap:8px;
  margin-bottom:14px;
}
.driver-admin-row{
  display:flex;align-items:center;gap:12px;flex-wrap:wrap;
  padding:12px 14px;background:var(--white);
  border:1px solid var(--line);border-radius:12px;
}
.driver-admin-info{flex:1;min-width:180px}
.driver-admin-name{font-weight:700;font-size:14px}
.driver-admin-phone{font-size:12px;color:var(--muted);font-family:Consolas,monospace}
.driver-admin-status{
  font-size:11px;font-weight:800;padding:4px 10px;border-radius:999px;
  text-transform:uppercase;letter-spacing:.05em;
}
.status-active{background:var(--green-soft);color:var(--green-dark)}
.status-inactive{background:#e6e9ec;color:#4b5563}

.settings-form{
  background:var(--white);border:1px solid var(--line);
  border-radius:var(--radius);padding:18px;
  display:flex;flex-direction:column;gap:10px;max-width:520px;
}
.settings-row{
  display:flex;align-items:center;gap:10px;flex-wrap:wrap;
}
.settings-row input[type=number]{
  width:140px;padding:10px 12px;border:1px solid var(--line);
  border-radius:10px;font-size:15px;font-family:inherit;
}
.settings-row input:focus{outline:none;border-color:var(--green)}

.add-driver-form{padding:16px 20px;display:flex;flex-direction:column;gap:14px}
.add-driver-form .form-row{display:flex;flex-direction:column;gap:6px}
.add-driver-form input{padding:11px 13px;border:1px solid var(--line);border-radius:10px;font-family:inherit;font-size:14px}
.add-driver-form input:focus{outline:none;border-color:var(--green)}

/* --- Bloc frais de livraison (patient) --- */
.delivery-fee-info{
  background:var(--green-soft);color:var(--green-dark);
  border:1px solid #c7e9dc;border-radius:10px;
  padding:10px 14px;font-size:14px;line-height:1.5;
}
'''
    css = css + admin_css
    PH_CSS.write_text(css, encoding="utf-8")
    print("[OK] pharmacien.css -> styles admin")
else:
    print("[i] pharmacien.css -> styles deja presents")

# =================================================================
# 6) pharmacien.js - breakdown totaux + WhatsApp + admin
# =================================================================
js = PH_JS.read_text(encoding="utf-8")

# 6a) Ajouter sous-total / livraison / total dans orderCard
old_mode = '  row("Mode", o.delivery_mode === "livraison" ? "Livraison" : "Retrait");'
new_mode = '''  row("Mode", o.delivery_mode === "livraison" ? "Livraison" : "Retrait");
  var _qty = Number(o.quantity) || 1;
  var _price = Number(o.price) || 0;
  var _subtotal = (o.subtotal !== undefined && o.subtotal !== null)
    ? Number(o.subtotal) : (_price * _qty);
  var _fee = Number(o.delivery_fee || 0);
  var _total = (o.total !== undefined && o.total !== null)
    ? Number(o.total) : (_subtotal + _fee);
  row("Sous-total", Math.round(_subtotal).toLocaleString("fr-FR") + " FCFA");
  row("Livraison", Math.round(_fee).toLocaleString("fr-FR") + " FCFA");
  row("Total", Math.round(_total).toLocaleString("fr-FR") + " FCFA");'''
if old_mode in js and "row(\"Sous-total\"" not in js:
    js = js.replace(old_mode, new_mode, 1)
    print("[OK] pharmacien.js -> breakdown totaux")
elif "row(\"Sous-total\"" in js:
    print("[i] pharmacien.js -> breakdown deja present")
else:
    print("[!] anchor row Mode introuvable")

# 6b) Remplacer buildWhatsappMessage
old_wa_start = js.find("function buildWhatsappMessage(o) {")
if old_wa_start != -1:
    old_wa_end = js.find("\n}\n", old_wa_start)
    if old_wa_end == -1:
        old_wa_end = js.find("\n}\r\n", old_wa_start)
    if old_wa_end != -1:
        old_wa_end += 2  # inclure le \n}
        new_wa = r'''function buildWhatsappMessage(o) {
  var lines = [];
  lines.push("\uD83D\uDCE6 LIVRAISON \u2014 " + o.reference);
  lines.push("");
  lines.push("\uD83D\uDC64 Client : " + (o.customer_name || ""));
  lines.push("\uD83D\uDCDE T\u00E9l\u00E9phone client : " + (o.phone || ""));
  lines.push("\uD83D\uDC8A Produit : " + (o.product_name || "") + " \u00D7 " + (o.quantity || 1));

  var qty = Number(o.quantity) || 1;
  var price = Number(o.price) || 0;
  var subtotal = (o.subtotal !== undefined && o.subtotal !== null)
    ? Number(o.subtotal) : (price * qty);
  var fee = Number(o.delivery_fee) || 0;
  var total = (o.total !== undefined && o.total !== null)
    ? Number(o.total) : (subtotal + fee);

  lines.push("\uD83D\uDCB5 Sous-total : " + Math.round(subtotal).toLocaleString("fr-FR") + " FCFA");
  lines.push("\uD83D\uDE9A Livraison : " + Math.round(fee).toLocaleString("fr-FR") + " FCFA");
  lines.push("\uD83D\uDCB0 TOTAL : " + Math.round(total).toLocaleString("fr-FR") + " FCFA");
  lines.push("");

  var addr = String(o.address || "").trim();
  lines.push("\uD83D\uDCCD Adresse :");
  lines.push(addr ? addr : "Non renseign\u00E9e");
  lines.push("");

  lines.push("\uD83D\uDDFA\uFE0F Localisation GPS :");
  if (o.latitude !== null && o.latitude !== undefined &&
      o.longitude !== null && o.longitude !== undefined) {
    lines.push("https://www.google.com/maps?q=" + o.latitude + "," + o.longitude);
  } else {
    lines.push("Non fournie");
  }
  return lines.join("\n");
}
'''
        js = js[:old_wa_start] + new_wa + js[old_wa_end:]
        print("[OK] pharmacien.js -> buildWhatsappMessage mis a jour")
else:
    print("[!] buildWhatsappMessage introuvable")

# 6c) Ajouter fonctions admin
admin_js = r'''
// ====== V2.3 Admin livreurs + settings ======

function loadSettingsDashboard() {
  var input = document.getElementById("delivery-fee-input");
  if (!input) return;
  fetch(API + "/settings").then(function (r) {
    if (!r.ok) throw new Error("settings");
    return r.json();
  }).then(function (s) {
    input.value = String(Math.round(Number(s.delivery_fee_default) || 0));
  }).catch(function () {});
}

function submitSettings(ev) {
  ev.preventDefault();
  var input = document.getElementById("delivery-fee-input");
  var status = document.getElementById("settings-status");
  var value = Number(input.value);
  if (isNaN(value) || value < 0) {
    if (status) status.textContent = "Montant invalide.";
    return;
  }
  fetch(API + "/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ delivery_fee_default: value })
  }).then(function (r) {
    return r.json().then(function (body) {
      if (!r.ok) throw new Error(body.detail || "Erreur");
      return body;
    });
  }).then(function (s) {
    input.value = String(Math.round(Number(s.delivery_fee_default) || 0));
    if (status) {
      status.textContent = "\u2713 Param\u00E8tres enregistr\u00E9s";
      setTimeout(function () { status.textContent = ""; }, 3000);
    }
  }).catch(function (err) {
    if (status) status.textContent = err.message || "Erreur";
  });
}

function loadDriversAdmin() {
  var list = document.getElementById("drivers-admin-list");
  if (!list) return;
  list.innerHTML = '<div class="muted small" style="padding:8px">Chargement...</div>';
  fetch(API + "/drivers?include_inactive=1").then(function (r) {
    if (!r.ok) throw new Error("drivers");
    return r.json();
  }).then(function (drivers) {
    list.innerHTML = "";
    if (!drivers || drivers.length === 0) {
      list.appendChild(el("div", "muted small", "Aucun livreur enregistr\u00E9."));
      return;
    }
    drivers.forEach(function (d) { list.appendChild(driverAdminRow(d)); });
  }).catch(function () {
    list.innerHTML = '<div class="muted small" style="padding:8px">Erreur de chargement.</div>';
  });
}

function driverAdminRow(d) {
  var row = el("div", "driver-admin-row");
  var info = el("div", "driver-admin-info");
  info.appendChild(el("div", "driver-admin-name", d.name));
  info.appendChild(el("div", "driver-admin-phone", String(d.phone || "").replace(/\D/g, "")));
  var badge = el("span", "driver-admin-status " + (d.is_active ? "status-active" : "status-inactive"),
                 d.is_active ? "\uD83D\uDFE2 Actif" : "\uD83D\uDD34 Inactif");
  var btn = el("button", "btn " + (d.is_active ? "btn-ghost" : "btn-primary"),
               d.is_active ? "Desactiver" : "Activer");
  btn.type = "button";
  btn.addEventListener("click", function () {
    btn.disabled = true;
    toggleDriver(d.id, !d.is_active).then(function () {
      loadDriversAdmin();
    }).catch(function () {
      btn.disabled = false;
      alert("Erreur");
    });
  });
  row.appendChild(info);
  row.appendChild(badge);
  row.appendChild(btn);
  return row;
}

function toggleDriver(id, newActive) {
  return fetch(API + "/drivers/" + id, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_active: !!newActive })
  }).then(function (r) {
    if (!r.ok) throw new Error("toggle");
    return r.json();
  });
}

function openAddDriverModal() {
  var modal = document.getElementById("add-driver-modal");
  if (!modal) return;
  modal.classList.remove("hidden");
  var form = document.getElementById("add-driver-form");
  if (form) form.reset();
  var err = document.getElementById("add-driver-error");
  if (err) { err.classList.add("hidden"); err.textContent = ""; }
  setTimeout(function () {
    var n = document.getElementById("new-driver-name");
    if (n) n.focus();
  }, 60);
}

function closeAddDriverModal() {
  var modal = document.getElementById("add-driver-modal");
  if (modal) modal.classList.add("hidden");
}

function submitNewDriver(ev) {
  ev.preventDefault();
  var nameEl = document.getElementById("new-driver-name");
  var phoneEl = document.getElementById("new-driver-phone");
  var errEl = document.getElementById("add-driver-error");
  var name = (nameEl.value || "").trim();
  var phone = (phoneEl.value || "").replace(/\D/g, "");
  if (!name) {
    errEl.textContent = "Le nom est obligatoire.";
    errEl.classList.remove("hidden");
    return;
  }
  if (phone.length < 6) {
    errEl.textContent = "Numero de telephone invalide.";
    errEl.classList.remove("hidden");
    return;
  }
  fetch(API + "/drivers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: name, phone: phone })
  }).then(function (r) {
    return r.json().then(function (body) {
      if (!r.ok) throw new Error(body.detail || "Erreur");
      return body;
    });
  }).then(function () {
    closeAddDriverModal();
    loadDriversAdmin();
  }).catch(function (err) {
    errEl.textContent = err.message || "Erreur";
    errEl.classList.remove("hidden");
  });
}

function initAdmin() {
  var addBtn = document.getElementById("add-driver-btn");
  if (addBtn) addBtn.addEventListener("click", openAddDriverModal);

  var settingsForm = document.getElementById("settings-form");
  if (settingsForm) settingsForm.addEventListener("submit", submitSettings);

  var addForm = document.getElementById("add-driver-form");
  if (addForm) addForm.addEventListener("submit", submitNewDriver);

  var modal = document.getElementById("add-driver-modal");
  if (modal) {
    var closeEls = modal.querySelectorAll("[data-close-add-driver]");
    Array.prototype.forEach.call(closeEls, function (b) {
      b.addEventListener("click", closeAddDriverModal);
    });
  }

  loadDriversAdmin();
  loadSettingsDashboard();
}

document.addEventListener("DOMContentLoaded", initAdmin);
'''

if "function loadDriversAdmin" not in js:
    # Ajouter avant "document.addEventListener(\"DOMContentLoaded\", init);" si present
    anchor = 'document.addEventListener("DOMContentLoaded", init);'
    if anchor in js:
        js = js.replace(anchor, admin_js + "\n" + anchor, 1)
    else:
        js = js + "\n" + admin_js
    print("[OK] pharmacien.js -> fonctions admin ajoutees")
else:
    print("[i] pharmacien.js -> fonctions admin deja presentes")

PH_JS.write_text(js, encoding="utf-8")

print()
print("=======================================================")
print("Patch V2.3 (frais de livraison + admin livreurs) installe.")
print()
print("Redemarre le serveur :")
print("  taskkill /F /IM python.exe")
print("  python main.py")
print()
print("Puis navigateur : Ctrl+Shift+R sur /pharmacien et sur /")
print("=======================================================")