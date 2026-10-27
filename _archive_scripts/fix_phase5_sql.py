"""
fix_phase5_sql.py
Corrige les requetes SQL de payments.py qui referencent 'o.total'
(colonne inexistante). Remplace par subtotal + delivery_fee.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
PAY = BASE / "v3_modules" / "payments.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_v3_p5_sql_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(PAY, backup / "payments.py")
print("[OK] Backup ->", backup.name)

src = PAY.read_text(encoding="utf-8")
fixes = 0

# Fix 1 : list_payments
old1 = ('sql = ("SELECT p.*, o.reference AS order_reference,"\n'
        '                   " o.customer_name, o.phone, o.total, o.user_id"\n'
        '                   " FROM payments p JOIN orders o ON o.id = p.order_id")')
new1 = ('sql = ("SELECT p.*, o.reference AS order_reference,"\n'
        '                   " o.customer_name, o.phone, o.user_id,"\n'
        '                   " (COALESCE(o.subtotal,0) + COALESCE(o.delivery_fee,0)) AS total"\n'
        '                   " FROM payments p JOIN orders o ON o.id = p.order_id")')
if old1 in src:
    src = src.replace(old1, new1, 1)
    fixes += 1
    print("[OK] list_payments corrige")
else:
    print("[!] anchor list_payments introuvable")

# Fix 2 : get_payment_admin
old2 = ('row = conn.execute(\n'
        '                "SELECT p.*, o.reference AS order_reference, o.customer_name,"\n'
        '                " o.phone, o.total FROM payments p"\n'
        '                " JOIN orders o ON o.id = p.order_id WHERE p.id = ?",\n'
        '                (payment_id,),\n'
        '            ).fetchone()')
new2 = ('row = conn.execute(\n'
        '                "SELECT p.*, o.reference AS order_reference, o.customer_name,"\n'
        '                " o.phone, (COALESCE(o.subtotal,0) + COALESCE(o.delivery_fee,0)) AS total"\n'
        '                " FROM payments p JOIN orders o ON o.id = p.order_id WHERE p.id = ?",\n'
        '                (payment_id,),\n'
        '            ).fetchone()')
if old2 in src:
    src = src.replace(old2, new2, 1)
    fixes += 1
    print("[OK] get_payment_admin corrige")
else:
    print("[!] anchor get_payment_admin introuvable")

PAY.write_text(src, encoding="utf-8")

# Verification : plus aucune reference a o.total
check = PAY.read_text(encoding="utf-8")
if "o.total" in check:
    print("[!] ATTENTION : il reste encore des 'o.total' dans payments.py")
    # Afficher les lignes concernees
    for i, line in enumerate(check.splitlines(), 1):
        if "o.total" in line:
            print("    ligne " + str(i) + " : " + line.strip())
else:
    print("[OK] Aucune reference a 'o.total'")

print()
print("=" * 60)
print("Fix applique : " + str(fixes) + " requete(s) corrigee(s).")
print("=" * 60)
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  python main.py")
print("  python test_phase5.py   (dans un autre CMD)")