# -*- coding: utf-8 -*-
"""Fix app.js : badges Rupture/Disponible/Stock faible + masquage bouton + limite qty."""
import os, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
APP = os.path.join(ROOT, "static", "app.js")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_appbadges_{TS}")
os.makedirs(BAK, exist_ok=True)

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]"}[k]
    print(p, m)

def brace_diff(s): return s.count("{") - s.count("}")

shutil.copy2(APP, os.path.join(BAK, "app.js"))
print("=" * 78)
print(f"FIX APP BADGES - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

src = open(APP, "r", encoding="utf-8").read()

# ============================================================
# 1. Remplacer availabilityTag : utiliser client_availability
# ============================================================
log("Fix 1 : availabilityTag", "INFO")

OLD_TAG = '''function availabilityTag(value) {
  var span = el("span", "tag");
  if (value === "disponible") {
    span.classList.add("tag-ok");
    span.textContent = "Disponible";
  } else {
    span.classList.add("tag-off");
    span.textContent = value === "rupture" ? "En rupture" : value;
  }
  return span;
}'''

NEW_TAG = '''function availabilityTag(p) {
  // LOT 7 : prend en compte client_availability + stock
  var span = el("span", "tag");
  var ca = (p && p.client_availability) ? p.client_availability : (p && p.availability);
  var sq = p ? p.stock_quantity : null;
  var minThresh = (p && p.stock_min_threshold) ? p.stock_min_threshold : 5;

  if (ca === "rupture" || (sq !== null && sq !== undefined && sq <= 0)) {
    span.classList.add("tag-off");
    span.textContent = "Rupture de stock";
    span.setAttribute("data-availability", "rupture");
  } else if (ca === "archive") {
    span.classList.add("tag-off");
    span.textContent = "Indisponible";
    span.setAttribute("data-availability", "archive");
  } else if (sq !== null && sq !== undefined && sq <= minThresh) {
    span.classList.add("tag-ok");
    span.style.background = "#FFF4E0";
    span.style.color = "#B26B00";
    span.textContent = "Stock faible (" + sq + ")";
    span.setAttribute("data-availability", "low");
  } else {
    span.classList.add("tag-ok");
    span.textContent = "Disponible";
    span.setAttribute("data-availability", "disponible");
  }
  return span;
}'''

if "data-availability" in src:
    log("availabilityTag deja patche", "WARN")
elif OLD_TAG in src:
    src = src.replace(OLD_TAG, NEW_TAG, 1)
    log("availabilityTag remplace", "OK")
else:
    log("availabilityTag pattern introuvable", "ERR")

# ============================================================
# 2. Appel : availabilityTag(p.availability) -> availabilityTag(p)
# ============================================================
log("Fix 2 : appel availabilityTag", "INFO")

OLD_CALL = 'row.appendChild(availabilityTag(p.availability));'
NEW_CALL = 'row.appendChild(availabilityTag(p));'

if OLD_CALL in src:
    src = src.replace(OLD_CALL, NEW_CALL, 1)
    log("Appel corrige", "OK")
elif NEW_CALL in src:
    log("Appel deja corrige", "WARN")
else:
    log("Appel pattern introuvable", "WARN")

# ============================================================
# 3. productCard : masquer bouton si rupture + limite qty
# ============================================================
log("Fix 3 : productCard - masquage rupture", "INFO")

OLD_IF = '''  if (p.availability === "disponible") {
    // Qty selector inline'''

NEW_IF = '''  var _available = (p.client_availability !== "rupture")
                && (p.stock_quantity === null || p.stock_quantity === undefined || p.stock_quantity > 0)
                && (p.is_active !== 0);

  if (_available) {
    // Qty selector inline'''

if "var _available = (p.client_availability" in src:
    log("productCard deja patche", "WARN")
elif OLD_IF in src:
    src = src.replace(OLD_IF, NEW_IF, 1)
    log("Condition masquage ajoutee", "OK")
else:
    log("productCard pattern introuvable", "WARN")

# ============================================================
# 4. Limite qtyInput.max au stock reel
# ============================================================
log("Fix 4 : limite qty au stock", "INFO")

OLD_MAX = '''    qtyInput.max = "99";
    qtyInput.value = "1";'''

NEW_MAX = '''    var _stockMax = (p.stock_quantity !== null && p.stock_quantity !== undefined)
                    ? Math.max(1, p.stock_quantity)
                    : 99;
    qtyInput.max = String(_stockMax);
    qtyInput.setAttribute("data-max-qty", String(_stockMax));
    qtyInput.value = "1";'''

if "_stockMax" in src:
    log("Limite qty deja patchee", "WARN")
elif OLD_MAX in src:
    src = src.replace(OLD_MAX, NEW_MAX, 1)
    log("Limite qty ajoutee", "OK")
else:
    log("Pattern qtyInput introuvable", "WARN")

# Aussi bloquer si on depasse dans getQty
OLD_GETQTY = '''    function getQty() {
      var n = parseInt(qtyInput.value, 10);
      if (isNaN(n) || n < 1) n = 1;
      if (n > 99) n = 99;
      qtyInput.value = String(n);
      return n;
    }'''

NEW_GETQTY = '''    function getQty() {
      var n = parseInt(qtyInput.value, 10);
      if (isNaN(n) || n < 1) n = 1;
      var _max = parseInt(qtyInput.max || "99", 10) || 99;
      if (n > _max) {
        n = _max;
        if (window.EHModal) window.EHModal.alert("Quantité limitée",
          "Maximum disponible : " + _max, "warn");
      }
      qtyInput.value = String(n);
      return n;
    }'''

if "Maximum disponible" in src:
    log("getQty deja patche", "WARN")
elif OLD_GETQTY in src:
    src = src.replace(OLD_GETQTY, NEW_GETQTY, 1)
    log("getQty : limite + message", "OK")
else:
    log("getQty pattern introuvable", "WARN")

# ============================================================
# 5. Classe CSS sur la carte si rupture (opacite + style)
# ============================================================
OLD_CARD = '''function productCard(p) {
  var card = el("article", "pt-product-card");'''
NEW_CARD = '''function productCard(p) {
  var card = el("article", "pt-product-card");
  // LOT 7 : classe si rupture (opacite + masquage boutons via CSS)
  if (p.client_availability === "rupture" || (p.stock_quantity !== null && p.stock_quantity !== undefined && p.stock_quantity <= 0)) {
    card.classList.add("eh-product-unavailable");
  }'''
if "eh-product-unavailable" in src and "if (p.client_availability" in src.split("function productCard")[1][:500] if "function productCard" in src else False:
    log("Classe rupture deja ajoutee", "WARN")
elif OLD_CARD in src:
    src = src.replace(OLD_CARD, NEW_CARD, 1)
    log("Classe eh-product-unavailable ajoutee", "OK")
else:
    log("productCard class pattern introuvable", "WARN")

# ============================================================
# 6. Verification equilibre
# ============================================================
diff = brace_diff(src)
if diff != 0:
    log(f"Deséquilibre ({diff}) - ROLLBACK", "ERR")
    shutil.copy2(os.path.join(BAK, "app.js"), APP)
    sys.exit(1)

open(APP, "w", encoding="utf-8").write(src)
log("app.js sauvegarde", "OK")

# ============================================================
# Verification
# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)
final = open(APP, "r", encoding="utf-8").read()
checks = [
    ("availabilityTag prend p",            "function availabilityTag(p)" in final),
    ("data-availability",                  "data-availability" in final),
    ("Badge rupture",                      "Rupture de stock" in final),
    ("Badge stock faible",                 "Stock faible" in final),
    ("Masquage bouton",                    "var _available = (p.client_availability" in final),
    ("Limite qty au stock",                "_stockMax" in final),
    ("Message quantite limitee",           "Maximum disponible" in final),
    ("Classe rupture carte",               "eh-product-unavailable" in final),
    ("Accolades equilibrees",              brace_diff(final) == 0),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

print()
print(f"[BACKUP] {BAK}")
print()
print("[CMD] Pas de restart Uvicorn (frontend only).")
print()
print("[TEST] Edge : F12 > Application > Clear site data + Ctrl+Shift+R")
print("  1) Page catalogue patient : badges Rupture/Disponible")
print("  2) Produit rupture : carte grisee + pas de bouton 'Ajouter'")
print("  3) Produit stock 3 : qtyInput limite a 3")
print()
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\app.js" "{APP}"')