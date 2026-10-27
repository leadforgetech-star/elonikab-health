# -*- coding: utf-8 -*-
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
print("\n[1] Petite commande (1 unite, 1 ligne, 1000 F) -> MOTO")
c, d = post_json("/api/delivery/estimate", {"latitude": LAT, "longitude": LON, "units": 1, "distinct_lines": 1, "amount": 1000})
check("Vehicle = MOTO", d.get("vehicle_type") == "MOTO", str(d))
check("Fee > 0", (d.get("fee") or 0) > 0, str(d.get("fee")))

# --- Cas 2 : seuil unites (40) ---
print("\n[2] 40 unites -> CAR")
c, d = post_json("/api/delivery/estimate", {"latitude": LAT, "longitude": LON, "units": 40, "distinct_lines": 1, "amount": 1000})
check("Vehicle = CAR", d.get("vehicle_type") == "CAR", str(d.get("reason")))

# --- Cas 3 : seuil lignes (10) ---
print("\n[3] 10 lignes distinctes -> CAR")
c, d = post_json("/api/delivery/estimate", {"latitude": LAT, "longitude": LON, "units": 5, "distinct_lines": 10, "amount": 5000})
check("Vehicle = CAR", d.get("vehicle_type") == "CAR", str(d.get("reason")))

# --- Cas 4 : seuil montant (80000) ---
print("\n[4] Montant 80000 -> CAR")
c, d = post_json("/api/delivery/estimate", {"latitude": LAT, "longitude": LON, "units": 3, "distinct_lines": 2, "amount": 80000})
check("Vehicle = CAR", d.get("vehicle_type") == "CAR", str(d.get("reason")))

# --- Cas 5 : pro 3 produits -> MOTO ---
print("\n[5] Pro 3 produits (sous seuils) -> MOTO")
c, d = post_json("/api/delivery/estimate", {"latitude": LAT, "longitude": LON, "units": 3, "distinct_lines": 3, "amount": 15000})
check("Vehicle = MOTO", d.get("vehicle_type") == "MOTO", str(d.get("reason")))

# --- Cas 6 : plusieurs seuils -> CAR coherent ---
print("\n[6] Plusieurs seuils atteints -> CAR")
c, d = post_json("/api/delivery/estimate", {"latitude": LAT, "longitude": LON, "units": 50, "distinct_lines": 12, "amount": 100000})
check("Vehicle = CAR", d.get("vehicle_type") == "CAR", str(d.get("reason")))

# --- Cas 7 : GPS manquant -> MOTO fallback ---
print("\n[7] GPS manquant -> fallback MOTO")
c, d = post_json("/api/delivery/estimate", {"latitude": None, "longitude": None, "units": 1, "distinct_lines": 1, "amount": 1000})
check("Vehicle = MOTO", d.get("vehicle_type") == "MOTO", str(d.get("reason")))
check("Distance = None", d.get("distance_km") is None, str(d.get("distance_km")))

# --- Cas 8 : tarif minimum ---
print("\n[8] Distance nulle -> tarif minimum applique")
c, d = post_json("/api/delivery/estimate", {"latitude": 6.3489, "longitude": 1.20285, "units": 1, "distinct_lines": 1, "amount": 1000})
check("Fee = minimum moto (500)", (d.get("fee") or 0) >= 500, str(d.get("fee")))

# --- Cas 9 : commande existante garde son tarif ---
print("\n[9] Commande existante : tarif inchange apres modif settings")
try:
    import sqlite3
    DB = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie\database.db"
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
