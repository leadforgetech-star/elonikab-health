"""test_phase4.py - Test du panier multi-produits."""
import json
import sqlite3
import sys
import urllib.error
import urllib.request
import http.cookiejar
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from v3_modules.auth import hash_password

API = "http://127.0.0.1:8000"
DB = BASE / "database.db"
EMAIL = "cart_test@elokinab.local"
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
            r = self.opener.open(req, timeout=10)
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


def cleanup():
    conn = sqlite3.connect(DB)
    try:
        row = conn.execute("SELECT id FROM users WHERE email=?", (EMAIL,)).fetchone()
        if row:
            uid = row[0]
            cart = conn.execute("SELECT id FROM carts WHERE user_id=?", (uid,)).fetchone()
            if cart:
                conn.execute("DELETE FROM cart_items WHERE cart_id=?", (cart[0],))
                conn.execute("DELETE FROM carts WHERE id=?", (cart[0],))
            conn.execute("DELETE FROM sessions WHERE user_id=?", (uid,))
            conn.execute("DELETE FROM users WHERE id=?", (uid,))
            conn.commit()
    finally:
        conn.close()


def get_product_ids():
    conn = sqlite3.connect(DB)
    try:
        rows = conn.execute(
            "SELECT id FROM products WHERE is_active=1 AND is_demo=0 ORDER BY id LIMIT 2"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def main():
    print("=" * 64)
    print("TEST PHASE 4 - PANIER MULTI-PRODUITS")
    print("=" * 64)
    print()

    print("[1/7] Preparation")
    cleanup()
    ids = get_product_ids()
    if len(ids) < 2:
        print("[ERREUR] Il faut au moins 2 produits actifs non-demo.")
        return 1
    p1, p2 = ids[0], ids[1]
    print("  Produits test : id=" + str(p1) + ", id=" + str(p2))
    print()

    c = Client()

    print("[2/7] Inscription + panier initial vide")
    st, b = c.call("POST", "/api/auth/register", {
        "email": EMAIL, "password": PWD, "full_name": "Cart Test",
        "phone": "90000000", "role": "PATIENT",
    })
    check("Inscription OK", st == 200, b)
    st, b = c.call("GET", "/api/cart")
    check("Panier initial vide", st == 200 and b.get("item_count") == 0, b)
    print()

    print("[3/7] Ajout de 2 produits")
    st, b = c.call("POST", "/api/cart/items", {"product_id": p1, "quantity": 2})
    check("Ajout produit 1", st == 200 and b.get("item_count") == 2, b)
    st, b = c.call("POST", "/api/cart/items", {"product_id": p2, "quantity": 1})
    check("Ajout produit 2", st == 200 and b.get("item_count") == 3, b)
    check("2 lignes distinctes", len(b.get("items", [])) == 2, b)
    check("Sous-total > 0", b.get("subtotal", 0) > 0, b)
    print()

    print("[4/7] Modification de quantite")
    item_id = b["items"][0]["id"]
    st, b = c.call("PATCH", "/api/cart/items/" + str(item_id), {"quantity": 5})
    check("Modification OK", st == 200, b)
    check("Quantite mise a jour", any(i["quantity"] == 5 for i in b["items"]), b)
    print()

    print("[5/7] Suppression d'un article")
    st, b = c.call("DELETE", "/api/cart/items/" + str(item_id))
    check("Suppression OK", st == 200 and len(b["items"]) == 1, b)
    print()

    print("[6/7] Commande multi-lignes via /api/orders/v2")
    # Remplir le panier avec 2 produits
    c.call("POST", "/api/cart/items", {"product_id": p1, "quantity": 1})
    st, b = c.call("GET", "/api/cart")
    st, b = c.call("POST", "/api/orders/v2", {
        "delivery_mode": "retrait",
        "customer_name": "Client Test",
        "phone": "90000000",
    })
    check("Commande creee", st == 200 and b.get("reference"), b)
    check("2 items dans la commande", len(b.get("items", [])) == 2, b)
    check("subtotal present", b.get("subtotal", 0) > 0, b)
    check("customer_type = PARTICULIER", b.get("customer_type") == "PARTICULIER", b)
    check("delivery_vehicle_type = MOTO", b.get("delivery_vehicle_type") == "MOTO", b)
    ref = b.get("reference")
    print()

    print("[7/7] Verification panier vide + non-regression V1")
    st, b = c.call("GET", "/api/cart")
    check("Panier vide apres commande", st == 200 and b.get("item_count") == 0, b)

    st, b = c.call("GET", "/api/orders/" + ref + "/items")
    check("GET items par ref", st == 200 and len(b) == 2, b)

    st, b = c.call("GET", "/api/products")
    check("V1 /api/products OK", st == 200 and isinstance(b, list), st)
    st, b = c.call("GET", "/api/orders")
    check("V1 /api/orders OK", st == 200, st)
    print()

    print("=" * 64)
    print("RESULTAT : " + str(PASS) + " PASS / " + str(FAIL) + " FAIL")
    print("=" * 64)
    if FAIL == 0:
        print("[OK] PHASE 4 validee.")
    else:
        print("[!] Des tests ont echoue.")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())