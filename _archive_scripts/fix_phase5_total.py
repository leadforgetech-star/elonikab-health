"""
fix_phase5_total.py
Corrige :
  1. cart.py : ajoute 'total' au retour de POST /api/orders/v2
  2. payments.py : calcule total = subtotal + delivery_fee (pas de colonne SQL)
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
CART = BASE / "v3_modules" / "cart.py"
PAY = BASE / "v3_modules" / "payments.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_v3_p5_fix_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(CART, backup / "cart.py")
shutil.copy2(PAY, backup / "payments.py")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. cart.py : ajouter 'total' au retour
# ============================================================
src = CART.read_text(encoding="utf-8")

old = '''        result = _row(row)
        result["items"] = [_row(i) for i in items]
        return result'''
new = '''        result = _row(row)
        result["items"] = [_row(i) for i in items]
        # total n'est pas une colonne SQL : on le calcule
        result["total"] = round(subtotal + delivery_fee, 2)
        result["delivery_fee"] = round(delivery_fee, 2)
        return result'''

if old in src:
    src = src.replace(old, new, 1)
    CART.write_text(src, encoding="utf-8")
    print("[OK] cart.py -> 'total' ajoute au retour")
elif '"total"]' in src:
    print("[i] cart.py deja patche")
else:
    print("[!] anchor retour cart introuvable")

# ============================================================
# 2. payments.py : idem pour init_payment + get_payment
# ============================================================
psrc = PAY.read_text(encoding="utf-8")

# 2a. init_payment
old_init = '''            now = datetime.now().isoformat(timespec="seconds")
            cur = conn.execute(
                "INSERT INTO payments (order_id, amount, payment_method,"
                " payment_number, payment_name, status, created_at)"
                " VALUES (?, ?, ?, ?, ?, 'PENDING', ?)",
                (order["id"], float(order["total"] or 0), method,
                 payment_number, payment_name, now),
            )'''
new_init = '''            # total n'est pas une colonne SQL : on le reconstruit
            subtotal = float(order["subtotal"] or 0)
            delivery_fee = float(order["delivery_fee"] or 0)
            total_amount = round(subtotal + delivery_fee, 2)

            now = datetime.now().isoformat(timespec="seconds")
            cur = conn.execute(
                "INSERT INTO payments (order_id, amount, payment_method,"
                " payment_number, payment_name, status, created_at)"
                " VALUES (?, ?, ?, ?, ?, 'PENDING', ?)",
                (order["id"], total_amount, method,
                 payment_number, payment_name, now),
            )'''
if old_init in psrc:
    psrc = psrc.replace(old_init, new_init, 1)
    print("[OK] payments.py -> init_payment corrige (calcul total)")
elif "total_amount" in psrc:
    print("[i] payments.py init deja patche")
else:
    print("[!] anchor init_payment introuvable")

# 2b. get_payment : renvoyer le total correct
old_get = '''        return _row(row) if row else {"status": "NONE", "amount": order["total"]}'''
new_get = '''        if row:
            return _row(row)
        subtotal = float(order["subtotal"] or 0)
        delivery_fee = float(order["delivery_fee"] or 0)
        return {"status": "NONE", "amount": round(subtotal + delivery_fee, 2)}'''
if old_get in psrc:
    psrc = psrc.replace(old_get, new_get, 1)
    print("[OK] payments.py -> get_payment corrige (fallback total)")
elif 'return {"status": "NONE"' in psrc and "subtotal" in psrc:
    print("[i] payments.py get_payment deja patche")
else:
    print("[!] anchor get_payment introuvable")

PAY.write_text(psrc, encoding="utf-8")

# ============================================================
# 3. Verification
# ============================================================
print()
print("=" * 60)
print("Fix applique.")
print("=" * 60)
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  python main.py")
print("  python test_phase5.py   (dans un autre CMD)")