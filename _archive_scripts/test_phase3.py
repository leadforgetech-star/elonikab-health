"""
test_phase3.py
Test automatique du parcours professionnel (Phase 3).
Lance le serveur AVANT (python main.py dans un autre terminal).

Usage :
    python test_phase3.py
"""
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

try:
    from v3_modules.auth import hash_password
except ImportError:
    print("[ERREUR] v3_modules/auth.py introuvable.")
    print("Lance d'abord : python v3_install_phase1_2.py")
    sys.exit(1)

API = "http://127.0.0.1:8000"
DB = BASE / "database.db"

PRO_EMAIL = "pro_test@elokinab.local"
PRO_PWD = "motdepasse123"
ADMIN_EMAIL = "admin_test@elokinab.local"
ADMIN_PWD = "admin123456"


# ============================================================
# Outils HTTP
# ============================================================

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
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            resp = self.opener.open(req, timeout=10)
            raw = resp.read().decode("utf-8") or "{}"
            return resp.status, json.loads(raw)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8") or "{}"
            try:
                body = json.loads(raw)
            except Exception:
                body = {"detail": raw}
            return e.code, body
        except urllib.error.URLError as e:
            print("[ERREUR] Serveur inaccessible :", e)
            print("Verifie que 'python main.py' tourne dans un autre terminal.")
            sys.exit(2)

    def reset(self):
        self.jar.clear()


# ============================================================
# Outils DB (pour creer un admin de test)
# ============================================================

def ensure_admin():
    conn = sqlite3.connect(DB)
    try:
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", (ADMIN_EMAIL,)
        ).fetchone()
        if row:
            print("  [i] Admin de test deja present (id=" + str(row[0]) + ")")
            return row[0]
        now = datetime.now().isoformat(timespec="seconds")
        cur = conn.execute(
            "INSERT INTO users (email, phone, password_hash, full_name, role, is_active, created_at)"
            " VALUES (?, ?, ?, ?, 'ADMIN', 1, ?)",
            (ADMIN_EMAIL, "", hash_password(ADMIN_PWD), "Admin Test", now),
        )
        conn.commit()
        print("  [OK] Admin de test cree (id=" + str(cur.lastrowid) + ")")
        return cur.lastrowid
    finally:
        conn.close()


def cleanup_test_pro():
    """Supprime le pro de test s'il existe (pour tests repetables)."""
    conn = sqlite3.connect(DB)
    try:
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", (PRO_EMAIL,)
        ).fetchone()
        if row:
            conn.execute("DELETE FROM professional_profiles WHERE user_id = ?", (row[0],))
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (row[0],))
            conn.execute("DELETE FROM users WHERE id = ?", (row[0],))
            conn.commit()
            print("  [OK] Ancien pro de test supprime (id=" + str(row[0]) + ")")
    finally:
        conn.close()


# ============================================================
# Assertions
# ============================================================

PASS, FAIL = 0, 0

def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        print("  [PASS] " + label)
        PASS += 1
    else:
        print("  [FAIL] " + label)
        if detail:
            print("         -> " + str(detail))
        FAIL += 1


# ============================================================
# Scenario
# ============================================================

def main():
    print("=" * 64)
    print("TEST PHASE 3 - PARCOURS PROFESSIONNEL")
    print("=" * 64)
    print()

    # --- Preparation ---
    print("[1/8] Preparation (admin de test + nettoyage)")
    ensure_admin()
    cleanup_test_pro()
    print()

    # --- Inscription PRO ---
    print("[2/8] Inscription d'un compte PROFESSIONNEL")
    pro = Client()
    st, body = pro.call("POST", "/api/auth/register", {
        "email": PRO_EMAIL,
        "password": PRO_PWD,
        "full_name": "Clinique Test",
        "phone": "90000000",
        "role": "PROFESSIONNEL",
    })
    check("HTTP 200", st == 200, body)
    check("role = PROFESSIONNEL", body.get("user", {}).get("role") == "PROFESSIONNEL", body)
    pro_user_id = body.get("user", {}).get("id")
    print()

    # --- Profil pro ---
    print("[3/8] Creation du profil de structure")
    st, body = pro.call("POST", "/api/professionals/profile", {
        "structure_name": "Clinique Test Elokinab",
        "structure_type": "CLINIQUE",
        "manager_name": "Dr Test",
        "phone": "90000000",
        "email": "contact@clinique-test.local",
        "address": "Lome, Togo",
        "latitude": 6.1319,
        "longitude": 1.2228,
        "notes": "Test automatique",
    })
    check("HTTP 200", st == 200, body)
    check("status = PENDING", body.get("status") == "PENDING", body)
    profile_id = body.get("id")
    print()

    # --- GET /me ---
    print("[4/8] Lecture du profil via /api/professionals/me")
    st, body = pro.call("GET", "/api/professionals/me")
    check("HTTP 200", st == 200, body)
    check("Structure correcte", body.get("structure_name") == "Clinique Test Elokinab", body)
    print()

    # --- Le pro ne doit PAS voir la liste globale ---
    print("[5/8] Le professionnel ne doit pas acceder a la liste globale")
    st, body = pro.call("GET", "/api/professionals")
    check("HTTP 403 (acces refuse)", st == 403, "status=" + str(st))
    print()

    # --- Connexion admin ---
    print("[6/8] Connexion admin + validation du profil")
    admin = Client()
    st, body = admin.call("POST", "/api/auth/login", {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PWD,
    })
    check("Connexion admin HTTP 200", st == 200, body)

    st, body = admin.call("GET", "/api/professionals?status=PENDING")
    check("Liste PENDING accessible", st == 200, body)
    found = any(p.get("id") == profile_id for p in (body if isinstance(body, list) else []))
    check("Le pro de test apparait dans la liste", found, body)
    print()

    # --- Approbation ---
    print("[7/8] Approbation du profil")
    st, body = admin.call("PATCH", "/api/professionals/" + str(profile_id) + "/status", {
        "status": "APPROVED",
    })
    check("PATCH HTTP 200", st == 200, body)
    check("status = APPROVED", body.get("status") == "APPROVED", body)

    # Le pro voit maintenant son statut approuve
    st, body = pro.call("GET", "/api/professionals/me")
    check("Le pro voit APPROVED", body.get("status") == "APPROVED", body)
    print()

    # --- Stats + non-regression V1 ---
    print("[8/8] Statistiques + non-regression V1")
    st, body = admin.call("GET", "/api/professionals/stats/summary")
    check("Stats HTTP 200", st == 200, body)
    check("approved >= 1", body.get("approved", 0) >= 1, body)

    st, body = admin.call("GET", "/api/products")
    check("V1 /api/products OK", st == 200 and isinstance(body, list), "status=" + str(st))
    st, body = admin.call("GET", "/api/orders")
    check("V1 /api/orders OK", st == 200 and isinstance(body, list), "status=" + str(st))
    st, body = admin.call("GET", "/api/settings")
    check("V1 /api/settings OK", st == 200, "status=" + str(st))
    print()

    # --- Bilan ---
    print("=" * 64)
    print("RESULTAT : " + str(PASS) + " PASS / " + str(FAIL) + " FAIL")
    print("=" * 64)
    if FAIL == 0:
        print("[OK] PHASE 3 validee.")
    else:
        print("[!] Des tests ont echoue. Verifie les details ci-dessus.")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())