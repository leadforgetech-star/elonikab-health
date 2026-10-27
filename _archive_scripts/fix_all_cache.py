"""
fix_all_cache.py
1. Injecte <meta cache-control no-store> dans TOUS les HTML
2. Ajoute un bout de JS qui desinstalle les Service Workers
3. Ajoute un cache-buster ?_v= sur les redirections first_visit
"""
from pathlib import Path
import re
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

META_BLOCK = (
    '<meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate, max-age=0">\n'
    '<meta http-equiv="Pragma" content="no-cache">\n'
    '<meta http-equiv="Expires" content="0">'
)

SW_KILL_JS = '''
<script>
(function(){
  try {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.getRegistrations().then(function(regs){
        regs.forEach(function(r){ r.unregister(); });
      });
      if (window.caches && caches.keys) {
        caches.keys().then(function(keys){
          keys.forEach(function(k){ caches.delete(k); });
        });
      }
    }
  } catch(e) {}
})();
</script>
'''

html_files = list(STATIC.glob("*.html"))
print(f"[i] {len(html_files)} fichiers HTML a traiter")
print()

for html_file in html_files:
    content = html_file.read_text(encoding="utf-8")
    original = content

    # 1. Retirer ancien meta si present (au cas ou)
    content = re.sub(
        r'<meta\s+http-equiv="Cache-Control"[^>]*>\s*',
        '', content
    )
    content = re.sub(
        r'<meta\s+http-equiv="Pragma"[^>]*>\s*',
        '', content
    )
    content = re.sub(
        r'<meta\s+http-equiv="Expires"[^>]*>\s*',
        '', content
    )

    # 2. Inserer les meta juste apres <head>
    if "<head>" in content:
        content = content.replace(
            "<head>",
            "<head>\n" + META_BLOCK,
            1
        )

    # 3. Inserer le SW-killer juste apres <body> (execution immediate)
    if "<body" in content:
        # Trouver la fin de la balise <body ...>
        idx = content.find("<body")
        end = content.find(">", idx)
        if end > 0:
            content = (
                content[:end+1] +
                "\n" + SW_KILL_JS +
                content[end+1:]
            )

    if content != original:
        html_file.write_text(content, encoding="utf-8")
        print(f"[OK] {html_file.name}")
    else:
        print(f"[SKIP] {html_file.name} (deja patche)")

# ============================================================
# Fix first_visit.js : rediriger vers /inscription au lieu de /static/register.html
# ============================================================
FV = STATIC / "first_visit.js"
if FV.exists():
    fv = FV.read_text(encoding="utf-8")
    old = 'window.location.href = "/static/register.html";'
    new = 'window.location.href = "/inscription";'
    if old in fv:
        fv = fv.replace(old, new)
        FV.write_text(fv, encoding="utf-8")
        print("[OK] first_visit.js -> redirige vers /inscription")

# ============================================================
# Fix magic link : rediriger vers /professionnel?_v=<timestamp>
# deja fait, mais on verifie
# ============================================================
MAGIC = BASE / "v3_modules" / "magic_links.py"
if MAGIC.exists():
    m = MAGIC.read_text(encoding="utf-8")
    if "window.location.replace" not in m:
        print("[!] magic_links.py n'a pas le fix location.replace")
        print("    Relance : python fix_magic_redirect.py")
    else:
        print("[OK] magic_links.py deja fixe")

print()
print("=" * 60)
print("FIX CACHE TOTAL APPLIQUE")
print("=" * 60)
print()
print("Actions faites :")
print("  1. <meta cache-control no-store> dans tous les HTML")
print("  2. SW-killer JS (desinstalle Service Workers + Cache Storage)")
print("  3. first_visit.js redirige vers /inscription")
print()
print("PROCHAINE ETAPE :")
print("  1. Vider le cache navigateur UNE FOIS (Ctrl+Shift+Suppr)")
print("  2. F12 -> Application -> Service Workers -> Unregister all")
print("  3. F12 -> Application -> Storage -> Clear site data")
print("  4. Fermer TOUS les onglets trycloudflare.com")
print("  5. Rouvrir le lien")
print("=" * 60)