"""
fix_guide_and_navbar.py
1. Reformule l'etape 1 du guide de demarrage
2. Remplace Mobile Money par Mixx/Flooz
3. Retire "par voiture" de l'etape 4
4. Ajoute le libelle "Demande" sous le + de la navbar
"""
from pathlib import Path
import re
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
JS = STATIC / "professional_dashboard.js"
HTML = STATIC / "professional.html"

shutil.copy2(JS, JS.with_suffix(".js.bak"))
shutil.copy2(HTML, HTML.with_suffix(".html.bak"))
print("[OK] Backups crees")

# ============================================================
# 1. Guide : reformuler l'etape 1 (avec gestion des retours ligne)
# ============================================================
src = JS.read_text(encoding="utf-8")

# Etape 1 : regex souple qui accepte plusieurs espaces / retours ligne
pattern1 = re.compile(
    r"Constituez votre demande depuis le\s+<strong>catalogue</strong>\s+ou\s+via\s+<strong>WhatsApp</strong>\.",
    re.DOTALL,
)
new1 = ("Ouvrez l'onglet <strong>+ Demande</strong> : choisissez "
        "<strong>Catalogue</strong> (ajoutez vos produits un par un) "
        "ou <strong>WhatsApp</strong> (envoyez votre liste par texte, photo ou PDF).")
count1 = len(pattern1.findall(src))
src = pattern1.sub(lambda m: new1, src)
print(f"[OK] Etape 1 : {count1} remplacement(s)")

# Etape 3 : Mobile Money -> Mixx/Flooz
old3 = "Reglez par Mobile Money et envoyez la preuve."
new3 = ("Reglez par <strong>Mixx</strong> ou <strong>Flooz</strong>, "
        "puis envoyez la preuve de paiement.")
if old3 in src:
    src = src.replace(old3, new3, 1)
    print("[OK] Etape 3 : Mixx/Flooz")
else:
    print("[!] Etape 3 : texte 'Mobile Money' introuvable")

# Etape 4 : retirer "par voiture"
old4 = "Recevez votre commande par voiture (livraison B2B)."
new4 = "Recevez votre commande apres validation de la pharmacie."
if old4 in src:
    src = src.replace(old4, new4, 1)
    print("[OK] Etape 4 : 'par voiture' retire")
else:
    print("[!] Etape 4 : texte 'par voiture' introuvable")

JS.write_text(src, encoding="utf-8")

# ============================================================
# 2. Navbar : ajouter le libelle "Demande" sous le +
# ============================================================
hsrc = HTML.read_text(encoding="utf-8")

# Chercher le lien central et ajouter le label
pattern_nav = re.compile(
    r'(<a href="/professionnel/demande"[^>]*class="central"[^>]*>)\s*'
    r'<span>\s*\+\s*</span>\s*'
    r'(</a>)',
    re.DOTALL,
)

def add_label(m):
    return m.group(1) + '<span>+</span><span class="lbl">Demande</span>' + m.group(2)

if pattern_nav.search(hsrc):
    hsrc = pattern_nav.sub(add_label, hsrc, count=1)
    HTML.write_text(hsrc, encoding="utf-8")
    print("[OK] Navbar : libelle 'Demande' ajoute sous le +")
else:
    # Fallback : chercher une forme plus simple
    old_simple = '<a href="/professionnel/demande" class="central">'
    idx = hsrc.find(old_simple)
    if idx >= 0:
        # Trouver la fin du <a ...>
        end = hsrc.find("</a>", idx)
        if end > 0:
            new_block = (old_simple +
                         '<span>+</span><span class="lbl">Demande</span>' +
                         '</a>')
            hsrc = hsrc[:idx] + new_block + hsrc[end + 4:]
            HTML.write_text(hsrc, encoding="utf-8")
            print("[OK] Navbar : libelle 'Demande' ajoute (fallback)")
    else:
        print("[!] Navbar : lien central introuvable")
        # Debug
        idx = hsrc.find("central")
        if idx > 0:
            print("Contexte :")
            print(hsrc[max(0, idx - 100):idx + 200])

# ============================================================
# 3. Verification
# ============================================================
check_js = JS.read_text(encoding="utf-8")
print()
print("Verification JS :")
print("  'Ouvrez l\\'onglet + Demande' present :", "Ouvrez l'onglet <strong>+ Demande</strong>" in check_js)
print("  'Mixx' present :", "Mixx" in check_js)
print("  'Flooz' present :", "Flooz" in check_js)
print("  'par voiture' encore present :", "par voiture" in check_js)

check_html = HTML.read_text(encoding="utf-8")
print()
print("Verification HTML :")
print("  'lbl Demande' dans navbar :", '<span class="lbl">Demande</span>' in check_html)

print()
print("=" * 55)
print("FIX APPLIQUE")
print("=" * 55)
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur /professionnel (ou navigation privee)")
print("  Pas besoin de redemarrer Uvicorn") 