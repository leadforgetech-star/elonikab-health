"""test_phase6.py - Test workflow ordonnance."""
import json, sqlite3, sys, urllib.error, urllib.request, http.cookiejar, uuid
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from v3_modules.auth import hash_password

API = "http://127.0.0.1:8000"
DB = BASE / "database.db"
PATIENT = "presc_patient@elokinab.local"
ADMIN = "admin_test@elokinab.local"
ADMIN_PWD = "admin123456"
PWD = "motdepasse123"


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
    def upload(self, path, filename, content, ctype):
        b = "----" + uuid.uuid4().hex
        body = b""
        body += ("--" + b + "\r\n").encode()
        body += ('Content-Disposition: form-data; name="file"; filename="' + filename + '"\r\n').encode()
        body += ("Content-Type: " + ctype + "\r\n\r\n").encode()
        body += content + b"\r\n"
        body += ("--" + b + "--\r\n").encode()
        req = urllib.request.Request(API + path, data=body, method="POST")
        req.add_header("Content-Type", "multipart/form-data; boundary=" + b)
        try:
            r = self.opener.open(req, timeout=20)
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


def cleanup():
    conn = sqlite3.connect(DB)
    try:
        row = conn.execute("SELECT id FROM users WHERE email=?", (PATIENT,)).fetchone()
        if not row: return
        uid = row[0]
        for o in conn.execute("SELECT id FROM orders WHERE user_id=?", (uid,)).fetchall():
            conn.execute("DELETE FROM prescriptions WHERE order_id=?", (o[0],))
            conn.execute("DELETE FROM order_items WHERE order_id=?", (o[0],))
            conn.execute("DELETE FROM orders WHERE id=?", (o[0],))
        cart = conn.execute("SELECT id FROM carts WHERE user_id=?", (uid,)).fetchone()
        if cart:
            conn.execute("DELETE FROM cart_items WHERE cart_id=?", (cart[0],))
            conn.execute("DELETE FROM carts WHERE id=?", (cart[0],))
        conn.execute("DELETE FROM sessions WHERE user_id=?", (uid,))
        conn.execute("DELETE FROM users WHERE id=?", (uid,))
        conn.commit()
    finally:
        conn.close()


def product_requiring_prescription():
    conn = sqlite3.connect(DB)
    try:
        r = conn.execute(
            "SELECT id FROM products WHERE requires_prescription=1 AND is_active=1 LIMIT 1"
        ).fetchone()
        if r: return r[0]
        # fallback : marque un produit comme tel
        r = conn.execute("SELECT id FROM products WHERE is_active=1 ORDER BY id LIMIT 1").fetchone()
        if r:
            conn.execute("UPDATE products SET requires_prescription=1 WHERE id=?", (r[0],))
            conn.commit()
            return r[0]
        return None
    finally:
        conn.close()


def main():
    print("=" * 64)
    print("TEST PHASE 6 - WORKFLOW ORDONNANCE")
    print("=" * 64)
    print()

    print("[1/7] Preparation")
    ensure_admin(); cleanup()
    pid = product_requiring_prescription()
    if not pid:
        print("[ERREUR] Aucun produit disponible.")
        return 1
    print("  Produit test : id=" + str(pid) + " (requires_prescription=1)")
    print()

    print("[2/7] Patient cree une commande")
    p = Client()
    st, b = p.call("POST", "/api/auth/register", {
        "email": PATIENT, "password": PWD, "full_name": "Presc Patient",
        "phone": "90000000", "role": "PATIENT"})
    check("Inscription", st == 200, b)
    p.call("POST", "/api/cart/items", {"product_id": pid, "quantity": 1})
    st, b = p.call("POST", "/api/orders/v2", {
        "delivery_mode": "retrait", "customer_name": "Presc Patient", "phone": "90000000"})
    check("Commande creee", st == 200 and b.get("reference"), b)
    ref = b.get("reference")
    print("  Ref : " + str(ref))
    print()

    print("[3/7] Detecter si ordonnance requise")
    st, b = p.call("GET", "/api/orders/" + ref + "/requires-prescription")
    check("requires=True", st == 200 and b.get("requires_prescription") is True, b)
    print()

    print("[4/7] Upload d'une ordonnance")
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789c63000100000005000100"
        "0d0a2db40000000049454e44ae426082")
    st, b = p.upload("/api/orders/" + ref + "/prescription", "presc.png", png, "image/png")
    check("Upload OK", st == 200, b)
    check("Statut PENDING", b.get("status") == "PENDING", b)
    presc_id = b.get("id")
    print()

    print("[5/7] Patient lit son ordonnance")
    st, b = p.call("GET", "/api/orders/" + ref + "/prescription")
    check("GET OK", st == 200 and b.get("status") == "PENDING", b)
    print()

    print("[6/7] Pharmacien approuve l'ordonnance")
    a = Client()
    st, _ = a.call("POST", "/api/auth/login", {"email": ADMIN, "password": ADMIN_PWD})
    check("Login admin", st == 200, _)

    st, b = a.call("GET", "/api/prescriptions?status=PENDING")
    check("Liste PENDING", st == 200 and isinstance(b, list), b)
    found = any(x.get("id") == presc_id for x in (b if isinstance(b, list) else []))
    check("Notre ordonnance dans la liste", found, b)

    st, b = a.call("PATCH", "/api/prescriptions/" + str(presc_id) + "/review",
                   {"status": "APPROVED", "comment": ""})
    check("Approbation OK", st == 200 and b.get("status") == "APPROVED", b)

    st, order = a.call("GET", "/api/orders/" + ref)
    check("orders.prescription_status=APPROVED",
          order.get("prescription_status") == "APPROVED", order)
    print()

    print("[7/7] Statut NEEDS_REVIEW + non-regression V1")
    st, b = a.call("PATCH", "/api/prescriptions/" + str(presc_id) + "/review",
                   {"status": "NEEDS_REVIEW", "comment": "Photo trop floue"})
    check("NEEDS_REVIEW OK", st == 200 and b.get("status") == "NEEDS_REVIEW", b)

    st, b = a.call("PATCH", "/api/prescriptions/" + str(presc_id) + "/review",
                   {"status": "REJECTED", "comment": ""})
    check("Refus sans motif → 400", st == 400, b)

    st, b = a.call("GET", "/api/products")
    check("V1 products OK", st == 200 and isinstance(b, list), st)
    st, b = a.call("GET", "/api/orders")
    check("V1 orders OK", st == 200, st)
    print()

    print("=" * 64)
    print("RESULTAT : " + str(PASS) + " PASS / " + str(FAIL) + " FAIL")
    print("=" * 64)
    if FAIL == 0: print("[OK] PHASE 6 validee.")
    else: print("[!] Des tests ont echoue.")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())