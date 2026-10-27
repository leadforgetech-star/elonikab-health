# -*- coding: utf-8 -*-
# diag_sse.py - Verifie si la notif a bien ete inseree en DB
import os, sqlite3

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
DB = os.path.join(ROOT, "database.db")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

print("=" * 70)
print("DIAG SSE")
print("=" * 70)

# 1. Dernieres notifications
print("\n[1] 10 dernieres notifications :")
rows = con.execute(
    "SELECT id, user_id, order_id, title, body, created_at"
    " FROM notifications ORDER BY id DESC LIMIT 10"
).fetchall()
if not rows:
    print("  (aucune notification)")
for r in rows:
    print(f"  id={r['id']}  user_id={r['user_id']}  order_id={r['order_id']}  "
          f"'{r['title']}'  {r['created_at']}")

# 2. Dernieres commandes
print("\n[2] 5 dernieres commandes :")
rows = con.execute(
    "SELECT id, reference, user_id, status, created_at"
    " FROM orders ORDER BY id DESC LIMIT 5"
).fetchall()
for r in rows:
    print(f"  id={r['id']}  ref={r['reference']}  user_id={r['user_id']}  "
          f"status={r['status']}  {r['created_at']}")

# 3. Users test
print("\n[3] Users test :")
rows = con.execute(
    "SELECT id, email, role FROM users WHERE email IN "
    "('patient@test.tg','pharmacien@test.tg','admin@test.tg')"
).fetchall()
for r in rows:
    print(f"  id={r['id']}  {r['email']}  ({r['role']})")

# 4. Diagnostic
print("\n[4] Diagnostic :")
last_order = con.execute(
    "SELECT id, reference, user_id FROM orders ORDER BY id DESC LIMIT 1"
).fetchone()
if last_order:
    uid = last_order["user_id"]
    notifs = con.execute(
        "SELECT COUNT(*) as n FROM notifications WHERE order_id=? AND user_id=?",
        (last_order["id"], uid)
    ).fetchone()
    print(f"  Derniere commande : {last_order['reference']}  (user_id={uid})")
    print(f"  Notifs pour cette commande : {notifs['n']}")

    if notifs["n"] == 0:
        print("  [!!] AUCUNE notif -> le push_notification n'a pas tourne")
        print("       => Uvicorn tourne probablement l'ANCIEN code")
        print("       => Restart Uvicorn OBLIGATOIRE")
    else:
        print("  [OK] notif presente en DB")
        print("       => SSE devrait la voir. Verifier cote front si le stream poll bien.")

con.close()
print("\n" + "=" * 70)