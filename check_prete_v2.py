# -*- coding: utf-8 -*-
"""Trouve TOUTES les occurrences de o.status === 'prete' dans renderDrawer."""
import os, re

JS = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie\static\pharmacien.js"
src = open(JS, "r", encoding="utf-8").read()

# Extraire renderDrawer
m = re.search(r"function renderDrawer[\s\S]*?\n  \}\n", src)
if not m:
    print("[!!] renderDrawer introuvable"); exit(1)

drawer = m.group(0)

# Trouver TOUTES les occurrences
occurrences = [m.start() for m in re.finditer(r'o\.status === "prete"', drawer)]
print("=" * 78)
print(f"TROUVE {len(occurrences)} occurrence(s) de 'prete' dans renderDrawer")
print("=" * 78)

for i, idx in enumerate(occurrences, 1):
    print(f"\n--- OCCURRENCE #{i} (position {idx}) ---")
    # Afficher 800 chars apres
    end = min(len(drawer), idx + 800)
    chunk = drawer[idx:end]
    print(chunk)

    # Checks sur ce bloc
    print()
    print(f"  Checks occurrence #{i} :")
    print("    [" + ("OK" if 'o.delivery_mode === "livraison"' in chunk else "!!") + "] Condition livraison")
    print("    [" + ("OK" if 'data-drawer-act="en_livraison"' in chunk else "!!") + "] Bouton En livraison")
    print("    [" + ("OK" if 'data-drawer-act="terminee"' in chunk else "!!") + "] Bouton Terminee")
    print("    [" + ("OK" if 'data-check=' in chunk else "--") + "] Contient checklist (data-check)")
    print("    [" + ("OK" if 'ph-drawer-actions' in chunk else "--") + "] Contient ph-drawer-actions")
    print()