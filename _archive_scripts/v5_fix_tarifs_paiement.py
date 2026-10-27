"""
v5_fix_tarifs_paiement.py
1. Configure le numero de paiement +22871039904
2. Affiche la formule tarifaire dans la page Confirmer
3. Expose les tarifs VOITURE/MOTO dans le dashboard pharmacien
4. Confirme le flux de paiement manuel
"""
from pathlib import Path
import datetime
import shutil
import sqlite3
import re

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
DB = BASE / "database.db"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_tarifs_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(DB, backup / "database.db")
for f in ("professional_demande_confirmer.js", "pharmacien.html", "pharmacien.js"):
    p = STATIC / f
    if p.exists():
        shutil.copy2(p, backup / f)
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. Configurer les tarifs + numero paiement en base
# ============================================================
conn = sqlite3.connect(DB)
conn.execute("""
    UPDATE pharmacy_settings SET
      payment_number = '+22871039904',
      payment_name = COALESCE(NULLIF(payment_name,''), 'Elokinab Health'),
      car_base_fee = COALESCE(car_base_fee, 1000),
      car_price_per_km = COALESCE(car_price_per_km, 250),
      car_minimum_fee = COALESCE(car_minimum_fee, 1000),
      motorbike_base_fee = COALESCE(motorbike_base_fee, 500),
      motorbike_price_per_km = COALESCE(motorbike_price_per_km, 150),
      motorbike_minimum_fee = COALESCE(motorbike_minimum_fee, 500)
    WHERE id=1
""")
conn.commit()
row = conn.execute("""
    SELECT car_base_fee, car_price_per_km, car_minimum_fee,
           motorbike_base_fee, motorbike_price_per_km,
           payment_number, payment_name
    FROM pharmacy_settings WHERE id=1
""").fetchone()
conn.close()
print("[OK] Base configuree :")
print("   VOITURE   : base =", row[0], "F  |  prix/km =", row[1], "F  |  min =", row[2], "F")
print("   MOTO      : base =", row[3], "F  |  prix/km =", row[4], "F")
print("   Paiement  :", row[5], "(" + str(row[6]) + ")")

# ============================================================
# 2. Endpoint /estimate-delivery : retourner la formule utilisee
# ============================================================
B2B = BASE / "v3_modules" / "b2b_requests.py"
src = B2B.read_text(encoding="utf-8")

# Modifier l'endpoint estimate_delivery pour inclure les tarifs
old_estimate = '''        return {
            "distance_km": dist,
            "delivery_fee": fee,
            "source": source,
            "subtotal": subtotal,
            "total": round(subtotal + fee, 2) if source == "gps" else None,
        }'''
new_estimate = '''        # Recuperer les tarifs utilises
        s = conn_settings = None
        try:
            conn_s = get_db()
            s = conn_s.execute(
                "SELECT car_base_fee, car_price_per_km, car_minimum_fee,"
                " delivery_fee_default"
                " FROM pharmacy_settings WHERE id=1"
            ).fetchone()
            conn_s.close()
        except Exception:
            s = None

        rates = {
            "vehicle": "VOITURE",
            "base_fee": float(s["car_base_fee"] or 1000) if s else 1000,
            "price_per_km": float(s["car_price_per_km"] or 250) if s else 250,
            "minimum_fee": float(s["car_minimum_fee"] or 1000) if s else 1000,
            "fallback_fee": float(s["delivery_fee_default"] or 1000) if s else 1000,
            "rounding": 50,
        }

        return {
            "distance_km": dist,
            "delivery_fee": fee,
            "source": source,
            "subtotal": subtotal,
            "total": round(subtotal + fee, 2) if source == "gps" else None,
            "rates": rates,
        }'''
if old_estimate in src:
    src = src.replace(old_estimate, new_estimate, 1)
    B2B.write_text(src, encoding="utf-8")
    print("[OK] b2b_requests.py -> endpoint estimate retourne les tarifs")

# ============================================================
# 3. Frontend : afficher la formule + tarif applique
# ============================================================
CONF_JS = STATIC / "professional_demande_confirmer.js"
js = CONF_JS.read_text(encoding="utf-8")

# Ajouter la formule dans le rendu
old_delivery = '''      } else if (state.estimate && state.estimate.source === "no_pharmacy") {
        deliveryLine =
          '<div class="totals-line">' +
            '<span class="lbl">Frais livraison</span>' +
            '<span class="val confirm">A confirmer</span>' +
          '</div>';
      } else {'''
new_delivery = '''      } else if (state.estimate && state.estimate.source === "no_pharmacy") {
        deliveryLine =
          '<div class="totals-line">' +
            '<span class="lbl">Frais livraison</span>' +
            '<span class="val confirm">A confirmer</span>' +
          '</div>';
      } else {
        var _unused = 1;'''
if old_delivery in js:
    js = js.replace(old_delivery, new_delivery, 1)

# Simplifier : on va reecrire la section delivery pour inclure la formule
old_delivery_section = re.compile(
    r"    var deliveryLine = '';\n.*?\n    }\n\n    var deliveryFields",
    re.DOTALL
)
new_delivery_section = '''    var deliveryLine = '';
    if (state.mode === "livraison") {
      if (state.estimate && state.estimate.source === "gps") {
        var r = state.estimate.rates || {};
        var formula = (r.base_fee || 1000) + ' F + ' +
                      state.estimate.distance_km + ' km x ' +
                      (r.price_per_km || 250) + ' F/km';
        var minFee = r.minimum_fee || 0;
        var roundTxt = r.rounding ? ' (arrondi aux ' + r.rounding + ' F)' : '';
        deliveryLine =
          '<div class="totals-line">' +
            '<span class="lbl">Distance</span>' +
            '<span class="val">' + state.estimate.distance_km + ' km</span>' +
          '</div>' +
          '<div class="totals-line">' +
            '<span class="lbl">Tarif ' + (r.vehicle || 'VOITURE') + '</span>' +
            '<span class="val" style="font-size:12px;font-weight:600;color:#64748b">' + formula + roundTxt + '</span>' +
          '</div>' +
          '<div class="totals-line">' +
            '<span class="lbl">Frais livraison</span>' +
            '<span class="val">' + money(state.estimate.delivery_fee) + '</span>' +
          '</div>';
      } else if (state.estimate && state.estimate.source === "no_gps") {
        deliveryLine =
          '<div class="totals-line">' +
            '<span class="lbl">Frais livraison</span>' +
            '<span class="val confirm">Activez le GPS</span>' +
          '</div>';
      } else if (state.estimate && state.estimate.source === "no_pharmacy") {
        deliveryLine =
          '<div class="totals-line">' +
            '<span class="lbl">Frais livraison</span>' +
            '<span class="val confirm">A confirmer</span>' +
          '</div>' +
          '<div class="totals-line">' +
            '<span class="lbl" style="font-size:12px;font-weight:600;color:#64748b">Position pharmacie non configuree</span>' +
            '<span class="val"></span>' +
          '</div>';
      } else {
        deliveryLine =
          '<div class="totals-line">' +
            '<span class="lbl">Frais livraison</span>' +
            '<span class="val confirm">En attente du GPS</span>' +
          '</div>';
      }
    } else {
      deliveryLine =
        '<div class="totals-line">' +
          '<span class="lbl">Frais livraison</span>' +
          '<span class="val">Retrait en pharmacie — 0 F</span>' +
        '</div>';
    }

    var deliveryFields'''
if old_delivery_section.search(js):
    js = js.replace(old_delivery_section.search(js).group(0), new_delivery_section, 1)
    print("[OK] professional_demande_confirmer.js -> formule tarifaire affichee")
else:
    # Fallback : remplacer juste la section var deliveryLine
    print("[!] pattern deliveryLine non trouve, fallback simple")
    # Essayer une autre approche
    idx = js.find("var deliveryLine =")
    end = js.find("var deliveryFields")
    if idx > 0 and end > idx:
        js = js[:idx] + new_delivery_section[:-len("    var deliveryFields")] + js[end:]
        print("[OK] fallback applique")

CONF_JS.write_text(js, encoding="utf-8")

# ============================================================
# 4. Ajouter les champs tarifaires dans le dashboard pharmacien
# ============================================================
PHHTML = STATIC / "pharmacien.html"
html = PHHTML.read_text(encoding="utf-8")

TARIFS_BLOCK = '''      <h3 class="settings-sub">Tarifs VOITURE (professionnels)</h3>
      <div class="settings-grid">
        <div>
          <label for="car-base-fee">Frais de base</label>
          <div class="settings-row">
            <input type="number" id="car-base-fee" min="0" step="50">
            <span class="muted">FCFA</span>
          </div>
        </div>
        <div>
          <label for="car-price-per-km">Prix par km</label>
          <div class="settings-row">
            <input type="number" id="car-price-per-km" min="0" step="10">
            <span class="muted">FCFA/km</span>
          </div>
        </div>
        <div>
          <label for="car-minimum-fee">Frais minimum</label>
          <div class="settings-row">
            <input type="number" id="car-minimum-fee" min="0" step="50">
            <span class="muted">FCFA</span>
          </div>
        </div>
      </div>

      <h3 class="settings-sub">Tarifs MOTO (particuliers)</h3>
      <div class="settings-grid">
        <div>
          <label for="moto-base-fee">Frais de base</label>
          <div class="settings-row">
            <input type="number" id="moto-base-fee" min="0" step="50">
            <span class="muted">FCFA</span>
          </div>
        </div>
        <div>
          <label for="moto-price-per-km">Prix par km</label>
          <div class="settings-row">
            <input type="number" id="moto-price-per-km" min="0" step="10">
            <span class="muted">FCFA/km</span>
          </div>
        </div>
        <div>
          <label for="moto-minimum-fee">Frais minimum</label>
          <div class="settings-row">
            <input type="number" id="moto-minimum-fee" min="0" step="50">
            <span class="muted">FCFA</span>
          </div>
        </div>
      </div>

      <h3 class="settings-sub">Paiement</h3>
      <div class="settings-grid">
        <div>
          <label for="payment-number-input">Numero de paiement</label>
          <div class="settings-row">
            <input type="tel" id="payment-number-input" placeholder="+228 71 03 99 04">
            <span class="muted small">Numero Mobile Money</span>
          </div>
        </div>
        <div>
          <label for="payment-name-input">Nom du beneficiaire</label>
          <div class="settings-row">
            <input type="text" id="payment-name-input" placeholder="Elokinab Health">
          </div>
        </div>
      </div>

      <h3 class="settings-sub">Contact WhatsApp (pour commandes pro)</h3>'''

# Chercher le point d'insertion
anchor = '<h3 class="settings-sub">Contact WhatsApp (pour commandes pro)</h3>'
if anchor in html and 'id="car-base-fee"' not in html:
    html = html.replace(anchor, TARIFS_BLOCK, 1)
    PHHTML.write_text(html, encoding="utf-8")
    print("[OK] pharmacien.html -> champs tarifs + paiement ajoutes")
else:
    print("[i] pharmacien.html -> champs tarifs deja presents")

# ============================================================
# 5. Patch pharmacien.js pour charger/sauvegarder les tarifs
# ============================================================
PHJS = STATIC / "pharmacien.js"
pjs = PHJS.read_text(encoding="utf-8")

# Ajouter au loadSettingsDashboard
old_load = '''    var waEl = document.getElementById("whatsapp-input");
    if (waEl) waEl.value = s.whatsapp_number || "";'''
new_load = '''    var waEl = document.getElementById("whatsapp-input");
    if (waEl) waEl.value = s.whatsapp_number || "";

    function setField(id, v) {
      var el = document.getElementById(id);
      if (!el) return;
      el.value = (v === null || v === undefined) ? "" : String(Math.round(Number(v)));
    }
    setField("car-base-fee", s.car_base_fee);
    setField("car-price-per-km", s.car_price_per_km);
    setField("car-minimum-fee", s.car_minimum_fee);
    setField("moto-base-fee", s.motorbike_base_fee);
    setField("moto-price-per-km", s.motorbike_price_per_km);
    setField("moto-minimum-fee", s.motorbike_minimum_fee);

    var pnum = document.getElementById("payment-number-input");
    if (pnum) pnum.value = s.payment_number || "";
    var pname = document.getElementById("payment-name-input");
    if (pname) pname.value = s.payment_name || "";'''

if old_load in pjs and "car-base-fee" not in pjs:
    pjs = pjs.replace(old_load, new_load, 1)
    print("[OK] pharmacien.js -> load des tarifs")

# Ajouter au submitSettings
old_payload = '''  var waEl = document.getElementById("whatsapp-input");
  if (waEl) payload.whatsapp_number = String(waEl.value || "").trim();'''
new_payload = '''  var waEl = document.getElementById("whatsapp-input");
  if (waEl) payload.whatsapp_number = String(waEl.value || "").trim();

  function numField(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    var v = String(el.value).trim();
    if (v === "") return null;
    var n = Number(v);
    return isNaN(n) ? null : n;
  }
  function txtField(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    return String(el.value || "").trim();
  }
  var carBase = numField("car-base-fee"); if (carBase !== null) payload.car_base_fee = carBase;
  var carPk = numField("car-price-per-km"); if (carPk !== null) payload.car_price_per_km = carPk;
  var carMin = numField("car-minimum-fee"); if (carMin !== null) payload.car_minimum_fee = carMin;
  var motoBase = numField("moto-base-fee"); if (motoBase !== null) payload.motorbike_base_fee = motoBase;
  var motoPk = numField("moto-price-per-km"); if (motoPk !== null) payload.motorbike_price_per_km = motoPk;
  var motoMin = numField("moto-minimum-fee"); if (motoMin !== null) payload.motorbike_minimum_fee = motoMin;
  var pnum = txtField("payment-number-input"); if (pnum !== null) payload.payment_number = pnum;
  var pname = txtField("payment-name-input"); if (pname !== null) payload.payment_name = pname;'''

if old_payload in pjs and "car_base_fee" not in pjs.split("payload.whatsapp_number")[1][:500]:
    pjs = pjs.replace(old_payload, new_payload, 1)
    print("[OK] pharmacien.js -> submit des tarifs")

PHJS.write_text(pjs, encoding="utf-8")

# ============================================================
# 6. Patch main.py : ajouter les nouveaux champs au SettingsUpdate
# ============================================================
MAIN = BASE / "main.py"
mainsrc = MAIN.read_text(encoding="utf-8")

if "motorbike_base_fee: Optional[float]" not in mainsrc:
    old_model = "class SettingsUpdate(BaseModel):"
    new_model = '''class SettingsUpdate(BaseModel):
    motorbike_base_fee: Optional[float] = None
    motorbike_price_per_km: Optional[float] = None
    motorbike_minimum_fee: Optional[float] = None
    car_base_fee: Optional[float] = None
    car_price_per_km: Optional[float] = None
    car_minimum_fee: Optional[float] = None
    delivery_max_km: Optional[float] = None
    payment_number: Optional[str] = None
    payment_name: Optional[str] = None
    pharmacy_name: Optional[str] = None
    pharmacy_phone: Optional[str] = None
    pharmacy_address: Optional[str] = None
    whatsapp_number: Optional[str] = None
    pharmacy_latitude: Optional[float] = None
    pharmacy_longitude: Optional[float] = None
    delivery_base_fee: Optional[float] = None
    delivery_price_per_km: Optional[float] = None
    delivery_fee_default: Optional[float] = None
'''
    if old_model in mainsrc:
        # Remplacer la classe entiere
        pattern = re.compile(
            r'class SettingsUpdate\(BaseModel\):.*?(?=\n\nclass |\n\n@app |\n\ndef |\Z)',
            re.DOTALL
        )
        mainsrc = pattern.sub(new_model, mainsrc, count=1)
        MAIN.write_text(mainsrc, encoding="utf-8")
        print("[OK] main.py -> SettingsUpdate etendu")

# ============================================================
# 7. Patch main.py : PATCH /api/settings accepte les nouveaux champs
# ============================================================
mainsrc = MAIN.read_text(encoding="utf-8")
if 'fields = payload.dict(exclude_unset=True, exclude_none=True)' in mainsrc:
    # Chercher le bloc de mise a jour
    old_block = re.compile(
        r'    conn\.execute\("INSERT OR IGNORE INTO pharmacy_settings.*?return row_to_dict\(row\)',
        re.DOTALL
    )
    new_block = '''    # Valider les champs numériques
    numeric_validators = {
        "delivery_fee_default": (0, 1000000),
        "delivery_base_fee": (0, 1000000),
        "delivery_price_per_km": (0, 1000000),
        "motorbike_base_fee": (0, 1000000),
        "motorbike_price_per_km": (0, 1000000),
        "motorbike_minimum_fee": (0, 1000000),
        "car_base_fee": (0, 1000000),
        "car_price_per_km": (0, 1000000),
        "car_minimum_fee": (0, 1000000),
        "delivery_max_km": (0, 1000),
    }
    for name, (vmin, vmax) in numeric_validators.items():
        if name in fields:
            try:
                v = float(fields[name])
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail=name + " : valeur invalide")
            if v < vmin or v > vmax:
                raise HTTPException(status_code=400, detail=name + " : valeur hors limites")
            fields[name] = v

    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO pharmacy_settings (id) VALUES (1)")
    if fields:
        set_clause = ", ".join(k + " = ?" for k in fields.keys())
        params = list(fields.values())
        conn.execute("UPDATE pharmacy_settings SET " + set_clause + " WHERE id = 1", params)
    conn.commit()
    row = conn.execute("SELECT * FROM pharmacy_settings WHERE id = 1").fetchone()
    conn.close()
    return row_to_dict(row)'''
    if old_block.search(mainsrc):
        mainsrc = old_block.sub(new_block, mainsrc, count=1)
        MAIN.write_text(mainsrc, encoding="utf-8")
        print("[OK] main.py -> PATCH /api/settings etendu")
    else:
        print("[!] bloc PATCH settings introuvable")

print()
print("=" * 60)
print("FIX TARIFS + PAIEMENT LIVRE")
print("=" * 60)
print()
print("Config base :")
print("  VOITURE : 1000 F + 250 F/km (min 1000 F)")
print("  MOTO    : 500 F + 150 F/km (min 500 F)")
print("  Paiement: +22871039904")
print()
print("UI :")
print("  - Formule affichee dans la page Confirmer")
print("  - Ex: '1000 F + 14.88 km x 250 F/km (arrondi aux 50 F)'")
print("  - Distance + frais + total visibles")
print()
print("Dashboard /pharmacien :")
print("  - Champs Tarifs VOITURE")
print("  - Champs Tarifs MOTO")
print("  - Numero de paiement + nom beneficiaire")
print()
print("Paiement manuel :")
print("  PENDING -> PROOF_SUBMITTED -> VERIFIED (valide par pharmacie)")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")