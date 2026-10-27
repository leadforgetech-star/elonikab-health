"""
fix_cache_bust.py
Force les navigateurs a revalider chaque fichier aupres du serveur.
Ajoute un parametre de version aux liens CSS/JS des pages HTML.
"""
from pathlib import Path
import re
import shutil
import time

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

VERSION = str(int(time.time()))
print("[INFO] Version de cache-bust :", VERSION)

# Backup
backup = BASE / ("_backup_cache_bust_" + VERSION)
backup.mkdir(parents=True, exist_ok=True)
print("[OK] Backup ->", backup.name)

# 1. Ajouter ?v=... aux <link> et <script> dans TOUS les fichiers HTML
def bump_refs(html):
    # <link href="/static/style.css"> -> <link href="/static/style.css?v=XXX">
    # <script src="/static/app.js"></script> -> <script src="/static/app.js?v=XXX"></script>
    html = re.sub(
        r'(href|src)="(/static/[^"]+\.(?:css|js))(?:\?v=[0-9]+)?"',
        r'\1="\2?v=' + VERSION + r'"',
        html,
    )
    return html

total = 0
for html_file in STATIC.glob("*.html"):
    old = html_file.read_text(encoding="utf-8")
    new = bump_refs(old)
    if new != old:
        shutil.copy2(html_file, backup / html_file.name)
        html_file.write_text(new, encoding="utf-8")
        print("[OK]", html_file.name)
        total += 1

print("[OK]", total, "fichiers HTML mis a jour avec ?v=" + VERSION)

# 2. Ajouter des headers "no-cache" pour /static/* dans main.py
MAIN = BASE / "main.py"
if MAIN.exists():
    shutil.copy2(MAIN, backup / "main.py")
    src = MAIN.read_text(encoding="utf-8")

    # Verifier si un middleware NoCache existe deja
    if "NoCacheAllStatic" not in src:
        # Retirer l'ancien StaticCacheMiddleware s'il existe
        src = re.sub(
            r"# --- Performance : cache navigateur pour /static/ ---.*?app\.add_middleware\(StaticCacheMiddleware\)\n",
            "",
            src,
            flags=re.DOTALL,
        )
        src = re.sub(
            r"class StaticCacheMiddleware.*?app\.add_middleware\(StaticCacheMiddleware\)\n",
            "",
            src,
            flags=re.DOTALL,
        )
        src = re.sub(
            r"class NoCacheStaticFiles.*?name=\"static\"\)\n",
            "",
            src,
            flags=re.DOTALL,
        )

        # Ajouter un middleware propre
        middleware = '''
# --- Cache bust V4 : no-store sur tout /static ---
class NoCacheAllStatic(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheAllStatic)
'''
        # Inserer avant le premier app.mount("/static", ...)
        anchor = 'app.mount("/static", StaticFiles'
        if anchor in src:
            src = src.replace(anchor, middleware + "\n" + anchor, 1)
        else:
            # Fallback : apres la definition de app = FastAPI(...)
            m = re.search(r"^app = FastAPI\([^\n]*\)\s*$", src, re.M)
            if m:
                src = src[:m.end()] + middleware + src[m.end():]

        MAIN.write_text(src, encoding="utf-8")
        print("[OK] main.py -> middleware NoCacheAllStatic ajoute")
    else:
        print("[i] main.py -> deja patche")

print()
print("=" * 60)
print("CACHE-BUST APPLIQUE")
print("=" * 60)
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --host 0.0.0.0 --port 8000")
print()
print("Puis teste SANS ?v= sur l'URL :")
print("  http://127.0.0.1:8000/static/professional.html")