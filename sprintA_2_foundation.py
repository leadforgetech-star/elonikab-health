# -*- coding: utf-8 -*-
"""
SPRINT A.2 - Fondation
========================
1. Migration : 4 champs de seuils dans pharmacy_settings
2. Nouvelle fonction compute_delivery_fee_v2 (retourne fee, dist, vehicle)
3. Nouvel endpoint /api/delivery/estimate (public)

AUCUNE modification de create_order. Les commandes actuelles continuent
avec l'ancien calcul. Retour arrière immédiat si erreur.
"""
import os, re, sqlite3, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
MAIN = os.path.join(ROOT, "main.py")
DB = os.path.join(ROOT, "database.db")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_sprintA2_{TS}")
os.makedirs(BAK, exist_ok=True)

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]", "STEP": "\n###"}[k]
    print(p, m)

def syntax_ok(path):
    try:
        with open(path, "rb") as f:
            compile(f.read(), path, "exec")
        return True, None
    except SyntaxError as e:
        return False, f"L{e.lineno}: {e.msg}"

shutil.copy2(MAIN, os.path.join(BAK, "main.py"))
shutil.copy2(DB, os.path.join(BAK, "database.db"))

print("=" * 78)
print(f"SPRINT A.2 - FONDATION - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

# ============================================================
# PHASE 1 : Migration DB
# ============================================================
log("PHASE 1 : Migration pharmacy_settings", "STEP")

conn = sqlite3.connect(DB)
cur = conn.cursor()
cols = {c[1] for c in cur.execute("PRAGMA table_info(pharmacy_settings)").fetchall()}

migrations = [
    ("delivery_auto_switch",     "INTEGER DEFAULT 1"),
    ("threshold_units",          "INTEGER DEFAULT 40"),
    ("threshold_distinct_lines", "INTEGER DEFAULT 10"),
    ("threshold_amount",         "REAL DEFAULT 80000"),
]
for name, definition in migrations:
    if name in cols:
        log(f"{name} existe deja", "WARN")
    else:
        cur.execute(f"ALTER TABLE pharmacy_settings ADD COLUMN {name} {definition}")
        log(f"{name} ajoute ({definition})", "OK")

conn.commit()
row = cur.execute("SELECT * FROM pharmacy_settings WHERE id = 1").fetchone()
if row:
    idx = [c[0] for c in cur.description]
    d = dict(zip(idx, row))
    print(f"\n  Valeurs seuils actuelles :")
    print(f"    delivery_auto_switch     = {d.get('delivery_auto_switch')}")
    print(f"    threshold_units          = {d.get('threshold_units')}")
    print(f"    threshold_distinct_lines = {d.get('threshold_distinct_lines')}")
    print(f"    threshold_amount         = {d.get('threshold_amount')}")
conn.close()

# ============================================================
# PHASE 2 : Nouvelle fonction compute_delivery_fee_v2
# ============================================================
log("PHASE 2 : compute_delivery_fee_v2", "STEP")

src = open(MAIN, "r", encoding="utf-8").read()

if "def compute_delivery_fee_v2" in src:
    log("Deja present", "WARN")
else:
    NEW_FN = '''

def compute_delivery_fee_v2(client_lat, client_lon, units=1, distinct_lines=1, amount=0.0):
    """Version avancée : selectionne moto ou voiture selon les seuils.
    Retourne (fee, distance_km, vehicle_type, reason).
    - fee = None + vehicle = None si aucun moyen disponible (out_of_range)
    - fee = delivery_fee_default + vehicle = MOTO si GPS manquant
    """
    conn = get_db()
    s = conn.execute("SELECT * FROM pharmacy_settings WHERE id = 1").fetchone()
    conn.close()
    if s is None:
        return 0.0, None, "MOTO", "no_settings"

    def col(name, default=None):
        try:
            v = s[name]
        except Exception:
            return default
        return default if v is None else v

    ph_lat = col("pharmacy_latitude")
    ph_lon = col("pharmacy_longitude")

    # Pas de GPS client ou pharmacie : fallback, moto par defaut
    if client_lat is None or client_lon is None or ph_lat is None or ph_lon is None:
        return float(col("delivery_fee_default", 0.0) or 0.0), None, "MOTO", "no_gps"

    # Calcul distance
    dist = haversine_km(float(ph_lat), float(ph_lon), float(client_lat), float(client_lon))

    # Selection vehicule
    auto = int(col("delivery_auto_switch", 1) or 0)
    th_units = int(col("threshold_units", 40) or 40)
    th_lines = int(col("threshold_distinct_lines", 10) or 10)
    th_amt = float(col("threshold_amount", 80000) or 80000)

    vehicle = "MOTO"
    reason = "default_moto"

    if auto:
        triggers = []
        if units >= th_units:
            triggers.append("units>=" + str(th_units))
        if distinct_lines >= th_lines:
            triggers.append("lines>=" + str(th_lines))
        if amount >= th_amt:
            triggers.append("amount>=" + str(int(th_amt)))
        if triggers:
            vehicle = "CAR"
            reason = "+".join(triggers)

    # Calcul fee selon vehicule
    def fee_for(v):
        if v == "MOTO":
            base = float(col("motorbike_base_fee", 1200) or 0)
            per_km = float(col("motorbike_price_per_km", 100) or 0)
            min_fee = float(col("motorbike_minimum_fee", 500) or 0)
            max_dist = float(col("motorbike_max_distance", 0) or 0)
        else:
            base = float(col("car_base_fee", 1000) or 0)
            per_km = float(col("car_price_per_km", 250) or 0)
            min_fee = float(col("car_minimum_fee", 1000) or 0)
            max_dist = float(col("car_max_distance", 0) or 0)
        fee = base + dist * per_km
        if fee < min_fee:
            fee = min_fee
        fee = round(fee / 50.0) * 50
        return fee, max_dist

    fee, max_dist = fee_for(vehicle)

    # Verification distance max
    if max_dist > 0 and dist > max_dist:
        other = "CAR" if vehicle == "MOTO" else "MOTO"
        fee2, max_dist2 = fee_for(other)
        if max_dist2 == 0 or dist <= max_dist2:
            return float(fee2), round(dist, 2), other, "fallback_" + vehicle.lower() + "_out_of_range"
        return None, round(dist, 2), None, "no_vehicle_available"

    return float(fee), round(dist, 2), vehicle, reason

'''
    # Inserer juste apres compute_delivery_fee existant
    anchor = "# V2.4 - Calcul des frais de livraison selon la distance"
    if anchor in src:
        # Trouver la fin de compute_delivery_fee (avant la prochaine @app)
        idx = src.find("def compute_delivery_fee(")
        end = src.find("\n@app.", idx)
        if end > 0:
            src = src[:end] + NEW_FN + src[end:]
            log("compute_delivery_fee_v2 insere", "OK")
        else:
            log("Ancre fin introuvable", "ERR")
    else:
        log("Ancre debut introuvable", "ERR")

# ============================================================
# PHASE 3 : Endpoint /api/delivery/estimate
# ============================================================
log("PHASE 3 : Endpoint /api/delivery/estimate", "STEP")

if "/api/delivery/estimate" in src:
    log("Deja present", "WARN")
else:
    ENDPOINT = '''

# ============================================================
# SPRINT A - Estimation livraison (public, avant commande)
# ============================================================
class DeliveryEstimateRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    units: int = 1
    distinct_lines: int = 1
    amount: float = 0.0


@app.post("/api/delivery/estimate")
def estimate_delivery(payload: DeliveryEstimateRequest):
    """Estime les frais de livraison et le vehicule selectionne.
    Endpoint public : accessible avant commande pour afficher au client.
    """
    fee, dist, vehicle, reason = compute_delivery_fee_v2(
        payload.latitude, payload.longitude,
        max(1, payload.units), max(1, payload.distinct_lines), float(payload.amount or 0)
    )
    return {
        "fee": fee,
        "distance_km": dist,
        "vehicle_type": vehicle,
        "reason": reason,
        "available": vehicle is not None,
    }

'''
    # Inserer avant "if __name__ == \"__main__\":"
    anchor = 'if __name__ == "__main__":'
    if anchor in src:
        idx = src.find(anchor)
        src = src[:idx] + ENDPOINT + src[idx:]
        log("Endpoint insere", "OK")
    else:
        log("Ancre __main__ introuvable", "ERR")

open(MAIN, "w", encoding="utf-8").write(src)
ok, err = syntax_ok(MAIN)
if not ok:
    log(f"main.py ERREUR : {err}", "ERR")
    shutil.copy2(os.path.join(BAK, "main.py"), MAIN)
    shutil.copy2(os.path.join(BAK, "database.db"), DB)
    sys.exit(1)
log("main.py syntaxe OK", "OK")

# ============================================================
# Verification
# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)
final = open(MAIN, "r", encoding="utf-8").read()
conn = sqlite3.connect(DB)
cur = conn.cursor()
new_cols = {c[1] for c in cur.execute("PRAGMA table_info(pharmacy_settings)").fetchall()}
conn.close()

checks = [
    ("Colonne delivery_auto_switch",      "delivery_auto_switch" in new_cols),
    ("Colonne threshold_units",           "threshold_units" in new_cols),
    ("Colonne threshold_distinct_lines",  "threshold_distinct_lines" in new_cols),
    ("Colonne threshold_amount",          "threshold_amount" in new_cols),
    ("Fonction compute_delivery_fee_v2",  "def compute_delivery_fee_v2(" in final),
    ("Ancienne compute_delivery_fee",     "def compute_delivery_fee(" in final),
    ("Endpoint /api/delivery/estimate",   "/api/delivery/estimate" in final),
    ("Classe DeliveryEstimateRequest",    "class DeliveryEstimateRequest" in final),
    ("main.py syntaxe OK",                syntax_ok(MAIN)[0]),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

print()
print(f"[BACKUP] {BAK}")
print()
print("[CMD] Restart Uvicorn :")
print("  taskkill /F /IM uvicorn.exe 2>nul")
print("  taskkill /F /IM python.exe 2>nul")
print("  cd /d \"C:\\Users\\ELOGE KEY\\Desktop\\pharma\\pharmacie\"")
print("  python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir v3_modules --reload-dir static")
print()
print("[TEST] Apres restart :")
print("  1) test_sprintA2.py (script de test a creer)")
print()
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\main.py" "{MAIN}"')
print(f'  copy "{BAK}\\database.db" "{DB}"')