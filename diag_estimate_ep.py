# -*- coding: utf-8 -*-
"""Diagnostic : ou est l'endpoint /api/delivery/estimate dans main.py ?"""
import os, re

MAIN = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie\main.py"
src = open(MAIN, "r", encoding="utf-8").read()
lines = src.split("\n")

print("=" * 78)
print("RECHERCHE : /api/delivery/estimate")
print("=" * 78)

# Trouver toutes les occurrences
matches = list(re.finditer(r"delivery/estimate", src))
print(f"\n{len(matches)} occurrence(s) :")
for m in matches:
    ln = src[:m.start()].count("\n") + 1
    print(f"  L{ln}: ...{src[max(0,m.start()-40):m.start()+50].replace(chr(10),' ')}...")

# Trouver la ligne du if __name__
idx_main = src.find('if __name__ == "__main__":')
if idx_main > 0:
    ln_main = src[:idx_main].count("\n") + 1
    print(f"\nif __name__ a la ligne {ln_main}")

# Trouver l'endpoint et comparer sa position
m_ep = re.search(r'@app\.(?:post|get)\([\"\'](/api/delivery/estimate)', src)
if m_ep:
    ln_ep = src[:m_ep.start()].count("\n") + 1
    print(f"Endpoint POST /api/delivery/estimate a la ligne {ln_ep}")
    if idx_main > 0 and m_ep.start() > idx_main:
        print("  ⚠️ L'ENDPOINT EST APRES if __name__ == '__main__' -> JAMAIS EXECUTE")
        print("  -> C'est pour ça qu'il renvoie 404")
    else:
        print("  ✅ L'endpoint est AVANT if __name__ -> OK")

# Afficher les 30 lignes autour de l'endpoint
if m_ep:
    start = max(0, m_ep.start() - 200)
    end = min(len(src), m_ep.start() + 2500)
    line_start = src[:start].count("\n") + 1
    print("\n" + "=" * 78)
    print(f"ZONE ENDPOINT (L{line_start} a ...)")
    print("=" * 78)
    for i, line in enumerate(src[start:end].split("\n"), line_start):
        marker = ">>>" if "/api/delivery/estimate" in line else "   "
        print(f"{marker} {i:4d}| {line}")

# Verifier indentation
if m_ep:
    ep_line = src[m_ep.start():].split("\n")[0]
    print(f"\nIndentation ligne @app: {len(ep_line) - len(ep_line.lstrip())} espaces")

# Verifier si DeliveryEstimateRequest existe
if "class DeliveryEstimateRequest" in src:
    m = re.search(r"class DeliveryEstimateRequest[\s\S]{0,300}", src)
    ln = src[:m.start()].count("\n") + 1
    print(f"\nclass DeliveryEstimateRequest a la ligne {ln} (OK)")
else:
    print("\n[!!] class DeliveryEstimateRequest INTROUVABLE")

# Verifier compute_delivery_fee_v2
if "def compute_delivery_fee_v2" in src:
    m = re.search(r"def compute_delivery_fee_v2[\s\S]{0,100}", src)
    ln = src[:m.start()].count("\n") + 1
    print(f"def compute_delivery_fee_v2 a la ligne {ln} (OK)")
else:
    print("[!!] compute_delivery_fee_v2 INTROUVABLE")