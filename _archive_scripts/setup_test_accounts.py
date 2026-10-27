"""
setup_test_accounts.py
Cree/verifie tous les comptes de test pour chaque role.
Mot de passe unique pour tous : Test1234
"""
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from v3_modules.auth import hash_password

DB = BASE / "database.db"
PWD = "Test1234"
PWD_HASH = hash_password(PWD)

ACCOUNTS = [
    # (email, phone, full_name, role)
    ("patient@test.tg",       "90000001", "Patient Test",     "PATIENT"),
    ("pro@test.tg",           "90000002", "Clinique Test",    "PROFESSIONNEL"),
    ("pharmacien@test.tg",    "90000003", "Pharmacien Test",  "PHARMACIEN"),
    ("admin@test.tg",         "90000004", "Admin Test",       "ADMIN"),
    ("livreur@test.tg",       "90000005", "Kossi Livreur",    "LIVREUR_MOTO"),
    ("chauffeur@test.tg",     "90000006", "Mensah Chauffeur", "CHAUFFEUR"),
]

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    now = datetime.now().isoformat(timespec="seconds")

    print("=" * 70)
    print("PREPARATION DES COMPTES DE TEST")
    print("=" * 70)
    print()

    for email, phone, name, role in ACCOUNTS:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()
        if existing:
            # Reinitialiser le mot de passe au cas ou
            conn.execute(
                "UPDATE users SET password_hash=?, is_active=1, updated_at=? WHERE id=?",
                (PWD_HASH, now, existing["id"]),
            )
            print("  [OK] " + email + "  (id=" + str(existing["id"]) + ", reset pwd)")
            uid = existing["id"]
        else:
            cur = conn.execute(
                "INSERT INTO users (email, phone, password_hash, full_name,"
                " role, is_active, created_at)"
                " VALUES (?, ?, ?, ?, ?, 1, ?)",
                (email, phone, PWD_HASH, name, role, now),
            )
            uid = cur.lastrowid
            print("  [NEW] " + email + "  (id=" + str(uid) + ")")

        # Si c'est le PRO : creer un profil approuve
        if role == "PROFESSIONNEL":
            prof = conn.execute(
                "SELECT id FROM professional_profiles WHERE user_id = ?", (uid,)
            ).fetchone()
            if not prof:
                conn.execute(
                    "INSERT INTO professional_profiles (user_id, structure_name,"
                    " structure_type, manager_name, phone, email, address,"
                    " status, created_at, reviewed_at)"
                    " VALUES (?, 'Clinique Test Elokinab', 'CLINIQUE', ?, ?, ?,"
                    " 'Lome, Togo', 'APPROVED', ?, ?)",
                    (uid, name, phone, email, now, now),
                )
                print("        [OK] profil pro cree et APPROVED")
            else:
                conn.execute(
                    "UPDATE professional_profiles SET status='APPROVED'"
                    " WHERE id=?", (prof["id"],)
                )

        # Si c'est un livreur/chauffeur : s'assurer qu'il existe dans drivers
        if role in ("LIVREUR_MOTO", "CHAUFFEUR"):
            driver = conn.execute(
                "SELECT id FROM drivers WHERE email = ?", (email,)
            ).fetchone()
            if driver:
                conn.execute(
                    "UPDATE drivers SET is_active=1, name=?, phone=? WHERE id=?",
                    (name, phone, driver["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO drivers (name, phone, email, is_active, created_at)"
                    " VALUES (?, ?, ?, 1, ?)",
                    (name, phone, email, now),
                )
                print("        [OK] driver cree et actif")

    conn.commit()
    conn.close()

    print()
    print("=" * 70)
    print("COMPTES PRETS — MOT DE PASSE COMMUN : " + PWD)
    print("=" * 70)
    print()
    print("  ROLE              EMAIL                      MOT DE PASSE")
    print("  " + "-" * 66)
    for email, phone, name, role in ACCOUNTS:
        print("  %-16s  %-24s  %s" % (role, email, PWD))
    print()
    print("PROCHAINE ETAPE :")
    print("  Ouvre /static/login.html sur iPhone et connecte-toi")
    print("  avec un de ces comptes selon le role a tester.")


if __name__ == "__main__":
    main()