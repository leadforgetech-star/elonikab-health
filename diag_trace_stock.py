# -*- coding: utf-8 -*-
"""
Ajoute des traces dans le helper pour voir ou ca bloque.
Puis reset une commande en_attente pour refaire un test propre.
"""
import os, re, sqlite3, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
MAIN = os.path.join(ROOT, "main.py")
DB = os.path.join(ROOT, "database.db")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_trace_{TS}")
os.makedirs(BAK, exist_ok=True)

shutil.copy2(MAIN, os.path.join(BAK, "main.py"))

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]"}[k]
    print(p, m)

print("=" * 78)
print(f"DIAG TRACE STOCK - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

# ============================================================
# 1. Enrichir le helper avec des traces
# ============================================================
log("PHASE 1 : Ajout de traces dans le helper", "INFO")
src = open(MAIN, "r", encoding="utf-8").read()

if "[TRACE-STOCK]" in src:
    log("Traces deja presentes", "WARN")
else:
    # Remplacer le try/except du helper
    OLD = '''def _apply_order_stock(conn, order_id, reference, action, user_id=None):
    """Applique une action stock. action='deduct' ou 'restore'.
    Idempotent : ne fait rien si le mouvement existe deja.
    """
    try:
        if action == "deduct":'''
    NEW = '''def _apply_order_stock(conn, order_id, reference, action, user_id=None):
    """Applique une action stock. action='deduct' ou 'restore'.
    Idempotent : ne fait rien si le mouvement existe deja.
    """
    print(f"[TRACE-STOCK] Entree : order={order_id} ref={reference} action={action} user={user_id}")
    try:
        if action == "deduct":'''

    if OLD in src:
        src = src.replace(OLD, NEW, 1)
        log("Trace d'entree ajoutee", "OK")
    else:
        log("Pattern helper introuvable", "WARN")

    # Remplacer le except final du helper
    OLD_ERR = '''        return {"ok": True, "action": action, "moved": moved, "skipped": skipped}
    except Exception as e:
        return {"ok": False, "error": str(e)}'''
    NEW_ERR = '''        print(f"[TRACE-STOCK] Sortie OK : moved={moved} skipped={skipped}")
        return {"ok": True, "action": action, "moved": moved, "skipped": skipped}
    except Exception as e:
        import traceback
        print(f"[TRACE-STOCK] ERREUR : {e}")
        traceback.print_exc()
        return {"ok": False, "error": str(e)}'''
    if OLD_ERR in src:
        src = src.replace(OLD_ERR, NEW_ERR, 1)
        log("Trace d'erreur ajoutee", "OK")
    else:
        log("Pattern except introuvable", "WARN")

    # Trace dans la boucle : voir chaque produit traite
    OLD_LOOP = '''        for it in items:
            pid = it["product_id"]
            qty = it["quantity"] or 1
            if not pid:
                continue
            prod = conn.execute(
                "SELECT id, stock_quantity FROM products WHERE id = ?", (pid,)
            ).fetchone()'''
    NEW_LOOP = '''        print(f"[TRACE-STOCK] {len(items)} item(s) a traiter")
        for it in items:
            pid = it["product_id"]
            qty = it["quantity"] or 1
            print(f"[TRACE-STOCK] item product_id={pid} qty={qty}")
            if not pid:
                continue
            prod = conn.execute(
                "SELECT id, stock_quantity FROM products WHERE id = ?", (pid,)
            ).fetchone()'''
    if OLD_LOOP in src:
        src = src.replace(OLD_LOOP, NEW_LOOP, 1)
        log("Trace dans la boucle ajoutee", "OK")

    # Trace quand on trouve NULL
    OLD_NULL = '''            if current is None:
                conn.execute(
                    "INSERT INTO stock_movements (product_id, type, quantity,"
                    " reason, reference, user_id, created_at)"
                    " VALUES (?, 'ADJUST', 0, ?, ?, ?, ?)",
                    (pid, marker + " (ignore : stock non renseigne)",
                     reference, user_id, now)
                )
                skipped += 1
                continue'''
    NEW_NULL = '''            if current is None:
                print(f"[TRACE-STOCK] product_id={pid} : stock NULL (skip deduit)")
                conn.execute(
                    "INSERT INTO stock_movements (product_id, type, quantity,"
                    " reason, reference, user_id, created_at)"
                    " VALUES (?, 'ADJUST', 0, ?, ?, ?, ?)",
                    (pid, marker + " (ignore : stock non renseigne)",
                     reference, user_id, now)
                )
                skipped += 1
                continue'''
    if OLD_NULL in src:
        src = src.replace(OLD_NULL, NEW_NULL, 1)
        log("Trace NULL ajoutee", "OK")

    # Trace avant UPDATE produit
    OLD_UPD = '''            delta = sign * qty
            new_qty = current + delta
            conn.execute(
                "INSERT INTO stock_movements (product_id, type, quantity,"'''
    NEW_UPD = '''            delta = sign * qty
            new_qty = current + delta
            print(f"[TRACE-STOCK] product_id={pid} : {current} + ({delta}) = {new_qty}")
            conn.execute(
                "INSERT INTO stock_movements (product_id, type, quantity,"'''
    if OLD_UPD in src:
        src = src.replace(OLD_UPD, NEW_UPD, 1)
        log("Trace UPDATE ajoutee", "OK")

open(MAIN, "w", encoding="utf-8").write(src)

# Valider syntaxe
try:
    with open(MAIN, "rb") as f:
        compile(f.read(), MAIN, "exec")
    log("main.py syntaxe OK", "OK")
except SyntaxError as e:
    log(f"ERREUR : {e}", "ERR")
    shutil.copy2(os.path.join(BAK, "main.py"), MAIN)
    sys.exit(1)

# ============================================================
# 2. Reset la commande CMD-261016-DF3AD9 a en_attente
# ============================================================
log("PHASE 2 : Reset commande a 'en_attente'", "INFO")
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("UPDATE orders SET status = 'en_attente' WHERE reference = 'CMD-261016-DF3AD9'")
conn.commit()
n = cur.rowcount
log(f"Commande reset ({n} ligne)", "OK")

# Afficher les stocks actuels des produits
for pid in [53, 68]:
    p = cur.execute("SELECT id, name, stock_quantity FROM products WHERE id = ?", (pid,)).fetchone()
    if p:
        print(f"  Produit {p[0]} '{p[1]}' : stock={p[2]}")

conn.close()

print()
print(f"[BACKUP] {BAK}")
print()
print("=" * 78)
print("ETAPES SUIVANTES")
print("=" * 78)
print()
print("1. Redemarre Uvicorn (pour prendre les traces) :")
print("   taskkill /F /IM uvicorn.exe 2>nul")
print("   taskkill /F /IM python.exe 2>nul")
print("   python -m uvicorn main:app --host 0.0.0.0 --port 8000")
print()
print("2. Dans un AUTRE terminal, refais le test :")
print("   python diag_stock_hook.py")
print()
print("3. Regarde le TERMINAL UVICORN : tu dois voir des lignes [TRACE-STOCK]")
print()
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\main.py" "{MAIN}"')