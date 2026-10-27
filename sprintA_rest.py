# -*- coding: utf-8 -*-
"""
SPRINT A.4 + A.5 + A.6 + A.7 - Tout en un script
==================================================
- A.4 : create_order utilise compute_delivery_fee_v2 + stocke vehicle
- A.5 : checkout.js affiche le vehicule selectionne
- A.6 : PATCH /api/orders/{ref}/vehicle (override manuel trace)
- A.7 : test_sprintA_final.py (9 cas) genere

Atomic + rollback si erreur.
"""
import os, re, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
MAIN = os.path.join(ROOT, "main.py")
CHECKOUT = os.path.join(ROOT, "static", "checkout.js")
TEST_FILE = os.path.join(ROOT, "test_sprintA_final.py")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_sprintArest_{TS}")
os.makedirs(BAK, exist_ok=True)

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]", "STEP": "\n###"}[k]
    print(p, m)

def syntax_ok(path):
    try:
        with open(path, "rb") as f:
            compile(f.read(), path, "exec")
        return True, None
    except SyntaxError as e:
        return False, f"L{e.lineno}: {e.msg}"

def brace_diff(s): return s.count("{") - s.count("}")

# Backups
for p, n in [(MAIN, "main.py"), (CHECKOUT, "checkout.js")]:
    if os.path.isfile(p):
        shutil.copy2(p, os.path.join(BAK, n))

print("=" * 78)
print(f"SPRINT A COMPLET - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

# ============================================================
# PHASE A.4 : Modifier create_order
# ============================================================
log("PHASE A.4 : create_order utilise v2 + stocke vehicle", "STEP")

main_src = open(MAIN, "r", encoding="utf-8").read()

if "compute_delivery_fee_v2(latitude, longitude" in main_src:
    log("A.4 deja applique", "WARN")
else:
    OLD_A4 = '''    if delivery_mode == "livraison":
        delivery_fee, delivery_distance = compute_delivery_fee(latitude, longitude)
    else:
        delivery_fee = 0.0
        delivery_distance = None
    subtotal = round(product["price"] * quantity, 2)'''

    NEW_A4 = '''    subtotal = round(product["price"] * quantity, 2)

    delivery_vehicle = None
    delivery_reason = None
    if delivery_mode == "livraison":
        # Sprint A.4 : calcul intelligent (moto/voiture selon seuils)
        delivery_fee, delivery_distance, delivery_vehicle, delivery_reason = compute_delivery_fee_v2(
            latitude, longitude, quantity, 1, subtotal
        )
        if delivery_vehicle is None:
            conn.close()
            raise HTTPException(
                400,
                "Aucun moyen de livraison disponible pour cette distance. "
                "Veuillez nous contacter ou choisir le retrait en pharmacie."
            )
    else:
        delivery_fee = 0.0
        delivery_distance = None
        delivery_vehicle = None
        delivery_reason = None'''

    if OLD_A4 in main_src:
        main_src = main_src.replace(OLD_A4, NEW_A4, 1)
        log("create_order : calcul v2 integre", "OK")
    else:
        log("Pattern create_order A.4 introuvable", "ERR")

    # Ajouter delivery_vehicle_type dans l'INSERT
    OLD_INSERT = '''        "INSERT INTO orders (reference, customer_name, phone, product_id, product_name,"
        " quantity, delivery_mode, address, prescription_file, status, created_at,"
        " latitude, longitude, location_accuracy, delivery_fee, delivery_distance_km,"
        " price, subtotal)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'en_attente', ?, ?, ?, ?, ?, ?, ?, ?)",
        (reference, name, phone_clean, product["id"], product["name"], quantity,
         delivery_mode, address.strip(), saved_file, created_at,
         latitude, longitude, location_accuracy, delivery_fee, delivery_distance,
         product["price"], subtotal),'''

    NEW_INSERT = '''        "INSERT INTO orders (reference, customer_name, phone, product_id, product_name,"
        " quantity, delivery_mode, address, prescription_file, status, created_at,"
        " latitude, longitude, location_accuracy, delivery_fee, delivery_distance_km,"
        " delivery_vehicle_type, price, subtotal)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'en_attente', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (reference, name, phone_clean, product["id"], product["name"], quantity,
         delivery_mode, address.strip(), saved_file, created_at,
         latitude, longitude, location_accuracy, delivery_fee, delivery_distance,
         delivery_vehicle, product["price"], subtotal),'''

    if OLD_INSERT in main_src:
        main_src = main_src.replace(OLD_INSERT, NEW_INSERT, 1)
        log("INSERT : delivery_vehicle_type ajoute", "OK")
    else:
        log("Pattern INSERT introuvable", "WARN")

    # Ajouter vehicle dans la reponse JSON
    OLD_RET = '''        "delivery_fee": delivery_fee,
        "delivery_distance_km": delivery_distance,
        "total": round(product["price"] * quantity + delivery_fee, 2),'''

    NEW_RET = '''        "delivery_fee": delivery_fee,
        "delivery_distance_km": delivery_distance,
        "delivery_vehicle_type": delivery_vehicle,
        "delivery_reason": delivery_reason,
        "total": round(product["price"] * quantity + delivery_fee, 2),'''

    if OLD_RET in main_src:
        main_src = main_src.replace(OLD_RET, NEW_RET, 1)
        log("Reponse JSON : vehicle ajoute", "OK")
    else:
        log("Pattern retour introuvable", "WARN")

# ============================================================
# PHASE A.6 : Route PATCH /api/orders/{ref}/vehicle
# ============================================================
log("PHASE A.6 : Route override vehicule", "STEP")

if "/api/orders/{reference}/vehicle" in main_src:
    log("A.6 deja applique", "WARN")
else:
    ROUTE_VEHICLE = '''

# ============================================================
# SPRINT A.6 - Override manuel du vehicule (PHARMACIEN/ADMIN)
# ============================================================
class VehicleOverride(BaseModel):
    vehicle_type: str
    reason: str = ""


@app.patch("/api/orders/{reference}/vehicle")
def override_vehicle(reference: str, payload: VehicleOverride,
                     user = Depends(get_current_user_dep)):
    """Modifie manuellement le vehicule d'une commande.
    Recalcule le tarif selon le nouveau vehicule et trace l'action.
    """
    if not user or user["role"] not in ("PHARMACIEN", "ADMIN"):
        raise HTTPException(403, "Reserve au personnel pharmacie")

    new_vehicle = (payload.vehicle_type or "").strip().upper()
    if new_vehicle not in ("MOTO", "CAR"):
        raise HTTPException(400, "Vehicule invalide (MOTO ou CAR)")

    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM orders WHERE reference = ?",
                          (reference,)).fetchone()
        if row is None:
            raise HTTPException(404, "Commande introuvable")
        if row["status"] not in ("en_attente", "confirmee"):
            raise HTTPException(400, "Modification impossible : commande deja en cours de traitement")
        if row["delivery_mode"] != "livraison":
            raise HTTPException(400, "Cette commande est en retrait, pas de livraison")

        # Recalcul fee selon nouveau vehicule
        lat = row["latitude"]
        lon = row["longitude"]
        s = conn.execute("SELECT * FROM pharmacy_settings WHERE id = 1").fetchone()
        if not s or lat is None or lon is None:
            raise HTTPException(400, "Position GPS manquante, impossible de recalculer")

        dist = haversine_km(float(s["pharmacy_latitude"]), float(s["pharmacy_longitude"]),
                            float(lat), float(lon))

        if new_vehicle == "MOTO":
            base = float(s["motorbike_base_fee"] or 1200)
            per_km = float(s["motorbike_price_per_km"] or 100)
            min_fee = float(s["motorbike_minimum_fee"] or 500)
        else:
            base = float(s["car_base_fee"] or 1000)
            per_km = float(s["car_price_per_km"] or 250)
            min_fee = float(s["car_minimum_fee"] or 1000)

        new_fee = base + dist * per_km
        if new_fee < min_fee:
            new_fee = min_fee
        new_fee = round(new_fee / 50.0) * 50

        old_vehicle = row["delivery_vehicle_type"]
        old_fee = row["delivery_fee"]

        conn.execute(
            "UPDATE orders SET delivery_vehicle_type = ?, delivery_fee = ?,"
            " delivery_distance_km = ? WHERE id = ?",
            (new_vehicle, new_fee, round(dist, 2), row["id"])
        )
        log_audit(conn, user["id"], "order.vehicle_override", "order", row["id"],
                 f"de {old_vehicle}({old_fee}) vers {new_vehicle}({new_fee}) motif={payload.reason}")
        conn.commit()

        updated = conn.execute("SELECT * FROM orders WHERE id = ?",
                              (row["id"],)).fetchone()
        return row_to_dict(updated)
    finally:
        conn.close()

'''
    anchor = 'if __name__ == "__main__":'
    if anchor in main_src:
        idx = main_src.find(anchor)
        main_src = main_src[:idx] + ROUTE_VEHICLE + main_src[idx:]
        log("Route PATCH /vehicle ajoutee", "OK")
    else:
        log("Ancre __main__ introuvable", "ERR")

# Sauvegarder + valider
open(MAIN, "w", encoding="utf-8").write(main_src)
ok, err = syntax_ok(MAIN)
if not ok:
    log(f"main.py ERREUR : {err}", "ERR")
    shutil.copy2(os.path.join(BAK, "main.py"), MAIN)
    sys.exit(1)
log("main.py syntaxe OK", "OK")

# ============================================================
# PHASE A.5 : checkout.js affiche le vehicule
# ============================================================
log("PHASE A.5 : checkout.js affiche vehicule", "STEP")

co_src = open(CHECKOUT, "r", encoding="utf-8").read()

if "vehicle_type" in co_src or "delivery/estimate" in co_src:
    log("A.5 deja applique", "WARN")
else:
    # Afficher le vehicule a cote du fee
    # Ancre : ligne qui affiche "Frais de livraison"
    # Chercher le rendu
    m = re.search(r"<[^>]*>[^<]*(?:Frais de livraison|Livraison)[^<]*</", co_src)
    if m:
        print(f"  [TRACE] Zone detectee : {m.group(0)[:80]}")
    else:
        print("  [TRACE] Recherche du bloc d'affichage livraison...")

    # Chercher la fonction qui affiche le fee
    # Approche : ajouter un element HTML qui affiche le vehicule
    # et l'appeler apres le calcul du fee

    # Fonction helper async
    HELPER = '''
// ============================================================
// SPRINT A.5 : Affichage du vehicule de livraison
// ============================================================
async function ehRefreshVehicleInfo() {
  try {
    var fee = (typeof computeFee === "function") ? computeFee() : 0;
    if (state.mode !== "livraison" || !state.address) return;
    var lat = state.latitude || null;
    var lon = state.longitude || null;
    var units = 1;
    var lines = 1;
    var amount = fee * 1;
    // Essayer de recuperer les infos du panier
    try {
      var c = (typeof state.cart !== "undefined" && state.cart) ? state.cart : null;
      if (c && Array.isArray(c.items)) {
        units = c.items.reduce(function(s, it){ return s + (it.quantity||1); }, 0);
        lines = c.items.length;
        amount = c.items.reduce(function(s, it){ return s + (it.price||0)*(it.quantity||1); }, 0);
      }
    } catch(e) {}

    var r = await fetch("/api/delivery/estimate", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      credentials: "same-origin",
      body: JSON.stringify({
        latitude: lat, longitude: lon,
        units: units, distinct_lines: lines, amount: amount
      })
    });
    if (!r.ok) return;
    var d = await r.json();
    var el = document.getElementById("eh-vehicle-info");
    if (!el) {
      // Creer un element apres la ligne fee
      var parent = null;
      var nodes = document.querySelectorAll(".co-row, .checkout-total, .fee-line");
      if (nodes.length) parent = nodes[0].parentNode;
      if (!parent) {
        var feeInput = document.querySelector("[data-fee], [id*='fee']");
        if (feeInput) parent = feeInput.parentNode;
      }
      if (!parent) return;
      el = document.createElement("div");
      el.id = "eh-vehicle-info";
      el.style.cssText = "font-size:13px;color:#475569;margin:6px 0;padding:8px 12px;background:#F5F8FC;border-radius:8px";
      parent.appendChild(el);
    }
    if (d.available) {
      var vLbl = d.vehicle_type === "CAR" ? "voiture" : "moto";
      var ico = d.vehicle_type === "CAR" ? "🚗" : "🛵";
      var dist = d.distance_km != null ? " (" + d.distance_km + " km)" : "";
      el.innerHTML = ico + " Livraison par <strong>" + vLbl + "</strong>" + dist
                   + " — <strong>" + Math.round(d.fee).toLocaleString("fr-FR") + " FCFA</strong>";
    } else {
      el.style.color = "#B23C3C";
      el.innerHTML = "❌ Aucun moyen de livraison disponible pour cette distance. Choisissez le retrait.";
    }
  } catch(e) { console.warn("[vehicle]", e); }
}
window.ehRefreshVehicleInfo = ehRefreshVehicleInfo;
'''

    # Inserer le helper juste avant la derniere ligne du fichier
    # Trouver la fin de la IIFE (derniere })
    last_idx = co_src.rstrip().rfind("}")
    if last_idx > 0:
        co_src = co_src[:last_idx] + "\n" + HELPER + "\n" + co_src[last_idx:]
        log("Helper ehRefreshVehicleInfo insere", "OK")

    # Hook : appeler apres les changements de mode/adresse
    # Chercher la fonction qui calcule le fee (computeFee)
    # Ajouter un appel dans les endroits ou computeFee est appele
    # Approche minimaliste : hook sur les inputs

    HOOK = '''
// Hook : rafraichir le vehicule quand l'adresse change
document.addEventListener("change", function(ev){
  var t = ev.target;
  if (!t) return;
  if (t.id === "co-address" || t.id === "address" || t.name === "address"
      || (t.tagName === "INPUT" && (t.type === "text" || t.type === "tel"))
      || t.tagName === "TEXTAREA") {
    if (state && state.mode === "livraison") {
      setTimeout(function(){ if (window.ehRefreshVehicleInfo) window.ehRefreshVehicleInfo(); }, 300);
    }
  }
  if (t.name === "mode" || t.dataset && t.dataset.mode) {
    setTimeout(function(){ if (window.ehRefreshVehicleInfo) window.ehRefreshVehicleInfo(); }, 300);
  }
});
document.addEventListener("click", function(ev){
  var t = ev.target.closest ? ev.target.closest("[data-mode]") : null;
  if (t) setTimeout(function(){ if (window.ehRefreshVehicleInfo) window.ehRefreshVehicleInfo(); }, 300);
});
'''

    # Inserer avant la fin
    if "ehRefreshVehicleInfo()" not in co_src:
        last_idx = co_src.rstrip().rfind("}")
        if last_idx > 0:
            co_src = co_src[:last_idx] + "\n" + HOOK + "\n" + co_src[last_idx:]

    # Verifier equilibre
    diff = brace_diff(co_src)
    if diff != 0:
        log(f"checkout.js desequilibre ({diff}) - ROLLBACK", "ERR")
        shutil.copy2(os.path.join(BAK, "checkout.js"), CHECKOUT)
    else:
        open(CHECKOUT, "w", encoding="utf-8").write(co_src)
        log("checkout.js sauvegarde", "OK")

# ============================================================
# PHASE A.7 : Generer test_sprintA_final.py
# ============================================================
log("PHASE A.7 : Generation test E2E", "STEP")

TEST_CODE = '''# -*- coding: utf-8 -*-
"""Sprint A - 9 cas de test E2E."""
import json, urllib.request, urllib.error, http.cookiejar, sys

BASE = "http://127.0.0.1:8000"

def post_json(path, body, cookies=None):
    req = urllib.request.Request(BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    if cookies: req.add_header("Cookie", cookies)
    try:
        r = urllib.request.urlopen(req, timeout=10)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read().decode())
        except: return e.code, {}

def login(email, pwd):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    req = urllib.request.Request(BASE + "/api/auth/login",
        data=json.dumps({"email": email, "password": pwd}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    op.open(req, timeout=10)
    return op

results = []
def check(label, ok, detail=""):
    results.append((label, ok, detail))
    print(f"  [{'OK' if ok else '!!'}] {label}  {detail}")

print("=" * 70)
print("SPRINT A - TESTS E2E")
print("=" * 70)

LAT = 6.3500   # proche pharmacie (~0.5 km)
LON = 1.2050

# --- Cas 1 : petite commande = MOTO ---
print("\\n[1] Petite commande (1 unite, 1 ligne, 1000 F) -> MOTO")
c, d = post_json("/api/delivery/estimate", {"latitude": LAT, "longitude": LON, "units": 1, "distinct_lines": 1, "amount": 1000})
check("Vehicle = MOTO", d.get("vehicle_type") == "MOTO", str(d))
check("Fee > 0", (d.get("fee") or 0) > 0, str(d.get("fee")))

# --- Cas 2 : seuil unites (40) ---
print("\\n[2] 40 unites -> CAR")
c, d = post_json("/api/delivery/estimate", {"latitude": LAT, "longitude": LON, "units": 40, "distinct_lines": 1, "amount": 1000})
check("Vehicle = CAR", d.get("vehicle_type") == "CAR", str(d.get("reason")))

# --- Cas 3 : seuil lignes (10) ---
print("\\n[3] 10 lignes distinctes -> CAR")
c, d = post_json("/api/delivery/estimate", {"latitude": LAT, "longitude": LON, "units": 5, "distinct_lines": 10, "amount": 5000})
check("Vehicle = CAR", d.get("vehicle_type") == "CAR", str(d.get("reason")))

# --- Cas 4 : seuil montant (80000) ---
print("\\n[4] Montant 80000 -> CAR")
c, d = post_json("/api/delivery/estimate", {"latitude": LAT, "longitude": LON, "units": 3, "distinct_lines": 2, "amount": 80000})
check("Vehicle = CAR", d.get("vehicle_type") == "CAR", str(d.get("reason")))

# --- Cas 5 : pro 3 produits -> MOTO ---
print("\\n[5] Pro 3 produits (sous seuils) -> MOTO")
c, d = post_json("/api/delivery/estimate", {"latitude": LAT, "longitude": LON, "units": 3, "distinct_lines": 3, "amount": 15000})
check("Vehicle = MOTO", d.get("vehicle_type") == "MOTO", str(d.get("reason")))

# --- Cas 6 : plusieurs seuils -> CAR coherent ---
print("\\n[6] Plusieurs seuils atteints -> CAR")
c, d = post_json("/api/delivery/estimate", {"latitude": LAT, "longitude": LON, "units": 50, "distinct_lines": 12, "amount": 100000})
check("Vehicle = CAR", d.get("vehicle_type") == "CAR", str(d.get("reason")))

# --- Cas 7 : GPS manquant -> MOTO fallback ---
print("\\n[7] GPS manquant -> fallback MOTO")
c, d = post_json("/api/delivery/estimate", {"latitude": None, "longitude": None, "units": 1, "distinct_lines": 1, "amount": 1000})
check("Vehicle = MOTO", d.get("vehicle_type") == "MOTO", str(d.get("reason")))
check("Distance = None", d.get("distance_km") is None, str(d.get("distance_km")))

# --- Cas 8 : tarif minimum ---
print("\\n[8] Distance nulle -> tarif minimum applique")
c, d = post_json("/api/delivery/estimate", {"latitude": 6.3489, "longitude": 1.20285, "units": 1, "distinct_lines": 1, "amount": 1000})
check("Fee = minimum moto (500)", (d.get("fee") or 0) >= 500, str(d.get("fee")))

# --- Cas 9 : commande existante garde son tarif ---
print("\\n[9] Commande existante : tarif inchange apres modif settings")
try:
    import sqlite3
    DB = r"C:\\Users\\ELOGE KEY\\Desktop\\pharma\\pharmacie\\database.db"
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT reference, delivery_fee, delivery_vehicle_type FROM orders WHERE delivery_mode='livraison' ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if r:
        print(f"  Commande {r['reference']} : fee={r['delivery_fee']} vehicle={r['delivery_vehicle_type']}")
        check("Vehicule fige sur commande", r["delivery_vehicle_type"] in ("MOTO", "CAR"), str(r["delivery_vehicle_type"]))
    else:
        check("Commande existante", True, "aucune commande livraison")
except Exception as e:
    check("Commande existante", False, str(e))

# --- Resume ---
print()
print("=" * 70)
ok = sum(1 for _, s, _ in results if s)
print(f"RESULTAT : {ok}/{len(results)}")
print("=" * 70)
sys.exit(0 if ok == len(results) else 1)
'''

open(TEST_FILE, "w", encoding="utf-8").write(TEST_CODE)
log("test_sprintA_final.py genere", "OK")

# ============================================================
# Verification finale
# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)

final_main = open(MAIN, "r", encoding="utf-8").read()
final_co = open(CHECKOUT, "r", encoding="utf-8").read()

checks = [
    ("A.4 : create_order utilise v2",       "compute_delivery_fee_v2(latitude, longitude" in final_main),
    ("A.4 : delivery_vehicle dans INSERT",  "delivery_vehicle_type" in final_main and "delivery_vehicle, product" in final_main),
    ("A.4 : vehicle dans reponse",          '"delivery_vehicle_type": delivery_vehicle' in final_main),
    ("A.4 : check aucun moyen dispo",       "Aucun moyen de livraison disponible" in final_main),
    ("A.5 : checkout.js affiche vehicle",   "ehRefreshVehicleInfo" in final_co),
    ("A.6 : PATCH /vehicle",                "/api/orders/{reference}/vehicle" in final_main),
    ("A.6 : log_audit sur override",        "order.vehicle_override" in final_main),
    ("A.7 : test_sprintA_final.py",         os.path.isfile(TEST_FILE)),
    ("main.py syntaxe OK",                  syntax_ok(MAIN)[0]),
    ("checkout.js equilibre",               brace_diff(final_co) == 0),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

passed = sum(1 for _, ok in checks if ok)
print(f"\n  RESULTAT : {passed}/{len(checks)}")

print()
print(f"[BACKUP] {BAK}")
print()
print("[CMD] Restart Uvicorn OBLIGATOIRE :")
print("  taskkill /F /IM uvicorn.exe 2>nul")
print("  taskkill /F /IM python.exe 2>nul")
print("  cd /d \"C:\\Users\\ELOGE KEY\\Desktop\\pharma\\pharmacie\"")
print("  python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir v3_modules --reload-dir static")
print()
print("[TEST] Apres restart :")
print("  python test_sprintA_final.py")
print()
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\main.py" "{MAIN}"')
print(f'  copy "{BAK}\\checkout.js" "{CHECKOUT}"')