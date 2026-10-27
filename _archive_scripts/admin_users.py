"""
admin_users.py
Liste les comptes utilisateurs et les sessions actives.
Ne montre JAMAIS les mots de passe (haches, non reversibles).

Usage :
    python admin_users.py                  # liste tous les comptes
    python admin_users.py --sessions       # sessions actives
    python admin_users.py --reset <email>  # reinitialiser un mot de passe
    python admin_users.py --deactivate <email>
    python admin_users.py --activate <email>
"""
import argparse
import sqlite3
import secrets
import string
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from v3_modules.auth import hash_password

DB = BASE / "database.db"


def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def list_users():
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, email, phone, full_name, role, is_active, created_at"
            " FROM users ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        print("Aucun utilisateur.")
        return

    print("=" * 100)
    print("COMPTES UTILISATEURS")
    print("=" * 100)
    print("%-4s %-28s %-18s %-16s %-14s %-6s %s" % (
        "ID", "Email", "Nom", "Telephone", "Role", "Actif", "Cree le"))
    print("-" * 100)
    for r in rows:
        print("%-4d %-28s %-18s %-16s %-14s %-6s %s" % (
            r["id"],
            (r["email"] or "")[:28],
            (r["full_name"] or "")[:18],
            (r["phone"] or "")[:16],
            r["role"],
            "OUI" if r["is_active"] else "NON",
            (r["created_at"] or "")[:19],
        ))
    print("-" * 100)
    print("Total : " + str(len(rows)) + " comptes")


def list_sessions():
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT s.id, s.token, s.created_at, s.expires_at,"
            " u.email, u.full_name, u.role"
            " FROM sessions s JOIN users u ON u.id = s.user_id"
            " WHERE s.expires_at > ?"
            " ORDER BY s.id DESC",
            (datetime.now().isoformat(timespec="seconds"),),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        print("Aucune session active.")
        return

    print("=" * 110)
    print("SESSIONS ACTIVES")
    print("=" * 110)
    print("%-4s %-28s %-18s %-14s %-20s %s" % (
        "ID", "Email", "Nom", "Role", "Creee le", "Expire le"))
    print("-" * 110)
    for r in rows:
        print("%-4d %-28s %-18s %-14s %-20s %s" % (
            r["id"],
            (r["email"] or "")[:28],
            (r["full_name"] or "")[:18],
            r["role"],
            (r["created_at"] or "")[:19],
            (r["expires_at"] or "")[:19],
        ))
    print("-" * 110)
    print("Total : " + str(len(rows)) + " sessions actives")
    print()
    print("Note : le token n'est pas affiche (equivalent a un mot de passe).")


def reset_password(email, custom=None):
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id, email FROM users WHERE email = ?", (email.lower(),)
        ).fetchone()
        if row is None:
            print("[ERREUR] Aucun compte avec l'email :", email)
            return

        if custom:
            new_pwd = custom
        else:
            # Generer un mot de passe temporaire lisible
            alphabet = string.ascii_letters + string.digits
            new_pwd = "".join(secrets.choice(alphabet) for _ in range(10))

        try:
            pwd_hash = hash_password(new_pwd)
        except ValueError as e:
            print("[ERREUR]", e)
            return

        conn.execute(
            "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
            (pwd_hash, datetime.now().isoformat(timespec="seconds"), row["id"]),
        )
        # Invalider toutes les sessions actives de cet utilisateur
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (row["id"],))
        conn.commit()

        print("=" * 60)
        print("MOT DE PASSE REINITIALISE")
        print("=" * 60)
        print("Email        : " + row["email"])
        print("Nouveau mdp  : " + new_pwd)
        print()
        print("IMPORTANT : Transmettez ce mot de passe par un canal securise")
        print("            (SMS, en personne). L'utilisateur devra le changer.")
        print("            Toutes ses sessions actives ont ete deconnectees.")
    finally:
        conn.close()


def set_active(email, active):
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id, email FROM users WHERE email = ?", (email.lower(),)
        ).fetchone()
        if row is None:
            print("[ERREUR] Aucun compte avec l'email :", email)
            return
        conn.execute(
            "UPDATE users SET is_active = ?, updated_at = ? WHERE id = ?",
            (1 if active else 0, datetime.now().isoformat(timespec="seconds"), row["id"]),
        )
        # Si desactivation : virer toutes les sessions
        if not active:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (row["id"],))
        conn.commit()
        print(("[ACTIVE] " if active else "[DESACTIVE] ") + row["email"])
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser(description="Gestion des comptes Elokinab Health.")
    ap.add_argument("--sessions", action="store_true", help="Liste les sessions actives")
    ap.add_argument("--reset", metavar="EMAIL", help="Reinitialiser le mot de passe")
    ap.add_argument("--password", metavar="PWD", help="Mot de passe specifique (avec --reset)")
    ap.add_argument("--deactivate", metavar="EMAIL", help="Desactiver un compte")
    ap.add_argument("--activate", metavar="EMAIL", help="Reactiver un compte")
    args = ap.parse_args()

    if args.sessions:
        list_sessions()
    elif args.reset:
        reset_password(args.reset, args.password)
    elif args.deactivate:
        set_active(args.deactivate, False)
    elif args.activate:
        set_active(args.activate, True)
    else:
        list_users()


if __name__ == "__main__":
    main()