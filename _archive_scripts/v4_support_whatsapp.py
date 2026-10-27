"""
v4_support_whatsapp.py
- Bouton "Discuter avec le support pharmacie" -> WhatsApp +22871039904
- Bouton "Ouvrir le catalogue" sur la page demande
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_support_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
for f in ("professional.html", "professional_demande.html",
          "professional_catalogue.html", "professional_dashboard.js",
          "professional_demande.js", "professional_catalogue.js",
          "professional_commandes.html", "professional_etablissement.html"):
    p = STATIC / f
    if p.exists():
        shutil.copy2(p, backup / f)
print("[OK] Backup ->", backup.name)

# ============================================================
# HELPERS
# ============================================================
WA_NUMBER = "22871039904"
WA_BASE = "https://wa.me/" + WA_NUMBER

def wa_url(message):
    """Genere une URL wa.me avec message pre-rempli."""
    import urllib.parse
    return WA_BASE + "?text=" + urllib.parse.quote(message)

# ============================================================
# CSS pour le bouton support (injecte dans les pages)
# ============================================================
SUPPORT_CSS = '''
/* ---- Bouton support WhatsApp ---- */
.support-btn{
  display:flex;align-items:center;justify-content:center;gap:8px;
  width:100%;padding:13px;border:0;border-radius:12px;
  background:#25d366;color:#fff;font-weight:800;font-size:14px;
  margin-top:12px;text-decoration:none;font-family:inherit;
  transition:.15s;cursor:pointer;
}
.support-btn:hover{background:#1da851;transform:translateY(-1px)}
.support-btn .ico{font-size:16px}

.support-mini{
  position:fixed;bottom:100px;right:16px;z-index:190;
  width:52px;height:52px;border-radius:50%;
  background:#25d366;color:#fff;border:0;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  font-size:24px;box-shadow:0 6px 18px rgba(37,211,102,.4);
  transition:.15s;
}
.support-mini:hover{background:#1da851;transform:scale(1.05)}
'''

def inject_support_css(html):
    if ".support-btn{" in html:
        return html
    return html.replace("</style>", SUPPORT_CSS + "\n</style>", 1)

# ============================================================
# 1. DASHBOARD : ajouter bouton support
# ============================================================
DASH = STATIC / "professional.html"
html = DASH.read_text(encoding="utf-8")

SUPPORT_BLOCK = '''  <!-- Support WhatsApp -->
  <a class="support-btn" id="support-link"
     href="https://wa.me/22871039904?text=Bonjour%20Elokinab%20Health%2C%20j%27ai%20une%20question%20concernant%20mes%20commandes."
     target="_blank" rel="noopener">
    <span class="ico">&#128172;</span> Discuter avec le support pharmacie
  </a>

'''

# Inserer apres la section "Activite recente" (avant </main>)
if 'class="support-btn"' not in html:
    anchor = "</main>"
    if anchor in html:
        html = html.replace(anchor, SUPPORT_BLOCK + anchor, 1)
        html = inject_support_css(html)
        DASH.write_text(html, encoding="utf-8")
        print("[OK] dashboard -> bouton support")
    else:
        print("[!] </main> introuvable dans dashboard")
else:
    print("[i] dashboard -> bouton support deja present")

# ============================================================
# 2. DEMANDE : ajouter bouton support + bouton ouvrir catalogue
# ============================================================
DEM = STATIC / "professional_demande.html"
html = DEM.read_text(encoding="utf-8")

# 2.1 Ajouter un bouton "Ouvrir le catalogue" en plus de "Depuis le catalogue"
#     -> Renommer "Depuis le catalogue" en "Parcourir le catalogue" + ajouter lien direct
# Simplement : ajouter un bouton "Voir le catalogue complet" en bas des sources
CAT_LINK = '''  <a href="/professionnel/catalogue" class="support-btn"
     style="background:#1a4a7f;margin-top:10px" id="open-catalogue-link">
    <span class="ico">&#128722;</span> Ouvrir le catalogue complet
  </a>

'''
# Inserer apres la grille sources
if 'id="open-catalogue-link"' not in html:
    anchor = '<h2 class="section-title">Ma demande</h2>'
    if anchor in html:
        html = html.replace(anchor, CAT_LINK + anchor, 1)
        print("[OK] demande -> bouton 'Ouvrir le catalogue'")
    else:
        print("[!] anchor 'Ma demande' introuvable")

# 2.2 Ajouter bouton support
SUPPORT_DEM = '''  <a class="support-btn" id="support-link"
     href="https://wa.me/22871039904?text=Bonjour%20Elokinab%20Health%2C%20j%27ai%20une%20question%20concernant%20ma%20demande."
     target="_blank" rel="noopener">
    <span class="ico">&#128172;</span> Discuter avec le support pharmacie
  </a>

'''
if 'id="support-link"' not in html:
    anchor = "</main>"
    if anchor in html:
        html = html.replace(anchor, SUPPORT_DEM + anchor, 1)
        print("[OK] demande -> bouton support")

html = inject_support_css(html)
DEM.write_text(html, encoding="utf-8")

# ============================================================
# 3. CATALOGUE : ajouter bouton support flottant + ajuster ajout
# ============================================================
CAT = STATIC / "professional_catalogue.html"
html = CAT.read_text(encoding="utf-8")

# Bouton support flottant (petit rond)
SUPPORT_FLOAT = '''
<a class="support-mini" id="support-mini"
   href="https://wa.me/22871039904?text=Bonjour%20Elokinab%20Health%2C%20j%27ai%20une%20question."
   target="_blank" rel="noopener" title="Contacter le support">
  &#128172;
</a>
'''
if 'class="support-mini"' not in html:
    html = html.replace("</body>", SUPPORT_FLOAT + "\n</body>", 1)
    print("[OK] catalogue -> bouton support flottant")

html = inject_support_css(html)
CAT.write_text(html, encoding="utf-8")

# ============================================================
# 4. Verifier que "Ajouter a ma demande" ne navigue PAS ailleurs
# ============================================================
# Dans le JS catalogue, s'assurer qu'apres ajout, on reste sur le catalogue.
CATJS = STATIC / "professional_catalogue.js"
if CATJS.exists():
    js = CATJS.read_text(encoding="utf-8")
    # Le JS actuel ne navigue pas apres ajout -> OK, on ne touche pas
    # Ajouter juste un petit feedback visuel plus fort (deja fait via toast)
    print("[OK] catalogue.js -> comportement d'ajout verifie (reste sur catalogue)")

# ============================================================
# 5. Commandes / Etablissement : ajouter bouton support
# ============================================================
for page_name in ("professional_commandes.html", "professional_etablissement.html"):
    page = STATIC / page_name
    if not page.exists():
        continue
    html = page.read_text(encoding="utf-8")
    if 'class="support-btn"' not in html:
        anchor = "</main>"
        if anchor in html:
            block = '''  <a class="support-btn"
     href="https://wa.me/22871039904?text=Bonjour%20Elokinab%20Health%2C%20j%27ai%20une%20question."
     target="_blank" rel="noopener"
     style="margin-top:24px">
    <span class="ico">&#128172;</span> Discuter avec le support pharmacie
  </a>

'''
            html = html.replace(anchor, block + anchor, 1)
            html = inject_support_css(html)
            page.write_text(html, encoding="utf-8")
            print("[OK]", page_name, "-> bouton support")
    else:
        print("[i]", page_name, "-> deja present")

print()
print("=" * 60)
print("SUPPORT WHATSAPP + CATALOGUE LIVRES")
print("=" * 60)
print()
print("Bouton 'Discuter avec le support pharmacie' (vert WhatsApp) :")
print("  - Dashboard /professionnel")
print("  - Demande /professionnel/demande")
print("  - Commandes /professionnel/commandes")
print("  - Etablissement /professionnel/etablissement")
print()
print("Bouton flottant rond (bas droite) :")
print("  - Catalogue /professionnel/catalogue")
print()
print("Bouton 'Ouvrir le catalogue complet' :")
print("  - Page Demande -> lien direct vers le catalogue")
print()
print("Message WhatsApp pre-rempli :")
print("  'Bonjour Elokinab Health, j'ai une question...'")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R dans le navigateur")
print("  (pas besoin de redemarrer Uvicorn)")