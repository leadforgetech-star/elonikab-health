"""
fix_magic_link_v2.py
Remplace le 302 du magic link par un HTML minimal + JS avec cache-bust.
-> URL unique a chaque clic = aucun cache possible.
"""
from pathlib import Path
import datetime
import re
import shutil

BASE = Path(__file__).resolve().parent
MAGIC = BASE / "v3_modules" / "magic_links.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_magic_v2_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAGIC, backup / "magic_links.py")
print("[OK] Backup ->", backup.name)

src = MAGIC.read_text(encoding="utf-8")

# 1. Verifier si deja patche
if "window.location.replace" in src and "?_v=" in src:
    print("[i] magic_links.py deja patche")
    raise SystemExit(0)

# 2. Trouver la fonction access_magic_link
pattern = re.compile(
    r'(@app\.(?:get|api_route)\("/acces/\{token\}"[^\n]*\n'
    r'def access_magic_link\(token: str\):.*?)(?=\n@app\.|\n\nclass |\n\ndef |\Z)',
    re.DOTALL
)

m = pattern.search(src)
if not m:
    print("[!] access_magic_link introuvable dans magic_links.py")
    raise SystemExit(1)

print("[i] Fonction access_magic_link trouvee")

new_fn = '''@app.get("/acces/{token}", include_in_schema=False)
def access_magic_link(token: str):
    import time
    from fastapi.responses import HTMLResponse
    conn = get_db()
    try:
        ml = conn.execute(
            "SELECT * FROM magic_links WHERE token=?", (token,)
        ).fetchone()
        if ml is None:
            raise HTTPException(404, "Lien invalide")
        if ml["revoked"]:
            raise HTTPException(403, "Lien revoque")
        if ml["expires_at"]:
            try:
                exp = datetime.fromisoformat(ml["expires_at"])
                if datetime.now() > exp:
                    raise HTTPException(403, "Lien expire")
            except ValueError:
                pass
        if ml["max_uses"] and ml["used_count"] >= ml["max_uses"]:
            raise HTTPException(403, "Lien deja utilise")
        user = conn.execute(
            "SELECT * FROM users WHERE id=? AND is_active=1", (ml["user_id"],)
        ).fetchone()
        if user is None:
            raise HTTPException(403, "Utilisateur inactif")

        # Incrementer usage
        conn.execute(
            "UPDATE magic_links SET used_count = used_count + 1 WHERE id=?",
            (ml["id"],)
        )

        # Creer une session
        session_token = secrets.token_urlsafe(48)
        now = datetime.now()
        exp = now + timedelta(days=SESSION_TTL_DAYS)
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at)"
            " VALUES (?, ?, ?, ?)",
            (session_token, user["id"],
             now.isoformat(timespec="seconds"),
             exp.isoformat(timespec="seconds"))
        )
        conn.commit()

        # Determiner la cible
        role = user["role"]
        if role == "PROFESSIONNEL":
            target = "/professionnel"
        elif role in ("PHARMACIEN", "ADMIN"):
            target = "/pharmacien"
        else:
            target = "/"

        # Cache-bust : timestamp unique
        cb = str(int(time.time() * 1000))
        final_url = target + "?_v=" + cb

        # HTML minimal qui force le rechargement avec cache-bust
        html = (
            '<!DOCTYPE html>'
            '<html lang="fr"><head><meta charset="utf-8">'
            '<title>Redirection...</title>'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<style>'
            'body{font-family:-apple-system,"Segoe UI",system-ui,sans-serif;'
            'display:flex;align-items:center;justify-content:center;'
            'height:100vh;margin:0;background:#f7fafc;color:#64748b}'
            '.sp{width:40px;height:40px;border:3px solid #e6ebf1;'
            'border-top-color:#1a4a7f;border-radius:50%;'
            'animation:s 1s linear infinite}'
            '@keyframes s{to{transform:rotate(360deg)}}'
            '</style></head><body><div class="sp"></div>'
            '<script>'
            'window.location.replace("' + final_url + '");'
            '</script>'
            '</body></html>'
        )

        resp = HTMLResponse(content=html)
        resp.set_cookie(
            SESSION_COOKIE, session_token,
            httponly=True, samesite="none", secure=True,
            max_age=SESSION_TTL_DAYS * 86400, path="/"
        )
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
    finally:
        conn.close()
'''

src = pattern.sub(new_fn + "\n", src, count=1)
MAGIC.write_text(src, encoding="utf-8")
print("[OK] magic_links.py -> access_magic_link remplace (HTML+JS+cache-bust)")

# Verification
check = MAGIC.read_text(encoding="utf-8")
print()
print("Verification :")
print("  window.location.replace :", "window.location.replace" in check)
print("  ?_v= cache-bust :", "?_v=" in check)
print("  HTMLResponse :", "HTMLResponse" in check)
print("  Cache-Control no-store :", "no-store" in check)

print()
print("=" * 60)
print("FIX MAGIC LINK V2 APPLIQUE")
print("=" * 60)
print()
print("Comportement :")
print("  /acces/{token}")
print("  -> HTML minimal (spinner)")
print("  -> JS: window.location.replace('/professionnel?_v=<ms>')")
print("  -> URL unique = aucun cache possible")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --host 0.0.0.0 --port 8000")
print("  Puis : python generate_link.py pro@test.tg --days 30")