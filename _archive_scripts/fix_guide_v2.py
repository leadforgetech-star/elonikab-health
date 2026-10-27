"""
fix_guide_v2.py
Reformule l'etape 1 du guide pour clarifier les 2 options dans l'onglet Demande.
"""
from pathlib import Path
import re
import shutil

BASE = Path(__file__).resolve().parent
JS = BASE / "static" / "professional_dashboard.js"

shutil.copy2(JS, JS.with_suffix(".js.bak"))
print("[OK] Backup ->", JS.with_suffix(".js.bak").name)

src = JS.read_text(encoding="utf-8")

# Nouveau bloc complet du guide
new_guide = '''    var guide = document.createElement("div");
    guide.className = "acc-guide";
    guide.innerHTML =
      '<h3>Comment commander sur Elokinab ?</h3>' +
      '<div class="acc-guide-steps">' +

        '<div class="acc-guide-step">' +
          '<div class="acc-guide-num">1</div>' +
          '<div class="acc-guide-text">' +
            'Ouvrez l\\'onglet <strong>+ Demande</strong> :' +
            '<div style="margin-top:6px;padding-left:4px;font-size:12.5px;color:#64748b">' +
              '\\u2192 <strong>Catalogue</strong> : ajoutez vos produits un par un<br>' +
              '\\u2192 <strong>WhatsApp</strong> : envoyez votre liste (texte, photo ou PDF)' +
            '</div>' +
          '</div>' +
        '</div>' +

        '<div class="acc-guide-step">' +
          '<div class="acc-guide-num">2</div>' +
          '<div class="acc-guide-text">Validez le recapitulatif et envoyez votre demande.</div>' +
        '</div>' +

        '<div class="acc-guide-step">' +
          '<div class="acc-guide-num">3</div>' +
          '<div class="acc-guide-text">Reglez par <strong>Mixx</strong> ou <strong>Flooz</strong>, puis envoyez la preuve de paiement.</div>' +
        '</div>' +

        '<div class="acc-guide-step">' +
          '<div class="acc-guide-num">4</div>' +
          '<div class="acc-guide-text">Recevez votre commande apres validation de la pharmacie.</div>' +
        '</div>' +

      '</div>';

    box.appendChild(guide);'''

# Chercher le bloc existant "var guide = ..."
pattern = re.compile(
    r'    var guide = document\.createElement\("div"\);.*?box\.appendChild\(guide\);',
    re.DOTALL,
)

if pattern.search(src):
    src = pattern.sub(new_guide, src, count=1)
    JS.write_text(src, encoding="utf-8")
    print("[OK] Guide reformule")
else:
    print("[!] Bloc guide introuvable")
    print("    Colle-moi le contexte :")
    idx = src.find("var guide =")
    if idx > 0:
        print(src[idx:idx+400])

# Verification
check = JS.read_text(encoding="utf-8")
if "Ouvrez l\\'onglet <strong>+ Demande</strong>" in check:
    print("[OK] Nouveau texte present")
if "Mixx" in check and "Flooz" in check:
    print("[OK] Mixx et Flooz presents")

print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur iPhone (ou navigation privee)")