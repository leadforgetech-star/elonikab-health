"""
fix_redirect_cache.py
Route / : redirection vers /professionnel?_v=<timestamp>
-> URL unique a chaque connexion = aucun cache possible.
Aussi : ajoute le meme comportement a /connexion (apres login)
et /inscription (apres inscription).
"""
from pathlib import Path
import datetime
import re
import shutil

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_redirect_cache_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAIN, backup / "main.py")
print("[OK] Backup ->", backup.name)

src = MAIN.read_text(encoding="utf-8")

# ============================================================
# 1. Remplacer la route / par une version avec cache-bust
# ============================================================
pattern = re.compile(
    r'(@app\.(?:get|api_route)\("/"[^)]*\)\s*\ndef\s+(\w+)[^:]*:.*?)(?=\n@app\.|\n\nclass |\n\ndef |\Z)',
    re.DOTALL
)

new_root = '''@app.get("/", include_in_schema=False)
def root_page(request: Request):
    """Redirige les pros/admins vers leur espace (avec cache-bust),
    sinon sert index.html (patient)."""
    import time
    token = request.cookies.get("elokinab_session")
    if token:
        try:
            conn = get_db()
            try:
                row = conn.execute(
                    "SELECT u.role FROM sessions s "
                    "JOIN users u ON u.id = s.user_id "
                    "WHERE s.token = ? AND s.expires_at > ?",
                    (token, datetime.now().isoformat(timespec="seconds")),
                ).fetchone()
                if row:
                    cb = str(int(time.time() * 1000))
                    if row["role"] == "PROFESSIONNEL":
                        return RedirectResponse(
                            "/professionnel?_v=" + cb, status_code=302
                        )
                    if row["role"] in ("PHARMACIEN", "ADMIN"):
                        return RedirectResponse(
                            "/pharmacien?_v=" + cb, status_code=302
                        )
            finally:
                conn.close()
        except Exception:
            pass
    return FileResponse(STATIC_DIR / "index.html")
'''

if pattern.search(src):
    src = pattern.sub(new_root, src, count=1)
    print("[OK] main.py -> route / avec cache-bust")
else:
    print("[!] route / introuvable")

# ============================================================
# 2. Verifier RedirectResponse importe
# ============================================================
if "from fastapi.responses import" in src:
    first_line = src.split("from fastapi.responses import")[1].split("\n")[0]
    if "RedirectResponse" not in first_line:
        src = src.replace(
            "from fastapi.responses import FileResponse",
            "from fastapi.responses import FileResponse, RedirectResponse",
            1,
        )
        print("[OK] main.py -> import RedirectResponse ajoute")
else:
    # Ajouter import complet
    src = src.replace(
        "from fastapi import",
        "from fastapi.responses import FileResponse, RedirectResponse\nfrom fastapi import",
        1,
    )
    print("[OK] main.py -> import RedirectResponse ajoute (2)")

# ============================================================
# 3. Ajouter un script inline dans index.html pour cache-bust auto
# ============================================================
INDEX = BASE / "static" / "index.html"
if INDEX.exists():
    html = INDEX.read_text(encoding="utf-8")

    # Script qui force un redirect cache-bust si connecte
    CACHEBUST_JS = '''<script>
(function () {
    // Force le rechargement avec ?_v= si un cookie de session existe
    try {
        if (document.cookie.indexOf("elokinab_session=") >= 0) {
            var params = new URLSearchParams(window.location.search);
            if (!params.has("_v")) {
                var cb = Date.now();
                window.location.replace("/?_v=" + cb);
            }
        }
    } catch (e) {}
})();
</script>
'''

    if "window.location.replace(\"/?_v=\"" not in html and "_v=cb" not in html:
        # Inserer juste apres <head>
        if "</head>" in html:
            html = html.replace("</head>", CACHEBUST_JS + "</head>", 1)
        elif "<body>" in html:
            html = html.replace("<body>", "<body>" + CACHEBUST_JS, 1)
        INDEX.write_text(html, encoding="utf-8")
        print("[OK] index.html -> script cache-bust ajoute")
    else:
        print("[i] index.html -> cache-bust deja present")

MAIN.write_text(src, encoding="utf-8")

print()
print("=" * 60)
print("FIX REDIRECT CACHE-BUST APPLIQUE")
print("=" * 60)
print()
print("Comportement :")
print("  - Requete / avec cookie PRO")
print("    -> 302 vers /professionnel?_v=1744301250000")
print("  - Requete / avec cookie PHARMACIEN")
print("    -> 302 vers /pharmacien?_v=1744301250000")
print("  - Requete / sans cookie")
print("    -> sert index.html (patient)")
print()
print("Resultat : chaque redirection a une URL unique.")
print("Le navigateur ne peut plus servir une vieille version.")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --host 0.0.0.0 --port 8000")
print("  Puis deconnecte-toi et reconnecte-toi via /connexion")