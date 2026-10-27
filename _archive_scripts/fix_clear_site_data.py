"""
fix_clear_site_data.py
Restaure main.py depuis le backup, puis reinsere proprement
ClearSiteDataMiddleware (hors try).
"""
from pathlib import Path
import re
import shutil

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
BAK = MAIN.with_suffix(".py.bak4")

if not BAK.exists():
    print("[!] Backup .py.bak4 introuvable. Essayer .py.bak3/.py.bak/.py.bak2")
    for alt in (".py.bak3", ".py.bak2", ".py.bak"):
        alt_path = MAIN.with_suffix(alt)
        if alt_path.exists():
            BAK = alt_path
            print(f"[OK] Utilise {alt_path.name}")
            break
    else:
        print("[!] Aucun backup trouve. Arret.")
        raise SystemExit(1)

# 1. Restaurer
shutil.copy2(BAK, MAIN)
print(f"[OK] main.py restaure depuis {BAK.name}")

# 2. Verifier qu'on a le bon etat (sans ClearSiteDataMiddleware)
src = MAIN.read_text(encoding="utf-8")
if "ClearSiteDataMiddleware" in src:
    # Retirer tout bloc existant
    src = re.sub(
        r"#\s*=+\n#\s*V8.*?ClearSiteDataMiddleware.*?\n(?:try:\n\s+app\.add_middleware\(ClearSiteDataMiddleware\)\nexcept Exception:\n\s+pass\n)?",
        "",
        src,
        flags=re.DOTALL,
    )
    print("[OK] Anciens blocs ClearSiteData retires")

# 3. Inserer proprement apres le dernier app.add_middleware (hors try)
middleware = '''

# ============================================================
# V8 - Clear-Site-Data pour Safari iOS
# Force Safari a vider son cache HTTP pour ce domaine a chaque HTML servi.
# ============================================================
class ClearSiteDataMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        ctype = response.headers.get("content-type", "").lower()
        if "text/html" in ctype:
            response.headers["Clear-Site-Data"] = '"cache"'
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

# Enregistrement direct (pas dans un try) — on est sur que BaseHTTPMiddleware est importe
app.add_middleware(ClearSiteDataMiddleware)
'''

# Trouver la ligne "app.add_middleware(NoCacheAllStatic)" et inserer APRES
anchor = "app.add_middleware(NoCacheAllStatic)"
if anchor in src:
    idx = src.find(anchor)
    end = src.find("\n", idx)
    src = src[:end+1] + middleware + src[end+1:]
    print("[OK] ClearSiteDataMiddleware insere apres NoCacheAllStatic")
else:
    # Fallback : apres "app = FastAPI(...)"
    m = re.search(r"^app = FastAPI\([^\)]*\)", src, re.MULTILINE)
    if m:
        src = src[:m.end()] + "\n" + middleware + src[m.end():]
        print("[OK] ClearSiteDataMiddleware insere apres FastAPI()")
    else:
        print("[!] Point d'insertion introuvable")

MAIN.write_text(src, encoding="utf-8")

# 4. Verification syntaxe
import py_compile
try:
    py_compile.compile(str(MAIN), doraise=True)
    print("[OK] Syntaxe main.py valide")
except py_compile.PyCompileError as e:
    print("[!] ERREUR de syntaxe :", e)
    raise SystemExit(1)

print()
print("=" * 60)
print("FIX APPLIQUE")
print("=" * 60)
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print("=" * 60)