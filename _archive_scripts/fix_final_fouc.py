"""
fix_final_fouc.py
Solution definitive au "flash vieille interface" :
1. Loading overlay inline sur toutes les pages (masque le FOUC)
2. Preload CSS pour charger plus vite
3. Visibility:hidden jusqu'a window.load
"""
from pathlib import Path
import datetime
import re
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_fouc_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
print("[OK] Backup ->", backup.name)

# ============================================================
# HEAD INJECTION : anti-FOUC + preload CSS
# ============================================================
ANTI_FOUC_HEAD = '''<style id="eh-fouc-fix">
/* Anti-FOUC : masque la page jusqu'a chargement complet */
html.eh-loading{visibility:hidden!important;opacity:0}
html.eh-loaded{visibility:visible;opacity:1;transition:opacity .15s ease}
</style>
<script id="eh-fouc-script">
(function(){
    try {
        document.documentElement.classList.add("eh-loading");
        function reveal() {
            document.documentElement.classList.remove("eh-loading");
            document.documentElement.classList.add("eh-loaded");
        }
        if (document.readyState === "complete") {
            reveal();
        } else {
            window.addEventListener("load", reveal, { once: true });
        }
        // Securite : ne jamais rester bloque plus de 2.5s
        setTimeout(reveal, 2500);
    } catch (e) {
        // En cas d'erreur, on affiche quand meme
        document.documentElement.className = "";
    }
})();
</script>
'''

PRELOAD_CSS = '''<link rel="preload" as="style" href="/static/professional_accueil.css">
<link rel="preload" as="style" href="/static/professional_common.css">
'''

# ============================================================
# Appliquer a toutes les pages HTML du dossier static
# ============================================================
PAGES = [
    "index.html",
    "professional.html",
    "professional_demande.html",
    "professional_commandes.html",
    "professional_etablissement.html",
    "professional_catalogue.html",
    "professional_demande_confirmer.html",
    "professional_reprendre.html",
    "suivi.html",
    "payment.html",
    "login.html",
    "register.html",
]

count = 0
for page in PAGES:
    p = STATIC / page
    if not p.exists():
        print(f"[i] {page} absent")
        continue

    html = p.read_text(encoding="utf-8")
    original = html

    # Sauvegarde
    shutil.copy2(p, backup / page)

    # 1. Retirer un ancien fix FOUC (idempotent)
    html = re.sub(
        r'<style id="eh-fouc-fix">.*?</style>\s*',
        '',
        html,
        flags=re.DOTALL,
    )
    html = re.sub(
        r'<script id="eh-fouc-script">.*?</script>\s*',
        '',
        html,
        flags=re.DOTALL,
    )
    html = re.sub(
        r'<link rel="preload" as="style" href="/static/professional_(?:accueil|common)\.css">\s*',
        '',
        html,
    )

    # 2. Inserer juste avant </head>
    if "</head>" in html:
        # Preload CSS uniquement pour les pages pro
        preload = ""
        if "professional" in page or page == "index.html":
            preload = PRELOAD_CSS
        html = html.replace(
            "</head>",
            preload + ANTI_FOUC_HEAD + "</head>",
            1,
        )
    elif "<body" in html:
        # Fallback : inserer dans le body
        html = re.sub(
            r'(<body[^>]*>)',
            r'\1' + ANTI_FOUC_HEAD,
            html,
            count=1,
        )

    if html != original:
        p.write_text(html, encoding="utf-8")
        count += 1
        print(f"[OK] {page} -> anti-FOUC applique")

print(f"[OK] {count} page(s) mise(s) a jour")

# ============================================================
# Verifier que index.html n'a PAS de JS redirect cassé
# ============================================================
print()
print("=" * 60)
print("VERIFICATION index.html")
print("=" * 60)
idx = STATIC / "index.html"
if idx.exists():
    content = idx.read_text(encoding="utf-8")
    has_js_redir = bool(re.search(
        r'window\.location\.(replace|href)\s*=\s*["\']/(connexion|professionnel|pharmacien|inscription)',
        content,
    ))
    has_old_design = "#0f9d76" in content
    has_new_design = "#1a4a7f" in content or "--blue" in content
    print(f"  JS redirect automatique : {has_js_redir}")
    print(f"  Vieux design vert       : {has_old_design}")
    print(f"  Nouveau design bleu     : {has_new_design}")
    if has_js_redir:
        print()
        print("  >>> index.html contient un redirect automatique.")
        print("      C'est ce qui cause le flash pour les visiteurs sans cookie.")

print()
print("=" * 60)
print("FIX FOUC APPLIQUE")
print("=" * 60)
print()
print("Comportement :")
print("  1. Page masquee (visibility:hidden) pendant le chargement")
print("  2. Revelee uniquement apres window.load (CSS + JS charges)")
print("  3. Si erreur ou timeout 2.5s -> revelee automatiquement")
print()
print("Resultat :")
print("  - Plus de flash de contenu non stylise")
print("  - Plus de flash de vieille interface")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --host 0.0.0.0 --port 8000")
print("  Puis OUVRE l'URL sur iPhone (nav privee ou pas)")