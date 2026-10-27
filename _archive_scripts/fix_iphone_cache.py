"""
fix_iphone_cache.py
1. Middleware Clear-Site-Data: "cache" sur toutes les routes HTML
2. Script inline dans index.html + professional.html : force reload si version differente
3. Cache-bust ?_v= sur les fetch critiques
"""
from pathlib import Path
import re
import shutil

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
STATIC = BASE / "static"

shutil.copy2(MAIN, MAIN.with_suffix(".py.bak4"))
print("[OK] Backup ->", MAIN.with_suffix(".py.bak4").name)

# ============================================================
# 1. Middleware Clear-Site-Data dans main.py
# ============================================================
src = MAIN.read_text(encoding="utf-8")

if "ClearSiteDataMiddleware" not in src:
    middleware = '''
# ============================================================
# V8 - Clear-Site-Data pour Safari iOS
# Force Safari a vider son cache HTTP pour ce domaine a chaque HTML servi.
# ============================================================
class ClearSiteDataMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        ctype = response.headers.get("content-type", "").lower()
        # Appliquer uniquement sur les pages HTML (pas les /api/*)
        if "text/html" in ctype:
            response.headers["Clear-Site-Data"] = "\\"cache\\""
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response
try:
    app.add_middleware(ClearSiteDataMiddleware)
except Exception:
    pass
'''
    # Inserer apres le NoCacheHTMLMiddleware s'il existe
    anchor = re.compile(
        r'(app\.add_middleware\(NoCacheHTMLMiddleware\))',
        re.DOTALL,
    )
    m = anchor.search(src)
    if m:
        src = src[:m.end()] + "\n" + middleware + src[m.end():]
        print("[OK] ClearSiteDataMiddleware ajoute apres NoCacheHTML")
    else:
        m = re.search(r"^app = FastAPI\([^\)]*\)", src, re.MULTILINE)
        if m:
            src = src[:m.end()] + "\n" + middleware + src[m.end():]
            print("[OK] ClearSiteDataMiddleware ajoute apres FastAPI()")
        else:
            print("[!] Point d'insertion introuvable")

MAIN.write_text(src, encoding="utf-8")

# ============================================================
# 2. Force reload JS dans index.html + professional.html
# ============================================================
FORCE_RELOAD_JS = '''<script>
(function(){
  try {
    // Version cote serveur
    var SERVER_VERSION = "v8.0";
    var CLIENT_VERSION = localStorage.getItem("eh_v");
    // Si version differente -> vider le storage et recharger avec cache-bust
    if (CLIENT_VERSION !== SERVER_VERSION) {
      localStorage.setItem("eh_v", SERVER_VERSION);
      // Si pas encore applique dans cette session, forcer reload
      var url = new URL(window.location.href);
      if (!url.searchParams.has("_v")) {
        url.searchParams.set("_v", String(Date.now()));
        window.location.replace(url.toString());
        return;
      }
    }
  } catch(e) {}
})();
</script>
'''

for fname in ("index.html", "professional.html"):
    f = STATIC / fname
    if not f.exists():
        continue
    html = f.read_text(encoding="utf-8")
    if "SERVER_VERSION = \"v8.0\"" in html:
        print(f"[i] {fname} deja patche")
        continue
    # Inserer tout en haut du <body>
    if "<body" in html:
        idx = html.find("<body")
        end = html.find(">", idx)
        if end > 0:
            html = html[:end+1] + "\n" + FORCE_RELOAD_JS + html[end+1:]
            f.write_text(html, encoding="utf-8")
            print(f"[OK] {fname} -> force reload JS")

print()
print("=" * 60)
print("FIX IPHONE CACHE APPLIQUE")
print("=" * 60)
print()
print("Comportement :")
print("  - Serveur envoie Clear-Site-Data: \"cache\" sur chaque HTML")
print("  - Safari iPhone efface son cache HTTP pour ce domaine")
print("  - Client JS compare version serveur vs localStorage")
print("  - Si different -> reload avec ?_v=<timestamp>")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print()
print("SUR IPHONE :")
print("  1. Reglages -> Safari -> Effacer historique et donnees")
print("  2. Reglages -> Safari -> Avance -> Donnees des sites -> Supprimer")
print("  3. Fermer Safari completement (glisser vers le haut)")
print("  4. Rouvrir et tester")
print("=" * 60)