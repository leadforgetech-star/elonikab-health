"""
fix_navbar_central.py
Reecrit integralement le style du bouton central de la navbar.
"""
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent
HTML = BASE / "static" / "professional.html"

html = HTML.read_text(encoding="utf-8")

# ============================================================
# 1. Remplacer tout le CSS lie au central (ancien + nouveau)
# ============================================================

# Retirer toutes les anciennes regles .pro-navbar .central
patterns_to_remove = [
    # Ancien bloc complet
    re.compile(r"/\* --- Navbar central : icone \+ label --- \*/.*?(?=\n/\*|\n</style>)", re.DOTALL),
    # Ancien .central
    re.compile(r"\.pro-navbar \.central\s*\{[^}]*\}", re.DOTALL),
    re.compile(r"\.pro-navbar \.central \.ico\s*\{[^}]*\}", re.DOTALL),
    re.compile(r"\.pro-navbar \.central \.lbl\s*\{[^}]*\}", re.DOTALL),
    re.compile(r"\.pro-navbar \.central \.nav-count\s*\{[^}]*\}", re.DOTALL),
    re.compile(r"\.pro-navbar \.central\.active\s*\{[^}]*\}", re.DOTALL),
]
for pat in patterns_to_remove:
    html = pat.sub("", html)
print("[OK] Anciens styles .central retires")

# Nouveau CSS propre — tout en un
NEW_CSS = '''
/* ============================================================
   NAVBAR CENTRAL — bouton + / Demande
   ============================================================ */
.pro-navbar .central{
  margin-top:-22px !important;
  background:var(--blue) !important;
  color:#fff !important;
  border-radius:50% !important;
  width:68px !important;
  height:68px !important;
  justify-self:center !important;
  display:flex !important;
  flex-direction:column !important;
  align-items:center !important;
  justify-content:center !important;
  box-shadow:0 6px 20px rgba(26,74,127,.35) !important;
  border:4px solid var(--bg) !important;
  text-decoration:none !important;
  line-height:1 !important;
  position:relative !important;
  box-sizing:border-box !important;
  padding:0 !important;
  gap:0 !important;
}
.pro-navbar .central:active{
  transform:scale(.96);
}
.pro-navbar .central .ico{
  font-size:26px !important;
  font-weight:900 !important;
  line-height:1 !important;
  display:block !important;
  margin:0 !important;
  padding:0 !important;
  height:26px !important;
  color:#fff !important;
}
.pro-navbar .central .lbl{
  font-size:9px !important;
  font-weight:700 !important;
  line-height:1 !important;
  display:block !important;
  margin:3px 0 0 0 !important;
  padding:0 !important;
  color:#fff !important;
  letter-spacing:.02em !important;
  text-transform:none !important;
}
.pro-navbar .central .nav-count{
  position:absolute !important;
  top:-4px !important;
  right:-4px !important;
  min-width:20px !important;
  height:20px !important;
  padding:0 5px !important;
  background:#fff !important;
  color:var(--blue-dark) !important;
  border:2px solid var(--blue) !important;
  border-radius:999px !important;
  font-size:10px !important;
  font-weight:900 !important;
  display:flex !important;
  align-items:center !important;
  justify-content:center !important;
  box-sizing:border-box !important;
}
.pro-navbar .central .nav-count.hidden{display:none !important}
.pro-navbar .central.active{background:var(--blue-dark) !important}
/* ============================================================ */

'''

if "</style>" in html:
    html = html.replace("</style>", NEW_CSS + "</style>", 1)
    print("[OK] Nouveau CSS .central injecte")

# ============================================================
# 2. Reecrire le bloc <a> central proprement
# ============================================================
pattern_a = re.compile(
    r'<a\s+href="/professionnel/demande"[^>]*>.*?</a>',
    re.DOTALL,
)

new_a = (
    '<a href="/professionnel/demande" class="central" id="nav-central" '
    'aria-label="Nouvelle demande">'
    '<span class="ico">+</span>'
    '<span class="lbl">Demande</span>'
    '</a>'
)

if pattern_a.search(html):
    html = pattern_a.sub(lambda m: new_a, html, count=1)
    print("[OK] Bloc <a> central reecrit")
else:
    print("[!] Bloc <a> /professionnel/demande introuvable")

HTML.write_text(html, encoding="utf-8")

# ============================================================
# 3. Verification
# ============================================================
check = HTML.read_text(encoding="utf-8")
print()
print("=" * 55)
print("VERIFICATION")
print("=" * 55)
print("  CSS .central avec flex-direction:column :",
      "flex-direction:column !important" in check)
print("  CSS .central .ico                      :",
      ".pro-navbar .central .ico" in check)
print("  CSS .central .lbl                      :",
      ".pro-navbar .central .lbl" in check)
print("  HTML <a class=\"central\">               :",
      'class="central"' in check)
print("  HTML <span class=\"ico\">+</span>         :",
      '<span class="ico">+</span>' in check)
print("  HTML <span class=\"lbl\">Demande</span>   :",
      '<span class="lbl">Demande</span>' in check)
print()
print("=" * 55)
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur /professionnel")
print("=" * 55)