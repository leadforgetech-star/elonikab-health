# -*- coding: utf-8 -*-
# inspect_pro_badges.py
# Dump la structure des badges cloche dans les pages pro
import os, re

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
STATIC = os.path.join(ROOT, "static")

PAGES = [
    "professional.html",
    "professional_catalogue.html",
    "professional_commandes.html",
    "professional_demande.html",
]

print("=" * 70)
print("INSPECT BADGES PRO")
print("=" * 70)

for name in PAGES:
    p = os.path.join(STATIC, name)
    if not os.path.exists(p):
        continue
    html = open(p, "r", encoding="utf-8").read()

    print(f"\n{'=' * 70}")
    print(f"FICHIER : {name}")
    print(f"{'=' * 70}")

    # 1. Chercher elements avec 'notif' dans id/class
    print("\n[Elements avec 'notif']")
    for m in re.finditer(r'<[^>]*(?:id|class)="[^"]*notif[^"]*"[^>]*>', html, re.IGNORECASE):
        print(f"  {m.group(0)[:200]}")

    # 2. Chercher les scripts charges
    print("\n[Scripts charges]")
    for m in re.finditer(r'<script[^>]*src=["\']([^"\']+)["\']', html):
        print(f"  {m.group(1)}")

    # 3. Chercher un eventuel container de liste commandes
    print("\n[Containers liste commandes/demandes]")
    for m in re.finditer(r'<[^>]*(?:id|class)="[^"]*(?:commandes?|orders?|demandes?|list)[^"]*"[^>]*>', html, re.IGNORECASE):
        print(f"  {m.group(0)[:200]}")