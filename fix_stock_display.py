# -*- coding: utf-8 -*-
"""
Fix Stock : 
1. Mobile : le tableau Stock ne doit plus etre cache
2. "Non renseigne" au lieu de "Rupture" pour produits jamais inventoriees
"""
import os, sqlite3, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
CSS  = os.path.join(ROOT, "static", "catalogue.css")
JS   = os.path.join(ROOT, "static", "catalogue.js")
DB   = os.path.join(ROOT, "database.db")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_stockfix_{TS}")
os.makedirs(BAK, exist_ok=True)
shutil.copy2(CSS, os.path.join(BAK, "catalogue.css"))
shutil.copy2(JS,  os.path.join(BAK, "catalogue.js"))
shutil.copy2(DB,  os.path.join(BAK, "database.db"))

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]"}[k]
    print(p, m)

print("=" * 78)
print(f"FIX STOCK DISPLAY - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

# ============================================================
# FIX 1 : CSS - autoriser le scroll mobile sur stock
# ============================================================
log("FIX 1 : CSS mobile stock", "INFO")

css = open(CSS, "r", encoding="utf-8").read()

OLD_CSS = """@media (max-width:800px){
  .ph-cat-page, .ph-stk-page{padding:16px 12px 40px}
  .ph-cat-title, .ph-stk-title{font-size:20px}
  .ph-cat-table-wrap{display:none}
  .ph-cat-cards{display:block}
  .ph-form-2col{grid-template-columns:1fr}
}"""

NEW_CSS = """@media (max-width:800px){
  .ph-cat-page, .ph-stk-page{padding:16px 12px 40px}
  .ph-cat-title, .ph-stk-title{font-size:20px}
  /* Cache la table UNIQUEMENT sur la page catalogue (cartes a la place) */
  .ph-cat-page .ph-cat-table-wrap{display:none}
  .ph-cat-cards{display:block}
  .ph-form-2col{grid-template-columns:1fr}
  /* Sur la page Stock : table visible avec scroll horizontal */
  .ph-stk-page .ph-cat-table-wrap{
    overflow-x:auto;
    -webkit-overflow-scrolling:touch;
  }
  .ph-stk-page .ph-cat-table{min-width:600px}
}"""

if NEW_CSS in css:
    log("CSS deja patche", "WARN")
elif OLD_CSS in css:
    css = css.replace(OLD_CSS, NEW_CSS, 1)
    open(CSS, "w", encoding="utf-8").write(css)
    log("CSS mobile patche", "OK")
else:
    log("Bloc CSS introuvable", "WARN")

# ============================================================
# FIX 2 : Migrer stock_quantity = 0 -> NULL (jamais inventorie)
# ============================================================
log("FIX 2 : Migration stock non renseigne", "INFO")

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Produits avec stock=0 ET aucun mouvement = jamais inventorie
rows = cur.execute("""
    SELECT p.id, p.name
    FROM products p
    WHERE p.stock_quantity = 0
      AND NOT EXISTS (
        SELECT 1 FROM stock_movements m WHERE m.product_id = p.id
      )
""").fetchall()

n_migrate = len(rows)
cur.execute("""
    UPDATE products
    SET stock_quantity = NULL
    WHERE stock_quantity = 0
      AND id IN (
        SELECT p.id FROM products p
        WHERE NOT EXISTS (
          SELECT 1 FROM stock_movements m WHERE m.product_id = p.id
        )
      )
""")
conn.commit()
log(f"{n_migrate} produit(s) passes en 'non renseigne'", "OK")

conn.close()

# ============================================================
# FIX 3 : JS - distinguer N/R et Rupture
# ============================================================
log("FIX 3 : JS logique N/R vs Rupture", "INFO")

js = open(JS, "r", encoding="utf-8").read()

# --- renderStock : badge dans le tableau ---
OLD_TBL = '''          var badge = "";
          if (p.stock_quantity == null) badge = '<span class="ph-badge ph-badge-muted">N/R</span>';
          else if (p.stock_quantity <= 0) badge = '<span class="ph-badge ph-badge-danger">Rupture</span>';
          else if (p.stock_quantity <= (p.stock_min_threshold||5)) badge = '<span class="ph-badge ph-badge-warn">Faible</span>';
          else badge = '<span class="ph-badge ph-badge-ok">OK</span>';'''

NEW_TBL = '''          var badge = "";
          if (p.stock_quantity == null) badge = '<span class="ph-badge ph-badge-muted">Non renseigné</span>';
          else if (p.stock_quantity <= 0) badge = '<span class="ph-badge ph-badge-danger">Rupture</span>';
          else if (p.stock_quantity <= (p.stock_min_threshold||5)) badge = '<span class="ph-badge ph-badge-warn">Faible</span>';
          else badge = '<span class="ph-badge ph-badge-ok">OK</span>';'''

if NEW_TBL in js:
    log("Tableau deja patche", "WARN")
elif OLD_TBL in js:
    js = js.replace(OLD_TBL, NEW_TBL, 1)
    log("Tableau : N/R ajoute", "OK")
else:
    log("Tableau pattern introuvable", "WARN")

# --- renderStock : afficher la valeur dans la colonne stock ---
OLD_VAL = '''            '<td><strong>' + (p.stock_quantity == null ? "—" : p.stock_quantity) + '</strong></td>' +'''
NEW_VAL = '''            '<td><strong>' + (p.stock_quantity == null ? "N/R" : p.stock_quantity) + '</strong></td>' +'''
if NEW_VAL in js:
    log("Valeur deja patchee", "WARN")
elif OLD_VAL in js:
    js = js.replace(OLD_VAL, NEW_VAL, 1)
    log("Valeur N/R ajoutee", "OK")

# --- Catalogue : statut "Non renseigné" ---
OLD_CAT = '''          else if (p.stock_quantity == null) statusBadge = '<span class="ph-badge ph-badge-muted">Stock N/R</span>';'''
NEW_CAT = '''          else if (p.stock_quantity == null) statusBadge = '<span class="ph-badge ph-badge-muted">Non renseigné</span>';'''
if NEW_CAT in js:
    log("Catalogue deja patche", "WARN")
elif OLD_CAT in js:
    js = js.replace(OLD_CAT, NEW_CAT, 1)
    log("Catalogue : N/R ajoute", "OK")

# Verification equilibre
braces = js.count("{") - js.count("}")
if braces != 0:
    log(f"Deséquilibre JS ({braces}) - ROLLBACK", "ERR")
    shutil.copy2(os.path.join(BAK, "catalogue.js"), JS)
    shutil.copy2(os.path.join(BAK, "database.db"), DB)
    sys.exit(1)

open(JS, "w", encoding="utf-8").write(js)
log("catalogue.js sauvegarde", "OK")

# ============================================================
# Verification
# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)

conn = sqlite3.connect(DB)
n_null = conn.execute("SELECT COUNT(*) FROM products WHERE stock_quantity IS NULL").fetchone()[0]
n_zero = conn.execute("SELECT COUNT(*) FROM products WHERE stock_quantity = 0").fetchone()[0]
conn.close()

final_css = open(CSS, "r", encoding="utf-8").read()
final_js = open(JS, "r", encoding="utf-8").read()

checks = [
    ("CSS : stock table visible mobile",  "ph-stk-page .ph-cat-table-wrap" in final_css),
    ("JS : label Non renseigné",          "Non renseigné" in final_js),
    ("JS : valeur N/R affichee",          'stock_quantity == null ? "N/R"' in final_js),
    (f"DB : {n_null} produits N/R",       n_null > 0),
    (f"DB : {n_zero} vrais ruptures",     True),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

print()
print(f"[BACKUP] {BAK}")
print()
print("[CMD] Pas de restart Uvicorn (DB + front).")
print()
print("[TEST] Edge : F12 > Application > Clear site data + Ctrl+Shift+R")
print("  - Stock mobile : tableau visible avec scroll horizontal")
print("  - Alertes : RUPTURES devrait tomber a 0 (ou peu)")
print("  - Badge 'Non renseigné' visible pour les produits sans stock")
print()
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\catalogue.css" "{CSS}"')
print(f'  copy "{BAK}\\catalogue.js" "{JS}"')
print(f'  copy "{BAK}\\database.db" "{DB}"')