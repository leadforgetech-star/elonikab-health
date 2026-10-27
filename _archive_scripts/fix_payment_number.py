"""
fix_payment_number.py
Corrige GET /api/orders/{ref}/payment pour renvoyer
payment_number et payment_name meme si aucun paiement n'est initie.
"""
from pathlib import Path
import datetime
import re
import shutil

BASE = Path(__file__).resolve().parent
PAY = BASE / "v3_modules" / "payments.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_pay_num_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(PAY, backup / "payments.py")
print("[OK] Backup ->", backup.name)

src = PAY.read_text(encoding="utf-8")

# Remplacer la fonction get_payment
pattern = re.compile(
    r'    @app\.get\("/api/orders/\{reference\}/payment"\).*?(?=\n    @app\.|\n    #|\Z)',
    re.DOTALL,
)

new_fn = '''    @app.get("/api/orders/{reference}/payment")
    def get_payment(reference: str, user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE reference = ? AND user_id = ?",
                (reference, user["id"]),
            ).fetchone()
            if order is None:
                raise HTTPException(404, "Commande introuvable")

            # Recuperer le paiement le plus recent (s'il existe)
            row = conn.execute(
                "SELECT * FROM payments WHERE order_id = ? ORDER BY id DESC LIMIT 1",
                (order["id"],),
            ).fetchone()

            # Recuperer les infos de config pharmacie
            settings = conn.execute(
                "SELECT payment_number, payment_name, whatsapp_number, pharmacy_phone"
                " FROM pharmacy_settings WHERE id = 1"
            ).fetchone()

            payment_number = ""
            payment_name = ""
            if settings:
                payment_number = (settings["payment_number"] or "").strip()
                payment_name = (settings["payment_name"] or "").strip()
                if not payment_number:
                    # Fallback : utiliser whatsapp ou phone
                    payment_number = (settings["whatsapp_number"] or "").strip()
                    if not payment_number:
                        payment_number = (settings["pharmacy_phone"] or "").strip()

            # Montant = subtotal + delivery_fee
            subtotal = float(order["subtotal"] or 0)
            delivery_fee = float(order["delivery_fee"] or 0)
            amount = round(subtotal + delivery_fee, 2)

            # Si un paiement existe, retourner ses donnees
            if row:
                result = _row(row)
                # Completer avec les infos de config au cas ou
                if not result.get("payment_number"):
                    result["payment_number"] = payment_number
                if not result.get("payment_name"):
                    result["payment_name"] = payment_name
                return result

            # Sinon : retourner un paiement virtuel avec toutes les infos
            return {
                "status": "NONE",
                "amount": amount,
                "payment_number": payment_number,
                "payment_name": payment_name,
                "payment_method": "MANUAL",
            }
        finally:
            conn.close()

'''

if pattern.search(src):
    src = pattern.sub(new_fn, src, count=1)
    PAY.write_text(src, encoding="utf-8")
    print("[OK] payments.py -> get_payment corrige")

    # Verification
    check = PAY.read_text(encoding="utf-8")
    if '"payment_number": payment_number' in check:
        print("[OK] Le fallback inclut payment_number")
    else:
        print("[!] Verification echouee")
else:
    print("[!] get_payment introuvable dans payments.py")

# ============================================================
# Corriger aussi les 2 caracteres non-ASCII dans payment.js
# ============================================================
PAYJS = BASE / "static" / "payment.js"
if PAYJS.exists():
    pjs = PAYJS.read_text(encoding="utf-8")
    # Remplacer le point median par un point normal dans les labels
    pjs = pjs.replace("\u00b7", "-")
    PAYJS.write_text(pjs, encoding="utf-8")
    print("[OK] payment.js -> caracteres non-ASCII remplaces")

print()
print("=" * 60)
print("FIX APPLIQUE")
print("=" * 60)
print()
print("1. Le serveur renvoie maintenant payment_number ET payment_name")
print("   meme si aucun paiement n'est encore initie.")
print()
print("2. Fallback automatique : si payment_number est vide, utilise")
print("   whatsapp_number ou pharmacy_phone.")
print()
print("3. payment.js : caracteres Unicode remplaces par '-'.")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print()
print("Puis sur iPhone : navigation privee, recharge la page paiement.")