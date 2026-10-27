"""
audit_suivi.py
Audit pre-refonte : analyse reelle des statuts, tables et routes.
"""
import sqlite3
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "database.db"
MAIN = BASE / "main.py"
MODULES = BASE / "v3_modules"


def header(title):
    print()
    print("=" * 70)
    print(" " + title)
    print("=" * 70)
    print()


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # 1. Tables existantes
    header("1. TABLES ET NOMBRE DE LIGNES")
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    for t in tables:
        try:
            n = conn.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
            print(f"  {t:30s} {n:>6d} lignes")
        except Exception:
            print(f"  {t:30s} ??? ")

    # 2. Schema orders
    header("2. COLONNES orders")
    cols = conn.execute("PRAGMA table_info(orders)").fetchall()
    for c in cols:
        print(f"  {c[1]:30s} {c[2]:10s}  default={c[4]}")

    # 3. Colonnes payments
    header("3. COLONNES payments")
    cols = conn.execute("PRAGMA table_info(payments)").fetchall()
    for c in cols:
        print(f"  {c[1]:30s} {c[2]:10s}  default={c[4]}")

    # 4. Colonnes requests
    header("4. COLONNES requests")
    cols = conn.execute("PRAGMA table_info(requests)").fetchall()
    for c in cols:
        print(f"  {c[1]:30s} {c[2]:10s}  default={c[4]}")

    # 5. Statuts reellement utilises
    header("5. VALEURS REELLES DES STATUTS")

    def distinct(col, table):
        try:
            rows = conn.execute(
                "SELECT " + col + ", COUNT(*) as n FROM " + table +
                " GROUP BY " + col + " ORDER BY n DESC"
            ).fetchall()
            if not rows:
                print(f"  [{table}.{col}] aucune donnee")
                return
            for r in rows:
                print(f"  [{table}.{col}] {str(r[0]):30s} {r[1]:>5d}")
        except Exception as e:
            print(f"  [{table}.{col}] ERREUR : {e}")

    distinct("status", "orders")
    print()
    distinct("payment_status", "orders")
    print()
    distinct("delivery_status", "orders")
    print()
    distinct("prescription_status", "orders")
    print()
    distinct("delivery_mode", "orders")
    print()
    distinct("customer_type", "orders")
    print()
    distinct("status", "payments")
    print()
    distinct("status", "requests")

    # 6. Sample des 5 dernieres commandes
    header("6. 5 DERNIERES COMMANDES")
    try:
        rows = conn.execute(
            "SELECT id, reference, status, payment_status, delivery_status,"
            " prescription_status, delivery_mode, customer_type, created_at,"
            " subtotal, delivery_fee"
            " FROM orders ORDER BY id DESC LIMIT 5"
        ).fetchall()
        for r in rows:
            print(f"  {r['reference']}")
            print(f"    status={r['status']} | pay={r['payment_status']} |"
                  f" del={r['delivery_status']} | presc={r['prescription_status']}")
            print(f"    mode={r['delivery_mode']} | type={r['customer_type']} |"
                  f" st={r['subtotal']} + {r['delivery_fee']}")
            print(f"    cree={r['created_at']}")
            print()
    except Exception as e:
        print("  Erreur :", e)

    # 7. Sample des 5 derniers paiements
    header("7. 5 DERNIERS PAIEMENTS")
    try:
        rows = conn.execute(
            "SELECT id, order_id, amount, status, created_at,"
            " submitted_at, verified_at, rejection_reason"
            " FROM payments ORDER BY id DESC LIMIT 5"
        ).fetchall()
        for r in rows:
            print(f"  id={r['id']} order_id={r['order_id']} "
                  f"amount={r['amount']} status={r['status']}")
            print(f"    cree={r['created_at']} submit={r['submitted_at']} "
                  f"verify={r['verified_at']}")
            if r['rejection_reason']:
                print(f"    refus={r['rejection_reason']}")
            print()
    except Exception as e:
        print("  Erreur :", e)

    # 8. Routes dans main.py
    header("8. ROUTES /api/orders, /api/payments, /api/requests (main.py)")
    src = MAIN.read_text(encoding="utf-8")
    routes = re.findall(
        r'@app\.(get|post|patch|delete)\("(/api/(?:orders|payments|requests)[^"]*)"',
        src
    )
    for method, path in routes:
        print(f"  {method.upper():7s} {path}")

    # 9. Routes dans les modules
    header("9. ROUTES DANS v3_modules/")
    if MODULES.exists():
        for mod in sorted(MODULES.glob("*.py")):
            text = mod.read_text(encoding="utf-8")
            routes = re.findall(
                r'@app\.(get|post|patch|delete)\("([^"]+)"',
                text
            )
            if routes:
                print(f"  --- {mod.name} ---")
                for method, path in routes:
                    print(f"    {method.upper():7s} {path}")

    # 10. Transitions de statut
    header("10. VARIABLES DE VALIDATION DE STATUTS")
    for mod in [MAIN] + sorted(MODULES.glob("*.py")):
        text = mod.read_text(encoding="utf-8")
        for var in ("ALLOWED_TRANSITIONS", "VALID_STATUSES",
                    "VALID_DRIVER_STATUSES", "VALID_ITEM_AVAILABILITY",
                    "VALID_TRANSITIONS", "NEXT_STATUS"):
            m = re.search(var + r'\s*=\s*(\{[^}]*\})', text, re.DOTALL)
            if m:
                print(f"  [{mod.name}] {var} =")
                block = m.group(1)
                # Couper les lignes longues
                for line in block.split("\n")[:15]:
                    print("    " + line.strip())

    # 11. Routes de la page /suivi et /commandes
    header("11. ROUTES PAGES (suivi, commandes)")
    for method, path in re.findall(
        r'@app\.(get)\("(/[^"]*)"', src
    ):
        if any(k in path for k in ("suivi", "commandes", "commande", "professionnel",
                                    "pharmacien", "acces", "connexion", "inscription")):
            print(f"  {method.upper():7s} {path}")

    # 12. Backend du suivi
    header("12. FICHIERS DU SUIVI")
    for f in ("static/suivi.html", "static/suivi.js", "static/suivi.css",
              "static/professional_commandes.html"):
        p = BASE / f
        if p.exists():
            size = p.stat().st_size
            print(f"  OK  {f} ({size} octets)")
        else:
            print(f"  [!] {f} MANQUANT")

    conn.close()

    header("FIN DE L'AUDIT")
    print("  Colle-moi l'integralite du resultat.")


if __name__ == "__main__":
    main()