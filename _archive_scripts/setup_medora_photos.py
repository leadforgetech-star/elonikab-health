from pathlib import Path
import json
import sqlite3

BASE = Path(__file__).resolve().parent
PHOTOS_DIR = BASE / "static" / "images" / "products" / "medora"
DATA_DIR = BASE / "data"
DB_PATH = BASE / "database.db"
TRACE_PATH = DATA_DIR / "medora_product_images.json"

PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
print("[OK] dossier :", PHOTOS_DIR.relative_to(BASE))

# --- Mapping nom de fichier propose par produit Medora ---
# L'utilisateur deposera les fichiers avec exactement ces noms.
FILENAMES = {
    "Laino Savon de Marseille": "laino-savon-marseille.jpg",
    "Laino Savon d'Alep": "laino-savon-alep.jpg",
    "Moustidose": "moustidose.jpg",
    "Fedate sirop": "fedate-sirop.jpg",
    "Fedate gélules": "fedate-gelules.jpg",
    "Dazel kit": "dazel-kit.jpg",
    "Hepafyt": "hepafyt.jpg",
    "Ridmal": "ridmal.jpg",
    "CALCHEK 10 mg (Amlodipine)": "calchek-10mg.jpg",
    "Metagard CR (Trimetazidine 35 mg)": "metagard-cr.jpg",
    "UBI Acide fusidique crème 2%": "ubi-acide-fusidique-creme-2.jpg",
    "UBI Amoxicilline 125 MG": "ubi-amoxicilline-125mg.jpg",
    "UBI Amoxicilline 250MG": "ubi-amoxicilline-250mg.jpg",
    "UBI Amoxicilline 500MG": "ubi-amoxicilline-500mg.jpg",
    "UBI Ampicilline IM INJ 1G": "ubi-ampicilline-1g.jpg",
    "UBI Ampicilline 500MG": "ubi-ampicilline-500mg.jpg",
    "UBI Benzatine benzylpenicilline 2,4 MUI": "ubi-benzatine-2-4mui.jpg",
    "UBI Ciprofloxacine 100MG/50ML": "ubi-ciprofloxacine-100mg.jpg",
    "UBI Ciprofloxacine 750MG": "ubi-ciprofloxacine-750mg.jpg",
    "UBI Cotrimoxazole 480MG/5ML": "ubi-cotrimoxazole-480mg-susp.jpg",
    "UBI Cotrimoxazole 480MG": "ubi-cotrimoxazole-480mg.jpg",
    "UBI Cotrimoxazole Fort 960MG": "ubi-cotrimoxazole-fort-960mg.jpg",
    "UBI Tribioderm pommade dermique": "ubi-tribioderm.jpg",
    "UBI Oxacilline 250MG/5ML": "ubi-oxacilline-250mg.jpg",
    "UBI Oxacilline 500MG": "ubi-oxacilline-500mg.jpg",
    "Azibact cp 50 mg (Azithromycine)": "azibact-50mg.jpg",
    "Stericef 1 g injectable (Ceftrie)": "stericef-1g.jpg",
    "UBI Desloratadine 0,5MG/ML": "ubi-desloratadine.jpg",
    "UBI Nystatine 100.000UI/ml": "ubi-nystatine.jpg",
    "UBI Clotrimazole 200MG": "ubi-clotrimazole-200mg.jpg",
    "UBI Fer (Ferrique Citrate d'ammonium, Vit B9, Vit B12, Cu, Mn)": "ubi-fer-sirop.jpg",
    "UBI Oméprazole 20MG": "ubi-omeprazole-20mg.jpg",
    "UBI Esomeprazole 40MG": "ubi-esomeprazole-40mg.jpg",
    "UBI Artemether 80mg": "ubi-artemether-80mg.jpg",
    "UBI Artemether 40mg": "ubi-artemether-40mg.jpg",
    "UBI Artemether 20mg": "ubi-artemether-20mg.jpg",
    "Larinate 60 mg (Artesunate injectable)": "larinate-60mg.jpg",
    "UBI Lidocaïne 2%": "ubi-lidocaine-2.jpg",
    "UBI Kétoprofène 100MG": "ubi-ketoprofene-100mg.jpg",
    "UBI Diclofénac 50MG": "ubi-diclofenac-50mg.jpg",
    "UBI Diclofénac sodique 75MG": "ubi-diclofenac-75mg.jpg",
    "Zerodol CR (Aceclofenac 200 mg)": "zerodol-cr.jpg",
    "UBI Acide Acétyle salicylique 500MG": "ubi-acide-acetyle-salicylique-500mg.jpg",
    "UBI Paracétamol 120MG/5ML": "ubi-paracetamol-120mg-susp.jpg",
    "UBI Paracétamol 500MG": "ubi-paracetamol-500mg.jpg",
    "UBI Albendazole 400MG": "ubi-albendazole-400mg.jpg",
    "UBI Mébendazole 100MG": "ubi-mebendazole-100mg.jpg",
    "UBI Mébendazole 100MG/5ML": "ubi-mebendazole-100mg-susp.jpg",
    "UBI Métronidazole 125MG/5ML": "ubi-metronidazole-125mg-susp.jpg",
    "UBI Métronidazole 250MG": "ubi-metronidazole-250mg.jpg",
    "UBI Métronidazole 500MG/100ML": "ubi-metronidazole-500mg-perf.jpg",
}

# Ibuprofene : 2 entrees distinctes (2 BL 10 et 10 BL 10) -> 2 fichiers distincts
FILENAMES_BY_PRESENTATION = {
    ("UBI Ibuprofène 400MG", "Comprimés · 2 BL 10"): "ubi-ibuprofene-400mg-2bl10.jpg",
    ("UBI Ibuprofène 400MG", "Comprimés · 10 BL 10"): "ubi-ibuprofene-400mg-10bl10.jpg",
}

# --- Lecture des produits Medora en base ---
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT id, name, presentation FROM products WHERE is_demo = 0 ORDER BY id"
).fetchall()
conn.close()

if not rows:
    print("[!] Aucun produit Medora en base. Lance d'abord : python import_medora.py --commit")
    raise SystemExit(1)

print("[INFO]", len(rows), "produits Medora en base")

trace = []
for r in rows:
    key = (r["name"], r["presentation"])
    if key in FILENAMES_BY_PRESENTATION:
        fname = FILENAMES_BY_PRESENTATION[key]
    elif r["name"] in FILENAMES:
        fname = FILENAMES[r["name"]]
    else:
        fname = None

    trace.append({
        "product_id": r["id"],
        "product_name": r["name"],
        "presentation": r["presentation"],
        "filename": fname,
        "image_url": "",
        "status": "not_found",
        "source_url": "",
        "notes": ""
    })

TRACE_PATH.write_text(json.dumps(trace, indent=2, ensure_ascii=False), encoding="utf-8")
print("[OK]", TRACE_PATH.relative_to(BASE))
print("[OK]", len(trace), "entrees de tracabilite (toutes en not_found)")
print()
print("Prochaine etape : telecharger les photos et les deposer dans :")
print("   " + str(PHOTOS_DIR))
print("avec les noms exacts du fichier de tracabilite.")