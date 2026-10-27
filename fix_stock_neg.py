# -*- coding: utf-8 -*-
"""Fix : stock negatif + diagnostic client_availability."""
import os, re, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
MAIN = os.path.join(ROOT, "main.py")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_negstock_{TS}")
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
        return False, f"L{e.lineno}: {e.msg}"

shutil.copy2(MAIN, os.path.join(BAK, "main.py"))
print("=" * 78)
print(f"FIX STOCK NEGATIF - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

src = open(MAIN, "r", encoding="utf-8").read()

# ============================================================
# FIX 1 : Clamp stock a 0 si negatif
# ============================================================
log("FIX 1 : Clamp stock a 0", "INFO")

OLD = '''            delta = sign * qty
            new_qty = current + delta
            print(f"[TRACE-STOCK] product_id={pid} : {current} + ({delta}) = {new_qty}")
            conn.execute(
                "INSERT INTO stock_movements (product_id, type, quantity,"
                " reason, reference, user_id, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pid, mtype, delta, marker, reference, user_id, now)
            )
            conn.execute(
                "UPDATE products SET stock_quantity = ? WHERE id = ?",
                (new_qty, pid)
            )
            moved += 1'''

NEW = '''            delta = sign * qty
            new_qty = current + delta

            # Clamp a 0 si negatif (stock jamais negatif)
            warning_gap = 0
            if new_qty < 0:
                warning_gap = abs(new_qty)
                new_qty = 0
                print(f"[TRACE-STOCK] product_id={pid} : {current} + ({delta}) = NEGATIF -> clamp a 0 (manque {warning_gap})")
            else:
                print(f"[TRACE-STOCK] product_id={pid} : {current} + ({delta}) = {new_qty}")

            conn.execute(
                "INSERT INTO stock_movements (product_id, type, quantity,"
                " reason, reference, user_id, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pid, mtype, delta, marker, reference, user_id, now)
            )

            # Mouvement warning si on a clampe
            if warning_gap > 0:
                conn.execute(
                    "INSERT INTO stock_movements (product_id, type, quantity,"
                    " reason, reference, user_id, created_at)"
                    " VALUES (?, 'ADJUST', 0, ?, ?, ?, ?)",
                    (pid, f"ATTENTION : stock insuffisant, manque {warning_gap}",
                     reference, user_id, now)
                )

            conn.execute(
                "UPDATE products SET stock_quantity = ? WHERE id = ?",
                (new_qty, pid)
            )
            moved += 1'''

if "warning_gap = abs(new_qty)" in src:
    log("Clamp deja present", "WARN")
elif OLD in src:
    src = src.replace(OLD, NEW, 1)
    log("Clamp stock negatif ajoute", "OK")
else:
    log("Pattern clamp introuvable", "WARN")

open(MAIN, "w", encoding="utf-8").write(src)
ok, err = syntax_ok(MAIN)
if not ok:
    log(f"main.py ERREUR : {err}", "ERR")
    shutil.copy2(os.path.join(BAK, "main.py"), MAIN)
    sys.exit(1)
log("main.py syntaxe OK", "OK")

# ============================================================
# Diagnostic : client_availability est-il dans le code ?
# ============================================================
print()
log("DIAGNOSTIC client_availability", "INFO")

final = open(MAIN, "r", encoding="utf-8").read()
if "client_availability" in final:
    log("Code client_availability present dans main.py", "OK")
    # Compter les occurrences
    n = final.count("client_availability")
    print(f"    {n} occurrence(s) dans main.py")
else:
    log("client_availability ABSENT de main.py", "ERR")

# ============================================================
# Verification
# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)
checks = [
    ("Clamp stock a 0",          "warning_gap = abs(new_qty)" in final),
    ("Mouvement warning",        "ATTENTION : stock insuffisant" in final),
    ("client_availability",      "client_availability" in final),
    ("Syntaxe OK",               syntax_ok(MAIN)[0]),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

print()
print(f"[BACKUP] {BAK}")
print()
print("=" * 78)
print("COMMANDE UVICORN --reload")
print("=" * 78)
print()
print("  taskkill /F /IM uvicorn.exe 2>nul")
print("  taskkill /F /IM python.exe 2>nul")
print("  cd /d \"C:\\Users\\ELOGE KEY\\Desktop\\pharma\\pharmacie\"")
print("  python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir v3_modules --reload-dir static")
print()
print("  ⚠️ --reload-dir limite la surveillance a 2 dossiers (evite les backups)")
print()
print("[TEST] Apres restart :")
print("  1) Confirmer une commande avec produit 53 (stock=5)")
print("  2) Le stock doit passer a 4")
print("  3) Si commande de 10 : stock -> 0 + mouvement warning")
print()
print("  Pour client_availability : ouvre http://127.0.0.1:8000/api/products")
print("  et cherche 'client_availability' sur les 3 premiers produits")
print()
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\main.py" "{MAIN}"')