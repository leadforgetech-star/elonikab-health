from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
MAIN = BASE / "main.py"
INDEX = STATIC / "index.html"
APPJS = STATIC / "app.js"
PHJS = STATIC / "pharmacien.js"
STYLECSS = STATIC / "style.css"
PHCSS = STATIC / "pharmacien.css"

# Sauvegarde
shutil.copy(MAIN, MAIN.with_suffix(".py.bak"))
for f in (INDEX, APPJS, PHJS, STYLECSS, PHCSS):
    shutil.copy(f, f.with_suffix(f.suffix + ".bak"))
print("[OK] sauvegardes .bak creees")

# ============================================================
# 1) main.py - migration + endpoint
# ============================================================
src = MAIN.read_text(encoding="utf-8")

# 1a) Migration idempotente
migration_marker = "# --- GPS MIGRATION ---"
if migration_marker not in src:
    anchor = '''        " status TEXT NOT NULL DEFAULT 'en_attente',"
        " created_at TEXT NOT NULL"
        ")"
    )
'''
    migr = anchor + '''
    # --- GPS MIGRATION ---
    existing_cols = {row[1] for row in cur.execute("PRAGMA table_info(orders)").fetchall()}
    for col_name, col_type in (("latitude", "REAL"), ("longitude", "REAL"), ("location_accuracy", "REAL")):
        if col_name not in existing_cols:
            cur.execute("ALTER TABLE orders ADD COLUMN " + col_name + " " + col_type)
    # --- end GPS MIGRATION ---
'''
    if anchor in src:
        src = src.replace(anchor, migr, 1)
        print("[OK] main.py -> migration GPS ajoutee")
    else:
        print("[!] anchor migration introuvable")
else:
    print("[i] main.py -> migration GPS deja presente")

# 1b) Signature create_order
old_sig = '''    address: str = Form(""),
    prescription: Optional[UploadFile] = File(None),
):'''
new_sig = '''    address: str = Form(""),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    location_accuracy: Optional[float] = Form(None),
    prescription: Optional[UploadFile] = File(None),
):'''
if old_sig in src and "latitude: Optional[float]" not in src:
    src = src.replace(old_sig, new_sig, 1)
    print("[OK] main.py -> signature create_order etendue")
elif "latitude: Optional[float]" in src:
    print("[i] main.py -> signature deja etendue")
else:
    print("[!] signature create_order introuvable")

# 1c) Validation GPS
val_anchor = '''    if delivery_mode == "livraison" and not address.strip():
        raise HTTPException(status_code=400, detail="Adresse obligatoire pour la livraison")
'''
val_new = val_anchor + '''    if latitude is not None and (latitude < -90 or latitude > 90):
        raise HTTPException(status_code=400, detail="Latitude invalide (doit etre entre -90 et 90)")
    if longitude is not None and (longitude < -180 or longitude > 180):
        raise HTTPException(status_code=400, detail="Longitude invalide (doit etre entre -180 et 180)")
    if location_accuracy is not None and location_accuracy < 0:
        raise HTTPException(status_code=400, detail="Accuracy invalide (doit etre superieure ou egale a 0)")
'''
if val_anchor in src and "Latitude invalide" not in src:
    src = src.replace(val_anchor, val_new, 1)
    print("[OK] main.py -> validation GPS ajoutee")
elif "Latitude invalide" in src:
    print("[i] main.py -> validation deja presente")
else:
    print("[!] anchor validation introuvable")

# 1d) INSERT
old_insert = '''    cur = conn.execute(
        "INSERT INTO orders (reference, customer_name, phone, product_id, product_name,"
        " quantity, delivery_mode, address, prescription_file, status, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'en_attente', ?)",
        (reference, name, phone_clean, product["id"], product["name"], quantity,
         delivery_mode, address.strip(), saved_file, created_at),
    )'''
new_insert = '''    cur = conn.execute(
        "INSERT INTO orders (reference, customer_name, phone, product_id, product_name,"
        " quantity, delivery_mode, address, prescription_file, status, created_at,"
        " latitude, longitude, location_accuracy)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'en_attente', ?, ?, ?, ?)",
        (reference, name, phone_clean, product["id"], product["name"], quantity,
         delivery_mode, address.strip(), saved_file, created_at,
         latitude, longitude, location_accuracy),
    )'''
if old_insert in src and "latitude, longitude, location_accuracy)" not in src:
    src = src.replace(old_insert, new_insert, 1)
    print("[OK] main.py -> INSERT etendu")
elif "latitude, longitude, location_accuracy)" in src:
    print("[i] main.py -> INSERT deja etendu")
else:
    print("[!] INSERT introuvable")

# 1e) Reponse JSON
old_ret = '''        "prescription_file": saved_file,
        "price": product["price"],
        "total": round(product["price"] * quantity, 2),
    }'''
new_ret = '''        "prescription_file": saved_file,
        "price": product["price"],
        "total": round(product["price"] * quantity, 2),
        "latitude": latitude,
        "longitude": longitude,
        "location_accuracy": location_accuracy,
    }'''
if old_ret in src and '"latitude": latitude' not in src:
    src = src.replace(old_ret, new_ret, 1)
    print("[OK] main.py -> reponse JSON etendue")
elif '"latitude": latitude' in src:
    print("[i] main.py -> reponse deja etendue")
else:
    print("[!] dict de reponse introuvable")

MAIN.write_text(src, encoding="utf-8")

# ============================================================
# 2) index.html - bouton geolocalisation
# ============================================================
html = INDEX.read_text(encoding="utf-8")

old_addr = '''        <div class="form-row hidden" id="address-row">
          <label for="f-address">Adresse de livraison</label>
          <textarea id="f-address" name="address" rows="2" placeholder="Quartier, rue, repere..."></textarea>
        </div>'''
new_addr = '''        <div class="form-row hidden" id="address-row">
          <label for="f-address">Adresse de livraison</label>
          <textarea id="f-address" name="address" rows="2" placeholder="Quartier, rue, repere..."></textarea>
          <div class="geo-block">
            <button type="button" class="btn btn-ghost geo-btn" id="geo-btn">
              <span class="geo-icon">📍</span> Utiliser ma localisation actuelle
            </button>
            <div id="geo-status" class="geo-status hidden"></div>
          </div>
          <input type="hidden" id="f-latitude" name="latitude">
          <input type="hidden" id="f-longitude" name="longitude">
          <input type="hidden" id="f-location-accuracy" name="location_accuracy">
        </div>'''
if old_addr in html and 'id="geo-btn"' not in html:
    html = html.replace(old_addr, new_addr, 1)
    print("[OK] index.html -> bloc geolocalisation ajoute")
elif 'id="geo-btn"' in html:
    print("[i] index.html -> bloc deja present")
else:
    print("[!] anchor address-row introuvable")

INDEX.write_text(html, encoding="utf-8")

# ============================================================
# 3) app.js - logique geolocalisation
# ============================================================
js = APPJS.read_text(encoding="utf-8")

if "function initGeolocation" not in js:
    geo_func = r'''function initGeolocation() {
  var btn = document.getElementById("geo-btn");
  var status = document.getElementById("geo-status");
  var latInput = document.getElementById("f-latitude");
  var lonInput = document.getElementById("f-longitude");
  var accInput = document.getElementById("f-location-accuracy");
  if (!btn || !status || !latInput || !lonInput || !accInput) return;

  function setStatus(htmlMsg, cls) {
    status.className = "geo-status" + (cls ? " " + cls : "");
    status.innerHTML = htmlMsg;
    status.classList.remove("hidden");
  }
  function clearStatus() {
    status.classList.add("hidden");
    status.innerHTML = "";
  }
  function reset() {
    latInput.value = "";
    lonInput.value = "";
    accInput.value = "";
    clearStatus();
    btn.innerHTML = '<span class="geo-icon">📍</span> Utiliser ma localisation actuelle';
    btn.disabled = false;
  }

  btn.addEventListener("click", function () {
    if (!navigator.geolocation) {
      setStatus("La geolocalisation n'est pas disponible sur ce navigateur. Vous pouvez continuer avec votre adresse.", "geo-error");
      return;
    }
    btn.disabled = true;
    btn.innerHTML = '<span class="geo-icon">⏳</span> Localisation en cours...';
    setStatus("Recuperation de votre position...", "geo-loading");

    navigator.geolocation.getCurrentPosition(
      function (pos) {
        var lat = pos.coords.latitude;
        var lon = pos.coords.longitude;
        var acc = pos.coords.accuracy;
        latInput.value = String(lat);
        lonInput.value = String(lon);
        accInput.value = String(acc);
        setStatus("&#10003; Localisation enregistree<br><span class='geo-coords'>" +
                  lat.toFixed(5) + ", " + lon.toFixed(5) +
                  " (&#177; " + Math.round(acc) + " m)</span>", "geo-success");
        btn.disabled = false;
        btn.innerHTML = '<span class="geo-icon">📍</span> Actualiser ma localisation';
      },
      function (err) {
        var msg = "Localisation indisponible.";
        if (err.code === 1) msg = "Vous avez refuse la localisation. Vous pouvez continuer avec votre adresse.";
        else if (err.code === 2) msg = "Position introuvable. Verifiez votre GPS puis reessayez.";
        else if (err.code === 3) msg = "Delai de localisation depasse. Reessayez.";
        setStatus(msg, "geo-error");
        btn.disabled = false;
        btn.innerHTML = '<span class="geo-icon">📍</span> Utiliser ma localisation actuelle';
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  });

  var radios = document.querySelectorAll("input[name=delivery_mode]");
  Array.prototype.forEach.call(radios, function (r) {
    r.addEventListener("change", function () {
      if (r.value === "retrait" && r.checked) reset();
    });
  });
}

'''
    marker = "function init() {"
    if marker in js:
        js = js.replace(marker, geo_func + marker, 1)
        print("[OK] app.js -> initGeolocation ajoutee")
    else:
        print("[!] marker init() introuvable")

    # Ajouter l'appel dans init()
    anchor = '  $("#order-form").addEventListener("submit", submitOrder);'
    if anchor in js:
        js = js.replace(anchor, anchor + "\n  initGeolocation();", 1)
        print("[OK] app.js -> appel initGeolocation branche")
else:
    print("[i] app.js -> initGeolocation deja presente")

# Nettoyer les champs GPS vides avant envoi (evite les erreurs de parsing)
old_fetch = '''  fetch(API + "/orders", { method: "POST", body: data })'''
new_fetch = '''  ["latitude", "longitude", "location_accuracy"].forEach(function (k) {
    var v = data.get(k);
    if (v === null || v === "" || v === undefined) data.delete(k);
  });
  fetch(API + "/orders", { method: "POST", body: data })'''
if old_fetch in js and '"latitude", "longitude", "location_accuracy"' not in js:
    js = js.replace(old_fetch, new_fetch, 1)
    print("[OK] app.js -> nettoyage des champs GPS vides")
elif '"latitude", "longitude", "location_accuracy"' in js:
    print("[i] app.js -> nettoyage deja present")
else:
    print("[!] fetch orders introuvable")

APPJS.write_text(js, encoding="utf-8")

# ============================================================
# 4) pharmacien.js - lien Google Maps
# ============================================================
pjs = PHJS.read_text(encoding="utf-8")

if "order-geo" not in pjs:
    anchor = '''  var actions = NEXT_ACTIONS[o.status] || [];'''
    geo_block = '''  if (o.latitude !== null && o.latitude !== undefined &&
      o.longitude !== null && o.longitude !== undefined) {
    var geo = el("div", "order-geo");
    var mapLink = el("a", "btn btn-ghost", "\U0001F4CD Voir la localisation");
    mapLink.href = "https://www.google.com/maps?q=" + o.latitude + "," + o.longitude;
    mapLink.target = "_blank";
    mapLink.rel = "noopener";
    geo.appendChild(mapLink);
    if (o.location_accuracy !== null && o.location_accuracy !== undefined) {
      geo.appendChild(el("span", "muted small",
        "Precision \u00B1 " + Math.round(o.location_accuracy) + " m"));
    }
    card.appendChild(geo);
  } else if (o.delivery_mode === "livraison") {
    card.appendChild(el("div", "muted small", "Localisation non fournie"));
  }

'''
    if anchor in pjs:
        pjs = pjs.replace(anchor, geo_block + anchor, 1)
        print("[OK] pharmacien.js -> bloc localisation ajoute")
    else:
        print("[!] anchor NEXT_ACTIONS introuvable")
else:
    print("[i] pharmacien.js -> bloc deja present")

PHJS.write_text(pjs, encoding="utf-8")

# ============================================================
# 5) style.css - styles geolocalisation
# ============================================================
css = STYLECSS.read_text(encoding="utf-8")

if ".geo-block" not in css:
    geo_css = '''
/* --- Geolocalisation (patch GPS) --- */
.geo-block{
  margin-top:10px;display:flex;flex-direction:column;gap:8px;
}
.geo-btn{
  width:100%;justify-content:center;
}
.geo-icon{font-size:16px;line-height:1}
.geo-status{
  font-size:13px;padding:10px 12px;border-radius:10px;
  background:var(--bg);border:1px solid var(--line);line-height:1.5;
}
.geo-loading{background:#fff4e0;color:#b26b00;border-color:#f2d9b3}
.geo-success{background:var(--green-soft);color:var(--green-dark);border-color:#c7e9dc}
.geo-error{background:#fdecec;color:#b23c3c;border-color:#f6d2d2}
.geo-coords{font-family:Consolas,monospace;font-size:12px;opacity:.85}
'''
    css = css + geo_css
    STYLECSS.write_text(css, encoding="utf-8")
    print("[OK] style.css -> styles geolocalisation")
else:
    print("[i] style.css -> styles deja presents")

# ============================================================
# 6) pharmacien.css - styles lien localisation
# ============================================================
pcss = PHCSS.read_text(encoding="utf-8")

if ".order-geo" not in pcss:
    geo_pcss = '''
/* --- Localisation dans les cartes commandes --- */
.order-geo{
  display:flex;align-items:center;gap:10px;flex-wrap:wrap;
  padding-top:4px;
}
.order-geo .btn{padding:7px 12px;font-size:13px}
'''
    pcss = pcss + geo_pcss
    PHCSS.write_text(pcss, encoding="utf-8")
    print("[OK] pharmacien.css -> styles localisation")
else:
    print("[i] pharmacien.css -> styles deja presents")

print()
print("=======================================================")
print("Patch GPS installe.")
print()
print("Redemarre le serveur :")
print("  taskkill /F /IM python.exe")
print("  python main.py")
print()
print("Puis navigateur : Ctrl+Shift+R")
print("=======================================================")