from pathlib import Path
import re
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
MAIN = BASE / "main.py"
PH_HTML = STATIC / "pharmacien.html"
PH_JS = STATIC / "pharmacien.js"
PH_CSS = STATIC / "pharmacien.css"

for f in (MAIN, PH_HTML, PH_JS, PH_CSS):
    shutil.copy(f, f.with_suffix(f.suffix + ".bak"))
print("[OK] sauvegardes .bak creees")

# =============================================================
# 1) main.py - table drivers + demo + routes API
# =============================================================
src = MAIN.read_text(encoding="utf-8")

# 1a) Table drivers + demo drivers (dans init_db, avant le bloc products)
if "CREATE TABLE IF NOT EXISTS drivers" not in src:
    anchor = '    cur.execute("SELECT COUNT(*) AS total FROM products")'
    drivers_block = '''    cur.execute(
        "CREATE TABLE IF NOT EXISTS drivers ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " name TEXT NOT NULL,"
        " phone TEXT NOT NULL,"
        " is_active INTEGER NOT NULL DEFAULT 1,"
        " created_at TEXT NOT NULL"
        ")"
    )
    cur.execute("SELECT COUNT(*) AS total FROM drivers")
    if cur.fetchone()["total"] == 0:
        now_drivers = datetime.now().isoformat(timespec="seconds")
        demo_drivers = [
            ("Kossi (DEMO)", "22890000001"),
            ("Mensah (DEMO)", "22890000002"),
            ("Komlan (DEMO)", "22890000003"),
        ]
        cur.executemany(
            "INSERT INTO drivers (name, phone, is_active, created_at) VALUES (?, ?, 1, ?)",
            [(n, p, now_drivers) for n, p in demo_drivers],
        )

'''
    if anchor in src:
        src = src.replace(anchor, drivers_block + anchor, 1)
        print("[OK] main.py -> table drivers + demo livresurs")
    else:
        print("[!] anchor products-count introuvable")

# 1b) Routes /api/drivers (juste avant le init_db() final)
routes_block = '''
# ============================================================
# V2.2 - Livreurs
# ============================================================

class DriverCreate(BaseModel):
    name: str
    phone: str


class DriverUpdate(BaseModel):
    is_active: bool


@app.get("/api/drivers")
def list_drivers(include_inactive: int = 0):
    conn = get_db()
    if include_inactive:
        rows = conn.execute(
            "SELECT * FROM drivers ORDER BY is_active DESC, name COLLATE NOCASE"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM drivers WHERE is_active = 1 ORDER BY name COLLATE NOCASE"
        ).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@app.post("/api/drivers")
def create_driver(payload: DriverCreate):
    name = payload.name.strip()
    phone = payload.phone.strip()
    if not name or not phone:
        raise HTTPException(status_code=400, detail="Nom et telephone obligatoires")
    created_at = datetime.now().isoformat(timespec="seconds")
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO drivers (name, phone, is_active, created_at) VALUES (?, ?, 1, ?)",
        (name, phone, created_at),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM drivers WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return row_to_dict(row)


@app.patch("/api/drivers/{driver_id}")
def update_driver(driver_id: int, payload: DriverUpdate):
    conn = get_db()
    row = conn.execute("SELECT * FROM drivers WHERE id = ?", (driver_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Livreur introuvable")
    conn.execute(
        "UPDATE drivers SET is_active = ? WHERE id = ?",
        (1 if payload.is_active else 0, driver_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM drivers WHERE id = ?", (driver_id,)).fetchone()
    conn.close()
    return row_to_dict(row)


'''

if "/api/drivers" not in src:
    # Inserer avant le init_db() de niveau module
    pattern = re.compile(r'\ninit_db\(\)\n')
    m = pattern.search(src)
    if m:
        src = src[:m.start()] + routes_block + "init_db()\n" + src[m.end():]
        print("[OK] main.py -> routes /api/drivers")
    else:
        print("[!] init_db() niveau module introuvable")
else:
    print("[i] main.py -> routes /api/drivers deja presentes")

MAIN.write_text(src, encoding="utf-8")

# =============================================================
# 2) pharmacien.html - modal de selection livreur
# =============================================================
html = PH_HTML.read_text(encoding="utf-8")

if 'id="driver-modal"' not in html:
    modal_html = '''<div id="driver-modal" class="modal hidden">
  <div class="modal-backdrop" data-close-modal></div>
  <div class="modal-content">
    <header class="modal-head">
      <h2>&#128666; Choisir un livreur</h2>
      <button type="button" class="modal-close" data-close-modal aria-label="Fermer">&times;</button>
    </header>
    <div id="driver-list" class="driver-list"></div>
    <div id="driver-selected" class="driver-selected hidden"></div>
    <footer class="modal-foot">
      <button type="button" class="btn btn-ghost" data-close-modal>Annuler</button>
      <button type="button" class="btn btn-primary hidden" id="driver-send-btn">&#128242; Envoyer sur WhatsApp</button>
    </footer>
  </div>
</div>

'''
    anchor = '<script src="/static/pharmacien.js"></script>'
    if anchor in html:
        html = html.replace(anchor, modal_html + anchor, 1)
        print("[OK] pharmacien.html -> modal livreur")
    else:
        print("[!] anchor script introuvable dans pharmacien.html")
else:
    print("[i] pharmacien.html -> modal deja present")

PH_HTML.write_text(html, encoding="utf-8")

# =============================================================
# 3) pharmacien.css - styles modal + bouton livreur
# =============================================================
css = PH_CSS.read_text(encoding="utf-8")

if ".modal-backdrop" not in css:
    modal_css = '''
/* --- Bouton livreur dans les cartes --- */
.order-driver{
  display:flex;align-items:center;gap:8px;flex-wrap:wrap;
  padding-top:8px;
}
.order-driver .btn{padding:8px 14px;font-size:13px}

/* --- Modal de selection livreur --- */
.modal{
  position:fixed;inset:0;z-index:100;
  display:flex;align-items:center;justify-content:center;
  padding:16px;
}
.modal-backdrop{
  position:absolute;inset:0;
  background:rgba(15,38,32,.45);
  backdrop-filter:blur(2px);
}
.modal-content{
  position:relative;
  background:var(--white);border:1px solid var(--line);
  border-radius:var(--radius);box-shadow:0 20px 60px rgba(15,38,32,.25);
  width:100%;max-width:460px;max-height:calc(100vh - 32px);
  display:flex;flex-direction:column;overflow:hidden;
}
.modal-head{
  display:flex;align-items:center;justify-content:space-between;
  gap:12px;padding:16px 20px;border-bottom:1px solid var(--line);
}
.modal-head h2{margin:0;font-size:17px}
.modal-close{
  background:none;border:0;font-size:24px;line-height:1;
  color:var(--muted);cursor:pointer;padding:2px 6px;border-radius:6px;
}
.modal-close:hover{background:var(--bg);color:var(--ink)}
.driver-list{
  padding:8px 12px;overflow-y:auto;flex:1;
  display:flex;flex-direction:column;gap:6px;
}
.driver-row{
  display:flex;align-items:center;gap:12px;
  padding:12px 12px;border:1px solid var(--line);border-radius:12px;
  cursor:pointer;background:var(--white);transition:.12s;
}
.driver-row:hover{border-color:var(--green);background:var(--green-soft)}
.driver-row input[type=radio]{accent-color:var(--green);margin:0}
.driver-label{display:flex;flex-direction:column;gap:2px;flex:1;cursor:pointer}
.driver-name{font-weight:700;font-size:14px}
.driver-phone{font-size:12px;color:var(--muted);font-family:Consolas,monospace}
.driver-selected{
  margin:0 12px 8px;padding:12px 14px;
  background:var(--green-soft);border:1px solid #c7e9dc;border-radius:12px;
}
.driver-selected-name{font-weight:700;color:var(--green-dark);margin-top:4px;font-size:14px}
.modal-foot{
  display:flex;gap:10px;justify-content:flex-end;
  padding:14px 20px;border-top:1px solid var(--line);
  background:var(--bg);
}
.modal-foot .btn{padding:10px 18px;font-size:14px}

@media (max-width:600px){
  .modal-content{max-width:100%}
  .modal-foot{flex-direction:column-reverse}
  .modal-foot .btn{width:100%}
}
'''
    css = css + modal_css
    PH_CSS.write_text(css, encoding="utf-8")
    print("[OK] pharmacien.css -> styles modal + bouton")
else:
    print("[i] pharmacien.css -> styles deja presents")

# =============================================================
# 4) pharmacien.js - logique livreurs + WhatsApp
# =============================================================
js = PH_JS.read_text(encoding="utf-8")

# 4a) Bouton "Envoyer au livreur" dans la carte (avant var actions = NEXT_ACTIONS)
btn_block = '''  if (o.delivery_mode === "livraison") {
    var driverBox = el("div", "order-driver");
    var driverBtn = el("button", "btn btn-primary", "\\uD83D\\uDE9A Envoyer au livreur");
    driverBtn.type = "button";
    driverBtn.addEventListener("click", function () { openDriverModal(o); });
    driverBox.appendChild(driverBtn);
    card.appendChild(driverBox);
  }

'''
if "Envoyer au livreur" not in js:
    anchor = "  var actions = NEXT_ACTIONS[o.status] || [];"
    if anchor in js:
        js = js.replace(anchor, btn_block + anchor, 1)
        print("[OK] pharmacien.js -> bouton Envoyer au livreur")
    else:
        print("[!] anchor NEXT_ACTIONS introuvable")

# 4b) Fonctions modal + WhatsApp
driver_js = r'''var driversCache = null;

function formatPhoneDisplay(raw) {
  return String(raw || "").replace(/\D/g, "");
}

function normalizePhone(raw) {
  var DEFAULT_COUNTRY_CODE = "228";
  if (!raw) return "";
  var s = String(raw).trim();
  var hasPlus = s.charAt(0) === "+";
  s = s.replace(/\D/g, "");
  if (!s) return "";
  if (hasPlus && s.indexOf(DEFAULT_COUNTRY_CODE) === 0) return s;
  if (s.indexOf(DEFAULT_COUNTRY_CODE) === 0) return s;
  if (s.charAt(0) === "0") s = s.substring(1);
  return DEFAULT_COUNTRY_CODE + s;
}

function buildWhatsappMessage(o) {
  var lines = [];
  lines.push("\uD83D\uDCE6 LIVRAISON \u2014 " + o.reference);
  lines.push("");
  lines.push("\uD83D\uDC64 Client : " + (o.customer_name || ""));
  lines.push("\uD83D\uDCDE T\u00E9l\u00E9phone client : " + (o.phone || ""));
  lines.push("\uD83D\uDC8A Produit : " + (o.product_name || ""));
  lines.push("\uD83D\uDD22 Quantit\u00E9 : " + (o.quantity || 1));
  if (o.total !== undefined && o.total !== null) {
    lines.push("\uD83D\uDCB0 Total : " + Math.round(o.total).toLocaleString("fr-FR") + " FCFA");
  }
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

function openDriverModal(order) {
  var modal = document.getElementById("driver-modal");
  if (!modal) return;
  modal.classList.remove("hidden");
  modal._order = order;
  modal._selectedDriver = null;

  var selectedBox = document.getElementById("driver-selected");
  if (selectedBox) { selectedBox.classList.add("hidden"); selectedBox.innerHTML = ""; }
  var sendBtn = document.getElementById("driver-send-btn");
  if (sendBtn) sendBtn.classList.add("hidden");

  loadDrivers();
}

function loadDrivers() {
  var list = document.getElementById("driver-list");
  if (!list) return;
  list.innerHTML = '<div class="muted small" style="padding:14px;text-align:center">Chargement...</div>';
  fetch(API + "/drivers").then(function(r) {
    if (!r.ok) throw new Error("Erreur serveur");
    return r.json();
  }).then(function(drivers) {
    driversCache = drivers;
    renderDriversList(drivers);
  }).catch(function() {
    list.innerHTML = '<div class="muted small" style="padding:14px;text-align:center">Erreur de chargement.</div>';
  });
}

function renderDriversList(drivers) {
  var list = document.getElementById("driver-list");
  list.innerHTML = "";
  if (!drivers || drivers.length === 0) {
    list.appendChild(el("div", "muted small", "Aucun livreur actif n'est enregistr\u00E9."));
    return;
  }
  drivers.forEach(function(d) {
    var row = el("div", "driver-row");
    var radio = document.createElement("input");
    radio.type = "radio";
    radio.name = "driver-choice";
    radio.value = String(d.id);
    radio.id = "driver-" + d.id;

    var label = el("label", "driver-label");
    label.htmlFor = "driver-" + d.id;
    label.appendChild(el("span", "driver-name", d.name));
    label.appendChild(el("span", "driver-phone", formatPhoneDisplay(d.phone)));

    row.appendChild(radio);
    row.appendChild(label);

    row.addEventListener("click", function(ev) {
      if (ev.target !== radio) radio.checked = true;
      selectDriver(d);
    });

    list.appendChild(row);
  });
}

function selectDriver(d) {
  var modal = document.getElementById("driver-modal");
  if (!modal) return;
  modal._selectedDriver = d;

  var selectedBox = document.getElementById("driver-selected");
  if (selectedBox) {
    selectedBox.classList.remove("hidden");
    selectedBox.innerHTML = "";
    selectedBox.appendChild(el("div", "muted small", "Livreur s\u00E9lectionn\u00E9"));
    selectedBox.appendChild(el("div", "driver-selected-name",
      "\uD83D\uDE9A " + d.name + " \u2014 " + formatPhoneDisplay(d.phone)));
  }
  var sendBtn = document.getElementById("driver-send-btn");
  if (sendBtn) sendBtn.classList.remove("hidden");
}

function openWhatsappForDriver(order, driver) {
  var phone = normalizePhone(driver.phone);
  if (!phone || phone.length < 8) {
    alert("Num\u00E9ro du livreur invalide.");
    return;
  }
  var message = buildWhatsappMessage(order);
  var url = "https://wa.me/" + phone + "?text=" + encodeURIComponent(message);
  window.open(url, "_blank", "noopener");

  var selectedBox = document.getElementById("driver-selected");
  if (selectedBox) {
    selectedBox.innerHTML = "";
    selectedBox.appendChild(el("div", "muted small",
      "WhatsApp ouvert pour " + driver.name));
  }
  setTimeout(closeDriverModal, 1400);
}

function closeDriverModal() {
  var modal = document.getElementById("driver-modal");
  if (modal) {
    modal.classList.add("hidden");
    modal._order = null;
    modal._selectedDriver = null;
  }
}

function initDriverModal() {
  var modal = document.getElementById("driver-modal");
  if (!modal) return;

  var closeBtns = modal.querySelectorAll("[data-close-modal]");
  Array.prototype.forEach.call(closeBtns, function(b) {
    b.addEventListener("click", closeDriverModal);
  });

  var sendBtn = document.getElementById("driver-send-btn");
  if (sendBtn) {
    sendBtn.addEventListener("click", function() {
      if (!modal._selectedDriver || !modal._order) return;
      openWhatsappForDriver(modal._order, modal._selectedDriver);
    });
  }
}

'''

if "function openDriverModal" not in js:
    anchor = "function render(){"
    if anchor not in js:
        anchor = "function render() {"
    if anchor in js:
        js = js.replace(anchor, driver_js + anchor, 1)
        print("[OK] pharmacien.js -> fonctions modal livreur")
    else:
        print("[!] anchor render() introuvable")
else:
    print("[i] pharmacien.js -> fonctions deja presentes")

# 4c) Appel initDriverModal() dans init()
if "initDriverModal();" not in js:
    pattern = re.compile(r'(function init\(\)\s*\{)')
    m = pattern.search(js)
    if m:
        js = js[:m.end()] + "\n  initDriverModal();" + js[m.end():]
        print("[OK] pharmacien.js -> initDriverModal() branche")
    else:
        print("[!] fonction init() introuvable")
else:
    print("[i] pharmacien.js -> initDriverModal() deja branche")

PH_JS.write_text(js, encoding="utf-8")

print()
print("=======================================================")
print("Patch V2.2 (livreurs + WhatsApp) installe.")
print()
print("Redemarre le serveur :")
print("  taskkill /F /IM python.exe")
print("  python main.py")
print()
print("Puis navigateur : Ctrl+Shift+R sur /pharmacien")
print("=======================================================")