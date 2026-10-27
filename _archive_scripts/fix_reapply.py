"""
fix_reapply.py
Verifie et reapplique les 2 fixes manquants :
1. magic_links.py : HTML + location.replace au lieu de 302
2. eh-loader : overlay CSS inline dans tous les HTML
"""
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
MAGIC = BASE / "v3_modules" / "magic_links.py"

# ============================================================
# 1. VERIFIER magic_links.py
# ============================================================
print("=" * 60)
print("1. VERIFICATION magic_links.py")
print("=" * 60)
print()

src = MAGIC.read_text(encoding="utf-8")

has_location_replace = "window.location.replace" in src
has_redirect_response = "RedirectResponse" in src
has_html_response = "HTMLResponse" in src

print(f"  window.location.replace present : {has_location_replace}")
print(f"  RedirectResponse present        : {has_redirect_response}")
print(f"  HTMLResponse present            : {has_html_response}")
print()

if has_location_replace and not has_redirect_response:
    print("[OK] magic_links.py est deja fixe correctement")
else:
    print("[!] magic_links.py N'EST PAS fixe -> application du fix...")
    print()

    # Trouver la fonction access_magic_link
    pattern = re.compile(
        r'(@app\.get\("/acces/\{token\}"[^\n]*\)\n'
        r'def access_magic_link\(token: str\):.*?)(?=\n@app\.|\n\nclass |\n\ndef |\Z)',
        re.DOTALL,
    )
    m = pattern.search(src)
    if not m:
        print("[!] Impossible de trouver access_magic_link")
        raise SystemExit(1)

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

        conn.execute(
            "UPDATE magic_links SET used_count = used_count + 1 WHERE id=?",
            (ml["id"],)
        )

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

        role = user["role"]
        if role == "PROFESSIONNEL":
            target = "/professionnel"
        elif role in ("PHARMACIEN", "ADMIN"):
            target = "/pharmacien"
        else:
            target = "/"

        cb = str(int(time.time() * 1000))
        html = (
            '<!DOCTYPE html>'
            '<html lang="fr"><head><meta charset="utf-8">'
            '<title>Redirection...</title>'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<style>'
            'body{font-family:-apple-system,"Segoe UI",system-ui,sans-serif;'
            'display:flex;align-items:center;justify-content:center;'
            'height:100vh;margin:0;background:#F5F8FC;color:#64748B}'
            '.sp{width:40px;height:40px;border:3px solid #E2E8F0;'
            'border-top-color:#1A4A7E;border-radius:50%;'
            'animation:s 1s linear infinite}'
            '@keyframes s{to{transform:rotate(360deg)}}'
            '</style></head><body><div class="sp"></div>'
            '<script>'
            'window.location.replace("' + target + '?_v=' + cb + '");'
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
        conn.close()'''

    src = pattern.sub(new_fn + "\n", src, count=1)
    MAGIC.write_text(src, encoding="utf-8")
    print("[OK] magic_links.py reecrit")
    print()

# ============================================================
# 2. INJECTER eh-loader dans tous les HTML
# ============================================================
print("=" * 60)
print("2. INJECTION eh-loader")
print("=" * 60)
print()

OVERLAY = '''<div id="eh-loader" aria-hidden="true"><div class="eh-sp"></div></div>
<style id="eh-loader-style">
#eh-loader{position:fixed;inset:0;z-index:999999;background:#F5F8FC;display:flex;align-items:center;justify-content:center;transition:opacity .15s ease}
#eh-loader.eh-hide{opacity:0;pointer-events:none}
#eh-loader .eh-sp{width:36px;height:36px;border:3px solid #E2E8F0;border-top-color:#1A4A7E;border-radius:50%;animation:eh-spin .8s linear infinite}
@keyframes eh-spin{to{transform:rotate(360deg)}}
</style>
<script>
(function(){
  function h(){
    var el=document.getElementById("eh-loader");
    if(!el||el.classList.contains("eh-hide"))return;
    el.classList.add("eh-hide");
    setTimeout(function(){if(el&&el.parentNode)el.parentNode.removeChild(el);},180);
  }
  setTimeout(h,1200);
  if(document.readyState==="complete")h();
  else window.addEventListener("load",h,{once:true});
})();
</script>'''

html_files = sorted(STATIC.glob("*.html"))
patched = 0

for f in html_files:
    content = f.read_text(encoding="utf-8")

    # Retirer un ancien loader s'il existe
    content = re.sub(
        r'<div id="eh-loader".*?</script>\s*',
        "",
        content,
        flags=re.DOTALL,
    )

    # Inserer apres <body ...>
    m = re.search(r'<body[^>]*>', content)
    if not m:
        print(f"[SKIP] {f.name} : pas de <body>")
        continue

    content = content[:m.end()] + "\n" + OVERLAY + content[m.end():]
    f.write_text(content, encoding="utf-8")
    patched += 1
    print(f"[OK] {f.name}")

print()
print(f"[OK] {patched} fichiers HTML patches")

# ============================================================
# 3. RESUME
# ============================================================
print()
print("=" * 60)
print("FIXES REAPPLIQUES")
print("=" * 60)
print()
print("  magic_links.py : HTML + location.replace + ?_v=<timestamp>")
print(f"  {patched} fichiers HTML : overlay eh-loader")
print()
print("PROCHAINE ETAPE :")
print("  1. Redemarrer Uvicorn")
print("  2. Sur PC : Ctrl+Shift+Suppr -> vider cache -> Ctrl+Shift+R")
print("  3. Sur iPhone : Reglages -> Safari -> Effacer historique")
print("  4. Tester le lien /acces/...")
print("=" * 60)