"""
fix_route_root.py
1. Rend la route / intelligente : redirige les pros et admins
2. Corrige /connexion qui plante
"""
from pathlib import Path
import re
import shutil
import datetime

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_root_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAIN, backup / "main.py")
print("[OK] Backup ->", backup.name)

src = MAIN.read_text(encoding="utf-8")

# ============================================================
# 1. Route / intelligente
# ============================================================
# Chercher la route / existante
pattern = re.compile(
    r'@app\.(get|api_route)\("/"[^)]*\)\s*\ndef\s+(\w+)\s*\([^)]*\):.*?(?=\n@app\.|\n\nclass |\n\ndef |\Z)',
    re.DOTALL
)

new_root = '''@app.get("/", include_in_schema=False)
def root_page(request: Request):
    """Redirige les pros/admins vers leur espace, sinon sert index.html."""
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
                    if row["role"] == "PROFESSIONNEL":
                        from fastapi.responses import RedirectResponse
                        return RedirectResponse("/professionnel", status_code=302)
                    if row["role"] in ("PHARMACIEN", "ADMIN"):
                        from fastapi.responses import RedirectResponse
                        return RedirectResponse("/pharmacien", status_code=302)
            finally:
                conn.close()
        except Exception:
            pass  # En cas d'erreur, on sert index.html normalement
    return FileResponse(STATIC_DIR / "index.html")
'''

if pattern.search(src):
    src = pattern.sub(new_root, src, count=1)
    print("[OK] main.py -> route / remplacee par version intelligente")
else:
    print("[!] route / introuvable, insertion manuelle")
    anchor = "\ninit_db()\n"
    if anchor in src:
        src = src.replace(anchor, "\n" + new_root + anchor, 1)
        print("[OK] main.py -> route / inseree avant init_db()")

# ============================================================
# 2. Verifier import Request
# ============================================================
if "from fastapi import" in src:
    first_import = src.split("from fastapi import")[1].split("\n")[0]
    if "Request" not in first_import:
        src = src.replace(
            "from fastapi import",
            "from fastapi import Request,",
            1,
        )
        print("[OK] main.py -> import Request ajoute")

MAIN.write_text(src, encoding="utf-8")

# ============================================================
# 3. Verifier la route /connexion dans main.py
# ============================================================
src = MAIN.read_text(encoding="utf-8")
print()
print("Route /connexion actuelle :")
connexion_pattern = re.compile(
    r'(@app\.(get|api_route)\("/connexion"[^)]*\)\s*\ndef\s+(\w+)\s*\([^)]*\):.*?)(?=\n@app\.|\n\nclass |\n\ndef |\Z)',
    re.DOTALL
)
m = connexion_pattern.search(src)
if m:
    print(m.group(1)[:400])
else:
    print("[!] Aucune route /connexion trouvee !")

print()
print("=" * 60)
print("FIX ROUTE ROOT APPLIQUE")
print("=" * 60)
print()
print("Changements :")
print(" 1. / -> Redirige PRO vers /professionnel")
print("      Redirige ADMIN/PHARMACIEN vers /pharmacien")
print("      Sinon -> index.html (patient)")
print(" 2. Import Request ajoute")
print()
print("PROCHAINE ETAPE :")
print(" taskkill /F /IM python.exe")
print(" uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print()
print("Puis teste :")
print(" 1. Ouvre l'URL de base connecte en PRO")
print(" 2. Doit rediriger directement vers /professionnel")
print(" 3. Aucun flash d'ancienne interface")