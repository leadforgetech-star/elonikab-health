"""
match_and_link_photos_v2.py

Version amelioree du matcher :
  - Ignore les parentheses dans les noms produits (molecule generique)
  - Ignore les petits mots (de, du, d, l, g)
  - Desambigue les doublons (Ibuprofene 2BL vs 10BL) par la presentation
  - Dry-run par defaut, --commit pour appliquer
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
BRAND_PREFIXES = ["ubi"]

IGNORE_TOKENS = {
    # Unites
    "mg", "ml", "ui", "mui", "mcg", "iu", "cl", "kg", "g", "gr", "l",
    # Petits mots
    "de", "du", "des", "la", "le", "les", "et", "a", "d",
}

GENERIC_PRES_TOKENS = {
    "bl", "bte", "boite", "boites", "cp", "cpr", "comprimes",
    "gelules", "gelule", "sirop", "flacon", "amp", "ampoule", "ampoules",
    "solution", "suspension", "buvable", "poudre", "injectable",
    "im", "inj", "sachets", "sachet", "sol", "susp", "buv",
    "cr", "vaginale", "vaginaux", "dermique", "perfusion", "perf",
    "pommade", "creme", "kit",
}


def strip_accents(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def tokenize(s):
    s = strip_accents(s).lower()
    return set(re.findall(r"[a-z]+|[0-9]+", s))


def strip_brand(name):
    n = name.strip()
    for bp in BRAND_PREFIXES:
        if n.lower().startswith(bp + " "):
            return n[len(bp) + 1:]
    return n


def slugify(s):
    s = strip_accents(s).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return re.sub(r"-+", "-", s)


def extract_keys(name, presentation):
    """Retourne (required, optional, pres_keys)."""
    base = strip_brand(name)

    # Extraire les parentheses comme optionnel
    optional = set()
    while "(" in base and ")" in base:
        s = base.index("(")
        e = base.index(")")
        inner = base[s + 1:e]
        optional |= {t for t in tokenize(inner) if t not in IGNORE_TOKENS}
        base = base[:s] + base[e + 1:]

    required = {t for t in tokenize(base) if t not in IGNORE_TOKENS}

    pres_keys = set()
    if presentation:
        for t in tokenize(presentation):
            if t in GENERIC_PRES_TOKENS or t in IGNORE_TOKENS:
                continue
            if t.isdigit() or len(t) >= 4:
                pres_keys.add(t)

    return required, optional, pres_keys


def file_keywords(path):
    toks = tokenize(path.stem)
    for bp in BRAND_PREFIXES:
        toks.discard(bp)
    return {t for t in toks if t not in IGNORE_TOKENS}


def match_file(fk, products):
    """Retourne (produit, ratio, best_prod)."""
    # --- Pass 1 : required keys toutes presentes ---
    candidates = [p for p in products if p["required"] and p["required"].issubset(fk)]

    if len(candidates) == 1:
        return candidates[0], 1.0, candidates[0]

    if len(candidates) > 1:
        # --- Pass 2 : affiner par optional keys ---
        with_optional = [p for p in candidates if p["optional"].issubset(fk)]
        if len(with_optional) == 1:
            return with_optional[0], 1.0, with_optional[0]
        if len(with_optional) > 1:
            candidates = with_optional

        # --- Pass 3 : affiner par pres_keys ---
        pres_full = [p for p in candidates if p["pres_keys"].issubset(fk)]
        if len(pres_full) == 1:
            return pres_full[0], 1.0, pres_full[0]
        if len(pres_full) > 1:
            pres_full.sort(key=lambda p: len(p["pres_keys"]), reverse=True)
            if len(pres_full) >= 2 and len(pres_full[0]["pres_keys"]) > len(pres_full[1]["pres_keys"]):
                return pres_full[0], 1.0, pres_full[0]
            return None, 1.0, pres_full[0]

        # Ambigu, on retourne le plus specifique
        candidates.sort(key=lambda p: (len(p["pres_keys"]), len(p["required"])), reverse=True)
        return candidates[0], 1.0, candidates[0]

    # --- Pass 4 : meilleur match partiel ---
    best_ratio = 0.0
    best_prod = None
    for p in products:
        if not p["required"]:
            continue
        hits = sum(1 for k in p["required"] if k in fk)
        ratio = hits / len(p["required"])
        if ratio > best_ratio:
            best_ratio = ratio
            best_prod = p
    return None, best_ratio, best_prod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    print("=" * 64)
    print("MATCHING PHOTOS MEDORA v2")
    print("=" * 64)
    print("Mode :", "COMMIT" if args.commit else "DRY-RUN")
    print()

    if not SRC_DIR.exists() or not DB_PATH.exists():
        print("[ERREUR] Dossier ou base introuvable.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, name, presentation FROM products WHERE is_demo = 0 ORDER BY id"
    ).fetchall()
    if not rows:
        print("[ERREUR] Aucun produit Medora en base.")
        conn.close()
        return

    products = []
    for r in rows:
        req, opt, pres = extract_keys(r["name"], r["presentation"] or "")
        products.append({
            "id": r["id"],
            "name": r["name"],
            "presentation": r["presentation"] or "",
            "required": req,
            "optional": opt,
            "pres_keys": pres,
        })
    print(str(len(products)) + " produits Medora en base.")

    files = [f for f in sorted(SRC_DIR.iterdir())
             if f.is_file() and f.suffix.lower() in VALID_EXTS]
    print(str(len(files)) + " fichiers dans photos_medora/.")
    print()

    matches = []
    ambiguous = []
    partial = []
    unknown = []

    for f in files:
        fk = file_keywords(f)
        prod, ratio, best = match_file(fk, products)
        if prod is not None:
            matches.append((f, prod))
            print("  [OK]      " + f.name)
            print("            -> " + prod["name"] +
                  ("  [" + prod["presentation"] + "]" if prod["presentation"] else ""))
        elif ratio >= 0.7 and best is not None:
            partial.append((f, best, ratio))
            manquants = sorted(k for k in best["required"] if k not in fk)
            print("  [PARTIEL] " + f.name + "  (" + format(ratio, ".2f") + ")")
            print("            -> " + best["name"] + "  |  manquants : " + str(manquants))
        else:
            unknown.append((f,))
            print("  [INCONNU] " + f.name)

    print()
    print("=" * 64)
    print("  Matches clairs  : " + str(len(matches)))
    print("  Partiels        : " + str(len(partial)))
    print("  Inconnus        : " + str(len(unknown)))
    print("=" * 64)
    print()

    if not matches:
        print("Aucun match a appliquer.")
        conn.close()
        return

    # --- Slugs (sans marque, avec desambiguisation pour doublons) ---
    slug_counts = defaultdict(list)
    for f, prod in matches:
        base_slug = slugify(strip_brand(prod["name"]))
        slug_counts[base_slug].append(prod)

    slug_map = {}
    for f, prod in matches:
        base_slug = slugify(strip_brand(prod["name"]))
        if len(slug_counts[base_slug]) > 1:
            pres_slug = slugify(prod["presentation"])
            slug = base_slug + ("-" + pres_slug if pres_slug else "")
        else:
            slug = base_slug
        slug_map[prod["id"]] = slug

    print("Apercu :")
    for f, prod in matches:
        print("  " + f.name.ljust(35) + " -> " + slug_map[prod["id"]] + f.suffix.lower())
    print()

    if not args.commit:
        print("=" * 64)
        print("DRY-RUN : aucune modification.")
        print("Pour appliquer : python match_and_link_photos_v2.py --commit")
        print("=" * 64)
        conn.close()
        return

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
                raise RuntimeError("Update impossible product_id=" + str(prod["id"]))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("[ERREUR]", e)
        print("ROLLBACK - aucune modification conservee.")
        conn.close()
        return

    conn.close()
    print("=" * 64)
    print("  Photos installees   : " + str(installed))
    print("  Produits mis a jour : " + str(updated))
    print("=" * 64)
    print()
    print("Ctrl+Shift+R dans le navigateur.")


if __name__ == "__main__":
    main()