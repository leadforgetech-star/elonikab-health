"""
v4_simplify_demande.py
- 'Depuis le catalogue' -> navigue vers /professionnel/catalogue
- Suppression du bouton 'Ouvrir le catalogue complet' (redondant)
- Page demande : 2 options seulement (Catalogue | Envoyer ma liste WhatsApp)
- Bouton WhatsApp flottant : cercle -> s'etend en 'Support' au scroll
"""
from pathlib import Path
import datetime
import shutil
import re

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_simplify_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
for f in ("professional_demande.html", "professional_demande.js",
          "professional_catalogue.html", "professional_catalogue.js"):
    p = STATIC / f
    if p.exists():
        shutil.copy2(p, backup / f)
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. DEMANDE : refonte de la section "sources"
# ============================================================
DEM = STATIC / "professional_demande.html"
html = DEM.read_text(encoding="utf-8")

# Retirer le bouton "Ouvrir le catalogue complet" ajoute precedentement
html = re.sub(
    r'<a href="/professionnel/catalogue" class="support-btn".*?id="open-catalogue-link">.*?</a>\s*',
    '', html, flags=re.DOTALL)
print("[OK] demande -> bouton 'Ouvrir le catalogue' retire")

# Retirer aussi le bouton WhatsApp en bas (on le remplace ailleurs si besoin)
# mais on garde le 'Discuter avec le support' -> il sera ajoute par les 2 options

# Remplacer le bloc "sources-grid" par 2 options
old_sources = re.compile(
    r'<div class="sources-grid">.*?</div>\s*(?=<h2 class="section-title">)',
    re.DOTALL
)
new_sources = '''<div class="sources-grid">
    <a href="/professionnel/catalogue" class="source-btn" id="src-catalogue">
      <div class="source-icon">&#128722;</div>
      <div class="source-label">Depuis le catalogue</div>
      <div class="source-hint">Parcourir et ajouter des produits</div>
    </a>
    <a class="source-btn" id="src-whatsapp" target="_blank" rel="noopener"
       href="https://wa.me/22871039904?text=Bonjour%20Elokinab%20Health%2C%20je%20souhaite%20passer%20une%20commande%20pour%20mon%20etablissement.%20Voici%20ma%20liste%20%3A%0A%0A">
      <div class="source-icon" style="background:#e6f9ee;color:#25d366">&#128172;</div>
      <div class="source-label">Envoyer ma liste WhatsApp</div>
      <div class="source-hint">PDF, photo ou texte</div>
    </a>
  </div>

  '''
if old_sources.search(html):
    html = old_sources.sub(new_sources, html, count=1)
    print("[OK] demande -> 2 options seulement")
else:
    print("[!] sources-grid non trouve")

# Retirer les modales devenues inutiles (PDF, photo, manuel) - on les garde au cas ou mais on cache
# On les laisse pour ne pas casser le JS (elles ne s'ouvrent plus depuis les sources)

DEM.write_text(html, encoding="utf-8")

# ============================================================
# 2. DEMANDE JS : adapter les handlers
# ============================================================
DEMJS = STATIC / "professional_demande.js"
if DEMJS.exists():
    js = DEMJS.read_text(encoding="utf-8")

    # Retirer les handlers devenus inutiles (src-catalogue etait button)
    # mais garder les handlers pour les items et le send final

    # Le JS actuel attache des listeners sur src-catalogue, src-manual, src-pdf, src-photo
    # Ces ID ne sont plus des buttons (src-catalogue est un <a href>). Les autres ID n'existent plus.
    # On va neutraliser les listeners sur ces elements pour eviter les erreurs JS.

    # On remplace le bloc "document.getElementById('src-manual').addEventListener..." etc.
    # par rien, en gardant le reste.

    # Il faut un peu de prudence ici car le JS peut varier.
    # On va juste supprimer les appels aux elements qui n'existent plus.

    js = re.sub(
        r'document\.getElementById\("src-manual"\)\.addEventListener\([^;]+\);\s*',
        '', js)
    js = re.sub(
        r'document\.getElementById\("src-pdf"\)\.addEventListener\([^;]+\);\s*',
        '', js)
    js = re.sub(
        r'document\.getElementById\("src-photo"\)\.addEventListener\([^;]+\);\s*',
        '', js)
    js = re.sub(
        r'document\.getElementById\("src-catalogue"\)\.addEventListener\([^;]+\);\s*',
        '', js)

    # Idem pour les handlers des modales PDF/photo (leurs triggers n'existent plus)
    # mais on laisse les modales elles-memes dans le HTML au cas ou

    DEMJS.write_text(js, encoding="utf-8")
    print("[OK] demande.js -> handlers nettoyes")

# ============================================================
# 3. CATALOGUE : bouton WhatsApp expansible au scroll
# ============================================================
CAT = STATIC / "professional_catalogue.html"
html = CAT.read_text(encoding="utf-8")

# Remplacer le bouton mini existant par la version extensible
old_mini = re.compile(r'<a class="support-mini".*?</a>', re.DOTALL)
new_mini = '''<a class="support-mini" id="support-mini"
   href="https://wa.me/22871039904?text=Bonjour%20Elokinab%20Health%2C%20j%27ai%20une%20question."
   target="_blank" rel="noopener" title="Contacter le support">
  <span class="ico">&#128172;</span>
  <span class="label">Support pharmacie</span>
</a>
'''
if old_mini.search(html):
    html = old_mini.sub(new_mini, html, count=1)
    print("[OK] catalogue -> bouton WhatsApp remplace par version extensible")
else:
    # Insertion fraiche
    html = html.replace("</body>", new_mini + "\n</body>", 1)
    print("[OK] catalogue -> bouton WhatsApp insere")

# Remplacer le CSS du support-mini par la version extensible
new_support_css = '''
/* ---- Bouton support WhatsApp expansible ---- */
.support-mini{
  position:fixed;bottom:100px;right:16px;z-index:190;
  height:52px;
  border-radius:26px;
  background:#25d366;color:#fff;border:0;cursor:pointer;
  display:inline-flex;align-items:center;justify-content:center;
  padding:0 16px;
  box-shadow:0 6px 18px rgba(37,211,102,.4);
  transition:all .3s cubic-bezier(.4,0,.2,1);
  overflow:hidden;
  text-decoration:none;
  gap:8px;
  max-width:calc(100vw - 32px);
}
.support-mini .ico{
  font-size:22px;line-height:1;flex-shrink:0;
}
.support-mini .label{
  display:none;
  font-size:13px;font-weight:800;
  white-space:nowrap;
  color:#fff;
}
.support-mini.expanded{
  padding:0 20px;
}
.support-mini.expanded .label{
  display:inline;
}
.support-mini:hover{background:#1da851;transform:translateY(-1px)}

/* Version pleine largeur sur les pages a carte centree */
.support-btn{
  display:flex;align-items:center;justify-content:center;gap:8px;
  width:100%;padding:13px;border:0;border-radius:12px;
  background:#25d366;color:#fff;font-weight:800;font-size:14px;
  margin-top:12px;text-decoration:none;font-family:inherit;
  transition:.15s;cursor:pointer;
}
.support-btn:hover{background:#1da851;transform:translateY(-1px)}
.support-btn .ico{font-size:16px}
'''
# Retirer l'ancien bloc support CSS
html = re.sub(
    r'/\* ---- Bouton support WhatsApp ---- \*/.*?(?=</style>)',
    new_support_css,
    html,
    flags=re.DOTALL
)
# Si pas trouve, ajouter avant </style>
if ".support-mini{" not in html:
    html = html.replace("</style>", new_support_css + "\n</style>", 1)

# Ajouter le JS du scroll expansible avant </body>
SCROLL_JS = '''
<script>
(function () {
  var btn = document.getElementById("support-mini");
  if (!btn) return;
  function update() {
    var y = window.scrollY || window.pageYOffset || 0;
    if (y > 120) btn.classList.add("expanded");
    else btn.classList.remove("expanded");
  }
  window.addEventListener("scroll", update, { passive: true });
  update();
})();
</script>
'''
if 'id="support-mini"' in html and "classList.add(\"expanded\")" not in html:
    html = html.replace("</body>", SCROLL_JS + "\n</body>", 1)
    print("[OK] catalogue -> JS du scroll ajoute")

CAT.write_text(html, encoding="utf-8")

print()
print("=" * 60)
print("SIMPLIFICATION LIVREE")
print("=" * 60)
print()
print("Page /professionnel/demande :")
print("  - 2 options seulement :")
print("    1. Depuis le catalogue    (ouvre /professionnel/catalogue)")
print("    2. Envoyer ma liste WhatsApp (ouvre WhatsApp +22871039904)")
print("  - Bouton 'Ouvrir le catalogue complet' supprime")
print()
print("Bouton WhatsApp dans le catalogue :")
print("  - Au chargement : cercle vert 52x52")
print("  - Au scroll > 120px : s'etend en pastille 'Support pharmacie'")
print("  - Retour en haut : reprend sa forme cercle")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R dans le navigateur")
print("  (pas besoin de redemarrer Uvicorn)")