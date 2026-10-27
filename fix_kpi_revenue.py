# -*- coding: utf-8 -*-
"""Remplace le KPI 'Panier moyen' par 'Revenus du jour'."""
import os, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
MAIN = os.path.join(ROOT, "main.py")
JS   = os.path.join(ROOT, "static", "pharmacien_stats.js")

TS  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, "_backup_kpi_rev_" + TS)
os.makedirs(BAK, exist_ok=True)

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]"}[k]
    print(p, m)

def syntax_ok(path):
    try:
        with open(path, "rb") as f:
            compile(f.read(), path, "exec")
        return True, None
    except SyntaxError as e:
        return False, "L" + str(e.lineno) + ": " + e.msg

shutil.copy2(MAIN, os.path.join(BAK, "main.py"))
shutil.copy2(JS,   os.path.join(BAK, "pharmacien_stats.js"))

print("=" * 78)
print("FIX KPI REVENUE - " + TS)
print("=" * 78)
print("[BACKUP] " + BAK + "\n")

# ============================================================
# PHASE 1 : Backend - ajouter today_revenue
# ============================================================
log("PHASE 1 : Backend today_revenue", "INFO")

main_src = open(MAIN, "r", encoding="utf-8").read()

OLD_BK = '''        # Aujourd'hui
        today = datetime.now().strftime("%Y-%m-%d")
        today_orders = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE created_at LIKE ?",
            (today + "%",)
        ).fetchone()[0]'''

NEW_BK = '''        # Aujourd'hui
        today = datetime.now().strftime("%Y-%m-%d")
        today_orders = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE created_at LIKE ?",
            (today + "%",)
        ).fetchone()[0]

        # Revenus du jour (hors refusees)
        today_revenue = 0.0
        try:
            row = conn.execute(
                "SELECT COALESCE(SUM(subtotal + delivery_fee), 0) AS rev"
                " FROM orders WHERE created_at LIKE ? AND status != 'refusee'",
                (today + "%",)
            ).fetchone()
            today_revenue = float(row["rev"] or 0) if row else 0.0
        except Exception:
            pass'''

if "today_revenue" in main_src:
    log("Backend deja patche", "WARN")
elif OLD_BK in main_src:
    main_src = main_src.replace(OLD_BK, NEW_BK, 1)
    open(MAIN, "w", encoding="utf-8").write(main_src)
    ok, err = syntax_ok(MAIN)
    if not ok:
        log("main.py ERREUR : " + str(err), "ERR")
        shutil.copy2(os.path.join(BAK, "main.py"), MAIN)
        sys.exit(1)
    log("Backend : today_revenue ajoute", "OK")
else:
    log("Ancien bloc Aujourd'hui introuvable", "WARN")

# Ajouter today_revenue dans le dict de retour
OLD_RET = '''            "total_orders": total,
            "today_orders": today_orders,'''
NEW_RET = '''            "total_orders": total,
            "today_orders": today_orders,
            "today_revenue": today_revenue,'''

if '"today_revenue": today_revenue' in main_src:
    log("today_revenue deja dans le return", "WARN")
elif OLD_RET in main_src:
    main_src = open(MAIN, "r", encoding="utf-8").read()
    main_src = main_src.replace(OLD_RET, NEW_RET, 1)
    open(MAIN, "w", encoding="utf-8").write(main_src)
    ok, err = syntax_ok(MAIN)
    if not ok:
        log("main.py ERREUR : " + str(err), "ERR")
        shutil.copy2(os.path.join(BAK, "main.py"), MAIN)
        sys.exit(1)
    log("Backend : today_revenue dans return", "OK")
else:
    log("Bloc return introuvable", "WARN")

# ============================================================
# PHASE 2 : Frontend - remplacer KPI
# ============================================================
log("PHASE 2 : Frontend KPI", "INFO")

js_src = open(JS, "r", encoding="utf-8").read()

OLD_KPI = '''      '<div class="ph-kpi ph-kpi-money">' +
        '<span class="ph-kpi-ico">&#128176;</span>' +
        '<strong>' + fmtMoney(data.avg_basket || 0) + '</strong>' +
        '<small>Panier moyen</small>' +
      '</div>' +'''

NEW_KPI = '''      '<div class="ph-kpi ph-kpi-money ph-kpi-ok">' +
        '<span class="ph-kpi-ico">&#128176;</span>' +
        '<strong>' + fmtMoney(data.today_revenue || 0) + '</strong>' +
        '<small>Revenus aujourd&#39;hui</small>' +
      '</div>' +'''

if "Revenus aujourd" in js_src:
    log("JS deja patche", "WARN")
elif OLD_KPI in js_src:
    js_src = js_src.replace(OLD_KPI, NEW_KPI, 1)
    open(JS, "w", encoding="utf-8").write(js_src)
    log("JS : KPI Revenus du jour", "OK")
else:
    log("Ancien KPI panier moyen introuvable", "WARN")

# ============================================================
# Verification
# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)

fm = open(MAIN, "r", encoding="utf-8").read()
fj = open(JS,   "r", encoding="utf-8").read()

checks = [
    ("Backend : today_revenue calcule", "today_revenue = 0.0" in fm),
    ("Backend : today_revenue renvoye", '"today_revenue": today_revenue' in fm),
    ("Frontend : KPI Revenus",          "Revenus aujourd" in fj),
    ("Frontend : ancien retire",        "Panier moyen" not in fj),
]
for label, ok in checks:
    print("  [" + ("OK" if ok else "!!") + "] " + label)

print()
print("[BACKUP] " + BAK)
print()
print("[CMD] Restart Uvicorn OBLIGATOIRE (main.py modifie) :")
print("  taskkill /F /IM uvicorn.exe 2>nul")
print("  taskkill /F /IM python.exe 2>nul")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print()
print("[TEST] Edge : F12 > Application > Clear site data + Disable cache + Ctrl+Shift+R")
print("  1) /pharmacien -> onglet Stats")
print("  2) Le 3e KPI doit afficher : 'Revenus aujourd hui' avec le montant du jour")
print()
print("[ROLLBACK] :")
print('  copy "' + BAK + '\\main.py" "' + MAIN + '"')
print('  copy "' + BAK + '\\pharmacien_stats.js" "' + JS + '"')