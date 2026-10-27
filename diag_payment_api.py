# -*- coding: utf-8 -*-
# diag_payment_api.py - Voir ce que retourne l'API payment + le calcul frais
import os, re, sqlite3, json

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
DB = os.path.join(ROOT, "database.db")
V3 = os.path.join(ROOT, "v3_modules")

# 1. Extraire le endpoint /api/orders/{ref}/payment dans payments.py
src = open(os.path.join(V3, "payments.py"), "r", encoding="utf-8").read()

print("=" * 78)
print("[1] Endpoint GET /api/orders/{reference}/payment")
print("=" * 78)
m = re.search(r'@app\.get\("/api/orders/\{reference\}/payment"\)[\s\S]*?(?=\n@app\.|\Z)', src)
if m:
    for line in m.group(0).split("\n")[:40]:
        print(f"  {line}")

# 2. Verifier ce que contient la DB pour la derniere commande avec paiement
print("\n" + "=" * 78)
print("[2] Dernier paiement en DB")
print("=" * 78)
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
rows = con.execute("""
    SELECT o.id as oid, o.reference, o.subtotal, o.delivery_fee, o.latitude, o.longitude,
           p.id as pid, p.status as pstatus, p.amount, p.proof_file, p.payment_method
    FROM orders o
    LEFT JOIN payments p ON p.order_id = o.id
    WHERE p.id IS NOT NULL
    ORDER BY o.id DESC LIMIT 3
""").fetchall()
for r in rows:
    print(f"\n  Commande {r['reference']} (id={r['oid']})")
    print(f"    sub={r['subtotal']}  livraison={r['delivery_fee']}")
    print(f"    lat={r['latitude']}  lon={r['longitude']}")
    print(f"    payment id={r['pid']}  status={r['pstatus']}")
    print(f"    amount={r['amount']}  method={r['payment_method']}")
    print(f"    proof_file={r['proof_file']}")

# 3. Verifier config pharmacie + calcul frais
print("\n" + "=" * 78)
print("[3] Config pharmacie (calcul frais)")
print("=" * 78)
s = con.execute("SELECT * FROM pharmacy_settings WHERE id=1").fetchone()
if s:
    for k in s.keys():
        if any(x in k.lower() for x in ["fee", "lat", "lon", "km", "moto", "car", "voiture"]):
            print(f"  {k} = {s[k]}")

# 4. Verifier items de la derniere commande
print("\n" + "=" * 78)
print("[4] Items de la derniere commande avec paiement")
print("=" * 78)
if rows:
    oid = rows[0]["oid"]
    items = con.execute("SELECT * FROM order_items WHERE order_id=?", (oid,)).fetchall()
    for it in items:
        print(f"  {it['quantity']}× {it['product_name']}  → {it['unit_price']} × {it['quantity']} = {it['subtotal']}")

# 5. Verifier timeline de la derniere commande
print("\n" + "=" * 78)
print("[5] Historique du dernier paiement")
print("=" * 78)
if rows and rows[0]["pid"]:
    pay_id = rows[0]["pid"]
    print(f"  Payment ID {pay_id} :")
    pay = con.execute("SELECT * FROM payments WHERE id=?", (pay_id,)).fetchone()
    for k in pay.keys():
        print(f"    {k} = {pay[k]}")

con.close()
print("\n" + "=" * 78)
print("FIN")
print("=" * 78)