"""
v4_catalogue_vert.py
- Remplace la palette bleue par la palette verte Elokinab
- Ajoute la navbar basse (Accueil | Catalogue | + Demande | Commandes | Établissement)
- Marque "Catalogue" comme actif
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
CAT = STATIC / "professional_catalogue.html"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_cat_vert_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(CAT, backup / "professional_catalogue.html")
print("[OK] Backup ->", backup.name)

html = CAT.read_text(encoding="utf-8")

# 1. Palette verte
html = html.replace("--blue:#1a4a7f;", "--blue:#0f9d76;")
html = html.replace("--blue-dark:#123258;", "--blue-dark:#0a7a5a;")
html = html.replace("--blue-soft:#eaf1f9;", "--blue-soft:#e8f7f1;")
html = html.replace("linear-gradient(135deg,var(--blue),#2a6ba8)", "linear-gradient(135deg,#0f9d76,#37c79c)")
print("[OK] Palette remplacee (bleu -> vert)")

# 2. Padding-bottom du body pour faire de la place a la navbar
html = html.replace(
    "padding-bottom:92px;",
    "padding-bottom:150px;"
)
print("[OK] Padding bas ajuste")

# 3. Ajouter les styles navbar basse (avant </style>)
NAVBAR_CSS = '''
/* ---- Navbar basse mobile ---- */
.pro-navbar{
  position:fixed;bottom:0;left:0;right:0;z-index:200;
  background:#fff;border-top:1px solid var(--line);
  display:grid;grid-template-columns:1fr 1fr 76px 1fr 1fr;
  padding:6px 6px calc(6px + env(safe-area-inset-bottom)) 6px;
  box-shadow:0 -2px 12px rgba(15,38,32,.06);
}
.pro-navbar a{
  padding:8px 4px;text-align:center;font-size:10px;font-weight:700;
  color:var(--muted);display:flex;flex-direction:column;align-items:center;gap:3px;
  text-decoration:none;
}
.pro-navbar a .ico{font-size:18px;line-height:1}
.pro-navbar a.active{color:var(--green-dark)}
.pro-navbar .central{
  margin-top:-22px;background:var(--green);color:#fff;border-radius:50%;
  width:64px;height:64px;justify-self:center;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  font-size:22px;font-weight:800;box-shadow:0 6px 20px rgba(15,157,118,.4);
  border:4px solid var(--bg);
}
.pro-navbar .central .lbl{font-size:9px;font-weight:700;margin-top:-2px}

/* Re-ajuster le badge flottant au-dessus de la navbar */
.cat-float{bottom:92px !important;}
'''
html = html.replace("</style>", NAVBAR_CSS + "</style>")
print("[OK] Styles navbar ajoutes")

# 4. Ajouter la navbar avant </body>
NAVBAR_HTML = '''
<!-- NAVBAR BASSE -->
<nav class="pro-navbar">
  <a href="/professionnel">
    <span class="ico">&#127968;</span> Accueil
  </a>
  <a href="/professionnel/catalogue" class="active">
    <span class="ico">&#128722;</span> Catalogue
  </a>
  <a href="/professionnel" class="central">
    <span>+</span><span class="lbl">Demande</span>
  </a>
  <a href="/professionnel/commandes">
    <span class="ico">&#128230;</span> Commandes
  </a>
  <a href="/professionnel" id="nav-etab-cat">
    <span class="ico">&#127970;</span> Établ.
  </a>
</nav>
'''
html = html.replace("</body>", NAVBAR_HTML + "\n</body>")
print("[OK] Navbar ajoutee")

CAT.write_text(html, encoding="utf-8")

print()
print("=" * 60)
print("CATALOGUE ADAPTE : COULEURS VERTES + NAVBAR BASSE")
print("=" * 60)
print()
print("Effet :")
print("  - Palette verte Elokinab (bleu -> vert partout)")
print("  - Navbar basse : Accueil | Catalogue | + Demande | Commandes | Etabl.")
print("  - Onglet 'Catalogue' marque actif")
print("  - Badge flottant 'Ma demande' remonte au-dessus de la navbar")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur Edge/iPhone")
print("  (pas besoin de redemarrer Uvicorn)")