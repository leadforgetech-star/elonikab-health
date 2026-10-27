"""diag_payment.py - Diagnostic page paiement."""
from pathlib import Path
import urllib.request
import urllib.error
import json

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
BASE_URL = "http://127.0.0.1:8000"

print("=" * 60)
print("DIAGNOSTIC PAGE PAIEMENT")
print("=" * 60)
print()

# 1. Fichiers
print("[1] Fichiers sur disque :")
for f in ("payment.html", "payment.js", "safe_locale.js"):
    p = STATIC / f
    if p.exists():
        size = p.stat().st_size
        print(f"    OK  {f} ({size} octets)")
    else:
        print(f"    [!] {f} INTROUVABLE")
print()

# 2. Contenu de payment.html - refs aux scripts
print("[2] Scripts references dans payment.html :")
html = (STATIC / "payment.html").read_text(encoding="utf-8")
import re
scripts = re.findall(r'<script[^>]*src="([^"]+)"', html)
for s in scripts:
    print(f"    {s}")
print()

# 3. Servis par le serveur
print("[3] Fichiers servis par le serveur :")
for path in ("/static/payment.html", "/static/payment.js", "/static/safe_locale.js"):
    try:
        r = urllib.request.urlopen(BASE_URL + path, timeout=5)
        code = r.status
        size = len(r.read())
        print(f"    {path} -> HTTP {code} ({size} octets)")
    except urllib.error.HTTPError as e:
        print(f"    {path} -> HTTP {e.code}")
    except Exception as e:
        print(f"    {path} -> ERREUR {e}")
print()

# 4. Contenu de payment.js - recherche de problemes
print("[4] Analyse payment.js :")
js = (STATIC / "payment.js").read_text(encoding="utf-8")
checks = [
    ("DOMContentLoaded", "DOMContentLoaded" in js),
    ("load function", "function load" in js),
    ("fetchPayment", "fetchPayment" in js),
    ("_loadTimer", "_loadTimer" in js),
    ("console.log", "console.log" in js),
]
for name, ok in checks:
    print(f"    {'OK ' if ok else '[!]'} {name} : {ok}")
print()

# 5. Chercher les caracteres non-ASCII dans payment.js (source de bugs)
print("[5] Caracteres non-ASCII dans payment.js :")
non_ascii = [(i, c) for i, c in enumerate(js) if ord(c) > 127]
if non_ascii:
    print(f"    {len(non_ascii)} caracteres non-ASCII trouves")
    # Montrer 5 exemples
    for i, c in non_ascii[:5]:
        line = js[:i].count("\n") + 1
        print(f"      Ligne {line} : U+{ord(c):04X} ('{c}')")
else:
    print("    Aucun")
print()

# 6. Verifier les accents dans le HTML
print("[6] Caracteres non-ASCII dans payment.html :")
html_non_ascii = [(i, c) for i, c in enumerate(html) if ord(c) > 127]
print(f"    {len(html_non_ascii)} caracteres non-ASCII")
print()

print("=" * 60)
print("Colle-moi le resultat complet.")
print("=" * 60)