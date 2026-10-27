"""
v4_catalogue_bleu_navbar.py
- Retour a la palette bleue d'origine
- Retire le badge flottant 'Ma demande'
- Ajoute le compteur dans le bouton central '+' de la navbar
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
CAT = STATIC / "professional_catalogue.html"
JS = STATIC / "professional_catalogue.js"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_cat_bleu_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(CAT, backup / "professional_catalogue.html")
shutil.copy2(JS, backup / "professional_catalogue.js")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. HTML : retour palette bleue
# ============================================================
html = CAT.read_text(encoding="utf-8")

html = html.replace("--blue:#0f9d76;", "--blue:#1a4a7f;")
html = html.replace("--blue-dark:#0a7a5a;", "--blue-dark:#123258;")
html = html.replace("--blue-soft:#e8f7f1;", "--blue-soft:#eaf1f9;")
html = html.replace("linear-gradient(135deg,#0f9d76,#37c79c)", "linear-gradient(135deg,var(--blue),#2a6ba8)")
# Re-bleu les elements verts utilises par erreur
html = html.replace("background:var(--green);", "background:var(--blue);")
print("[OK] Palette remise en bleu")

# ============================================================
# 2. HTML : retirer le bouton flottant
# ============================================================
old_float = '''<button class="cat-float empty" id="float" type="button">
  <span class="cat-float-icon">&#128221;</span>
  Ma demande
  <span class="cat-float-count" id="float-count">0</span>
</button>
'''
if old_float in html:
    html = html.replace(old_float, "")
    print("[OK] Badge flottant retire")
else:
    # Fallback : regex souple
    import re
    html = re.sub(r'<button class="cat-float[^"]*"[^>]*id="float"[^>]*>.*?</button>\s*',
                  '', html, flags=re.DOTALL)
    print("[i] Badge flottant retire (fallback)")

# ============================================================
# 3. HTML : ajouter compteur dans le bouton central '+' de la navbar
# ============================================================
old_central = '''  <a href="/professionnel" class="central">
    <span>+</span><span class="lbl">Demande</span>
  </a>'''
new_central = '''  <a href="/professionnel" class="central" id="nav-central">
    <span id="nav-central-plus">+</span>
    <span class="lbl">Demande</span>
    <span class="nav-count hidden" id="nav-count">0</span>
  </a>'''
if old_central in html:
    html = html.replace(old_central, new_central, 1)
    print("[OK] Compteur ajoute dans le bouton central")
else:
    print("[!] Pattern du bouton central introuvable")

# ============================================================
# 4. HTML : styles pour le compteur dans la navbar
# ============================================================
NAV_COUNT_CSS = '''
/* ---- Compteur dans le bouton central de la navbar ---- */
.pro-navbar .central{position:relative}
.pro-navbar .central .nav-count{
  position:absolute;top:-4px;right:-4px;
  min-width:22px;height:22px;padding:0 6px;
  background:#fff;color:var(--green-dark);
  border:2px solid var(--green);
  border-radius:999px;font-size:11px;font-weight:900;
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 2px 6px rgba(15,157,118,.35);
}
.pro-navbar .central .nav-count.hidden{display:none}

/* Le badge flottant disparait -> on peut reduire le padding bas du body */
body{padding-bottom:92px !important;}
'''
# Retirer l'ancien ajustement float si present
html = html.replace(".cat-float{bottom:92px !important;}", "")
html = html.replace("</style>", NAV_COUNT_CSS + "</style>")
print("[OK] Styles du compteur ajoutes")

CAT.write_text(html, encoding="utf-8")

# ============================================================
# 5. JS : remplacer updateFloat par updateNavCount
# ============================================================
js = JS.read_text(encoding="utf-8")

# Remplacer la fonction updateFloat
old_update = '''  function updateFloat() {
    var f = document.getElementById("float");
    var c = document.getElementById("float-count");
    if (!f || !c) return;
    c.textContent = state.draftItemsCount;
    if (state.draftItemsCount > 0) f.classList.remove("empty");
    else f.classList.add("empty");
  }'''
new_update = '''  function updateNavCount() {
    var c = document.getElementById("nav-count");
    if (!c) return;
    var n = state.draftItemsCount;
    if (n > 0) {
      c.textContent = n > 99 ? "99+" : String(n);
      c.classList.remove("hidden");
    } else {
      c.classList.add("hidden");
    }
  }'''
if old_update in js:
    js = js.replace(old_update, new_update, 1)
    print("[OK] updateFloat -> updateNavCount")
else:
    print("[!] updateFloat introuvable")

# Remplacer les appels a updateFloat()
js = js.replace("updateFloat();", "updateNavCount();")
print("[OK] Appels renommes")

# Retirer le handler du clic sur le float
old_click = '''    // Float -> retour à la demande
    document.getElementById("float").addEventListener("click", function () {
      window.location.href = "/professionnel";
    });'''
if old_click in js:
    js = js.replace(old_click, "")
    print("[OK] Handler du float retire")
else:
    print("[i] Handler float deja retire")

JS.write_text(js, encoding="utf-8")

print()
print("=" * 60)
print("CATALOGUE : BLEU + COMPTEUR DANS NAVBAR")
print("=" * 60)
print()
print("Changements :")
print("  - Palette bleue restauree")
print("  - Badge flottant 'Ma demande' supprime")
print("  - Compteur affiche sur le bouton central '+' de la navbar")
print("  - Si 0 item -> pas de pastille ; sinon pastille verte avec le nombre")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur Edge/iPhone")