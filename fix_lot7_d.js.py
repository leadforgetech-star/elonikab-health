# -*- coding: utf-8 -*-
"""Fix catalogue.js : URLs doublees + photo visible a la creation."""
import os, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
JS   = os.path.join(ROOT, "static", "catalogue.js")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_lot7_fix_{TS}")
os.makedirs(BAK, exist_ok=True)

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]"}[k]
    print(p, m)

shutil.copy2(JS, os.path.join(BAK, "catalogue.js"))
print("=" * 78)
print(f"FIX LOT 7 - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

src = open(JS, "r", encoding="utf-8").read()

# ============================================================
# FIX 1 : URLs doublees /api/api/
# ============================================================
log("FIX 1 : URLs doublees", "INFO")

fixes = [
    ('apiCall("GET", "/api/admin/stock")',                'apiCall("GET", "/admin/stock")'),
    ('apiCall("GET", "/api/admin/stock/alerts")',         'apiCall("GET", "/admin/stock/alerts")'),
    ('apiCall("GET", "/api/admin/stock/movements?limit=50")',
     'apiCall("GET", "/admin/stock/movements?limit=50")'),
    ('apiCall("POST", "/api/admin/products"',             'apiCall("POST", "/admin/products"'),
    ('apiCall("PATCH", "/api/admin/products/"',           'apiCall("PATCH", "/admin/products/"'),
    ('apiCall("DELETE", "/api/admin/products/"',          'apiCall("DELETE", "/admin/products/"'),
    ('apiCall("POST", "/api/admin/stock/movements", payload)',
     'apiCall("POST", "/admin/stock/movements", payload)'),
    ('fetch(API + "/api/admin/products/" + pid + "/images"',
     'fetch(API + "/admin/products/" + pid + "/images"'),
]

n_fixed = 0
for old, new in fixes:
    if old in src:
        src = src.replace(old, new)
        n_fixed += 1
        log(f"  Corrige : {old[:60]}...", "OK")

if n_fixed == 0:
    log("Aucune URL a corriger (deja fait ?)", "WARN")

# ============================================================
# FIX 2 : Photo visible pour create + edit, optionnelle
# ============================================================
log("FIX 2 : Photo optionnelle a la creation", "INFO")

OLD_IMG = '''        (product ? (
          '<div class="ph-form-row"><label>Image principale</label>' +
          '<div class="ph-image-preview" id="f-img-prev">' +
            (product.image_url ? '<img src="' + esc(product.image_url) + '">' : '📷') +
          '</div>' +
          '<input type="file" id="f-img-input" accept="image/jpeg,image/png,image/webp" style="margin-top:6px;font-size:12px">' +
          '</div>'
        ) : '') +'''

NEW_IMG = '''        '<div class="ph-form-row"><label>Image principale <small style="color:#64748B;font-weight:400">(optionnel)</small></label>' +
          '<div class="ph-image-preview" id="f-img-prev">' +
            (product && product.image_url ? '<img src="' + esc(product.image_url) + '">' : '📷') +
          '</div>' +
          '<input type="file" id="f-img-input" accept="image/jpeg,image/png,image/webp" style="margin-top:6px;font-size:12px">' +
          '<small style="color:#94A3B8;font-size:11.5px;display:block;margin-top:4px">Formats acceptés : JPG, PNG, WEBP — max 5 Mo</small>' +
        '</div>' +'''

if 'Image principale <small' in src:
    log("Photo deja patchee", "WARN")
elif OLD_IMG in src:
    src = src.replace(OLD_IMG, NEW_IMG, 1)
    log("Photo visible a la creation", "OK")
else:
    log("Bloc photo introuvable", "WARN")

# ============================================================
# Verification
# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)

# Equilibre accolades
braces = src.count("{") - src.count("}")
parens = src.count("(") - src.count(")")

checks = [
    ("URL /admin/stock corrigee",         '"GET", "/admin/stock"' in src),
    ("URL alerts corrigee",               '"GET", "/admin/stock/alerts"' in src),
    ("URL movements corrigee",            '"GET", "/admin/stock/movements?limit=50"' in src),
    ("URL products corrigee",             '"POST", "/admin/products"' in src),
    ("URL upload corrigee",               'API + "/admin/products/"' in src),
    ("Plus de /api/api/",                 '/api/api/' not in src),
    ("Photo visible a la creation",       'Image principale <small' in src),
    ("Photo marquee optionnelle",         '(optionnel)' in src),
    ("Accolades equilibrees",             braces == 0),
    ("Parens equilibres",                 parens == 0),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

print()
if braces == 0 and parens == 0:
    open(JS, "w", encoding="utf-8").write(src)
    log("catalogue.js sauvegarde", "OK")
else:
    log(f"Deséquilibre ({braces} accolades, {parens} parens) - ROLLBACK", "ERR")
    shutil.copy2(os.path.join(BAK, "catalogue.js"), JS)
    sys.exit(1)

print()
print(f"[BACKUP] {BAK}")
print()
print("[CMD] Pas de restart Uvicorn (front uniquement).")
print()
print("[TEST] Edge : F12 > Application > Clear site data + Ctrl+Shift+R")
print("  1) Onglet Stock : plus de 404, tout se charge")
print("  2) Onglet Catalogue -> 'Ajouter' : champ 'Image principale (optionnel)' visible")
print()
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\catalogue.js" "{JS}"')