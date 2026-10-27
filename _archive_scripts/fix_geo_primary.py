from pathlib import Path
import re
import shutil

BASE = Path(__file__).resolve().parent
INDEX = BASE / "static" / "index.html"
APPJS = BASE / "static" / "app.js"
CSS = BASE / "static" / "style.css"

# ============================================================
# 1) index.html : reordonner le bloc address-row
# ============================================================
html = INDEX.read_text(encoding="utf-8")
shutil.copy(INDEX, INDEX.with_suffix(".html.bak"))
print("[OK] sauvegarde index.html.bak")

# Bloc cible actuel (apres le fix precedent)
pattern = re.compile(
    r'<div class="form-row hidden" id="address-row">.*?</div>\s*(?=<div id="form-error"|<button type="submit")',
    re.DOTALL,
)
m = pattern.search(html)
if not m:
    print("[!] bloc address-row introuvable")
    raise SystemExit(1)

new_block = '''<div class="form-row hidden" id="address-row">
  <label>Localisation pour la livraison</label>

  <div class="geo-block">
    <button type="button" class="btn btn-primary geo-btn" id="geo-btn">
      <span class="geo-icon">📍</span> Utiliser ma localisation actuelle
    </button>
    <div id="geo-status" class="geo-status hidden"></div>
  </div>

  <button type="button" class="geo-toggle-address" id="geo-toggle-address">
    Vous ne pouvez pas utiliser le GPS ? Saisir l'adresse manuellement
  </button>

  <div id="geo-address-block" class="geo-address-block hidden">
    <label for="f-address">Adresse de livraison <span class="muted small">(facultatif si GPS fourni)</span></label>
    <textarea id="f-address" name="address" rows="2" placeholder="Quartier, rue, repere..."></textarea>
  </div>

  <input type="hidden" id="f-latitude" name="latitude">
  <input type="hidden" id="f-longitude" name="longitude">
  <input type="hidden" id="f-location-accuracy" name="location_accuracy">
</div>
'''
html = html[:m.start()] + new_block + html[m.end():]
INDEX.write_text(html, encoding="utf-8")
print("[OK] index.html -> bloc reordonne (GPS en premier)")

# ============================================================
# 2) app.js : gerer le toggle adresse
# ============================================================
js = APPJS.read_text(encoding="utf-8")
shutil.copy(APPJS, APPJS.with_suffix(".js.bak"))
print("[OK] sauvegarde app.js.bak")

# Ajouter la logique du toggle dans initGeolocation
toggle_code = r'''
  var toggleBtn = document.getElementById("geo-toggle-address");
  var addrBlock = document.getElementById("geo-address-block");
  if (toggleBtn && addrBlock) {
    toggleBtn.addEventListener("click", function () {
      addrBlock.classList.toggle("hidden");
      if (!addrBlock.classList.contains("hidden")) {
        toggleBtn.textContent = "Masquer la saisie d'adresse";
        var ta = document.getElementById("f-address");
        if (ta) ta.focus();
      } else {
        toggleBtn.textContent = "Vous ne pouvez pas utiliser le GPS ? Saisir l'adresse manuellement";
      }
    });
  }
'''

# Inserer dans initGeolocation, juste avant la fermeture finale
anchor = '  var radios = document.querySelectorAll("input[name=delivery_mode]");'
if anchor in js and "geo-toggle-address" not in js:
    js = js.replace(anchor, toggle_code + "\n" + anchor, 1)
    print("[OK] app.js -> toggle adresse ajoute")
elif "geo-toggle-address" in js:
    print("[i] app.js -> toggle deja present")
else:
    print("[!] anchor radios introuvable dans app.js")

APPJS.write_text(js, encoding="utf-8")

# ============================================================
# 3) style.css : styles du toggle + block adresse
# ============================================================
css = CSS.read_text(encoding="utf-8")
shutil.copy(CSS, CSS.with_suffix(".css.bak"))
print("[OK] sauvegarde style.css.bak")

extra = '''
/* --- Bloc GPS prioritaire --- */
.geo-toggle-address{
  background:none;border:0;padding:6px 0;
  color:var(--green-dark);font-size:13px;font-weight:600;
  text-decoration:underline;cursor:pointer;text-align:left;
}
.geo-toggle-address:hover{color:var(--green)}
.geo-address-block{
  margin-top:8px;display:flex;flex-direction:column;gap:6px;
}
.geo-btn{
  width:100%;justify-content:center;
  padding:14px 18px;font-size:15px;
}
'''
if ".geo-toggle-address" not in css:
    css = css + extra
    CSS.write_text(css, encoding="utf-8")
    print("[OK] style.css -> styles toggle ajoutes")
else:
    print("[i] style.css -> styles deja presents")

print()
print("Fix applique. Redemarre le serveur, puis Ctrl+Shift+R.")