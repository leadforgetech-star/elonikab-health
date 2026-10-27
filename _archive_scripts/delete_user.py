"""
delete_user.py - Suppression propre d'un compte utilisateur.
Usage : python delete_user.py 13 --commit
"""
import argparse
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "database.db"


def find_user(conn, key):
    if str(key).isdigit():
        return conn.execute("SELECT * FROM users WHERE id = ?", (int(key),)).fetchone()
    return conn.execute("SELECT * FROM users WHERE email = ?", (str(key).lower(),)).fetchone()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key")
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--keep-orders", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    user = find_user(conn, args.key)
    if user is None:
        print("[ERREUR] Utilisateur introuvable :", args.key)
        return 1

    uid = user["id"]
    email = user["email"]
    print("Utilisateur :", email, "(ID " + str(uid) + ")")

    if not args.commit:
        print("[DRY-RUN] Pour supprimer : python delete_user.py", args.key, "--commit")
        conn.close()
        return 0

    try:
        conn.execute("BEGIN")
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (uid,))

        cart = conn.execute("SELECT id FROM carts WHERE user_id = ?", (uid,)).fetchone()
        if cart:
            conn.execute("DELETE FROM cart_items WHERE cart_id = ?", (cart["id"],))
            conn.execute("DELETE FROM carts WHERE id = ?", (cart["id"],))

        conn.execute("DELETE FROM professional_profiles WHERE user_id = ?", (uid,))

        if args.keep_orders:
            conn.execute("UPDATE orders SET user_id = NULL WHERE user_id = ?", (uid,))
        else:
            for r in conn.execute("SELECT id FROM orders WHERE user_id = ?", (uid,)).fetchall():
                oid = r[0]
                conn.execute("DELETE FROM order_items WHERE order_id = ?", (oid,))
                conn.execute("DELETE FROM prescriptions WHERE order_id = ?", (oid,))
                conn.execute("DELETE FROM payments WHERE order_id = ?", (oid,))
                conn.execute("DELETE FROM deliveries WHERE order_id = ?", (oid,))
                conn.execute("DELETE FROM receipts WHERE order_id = ?", (oid,))
            conn.execute("DELETE FROM orders WHERE user_id = ?", (uid,))

        conn.execute("DELETE FROM notifications WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM users WHERE id = ?", (uid,))
        conn.commit()
        print("[OK] Compte supprime :", email)
    except Exception as e:
        conn.rollback()
        print("[ERREUR]", e)
        return 1
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())