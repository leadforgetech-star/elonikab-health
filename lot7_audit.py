# -*- coding: utf-8 -*-
"""
LOT 7 - AUDIT PREALABLE
========================
Genere rapport_lot7_audit.txt :
- Structure DB (produits, stock, images)
- Routes existantes liees au catalogue
- Roles et permissions actuelles
- Emplacement des images produits
- Journal d'audit existant
"""
import os, re, sqlite3, datetime

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
DB = os.path.join(ROOT, "database.db")
STATIC = os.path.join(ROOT, "static")
V3 = os.path.join(ROOT, "v3_modules")
OUT = os.path.join(ROOT, "rapport_lot7_audit.txt")

lines = []
def hr(t): lines.append("=" * 78); lines.append(t); lines.append("=" * 78)
def sub(t): lines.append(""); lines.append("-" * 78); lines.append(t); lines.append("-" * 78)

lines.append("LOT 7 - AUDIT PREALABLE - " + datetime.datetime.now().isoformat(timespec="seconds"))

# 1. TABLES
hr("[1] TABLES SQLite")
if os.path.isfile(DB):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    lines.append(f"\n{len(tables)} tables :")
    for t in tables:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        lines.append(f"  - {t} ({n} lignes)")

    for tbl in ["products", "order_items", "orders", "audit_logs"]:
        if tbl in tables:
            sub(f"TABLE [{tbl}]")
            for c in cur.execute(f"PRAGMA table_info({tbl})").fetchall():
                pk = " PK" if c["pk"] else ""
                nn = " NOT NULL" if c["notnull"] else ""
                lines.append(f"  {c['name']:30s} {c['type']:15s}{pk}{nn}")
    conn.close()

# 2. ROUTES CATALOGUE
hr("[2] ROUTES API catalogue / produits")
pat = re.compile(r'@app\.(get|post|patch|put|delete|api_route)\s*\(\s*["\']([^"\']+)["\']', re.MULTILINE)
pat_prod = re.compile(r'/(products?|catalog|categories)', re.IGNORECASE)

for root, dirs, files in os.walk(ROOT):
    if any(x in root for x in ("_backup", "__pycache__", "_archive", "venv")): continue
    for f in files:
        if not f.endswith(".py") or f.startswith(("fix_","lot","test_","audit_","check_","dump_","pharm_","patch_","add_")): continue
        fpath = os.path.join(root, f)
        rel = os.path.relpath(fpath, ROOT)
        try: src = open(fpath, "r", encoding="utf-8", errors="ignore").read()
        except: continue
        for m in pat.finditer(src):
            if pat_prod.search(m.group(2)):
                ln = src[:m.start()].count("\n") + 1
                end = src.find("\n", m.end())
                fn_m = re.search(r"def\s+(\w+)", src[m.end():m.end()+300])
                fn = fn_m.group(1) if fn_m else "?"
                lines.append(f"  [{rel}:{ln}] {m.group(1).upper():6s} {m.group(2):45s} -> {fn}")

# 3. IMAGES
hr("[3] IMAGES PRODUITS")
for d in [os.path.join(STATIC, "images", "products"),
          os.path.join(STATIC, "images", "products", "medora"),
          os.path.join(STATIC, "images", "products", "pharma_dev")]:
    if os.path.isdir(d):
        files = os.listdir(d)
        sub(f"{d} ({len(files)} fichiers)")

# 4. ROLES
hr("[4] ROLES")
if os.path.isfile(DB):
    conn = sqlite3.connect(DB)
    for r in conn.execute("SELECT role, COUNT(*) FROM users GROUP BY role").fetchall():
        lines.append(f"  {r[0]:20s} : {r[1]} utilisateur(s)")
    conn.close()

# 5. STOCK
hr("[5] CHAMPS STOCK dans products")
if os.path.isfile(DB):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cols = conn.execute("PRAGMA table_info(products)").fetchall()
    stock_cols = [c["name"] for c in cols if any(k in c["name"].lower() for k in ["stock","lot","expir","quant"])]
    lines.append("  Colonnes liees : " + ", ".join(stock_cols) if stock_cols else "  (aucune)")
    conn.close()

# 6. AUDIT_LOGS
hr("[6] AUDIT_LOGS")
if os.path.isfile(DB):
    conn = sqlite3.connect(DB)
    for r in conn.execute("SELECT DISTINCT action FROM audit_logs ORDER BY action").fetchall():
        n = conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action = ?", (r[0],)).fetchone()[0]
        lines.append(f"  {r[0]:30s} ({n}x)")
    conn.close()

report = "\n".join(lines)
open(OUT, "w", encoding="utf-8").write(report)
print("=" * 78)
print(f"[OK] Rapport : {OUT}")
print(f"     {len(report)} caracteres")
print("=" * 78)