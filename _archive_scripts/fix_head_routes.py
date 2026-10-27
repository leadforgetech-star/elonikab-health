"""
fix_head_routes.py
Ajoute le support HEAD sur les routes HTML propres pour que
curl -sI fonctionne (et pour que les navigateurs fassent des pre-requetes HEAD).
"""
from pathlib import Path
import re
import shutil

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
shutil.copy2(MAIN, MAIN.with_suffix(".py.bak2"))
print("[OK] Backup ->", MAIN.with_suffix(".py.bak2").name)

src = MAIN.read_text(encoding="utf-8")

# Liste des routes HTML a convertir de @app.get en @app.api_route(GET, HEAD)
ROUTES = [
    "/professionnel",
    "/connexion",
    "/inscription",
    "/pharmacien",
    "/suivi",
    "/professionnel/demande",
    "/professionnel/commandes",
    "/professionnel/etablissement",
    "/professionnel/catalogue",
]

count = 0
for route in ROUTES:
    # Pattern : @app.get("<route>", include_in_schema=False)
    #      ou : @app.get("<route>")
    pattern = re.compile(
        r'@app\.get\("' + re.escape(route) + r'"(,\s*include_in_schema\s*=\s*False)?\)',
        re.MULTILINE,
    )
    def repl(m):
        args = m.group(1) or ""
        return '@app.api_route("' + route + '", methods=["GET", "HEAD"]' + args + ')'
    new_src = pattern.sub(repl, src)
    if new_src != src:
        count += 1
        src = new_src
        print(f"[OK] {route} -> GET + HEAD")

MAIN.write_text(src, encoding="utf-8")
print(f"[OK] {count} route(s) mises a jour")

# Verification
check = MAIN.read_text(encoding="utf-8")
n_api = check.count('methods=["GET", "HEAD"]')
print()
print(f"[VERIF] {n_api} route(s) avec methods=[GET, HEAD]")
print()
print("=" * 60)
print("FIX APPLIQUE")
print("=" * 60)
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print("  Puis test :")
print('  curl -sI http://127.0.0.1:8000/professionnel | findstr /I "cache"')
print("=" * 60)