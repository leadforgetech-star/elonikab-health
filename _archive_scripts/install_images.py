from pathlib import Path
import re

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
MAIN = BASE / "main.py"

# ==============================================================
# 1) Dossier images
# ==============================================================
IMG_DIR = STATIC / "images" / "products"
IMG_DIR.mkdir(parents=True, exist_ok=True)
print("[OK] dossier cree :", IMG_DIR.relative_to(BASE))

readme = """IMAGES PRODUITS - PHARMACIE PILOTE
==================================

Deposez ici exactement 8 fichiers avec CES NOMS :

  1. doliprane_1000mg.jpg
  2. amoxicilline_500mg.jpg
  3. vitamine_c_1000mg.jpg
  4. serum_physiologique.jpg
  5. ibuprofene_400mg.jpg
  6. pansements_40.jpg
  7. thermometre_digital.jpg
  8. gel_hydroalcoolique_250ml.jpg

Format recommande : JPG, 800x800 px environ, fond blanc,
produit centre, entierement visible.

Si un fichier est absent, l'application affiche
automatiquement les initiales du produit (fallback).

ATTENTION : verifiez que chaque photo correspond bien au
nom du produit (marque, dosage, presentation).
"""
(IMG_DIR / "README.txt").write_text(readme, encoding="utf-8")
print("[OK] README.txt ecrit")

# ==============================================================
# 2) Patch main.py -> migration image_url
# ==============================================================
src = MAIN.read_text(encoding="utf-8")

MIGRATION_MARKER = "# --- IMAGES PRODUITS (patch) ---"
MIGRATION_BLOCK = '''    # --- IMAGES PRODUITS (patch) ---
    image_map = {
        "Doliprane 1000 mg": "doliprane_1000mg.jpg",
        "Amoxicilline 500 mg": "amoxicilline_500mg.jpg",
        "Vitamine C 1000 mg": "vitamine_c_1000mg.jpg",
        "Serum physiologique": "serum_physiologique.jpg",
        "Ibuprofene 400 mg": "ibuprofene_400mg.jpg",
        "Pansements assortis": "pansements_40.jpg",
        "Thermometre digital": "thermometre_digital.jpg",
        "Gel hydroalcoolique": "gel_hydroalcoolique_250ml.jpg",
    }
    for _name, _fname in image_map.items():
        cur.execute(
            "UPDATE products SET image_url = ?"
            " WHERE name = ? AND (image_url IS NULL OR image_url = '')",
            ("/static/images/products/" + _fname, _name),
        )
    # --- fin patch ---

'''

if MIGRATION_MARKER not in src:
    # Insertion juste avant "conn.commit()" dans init_db()
    # On cible le premier "    conn.commit()" qui suit "def init_db():"
    i = src.index("def init_db():")
    j = src.index("    conn.commit()", i)
    src = src[:j] + MIGRATION_BLOCK + src[j:]
    MAIN.write_text(src, encoding="utf-8")
    print("[OK] main.py -> migration image_url ajoutee")
else:
    print("[i] main.py deja patche (migration presente)")

# ==============================================================
# 3) Patch style.css
# ==============================================================
css_path = STATIC / "style.css"
css = css_path.read_text(encoding="utf-8")

# .thumb : fond blanc + object-fit contain
old_thumb = ".thumb{height:160px;background:linear-gradient(135deg,#eaf7f2,#d6efe6);display:flex;align-items:center;justify-content:center;overflow:hidden}"
new_thumb = ".thumb{height:180px;background:#ffffff;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:center;overflow:hidden;padding:12px}"
if old_thumb in css:
    css = css.replace(old_thumb, new_thumb)
    print("[OK] style.css -> .thumb (fond blanc, 180px, padding)")

old_thumb_img = ".thumb img{width:100%;height:100%;object-fit:cover}"
new_thumb_img = ".thumb img{width:100%;height:100%;object-fit:contain}"
if old_thumb_img in css:
    css = css.replace(old_thumb_img, new_thumb_img)
    print("[OK] style.css -> .thumb img object-fit: contain")

# .detail-media et .detail-thumb : fond blanc + contain
old_detail_media = ".detail-media{border-radius:14px;overflow:hidden;background:linear-gradient(135deg,#eaf7f2,#d6efe6);min-height:300px;display:flex;align-items:center;justify-content:center}"
new_detail_media = ".detail-media{border-radius:14px;overflow:hidden;background:#ffffff;border:1px solid var(--line);min-height:320px;display:flex;align-items:center;justify-content:center;padding:18px}"
if old_detail_media in css:
    css = css.replace(old_detail_media, new_detail_media)
    print("[OK] style.css -> .detail-media (fond blanc)")

old_detail_img = ".detail-thumb img{width:100%;height:100%;object-fit:cover}"
new_detail_img = ".detail-thumb img{width:100%;height:100%;object-fit:contain}"
if old_detail_img in css:
    css = css.replace(old_detail_img, new_detail_img)
    print("[OK] style.css -> .detail-thumb img object-fit: contain")

# .sugg-thumb img : contain (au lieu de cover)
old_sugg_img = ".suggestions .sugg-thumb img{width:100%;height:100%;object-fit:cover}"
new_sugg_img = ".suggestions .sugg-thumb img{width:100%;height:100%;object-fit:contain;background:#fff;padding:3px}"
if old_sugg_img in css:
    css = css.replace(old_sugg_img, new_sugg_img)
    print("[OK] style.css -> .sugg-thumb img object-fit: contain")

css_path.write_text(css, encoding="utf-8")

# ==============================================================
# 4) Patch app.js -> fallback onerror
# ==============================================================
js_path = STATIC / "app.js"
js = js_path.read_text(encoding="utf-8")

# --- productThumb : onerror ---
old_pthumb = '''function productThumb(p, className) {
  var wrap = el("div", className);
  if (p.image_url) {
    var img = document.createElement("img");
    img.src = p.image_url;
    img.alt = p.name;
    wrap.appendChild(img);
  } else {
    wrap.appendChild(el("div", "thumb-placeholder", initials(p.name)));
  }
  return wrap;
}'''
new_pthumb = '''function productThumb(p, className) {
  var wrap = el("div", className);
  if (p.image_url) {
    var img = document.createElement("img");
    img.src = p.image_url;
    img.alt = p.name;
    img.loading = "lazy";
    img.onerror = function () {
      img.remove();
      wrap.appendChild(el("div", "thumb-placeholder", initials(p.name)));
    };
    wrap.appendChild(img);
  } else {
    wrap.appendChild(el("div", "thumb-placeholder", initials(p.name)));
  }
  return wrap;
}'''
if old_pthumb in js:
    js = js.replace(old_pthumb, new_pthumb)
    print("[OK] app.js -> productThumb onerror + lazy")
elif "productThumb" in js and "img.onerror" not in js:
    print("[!] productThumb present mais pattern exact introuvable")
else:
    print("[i] app.js -> productThumb deja patche")

# --- Suggestions : onerror ---
old_sugg = '''      if (p.image_url) {
        var img = document.createElement("img");
        img.src = p.image_url;
        img.alt = p.name;
        thumb.appendChild(img);
      } else {
        thumb.textContent = initials(p.name);
      }'''
new_sugg = '''      if (p.image_url) {
        var img = document.createElement("img");
        img.src = p.image_url;
        img.alt = p.name;
        img.loading = "lazy";
        img.onerror = function () {
          img.remove();
          thumb.textContent = initials(p.name);
        };
        thumb.appendChild(img);
      } else {
        thumb.textContent = initials(p.name);
      }'''
if old_sugg in js:
    js = js.replace(old_sugg, new_sugg)
    print("[OK] app.js -> suggestions onerror + lazy")
elif "sugg-thumb" in js and "img.onerror" not in js:
    print("[!] suggestions pattern introuvable")
else:
    print("[i] app.js -> suggestions deja patche")

js_path.write_text(js, encoding="utf-8")

print()
print("=======================================================")
print("Installation terminee.")
print()
print("Prochaine etape :")
print("  1. Telecharge 8 images et depose-les dans :")
print("     static\\images\\products\\")
print("  2. Verifie les noms (voir README.txt dans ce dossier)")
print("  3. Redemarre le serveur : taskkill /F /IM python.exe  puis  python main.py")
print("  4. Navigateur : Ctrl+Shift+R")
print("=======================================================")