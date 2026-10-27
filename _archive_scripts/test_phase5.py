"""test_phase5.py - Test paiement manuel + preuve + validation."""
import io
import json
import sqlite3
import sys
import urllib.error
import urllib.request
import http.cookiejar
import uuid
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from v3_modules.auth import hash_password

API = "http://127.0.0.1:8000"
DB = BASE / "database.db"
PATIENT_EMAIL = "pay_patient@elokinab.local"
ADMIN_EMAIL = "admin_test@elokinab.local"
ADMIN_PWD = "admin123456"
PWD = "motdepasse123"


class Client:
    def __init__(self):
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def call(self, method, path, data=None):
        body = json.dumps(data).encode() if data is not None else None
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(API + path, data=body, headers=headers, method=method)
        try:
            r = self.opener.open(req, timeout=15)
            return r.status, json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            try: return e.code, json.loads(e.read().decode() or "{}")
            except: return e.code, {}
    def upload(self, path, filename, content_bytes, content_type):
        boundary = "----" + uuid.uuid4().hex
        body = b""
        body += ("--" + boundary + "\r\n").encode()
        body += ('Content-Disposition: form-data; name="file"; filename="' + filename + '"\r\n').encode()
        body += ("Content-Type: " + content_type + "\r\n\r\n").encode()
        body += content_bytes + b"\r\n"
        body += ("--" + boundary + "--\r\n").encode()
        req = urllib.request.Request(API + path, data=body, method="POST")
        req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)
        try:
            r = self.opener.open(req, timeout=20)
            return r.status, json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            try: return e.code, json.loads(e.read().decode() or "{}")
            except: return e.code, {}


PASS, FAIL = 0, 0
def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        print("  [PASS] " + label); PASS += 1
    else:
        print("  [FAIL] " + label)
        if detail: print("         ->", detail)
        FAIL += 1


def ensure_admin():
    conn = sqlite3.connect(DB)
    try:
        row = conn.execute("SELECT id FROM users WHERE email=?", (ADMIN_EMAIL,)).fetchone()
        if row:
            return row[0]
        now = datetime.now().isoformat(timespec="seconds")
        cur = conn.execute(
            "INSERT INTO users (email, phone, password_hash, full_name, role, is_active, created_at)"
            " VALUES (?, ?, ?, 'Admin Test', 'ADMIN', 1, ?)",
            (ADMIN_EMAIL, "", hash_password(ADMIN_PWD), now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def cleanup():
    conn = sqlite3.connect(DB)
    try:
        row = conn.execute("SELECT id FROM users WHERE email=?", (PATIENT_EMAIL,)).fetchone()
        if row:
            uid = row[0]
            cart = conn.execute("SELECT id FROM carts WHERE user_id=?", (uid,)).fetchone()
            if cart:
                conn.execute("DELETE FROM cart_items WHERE cart_id=?", (cart[0],))
                conn.execute("DELETE FROM carts WHERE id=?", (cart[0],))
            # commandes et paiements lies
            orders = conn.execute("SELECT id FROM orders WHERE user_id=?", (uid,)).fetchall()
            for o in orders:
                conn.execute("DELETE FROM payments WHERE order_id=?", (o[0],))
                conn.execute("DELETE FROM order_items WHERE order_id=?", (o[0],))
                conn.execute("DELETE FROM orders WHERE id=?", (o[0],))
            conn.execute("DELETE FROM sessions WHERE user_id=?", (uid,))
            conn.execute("DELETE FROM users WHERE id=?", (uid,))
            conn.commit()
    finally:
        conn.close()


def get_product_id():
    conn = sqlite3.connect(DB)
    try:
        r = conn.execute("SELECT id FROM products WHERE is_active=1 AND is_demo=0 ORDER BY id LIMIT 1").fetchone()
        return r[0] if r else None
    finally:
        conn.close()


def set_payment_number():
    conn = sqlite3.connect(DB)
    try:
        conn.execute("UPDATE pharmacy_settings SET payment_number=?, payment_name=? WHERE id=1",
                     ("+22890000000", "Elokinab Health SARL"))
        conn.commit()
    finally:
        conn.close()


def main():
    print("=" * 64)
    print("TEST PHASE 5 - PAIEMENT MANUEL + PREUVE + VALIDATION")
    print("=" * 64)
    print()

    print("[1/8] Preparation")
    ensure_admin()
    cleanup()
    set_payment_number()
    pid = get_product_id()
    if not pid:
        print("[ERREUR] Aucun produit actif non-demo.")
        return 1
    print("  Produit test : id=" + str(pid))
    print()

    print("[2/8] Creer patient + panier + commande")
    p = Client()
    st, b = p.call("POST", "/api/auth/register", {
        "email": PATIENT_EMAIL, "password": PWD, "full_name": "Pay Patient",
        "phone": "90000000", "role": "PATIENT"
    })
    check("Inscription OK", st == 200, b)

    p.call("POST", "/api/cart/items", {"product_id": pid, "quantity": 2})
    st, b = p.call("POST", "/api/orders/v2", {
        "delivery_mode": "retrait",
        "customer_name": "Pay Patient",
        "phone": "90000000"
    })
    check("Commande creee", st == 200 and b.get("reference"), b)
    ref = b.get("reference")
    total = b.get("total")
    print("  Reference : " + str(ref) + "  Total : " + str(total) + " FCFA")
    print()

    print("[3/8] Initier le paiement")
    st, b = p.call("POST", "/api/orders/" + ref + "/payment", {"payment_method": "MANUAL"})
    check("Init OK", st == 200 and b.get("status") == "PENDING", b)
    check("Numero configure recupere", b.get("payment_number") == "+22890000000", b)
    check("Montant = total commande", abs((b.get("amount") or 0) - (total or 0)) < 0.01, b)
    payment_id = b.get("id")
    print()

    print("[4/8] Upload preuve (fausse image PNG)")
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789c63000100000005000100"
        "0d0a2db40000000049454e44ae426082"
    )
    st, b = p.upload("/api/orders/" + ref + "/payment/proof", "proof.png", png, "image/png")
    check("Upload OK", st == 200, b)
    check("Statut = PROOF_SUBMITTED", b.get("status") == "PROOF_SUBMITTED", b)
    check("proof_file present", bool(b.get("proof_file")), b)
    print()

    print("[5/8] Le patient voit son paiement")
    st, b = p.call("GET", "/api/orders/" + ref + "/payment")
    check("GET OK", st == 200 and b.get("status") == "PROOF_SUBMITTED", b)
    print()

    print("[6/8] Pharmacien : liste des preuves en attente")
    a = Client()
    st, b = a.call("POST", "/api/auth/login", {"email": ADMIN_EMAIL, "password": ADMIN_PWD})
    check("Login admin OK", st == 200, b)
    st, b = a.call("GET", "/api/payments?status=PROOF_SUBMITTED")
    check("Liste OK", st == 200 and isinstance(b, list), b)
    found = any(x.get("id") == payment_id for x in (b if isinstance(b, list) else []))
    check("Notre paiement est dans la liste", found, b)
    print()

    print("[7/8] Pharmacien valide le paiement")
    st, b = a.call("PATCH", "/api/payments/" + str(payment_id) + "/verify")
    check("Verify OK", st == 200 and b.get("status") == "VERIFIED", b)

    # Verifier que la commande a payment_status=VERIFIED
    st, order = a.call("GET", "/api/orders/" + ref)
    check("Commande payment_status=VERIFIED", order.get("payment_status") == "VERIFIED", order)
    print()

    print("[8/8] Non-regression V1")
    st, b = a.call("GET", "/api/products")
    check("V1 /api/products OK", st == 200 and isinstance(b, list), st)
    st, b = a.call("GET", "/api/orders")
    check("V1 /api/orders OK", st == 200, st)
    st, b = a.call("GET", "/api/settings")
    check("V1 /api/settings OK", st == 200, st)
    print()

    print("=" * 64)
    print("RESULTAT : " + str(PASS) + " PASS / " + str(FAIL) + " FAIL")
    print("=" * 64)
    if FAIL == 0:
        print("[OK] PHASE 5 validee.")
    else:
        print("[!] Des tests ont echoue.")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())