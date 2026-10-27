"""diag_notif.py - Pourquoi la notification n'apparait pas ?"""
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "database.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

print("=" * 70)
print("DIAGNOSTIC NOTIFICATIONS")
print("=" * 70)
print()

# 1. User pro
print("[1] User pro@test.tg :")
u = conn.execute(
    "SELECT id, email, role FROM users WHERE email='pro@test.tg'"
).fetchone()
if u:
    print(f"    ID = {u['id']}  Email = {u['email']}  Role = {u['role']}")
    pro_id = u["id"]
else:
    print("    INTROUVABLE")
    pro_id = None
print()

# 2. Commandes du pro
print("[2] 5 dernieres commandes avec user_id + payment_status :")
rows = conn.execute("""
    SELECT id, reference, user_id, customer_name, status, payment_status, created_at
    FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 5
""", (pro_id,)).fetchall()
if rows:
    for r in rows:
        print(f"    {r['reference']}")
        print(f"      user_id={r['user_id']}  status={r['status']}  pay={r['payment_status']}")
        print(f"      client={r['customer_name']}  cree={r['created_at']}")
else:
    print("    Aucune commande pour ce pro")
print()

# 3. Commandes SANS user_id (orphelines)
print("[3] Commandes recentes SANS user_id (cote B) :")
rows = conn.execute("""
    SELECT id, reference, user_id, customer_name, status, payment_status, created_at
    FROM orders WHERE user_id IS NULL ORDER BY id DESC LIMIT 5
""").fetchall()
if rows:
    for r in rows:
        print(f"    {r['reference']}  status={r['status']}  pay={r['payment_status']}  client={r['customer_name']}")
else:
    print("    Aucune commande orpheline")
print()

# 4. Paiements recents
print("[4] 5 derniers paiements :")
rows = conn.execute("""
    SELECT p.id, p.order_id, o.reference AS order_ref, o.user_id,
           p.status, p.verified_at, p.verified_by
    FROM payments p JOIN orders o ON o.id = p.order_id
    ORDER BY p.id DESC LIMIT 5
""").fetchall()
if rows:
    for r in rows:
        print(f"    p.id={r['id']}  order={r['order_ref']}  order.user_id={r['user_id']}")
        print(f"      pay.status={r['status']}  verified_at={r['verified_at']}  by={r['verified_by']}")
else:
    print("    Aucun paiement")
print()

# 5. Notifications pro
print(f"[5] Notifications pour user_id={pro_id} :")
rows = conn.execute("""
    SELECT id, title, body, is_read, created_at
    FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT 10
""", (pro_id,)).fetchall()
print(f"    Total : {len(rows)}")
for r in rows:
    print(f"    #{r['id']}  [{r['is_read']}]  {r['title']}  ({r['created_at']})")
    print(f"        {r['body'][:80]}")
print()

# 6. Toutes les notifications recentes (tous users)
print("[6] Toutes les 10 dernieres notifications (tous users) :")
rows = conn.execute("""
    SELECT n.id, n.user_id, u.email, n.title, n.body, n.is_read, n.created_at
    FROM notifications n LEFT JOIN users u ON u.id = n.user_id
    ORDER BY n.id DESC LIMIT 10
""").fetchall()
print(f"    Total : {len(rows)}")
for r in rows:
    email = r["email"] or "(user inconnu)"
    print(f"    #{r['id']}  user_id={r['user_id']} ({email})  {r['title']}")
    print(f"        read={r['is_read']}  {r['created_at']}")
print()

conn.close()
print("=" * 70)
print("Colle-moi tout le resultat.")
print("=" * 70)