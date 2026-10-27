from pathlib import Path
import re
import shutil

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
APPJS = BASE / "static" / "app.js"

shutil.copy(MAIN, MAIN.with_suffix(".py.bak"))
shutil.copy(APPJS, APPJS.with_suffix(".js.bak"))
print("[OK] sauvegardes creees")

# =================================================================
# DIAGNOSTIC app.js
# =================================================================
js = APPJS.read_text(encoding="utf-8")
print()
print("=== DIAGNOSTIC app.js ===")
print("Taille :", len(js), "caracteres")
print("Lignes :", js.count("\n") + 1)
ob, cb = js.count("{"), js.count("}")
op, cp = js.count("("), js.count(")")
print("Accolades {} :", ob, "/", cb, "->", "OK" if ob == cb else "DESEQUILIBRE")
print("Parentheses () :", op, "/", cp, "->", "OK" if op == cp else "DESEQUILIBRE")

fns = ["function money", "function el", "function showView", "function apiGet",
       "function loadProducts", "function loadCategories", "function renderCatalog",
       "function renderProduct", "function renderConfirmation", "function submitOrder",
       "function initGeolocation", "function initDeliveryFeeDisplay",
       "function updateDeliveryFeeDisplay", "function haversineKm",
       "function loadSettings", "function init", "function attachSuggestions"]
for fn in fns:
    print("  %-40s %s" % (fn, "OK" if fn in js else "MANQUANT"))
print()

# =================================================================
# BACKEND : colonnes price + subtotal dans orders
# =================================================================
src = MAIN.read_text(encoding="utf-8")

# Migration
anchor_mig = '''    ord_cols2 = {row[1] for row in cur.execute("PRAGMA table_info(orders)").fetchall()}
    if "delivery_distance_km" not in ord_cols2:
        cur.execute("ALTER TABLE orders ADD COLUMN delivery_distance_km REAL")'''
new_mig = anchor_mig + '''
    if "price" not in ord_cols2:
        cur.execute("ALTER TABLE orders ADD COLUMN price REAL NOT NULL DEFAULT 0")
    if "subtotal" not in ord_cols2:
        cur.execute("ALTER TABLE orders ADD COLUMN subtotal REAL NOT NULL DEFAULT 0")'''
if anchor_mig in src and "ADD COLUMN price" not in src:
    src = src.replace(anchor_mig, new_mig, 1)
    print("[OK] main.py -> migration price + subtotal")
elif "ADD COLUMN price" in src:
    print("[i] main.py -> migration deja faite")
else:
    print("[!] anchor migration introuvable")

# Calcul subtotal
old_fee = '''    if delivery_mode == "livraison":
        delivery_fee, delivery_distance = compute_delivery_fee(latitude, longitude)
    else:
        delivery_fee = 0.0
        delivery_distance = None'''
new_fee = old_fee + '''
    subtotal = round(product["price"] * quantity, 2)'''
if old_fee in src and "subtotal = round" not in src:
    src = src.replace(old_fee, new_fee, 1)
    print("[OK] main.py -> calcul subtotal")

# INSERT : ajouter price + subtotal
old_ins = '''        " latitude, longitude, location_accuracy, delivery_fee, delivery_distance_km)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'en_attente', ?, ?, ?, ?, ?, ?)",
        (reference, name, phone_clean, product["id"], product["name"], quantity,
         delivery_mode, address.strip(), saved_file, created_at,
         latitude, longitude, location_accuracy, delivery_fee, delivery_distance),
    )'''
new_ins = '''        " latitude, longitude, location_accuracy, delivery_fee, delivery_distance_km,"
        " price, subtotal)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'en_attente', ?, ?, ?, ?, ?, ?, ?, ?)",
        (reference, name, phone_clean, product["id"], product["name"], quantity,
         delivery_mode, address.strip(), saved_file, created_at,
         latitude, longitude, location_accuracy, delivery_fee, delivery_distance,
         product["price"], subtotal),
    )'''
if old_ins in src and "price, subtotal)" not in src:
    src = src.replace(old_ins, new_ins, 1)
    print("[OK] main.py -> INSERT price + subtotal")
elif "price, subtotal)" in src:
    print("[i] main.py -> INSERT deja patche")

MAIN.write_text(src, encoding="utf-8")

# =================================================================
# FRONTEND : renderConfirmation + rappel apres GPS
# =================================================================

# 1) renderConfirmation : reecriture complete avec breakdown
start = js.find("function renderConfirmation(o) {")
if start == -1:
    print("[!] renderConfirmation introuvable")
else:
    depth = 0
    i = start
    end = -1
    while i < len(js):
        if js[i] == "{":
            depth += 1
        elif js[i] == "}":
            depth -= 1
            if depth == 0 and i > start:
                end = i + 1
                break
        i += 1
    if end == -1:
        print("[!] fin de renderConfirmation introuvable")
    else:
        new_fn = '''function renderConfirmation(o) {
  var box = $("#confirm-box");
  box.innerHTML = "";
  box.appendChild(el("div", "confirm-icon", "OK"));
  box.appendChild(el("h1", null, "Demande envoyee"));
  box.appendChild(el("p", "muted", "Votre demande a ete transmise a la pharmacie. Elle doit etre verifiee puis confirmee par un pharmacien avant delivrance."));

  var ref = el("div", "ref-box");
  ref.appendChild(el("span", "muted small", "Numero de demande"));
  ref.appendChild(el("strong", null, o.reference));
  box.appendChild(ref);

  var dl = el("dl", "summary");
  summaryRow(dl, "Client", o.customer_name);
  summaryRow(dl, "Telephone", o.phone);

  var qty = Number(o.quantity) || 1;
  var price = Number(o.price) || 0;
  var subtotal = (o.subtotal !== undefined && o.subtotal !== null)
    ? Number(o.subtotal) : (price * qty);
  var fee = Number(o.delivery_fee) || 0;
  var total = (o.total !== undefined && o.total !== null)
    ? Number(o.total) : (subtotal + fee);

  summaryRow(dl, "Produit", o.product_name + " (x" + qty + ")");
  if (o.delivery_distance_km !== null && o.delivery_distance_km !== undefined) {
    summaryRow(dl, "Distance", Number(o.delivery_distance_km).toFixed(1) + " km");
  }
  summaryRow(dl, "Sous-total", Math.round(subtotal).toLocaleString("fr-FR") + " FCFA");
  summaryRow(dl, "Livraison", Math.round(fee).toLocaleString("fr-FR") + " FCFA");
  summaryRow(dl, "Total", Math.round(total).toLocaleString("fr-FR") + " FCFA");
  summaryRow(dl, "Mode", o.delivery_mode === "livraison" ? "Livraison a domicile" : "Retrait en pharmacie");
  if (o.address) summaryRow(dl, "Adresse", o.address);
  summaryRow(dl, "Ordonnance", o.prescription_file ? "Jointe" : "Non jointe");
  summaryRow(dl, "Statut", "En attente de confirmation");
  box.appendChild(dl);

  var actions = el("div", "confirm-actions");
  var b1 = el("button", "btn btn-primary", "Retour au catalogue");
  b1.addEventListener("click", function () { goCatalog(""); });
  var b2 = el("button", "btn btn-ghost", "Nouvelle demande");
  b2.addEventListener("click", function () { goOrder(null); });
  actions.appendChild(b1);
  actions.appendChild(b2);
  box.appendChild(actions);
}'''
        js = js[:start] + new_fn + js[end:]
        print("[OK] app.js -> renderConfirmation avec breakdown")

# 2) Rappeler updateDeliveryFeeDisplay apres acquisition GPS
# Chercher la ligne de succes GPS et inserer l'appel
gps_success_anchor = 'btn.innerHTML = \'<span class="geo-icon">&#128205;</span> Actualiser ma localisation\';'
if gps_success_anchor in js and "updateDeliveryFeeDisplay();" not in js[js.find(gps_success_anchor)-500:js.find(gps_success_anchor)+200]:
    js = js.replace(
        gps_success_anchor,
        gps_success_anchor + '\n        if (typeof updateDeliveryFeeDisplay === "function") updateDeliveryFeeDisplay();',
        1
    )
    print("[OK] app.js -> recalcul frais apres GPS")
else:
    # Fallback : chercher une autre forme
    anchor2 = 'setStatus("&#10003; Localisation enregistree'
    idx = js.find(anchor2)
    if idx != -1:
        # Trouver la fin de la fonction onSuccess (prochain "}" ligne)
        seg = js[idx:idx+1500]
        end_idx = seg.find("\n    }")
        if end_idx != -1:
            insert_pos = idx + end_idx
            js = js[:insert_pos] + '\n      if (typeof updateDeliveryFeeDisplay === "function") updateDeliveryFeeDisplay();' + js[insert_pos:]
            print("[OK] app.js -> recalcul frais apres GPS (fallback)")

APPJS.write_text(js, encoding="utf-8")

print()
print("=======================================================")
print("Fix applique.")
print()
print("Redemarre le serveur puis Ctrl+Shift+R.")
print()
print("Pour le catalogue vide :")
print("  1. F12 -> Console -> cherche les lignes rouges")
print("  2. Si rien : navigation privee (Ctrl+Shift+N)")
print("     -> http://127.0.0.1:8000")
print("  3. Si en prive ca marche : vide le cache completement")
print("     (Ctrl+Shift+Suppr -> Images et fichiers en cache)")
print("=======================================================")