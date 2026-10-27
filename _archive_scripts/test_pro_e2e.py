"""
test_pro_e2e.py
Test de bout en bout cote professionnel.
Necessite Uvicorn lance sur http://127.0.0.1:8000
"""
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
DB = BASE / "database.db"
API = "http://127.0.0.1:8000"
PRO_EMAIL = "pro@test.tg"
PRO_PWD = "Test1234"


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
            raw = r.read().decode("utf-8") or "{}"
            return r.status, json.loads(raw)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8") or "{}"
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"detail": raw}

    def upload(self, path, filename, content, ctype):
        boundary = "----" + uuid.uuid4().hex
        body = b""
        body += ("--" + boundary + "\r\n").encode()
        body += (
            'Content-Disposition: form-data; name="file"; filename="'
            + filename + '"\r\n'
        ).encode()
        body += ("Content-Type: " + ctype + "\r\n\r\n").encode()
        body += content + b"\r\n"
        body += ("--" + boundary + "--\r\n").encode()
        req = urllib.request.Request(API + path, data=body, method="POST")
        req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)
        try:
            r = self.opener.open(req, timeout=30)
            return r.status, json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8") or "{}"
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"detail": raw}

    def upload_binary(self, path, filename, content):
        import base64
        req = urllib.request.Request(API + path, data=content, method="POST")
        req.add_header("Content-Type", "application/octet-stream")
        req.add_header("X-Filename", base64.b64encode(filename.encode()).decode())
        try:
            r = self.opener.open(req, timeout=30)
            return r.status, json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8") or "{}"
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"detail": raw}


PASS = 0
FAIL = 0
ERRORS = []


def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        print("  [PASS] " + label)
        PASS += 1
    else:
        print("  [FAIL] " + label)
        if detail:
            print("         -> " + str(detail)[:200])
        FAIL += 1
        ERRORS.append(label)


def section(title):
    print()
    print("=" * 66)
    print(" " + title)
    print("=" * 66)
    print()


def main():
    section("TEST E2E - ESPACE PROFESSIONNEL")

    # ============================================================
    # 0. Preparation
    # ============================================================
    section("[0/8] Preparation")

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # Nettoyer l'ancienne demande en cours pour ce pro
    user = conn.execute(
        "SELECT id FROM users WHERE email=?", (PRO_EMAIL,)
    ).fetchone()
    check("Compte pro existe", user is not None)
    if user is None:
        print("[ERREUR] Compte pro@test.tg introuvable.")
        return 1

    uid = user["id"]
    # Supprimer les drafts pour repartir a zero
    drafts = conn.execute(
        "SELECT id FROM requests WHERE user_id=? AND status='DRAFT'", (uid,)
    ).fetchall()
    for d in drafts:
        conn.execute("DELETE FROM request_items WHERE request_id=?", (d["id"],))
        conn.execute("DELETE FROM request_attachments WHERE request_id=?", (d["id"],))
        conn.execute("DELETE FROM requests WHERE id=?", (d["id"],))
    conn.commit()
    print(f"  [i] {len(drafts)} brouillon(s) nettoye(s)")
    conn.close()

    # ============================================================
    # 1. Connexion
    # ============================================================
    section("[1/8] Connexion pro")
    c = Client()
    st, b = c.call("POST", "/api/auth/login", {
        "email": PRO_EMAIL, "password": PRO_PWD
    })
    check("Login HTTP 200", st == 200, b)
    check("Role = PROFESSIONNEL",
          b.get("user", {}).get("role") == "PROFESSIONNEL", b)
    check("Cookie session recu", len(c.jar) > 0)

    # ============================================================
    # 2. Organisation
    # ============================================================
    section("[2/8] Profil etablissement")
    st, org = c.call("GET", "/api/pro/organizations/me")
    check("GET /organizations/me", st == 200, org)
    check("Nom etablissement present",
          bool(org.get("structure_name")), org)

    # ============================================================
    # 3. Catalogue
    # ============================================================
    section("[3/8] Catalogue")
    st, prods = c.call("GET", "/api/products")
    check("GET /products", st == 200 and isinstance(prods, list), prods)
    check("Au moins 3 produits", len(prods) >= 3, f"n={len(prods) if isinstance(prods, list) else '?'}")

    if isinstance(prods, list) and len(prods) >= 3:
        p1, p2, p3 = prods[0], prods[1], prods[2]
    else:
        return 1

    # ============================================================
    # 4. Demande en cours
    # ============================================================
    section("[4/8] Demande en cours")
    st, draft = c.call("GET", "/api/pro/requests/draft")
    check("Draft cree", st == 200 and draft.get("reference"), draft)
    ref = draft["reference"]
    print(f"  [i] Reference draft : {ref}")

    # Ajouter 3 produits
    for p, qty in [(p1, 2), (p2, 1), (p3, 5)]:
        st, _ = c.call("POST", f"/api/pro/requests/{ref}/items", {
            "product_id": p["id"],
            "description": p["name"],
            "requested_quantity": qty
        })
        check(f"Ajout '{p['name'][:30]}' x{qty}", st == 200, _)

    # Verifier le summary
    st, summary = c.call("GET", f"/api/pro/requests/{ref}/summary")
    check("GET /summary", st == 200, summary)
    check("3 items", summary.get("items_count") == 3, summary)
    check("Sous-total > 0", summary.get("subtotal", 0) > 0, summary)
    print(f"  [i] Sous-total : {summary.get('subtotal')} F")

    # ============================================================
    # 5. Estimation livraison
    # ============================================================
    section("[5/8] Estimation livraison (VOITURE)")
    st, est = c.call("POST", f"/api/pro/requests/{ref}/estimate-delivery", {
        "delivery_mode": "livraison",
        "latitude": 6.1319,
        "longitude": 1.2228,
        "location_accuracy": 50,
        "address": "",
        "notes": ""
    })
    check("POST /estimate-delivery", st == 200, est)
    check("Distance retournee",
          est.get("distance_km") is not None or est.get("source") == "no_pharmacy",
          est)
    check("Frais retournes",
          est.get("delivery_fee") is not None, est)
    print(f"  [i] Distance : {est.get('distance_km')} km")
    print(f"  [i] Frais    : {est.get('delivery_fee')} F")
    print(f"  [i] Source   : {est.get('source')}")

    # ============================================================
    # 6. Soumission -> creation commande
    # ============================================================
    section("[6/8] Soumission de la demande")
    st, submit_result = c.call("POST", f"/api/pro/requests/{ref}/submit", {
        "delivery_mode": "livraison",
        "address": "Lome, Togo - Test E2E",
        "latitude": 6.1319,
        "longitude": 1.2228,
        "location_accuracy": 50,
        "notes": "Test automatique"
    })
    check("Submit HTTP 200", st == 200, submit_result)
    order_ref = submit_result.get("order_reference")
    check("Order reference generee", bool(order_ref), submit_result)
    print(f"  [i] Commande creee : {order_ref}")

    # Verifier que la commande existe
    st, order = c.call("GET", f"/api/orders/{order_ref}")
    check("Commande accessible", st == 200, order)
    check("Statut initial", order.get("status") in ("en_attente", "confirmee"), order)
    check("payment_status = PENDING",
          order.get("payment_status") in ("PENDING", "PROOF_SUBMITTED"), order)
    check("subtotal > 0", float(order.get("subtotal") or 0) > 0, order)

    # ============================================================
    # 7. Paiement - preuve binaire
    # ============================================================
    section("[7/8] Paiement et upload preuve")

    # Init paiement
    st, pay = c.call("POST", f"/api/orders/{order_ref}/payment", {
        "payment_method": "MANUAL"
    })
    check("Init paiement", st == 200, pay)
    check("payment_number present",
          bool(pay.get("payment_number")), pay)
    print(f"  [i] Numero a payer : {pay.get('payment_number')}")
    print(f"  [i] Beneficiaire   : {pay.get('payment_name')}")

    # Upload binaire d'une petite image PNG valide
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d494844520000000100000001"
        "08060000001f15c4890000000a49444154789c6300010000"
        "00050001000d0a2db40000000049454e44ae426082"
    )
    st, proof = c.upload_binary(
        f"/api/orders/{order_ref}/payment/proof-binary",
        "test_e2e.png",
        png
    )
    check("Upload binaire HTTP 200", st == 200, proof)
    check("Statut = PROOF_SUBMITTED",
          proof.get("status") == "PROOF_SUBMITTED", proof)
    check("proof_file present",
          bool(proof.get("proof_file")), proof)
    print(f"  [i] Preuve : {proof.get('proof_file')}")

    # Verifier cote commande
    st, order2 = c.call("GET", f"/api/orders/{order_ref}")
    check("order.payment_status = PROOF_SUBMITTED",
          order2.get("payment_status") == "PROOF_SUBMITTED", order2)

    # ============================================================
    # 8. Timeline et notifications
    # ============================================================
    section("[8/8] Timeline et suivi")

    st, tl = c.call("GET", f"/api/orders/{order_ref}/timeline")
    check("GET /timeline", st == 200, tl)
    check("Timeline a des events", len(tl.get("events", [])) >= 2, tl)
    check("can_pay present", "can_pay" in tl, tl)
    print(f"  [i] Events : {len(tl.get('events', []))}")
    for ev in tl.get("events", [])[:6]:
        print(f"        - {ev.get('label')}  ({ev.get('at', '?')[:16]})")

    # Notifications (doit y avoir au moins 1 pour la pharmacie)
    st, notifs = c.call("GET", "/api/notifications?unread_only=1")
    check("GET /notifications", st == 200 and isinstance(notifs, list), notifs)

    # ============================================================
    # Resultat
    # ============================================================
    section("RESULTAT")
    print(f"  PASS : {PASS}")
    print(f"  FAIL : {FAIL}")
    print()
    if FAIL > 0:
        print("Tests echoues :")
        for e in ERRORS:
            print("  - " + e)
        return 1
    print("[OK] Parcours professionnel complet valide.")
    return 0


if __name__ == "__main__":
    sys.exit(main())