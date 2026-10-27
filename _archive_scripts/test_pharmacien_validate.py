"""
test_pharmacien_validate.py
Teste la validation d'un paiement par le pharmacien.
Verifie ensuite que la notification est creee pour le client.
"""
import json
import sqlite3
import sys
import urllib.error
import urllib.request
import http.cookiejar
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "database.db"
API = "http://127.0.0.1:8000"
PHARMACIEN = "pharmacien@test.tg"
PWD = "Test1234"


class Client:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )

    def call(self, method, path, data=None):
        url = API + path
        body = None
        headers = {"Accept": "application/json"}
        if data is not None:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            r = self.opener.open(req, timeout=15)
            return r.status, json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8") or "{}"
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"detail": raw}


PASS = 0
FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        print("  [PASS] " + label)
        PASS += 1
    else:
        print("  [FAIL] " + label)
        if detail:
            print("         -> " + str(detail)[:200])
        FAIL += 1


def main():
    print("=" * 66)
    print(" TEST VALIDATION PAIEMENT PAR LE PHARMACIEN")
    print("=" * 66)
    print()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # 1. Chercher un paiement PROOF_SUBMITTED pour le pro
    print("[1] Recherche d'un paiement a valider...")
    row = conn.execute("""
        SELECT p.id AS payment_id, p.order_id, o.reference AS order_ref,
               o.user_id, u.email AS user_email
        FROM payments p
        JOIN orders o ON o.id = p.order_id
        JOIN users u ON u.id = o.user_id
        WHERE p.status = 'PROOF_SUBMITTED'
              AND u.email = 'pro@test.tg'
        ORDER BY p.id DESC LIMIT 1
    """).fetchone()

    if row is None:
        print("  [!] Aucun paiement PROOF_SUBMITTED pour pro@test.tg")
        print("      Cree-en un en uploadant une preuve d'abord.")
        conn.close()
        return 1

    payment_id = row["payment_id"]
    order_ref = row["order_ref"]
    user_id = row["user_id"]
    print(f"  [i] Paiement ID = {payment_id}")
    print(f"  [i] Commande    = {order_ref}")
    print(f"  [i] User_id     = {user_id}")

    # 2. Compter les notifications AVANT
    notifs_before = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id=? AND order_id=?",
        (user_id, row["order_id"])
    ).fetchone()[0]
    print(f"  [i] Notifications avant : {notifs_before}")
    print()

    # 3. Connexion pharmacien
    print("[2] Connexion pharmacien...")
    c = Client()
    st, b = c.call("POST", "/api/auth/login", {
        "email": PHARMACIEN, "password": PWD
    })
    check("Login HTTP 200", st == 200, b)
    check("Role correct", b.get("user", {}).get("role") in ("PHARMACIEN", "ADMIN"), b)
    print()

    # 4. Valider le paiement
    print(f"[3] Validation PATCH /api/payments/{payment_id}/verify...")
    st, response = c.call("PATCH", f"/api/payments/{payment_id}/verify")
    check("PATCH HTTP 200", st == 200, response)
    check("Statut = VERIFIED", response.get("status") == "VERIFIED", response)
    check("verified_at present", bool(response.get("verified_at")), response)
    print(f"  [i] Reponse : {response}")
    print()

    # 5. Verifier en base
    print("[4] Verification en base...")
    pay_after = conn.execute(
        "SELECT status, verified_at, verified_by FROM payments WHERE id=?",
        (payment_id,)
    ).fetchone()
    check("payments.status = VERIFIED",
          pay_after["status"] == "VERIFIED", dict(pay_after))
    check("payments.verified_at rempli",
          pay_after["verified_at"] is not None, dict(pay_after))
    check("payments.verified_by rempli",
          pay_after["verified_by"] is not None, dict(pay_after))

    order_after = conn.execute(
        "SELECT payment_status FROM orders WHERE reference=?",
        (order_ref,)
    ).fetchone()
    check("orders.payment_status = VERIFIED",
          order_after["payment_status"] == "VERIFIED", dict(order_after))
    print()

    # 6. Verifier la notification
    print("[5] Verification de la notification creee...")
    notifs_after = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id=? AND order_id=?",
        (user_id, row["order_id"])
    ).fetchone()[0]
    print(f"  [i] Notifications apres : {notifs_after}")

    check("Notification creee", notifs_after > notifs_before,
          f"avant={notifs_before} apres={notifs_after}")

    last_notif = conn.execute("""
        SELECT id, title, body, is_read, created_at
        FROM notifications
        WHERE user_id=? AND order_id=?
        ORDER BY id DESC LIMIT 1
    """, (user_id, row["order_id"])).fetchone()
    if last_notif:
        print(f"  [i] Derniere notification :")
        print(f"        Titre : {last_notif['title']}")
        print(f"        Corps : {last_notif['body']}")
        print(f"        Lu    : {last_notif['is_read']}")
        print(f"        Date  : {last_notif['created_at']}")

    conn.close()

    print()
    print("=" * 66)
    print(f" RESULTAT : {PASS} PASS / {FAIL} FAIL")
    print("=" * 66)
    if FAIL == 0:
        print("[OK] La validation cree bien une notification.")
        print("     Recharge la page /professionnel pour la voir.")
    else:
        print("[!] Des erreurs. Colle-moi le resultat ci-dessus.")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())