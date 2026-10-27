# test_phase3b.py - verifie protection /professionnel + fix org_id
import urllib.request, urllib.error, json, http.cookiejar

BASE = "http://127.0.0.1:8000"

def make_op():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPRedirectHandler(),  # suit les redirects par defaut
    )
    return op, cj

def get_status(op, path, follow=True):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k): return None
    if not follow:
        op2 = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(op.handlers and http.cookiejar.CookieJar() or None),
        )
        # On remplace juste pour cette requete
    req = urllib.request.Request(BASE + path)
    try:
        with op.open(req, timeout=8) as r:
            return r.status, r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location", "")

def login(op, email, pwd):
    req = urllib.request.Request(
        BASE + "/api/auth/login",
        data=json.dumps({"email": email, "password": pwd}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with op.open(req, timeout=8) as r:
        return json.loads(r.read())

print("=" * 60)
print("TEST PHASE 3b")
print("=" * 60)

# T1 : anonyme -> /professionnel
print("\n[T1] Anonyme -> /professionnel")
op, _ = make_op()
st, url = get_status(op, "/professionnel", follow=False)
print(f"  final_url={url}")
print(f"  {'OK' if '/connexion' in url else '!!! ECHEC'} (attendu /connexion...)")

# T2 : patient -> /professionnel
print("\n[T2] PATIENT -> /professionnel")
op, _ = make_op()
login(op, "patient@test.tg", "Test1234")
st, url = get_status(op, "/professionnel", follow=False)
print(f"  final_url={url}")
print(f"  {'OK (redirect /)' if url.endswith('/') or url.endswith(':8000/') else '!!! ECHEC (attendu redirect /)'}")

# T3 : pro (org=1) -> /professionnel
print("\n[T3] PRO (org=1) -> /professionnel")
op, _ = make_op()
login(op, "pro@test.tg", "Test1234")
st, url = get_status(op, "/professionnel", follow=False)
print(f"  final_url={url}")
print(f"  {'OK (page servie)' if url.rstrip('/').endswith('/professionnel') else '!!! ECHEC'}")

# T4 : verif DB : pro@test.tg a bien organization_id
import sqlite3, os
ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
con = sqlite3.connect(os.path.join(ROOT, "database.db"))
row = con.execute(
    "SELECT id, email, role, organization_id FROM users WHERE email='pro@test.tg'"
).fetchone()
con.close()
print(f"\n[T4] DB pro@test.tg : id={row[0]} role={row[2]} org={row[3]}")
print(f"  {'OK' if row[3] is not None else '!!! ECHEC (org_id NULL)'}")

print("\n" + "=" * 60)
print("FIN")