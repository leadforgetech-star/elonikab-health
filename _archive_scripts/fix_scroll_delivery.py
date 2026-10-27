"""
fix_scroll_delivery.py
Quand on choisit Livraison, scroll auto vers les champs de livraison (adresse + GPS).
Et fait clignoter le bouton GPS pour attirer l'attention.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
CART_JS = BASE / "static" / "cart.js"
MOBILE = BASE / "static" / "mobile.css"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_scroll_delivery_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(CART_JS, backup / "cart.js")
shutil.copy2(MOBILE, backup / "mobile.css")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. cart.js : scroll auto + animation quand Livraison est choisie
# ============================================================
js = CART_JS.read_text(encoding="utf-8")

old = '''  function selectMode(mode) {
    state.mode = mode;
    var modes = document.querySelectorAll(".mode-btn");
    Array.prototype.forEach.call(modes, function (b) {
      b.classList.toggle("active", b.getAttribute("data-mode") === mode);
    });
    var fields = $("co-delivery-fields");
    if (mode === "livraison") fields.classList.remove("hidden");
    else fields.classList.add("hidden");
    updateTotals();
  }'''

new = '''  function selectMode(mode) {
    state.mode = mode;
    var modes = document.querySelectorAll(".mode-btn");
    Array.prototype.forEach.call(modes, function (b) {
      b.classList.toggle("active", b.getAttribute("data-mode") === mode);
    });
    var fields = $("co-delivery-fields");
    if (mode === "livraison") {
      fields.classList.remove("hidden");
      // Scroll auto vers les champs de livraison
      setTimeout(function () {
        if (fields.scrollIntoView) {
          fields.scrollIntoView({ behavior: "smooth", block: "center" });
        }
        // Faire clignoter le bouton GPS pour attirer l'attention
        var gpsBtn = $("co-gps");
        if (gpsBtn) {
          gpsBtn.classList.add("attention-pulse");
          setTimeout(function () {
            gpsBtn.classList.remove("attention-pulse");
          }, 4000);
        }
        // Focus sur l'adresse si vide
        var addr = $("co-address");
        if (addr && !addr.value) {
          // On NE fait PAS focus() pour eviter que le clavier s'ouvre
          // juste un highlight visuel
          addr.classList.add("attention-highlight");
          setTimeout(function () {
            addr.classList.remove("attention-highlight");
          }, 4000);
        }
      }, 120);
    } else {
      fields.classList.add("hidden");
    }
    updateTotals();
  }'''

if old in js and "attention-pulse" not in js:
    js = js.replace(old, new, 1)
    CART_JS.write_text(js, encoding="utf-8")
    print("[OK] cart.js -> scroll auto + animation")
elif "attention-pulse" in js:
    print("[i] cart.js deja patche")
else:
    print("[!] anchor selectMode introuvable")

# ============================================================
# 2. mobile.css : animation d'attention
# ============================================================
css = MOBILE.read_text(encoding="utf-8")

if "attention-pulse" not in css:
    css += '''

/* --- Animation d'attention pour le GPS --- */
@keyframes attentionPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(15,157,118,.55); }
  50%      { box-shadow: 0 0 0 12px rgba(15,157,118,0); }
}
.attention-pulse{
  animation: attentionPulse 1.4s ease-out 3;
  background: #0f9d76 !important;
  color: #fff !important;
  font-weight: 800 !important;
}

@keyframes attentionHighlight {
  0%, 100% { border-color: #ddece6; background: #fff; }
  50%      { border-color: #0f9d76; background: #f0faf6; }
}
.attention-highlight{
  animation: attentionHighlight 1s ease-in-out 4;
}
'''
    MOBILE.write_text(css, encoding="utf-8")
    print("[OK] mobile.css -> animations")
else:
    print("[i] mobile.css deja patche")

print()
print("=" * 60)
print("FIX SCROLL LIVRAISON APPLIQUE")
print("=" * 60)
print()
print("Effet :")
print("  - Clic sur Livraison -> scroll auto vers adresse + GPS")
print("  - Le bouton GPS pulse en vert (attire l'oeil)")
print("  - Le champ adresse clignote doucement")
print("  - Tout revient a la normale apres 4 secondes")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur l'iPhone (ou navigation privee)")