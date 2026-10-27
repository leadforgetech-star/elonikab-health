# -*- coding: utf-8 -*-
"""
SPRINT A - AUDIT AVANT CODE
============================
Dump exhaustif de ce qui existe pour la livraison intelligente.
Aucune modification. Sortie dans sprintA_audit.txt
"""
import os, re, sqlite3, datetime

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
DB = os.path.join(ROOT, "database.db")
MAIN = os.path.join(ROOT, "main.py")
STATIC = os.path.join(ROOT, "static")
OUT = os.path.join(ROOT, "sprintA_audit.txt")

lines = []
def hr(t): lines.append("=" * 78); lines.append(t); lines.append("=" * 78)
def sub(t): lines.append(""); lines.append("-" * 78); lines.append(t); lines.append("-" * 78)

lines.append("SPRINT A - AUDIT LIVRAISON INTELLIGENTE - " + datetime.datetime.now().isoformat(timespec="seconds"))
lines.append("")

# ============================================================
# 1. CHAMPS pharmacy_settings
# ============================================================
hr("[1] pharmacy_settings : schema et valeurs")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cols = cur.execute("PRAGMA table_info(pharmacy_settings)").fetchall()
lines.append("\nSchema :")
for c in cols:
    lines.append(f"  {c['name']:30s} {c['type']:10s}" + (" PK" if c['pk'] else ""))

row = cur.execute("SELECT * FROM pharmacy_settings WHERE id = 1").fetchone()
if row:
    lines.append("\nValeurs actuelles :")
    for k in row.keys():
        v = row[k]
        lines.append(f"  {k:30s} = {v!r}")

# ============================================================
# 2. FONCTIONS de calcul dans main.py
# ============================================================
hr("[2] Fonctions de calcul de livraison dans main.py")

main_src = open(MAIN, "r", encoding="utf-8").read()

# haversine
sub("haversine_km")
m = re.search(r"def haversine_km[\s\S]*?(?=\ndef |\n@app|\nclass )", main_src)
if m: lines.append(m.group(0).rstrip())
else: lines.append("  [!!] introuvable")

# compute_delivery_fee
sub("compute_delivery_fee")
m = re.search(r"def compute_delivery_fee[\s\S]*?(?=\ndef |\n@app|\nclass )", main_src)
if m: lines.append(m.group(0).rstrip())
else: lines.append("  [!!] introuvable")

# ============================================================
# 3. UTILISATION de delivery_fee et delivery_vehicle_type
# ============================================================
hr("[3] Où delivery_fee et delivery_vehicle_type sont utilisés")

for kw in ["delivery_fee", "delivery_vehicle_type", "delivery_mode", "compute_delivery_fee"]:
    sub(kw)
    matches = [m.start() for m in re.finditer(re.escape(kw), main_src)]
    lines.append(f"  {len(matches)} occurrence(s) dans main.py")
    # Afficher les 5 premières lignes avec numéro
    for m in list(re.finditer(re.escape(kw), main_src))[:8]:
        ln = main_src[:m.start()].count("\n") + 1
        line = main_src.split("\n")[ln - 1].strip()[:100]
        lines.append(f"    L{ln}: {line}")

# ============================================================
# 4. Colonnes de la table orders
# ============================================================
hr("[4] Colonnes orders (delivery)")

cols = cur.execute("PRAGMA table_info(orders)").fetchall()
for c in cols:
    if "delivery" in c["name"].lower() or "fee" in c["name"].lower() or "vehicle" in c["name"].lower():
        lines.append(f"  {c['name']:30s} {c['type']:10s}")

# Échantillon
sub("Commandes existantes avec delivery")
rows = cur.execute("""
    SELECT id, reference, delivery_mode, delivery_vehicle_type,
           delivery_fee, delivery_distance_km
    FROM orders
    ORDER BY id DESC LIMIT 5
""").fetchall()
for r in rows:
    lines.append(f"  {r['reference']} mode={r['delivery_mode']} vehicle={r['delivery_vehicle_type']!r} fee={r['delivery_fee']} dist={r['delivery_distance_km']}")

# ============================================================
# 5. FRONTEND - checkout
# ============================================================
hr("[5] Frontend : où le tarif livraison est affiché au client")

CHECKOUT = os.path.join(STATIC, "checkout.js")
if os.path.isfile(CHECKOUT):
    src = open(CHECKOUT, "r", encoding="utf-8").read()
    sub("checkout.js : occurrences de delivery/fee/livraison")
    for kw in ["delivery_fee", "livraison", "delivery_mode", "compute", "fee"]:
        ms = list(re.finditer(re.escape(kw), src))
        if ms:
            lines.append(f"\n  '{kw}': {len(ms)} occurrence(s)")
            for m in ms[:5]:
                ln = src[:m.start()].count("\n") + 1
                line = src.split("\n")[ln - 1].strip()[:100]
                lines.append(f"    L{ln}: {line}")

# Autres fichiers
for fname in ["cart.js", "app.js", "payment.js"]:
    fpath = os.path.join(STATIC, fname)
    if not os.path.isfile(fpath): continue
    src = open(fpath, "r", encoding="utf-8", errors="ignore").read()
    sub(f"{fname} : occurrences livraison")
    for kw in ["delivery_fee", "delivery_vehicle", "compute_delivery", "frais de livraison"]:
        ms = list(re.finditer(re.escape(kw), src))
        if ms:
            lines.append(f"  '{kw}': {len(ms)} occurrence(s)")
            for m in ms[:3]:
                ln = src[:m.start()].count("\n") + 1
                line = src.split("\n")[ln - 1].strip()[:100]
                lines.append(f"    L{ln}: {line}")

# ============================================================
# 6. ROUTE POST /api/orders (create_order)
# ============================================================
hr("[6] Route POST /api/orders (create_order) - extrait")

m = re.search(r"@app\.post\(\"/api/orders\"\)[\s\S]*?(?=\n@app\.|\nclass |\nif __name__)", main_src)
if m:
    block = m.group(0)
    # Afficher uniquement les 60 premières lignes
    for i, line in enumerate(block.split("\n")[:60], 1):
        lines.append(f"  {i:3d}| {line}")
else:
    lines.append("  [!!] introuvable")

# ============================================================
# 7. SYNTHESE
# ============================================================
hr("[7] SYNTHESE")

lines.append("""
Champs disponibles pour les seuils (configurables) :
  - delivery_fee_default     : deja la
  - delivery_base_fee        : deja la
  - delivery_price_per_km    : deja la
  - delivery_max_km          : deja la
  - motorbike_base_fee       : deja la
  - motorbike_price_per_km   : deja la
  - motorbike_minimum_fee    : deja la
  - car_base_fee             : deja la
  - car_price_per_km         : deja la
  - car_minimum_fee          : deja la

Champs à AJOUTER dans pharmacy_settings :
  - delivery_auto_switch     : 1 = activé, 0 = toujours moto
  - threshold_units          : nombre d'unités pour passer en voiture (défaut 40)
  - threshold_distinct_lines : lignes distinctes (défaut 10)
  - threshold_amount         : montant (défaut 80000)

Colonnes orders à vérifier :
  - delivery_vehicle_type    : deja presente
  - delivery_distance_km     : deja presente
  - delivery_fee             : deja presente

Points à vérifier dans le code :
  - compute_delivery_fee retourne juste (fee, distance) : PAS de type véhicule
  - create_order utilise compute_delivery_fee mais ne sélectionne PAS moto/voiture
  - Frontend checkout.js affiche-t-il le type de véhicule ?

Prochaines étapes (à valider après audit) :
  A.2 Modifier compute_delivery_fee pour :
      - accepter le contexte de commande (nb unités, nb lignes, montant)
      - retourner (fee, distance, vehicle_type)
  A.3 Ajouter les 4 champs de seuils dans pharmacy_settings
  A.4 Mettre à jour create_order :
      - calculer la sélection moto/voiture
      - stocker delivery_vehicle_type
  A.5 Mettre à jour checkout.js pour afficher le véhicule
  A.6 Route PATCH manuelle pour les rôles autorisés
  A.7 Tests E2E (9 cas listés dans ta validation)
""")

conn.close()

report = "\n".join(lines)
open(OUT, "w", encoding="utf-8").write(report)
print("=" * 78)
print(f"[OK] Audit genere : {OUT}")
print(f"     {len(report)} caracteres")
print("=" * 78)
print()
print("Ouvre-le : start notepad sprintA_audit.txt")