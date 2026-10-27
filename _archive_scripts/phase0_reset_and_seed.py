# phase0_reset_and_seed.py
# Phase 0 complete : backup + purge donnees dev + seed comptes de test
import os, sqlite3, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
DB   = os.path.join(ROOT, "database.db")

if not os.path.exists(DB):
    print(f"[ERREUR] {DB} introuvable"); sys.exit(1)

# ============================================================
# 1) BACKUP HORODATE
# ============================================================
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
bak_dir = os.path.join(ROOT, f"_backup_db_{ts}")
os.makedirs(bak_dir, exist_ok=True)
shutil.copy2(DB, os.path.join(bak_dir, "database.db"))
print(f"[BACKUP] {bak_dir}\\database.db")

# ============================================================
# 2) PURGE (ordre enfants -> parents)
# ============================================================
PURGE_ORDER = [
    "cart_items", "carts",
    "order_items", "order_status_history", "payments",
    "prescriptions", "receipts", "deliveries",
    "notifications",
    "request_attachments", "request_items", "requests",
    "orders",
    "magic_links", "sessions", "password_resets", "pending_uploads",
    "professional_profiles",
    "drivers", "driver_pins",
    "addresses",
    "audit_logs", "documents",
    "users",
]
KEEP = {"products", "pharmacy_settings", "sqlite_sequence"}

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()
cur.execute("PRAGMA foreign_keys = OFF")

existing = {r[0] for r in cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
)}

print("\n[PURGE]")
total = 0
for t in PURGE_ORDER:
    if t not in existing:
        print(f"  [SKIP] {t:<24} (absent)")
        continue
    n = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    cur.execute(f'DELETE FROM "{t}"')
    total += n
    print(f"  [OK]   {t:<24} {n} lignes")

try:
    cur.execute("DELETE FROM sqlite_sequence")
    print("  [OK]   sqlite_sequence")
except Exception as e:
    print(f"  [SKIP] sqlite_sequence : {e}")

con.commit()
print(f"[TOTAL] {total} lignes supprimees")

# ============================================================
# 3) SEED (comptes de test propres)
# ============================================================
sys.path.insert(0, ROOT)
try:
    from v3_modules.auth import hash_password
except Exception as e:
    print(f"\n[ERREUR] import hash_password : {e}")
    print("[INFO] La base est purgee mais le seed a echoue.")
    con.close(); sys.exit(1)

PWD = "Test1234"
now = datetime.datetime.now().isoformat(timespec="seconds")

cur.execute("PRAGMA foreign_keys = ON")

# Verif base videe
n = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
if n > 0:
    print(f"\n[ATTENTION] users non vide ({n} lignes). Seed annule.")
    con.close(); sys.exit(1)

def make_user(email, name, role, org_id=None):
    cur.execute("""
        INSERT INTO users
        (email, phone, password_hash, full_name, role, is_active, created_at, organization_id)
        VALUES (?, '', ?, ?, ?, 1, ?, ?)
    """, (email, hash_password(PWD), name, role, now, org_id))
    uid = cur.lastrowid
    print(f"  [SEED] {role:<15} id={uid:<3} {email}")
    return uid

print("\n[SEED]")
make_user("patient@test.tg", "Patient Test", "PATIENT")
make_user("pharmacien@test.tg", "Pharmacien Test", "PHARMACIEN")
make_user("admin@test.tg", "Admin Test", "ADMIN")

uid_pro = make_user("pro@test.tg", "Pro Test", "PROFESSIONNEL")

cur.execute("""
    INSERT INTO professional_profiles
    (user_id, structure_name, structure_type, manager_name, phone, email,
     address, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, 'APPROVED', ?)
""", (uid_pro, "Clinique Test", "CLINIQUE", "Pro Test",
      "+228 90 00 00 00", "pro@test.tg", "Lome", now))
pid = cur.lastrowid
print(f"  [SEED] ETABLISSEMENT  id={pid:<3} Clinique Test")

cur.execute("UPDATE users SET organization_id=? WHERE id=?", (pid, uid_pro))
print(f"  [SEED] user {uid_pro} lie a organization_id={pid}")

con.commit()

# ============================================================
# 4) VERIFICATION FINALE
# ============================================================
print("\n[INTEGRITE]")
integ = cur.execute("PRAGMA integrity_check").fetchone()[0]
fk_viol = cur.execute("PRAGMA foreign_key_check").fetchall()
print(f"  integrity_check    = {integ}")
print(f"  foreign_key_check  = {len(fk_viol)} violation(s)")

print("\n[ETAT FINAL]")
for t in sorted(existing):
    n = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    flag = "KEEP" if t in KEEP else ""
    print(f"  {t:<28} {n:>4} lignes  {flag}")

print("\n[USERS FINAUX]")
for r in cur.execute("SELECT id, email, role, organization_id FROM users ORDER BY id"):
    org = r["organization_id"] if r["organization_id"] else "-"
    print(f"  {r['id']:<3} {r['email']:<24} {r['role']:<15} org={org}")

con.close()
print("\n[DONE] Reset + seed termines.")
print("[INFO] Mot de passe commun : Test1234")