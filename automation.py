#!/usr/bin/env python3
"""
automation.py - Elonikab Health B2B
Automatise la preparation de l'architecture B2B (organisations, demandes,
pieces jointes) sans casser l'existant.

Usage :
    python automation.py            # analyse (check)
    python automation.py --check
    python automation.py --backup
    python automation.py --migrate
    python automation.py --test
    python automation.py --all      # backup + migrate + test
    python automation.py --restore <chemin_backup>
"""
import argparse
import importlib.util
import json
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================
DEFAULT_PROJECT = Path.home() / "Desktop" / "pharma" / "pharmacie"

REPORT = {"started_at": None, "ended_at": None,
          "steps": [], "errors": [], "warnings": [], "changed": []}


# ============================================================
# UTILITAIRES
# ============================================================
def log(msg, kind="info"):
    prefix = {"info": "[i]", "ok": "[OK]", "warn": "[!]", "err": "[ERR]"}.get(kind, "[i]")
    print(prefix + " " + msg)
    if kind == "err":
        REPORT["errors"].append(msg)
    elif kind == "warn":
        REPORT["warnings"].append(msg)


def find_project():
    """Detecte le dossier du projet."""
    candidates = [Path.cwd(), Path(__file__).resolve().parent, DEFAULT_PROJECT]
    for c in candidates:
        if (c / "main.py").exists() and (c / "database.db").exists():
            return c
    return None


def table_info(conn, table):
    """Retourne {colonne: type} pour une table, {} si absente."""
    try:
        rows = conn.execute("PRAGMA table_info(" + table + ")").fetchall()
        return {r[1]: r[2] for r in rows}
    except sqlite3.Error:
        return {}


def list_tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def has_column(conn, table, column):
    return column in table_info(conn, table)


# ============================================================
# ETAPE 1 : ANALYSE
# ============================================================
def step_check(project):
    log("Analyse du projet : " + str(project))
    report = {"project": str(project), "files": {}, "tables": {}, "missing": []}

    # Fichiers cles
    for f in ("main.py", "database.db", "requirements.txt"):
        p = project / f
        report["files"][f] = p.exists()
        if not p.exists():
            report["missing"].append(f)

    # Dossiers
    for d in ("static", "uploads", "v3_modules"):
        p = project / d
        report["files"][d + "/"] = p.exists()

    # Base
    conn = sqlite3.connect(str(project / "database.db"))
    try:
        tables = list_tables(conn)
        report["tables_count"] = len(tables)
        for t in ("users", "products", "orders", "order_items",
                  "professional_profiles", "payments", "prescriptions",
                  "notifications", "pharmacy_settings", "sessions"):
            report["tables"][t] = t in tables
    finally:
        conn.close()

    log("Tables existantes : " + str(report["tables_count"]))
    for t, ok in report["tables"].items():
        log("  - " + t + " : " + ("OK" if ok else "absent"), "ok" if ok else "warn")
    if report["missing"]:
        log("Fichiers manquants : " + ", ".join(report["missing"]), "warn")

    return report


# ============================================================
# ETAPE 2 : BACKUP
# ============================================================
def step_backup(project):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = project / "backups" / ("backup_" + ts)
    bdir.mkdir(parents=True, exist_ok=True)

    items = ["main.py", "database.db", "requirements.txt"]
    for name in items:
        src = project / name
        if src.exists():
            shutil.copy2(src, bdir / name)

    # Sauvegarder aussi v3_modules et static si petits
    for sub in ("v3_modules",):
        s = project / sub
        if s.exists() and s.is_dir():
            dst = bdir / sub
            dst.mkdir(exist_ok=True)
            for f in s.glob("*.py"):
                shutil.copy2(f, dst / f.name)

    log("Backup cree : " + str(bdir.relative_to(project)), "ok")
    REPORT["backup_dir"] = str(bdir)
    return bdir


# ============================================================
# ETAPE 3 : MIGRATIONS
# ============================================================
def step_migrate(project):
    db = project / "database.db"
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    changed = []

    try:
        # -----------------------------------------------------
        # 3.1 Extension de professional_profiles (organisations)
        # -----------------------------------------------------
        if "professional_profiles" in list_tables(conn):
            cols = table_info(conn, "professional_profiles")
            for cname, ctype in (
                ("delivery_address", "TEXT DEFAULT ''"),
                ("delivery_instructions", "TEXT DEFAULT ''"),
                ("billing_name", "TEXT DEFAULT ''"),
                ("billing_email", "TEXT DEFAULT ''"),
                ("tax_id", "TEXT DEFAULT ''"),
            ):
                if cname not in cols:
                    cur.execute(
                        "ALTER TABLE professional_profiles ADD COLUMN "
                        + cname + " " + ctype
                    )
                    changed.append("professional_profiles." + cname)
                    log("+ professional_profiles." + cname, "ok")

        # -----------------------------------------------------
        # 3.2 Extension de users (lien vers organisation)
        # -----------------------------------------------------
        if "users" in list_tables(conn):
            cols = table_info(conn, "users")
            if "organization_id" not in cols:
                cur.execute(
                    "ALTER TABLE users ADD COLUMN organization_id INTEGER"
                )
                changed.append("users.organization_id")
                log("+ users.organization_id", "ok")

        # -----------------------------------------------------
        # 3.3 Extension de orders (lien vers request)
        # -----------------------------------------------------
        if "orders" in list_tables(conn):
            cols = table_info(conn, "orders")
            for cname, ctype in (
                ("request_id", "INTEGER"),
                ("organization_id", "INTEGER"),
            ):
                if cname not in cols:
                    cur.execute(
                        "ALTER TABLE orders ADD COLUMN " + cname + " " + ctype
                    )
                    changed.append("orders." + cname)
                    log("+ orders." + cname, "ok")

        # -----------------------------------------------------
        # 3.4 Table REQUESTS (demandes B2B)
        # -----------------------------------------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT NOT NULL UNIQUE,
                organization_id INTEGER,
                user_id INTEGER,
                status TEXT NOT NULL DEFAULT 'DRAFT',
                notes TEXT DEFAULT '',
                source_summary TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        """)
        if "requests" not in [t for t in REPORT.get("_known_tables", [])]:
            log("+ table requests", "ok")
            changed.append("table:requests")

        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_requests_org ON requests(organization_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_requests_user ON requests(user_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(status)"
        )

        # -----------------------------------------------------
        # 3.5 Table REQUEST_ITEMS
        # -----------------------------------------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS request_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                product_id INTEGER,
                description TEXT NOT NULL,
                requested_quantity REAL DEFAULT 0,
                availability_status TEXT DEFAULT 'A_CONFIRMER',
                confirmed_quantity REAL,
                confirmed_unit_price REAL,
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE
            )
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_request_items_req ON request_items(request_id)"
        )

        # -----------------------------------------------------
        # 3.6 Table REQUEST_ATTACHMENTS (PDF, photo, autres)
        # -----------------------------------------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS request_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                organization_id INTEGER,
                type TEXT NOT NULL,
                original_filename TEXT DEFAULT '',
                storage_path TEXT NOT NULL,
                mime_type TEXT DEFAULT '',
                size_bytes INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE
            )
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_attachments_req ON request_attachments(request_id)"
        )

        # -----------------------------------------------------
        # 3.7 Table DOCUMENTS (factures, bons de livraison, etc.)
        # -----------------------------------------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER,
                order_id INTEGER,
                request_id INTEGER,
                type TEXT NOT NULL,
                storage_path TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_documents_org ON documents(organization_id)"
        )

        # -----------------------------------------------------
        # 3.8 Table NOTIFICATIONS_B2B (si notifications existante, on ne double pas)
        # -----------------------------------------------------
        if "notifications" in list_tables(conn):
            cols = table_info(conn, "notifications")
            if "organization_id" not in cols:
                cur.execute(
                    "ALTER TABLE notifications ADD COLUMN organization_id INTEGER"
                )
                changed.append("notifications.organization_id")
                log("+ notifications.organization_id", "ok")
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    organization_id INTEGER,
                    order_id INTEGER,
                    channel TEXT DEFAULT 'IN_APP',
                    type TEXT DEFAULT 'info',
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    is_read INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)

        conn.commit()
        log("Migration SQLite terminee (" + str(len(changed)) + " changement(s))", "ok")
        REPORT["changed"] = changed

    except Exception as e:
        conn.rollback()
        log("Erreur migration : " + str(e), "err")
        raise
    finally:
        conn.close()

    # Dossiers utiles
    for d in ("uploads/requests", "backups"):
        p = project / d
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            log("+ dossier " + d, "ok")

    return changed


# ============================================================
# ETAPE 4 : SYNTAXE PYTHON
# ============================================================
def step_syntax(project):
    ok = True
    for f in ("main.py",):
        p = project / f
        if not p.exists():
            continue
        r = subprocess.run(
            [sys.executable, "-m", "py_compile", str(p)],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            log("Syntaxe invalide dans " + f + " : " + r.stderr.strip(), "err")
            ok = False
        else:
            log("Syntaxe OK : " + f, "ok")

    moddir = project / "v3_modules"
    if moddir.exists():
        for f in moddir.glob("*.py"):
            r = subprocess.run(
                [sys.executable, "-m", "py_compile", str(f)],
                capture_output=True, text=True
            )
            if r.returncode != 0:
                log("Syntaxe invalide dans " + f.name, "err")
                ok = False
    return ok


# ============================================================
# ETAPE 5 : TESTS ENDPOINTS
# ============================================================
def step_test(project, port=8000, base_url=None):
    """Teste les endpoints essentiels. Necessite que le serveur tourne."""
    base = base_url or ("http://127.0.0.1:" + str(port))
    endpoints = [
        ("GET", "/", "page accueil"),
        ("GET", "/api/products", "catalogue"),
        ("GET", "/api/categories", "categories"),
        ("GET", "/api/settings", "parametres"),
        ("GET", "/api/auth/me", "auth (401 attendu si non connecte)"),
    ]
    results = []
    for method, path, label in endpoints:
        url = base + path
        try:
            req = urllib.request.Request(url, method=method)
            with urllib.request.urlopen(req, timeout=5) as resp:
                code = resp.status
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception as e:
            code = "ERR:" + type(e).__name__
        ok = (isinstance(code, int) and code < 500) or code == 401
        symbol = "OK" if ok else "FAIL"
        log("  " + label + " -> " + str(code) + " [" + symbol + "]",
            "ok" if ok else "warn")
        results.append({"endpoint": path, "code": code, "ok": ok})
    return results


# ============================================================
# ETAPE 6 : RESTORE
# ============================================================
def step_restore(project, backup_path):
    bdir = Path(backup_path)
    if not bdir.is_absolute():
        bdir = project / backup_path
    if not bdir.exists():
        log("Backup introuvable : " + str(bdir), "err")
        return False
    confirm = input("Restaurer depuis " + str(bdir) + " ? (oui/non) : ").strip().lower()
    if confirm != "oui":
        log("Restauration annulee par l'utilisateur", "warn")
        return False
    for name in ("database.db", "main.py", "requirements.txt"):
        src = bdir / name
        if src.exists():
            shutil.copy2(src, project / name)
            log("Restaure : " + name, "ok")
    return True


# ============================================================
# RAPPORT
# ============================================================
def print_report():
    print()
    print("=" * 66)
    print(" RAPPORT FINAL")
    print("=" * 66)
    print(" Backups :", REPORT.get("backup_dir", "aucun"))
    print(" Changements DB :", len(REPORT.get("changed", [])))
    for c in REPORT.get("changed", []):
        print("   +", c)
    print(" Erreurs :", len(REPORT["errors"]))
    for e in REPORT["errors"]:
        print("   !", e)
    print(" Avertissements :", len(REPORT["warnings"]))
    for w in REPORT["warnings"]:
        print("   ?", w)
    print("=" * 66)


# ============================================================
# MAIN
# ============================================================
def main():
    ap = argparse.ArgumentParser(description="Elonikab Health - automation B2B")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--backup", action="store_true")
    ap.add_argument("--migrate", action="store_true")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--restore", metavar="PATH")
    ap.add_argument("--project", metavar="DIR")
    args = ap.parse_args()

    REPORT["started_at"] = datetime.now().isoformat(timespec="seconds")

    project = Path(args.project).resolve() if args.project else find_project()
    if project is None or not (project / "main.py").exists():
        log("Projet introuvable. Utilise --project <chemin>", "err")
        print_report()
        return 2

    log("Projet : " + str(project))
    print()

    if args.restore:
        step_restore(project, args.restore)
        print_report()
        return 0

    # Par defaut -> check
    do_check = args.check or args.all or not (args.backup or args.migrate or args.test)
    do_backup = args.backup or args.all
    do_migrate = args.migrate or args.all
    do_test = args.test or args.all

    report_check = None
    if do_check:
        report_check = step_check(project)
        print()

    backup_dir = None
    if do_backup:
        backup_dir = step_backup(project)
        print()

    if do_migrate:
        if not backup_dir:
            backup_dir = step_backup(project)
            print()
        try:
            step_migrate(project)
        except Exception as e:
            log("Migration echouee : " + str(e), "err")
            if backup_dir:
                log("Restauration auto depuis le backup...", "warn")
                step_restore(project, str(backup_dir))
            print_report()
            return 1
        if not step_syntax(project):
            log("Syntaxe invalide apres migration", "err")
            print_report()
            return 1
        print()

    if do_test:
        log("Test des endpoints (serveur doit tourner sur :8000)", "info")
        step_test(project)
        print()

    REPORT["ended_at"] = datetime.now().isoformat(timespec="seconds")
    print_report()

    if REPORT["errors"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())