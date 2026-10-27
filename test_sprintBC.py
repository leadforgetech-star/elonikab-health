# -*- coding: utf-8 -*-
"""Tests Sprint B + C - Backend compta + stock avance."""
import json, urllib.request, urllib.error, http.cookiejar, sys

BASE = "http://127.0.0.1:8000"

def login(email, pwd):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    req = urllib.request.Request(BASE + "/api/auth/login",
        data=json.dumps({"email": email, "password": pwd}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    op.open(req, timeout=10)
    return op

def call(op, method, path, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(BASE + path, data=data,
        headers={"Content-Type": "application/json"} if body else {},
        method=method)
    try:
        r = op.open(req, timeout=10)
        txt = r.read().decode()
        return r.status, json.loads(txt) if txt else {}
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read().decode())
        except: return e.code, {}

results = []
def check(label, ok, detail=""):
    results.append((label, ok))
    print(f"  [{'OK' if ok else '!!'}] {label}  {detail}")

print("=" * 70)
print("SPRINT B+C - TESTS BACKEND")
print("=" * 70)

# Login
try:
    op = login("pharmacien@test.tg", "Test1234")
    print("  [OK] Login pharmacien")
except Exception as e:
    print(f"  [!!] Login : {e}"); sys.exit(1)

# === COMPTABILITE ===
print("\n[1] Depense : creer")
c, d = call(op, "POST", "/api/compta/expenses", {
    "category": "Loyer", "label": "Loyer Octobre", "amount": 50000,
    "expense_date": "2026-10-01", "payment_method": "virement"
})
check("POST /expenses -> 200", c == 200, str(c))
exp_id = d.get("id") if c == 200 else None

print("\n[2] Depense : liste")
c, d = call(op, "GET", "/api/compta/expenses?month=2026-10")
check("GET /expenses -> 200", c == 200)
check("Depense trouvee", any(e["id"] == exp_id for e in d) if isinstance(d, list) else False)

print("\n[3] Bilan mensuel")
c, d = call(op, "GET", "/api/compta/summary?month=2026-10")
check("GET /summary -> 200", c == 200)
check("depenses >= 50000", (d.get("depenses") or 0) >= 50000, str(d.get("depenses")))
check("benefice present", "benefice" in d, str(d.get("benefice")))

print("\n[4] Journal caisse")
c, d = call(op, "GET", "/api/compta/journal")
check("GET /journal -> 200", c == 200)
check("Au moins 1 ecriture", isinstance(d, list) and len(d) >= 1)

print("\n[5] Depense : supprimer")
c, d = call(op, "DELETE", f"/api/compta/expenses/{exp_id}")
check("DELETE /expenses -> 200", c == 200)

# === STOCK AVANCE ===
print("\n[6] Valorisation stock")
c, d = call(op, "GET", "/api/admin/stock/valuation")
check("GET /valuation -> 200", c == 200)
check("total_purchase present", "total_purchase" in d)
check("items present", "items" in d and isinstance(d["items"], list))

print("\n[7] Previsions stock")
c, d = call(op, "GET", "/api/admin/stock/forecast?days=30")
check("GET /forecast -> 200", c == 200)
check("items present", "items" in d and isinstance(d["items"], list))

print("\n[8] Fournisseur : creer")
c, d = call(op, "POST", "/api/admin/suppliers", {
    "name": "Test Fournisseur SARL", "phone": "22890000000"
})
check("POST /suppliers -> 200", c == 200)
sup_id = d.get("id") if c == 200 else None

print("\n[9] Fournisseur : liste")
c, d = call(op, "GET", "/api/admin/suppliers")
check("GET /suppliers -> 200", c == 200)
check("Fournisseur present", isinstance(d, list) and any(s["id"] == sup_id for s in d))

print("\n[10] Commande achat : creer")
c, d = call(op, "POST", "/api/admin/purchase-orders", {"supplier_id": sup_id})
check("POST /purchase-orders -> 200", c == 200)
po_id = d.get("id") if c == 200 else None

print("\n[11] Commande achat : ajouter item")
if po_id:
    c, d = call(op, "POST", f"/api/admin/purchase-orders/{po_id}/items", {
        "product_id": 1, "quantity": 10, "unit_price": 500
    })
    check("POST /items -> 200", c == 200)

print("\n[12] Commande achat : receptionner")
if po_id:
    c, d = call(op, "PATCH", f"/api/admin/purchase-orders/{po_id}/receive", {})
    check("PATCH /receive -> 200", c == 200)
    check("received > 0", (d.get("received") or 0) > 0)

print("\n[13] Dashboard compta")
c, d = call(op, "GET", "/api/compta/dashboard")
check("GET /dashboard -> 200", c == 200)
check("recettes present", "recettes" in d)
check("stock_value present", "stock_value" in d)
check("dormant_products present", "dormant_products" in d)

# === SECURITE ===
print("\n[14] Securite patient")
try:
    op_p = login("patient@test.tg", "Test1234")
    c, _ = call(op_p, "GET", "/api/compta/expenses")
    check("Patient bloque compta", c == 403, str(c))
    c, _ = call(op_p, "GET", "/api/admin/suppliers")
    check("Patient bloque fournisseurs", c == 403, str(c))
except Exception as e:
    check("Patient test", False, str(e))

# === RESUME ===
print()
print("=" * 70)
ok = sum(1 for _, s in results if s)
print(f"RESULTAT : {ok}/{len(results)}")
print("=" * 70)
for label, s in results:
    print(f"  [{'OK' if s else '!!'}] {label}")
sys.exit(0 if ok == len(results) else 1)
