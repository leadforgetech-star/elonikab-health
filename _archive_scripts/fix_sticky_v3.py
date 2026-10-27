"""
fix_sticky_v3.py
- Corrige position: sticky (overflow-x: clip au lieu de hidden)
- Force -webkit-sticky pour iOS
- Renomme le bouton Suivi en 'Suivre ma commande'
"""
from pathlib import Path
import datetime
import re
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_sticky_v3_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(STATIC / "mobile.css", backup / "mobile.css")
shutil.copy2(STATIC / "header.css", backup / "header.css")
shutil.copy2(STATIC / "header.js", backup / "header.js")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. mobile.css : remplacer overflow-x: hidden par clip
# ============================================================
MOBILE = STATIC / "mobile.css"
css = MOBILE.read_text(encoding="utf-8")

# Retirer toutes les regles overflow-x: hidden sur html/body
css = re.sub(
    r"html,\s*body\s*\{[^}]*overflow-x:\s*hidden[^}]*\}",
    "html, body { max-width: 100%; }",
    css,
)
css = re.sub(r"overflow-x:\s*hidden\s*;", "overflow-x: clip;", css)

# Retirer toute regle body { overflow-y: auto } qui pourrait casser sticky
css = re.sub(r"body\s*\{\s*overflow-y:\s*auto;\s*\}", "", css)

# Ajouter en tete un bloc explicite
PREFIX = '''/* === STICKY FIX : ne JAMAIS mettre overflow-x:hidden sur html/body (casse sticky) === */
html{
  overflow-x: clip;
  overflow-y: visible;
}
body{
  max-width: 100%;
  overflow-x: clip;
}
/* === fin STICKY FIX === */

'''
if "STICKY FIX" not in css:
    css = PREFIX + css
    print("[OK] mobile.css -> STICKY FIX en tete")

MOBILE.write_text(css, encoding="utf-8")

# ============================================================
# 2. header.css : sticky robuste avec -webkit-sticky
# ============================================================
HC = STATIC / "header.css"
hcss = HC.read_text(encoding="utf-8")

# Retirer anciens blocs .topbar sticky pour eviter doublons
hcss = re.sub(
    r"/\* --- Header vraiment sticky ---.*?(?=\n/\*|\Z)",
    "",
    hcss,
    flags=re.DOTALL,
)

STICKY_BLOCK = '''
/* --- Header vraiment sticky (V3) --- */
.topbar{
  position: -webkit-sticky !important;
  position: sticky !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  z-index: 9999 !important;
  background: #ffffff !important;
  box-shadow: 0 2px 10px rgba(15,38,32,.08) !important;
  /* Ne pas mettre overflow ici : casse le sticky */
}
.eh-mini-bar{
  position: -webkit-sticky !important;
  position: sticky !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  z-index: 9999 !important;
  background: #ffffff !important;
  box-shadow: 0 2px 10px rgba(15,38,32,.08) !important;
}
/* Forcer : .topbar doit etre enfant direct de body pour sticky */
body > .topbar{ display: block; }
/* Aucun ancetre ne doit avoir overflow:hidden/transform */
body{ overflow-x: clip !important; }

/* --- Bouton Suivre ma commande --- */
.eh-track-btn{
  display: inline-flex !important;
  align-items: center;
  gap: 6px;
  padding: 9px 14px !important;
  font-size: 13px !important;
  font-weight: 700;
  background: #0f9d76 !important;
  color: #ffffff !important;
  border: 1px solid #0f9d76 !important;
  border-radius: 10px;
  text-decoration: none;
  white-space: nowrap;
}
.eh-track-btn:hover{
  background: #0a7a5a !important;
  border-color: #0a7a5a !important;
}
@media (max-width: 520px){
  .eh-track-btn{
    padding: 7px 10px !important;
    font-size: 12px !important;
    gap: 4px;
  }
  .eh-track-btn .eh-track-icon{ font-size: 14px; }
}
'''

hcss += STICKY_BLOCK
HC.write_text(hcss, encoding="utf-8")
print("[OK] header.css -> sticky V3 + bouton")

# ============================================================
# 3. header.js : changer le label
# ============================================================
HJ = STATIC / "header.js"
js = HJ.read_text(encoding="utf-8")

# Remplacer n'importe quelle variante du bouton Suivi
patterns = [
    ('''    // Lien Suivi toujours visible avec label
    var track = el("a", "eh-link-btn eh-track-btn");
    track.href = "/suivi";
    track.title = "Suivre mes commandes";
    track.innerHTML = '&#128230; Suivi';
    wrap.appendChild(track);''',
     '''    // Bouton Suivre ma commande
    var track = el("a", "eh-track-btn");
    track.href = "/suivi";
    track.title = "Suivre ma commande";
    track.innerHTML = '<span class="eh-track-icon">&#128230;</span> Suivre ma commande';
    wrap.appendChild(track);'''),
]

changed = False
for old, new in patterns:
    if old in js:
        js = js.replace(old, new, 1)
        changed = True
        break

if not changed:
    # Fallback : chercher un bloc existant
    if "eh-track-btn" in js:
        # Remplacer innerHTML
        js = re.sub(
            r'track\.innerHTML\s*=\s*[\'"][^\'"]*[\'"];',
            'track.innerHTML = \'<span class="eh-track-icon">&#128230;</span> Suivre ma commande\';',
            js,
            count=1,
        )
        # Remplacer title
        js = re.sub(
            r'track\.title\s*=\s*[\'"][^\'"]*[\'"];',
            'track.title = "Suivre ma commande";',
            js,
            count=1,
        )
        # Retirer eh-link-btn s'il est présent en même temps que eh-track-btn
        js = js.replace('"eh-link-btn eh-track-btn"', '"eh-track-btn"')
        js = js.replace("'eh-link-btn eh-track-btn'", "'eh-track-btn'")
        changed = True
        print("[OK] header.js -> label mis a jour (fallback)")

if changed:
    HJ.write_text(js, encoding="utf-8")
    print("[OK] header.js -> 'Suivre ma commande'")
else:
    print("[!] header.js -> pattern du bouton introuvable")
    # Debug : chercher "Suivi" dans le fichier
    for i, line in enumerate(js.splitlines(), 1):
        if "Suivi" in line or "track" in line.lower() and "href" in line:
            print("    ligne " + str(i) + " : " + line.strip())

print()
print("=" * 60)
print("FIX STICKY V3 APPLIQUE")
print("=" * 60)
print()
print("Corrections :")
print("  1. overflow-x: hidden -> overflow-x: clip (sticky fonctionne)")
print("  2. position: -webkit-sticky pour iOS Safari")
print("  3. z-index 9999 (header au-dessus de tout)")
print("  4. Bouton renomme : 'Suivre ma commande'")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur l'iPhone (ou navigation privee)")