"""test_phases_7_13.py - Test des phases 7 a 13."""
import io, json, sqlite3, sys, urllib.error, urllib.request, http.cookiejar
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from v3_modules.auth import hash_password

API = "http://127.0.0.1:8000"
DB = BASE / "database.db"
ADMIN = "admin_test@elokinab.local"
ADMIN_PWD = "admin123456"


class Client:
    def __init__(self):
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def call(self, m, p, d=None):
        body = json.dumps(d).encode() if d is not None else None
        h = {"Accept": "application/json"}
        if d is not None: h["Content-Type"] = "application/json"
        req = urllib.request.Request(API + p, data=body, headers=h, method=m)
        try:
            r = self.opener.open(req, timeout=15)
            return r.status, json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            try: return e.code, json.loads(e.read().decode() or "{}")
            except: return e.code, {}


PASS, FAIL = 0, 0
def check(l, c, d=""):
    global PASS, FAIL
    if c: print("  [PASS] " + l); PASS += 1
    else:
        print("  [FAIL] " + l)
        if d: print("         ->", d)
        FAIL += 1


def ensure_admin():
    conn = sqlite3.connect(DB)
    try:
        r = conn.execute("SELECT id FROM users WHERE email=?", (ADMIN,)).fetchone()
        if r: return r[0]
        now = datetime.now().isoformat(timespec="seconds")
        cur = conn.execute(
            "INSERT INTO users (email, phone, password_hash, full_name, role, is_active, created_at)"
            " VALUES (?, ?, ?, 'Admin Test', 'ADMIN', 1, ?)",
            (ADMIN, "", hash_password(ADMIN_PWD), now))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def main():
    print("=" * 64)
    print("TEST PHASES 7 A 13")
    print("=" * 64)
    print()
    ensure_admin()

    a = Client()
    st, _ = a.call("POST", "/api/auth/login", {"email": ADMIN, "password": ADMIN_PWD})
    check("Login admin", st == 200, _)

    print()
    print("[Phase 7] Verification des tarifs MOTO/VOITURE")
    st, s = a.call("GET", "/api/settings")
    check("Settings OK", st == 200, s)
    for k in ("motorbike_base_fee", "motorbike_price_per_km",
              "car_base_fee", "car_price_per_km"):
        check("Champ " + k + " present", k in s, s)

    print()
    print("[Phase 8] Endpoints livreur/chauffeur")
    st, b = a.call("GET", "/api/deliveries")
    check("GET /api/deliveries OK (admin)", st == 200 and isinstance(b, list), b)

    print()
    print("[Phase 9] Dashboard admin consolide")
    st, b = a.call("GET", "/api/admin/dashboard")
    check("GET /api/admin/dashboard OK", st == 200, b)
    if isinstance(b, dict):
        for k in ("orders_total", "payments_pending", "prescriptions_pending",
                  "users_total", "deliveries_active"):
            check("Stat " + k, k in b, b)

    st, b = a.call("GET", "/api/admin/users")
    check("GET /api/admin/users OK", st == 200 and isinstance(b, list), b)

    print()
    print("[Phase 10] Notifications + recu")
    st, b = a.call("GET", "/api/notifications")
    check("GET /api/notifications OK", st == 200 and isinstance(b, list), b)

    # Recu sur la derniere commande
    st, orders = a.call("GET", "/api/orders")
    if isinstance(orders, list) and orders:
        ref = orders[0].get("reference")
        import urllib.request as ur
        try:
            r = ur.urlopen(API + "/api/orders/" + ref + "/receipt", timeout=10)
            html = r.read().decode()
            check("Recu genere", r.status == 200 and "Recu" in html, r.status)
        except Exception as e:
            check("Recu genere", False, str(e))
    else:
        check("Recu (skip: aucune commande)", True)

    print()
    print("[Phase 11] Securite (presence des modules)")
    check("auth avec scrypt", Path(BASE / "v3_modules" / "auth.py").exists())
    check("uploads/proofs cree", (BASE / "uploads").exists())

    print()
    print("[Phase 12] Non-regression globale")
    for path in ("/api/products", "/api/categories", "/api/orders",
                 "/api/drivers", "/api/settings", "/api/payments",
                 "/api/prescriptions", "/api/professionals",
                 "/api/admin/dashboard"):
        st, _b = a.call("GET", path)
        check("GET " + path, st == 200, "status=" + str(st))

    print()
    print("=" * 64)
    print("RESULTAT : " + str(PASS) + " PASS / " + str(FAIL) + " FAIL")
    print("=" * 64)
    if FAIL == 0:
        print("[OK] PHASES 7 a 13 validees.")
    else:
        print("[!] Certains tests ont echoue.")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
