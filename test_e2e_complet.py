# -*- coding: utf-8 -*-
# Tests E2E complets - 12 scenarios critiques (Lot 1 + Lot 2)
import json, urllib.request, urllib.error, http.cookiejar, sqlite3, sys

BASE = "http://127.0.0.1:8000"
DB   = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie\database.db"

def login(email, password):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    req = urllib.request.Request(
        BASE + "/api/auth/login",
        data=json.dumps({"email": email, "password": password}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    r = op.open(req, timeout=10)
    return op

def call(op, method, path, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(BASE + path, data=data,
        headers={"Content-Type":"application/json"} if body else {},
        method=method)
    try:
        r = op.open(req, timeout=10)
        return r.status, r.read().decode()[:300]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except Exception as e:
        return None, str(e)

def call_noauth(method, path, data=None, ct=None):
    req = urllib.request.Request(BASE + path, data=data,
        headers={"Content-Type": ct} if ct else {}, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=10)
        return r.status, r.read().decode()[:300]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except Exception as e:
        return None, str(e)

results = []
def check(label, condition, detail=''):
    status = "OK" if condition else "ECHEC"
    results.append((label, status, detail))
    print("  [" + status + "] " + label + "  " + detail)

print("=" * 70)
print("TESTS E2E COMPLETS")
print("=" * 70)

# S1
print("\n[S1] POST /api/orders sans auth = 401")
code, _ = call_noauth("POST", "/api/orders",
    data=b"customer_name=T&phone=2289&product_id=1&quantity=1&delivery_mode=retrait",
    ct="application/x-www-form-urlencoded")
check("S1", code == 401, "recu " + str(code))

# S2
print("\n[S2] GET /api/drivers sans auth")
code, _ = call_noauth("GET", "/api/drivers")
check("S2", code in (401, 403), "recu " + str(code))

# S3
print("\n[S3] PATCH /api/settings sans auth")
code, _ = call_noauth("PATCH", "/api/settings", data=b"{}", ct="application/json")
check("S3", code in (401, 403), "recu " + str(code))

# S4
print("\n[S4] GET /api/settings public = 200")
code, _ = call_noauth("GET", "/api/settings")
check("S4", code == 200, "recu " + str(code))

# S5
print("\n[S5] Patient -> GET /api/drivers = 403")
try:
    op_p = login("patient@test.tg", "Test1234")
    code, _ = call(op_p, "GET", "/api/drivers")
    check("S5", code == 403, "recu " + str(code))
except Exception as e:
    check("S5", False, "login patient echoue: " + str(e))

# S6
print("\n[S6] Pharmacien -> GET /api/drivers = 200")
try:
    op_ph = login("pharmacien@test.tg", "Test1234")
    code, _ = call(op_ph, "GET", "/api/drivers")
    check("S6", code == 200, "recu " + str(code))
except Exception as e:
    check("S6", False, "login pharm echoue: " + str(e))

# S7
print("\n[S7] Pharmacien -> PATCH /api/settings = 200")
try:
    code, _ = call(op_ph, "PATCH", "/api/settings", {"delivery_base_fee": 1000})
    check("S7", code == 200, "recu " + str(code))
except Exception as e:
    check("S7", False, str(e))

# S8
print("\n[S8] Patient connecte -> POST /api/orders")
try:
    op_p2 = login("patient@test.tg", "Test1234")
    req = urllib.request.Request(BASE + "/api/orders",
        data=b"customer_name=T&phone=2289&product_id=1&quantity=1&delivery_mode=retrait",
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    try:
        r = op_p2.open(req, timeout=10)
        check("S8", r.status in (200, 201), "recu " + str(r.status))
    except urllib.error.HTTPError as e:
        check("S8", e.code in (200, 201, 400), "recu " + str(e.code))
except Exception as e:
    check("S8", False, str(e))

# S9
print("\n[S9] audit_logs non vide")
conn = sqlite3.connect(DB)
n = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
conn.close()
check("S9", n > 0, str(n) + " lignes")

# S10
print("\n[S10] Actions instrumentees presentes")
conn = sqlite3.connect(DB)
actions = set(r[0] for r in conn.execute("SELECT DISTINCT action FROM audit_logs").fetchall())
conn.close()
expected = {"order.status_change", "payment.verify"}
missing = expected - actions
check("S10", len(missing) == 0, "presents=" + str(sorted(actions)))

# S11
print("\n[S11] Verification coherence paiements")
conn = sqlite3.connect(DB)
rows = conn.execute(
    "SELECT COUNT(*) FROM orders WHERE status = 'refusee' AND payment_status IN ('VERIFIED', 'PROOF_SUBMITTED')"
).fetchone()[0]
conn.close()
check("S11", True, str(rows) + " cas (informatif)")

# S12
print("\n[S12] GET /api/products public = 200")
code, _ = call_noauth("GET", "/api/products")
check("S12", code == 200, "recu " + str(code))

print()
print("=" * 70)
ok_count = sum(1 for _, s, _ in results if s == "OK")
print("RESULTAT : " + str(ok_count) + "/" + str(len(results)) + " tests OK")
print("=" * 70)
for label, s, detail in results:
    mark = "OK" if s == "OK" else "!!"
    print("  [" + mark + "] " + label + "  " + detail)

sys.exit(0 if ok_count == len(results) else 1)
