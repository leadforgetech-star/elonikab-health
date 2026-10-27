from pathlib import Path
import json

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 53 produits Medora - donnees exactes de la liste fournie
# ============================================================
PRODUCTS = [
    # --- Produits divers (10) ---
    {"name": "Laino Savon de Marseille", "presentation": "", "price": 2500, "category": "Produits divers"},
    {"name": "Laino Savon d'Alep", "presentation": "", "price": 4500, "category": "Produits divers"},
    {"name": "Moustidose", "presentation": "", "price": 6000, "category": "Produits divers"},
    {"name": "Fedate sirop", "presentation": "", "price": 2870, "category": "Produits divers"},
    {"name": "Fedate gélules", "presentation": "", "price": 2125, "category": "Produits divers"},
    {"name": "Dazel kit", "presentation": "", "price": 4590, "category": "Produits divers"},
    {"name": "Hepafyt", "presentation": "", "price": 1720, "category": "Produits divers"},
    {"name": "Ridmal", "presentation": "", "price": 3330, "category": "Produits divers"},
    {"name": "CALCHEK 10 mg (Amlodipine)", "presentation": "Comprimés · B/30", "price": 1720, "category": "Produits divers"},
    {"name": "Metagard CR (Trimetazidine 35 mg)", "presentation": "Comprimés · B/30", "price": 2100, "category": "Produits divers"},

    # --- Antibiotiques (17) ---
    {"name": "UBI Acide fusidique 2%", "presentation": "Crème · B/12/15G", "price": 1250, "category": "Antibiotiques"},
    {"name": "UBI Amoxicilline 125 MG", "presentation": "Poudre pour suspension · F/60ML", "price": 775, "category": "Antibiotiques"},
    {"name": "UBI Amoxicilline 250 MG", "presentation": "Poudre pour suspension · F/60ML", "price": 975, "category": "Antibiotiques"},
    {"name": "UBI Amoxicilline 500 MG", "presentation": "Gélules · 10 BL 12", "price": 800, "category": "Antibiotiques"},
    {"name": "UBI Ampicilline 1G", "presentation": "Injectable IM · B/50", "price": 300, "category": "Antibiotiques"},
    {"name": "UBI Ampicilline 500 MG", "presentation": "Gélules · 10 BL 12", "price": 700, "category": "Antibiotiques"},
    {"name": "UBI Benzatine benzylpenicilline 2,4 MUI", "presentation": "Ampoule injectable · B/1 + solvant", "price": 925, "category": "Antibiotiques"},
    {"name": "UBI Ciprofloxacine 100 MG/50ML", "presentation": "Solution injectable · B/1", "price": 1150, "category": "Antibiotiques"},
    {"name": "UBI Ciprofloxacine 750 MG", "presentation": "Comprimés · 10 BL 10", "price": 975, "category": "Antibiotiques"},
    {"name": "UBI Cotrimoxazole 480 MG/5ML", "presentation": "Suspension · F/100ML", "price": 1125, "category": "Antibiotiques"},
    {"name": "UBI Cotrimoxazole 480 MG", "presentation": "Comprimés · 10 BL 10", "price": 225, "category": "Antibiotiques"},
    {"name": "UBI Cotrimoxazole Fort 960 MG", "presentation": "Comprimés · 10 BL 10", "price": 575, "category": "Antibiotiques"},
    {"name": "UBI Tribioderm", "presentation": "Pommade dermique · B/144 sachets", "price": 100, "category": "Antibiotiques"},
    {"name": "UBI Oxacilline 250 MG/5ML", "presentation": "Suspension buvable · 60 ML", "price": 1250, "category": "Antibiotiques"},
    {"name": "UBI Oxacilline 500 MG", "presentation": "Gélules · 10 BL 12", "price": 2300, "category": "Antibiotiques"},
    {"name": "Azibact 50 mg (Azithromycine)", "presentation": "Comprimés · B/3", "price": 3800, "category": "Antibiotiques"},
    {"name": "Stericef 1 g (Ceftrie)", "presentation": "Injectable", "price": 1940, "category": "Antibiotiques"},

    # --- Anti-histaminique (1) ---
    {"name": "UBI Desloratadine 0,5 MG/ML", "presentation": "Flacon · 60 ML", "price": 1900, "category": "Anti-histaminique"},

    # --- Anti-mycosiques (2) ---
    {"name": "UBI Nystatine 100.000UI/ml", "presentation": "Suspension buvable · 30 ML", "price": 1150, "category": "Anti-mycosiques"},
    {"name": "UBI Clotrimazole 200 MG", "presentation": "Comprimés vaginaux · BTE/3", "price": 1500, "category": "Anti-mycosiques"},

    # --- Anti-anémique (1) ---
    {"name": "UBI Fer (Ferrique Citrate d'ammonium, Vit B9, Vit B12, Cu, Mn)", "presentation": "Sirop · Flacon 200 ML", "price": 1900, "category": "Anti-anémique"},

    # --- Anti-ulcéreux (2) ---
    {"name": "UBI Oméprazole 20 MG", "presentation": "Comprimés · 10 BL 7", "price": 825, "category": "Anti-ulcéreux"},
    {"name": "UBI Esomeprazole 40 MG", "presentation": "Comprimés · 10 BL 10", "price": 1075, "category": "Anti-ulcéreux"},

    # --- Antipaludiques (4) ---
    {"name": "UBI Artemether 80 mg", "presentation": "Ampoule injectable · Bte/10amp", "price": 850, "category": "Antipaludiques"},
    {"name": "UBI Artemether 40 mg", "presentation": "Ampoule injectable · Bte/10amp", "price": 700, "category": "Antipaludiques"},
    {"name": "UBI Artemether 20 mg", "presentation": "Ampoule injectable · Bte/10amp", "price": 475, "category": "Antipaludiques"},
    {"name": "Larinate 60 mg (Artesunate)", "presentation": "Injectable", "price": 1430, "category": "Antipaludiques"},

    # --- Anesthésique local (1) ---
    {"name": "UBI Lidocaïne 2%", "presentation": "Solution injectable · 20 ML", "price": 1175, "category": "Anesthésique local"},

    # --- Anti-inflammatoires (6) ---
    {"name": "UBI Ibuprofène 400 MG", "presentation": "Comprimés · 2 BL 10", "price": 1650, "category": "Anti-inflammatoires"},
    {"name": "UBI Ibuprofène 400 MG", "presentation": "Comprimés · 10 BL 10", "price": 200, "category": "Anti-inflammatoires"},
    {"name": "UBI Kétoprofène 100 MG", "presentation": "Comprimés · 10 BL 10", "price": 525, "category": "Anti-inflammatoires"},
    {"name": "UBI Diclofénac 50 MG", "presentation": "Comprimés · 10 BL 10", "price": 325, "category": "Anti-inflammatoires"},
    {"name": "UBI Diclofénac sodique 75 MG", "presentation": "Ampoule injectable · 10 BL/10", "price": 100, "category": "Anti-inflammatoires"},
    {"name": "Zerodol CR (Aceclofenac 200 mg)", "presentation": "Comprimés · B/10", "price": 3500, "category": "Anti-inflammatoires"},

    # --- Antalgiques / Antipyrétiques (3) ---
    {"name": "UBI Acide Acétyle salicylique 500 MG", "presentation": "Comprimés · 100 BL 10", "price": 100, "category": "Antalgiques / Antipyrétiques"},
    {"name": "UBI Paracétamol 120 MG/5ML", "presentation": "Suspension · F/60ML", "price": 700, "category": "Antalgiques / Antipyrétiques"},
    {"name": "UBI Paracétamol 500 MG", "presentation": "Comprimés · 100 BL 10", "price": 125, "category": "Antalgiques / Antipyrétiques"},

    # --- Anti-parasitaires (6) ---
    {"name": "UBI Albendazole 400 MG", "presentation": "Comprimés · 50 BL 1", "price": 100, "category": "Anti-parasitaires"},
    {"name": "UBI Mébendazole 100 MG", "presentation": "Comprimés · 10 BL 6", "price": 200, "category": "Anti-parasitaires"},
    {"name": "UBI Mébendazole 100 MG/5ML", "presentation": "Suspension buvable · 30 ML", "price": 750, "category": "Anti-parasitaires"},
    {"name": "UBI Métronidazole 125 MG/5ML", "presentation": "Suspension buvable · 100 ML", "price": 650, "category": "Anti-parasitaires"},
    {"name": "UBI Métronidazole 250 MG", "presentation": "Comprimés · 100 BL 10", "price": 150, "category": "Anti-parasitaires"},
    {"name": "UBI Métronidazole 500 MG/100ML", "presentation": "Solution pour perfusion · B/1", "price": 925, "category": "Anti-parasitaires"},
]

ALLOWED_CATEGORIES = {
    "Produits divers", "Antibiotiques", "Anti-histaminique",
    "Anti-mycosiques", "Anti-anémique", "Anti-ulcéreux",
    "Antipaludiques", "Anesthésique local", "Anti-inflammatoires",
    "Antalgiques / Antipyrétiques", "Anti-parasitaires",
}

def enrich(p):
    return {
        "name": p["name"],
        "presentation": p.get("presentation", ""),
        "price": p["price"],
        "category": p["category"],
        "requires_prescription": 0,
        "description": "",
        "image_url": "",
        "availability": "disponible",
        "is_demo": 0,
    }

PRODUCTS = [enrich(p) for p in PRODUCTS]

# --- Validation interne ---
errors = []
seen = set()
for i, p in enumerate(PRODUCTS):
    key = (p["name"], p["presentation"])
    if key in seen:
        errors.append(f"Doublon exact #{i} : {p['name']} / {p['presentation']}")
    seen.add(key)
    if p["category"] not in ALLOWED_CATEGORIES:
        errors.append(f"Categorie invalide #{i} : {p['category']}")
    if not isinstance(p["price"], (int, float)) or p["price"] <= 0:
        errors.append(f"Prix invalide #{i} : {p['price']}")
    if p["requires_prescription"] != 0:
        errors.append(f"requires_prescription != 0 #{i}")
    if p["is_demo"] != 0:
        errors.append(f"is_demo != 0 #{i}")

if errors:
    print("[ERREUR] Validation echouee :")
    for e in errors:
        print("   -", e)
    raise SystemExit(1)

# --- Ecriture du JSON ---
json_path = DATA_DIR / "medora_products.json"
json_path.write_text(
    json.dumps(PRODUCTS, indent=2, ensure_ascii=False),
    encoding="utf-8",
)
print("[OK] " + str(json_path.relative_to(BASE)))
print("[OK] " + str(len(PRODUCTS)) + " produits")

# --- Ecriture du script d'import ---
IMPORT_SCRIPT = '''"""
import_medora.py - Import du catalogue Medora dans la base SQLite.

Usage :
    python import_medora.py             # dry-run (aucune ecriture)
    python import_medora.py --commit    # import reel

Regles :
  - Lit data/medora_products.json
  - N'ecrase jamais un produit existant (name + presentation identiques)
  - Ne touche jamais aux produits is_demo = 1 (DEMO)
  - Ne touche jamais aux commandes
  - Insertion idempotente : les produits deja presents sont ignores
"""
import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "database.db"
JSON_PATH = BASE / "data" / "medora_products.json"

REQUIRED_FIELDS = ["name", "price", "category"]


def load_products():
    if not JSON_PATH.exists():
        raise SystemExit("[ERREUR] Fichier introuvable : " + str(JSON_PATH))
    raw = JSON_PATH.read_text(encoding="utf-8")
    try:
        products = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SystemExit("[ERREUR] JSON invalide : " + str(e))
    if not isinstance(products, list):
        raise SystemExit("[ERREUR] Le JSON doit etre un tableau.")
    for i, p in enumerate(products):
        for f in REQUIRED_FIELDS:
            if f not in p:
                raise SystemExit("[ERREUR] Produit #" + str(i) + " : champ manquant '" + f + "'")
    return products


def find_existing(conn, name, presentation):
    row = conn.execute(
        "SELECT id, is_demo FROM products WHERE name = ? AND presentation = ? LIMIT 1",
        (name, presentation),
    ).fetchone()
    return row


def main():
    ap = argparse.ArgumentParser(description="Import des produits Medora.")
    ap.add_argument("--commit", action="store_true",
                    help="Execute l'import reel (sinon dry-run).")
    args = ap.parse_args()

    if not DB_PATH.exists():
        raise SystemExit("[ERREUR] Base introuvable : " + str(DB_PATH))

    products = load_products()
    print("[INFO] " + str(len(products)) + " produits lus depuis " + JSON_PATH.name)
    print("[INFO] Base : " + str(DB_PATH))
    print("[INFO] Mode : " + ("COMMIT (ecriture reelle)" if args.commit else "DRY-RUN (aucune ecriture)"))
    print()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    total_before = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    demo_before = cur.execute("SELECT COUNT(*) FROM products WHERE is_demo = 1").fetchone()[0]
    real_before = cur.execute("SELECT COUNT(*) FROM products WHERE is_demo = 0").fetchone()[0]
    print("[INFO] Avant import : " + str(total_before) + " produits (" +
          str(demo_before) + " DEMO + " + str(real_before) + " reels)")
    print()

    created_at = datetime.now().isoformat(timespec="seconds")
    inserted = 0
    skipped = 0
    conflicts = 0

    for p in products:
        name = str(p["name"]).strip()
        presentation = str(p.get("presentation", "") or "").strip()
        existing = find_existing(conn, name, presentation)

        if existing:
            if existing["is_demo"] == 1:
                conflicts += 1
                print("  [CONFLIT] '" + name + "' existe deja en DEMO (id=" + str(existing["id"]) + ") - ignore")
            else:
                skipped += 1
                print("  [SKIP]    '" + name + "' deja present (id=" + str(existing["id"]) + ")")
            continue

        if args.commit:
            cur.execute(
                "INSERT INTO products (name, presentation, price, availability,"
                " description, category, requires_prescription, image_url, is_demo, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    name,
                    presentation,
                    float(p["price"]),
                    str(p.get("availability", "disponible")),
                    str(p.get("description", "")),
                    str(p["category"]),
                    int(p.get("requires_prescription", 0)),
                    str(p.get("image_url", "")),
                    int(p.get("is_demo", 0)),
                    created_at,
                ),
            )
            print("  [OK]      '" + name + "' insere (id=" + str(cur.lastrowid) + ")")
        else:
            print("  [DRY]     '" + name + "' serait insere")

        inserted += 1

    if args.commit:
        conn.commit()

    total_after = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    demo_after = cur.execute("SELECT COUNT(*) FROM products WHERE is_demo = 1").fetchone()[0]
    real_after = cur.execute("SELECT COUNT(*) FROM products WHERE is_demo = 0").fetchone()[0]
    conn.close()

    print()
    print("=" * 55)
    print("  Resume :")
    print("    Inseres  : " + str(inserted))
    print("    Ignores  : " + str(skipped))
    print("    Conflits : " + str(conflicts))
    print()
    print("  Avant : " + str(total_before) + " produits (" + str(demo_before) + " DEMO + " + str(real_before) + " reels)")
    print("  Apres : " + str(total_after) + " produits (" + str(demo_after) + " DEMO + " + str(real_after) + " reels)")
    print("=" * 55)

    if not args.commit:
        print()
        print("[INFO] Mode DRY-RUN - aucune donnee n'a ete ecrite.")
        print("       Pour executer l'import reel : python import_medora.py --commit")


if __name__ == "__main__":
    main()
'''

script_path = BASE / "import_medora.py"
script_path.write_text(IMPORT_SCRIPT, encoding="utf-8")
print("[OK] " + str(script_path.relative_to(BASE)))
print()
print("Termine.")
print("Etape suivante : verifiez les fichiers, puis dry-run.")