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

# 1a) Migration : nouvelles colonnes pharmacy_settings + orders.delivery_distance_km
if "pharmacy_latitude" not in src:
    anchor = '''    cur.execute(
        "INSERT OR IGNORE INTO pharmacy_settings (id, delivery_fee_default) VALUES (1, 500)"
    )'''
    new_block = anchor + '''
    ps_cols = {row[1] for row in cur.execute("PRAGMA table_info(pharmacy_settings)").fetchall()}
    ps_new_cols = [
        ("pharmacy_latitude", "REAL"),
        ("pharmacy_longitude", "REAL"),
        ("delivery_base_fee", "REAL NOT NULL DEFAULT 300"),
        ("delivery_price_per_km", "REAL NOT NULL DEFAULT 100"),
        ("delivery_max_km", "REAL NOT NULL DEFAULT 0"),
    ]
    for col_name, col_type in ps_new_cols:
        if col_name not in ps_cols:
            cur.execute("ALTER TABLE pharmacy_settings ADD COLUMN " + col_name + " " + col_type)
    ord_cols2 = {row[1] for row in cur.execute("PRAGMA table_info(orders)").fetchall()}
    if "delivery_distance_km" not in ord_cols2:
        cur.execute("ALTER TABLE orders ADD COLUMN delivery_distance_km REAL")'''
    if anchor in src:
        src = src.replace(anchor, new_block, 1)
        print("[OK] main.py -> migration colonnes distance")
    else:
        print("[!] anchor INSERT OR IGNORE introuvable")

# 1b) Fonction Haversine + calcul frais (avant create_order)
helper = '''

# ============================================================
# V2.4 - Calcul des frais de livraison selon la distance
# ============================================================

def haversine_km(lat1, lon1, lat2, lon2):
    """Distance a vol d'oiseau en km entre deux points GPS."""
    from math import radians, sin, cos, asin, sqrt
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))


def compute_delivery_fee(client_lat, client_lon):
    """Retourne (fee, distance_km) selon la position du client.
    Si GPS client ou position pharmacie manquants : fallback delivery_fee_default,
    distance = None."""
    conn = get_db()
    s = conn.execute("SELECT * FROM pharmacy_settings WHERE id = 1").fetchone()
    conn.close()
    if s is None:
        return 0.0, None

    def col(name, default=0.0):
        try:
            v = s[name]
        except Exception:
            return default
        return default if v is None else v

    fallback = float(col("delivery_fee_default", 0.0))
    ph_lat = s["pharmacy_latitude"] if "pharmacy_latitude" in s.keys() else None
    ph_lon = s["pharmacy_longitude"] if "pharmacy_longitude" in s.keys() else None

    if client_lat is None or client_lon is None or ph_lat is None or ph_lon is None:
        return fallback, None

    dist = haversine_km(float(ph_lat), float(ph_lon), float(client_lat), float(client_lon))
    base = float(col("delivery_base_fee", 300.0))
    per_km = float(col("delivery_price_per_km", 100.0))
    fee = base + dist * per_km
    fee = round(fee / 50.0) * 50  # arrondi aux 50 FCFA
    return float(fee), round(dist, 2)


'''
if "def compute_delivery_fee" not in src:
    anchor = '@app.post("/api/orders")'
    if anchor in src:
        src = src.replace(anchor, helper + anchor, 1)
        print("[OK] main.py -> helper haversine + compute_delivery_fee")
    else:
        print("[!] anchor POST /api/orders introuvable")

# 1c) Remplacer le bloc de calcul du fee + INSERT + retour
old_calc = '''    if delivery_mode == "livraison":
        settings_row = conn.execute(
            "SELECT delivery_fee_default FROM pharmacy_settings WHERE id = 1"
        ).fetchone()
        delivery_fee = float(settings_row["delivery_fee_default"]) if settings_row else 0.0
    else:
        delivery_fee = 0.0
'''
new_calc = '''    if delivery_mode == "livraison":
        delivery_fee, delivery_distance = compute_delivery_fee(latitude, longitude)
    else:
        delivery_fee = 0.0
        delivery_distance = None
'''
if old_calc in src:
    src = src.replace(old_calc, new_calc, 1)
    print("[OK] main.py -> calcul delivery_fee par distance")
elif "compute_delivery_fee(latitude, longitude)" in src:
    print("[i] main.py -> calcul deja patche")
else:
    print("[!] ancien bloc de calcul introuvable")

# INSERT : ajouter delivery_distance_km
old_ins = '''        " latitude, longitude, location_accuracy, delivery_fee)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'en_attente', ?, ?, ?, ?, ?)",
        (reference, name, phone_clean, product["id"], product["name"], quantity,
         delivery_mode, address.strip(), saved_file, created_at,
         latitude, longitude, location_accuracy, delivery_fee),
    )'''
new_ins = '''        " latitude, longitude, location_accuracy, delivery_fee, delivery_distance_km)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'en_attente', ?, ?, ?, ?, ?, ?)",
        (reference, name, phone_clean, product["id"], product["name"], quantity,
         delivery_mode, address.strip(), saved_file, created_at,
         latitude, longitude, location_accuracy, delivery_fee, delivery_distance),
    )'''
if old_ins in src and "delivery_distance_km)" not in src.split("INSERT INTO orders")[1][:500]:
    src = src.replace(old_ins, new_ins, 1)
    print("[OK] main.py -> INSERT delivery_distance_km")
elif "delivery_distance_km)" in src:
    print("[i] main.py -> INSERT deja patche")

# Retour JSON : ajouter delivery_distance_km
old_json = '''        "subtotal": round(product["price"] * quantity, 2),
        "delivery_fee": delivery_fee,
        "total": round(product["price"] * quantity + delivery_fee, 2),'''
new_json = '''        "subtotal": round(product["price"] * quantity, 2),
        "delivery_fee": delivery_fee,
        "delivery_distance_km": delivery_distance,
        "total": round(product["price"] * quantity + delivery_fee, 2),'''
if old_json in src and '"delivery_distance_km":' not in src:
    src = src.replace(old_json, new_json, 1)
    print("[OK] main.py -> retour JSON delivery_distance_km")

# 1d) PATCH /api/settings : accepter les nouveaux champs
old_model = '''class SettingsUpdate(BaseModel):
    delivery_fee_default: float
'''
new_model = '''class SettingsUpdate(BaseModel):
    delivery_fee_default: Optional[float] = None
    pharmacy_latitude: Optional[float] = None
    pharmacy_longitude: Optional[float] = None
    delivery_base_fee: Optional[float] = None
    delivery_price_per_km: Optional[float] = None
    delivery_max_km: Optional[float] = None
'''
if old_model in src:
    src = src.replace(old_model, new_model, 1)
    print("[OK] main.py -> SettingsUpdate etendu")

# 1e) Remplacer le corps de PATCH /api/settings
old_patch_fn = '''@app.patch("/api/settings")
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
new_patch_fn = '''@app.patch("/api/settings")
def update_settings(payload: SettingsUpdate):
    fields = payload.dict(exclude_unset=True, exclude_none=True)

    validators = {
        "delivery_fee_default": (0, 1000000, "Frais par defaut"),
        "delivery_base_fee": (0, 1000000, "Frais de base"),
        "delivery_price_per_km": (0, 1000000, "Prix par km"),
        "delivery_max_km": (0, 1000, "Distance maximale"),
    }
    for name, (vmin, vmax, label) in validators.items():
        if name in fields:
            try:
                v = float(fields[name])
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail=label + " : valeur invalide")
            if v < vmin or v > vmax:
                raise HTTPException(status_code=400, detail=label + " : valeur hors limites")
            fields[name] = v

    if "pharmacy_latitude" in fields:
        try:
            lat = float(fields["pharmacy_latitude"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Latitude invalide")
        if lat < -90 or lat > 90:
            raise HTTPException(status_code=400, detail="Latitude invalide")
        fields["pharmacy_latitude"] = lat

    if "pharmacy_longitude" in fields:
        try:
            lon = float(fields["pharmacy_longitude"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Longitude invalide")
        if lon < -180 or lon > 180:
            raise HTTPException(status_code=400, detail="Longitude invalide")
        fields["pharmacy_longitude"] = lon

    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO pharmacy_settings (id) VALUES (1)")
    if fields:
        set_clause = ", ".join(k + " = ?" for k in fields.keys())
        params = list(fields.values())
        conn.execute("UPDATE pharmacy_settings SET " + set_clause + " WHERE id = 1", params)
    conn.commit()
    row = conn.execute("SELECT * FROM pharmacy_settings WHERE id = 1").fetchone()
    conn.close()
    return row_to_dict(row)
'''
if old_patch_fn in src:
    src = src.replace(old_patch_fn, new_patch_fn, 1)
    print("[OK] main.py -> PATCH /api/settings etendu")
elif 'fields = payload.dict' in src:
    print("[i] main.py -> PATCH deja patche")
else:
    print("[!] ancien PATCH /api/settings introuvable")

MAIN.write_text(src, encoding="utf-8")

# =================================================================
# 2) index.html : affichage enrichi du bloc delivery-fee
# =================================================================
html = INDEX.read_text(encoding="utf-8")
# Le bloc existe deja (#delivery-fee-info), on n'a rien a ajouter cote HTML.

# =================================================================
# 3) app.js : calcul client-side distance + affichage
# =================================================================
js = APPJS.read_text(encoding="utf-8")

# Remplacer updateDeliveryFeeDisplay par une version distance-aware
old_ufd = js.find("function updateDeliveryFeeDisplay() {")
if old_ufd != -1:
    # Trouver la fin de la fonction (premiere "}\n}" apres)
    end_marker = js.find("\n}\n", old_ufd)
    if end_marker == -1:
        end_marker = js.find("\n}\r\n", old_ufd)
    if end_marker != -1:
        end_marker += 2
        new_ufd = r'''function haversineKm(lat1, lon1, lat2, lon2) {
  var R = 6371.0;
  var dLat = (lat2 - lat1) * Math.PI / 180;
  var dLon = (lon2 - lon1) * Math.PI / 180;
  var a = Math.sin(dLat / 2) * Math.sin(dLat / 2)
        + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180)
        * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  return 2 * R * Math.asin(Math.sqrt(a));
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

  var s = pharmacySettings || {};
  var fallback = Math.round(Number(s.delivery_fee_default) || 0);
  var phLat = s.pharmacy_latitude;
  var phLon = s.pharmacy_longitude;
  var base = Number(s.delivery_base_fee);
  var perKm = Number(s.delivery_price_per_km);

  var latEl = document.getElementById("f-latitude");
  var lonEl = document.getElementById("f-longitude");
  var clientLat = latEl && latEl.value ? Number(latEl.value) : null;
  var clientLon = lonEl && lonEl.value ? Number(lonEl.value) : null;

  if (phLat === null || phLat === undefined || phLon === null || phLon === undefined
      || isNaN(phLat) || isNaN(phLon)) {
    // Position pharmacie non configuree : fallback
    box.innerHTML = "&#128666; Frais de livraison : <strong>"
      + fallback.toLocaleString("fr-FR") + " FCFA</strong>"
      + "<br><span class='muted small'>Position pharmacie non configuree.</span>";
    box.classList.remove("hidden");
    return;
  }

  if (clientLat === null || clientLon === null || isNaN(clientLat) || isNaN(clientLon)) {
    // Pas de GPS client : fallback
    box.innerHTML = "&#128666; Frais de livraison estim&#233;s : <strong>"
      + fallback.toLocaleString("fr-FR") + " FCFA</strong>"
      + "<br><span class='muted small'>Activez la localisation pour un tarif bas&#233; sur la distance.</span>";
    box.classList.remove("hidden");
    return;
  }

  var dist = haversineKm(phLat, phLon, clientLat, clientLon);
  var b = isNaN(base) ? 300 : base;
  var p = isNaN(perKm) ? 100 : perKm;
  var fee = b + dist * p;
  fee = Math.round(fee / 50) * 50;

  box.innerHTML = "&#128666; Distance estim&#233;e : <strong>"
    + dist.toFixed(1) + " km</strong>"
    + "<br>&#128181; Frais de livraison : <strong>"
    + fee.toLocaleString("fr-FR") + " FCFA</strong>"
    + "<br><span class='muted small'>Distance &#224; vol d'oiseau, tarif indicatif. La pharmacie confirme.</span>";
  box.classList.remove("hidden");
}
'''
        js = js[:old_ufd] + new_ufd + js[end_marker:]
        print("[OK] app.js -> updateDeliveryFeeDisplay distance-aware")

# Brancher le recalcul sur changement de GPS client
if "updateDeliveryFeeDisplay();" in js and "f-latitude" not in js.split("input[name=delivery_mode]")[0][-2000:]:
    # Ajouter l'appel apres acquisition GPS reussie
    anchor_gps = "        btn.innerHTML = '<span class=\"geo-icon\">&#128205;</span> Actualiser ma localisation';"
    if anchor_gps in js and "updateDeliveryFeeDisplay();" not in js[js.find(anchor_gps):js.find(anchor_gps)+300]:
        js = js.replace(anchor_gps, anchor_gps + "\n        updateDeliveryFeeDisplay();", 1)
        print("[OK] app.js -> recalcul apres acquisition GPS")

APPJS.write_text(js, encoding="utf-8")

# =================================================================
# 4) pharmacien.html : etendre la section parametres
# =================================================================
html = PH_HTML.read_text(encoding="utf-8")

old_form = '''    <form id="settings-form" class="settings-form">
      <label for="delivery-fee-input">Frais de livraison par defaut</label>
      <div class="settings-row">
        <input type="number" id="delivery-fee-input" min="0" step="50" required>
        <span class="muted">FCFA</span>
        <button type="submit" class="btn btn-primary">Enregistrer</button>
      </div>
      <span id="settings-status" class="muted small"></span>
    </form>'''
new_form = '''    <form id="settings-form" class="settings-form">
      <h3 class="settings-sub">Position de la pharmacie</h3>
      <p class="muted small">N&#233;cessaire pour calculer les frais de livraison selon la distance.</p>
      <div class="settings-row">
        <input type="number" id="ph-lat-input" step="0.00001" placeholder="Latitude" class="settings-input-wide">
        <input type="number" id="ph-lon-input" step="0.00001" placeholder="Longitude" class="settings-input-wide">
        <button type="button" class="btn btn-ghost" id="ph-geo-btn">&#128205; Utiliser ma position</button>
      </div>

      <h3 class="settings-sub">Tarification</h3>
      <div class="settings-grid">
        <div>
          <label for="base-fee-input">Frais de base</label>
          <div class="settings-row">
            <input type="number" id="base-fee-input" min="0" step="50">
            <span class="muted">FCFA</span>
          </div>
        </div>
        <div>
          <label for="per-km-input">Prix par km</label>
          <div class="settings-row">
            <input type="number" id="per-km-input" min="0" step="10">
            <span class="muted">FCFA/km</span>
          </div>
        </div>
        <div>
          <label for="fallback-fee-input">Frais si GPS indisponible</label>
          <div class="settings-row">
            <input type="number" id="fallback-fee-input" min="0" step="50">
            <span class="muted">FCFA</span>
          </div>
        </div>
        <div>
          <label for="max-km-input">Distance maximale (0 = illimite)</label>
          <div class="settings-row">
            <input type="number" id="max-km-input" min="0" step="1">
            <span class="muted">km</span>
          </div>
        </div>
      </div>

      <div class="settings-row">
        <button type="submit" class="btn btn-primary">Enregistrer</button>
        <span id="settings-status" class="muted small"></span>
      </div>
    </form>'''
if old_form in html:
    html = html.replace(old_form, new_form, 1)
    PH_HTML.write_text(html, encoding="utf-8")
    print("[OK] pharmacien.html -> formulaire parametres etendu")
elif "ph-lat-input" in html:
    print("[i] pharmacien.html -> formulaire deja etendu")
else:
    print("[!] ancien formulaire settings introuvable")

# =================================================================
# 5) pharmacien.css : styles additionnels
# =================================================================
css = PH_CSS.read_text(encoding="utf-8")
if ".settings-sub" not in css:
    css += '''
/* --- V2.4 : formulaire parametres etendu --- */
.settings-sub{
  font-size:13px;text-transform:uppercase;letter-spacing:.06em;
  color:var(--muted);margin:12px 0 6px;font-weight:800;
}
.settings-sub:first-child{margin-top:0}
.settings-form{max-width:720px}
.settings-grid{
  display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
  gap:14px;margin-bottom:8px;
}
.settings-grid label{font-size:12px;font-weight:700;display:block;margin-bottom:4px}
.settings-input-wide{
  flex:1;min-width:140px;padding:10px 12px;border:1px solid var(--line);
  border-radius:10px;font-size:14px;font-family:inherit;
}
.settings-input-wide:focus{outline:none;border-color:var(--green)}
'''
    PH_CSS.write_text(css, encoding="utf-8")
    print("[OK] pharmacien.css -> styles V2.4")

# =================================================================
# 6) pharmacien.js : charger/enregistrer les nouveaux champs
# =================================================================
js = PH_JS.read_text(encoding="utf-8")

# Remplacer loadSettingsDashboard
old_load = js.find("function loadSettingsDashboard() {")
if old_load != -1:
    end_marker = js.find("\n}\n", old_load)
    if end_marker == -1:
        end_marker = js.find("\n}\r\n", old_load)
    if end_marker != -1:
        end_marker += 2
        new_load = r'''function loadSettingsDashboard() {
  fetch(API + "/settings").then(function (r) {
    if (!r.ok) throw new Error("settings");
    return r.json();
  }).then(function (s) {
    function setVal(id, v, digits) {
      var el = document.getElementById(id);
      if (!el) return;
      if (v === null || v === undefined || v === "") { el.value = ""; return; }
      el.value = digits !== undefined ? Number(v).toFixed(digits) : String(Math.round(Number(v)));
    }
    setVal("fallback-fee-input", s.delivery_fee_default);
    setVal("base-fee-input", s.delivery_base_fee);
    setVal("per-km-input", s.delivery_price_per_km);
    setVal("max-km-input", s.delivery_max_km);
    setVal("ph-lat-input", s.pharmacy_latitude, 5);
    setVal("ph-lon-input", s.pharmacy_longitude, 5);
  }).catch(function () {});
}
'''
        js = js[:old_load] + new_load + js[end_marker:]
        print("[OK] pharmacien.js -> loadSettingsDashboard etendu")

# Remplacer submitSettings
old_sub = js.find("function submitSettings(ev) {")
if old_sub != -1:
    end_marker = js.find("\n}\n", old_sub)
    if end_marker == -1:
        end_marker = js.find("\n}\r\n", old_sub)
    if end_marker != -1:
        end_marker += 2
        new_sub = r'''function submitSettings(ev) {
  ev.preventDefault();
  var status = document.getElementById("settings-status");

  function num(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    var raw = String(el.value).trim();
    if (raw === "") return null;
    var n = Number(raw);
    return isNaN(n) ? null : n;
  }

  var payload = {
    delivery_fee_default: num("fallback-fee-input"),
    delivery_base_fee: num("base-fee-input"),
    delivery_price_per_km: num("per-km-input"),
    delivery_max_km: num("max-km-input"),
    pharmacy_latitude: num("ph-lat-input"),
    pharmacy_longitude: num("ph-lon-input")
  };
  Object.keys(payload).forEach(function (k) {
    if (payload[k] === null) delete payload[k];
  });

  fetch(API + "/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  }).then(function (r) {
    return r.json().then(function (body) {
      if (!r.ok) throw new Error(body.detail || "Erreur");
      return body;
    });
  }).then(function () {
    if (status) {
      status.textContent = "\u2713 Param\u00E8tres enregistr\u00E9s";
      setTimeout(function () { status.textContent = ""; }, 3000);
    }
    loadSettingsDashboard();
  }).catch(function (err) {
    if (status) status.textContent = err.message || "Erreur";
  });
}
'''
        js = js[:old_sub] + new_sub + js[end_marker:]
        print("[OK] pharmacien.js -> submitSettings etendu")

# Ajouter bouton "Utiliser ma position" pour la pharmacie
if "ph-geo-btn" not in js:
    init_patch = '''
function initPharmacyGeo() {
  var btn = document.getElementById("ph-geo-btn");
  if (!btn) return;
  btn.addEventListener("click", function () {
    if (!navigator.geolocation) {
      alert("Geolocalisation indisponible sur ce navigateur.");
      return;
    }
    btn.disabled = true;
    btn.textContent = "\\u23F3 Localisation...";
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        var lat = document.getElementById("ph-lat-input");
        var lon = document.getElementById("ph-lon-input");
        if (lat) lat.value = pos.coords.latitude.toFixed(5);
        if (lon) lon.value = pos.coords.longitude.toFixed(5);
        btn.disabled = false;
        btn.innerHTML = "\\uD83D\\uDCCD Utiliser ma position";
      },
      function () {
        btn.disabled = false;
        btn.innerHTML = "\\uD83D\\uDCCD Utiliser ma position";
        alert("Localisation indisponible. Autorisez la geolocalisation puis reessayez.");
      },
      { enableHighAccuracy: true, timeout: 20000, maximumAge: 60000 }
    );
  });
}
document.addEventListener("DOMContentLoaded", initPharmacyGeo);
'''
    js = js + init_patch
    print("[OK] pharmacien.js -> initPharmacyGeo")

PH_JS.write_text(js, encoding="utf-8")

print()
print("=======================================================")
print("Patch V2.4 (frais par distance) installe.")
print()
print("Etapes suivantes :")
print("  1. taskkill /F /IM python.exe")
print("  2. python main.py")
print("  3. Navigateur : Ctrl+Shift+R")
print()
print("CONFIGURATION :")
print("  - Va sur /pharmacien > Parametres de livraison")
print("  - Clique 'Utiliser ma position' pour definir la pharmacie")
print("  - Regle frais de base + prix/km + fallback")
print("  - Enregistre")
print("=======================================================")