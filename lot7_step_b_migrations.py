# -*- coding: utf-8 -*-
"""
LOT 7 - ETAPE B : Migrations DB
================================
Cree 3 nouvelles tables SANS toucher a l'existant :
  - stock_movements : historique des mouvements
  - stock_lots      : lots + peremptions
  - product_images  : galerie multi-images

Backup DB complet avant. Idempotent (re-executable).
"""
import os, sqlite3, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
DB = os.path.join(ROOT, "database.db")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_lot7_stepB_{TS}")
os.makedirs(BAK, exist_ok=True)

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]", "STEP": "\n###"}[k]
    print(p, m)

print("=" * 78)
print(f"LOT 7 - ETAPE B (MIGRATIONS DB) - {TS}")
print("=" * 78)

# ============================================================
# PHASE 0 : Backup
# ============================================================
log("PHASE 0 : Backup database.db", "STEP")
shutil.copy2(DB, os.path.join(BAK, "database.db"))
log(f"Backup : {BAK}\\database.db", "OK")

# ============================================================
# PHASE 1 : Creation des tables
# ============================================================
log("PHASE 1 : Creation des tables", "STEP")

conn = sqlite3.connect(DB)
cur = conn.cursor()

# --- Table stock_movements ---
cur.execute("""
CREATE TABLE IF NOT EXISTS stock_movements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL,
    type            TEXT NOT NULL,            -- IN, OUT, ADJUST, CANCEL
    quantity        INTEGER NOT NULL,          -- signe : + entree, - sortie
    reason          TEXT DEFAULT '',           -- motif (obligatoire pour ADJUST)
    reference       TEXT DEFAULT '',           -- ex: CMD-xxx, LOT-xxx
    user_id         INTEGER,                   -- auteur du mouvement
    created_at      TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id)
)
""")
log("Table stock_movements creee", "OK")

# --- Table stock_lots ---
cur.execute("""
CREATE TABLE IF NOT EXISTS stock_lots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL,
    lot_number      TEXT NOT NULL,             -- numero de lot
    expiry_date     TEXT,                       -- YYYY-MM-DD
    quantity        INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id)
)
""")
log("Table stock_lots creee", "OK")

# --- Table product_images ---
cur.execute("""
CREATE TABLE IF NOT EXISTS product_images (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL,
    file_path       TEXT NOT NULL,             -- /static/images/products/xxx.jpg
    is_primary      INTEGER NOT NULL DEFAULT 0,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id)
)
""")
log("Table product_images creee", "OK")

# --- Index pour performance ---
log("Index", "STEP")

cur.execute("CREATE INDEX IF NOT EXISTS idx_stock_mov_product ON stock_movements(product_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_stock_mov_created ON stock_movements(created_at)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_stock_lots_product ON stock_lots(product_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_stock_lots_expiry ON stock_lots(expiry_date)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_product_images_product ON product_images(product_id)")
log("5 index crees", "OK")

conn.commit()

# ============================================================
# PHASE 2 : Migration des images existantes
# ============================================================
log("PHASE 2 : Migration des images produits existantes", "STEP")

now = datetime.datetime.now().isoformat(timespec="seconds")
rows = cur.execute("""
    SELECT id, image_url FROM products
    WHERE image_url IS NOT NULL AND image_url != ''
""").fetchall()

migrated = 0
for pid, url in rows:
    # Verifier si deja migre
    existing = cur.execute(
        "SELECT id FROM product_images WHERE product_id = ? AND is_primary = 1",
        (pid,)
    ).fetchone()
    if existing:
        continue
    cur.execute("""
        INSERT INTO product_images (product_id, file_path, is_primary, sort_order, created_at)
        VALUES (?, ?, 1, 0, ?)
    """, (pid, url, now))
    migrated += 1

conn.commit()
log(f"{migrated} image(s) migree(s) vers product_images", "OK")

# ============================================================
# PHASE 3 : Verification
# ============================================================
log("PHASE 3 : Verification", "STEP")

# Structure des 3 tables
for tbl in ["stock_movements", "stock_lots", "product_images"]:
    cols = cur.execute(f"PRAGMA table_info({tbl})").fetchall()
    n = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    print(f"\n  [{tbl}] {n} ligne(s), {len(cols)} colonnes :")
    for c in cols:
        pk = " PK" if c[5] else ""
        nn = " NOT NULL" if c[3] else ""
        print(f"    - {c[1]:15s} {c[2]:10s}{pk}{nn}")

# Verification d'integrite
cur.execute("PRAGMA foreign_key_check")
fk_issues = cur.fetchall()
if fk_issues:
    log(f"Problemes FK : {len(fk_issues)}", "WARN")
else:
    log("Aucun probleme d'integrite", "OK")

conn.close()

# ============================================================
# RAPPORT
# ============================================================
print()
print("=" * 78)
print("RAPPORT")
print("=" * 78)
print(f"Backup : {BAK}")
print()
print("[OK] 3 tables creees, 5 index, images migrees")
print()
print("Tables creees :")
print("  - stock_movements : type (IN/OUT/ADJUST/CANCEL), quantity signee, reason, user_id")
print("  - stock_lots      : lot_number, expiry_date, quantity")
print("  - product_images  : file_path, is_primary, sort_order")
print()
print("Prochaines etapes :")
print("  1. Verifier avec : python check_lot7_db.py")
print("  2. Passer a l'etape C (API CRUD produits)")
print()
print("[ROLLBACK] :")
print(f"  copy \"{BAK}\\database.db\" \"{DB}\"")