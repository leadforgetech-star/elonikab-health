# -*- coding: utf-8 -*-
"""
Lot 7 V2 : deduction a confirmation + restauration au refus + client_availability
=================================================================================
- Deduction : en_attente -> confirmee
- Restauration : (confirmee|en_preparation|prete) -> refusee
- Idempotent (jamais 2 fois le meme mouvement)
- Ajoute client_availability base sur stock_quantity
"""
import os, re, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
MAIN = os.path.join(ROOT, "main.py")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_stockv2_{TS}")
os.makedirs(BAK, exist_ok=True)

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]", "STEP": "\n###"}[k]
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
print(f"LOT 7 STOCK V2 - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

src = open(MAIN, "r", encoding="utf-8").read()

# ============================================================
# PHASE 1 : Remplacer le helper de deduction
# ============================================================
log("PHASE 1 : Remplacement du helper", "STEP")

start = src.find("def _deduct_order_stock(")
if start < 0:
    log("Ancien helper introuvable", "ERR"); sys.exit(1)

# Remonter aux commentaires du bloc
header_start = src.rfind("# LOT 7 - Deduction stock automatique", 0, start)
if header_start > 0:
    header_start = src.rfind("\n\n", 0, header_start) + 1
    start = header_start

# Trouver la fin de la fonction (3 sauts de ligne ou prochaine def)
end = src.find("\n\n\n", start + 100)
if end < 0:
    end = len(src)

NEW_HELPER = '''# ============================================================
# LOT 7 - Stock sur commande (confirmation / annulation)
# ============================================================
def _apply_order_stock(conn, order_id, reference, action, user_id=None):
    """Applique une action stock. action='deduct' ou 'restore'.
    Idempotent : ne fait rien si le mouvement existe deja.
    """
    try:
        if action == "deduct":
            marker = "Commande confirmee : " + reference
            mtype = "OUT"; sign = -1
        else:
            marker = "Annulation commande : " + reference
            mtype = "IN"; sign = 1

        # Idempotence
        existing = conn.execute(
            "SELECT id FROM stock_movements WHERE reference = ? AND reason = ? LIMIT 1",
            (reference, marker)
        ).fetchone()
        if existing:
            return {"ok": True, "already_done": True}

        # Recuperer les items
        items = conn.execute(
            "SELECT product_id, quantity FROM order_items WHERE order_id = ?",
            (order_id,)
        ).fetchall()
        if not items:
            row = conn.execute(
                "SELECT product_id, quantity FROM orders WHERE id = ?",
                (order_id,)
            ).fetchone()
            if row and row["product_id"]:
                items = [row]

        now = datetime.now().isoformat(timespec="seconds")
        moved = 0; skipped = 0

        for it in items:
            pid = it["product_id"]
            qty = it["quantity"] or 1
            if not pid:
                continue
            prod = conn.execute(
                "SELECT id, stock_quantity FROM products WHERE id = ?", (pid,)
            ).fetchone()
            if not prod:
                continue
            current = prod["stock_quantity"]
            if current is None:
                conn.execute(
                    "INSERT INTO stock_movements (product_id, type, quantity,"
                    " reason, reference, user_id, created_at)"
                    " VALUES (?, 'ADJUST', 0, ?, ?, ?, ?)",
                    (pid, marker + " (ignore : stock non renseigne)",
                     reference, user_id, now)
                )
                skipped += 1
                continue

            delta = sign * qty
            new_qty = current + delta
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
            moved += 1

        return {"ok": True, "action": action, "moved": moved, "skipped": skipped}
    except Exception as e:
        return {"ok": False, "error": str(e)}


'''

src = src[:start] + NEW_HELPER + src[end:]
log("Helper remplace", "OK")

# ============================================================
# PHASE 2 : Nouveau hook
# ============================================================
log("PHASE 2 : Hook confirmee + refusee", "STEP")

OLD_HOOK = '''
    # LOT 7 : deduction auto du stock quand la commande passe a 'prete'
    if new_status == "prete":
        try:
            _res = _deduct_order_stock(conn, row["id"], reference,
                                       user["id"] if user else None)
            if _res.get("deducted"):
                log_audit(conn, user["id"] if user else None,
                          "stock.auto_deduct", "order", row["id"],
                          "deduit=" + str(_res["deducted"]) + " ignore=" + str(_res.get("skipped", 0)))
        except Exception as _e:
            print(f"[stock-deduct] erreur : {_e}")'''

NEW_HOOK = '''
    # LOT 7 : gestion stock sur confirmation / annulation
    _uid = user["id"] if user else None
    if new_status == "confirmee" and current_status == "en_attente":
        try:
            _res = _apply_order_stock(conn, row["id"], reference, "deduct", _uid)
            if _res.get("moved"):
                log_audit(conn, _uid, "stock.deduct", "order", row["id"],
                          "moved=" + str(_res["moved"]))
        except Exception as _e:
            print(f"[stock-deduct] erreur : {_e}")

    if new_status == "refusee" and current_status in ("confirmee", "en_preparation", "prete"):
        try:
            _res = _apply_order_stock(conn, row["id"], reference, "restore", _uid)
            if _res.get("moved"):
                log_audit(conn, _uid, "stock.restore", "order", row["id"],
                          "moved=" + str(_res["moved"]))
        except Exception as _e:
            print(f"[stock-restore] erreur : {_e}")'''

if 'new_status == "confirmee" and current_status == "en_attente"' in src:
    log("Hook deja patche", "WARN")
elif OLD_HOOK in src:
    src = src.replace(OLD_HOOK, NEW_HOOK, 1)
    log("Hook remplace", "OK")
else:
    # Fallback regex
    m = re.search(r'\n    # LOT 7 : deduction auto du stock.*?print\(f"\[stock-deduct\] erreur : \{_e\}"\)', src, re.DOTALL)
    if m:
        src = src.replace(m.group(0), NEW_HOOK, 1)
        log("Hook remplace (fallback)", "OK")
    else:
        log("Hook introuvable", "ERR")

# ============================================================
# PHASE 3 : client_availability
# ============================================================
log("PHASE 3 : client_availability", "STEP")

OLD_CAN = '''        d["can_order"] = bool(
            is_active == 1
            and avail != "rupture"
            and (sq is None or sq > 0)
        )
        result.append(d)'''

NEW_CAN = '''        # LOT 7 : dispo cote client (basee sur stock)
        if is_active != 1:
            d["client_availability"] = "archive"
        elif sq is not None and sq <= 0:
            d["client_availability"] = "rupture"
        else:
            d["client_availability"] = "disponible"

        d["can_order"] = bool(is_active == 1 and d["client_availability"] == "disponible")
        result.append(d)'''

if "client_availability" in src:
    log("client_availability deja present", "WARN")
elif OLD_CAN in src:
    src = src.replace(OLD_CAN, NEW_CAN, 1)
    log("client_availability ajoute", "OK")
else:
    log("Pattern can_order introuvable", "WARN")

# ============================================================
# Sauvegarde + validation
# ============================================================
open(MAIN, "w", encoding="utf-8").write(src)
ok, err = syntax_ok(MAIN)
if not ok:
    log(f"main.py ERREUR : {err}", "ERR")
    shutil.copy2(os.path.join(BAK, "main.py"), MAIN)
    sys.exit(1)
log("main.py syntaxe OK", "OK")

print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)
final = open(MAIN, "r", encoding="utf-8").read()
checks = [
    ("Helper _apply_order_stock",       "_apply_order_stock" in final),
    ("Plus de _deduct_order_stock",     "_deduct_order_stock" not in final),
    ("Hook confirmee (deduct)",         'new_status == "confirmee" and current_status == "en_attente"' in final),
    ("Hook refusee (restore)",          'new_status == "refusee" and current_status in ("confirmee"' in final),
    ("client_availability",             "client_availability" in final),
    ("Syntaxe OK",                      syntax_ok(MAIN)[0]),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

print()
print(f"[BACKUP] {BAK}")
print()
print("[CMD] Restart Uvicorn :")
print("  taskkill /F /IM uvicorn.exe 2>nul")
print("  taskkill /F /IM python.exe 2>nul")
print("  python -m uvicorn main:app --host 0.0.0.0 --port 8000")
print()
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\main.py" "{MAIN}"')