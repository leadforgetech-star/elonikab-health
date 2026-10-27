"""
fix_html_cache.py
Ajoute des en-tetes no-cache sur toutes les routes HTML propres
(/professionnel, /inscription, /connexion, /pharmacien, /suivi, etc.)
pour eviter que le navigateur affiche une ancienne version avant redirection.
"""
from pathlib import Path
import re
import shutil

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
shutil.copy2(MAIN, MAIN.with_suffix(".py.bak"))
print("[OK] Backup ->", MAIN.with_suffix(".py.bak").name)

src = MAIN.read_text(encoding="utf-8")

# ============================================================
# 1. Verifier que Response est importe
# ============================================================
if "from fastapi.responses import FileResponse" in src and "Response" not in src.split("from fastapi.responses import")[1].split("\n")[0]:
    src = src.replace(
        "from fastapi.responses import FileResponse",
        "from fastapi.responses import FileResponse, Response",
        1,
    )
    print("[OK] Import Response ajoute")
elif "Response" in src.split("from fastapi.responses import")[1][:80]:
    print("[i] Response deja importe")

# ============================================================
# 2. Middleware no-cache pour les routes HTML (hors /static/)
# ============================================================
if "NoCacheHTMLMiddleware" not in src:
    middleware = '''
# ============================================================
# V7 - No-cache sur les routes HTML propres
# (les /static/ ont deja leur no-cache via NoCacheAllStatic)
# ============================================================
from starlette.middleware.base import BaseHTTPMiddleware
class NoCacheHTMLMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        ctype = response.headers.get("content-type", "").lower()
        # No-cache uniquement pour les pages HTML (routes + /static/*.html)
        if "text/html" in ctype:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response
try:
    app.add_middleware(NoCacheHTMLMiddleware)
except Exception:
    pass
'''
    # Inserer juste apres l'ajout du NoCacheAllStatic (s'il existe)
    anchor_pattern = re.compile(
        r"(app\.add_middleware\(NoCacheAllStatic\))",
        re.DOTALL,
    )
    m = anchor_pattern.search(src)
    if m:
        src = src[:m.end()] + "\n" + middleware + src[m.end():]
        print("[OK] NoCacheHTMLMiddleware ajoute apres NoCacheAllStatic")
    else:
        # Fallback : apres "app = FastAPI(...)"
        m = re.search(r"^app = FastAPI\([^\)]*\)\s*$", src, re.MULTILINE)
        if m:
            src = src[:m.end()] + "\n" + middleware + src[m.end():]
            print("[OK] NoCacheHTMLMiddleware ajoute apres FastAPI()")
        else:
            print("[!] Point d'insertion introuvable")

MAIN.write_text(src, encoding="utf-8")

# ============================================================
# 3. Verification
# ============================================================
check = MAIN.read_text(encoding="utf-8")
print()
print("=" * 60)
print("VERIFICATION")
print("=" * 60)
print("  NoCacheHTMLMiddleware present :", "NoCacheHTMLMiddleware" in check)
print("  Import Response present       :", "Response" in check.split("from fastapi.responses")[1][:100])
print()
print("=" * 60)
print("FIX APPLIQUE")
print("=" * 60)
print()
print("Comportement :")
print("  - Toute reponse HTML (routes propres + /static/*.html)")
print("    => Cache-Control: no-store")
print("  - Le navigateur revalidera toujours, plus de vieux HTML")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print("  Puis vide le cache navigateur une derniere fois.")
print("=" * 60)