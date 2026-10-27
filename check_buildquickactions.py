# -*- coding: utf-8 -*-
"""Verifie si buildQuickActions a bien le Refuser sur confirmee/en_preparation."""
import os, re

JS = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie\static\pharmacien.js"

src = open(JS, "r", encoding="utf-8").read()

m = re.search(r"function buildQuickActions[\s\S]*?\n  \}", src)
if not m:
    print("[!!] buildQuickActions INTROUVABLE")
    exit(1)

block = m.group(0)
print("=" * 70)
print("CONTENU ACTUEL de buildQuickActions")
print("=" * 70)
print(block)
print()
print("=" * 70)
print("DIAGNOSTIC")
print("=" * 70)

# Verifier chaque transition
tests = [
    ("en_attente = Refuser",       'en_attente' in block and 'refuse' in block.split('en_attente')[1].split('else')[0]),
    ("confirmee = Refuser",        'confirmee' in block and 'refuse' in block.split('confirmee')[1].split('else')[0]),
    ("en_preparation = Refuser",   'en_preparation' in block and 'refuse' in block.split('en_preparation')[1].split('else')[0]),
    ("prete = Terminee",           'prete' in block and 'complete' in block.split('if (o.status === "prete")')[1].split('else')[0]),
]
for label, ok in tests:
    print("  [" + ("OK" if ok else "!!") + "] " + label)

print()
if all(ok for _, ok in tests):
    print("=> Le patch EST dans le fichier. Probleme = CACHE NAVIGATEUR.")
    print("   Solution : F12 > Application > Clear site data + Ctrl+Shift+R")
else:
    print("=> Le patch N'EST PAS dans le fichier. Il faut relancer fix_coherence.py")