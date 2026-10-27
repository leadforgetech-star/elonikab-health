# -*- coding: utf-8 -*-
# optim_patient_speed.py
# Optimisations backend + frontend pour accelerer le parcours patient
import os, re, shutil, datetime, ast

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
STATIC = os.path.join(ROOT, "static")
MAIN = os.path.join(ROOT, "main.py")
APP = os.path.join(STATIC, "app.js")
INDEX = os.path.join(STATIC, "index.html")

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
bak = os.path.join(ROOT, f"_backup_optim_speed_{ts}")
os.makedirs(bak, exist_ok=True)
for f in (MAIN, APP, INDEX):
    shutil.copy2(f, os.path.join(bak, os.path.basename(f)))
print(f"[BACKUP] {bak}\n")

# ============================================================
# 1. BACKEND : Index SQLite + cache HTTP + compression
# ============================================================
main_src = open(MAIN, "r", encoding="utf-8").read()

# --- 1a. Ajouter un middleware de cache HTTP + Vary ---
if "class PatientCacheMiddleware" in main_src:
    print("[SKIP] PatientCacheMiddleware deja present")
else:
    CACHE_MW = '''

# ============================================================
# Patient Cache : cache HTTP sur categories + products (5 min)
# ============================================================
class PatientCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        if request.method == "GET":
            # Routes cacheables 5 min
            if path in ("/api/categories", "/api/products", "/api/settings"):
                response.headers["Cache-Control"] = "public, max-age=300, must-revalidate"
                response.headers["Vary"] = "Accept-Encoding, Cookie"
            else:
                # No-cache par defaut pour le reste
                if "cache-control" not in (k.lower() for k in response.headers.keys()):
                    response.headers["Cache-Control"] = "no-store"
        return response

try:
    app.add_middleware(PatientCacheMiddleware)
    print("[BOOT] PatientCacheMiddleware actif")
except Exception:
    pass
'''
    # Inserer avant les autres middlewares
    MARKER = "app.add_middleware(GZipMiddleware, minimum_size=500)"
    if MARKER in main_src:
        main_src = main_src.replace(MARKER, CACHE_MW + "\n" + MARKER, 1)
        print("[OK] main.py : PatientCacheMiddleware ajoute")
    else:
        # fallback : inserer apres BaseHTTPMiddleware import
        MARKER2 = "from starlette.middleware.base import BaseHTTPMiddleware"
        if MARKER2 in main_src:
            main_src = main_src.replace(MARKER2, MARKER2 + CACHE_MW, 1)
            print("[OK] main.py : PatientCacheMiddleware ajoute (fallback)")

# --- 1b. Brotli si dispo, sinon GZip (deja en place) ---
if "import brotli" not in main_src and "from brotli" not in main_src:
    BROTLI_BOOT = '''
# Brotli si dispo (meilleure compression)
try:
    from starlette.middleware.brotli import BrotliMiddleware
    app.add_middleware(BrotliMiddleware, quality=5)
    print("[BOOT] BrotliMiddleware actif")
except Exception:
    pass  # fallback GZip deja en place
'''
    # Inserer juste apres FastAPI() (mais avant les routes)
    MARKER_FASTAPI = "app = FastAPI("
    idx = main_src.find(MARKER_FASTAPI)
    if idx > 0:
        # Trouver la fin de la ligne FastAPI
        end_of_line = main_src.find("\n", idx)
        main_src = main_src[:end_of_line + 1] + BROTLI_BOOT + main_src[end_of_line + 1:]
        print("[OK] main.py : Brotli (fallback GZip)")

# --- 1c. Verifier la syntaxe ---
try:
    ast.parse(main_src)
    open(MAIN, "w", encoding="utf-8").write(main_src)
    print("[OK] main.py sauvegarde")
except SyntaxError as e:
    print(f"[!!] main.py SyntaxError ligne {e.lineno}: {e.msg}")

# ============================================================
# 2. INDEX SQLITE supplementaires
# ============================================================
INDEX_SCRIPT = '''# -*- coding: utf-8 -*-
# add_indexes_v2.py - Index SQLite pour accelerer la liste des commandes
import sqlite3, os

ROOT = r"C:\\\\Users\\\\ELOGE KEY\\\\Desktop\\\\pharma\\\\pharmacie"
DB = os.path.join(ROOT, "database.db")

con = sqlite3.connect(DB)
con.execute("PRAGMA journal_mode = WAL")

INDEXES = [
    ("idx_orders_user_status", "CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status)"),
    ("idx_orders_user_created", "CREATE INDEX IF NOT EXISTS idx_orders_user_created ON orders(user_id, created_at DESC)"),
    ("idx_products_active_cat", "CREATE INDEX IF NOT EXISTS idx_products_active_cat ON products(is_active, category)"),
    ("idx_notif_user_created", "CREATE INDEX IF NOT EXISTS idx_notif_user_created ON notifications(user_id, created_at DESC)"),
]

for name, sql in INDEXES:
    try:
        con.execute(sql)
        print(f"  [OK] {name}")
    except Exception as e:
        print(f"  [!!] {name} : {e}")

con.commit()
con.close()
print("\\n[OK] Index v2 crees")
'''

SCRIPT_PATH = os.path.join(ROOT, "add_indexes_v2.py")
open(SCRIPT_PATH, "w", encoding="utf-8").write(INDEX_SCRIPT)
print(f"[OK] {SCRIPT_PATH} cree")

# ============================================================
# 3. FRONTEND : Prefetch au hover + Lazy loading
# ============================================================
app_js = open(APP, "r", encoding="utf-8").read()

if "prefetchOnHover" in app_js:
    print("[SKIP] app.js : prefetch hover deja present")
else:
    # Ajouter une fonction prefetch au hover des categories
    HELPER = '''

/* ============================================================
   Prefetch au hover : precharge les produits d'une categorie
   ============================================================ */
function prefetchOnHover(catName) {
  if (!catName) return;
  var key = "eh_prefetch_" + catName;
  var cache = window.__eh_prefetched = window.__eh_prefetched || {};
  if (cache[key]) return;
  cache[key] = true;
  try {
    fetch("/api/products?category=" + encodeURIComponent(catName), {
      credentials: "same-origin"
    }).catch(function () {});
  } catch (e) {}
}

/* Prefetch des images produit (petit hint navigateur) */
function prefetchImage(url) {
  if (!url) return;
  try {
    var i = new Image();
    i.src = url;
  } catch (e) {}
}
'''
    # Inserer avant la fonction init() ou avant les DOMContentLoaded
    MARKER = "document.addEventListener(\"DOMContentLoaded\", init);"
    if MARKER in app_js:
        app_js = app_js.replace(MARKER, HELPER + "\n" + MARKER, 1)
        print("[OK] app.js : prefetchOnHover() ajoute")
    else:
        # Inserer avant dernier })();
        last = app_js.rfind("})();")
        if last > 0:
            app_js = app_js[:last] + HELPER + "\n" + app_js[last:]
            print("[OK] app.js : prefetchOnHover() ajoute (fallback)")

    # Ajouter le hook hover sur les categories rendues
    OLD_RENDER = '''    card.appendChild(el("span", "pt-cat-name", cat.name));
    card.appendChild(el("span", "pt-cat-count", cat.total + " produit" + (cat.total > 1 ? "s" : "")));
    box.appendChild(card);'''
    NEW_RENDER = '''    card.appendChild(el("span", "pt-cat-name", cat.name));
    card.appendChild(el("span", "pt-cat-count", cat.total + " produit" + (cat.total > 1 ? "s" : "")));
    // Prefetch au survol
    card.addEventListener("mouseenter", function () { prefetchOnHover(cat.name); });
    card.addEventListener("touchstart", function () { prefetchOnHover(cat.name); }, { passive: true });
    box.appendChild(card);'''

    if OLD_RENDER in app_js:
        app_js = app_js.replace(OLD_RENDER, NEW_RENDER, 1)
        print("[OK] app.js : prefetch hover sur categories")

    open(APP, "w", encoding="utf-8").write(app_js)

# ============================================================
# 4. Bump versions pour forcer reload
# ============================================================
idx = open(INDEX, "r", encoding="utf-8").read()
idx = re.sub(r'(app\.js\?v=)[\d.]+', r'\g<1>17', idx)
open(INDEX, "w", encoding="utf-8").write(idx)
print("[OK] index.html : app.js v=17")

# ============================================================
# 5. VERIF
# ============================================================
print("\n" + "=" * 70)
print("VERIFICATION")
print("=" * 70)
m = open(MAIN, "r", encoding="utf-8").read()
a = open(APP, "r", encoding="utf-8").read()
h = open(INDEX, "r", encoding="utf-8").read()

checks = [
    ("main.py : PatientCacheMiddleware", "PatientCacheMiddleware" in m),
    ("main.py : Brotli (fallback)", "BrotliMiddleware" in m),
    ("app.js : prefetchOnHover", "prefetchOnHover" in a),
    ("app.js : prefetch au hover", 'addEventListener("mouseenter"' in a),
    ("app.js v=17", "app.js?v=17" in h),
    ("add_indexes_v2.py cree", os.path.exists(SCRIPT_PATH)),
]
all_ok = True
for label, ok in checks:
    if not ok: all_ok = False
    print(f"  [{'OK' if ok else '!!'}] {label}")

print("\n" + "=" * 70)
if all_ok:
    print("OPTIMISATIONS PATIENT OK")
else:
    print("PATCH PARTIEL - verifie ci-dessus")
print("=" * 70)

print(f"\n[BACKUP] {bak}")
print("\n[CMD 1] Ajouter les index SQLite (UNE fois) :")
print("  python add_indexes_v2.py")
print("\n[CMD 2] Restart Uvicorn OBLIGATOIRE :")
print("  taskkill /F /IM uvicorn.exe 2>nul")
print("  taskkill /F /IM python.exe 2>nul")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print("\n[TEST]")
print("  1) / -> hover sur une categorie -> les produits sont precharges")
print("  2) Clique la categorie -> affichage INSTANTANE")
print("  3) F12 Network -> verifier que /api/products a 'Cache-Control'")