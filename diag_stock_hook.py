# -*- coding: utf-8 -*-
"""Diagnostic : pourquoi la deduction stock ne se declenche pas ?"""
import sqlite3, os, urllib.request, json, http.cookiejar

DB = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie\database.db"
BASE = "http://127.0.0.1:8000"

def login(email, pwd):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    req = urllib.request.Request(
        BASE + "/api/auth/login",
        data=json.dumps({"email": email, "password": pwd}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    op.open(req, timeout=10)
    return op

print("=" * 78)
print("DIAGNOSTIC STOCK HOOK")
print("=" * 78)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 1. La commande testee a-t-elle des items ?
print("\n[1] Derniere commande 'confirmee' et ses items")
orders = cur.execute("""
    SELECT o.id, o.reference, o.status, o.product_id, o.quantity, o.product_name
    FROM orders o
    WHERE o.status = 'confirmee'
    ORDER BY o.id DESC LIMIT 3
""").fetchall()

for o in orders:
    print(f"\n  Commande {o['reference']} (id={o['id']}) - status={o['status']}")
    print(f"    orders.product_id = {o['product_id']}, quantity = {o['quantity']}")
    items = cur.execute("SELECT product_id, quantity, product_name FROM order_items WHERE order_id = ?", (o["id"],)).fetchall()
    if not items:
        print(f"    ❌ AUCUN order_item -> deduction impossible")
    else:
        for it in items:
            print(f"    item: product_id={it['product_id']} qty={it['quantity']} '{it['product_name']}'")

# 2. Les mouvements de stock recents
print("\n[2] Derniers mouvements de stock (5)")
moves = cur.execute("""
    SELECT id, product_id, type, quantity, reason, reference, user_id, created_at
    FROM stock_movements
    ORDER BY id DESC LIMIT 5
""").fetchall()
if not moves:
    print("  ❌ AUCUN mouvement enregistre -> le hook n'est jamais appele")
else:
    for m in moves:
        print(f"  #{m['id']} product_id={m['product_id']} {m['type']} qty={m['quantity']} ref={m['reference']} reason={m['reason'][:40]}")

# 3. Logs d'audit recents
print("\n[3] Derniers audit_logs (10)")
logs = cur.execute("""
    SELECT id, user_id, action, target_type, target_id, substr(details,1,50) AS d, created_at
    FROM audit_logs ORDER BY id DESC LIMIT 10
""").fetchall()
for l in logs:
    print(f"  #{l['id']} {l['action']:25s} {l['target_type']}/{l['target_id']} {l['d']}")

conn.close()

# 4. Test direct : login pharmacien et fait un changement de statut
print("\n[4] Test direct : confirmer une commande 'en_attente'")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
row = cur.execute("""
    SELECT reference FROM orders WHERE status = 'en_attente'
    ORDER BY id DESC LIMIT 1
""").fetchone()
conn.close()

if not row:
    print("  ❌ Aucune commande 'en_attente' pour tester")
else:
    ref = row["reference"]
    print(f"  Reference : {ref}")
    try:
        op = login("pharmacien@test.tg", "Test1234")
        req = urllib.request.Request(
            BASE + f"/api/orders/{ref}/status",
            data=json.dumps({"status": "confirmee"}).encode(),
            headers={"Content-Type": "application/json"},
            method="PATCH")
        try:
            r = op.open(req, timeout=10)
            print(f"  PATCH status -> HTTP {r.status}")
            body = json.loads(r.read().decode())
            print(f"  Reponse : status={body.get('status')}")
        except urllib.error.HTTPError as e:
            print(f"  ❌ PATCH erreur HTTP {e.code}")
            print(f"  Detail : {e.read().decode()[:200]}")

        # Verifier immediatement
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        moves = cur.execute("""
            SELECT COUNT(*) FROM stock_movements WHERE reference = ?
        """, (ref,)).fetchone()[0]
        print(f"  Mouvements stock pour {ref} : {moves}")
        if moves > 0:
            print("  ✅ Le hook fonctionne !")
        else:
            print("  ❌ Le hook ne s'est PAS declenche")
        conn.close()
    except Exception as e:
        print(f"  ❌ Erreur : {e}")

print()
print("=" * 78)