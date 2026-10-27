# -*- coding: utf-8 -*-
"""Diagnostic de performance : local vs tunnel + temps par requete."""
import urllib.request, time, json

LOCAL = "http://127.0.0.1:8000"
TUNNEL = "https://approach-aus-angeles-lot.trycloudflare.com"

ENDPOINTS = [
    "/api/products",
    "/api/settings",
]

AUTH_ENDPOINTS = [
    "/api/orders",
    "/api/payments",
    "/api/prescriptions",
    "/api/drivers?include_inactive=1",
]

def timeit(url, method="GET", cookies=None):
    req = urllib.request.Request(url, method=method)
    if cookies:
        req.add_header("Cookie", cookies)
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=15)
        r.read()
        return (time.time() - t0) * 1000, r.status
    except Exception as e:
        return (time.time() - t0) * 1000, str(e)

print("=" * 70)
print("DIAGNOSTIC PERFORMANCE")
print("=" * 70)

print("\n[1] Endpoints PUBLICS (local vs tunnel)")
print("-" * 70)
print(f"{'Endpoint':35s} {'Local':>10s} {'Tunnel':>10s}")
for ep in ENDPOINTS:
    l_ms, l_st = timeit(LOCAL + ep)
    t_ms, t_st = timeit(TUNNEL + ep)
    print(f"{ep:35s} {l_ms:>8.0f}ms {t_ms:>8.0f}ms")

print("\n[2] Login via tunnel (recuperer cookie)")
# Login pour tester les endpoints auth
import http.cookiejar
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
login_req = urllib.request.Request(
    TUNNEL + "/api/auth/login",
    data=json.dumps({"email":"pharmacien@test.tg","password":"Test1234"}).encode(),
    headers={"Content-Type":"application/json"},
    method="POST"
)
t0 = time.time()
try:
    r = op.open(login_req, timeout=20)
    login_ms = (time.time() - t0) * 1000
    print(f"  Login tunnel : {login_ms:.0f}ms")
except Exception as e:
    print(f"  [!!] Login echoue : {e}")
    login_ms = 0

print("\n[3] Endpoints AUTH (tunnel)")
print("-" * 70)
if login_ms > 0:
    total = 0
    for ep in AUTH_ENDPOINTS:
        t0 = time.time()
        try:
            r = op.open(urllib.request.Request(TUNNEL + ep), timeout=15)
            r.read()
            ms = (time.time() - t0) * 1000
            total += ms
            print(f"  {ep:35s} {ms:>8.0f}ms")
        except Exception as e:
            print(f"  {ep:35s} ERR {e}")
    print(f"\n  Total parallele estime : max des 4 = ~{total/4:.0f}ms (si sequentiel)")

print("\n" + "=" * 70)
print("INTERPRETATION")
print("=" * 70)
print("""
  Local < 100ms       -> serveur rapide
  Local 100-500ms     -> serveur un peu lent (index SQLite ?)
  Local > 500ms       -> probleme serveur

  Tunnel - Local < 300ms  -> tunnel correct
  Tunnel - Local > 500ms  -> LATENCE TUNNEL (normal pour trycloudflare)
  Tunnel - Local > 1000ms -> tres lent, peut etre cause locale
""")