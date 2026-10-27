"""
match_and_link_photos.py

Scanne photos_medora/, déduit le produit de chaque fichier par mots-clés,
copie l'image dans static/images/products/medora/ SANS la marque (UBI),
et met à jour image_url en base (uniquement les produits is_demo=0).

Usage :
    python match_and_link_photos.py            # dry-run
    python match_and_link_photos.py --commit   # applique
"""
import argparse
import re
import shutil
import sqlite3
import unicodedata
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
SRC_DIR = BASE / "photos_medora"
DST_DIR = BASE / "static" / "images" / "products" / "medora"
DB_PATH = BASE / "database.db"

VALID_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# Marques à retirer (casse ignorée, espace obligatoire après pour ne pas
# toucher un mot qui commencerait par "ubi" par hasard).
BRAND_PREFIXES = ["ubi"]

# Unités à ignorer dans les mots-clés (non discriminantes)
UNIT_TOKENS = {"mg", "ml", "ui", "mui", "mcg", "iu", "cl", "l", "kg"}

# Mots génériques à ignorer dans les présentations
GENERIC_PRES_TOKENS = {
    "de", "du", "des", "la", "le", "les", "et", "pour", "avec",
    "bl", "bte", "boite", "boites", "cp", "cpr", "comprimes",
    "gelules", "gelule", "sirop", "flacon", "amp", "ampoule", "ampoules",
    "solution", "suspension", "buvable", "poudre", "injectable",
    "im", "in", "inj", "sachets", "sachet", "sol", "susp", "buv",
    "cp", "cpr", "cr", "vaginale", "vaginaux", "dermique",
    "perfusion", "perf", "pommade", "creme", "kit", "cr",
}


# ----------------------------------------------------------------------------
# Normalisation
# ----------------------------------------------------------------------------
def strip_accents(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def tokenize(s):
    """Retourne un set de tokens alphanumériques, casse/accents ignorés.
    'Cotrimoxazole 480MG/5ML' -> {'cotrimoxazole', '480', 'mg', '5', 'ml'}
    """
    s = strip_accents(s).lower()
    return set(re.findall(r"[a-z]+|[0-9]+", s))


def strip_brand(name):
    """Retire les préfixes de marque du nom, pour le slug et les mots-clés."""
    n = name.strip()
    for bp in BRAND_PREFIXES:
        if n.lower().startswith(bp + " "):
            return n[len(bp) + 1:]
    return n


def slugify(s):
    """Convertit en slug URL-safe : 'Amoxicilline 500MG' -> 'amoxicilline-500mg'."""
    s = strip_accents(s).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    s = re.sub(r"-+", "-", s)
    return s


# ----------------------------------------------------------------------------
# Extraction des mots-clés
# ----------------------------------------------------------------------------
def product_keywords(name, presentation):
    """Construit l'ensemble des mots-clés discriminants d'un produit."""
    base = strip_brand(name)
    toks = tokenize(base)
    # Retirer les unités pures
    toks = {t for t in toks if t not in UNIT_TOKENS}

    # Ajouter les chiffres de la présentation (conditionnement)
    if presentation:
        pres_toks = tokenize(presentation)
        for t in pres_toks:
            if t in GENERIC_PRES_TOKENS or t in UNIT_TOKENS:
                continue
            # Ne garder que ce qui est discriminant : chiffres et mots longs
            if t.isdigit() or len(t) >= 4:
                toks.add(t)

    return toks


def file_keywords(path):
    """Mots-clés extraits du nom de fichier (sans extension)."""
    toks = tokenize(path.stem)
    for bp in BRAND_PREFIXES:
        toks.discard(bp)
    return toks


# ----------------------------------------------------------------------------
# Matching
# ----------------------------------------------------------------------------
def match_file(fk, products):
    """Retourne (produit, ratio, nb_keys) ou (None, best_ratio, 0).
    Sélectionne les produits dont TOUS les mots-clés sont présents.
    Si plusieurs, prend celui avec le plus de mots-clés (le plus spécifique).
    """
    candidates = []
    best_ratio = 0.0
    best_prod = None

    for prod in products:
        keys = prod["keys"]
        if not keys:
            continue
        hits = sum(1 for k in keys if k in fk)
        ratio = hits / len(keys)
        if ratio == 1.0:
            candidates.append(prod)
        if ratio > best_ratio:
            best_ratio = ratio
            best_prod = prod

    if not candidates:
        return None, best_ratio, best_prod
    if len(candidates) == 1:
        return candidates[0], 1.0, candidates[0]

    # Plusieurs candidats à 100% : prendre celui avec le plus de clés
    candidates.sort(key=lambda p: len(p["keys"]), reverse=True)
    top = candidates[0]
    if len(candidates) > 1 and len(candidates[0]["keys"]) == len(candidates[1]["keys"]):
        return None, 1.0, top  # ambigu
    return top, 1.0, top


# ----------------------------------------------------------------------------
# Programme principal
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Matching photos Medora par mots-clés.")
    ap.add_argument("--commit", action="store_true", help="Applique les changements.")
    args = ap.parse_args()

    print("=" * 64)
    print("MATCHING PHOTOS MEDORA PAR MOTS-CLES (sans marque UBI)")
    print("=" * 64)
    print("Mode :", "COMMIT" if args.commit else "DRY-RUN")
    print("Source :", SRC_DIR)
    print("Cible  :", DST_DIR)
    print()

    if not SRC_DIR.exists():
        print("[ERREUR] Dossier source introuvable :", SRC_DIR)
        return

    if not DB_PATH.exists():
        print("[ERREUR] Base introuvable :", DB_PATH)
        return

    # Chargement des produits Medora
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, name, presentation FROM products WHERE is_demo = 0 ORDER BY id"
    ).fetchall()
    if not rows:
        print("[ERREUR] Aucun produit Medora (is_demo=0) en base.")
        conn.close()
        return

    products = []
    for r in rows:
        products.append({
            "id": r["id"],
            "name": r["name"],
            "presentation": r["presentation"] or "",
            "keys": product_keywords(r["name"], r["presentation"] or ""),
        })
    print(str(len(products)) + " produits Medora en base.")
    print()

    # Scan des fichiers
    files = [f for f in sorted(SRC_DIR.iterdir())
             if f.is_file() and f.suffix.lower() in VALID_EXTS]
    print(str(len(files)) + " fichiers image dans photos_medora/.")
    print()

    if not files:
        print("Aucun fichier a traiter.")
        conn.close()
        return

    # Matching
    matches = []            # (file, product)
    ambiguous = []          # (file, best_candidate, nb_candidates)
    partial = []            # (file, best_product, ratio)
    unknown = []            # (file,)

    print("Matching :")
    for f in files:
        fk = file_keywords(f)
        prod, ratio, best = match_file(fk, products)

        if prod is not None:
            matches.append((f, prod))
            print("  [OK]      " + f.name)
            print("            -> " + prod["name"] +
                  ("  [" + prod["presentation"] + "]" if prod["presentation"] else ""))
        elif ratio == 1.0 and best is not None:
            ambiguous.append((f, best))
            print("  [AMBIGU]  " + f.name)
            print("            -> plusieurs candidats a 100%, dont : " + best["name"])
        elif ratio >= 0.5:
            partial.append((f, best, ratio))
            manquants = sorted(k for k in best["keys"] if k not in fk)
            print("  [PARTIEL] " + f.name + "  (" + format(ratio, ".2f") + ")")
            print("            -> " + best["name"] + "  |  mots manquants : " + str(manquants))
        else:
            unknown.append((f,))
            print("  [INCONNU] " + f.name)

    print()
    print("=" * 64)
    print("  Matches clairs  : " + str(len(matches)))
    print("  Ambigus         : " + str(len(ambiguous)))
    print("  Partiels        : " + str(len(partial)))
    print("  Inconnus        : " + str(len(unknown)))
    print("=" * 64)
    print()

    if not matches:
        print("Aucun match a appliquer. Verifie le nommage des fichiers.")
        conn.close()
        return

    # ---- Calcul des noms cibles (slug sans marque) --------------------------
    slug_map = {}           # product_id -> slug cible
    slug_counts = defaultdict(list)
    for f, prod in matches:
        base_slug = slugify(strip_brand(prod["name"]))
        slug_counts[base_slug].append(prod)

    for f, prod in matches:
        base_slug = slugify(strip_brand(prod["name"]))
        if len(slug_counts[base_slug]) > 1:
            pres_slug = slugify(prod["presentation"])
            slug = base_slug + "-" + pres_slug if pres_slug else base_slug
        else:
            slug = base_slug
        slug_map[prod["id"]] = slug

    # ---- Aperçu -------------------------------------------------------------
    print("Apercu des fichiers qui seront copies :")
    for f, prod in matches:
        slug = slug_map[prod["id"]]
        ext = f.suffix.lower()
        print("  " + f.name.ljust(30) + " -> " + slug + ext)
    print()

    if not args.commit:
        print("=" * 64)
        print("DRY-RUN : aucune modification effectuee.")
        print("Pour appliquer : python match_and_link_photos.py --commit")
        print("=" * 64)
        conn.close()
        return

    # ---- Commit -------------------------------------------------------------
    DST_DIR.mkdir(parents=True, exist_ok=True)
    installed = 0
    updated = 0

    try:
        conn.execute("BEGIN")
        for f, prod in matches:
            slug = slug_map[prod["id"]]
            ext = f.suffix.lower()
            target_name = slug + ext
            target_path = DST_DIR / target_name
            shutil.copy2(f, target_path)
            installed += 1

            url = "/static/images/products/medora/" + target_name
            cur = conn.execute(
                "UPDATE products SET image_url = ? WHERE id = ? AND is_demo = 0",
                (url, prod["id"]),
            )
            if cur.rowcount == 1:
                updated += 1
            else:
                raise RuntimeError(
                    "Mise a jour impossible pour product_id=" + str(prod["id"])
                )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("[ERREUR]", e)
        print("ROLLBACK effectue - aucune modification conservee.")
        conn.close()
        return

    conn.close()

    print("=" * 64)
    print("  Photos installees   : " + str(installed))
    print("  Produits mis a jour : " + str(updated))
    print("=" * 64)
    print()
    print("Rechargez le navigateur avec Ctrl+Shift+R.")


if __name__ == "__main__":
    main()