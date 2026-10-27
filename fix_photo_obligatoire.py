# -*- coding: utf-8 -*-
"""Rend la photo obligatoire pour creer un produit."""
import os, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
JS   = os.path.join(ROOT, "static", "catalogue.js")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_photo_oblig_{TS}")
os.makedirs(BAK, exist_ok=True)
shutil.copy2(JS, os.path.join(BAK, "catalogue.js"))

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]"}[k]
    print(p, m)

print("=" * 78)
print(f"PHOTO OBLIGATOIRE - {TS}")
print("=" * 78)

src = open(JS, "r", encoding="utf-8").read()

# --- 1. Marquer le champ comme obligatoire ---
OLD_LBL = "'<div class=\"ph-form-row\"><label>Image principale <small style=\"color:#64748B;font-weight:400\">(optionnel)</small></label>'"
NEW_LBL = "'<div class=\"ph-form-row\"><label>Image principale <span style=\"color:#B23C3C\">*</span></label>'"

if OLD_LBL in src:
    src = src.replace(OLD_LBL, NEW_LBL, 1)
    log("Label change en obligatoire", "OK")
else:
    log("Label introuvable", "WARN")

# --- 2. Blocage a la creation sans image ---
OLD_CHECK = '''    if (!payload.name || payload.name.length < 2) { toast("Nom obligatoire", "err"); return; }
    if (isNaN(payload.price) || payload.price < 0) { toast("Prix invalide", "err"); return; }'''

NEW_CHECK = '''    if (!payload.name || payload.name.length < 2) { toast("Nom obligatoire", "err"); return; }
    if (isNaN(payload.price) || payload.price < 0) { toast("Prix invalide", "err"); return; }

    // Photo obligatoire pour la creation
    var isNewProduct = !editingProductId;
    var imgInputCheck = $("f-img-input");
    var hasFile = imgInputCheck && imgInputCheck.files && imgInputCheck.files[0];
    if (isNewProduct && !hasFile) {
      toast("Image obligatoire pour creer un produit", "err");
      return;
    }'''

if "Image obligatoire pour creer" in src:
    log("Check deja present", "WARN")
elif OLD_CHECK in src:
    src = src.replace(OLD_CHECK, NEW_CHECK, 1)
    log("Check photo obligatoire ajoute", "OK")
else:
    log("Bloc checks introuvable", "WARN")

# --- 3. Verification equilibre ---
braces = src.count("{") - src.count("}")
parens = src.count("(") - src.count(")")
if braces != 0 or parens != 0:
    log(f"Deséquilibre - ROLLBACK", "ERR")
    shutil.copy2(os.path.join(BAK, "catalogue.js"), JS)
    sys.exit(1)

open(JS, "w", encoding="utf-8").write(src)
log("catalogue.js sauvegarde", "OK")

print()
print("[BACKUP] " + BAK)
print("[CMD] Pas de restart Uvicorn.")
print("[TEST] F12 > Application > Clear site data + Ctrl+Shift+R")
print("  - Ajouter un produit sans photo -> toast rouge 'Image obligatoire'")
print("  - Ajouter un produit avec photo -> OK")