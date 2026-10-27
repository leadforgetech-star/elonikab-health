# -*- coding: utf-8 -*-
# Test Lot 3+4+5
import json, urllib.request, urllib.error, http.cookiejar, sys

BASE = "http://127.0.0.1:8000"

def login(email, password):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    req = urllib.request.Request(
        BASE + "/api/auth/login",
        data=json.dumps({"email": email, "password": password}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    op.open(req, timeout=10)
    return op

results = []
def check(label, ok, detail=''):
    results.append((label, ok, detail))
    print("  [" + ("OK" if ok else "!!") + "] " + label + "  " + detail)

print("=" * 60)
print("TEST LOT 3+4+5")
print("=" * 60)

# Stats endpoint
print("\n[S1] /api/stats/summary pharmacien")
try:
    op = login("pharmacien@test.tg", "Test1234")
    r = op.open(BASE + "/api/stats/summary", timeout=10)
    data = json.loads(r.read().decode())
    check("Stats accessible", r.status == 200, "")
    check("total_orders present", "total_orders" in data)
    check("by_status present", "by_status" in data)
    check("payments_by_status present", "payments_by_status" in data)
except Exception as e:
    check("Stats pharmacien", False, str(e))

# Stats refusees patient
print("\n[S2] /api/stats/summary patient -> 403")
try:
    op_p = login("patient@test.tg", "Test1234")
    try:
        r = op_p.open(BASE + "/api/stats/summary", timeout=10)
        check("Patient bloque", r.status == 403, "recu " + str(r.status))
    except urllib.error.HTTPError as e:
        check("Patient bloque", e.code == 403, "recu " + str(e.code))
except Exception as e:
    check("Patient login", False, str(e))

# Stats refusees non auth
print("\n[S3] /api/stats/summary sans auth -> 403")
try:
    r = urllib.request.urlopen(BASE + "/api/stats/summary", timeout=10)
    check("Non auth bloque", r.status == 403, "")
except urllib.error.HTTPError as e:
    check("Non auth bloque", e.code in (401, 403), "recu " + str(e.code))
except Exception as e:
    check("Non auth", False, str(e))

print()
print("=" * 60)
ok = sum(1 for _, s, _ in results if s)
print("RESULTAT : " + str(ok) + "/" + str(len(results)))
print("=" * 60)
sys.exit(0 if ok == len(results) else 1)
