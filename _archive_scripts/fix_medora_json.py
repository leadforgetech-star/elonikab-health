from pathlib import Path
import json

BASE = Path(__file__).resolve().parent
JSON_PATH = BASE / "data" / "medora_products.json"
JSON_PATH.parent.mkdir(parents=True, exist_ok=True)

# ============================================================
# 53 produits Medora - version corrigee, fidele a la source
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
    {"name": "CALCHEK 10 mg (Amlodipine)", "presentation": "B/30", "price": 1720, "category": "Produits divers"},
    {"name": "Metagard CR (Trimetazidine 35 mg)", "presentation": "B/30", "price": 2100, "category": "Produits divers"},

    # --- Antibiotiques (17) ---
    {"name": "UBI Acide fusidique crème 2%", "presentation": "B/12/15G", "price": 1250, "category": "Antibiotiques"},
    {"name": "UBI Amoxicilline 125 MG", "presentation": "Poudre pour suspension · F/60ML", "price": 775, "category": "Antibiotiques"},
    {"name": "UBI Amoxicilline 250MG", "presentation": "Poudre pour suspension · F/60ML", "price": 975, "category": "Antibiotiques"},
    {"name": "UBI Amoxicilline 500MG", "presentation": "Gélules · 10 BL 12", "price": 800, "category": "Antibiotiques"},
    {"name": "UBI Ampicilline IM INJ 1G", "presentation": "B/50", "price": 300, "category": "Antibiotiques"},
    {"name": "UBI Ampicilline 500MG", "presentation": "Gélules · 10 BL 12", "price": 700, "category": "Antibiotiques"},
    {"name": "UBI Benzatine benzylpenicilline 2,4 MUI", "presentation": "Ampoule injectable · B/1 + solvant", "price": 925, "category": "Antibiotiques"},
    {"name": "UBI Ciprofloxacine 100MG/50ML", "presentation": "Solution injectable · B/1", "price": 1150, "category": "Antibiotiques"},
    {"name": "UBI Ciprofloxacine 750MG", "presentation": "Comprimés · 10 BL 10", "price": 975, "category": "Antibiotiques"},
    {"name": "UBI Cotrimoxazole 480MG/5ML", "presentation": "Suspension · F/100ML", "price": 1125, "category": "Antibiotiques"},
    {"name": "UBI Cotrimoxazole 480MG", "presentation": "Comprimés · 10 BL 10", "price": 225, "category": "Antibiotiques"},
    {"name": "UBI Cotrimoxazole Fort 960MG", "presentation": "Comprimés · 10 BL 10", "price": 575, "category": "Antibiotiques"},
    {"name": "UBI Tribioderm pommade dermique", "presentation": "B/144 sachets", "price": 100, "category": "Antibiotiques"},
    {"name": "UBI Oxacilline 250MG/5ML", "presentation": "Suspension buvable · 60 ML", "price": 1250, "category": "Antibiotiques"},
    {"name": "UBI Oxacilline 500MG", "presentation": "Gélules · 10 BL 12", "price": 2300, "category": "Antibiotiques"},
    {"name": "Azibact cp 50 mg (Azithromycine)", "presentation": "B/3", "price": 3800, "category": "Antibiotiques"},
    {"name": "Stericef 1 g injectable (Ceftrie)", "presentation": "", "price": 1940, "category": "Antibiotiques"},

    # --- Anti-histaminique (1) ---
    {"name": "UBI Desloratadine 0,5MG/ML", "presentation": "Flacon · 60 ML", "price": 1900, "category": "Anti-histaminique"},

    # --- Anti-mycosiques (2) ---
    {"name": "UBI Nystatine 100.000UI/ml", "presentation": "Suspension buvable · 30 ML", "price": 1150, "category": "Anti-mycosiques"},
    {"name": "UBI Clotrimazole 200MG", "presentation": "Comprimés vaginaux · BTE/3", "price": 1500, "category": "Anti-mycosiques"},

    # --- Anti-anémique (1) ---
    {"name": "UBI Fer (Ferrique Citrate d'ammonium, Vit B9, Vit B12, Cu, Mn)", "presentation": "Sirop · Flacon 200 ML", "price": 1900, "category": "Anti-anémique"},

    # --- Anti-ulcéreux (2) ---
    {"name": "UBI Oméprazole 20MG", "presentation": "Comprimés · 10 BL 7", "price": 825, "category": "Anti-ulcéreux"},
    {"name": "UBI Esomeprazole 40MG", "presentation": "Comprimés · 10 BL 10", "price": 1075, "category": "Anti-ulcéreux"},

    # --- Antipaludiques (4) ---
    {"name": "UBI Artemether 80mg", "presentation": "Ampoule injectable · Bte/10amp", "price": 850, "category": "Antipaludiques"},
    {"name": "UBI Artemether 40mg", "presentation": "Ampoule injectable · Bte/10amp", "price": 700, "category": "Antipaludiques"},
    {"name": "UBI Artemether 20mg", "presentation": "Ampoule injectable · Bte/10amp", "price": 475, "category": "Antipaludiques"},
    {"name": "Larinate 60 mg (Artesunate injectable)", "presentation": "", "price": 1430, "category": "Antipaludiques"},

    # --- Anesthésique local (1) ---
    {"name": "UBI Lidocaïne 2%", "presentation": "Solution injectable · 20 ML", "price": 1175, "category": "Anesthésique local"},

    # --- Anti-inflammatoires (6) ---
    {"name": "UBI Ibuprofène 400MG", "presentation": "Comprimés · 2 BL 10", "price": 1650, "category": "Anti-inflammatoires"},
    {"name": "UBI Ibuprofène 400MG", "presentation": "Comprimés · 10 BL 10", "price": 200, "category": "Anti-inflammatoires"},
    {"name": "UBI Kétoprofène 100MG", "presentation": "Comprimés · 10 BL 10", "price": 525, "category": "Anti-inflammatoires"},
    {"name": "UBI Diclofénac 50MG", "presentation": "Comprimés · 10 BL 10", "price": 325, "category": "Anti-inflammatoires"},
    {"name": "UBI Diclofénac sodique 75MG", "presentation": "Ampoule IM · 10 BL/10", "price": 100, "category": "Anti-inflammatoires"},
    {"name": "Zerodol CR (Aceclofenac 200 mg)", "presentation": "Comprimés · B/10", "price": 3500, "category": "Anti-inflammatoires"},

    # --- Antalgiques / Antipyrétiques (3) ---
    {"name": "UBI Acide Acétyle salicylique 500MG", "presentation": "Comprimés · 100 BL 10", "price": 100, "category": "Antalgiques / Antipyrétiques"},
    {"name": "UBI Paracétamol 120MG/5ML", "presentation": "Suspension · F/60ML", "price": 700, "category": "Antalgiques / Antipyrétiques"},
    {"name": "UBI Paracétamol 500MG", "presentation": "Comprimés · 100 BL 10", "price": 125, "category": "Antalgiques / Antipyrétiques"},

    # --- Anti-parasitaires (6) ---
    {"name": "UBI Albendazole 400MG", "presentation": "Comprimés · 50 BL 1", "price": 100, "category": "Anti-parasitaires"},
    {"name": "UBI Mébendazole 100MG", "presentation": "Comprimés · 10 BL 6", "price": 200, "category": "Anti-parasitaires"},
    {"name": "UBI Mébendazole 100MG/5ML", "presentation": "Suspension buvable · 30 ML", "price": 750, "category": "Anti-parasitaires"},
    {"name": "UBI Métronidazole 125MG/5ML", "presentation": "Suspension buvable · 100 ML", "price": 650, "category": "Anti-parasitaires"},
    {"name": "UBI Métronidazole 250MG", "presentation": "Comprimés · 100 BL 10", "price": 150, "category": "Anti-parasitaires"},
    {"name": "UBI Métronidazole 500MG/100ML", "presentation": "Solution pour perfusion · B/1", "price": 925, "category": "Anti-parasitaires"},
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

# --- Validation ---
errors = []
seen = set()
for i, p in enumerate(PRODUCTS):
    key = (p["name"], p["presentation"])
    if key in seen:
        errors.append("Doublon exact #" + str(i) + " : " + p["name"] + " / " + p["presentation"])
    seen.add(key)
    if p["category"] not in ALLOWED_CATEGORIES:
        errors.append("Categorie invalide #" + str(i) + " : " + p["category"])
    if not isinstance(p["price"], (int, float)) or p["price"] <= 0:
        errors.append("Prix invalide #" + str(i))

if errors:
    print("[ERREUR] Validation echouee :")
    for e in errors:
        print("   -", e)
    raise SystemExit(1)

# --- Compteurs par categorie ---
from collections import Counter
counts = Counter(p["category"] for p in PRODUCTS)

# --- Ecriture ---
JSON_PATH.write_text(
    json.dumps(PRODUCTS, indent=2, ensure_ascii=False),
    encoding="utf-8",
)
print("[OK] data/medora_products.json mis a jour")
print("[OK] Total : " + str(len(PRODUCTS)) + " produits")
print()
print("Repartition :")
for cat in sorted(counts.keys()):
    print("   %-35s %d" % (cat, counts[cat]))