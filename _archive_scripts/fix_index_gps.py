from pathlib import Path
import re
import shutil

BASE = Path(__file__).resolve().parent
INDEX = BASE / "static" / "index.html"

html = INDEX.read_text(encoding="utf-8")
shutil.copy(INDEX, INDEX.with_suffix(".html.bak"))
print("[OK] sauvegarde ->", INDEX.with_suffix(".html.bak").name)

# Si deja patche, on ne fait rien
if 'id="geo-btn"' in html:
    print("[i] index.html deja patche")
    raise SystemExit(0)

# 1) Localiser le bloc address-row (peu importe les espaces/attributs)
pattern = re.compile(
    r'(<div[^>]*id="address-row"[^>]*>.*?</div>)',
    re.DOTALL | re.IGNORECASE,
)
m = pattern.search(html)
if not m:
    print("[!] bloc address-row introuvable. Contenu du formulaire :")
    # Afficher un extrait pour debug
    idx = html.find('id="address-row"')
    if idx == -1:
        print("    'address-row' n'existe NULLE PART dans index.html")
    else:
        print(html[max(0, idx - 200): idx + 400])
    raise SystemExit(1)

old_block = m.group(1)
print("[i] ancien bloc trouve (longueur", len(old_block), "caracteres)")

# 2) Construire le nouveau bloc a partir de l'ancien (on garde le textarea tel quel)
# On insere le bloc geo juste avant la fermeture </div> du address-row.
geo_html = '''
          <div class="geo-block">
            <button type="button" class="btn btn-ghost geo-btn" id="geo-btn">
              <span class="geo-icon">📍</span> Utiliser ma localisation actuelle
            </button>
            <div id="geo-status" class="geo-status hidden"></div>
          </div>
          <input type="hidden" id="f-latitude" name="latitude">
          <input type="hidden" id="f-longitude" name="longitude">
          <input type="hidden" id="f-location-accuracy" name="location_accuracy">
        '''

# On remplace le dernier </div> par geo_html + </div>
new_block = old_block[:-len("</div>")] + geo_html + "</div>"

html = html.replace(old_block, new_block, 1)
INDEX.write_text(html, encoding="utf-8")
print("[OK] index.html -> bloc geolocalisation insere")
print("[OK] Verifie le fichier avec : findstr /C:\"geo-btn\" static\\index.html")