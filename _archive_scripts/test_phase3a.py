# test_phase3a.py - test auth + ownership sur les 3 routes patchees
import urllib.request, urllib.error, json, http.cookiejar, sys

BASE = "http://127.0.0.1:8000"

def make_session():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    return op

def post(op, path, data):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with op.open(req, timeout=8) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]

def get(op, path):
    req = urllib.request.Request(BASE + path)
    try:
        with op.open(req, timeout=8) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]

print("=" * 60)
print("TEST PHASE 3a")
print("=" * 60)

# --- T1 : non connecte ---
print("\n[T1] Anonyme -> GET /api/orders")
op = make_session()
st, body = get(op, "/api/orders")
print(f"  status={st}  body={body}")
print(f"  {'OK' if st == 401 else '!!! ECHEC'} (attendu 401)")

# --- T2 : patient connecte ---
print("\n[T2] PATIENT -> GET /api/orders")
op = make_session()
st, body = post(op, "/api/auth/login", {"email": "patient@test.tg", "password": "Test1234"})
print(f"  login status={st}")
if st == 200:
    st2, body2 = get(op, "/api/orders")
    print(f"  orders status={st2}  len={len(body2) if isinstance(body2, list) else '?'}")
    print(f"  {'OK' if st2 == 200 and body2 == [] else '!!! ECHEC'} (attendu 200 + [])")

# --- T3 : pharmacien connecte ---
print("\n[T3] PHARMACIEN -> GET /api/orders")
op = make_session()
st, body = post(op, "/api/auth/login", {"email": "pharmacien@test.tg", "password": "Test1234"})
print(f"  login status={st}")
if st == 200:
    st2, body2 = get(op, "/api/orders")
    print(f"  orders status={st2}  len={len(body2) if isinstance(body2, list) else '?'}")
    print(f"  {'OK' if st2 == 200 and body2 == [] else '!!! ECHEC'}")

# --- T4 : reference inexistante ---
print("\n[T4] GET /api/orders/FAKE-REF-XYZ")
op = make_session()
post(op, "/api/auth/login", {"email": "patient@test.tg", "password": "Test1234"})
st, body = get(op, "/api/orders/FAKE-REF-XYZ")
print(f"  status={st}  body={body}")
print(f"  {'OK' if st == 404 else '!!! ECHEC'} (attendu 404)")

# --- T5 : PATCH status par patient (doit etre 403) ---
print("\n[T5] PATIENT -> PATCH /api/orders/FAKE/status (doit etre 403)")
op = make_session()
post(op, "/api/auth/login", {"email": "patient@test.tg", "password": "Test1234"})
req = urllib.request.Request(
    BASE + "/api/orders/FAKE-REF-XYZ/status",
    data=json.dumps({"status": "confirmee"}).encode(),
    headers={"Content-Type": "application/json"},
    method="PATCH",
)
try:
    with op.open(req, timeout=8) as r:
        print(f"  status={r.status}")
        print(f"  !!! ECHEC (attendu 403, recu {r.status})")
except urllib.error.HTTPError as e:
    print(f"  status={e.code}")
    print(f"  {'OK' if e.code == 403 else '!!! ECHEC'} (attendu 403)")

print("\n" + "=" * 60)
print("FIN")