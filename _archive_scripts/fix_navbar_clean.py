"""
fix_navbar_clean.py
1. Restaure les fichiers depuis les .bak
2. Reapplique le guide (etapes 1, 3, 4) proprement
3. Reapplique la navbar central avec label "Demande" (HTML + CSS correct)
"""
from pathlib import Path
import re
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
JS = STATIC / "professional_dashboard.js"
HTML = STATIC / "professional.html"

# ============================================================
# 1. Restaurer depuis les backups si disponibles
# ============================================================
for p in (JS, HTML):
    bak = p.with_suffix(p.suffix + ".bak")
    if bak.exists():
        shutil.copy2(bak, p)
        print(f"[OK] Restaure {p.name} depuis {bak.name}")
    else:
        print(f"[!] {bak.name} introuvable - on continue")

# ============================================================
# 2. Guide : etape 1 reformulee + Mixx/Flooz + sans "par voiture"
# ============================================================
src = JS.read_text(encoding="utf-8")

# Etape 1
pattern1 = re.compile(
    r"Constituez votre demande depuis le\s+<strong>catalogue</strong>\s+"
    r"ou\s+via\s+<strong>WhatsApp</strong>\.",
    re.DOTALL,
)
new1 = ("Ouvrez l'onglet <strong>+ Demande</strong> : choisissez "
        "<strong>Catalogue</strong> (ajoutez vos produits un par un) "
        "ou <strong>WhatsApp</strong> (envoyez votre liste par texte, photo ou PDF).")
n1 = len(pattern1.findall(src))
src = pattern1.sub(lambda m: new1, src)
print(f"[OK] Etape 1 guide : {n1} remplacement(s)")

# Etape 3
if "Reglez par Mobile Money et envoyez la preuve." in src:
    src = src.replace(
        "Reglez par Mobile Money et envoyez la preuve.",
        "Reglez par <strong>Mixx</strong> ou <strong>Flooz</strong>, puis envoyez la preuve de paiement.",
        1,
    )
    print("[OK] Etape 3 : Mixx/Flooz")

# Etape 4
if "Recevez votre commande par voiture (livraison B2B)." in src:
    src = src.replace(
        "Recevez votre commande par voiture (livraison B2B).",
        "Recevez votre commande apres validation de la pharmacie.",
        1,
    )
    print("[OK] Etape 4 : 'par voiture' retire")

JS.write_text(src, encoding="utf-8")

# ============================================================
# 3. Navbar central : remplacer le bloc entier proprement
# ============================================================
html = HTML.read_text(encoding="utf-8")

# Chercher toutes les formes possibles du lien central
# Forme cible : lien vers /professionnel/demande avec class contenant "central"
old_block_re = re.compile(
    r'<a\s+href="/professionnel/demande"[^>]*class="[^"]*central[^"]*"[^>]*>.*?</a>',
    re.DOTALL,
)

new_block = (
    '<a href="/professionnel/demande" class="central" id="nav-central">\n'
    '  <span class="ico">+</span>\n'
    '  <span class="lbl">Demande</span>\n'
    '</a>'
)

m = old_block_re.search(html)
if m:
    html = old_block_re.sub(lambda x: new_block, html, count=1)
    print("[OK] Navbar central remplace")
else:
    print("[!] Bloc central introuvable - affichage du contexte pour debug")
    idx = html.find("/professionnel/demande")
    if idx > 0:
        print(html[max(0, idx - 100):idx + 250])

# ============================================================
# 4. CSS navbar : s'assurer que le label est bien stylise
# ============================================================
CSS_ADD = '''
/* --- Navbar central : icone + label --- */
.pro-navbar .central{
  margin-top:-22px;
  background:var(--blue);
  color:#fff;
  border-radius:50%;
  width:64px;
  height:64px;
  justify-self:center;
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
  box-shadow:0 6px 20px rgba(26,74,127,.35);
  border:4px solid var(--bg);
  text-decoration:none;
  line-height:1;
}
.pro-navbar .central .ico{
  font-size:22px;
  font-weight:800;
  line-height:1;
  margin-bottom:1px;
}
.pro-navbar .central .lbl{
  font-size:9px;
  font-weight:700;
  letter-spacing:.02em;
  margin-top:1px;
  line-height:1;
}
.pro-navbar .central .nav-count{
  position:absolute;
  top:-4px;
  right:-4px;
  min-width:20px;
  height:20px;
  padding:0 5px;
  background:#fff;
  color:var(--blue-dark);
  border:2px solid var(--blue);
  border-radius:999px;
  font-size:10px;
  font-weight:900;
  display:flex;
  align-items:center;
  justify-content:center;
}
.pro-navbar .central .nav-count.hidden{display:none}
'''

# Injecter avant </style> (uniquement si pas deja present)
if "/* --- Navbar central : icone + label --- */" not in html:
    html = html.replace("</style>", CSS_ADD + "\n</style>", 1)
    print("[OK] CSS navbar central ajoute")
else:
    print("[i] CSS navbar central deja present")

HTML.write_text(html, encoding="utf-8")

# ============================================================
# 5. Verification
# ============================================================
print()
print("=" * 55)
print("VERIFICATION")
print("=" * 55)
check_html = HTML.read_text(encoding="utf-8")
check_js = JS.read_text(encoding="utf-8")

print("HTML :")
print("  Navbar central present :", 'class="central"' in check_html)
print("  Label 'Demande' present :", '<span class="lbl">Demande</span>' in check_html)
print("  CSS .central .lbl      :", '.pro-navbar .central .lbl' in check_html)
print()
print("JS :")
print("  Nouvelle etape 1 :", "Ouvrez l'onglet <strong>+ Demande</strong>" in check_js)
print("  'Mixx' present   :", "Mixx" in check_js)
print("  'Flooz' present  :", "Flooz" in check_js)
print("  'par voiture'    :", "par voiture" in check_js, "(doit etre False)")
print()
print("=" * 55)
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur /professionnel (ou navigation privee iPhone)")
print("  Si la page est blanche -> F12 Console, colle-moi les erreurs")
print("=" * 55)