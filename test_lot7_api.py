# -*- coding: utf-8 -*-
"""Test complet des nouvelles routes Lot 7 (produits + stock)."""
import json, urllib.request, urllib.error, http.cookiejar, sys

BASE = "http://127.0.0.1:8000"

def login(email, pwd):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    req = urllib.request.Request(
        BASE + "/api/auth/login",
        data=json.dumps({"email": email, "password": pwd}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    op.open(req, timeout=10)
    return op

def call(op, method, path, body=None, is_json=True):
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if is_json and body else {}
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        r = op.open(req, timeout=10)
        txt = r.read().decode()
        return r.status, json.loads(txt) if txt else {}
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except:
            return e.code, {}

results = []
def check(label, ok, detail=""):
    results.append((label, ok))
    print(f"  [{'OK' if ok else '!!'}] {label}  {detail}")

print("=" * 70)
print("TESTS LOT 7 - API CATALOGUE + STOCK")
print("=" * 70)

# Login pharmacien
print("\n[1] Login pharmacien")
try:
    op = login("pharmacien@test.tg", "Test1234")
    print("  [OK] Connecte")
except Exception as e:
    print(f"  [!!] Echec : {e}"); sys.exit(1)

# --- PRODUITS ---
print("\n[2] CREER un produit")
code, data = call(op, "POST", "/api/admin/products", {
    "name": "TEST-PRODUIT-LOT7",
    "presentation": "Boite de 10",
    "description": "Produit de test",
    "category": "Test",
    "price": 1500,
    "requires_prescription": 0,
    "stock_quantity": 0,
    "stock_min_threshold": 5,
})
check("POST /api/admin/products -> 200", code == 200, f"recu {code}")
new_id = data.get("id") if code == 200 else None
check("ID retourne", new_id is not None, f"id={new_id}")

# --- MODIFIER ---
print("\n[3] MODIFIER le produit")
code, data = call(op, "PATCH", f"/api/admin/products/{new_id}", {
    "price": 2000,
    "description": "Modifie par test"
})
check("PATCH -> 200", code == 200, f"recu {code}")
check("Prix mis a jour", data.get("price") == 2000, f"price={data.get('price')}")

# --- MOUVEMENT STOCK IN ---
print("\n[4] MOUVEMENT STOCK : IN 10")
code, data = call(op, "POST", "/api/admin/stock/movements", {
    "product_id": new_id,
    "type": "IN",
    "quantity": 10,
    "reason": "Reception test",
    "reference": "LOT-TEST-001"
})
check("POST movements IN -> 200", code == 200, f"recu {code}")
check("Nouvelle quantite = 10", data.get("new_quantity") == 10, f"qty={data.get('new_quantity')}")

# --- MOUVEMENT STOCK OUT ---
print("\n[5] MOUVEMENT STOCK : OUT 3")
code, data = call(op, "POST", "/api/admin/stock/movements", {
    "product_id": new_id,
    "type": "OUT",
    "quantity": 3,
    "reason": "Vente test"
})
check("POST movements OUT -> 200", code == 200, f"recu {code}")
check("Nouvelle quantite = 7", data.get("new_quantity") == 7, f"qty={data.get('new_quantity')}")

# --- REFUS OUT > stock ---
print("\n[6] REFUS OUT > stock disponible")
code, data = call(op, "POST", "/api/admin/stock/movements", {
    "product_id": new_id,
    "type": "OUT",
    "quantity": 999,
    "reason": "Test refus"
})
check("OUT excessif refuse (400)", code == 400, f"recu {code}")

# --- REFUS ADJUST sans motif ---
print("\n[7] REFUS ADJUST sans motif")
code, data = call(op, "POST", "/api/admin/stock/movements", {
    "product_id": new_id,
    "type": "ADJUST",
    "quantity": 5,
    "reason": ""
})
check("ADJUST sans motif refuse (400)", code == 400, f"recu {code}")

# --- HISTORIQUE ---
print("\n[8] HISTORIQUE des mouvements")
code, data = call(op, "GET", f"/api/admin/stock/movements?product_id={new_id}")
check("GET movements -> 200", code == 200, f"recu {code}")
check("2 mouvements enregistres", len(data) == 2, f"n={len(data)}")

# --- ALERTES ---
print("\n[9] ALERTES stock")
code, data = call(op, "GET", "/api/admin/stock/alerts")
check("GET alerts -> 200", code == 200, f"recu {code}")
check("Structure complete", all(k in data for k in ["rupture", "low_stock", "expiring_soon"]))

# --- LOT ---
print("\n[10] CREER un lot avec peremption")
code, data = call(op, "POST", "/api/admin/stock/lots", {
    "product_id": new_id,
    "lot_number": "LOT-2026-001",
    "expiry_date": "2027-12-31",
    "quantity": 7
})
check("POST lot -> 200", code == 200, f"recu {code}")

# --- ARCHIVAGE ---
print("\n[11] ARCHIVER le produit (pas de suppression)")
code, data = call(op, "DELETE", f"/api/admin/products/{new_id}")
check("DELETE -> 200", code == 200, f"recu {code}")
check("Flag archived=True", data.get("archived") is True)

# Verifier qu'il est inactif
code, data = call(op, "GET", "/api/admin/stock")
inactive = [p for p in data if p["id"] == new_id]
check("Produit absent du stock actif", len(inactive) == 0)

# --- SECURITE : patient ne peut pas ---
print("\n[12] SECURITE : patient bloque")
try:
    op_p = login("patient@test.tg", "Test1234")
    code, _ = call(op_p, "POST", "/api/admin/products", {"name": "HACK", "price": 100})
    check("Patient bloque (403)", code == 403, f"recu {code}")
    code, _ = call(op_p, "POST", "/api/admin/stock/movements",
                   {"product_id": 1, "type": "IN", "quantity": 10})
    check("Patient bloque stock (403)", code == 403, f"recu {code}")
except Exception as e:
    check("Patient test", False, str(e))

# --- REFUS sans auth ---
print("\n[13] SECURITE : non-auth bloque")
try:
    r = urllib.request.urlopen(BASE + "/api/admin/products", timeout=5)
    check("Non-auth bloque", False, f"recu {r.status}")
except urllib.error.HTTPError as e:
    check("Non-auth bloque (401/403)", e.code in (401, 403), f"recu {e.code}")

# --- RESUME ---
print()
print("=" * 70)
ok = sum(1 for _, s in results if s)
print(f"RESULTAT : {ok}/{len(results)} tests OK")
print("=" * 70)
for label, s in results:
    print(f"  [{'OK' if s else '!!'}] {label}")

sys.exit(0 if ok == len(results) else 1)