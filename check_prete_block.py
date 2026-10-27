# -*- coding: utf-8 -*-
"""Affiche le bloc 'prete' dans renderDrawer pour verifier visuellement."""
import os, re

JS = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie\static\pharmacien.js"
src = open(JS, "r", encoding="utf-8").read()

# Extraire renderDrawer
m = re.search(r"function renderDrawer[\s\S]*?\n  \}\n", src)
if not m:
    print("[!!] renderDrawer introuvable"); exit(1)

drawer = m.group(0)

# Trouver le bloc prete
idx = drawer.find('o.status === "prete"')
if idx < 0:
    print("[!!] Bloc prete introuvable dans renderDrawer")
    exit(1)

# Afficher 800 chars apres
end = min(len(drawer), idx + 900)
print("=" * 78)
print("BLOC 'prete' dans renderDrawer")
print("=" * 78)
print(drawer[max(0, idx-50):end])
print()
print("=" * 78)
print("CHECKS")
print("=" * 78)
block = drawer[idx:idx+600]
print("  [" + ("OK" if 'o.delivery_mode === "livraison"' in block else "!!") + "] Condition livraison")
print("  [" + ("OK" if 'data-drawer-act="en_livraison"' in block else "!!") + "] Bouton En livraison")
print("  [" + ("OK" if 'data-drawer-act="terminee"' in block else "!!") + "] Bouton Terminee")