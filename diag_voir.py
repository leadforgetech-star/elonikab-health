# -*- coding: utf-8 -*-
# diag_voir.py - Analyse du bouton "Voir" dans le catalogue
import os, re

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
STATIC = os.path.join(ROOT, "static")
APP = os.path.join(STATIC, "app.js")
INDEX = os.path.join(STATIC, "index.html")
CSS = os.path.join(STATIC, "patient_common.css")

app = open(APP, "r", encoding="utf-8").read()
idx = open(INDEX, "r", encoding="utf-8").read()
css = open(CSS, "r", encoding="utf-8").read()

print("=" * 78)
print("[1] Fonction openProduct()")
print("=" * 78)
for i, line in enumerate(app.split("\n"), 1):
    if "function openProduct" in line:
        for j in range(i-1, min(len(app.split("\n")), i+20)):
            print(f"  {j+1:4}  {app.split(chr(10))[j]}")
        break

print("\n" + "=" * 78)
print("[2] Fonction renderProduct()")
print("=" * 78)
for i, line in enumerate(app.split("\n"), 1):
    if "function renderProduct" in line:
        for j in range(i-1, min(len(app.split("\n")), i+40)):
            print(f"  {j+1:4}  {app.split(chr(10))[j]}")
        break

print("\n" + "=" * 78)
print("[3] Structure de view-product dans index.html")
print("=" * 78)
m = re.search(r'<section id="view-product"[\s\S]*?</section>', idx)
if m:
    for line in m.group(0).split("\n"):
        print(f"  {line}")

print("\n" + "=" * 78)
print("[4] Classes CSS pour product-detail")
print("=" * 78)
for i, line in enumerate(css.split("\n"), 1):
    if ".product-detail" in line or ".detail-" in line or ".pt-product-detail" in line:
        print(f"  L{i}: {line.strip()[:120]}")

print("\n" + "=" * 78)
print("[5] Bouton 'Voir' dans productCard()")
print("=" * 78)
for i, line in enumerate(app.split("\n"), 1):
    if 'el("button"' in line and "Voir" in line:
        for j in range(max(0, i-3), min(len(app.split("\n")), i+5)):
            print(f"  {j+1:4}  {app.split(chr(10))[j]}")