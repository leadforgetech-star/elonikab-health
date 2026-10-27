"""
fix_final_v2.py
1. Corrige l'apostrophe dans professional_dashboard.js
2. Reconstruit le bloc central de la navbar proprement
3. S'assure que le CSS .ico et .lbl est present
"""
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
JS = STATIC / "professional_dashboard.js"
HTML = STATIC / "professional.html"

# ============================================================
# 1. JS : fix apostrophe dans "Ouvrez l'onglet"
# ============================================================
src = JS.read_text(encoding="utf-8")

# Remplacer par une apostrophe typographique (U+2019) qui ne casse pas le JS
avant = src.count("Ouvrez l'onglet")
src = src.replace("Ouvrez l'onglet", "Ouvrez l\u2019onglet")
apres = src.count("Ouvrez l\u2019onglet")
print(f"[OK] JS : apostrophe corrigee ({avant} -> {apres})")

# Chercher d'autres apostrophes problematiques dans les nouvelles phrases
# 'd'aide', 'd'Elokinab', etc. dans les strings JS
autres = [
    ("l'activite", "l\u2019activite"),
    ("d'activite", "d\u2019activite"),
    ("l'etape", "l\u2019etape"),
    ("d'etape", "d\u2019etape"),
    ("l'utilisateur", "l\u2019utilisateur"),
    ("d'aide", "d\u2019aide"),
    ("l'aide", "l\u2019aide"),
    ("l'accueil", "l\u2019accueil"),
    ("d'accueil", "d\u2019accueil"),
    ("l'etablissement", "l\u2019etablissement"),
    ("d'etablissement", "d\u2019etablissement"),
    ("l'application", "l\u2019application"),
    ("l'image", "l\u2019image"),
]
for old, new in autres:
    if old in src:
        n = src.count(old)
        src = src.replace(old, new)
        print(f"[OK] JS : '{old}' remplace ({n}x)")

JS.write_text(src, encoding="utf-8")

# ============================================================
# 2. HTML : reconstruire le bloc central proprement
# ============================================================
html = HTML.read_text(encoding="utf-8")

# Chercher TOUT lien qui pointe vers /professionnel/demande
pattern = re.compile(
    r'<a\s+[^>]*href="/professionnel/demande"[^>]*>.*?</a>',
    re.DOTALL,
)
matches = pattern.findall(html)
print(f"[i] HTML : {len(matches)} lien(s) vers /professionnel/demande")

new_link = (
    '<a href="/professionnel/demande" class="central" id="nav-central">'
    '<span class="ico">+</span>'
    '<span class="lbl">Demande</span>'
    '</a>'
)

if matches:
    html = pattern.sub(lambda m: new_link, html, count=1)
    print("[OK] HTML : bloc central reconstruit")
else:
    print("[!] HTML : aucun lien /professionnel/demande trouve")
    # Debug : chercher "central"
    idx = html.find("central")
    if idx > 0:
        print("Contexte 'central' :")
        print(html[max(0, idx - 150):idx + 200])

# ============================================================
# 3. CSS : s'assurer que .ico et .lbl sont stylises correctement
# ============================================================
if ".pro-navbar .central .ico" not in html:
    CSS_ADD = '''
/* --- Navbar central : icone + label --- */
.pro-navbar .central .ico{
  font-size:22px;
  font-weight:800;
  line-height:1;
  display:block;
}
.pro-navbar .central .lbl{
  font-size:9px;
  font-weight:700;
  line-height:1;
  margin-top:2px;
  letter-spacing:.02em;
  display:block;
}
'''
    if "</style>" in html:
        html = html.replace("</style>", CSS_ADD + "</style>", 1)
        print("[OK] CSS .ico + .lbl ajoute")
    else:
        print("[!] </style> introuvable")
else:
    print("[i] CSS deja present")

HTML.write_text(html, encoding="utf-8")

# ============================================================
# 4. Verification finale
# ============================================================
print()
print("=" * 55)
print("VERIFICATION")
print("=" * 55)

check_js = JS.read_text(encoding="utf-8")
check_html = HTML.read_text(encoding="utf-8")

print("JS :")
print("  'l'onglet' (mauvais) encore present :", "l'onglet" in check_js, "(doit etre False)")
print("  'l\u2019onglet' (bon) present         :", "l\u2019onglet" in check_js)
print()
print("HTML :")
print("  Bloc central :", 'class="central"' in check_html)
print("  Label Demande :", '<span class="lbl">Demande</span>' in check_html)
print("  CSS .ico :", '.pro-navbar .central .ico' in check_html)
print("  CSS .lbl :", '.pro-navbar .central .lbl' in check_html)
print()
print("=" * 55)
print("PROCHAINE ETAPE :")
print("  1. Ctrl+Shift+Suppr -> vider le cache Edge")
print("  2. Ctrl+Shift+R sur /professionnel")
print("  3. F12 -> Console : plus d'erreur SyntaxError ?")
print("=" * 55)