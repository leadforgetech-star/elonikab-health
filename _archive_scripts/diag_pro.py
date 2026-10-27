"""
diag_pro.py - Diagnostic du probleme professional.html
"""
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
HTML = BASE / "static" / "professional.html"

print("=" * 70)
print("DIAGNOSTIC PROFESSIONAL.HTML")
print("=" * 70)
print()

# 1. Le fichier sur disque contient-il le nouveau code ?
print("[1] Fichier sur disque :")
if HTML.exists():
    content = HTML.read_text(encoding="utf-8")
    size = len(content)
    has_actions = "pro-action-card" in content
    has_wa = "Envoyer une liste" in content
    has_modal = "wa-modal" in content
    print("    Chemin  :", HTML)
    print("    Taille  :", size, "octets")
    print("    Contient 'pro-action-card' :", has_actions)
    print("    Contient 'Envoyer une liste' :", has_wa)
    print("    Contient 'wa-modal' :", has_modal)
else:
    print("    [ERREUR] Fichier introuvable !")
print()

# 2. Combien de processus python.exe tournent ?
print("[2] Processus python.exe :")
try:
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq python.exe"],
                       capture_output=True, text=True)
    lines = [l for l in r.stdout.split("\n") if "python.exe" in l]
    if lines:
        for l in lines:
            print("   ", l.strip())
    else:
        print("    Aucun processus python.exe en cours.")
except Exception as e:
    print("    Erreur tasklist:", e)
print()

# 3. Qui ecoute sur le port 8000 ?
print("[3] Qui ecoute sur le port 8000 :")
try:
    r = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
    listeners = [l for l in r.stdout.split("\n") if ":8000" in l and "LISTENING" in l]
    if listeners:
        for l in listeners:
            print("   ", l.strip())
    else:
        print("    Personne n'ecoute sur le port 8000.")
except Exception as e:
    print("    Erreur netstat:", e)
print()

# 4. Ce que le serveur renvoie reellement
print("[4] Contenu servi par le serveur (http://127.0.0.1:8000) :")
try:
    req = urllib.request.Request("http://127.0.0.1:8000/static/professional.html")
    with urllib.request.urlopen(req, timeout=5) as resp:
        served = resp.read().decode("utf-8", errors="replace")
    print("    Taille  :", len(served), "octets")
    print("    Contient 'pro-action-card' :", "pro-action-card" in served)
    print("    Contient 'Envoyer une liste' :", "Envoyer une liste" in served)
    print("    Contient 'wa-modal' :", "wa-modal" in served)
    print("    Contient 'pro-actions' :", "pro-actions" in served)
    # extrait
    idx = served.find("<body")
    print("    Apercu (extrait ligne 1-5 apres <body>) :")
    tail = served[idx:idx+500]
    for line in tail.split("\n")[:8]:
        print("       ", line.strip()[:80])
except Exception as e:
    print("    Erreur:", e)
print()

# 5. Le fichier servi est-il le meme que celui sur disque ?
print("[5] Comparaison :")
try:
    req = urllib.request.Request("http://127.0.0.1:8000/static/professional.html")
    with urllib.request.urlopen(req, timeout=5) as resp:
        served = resp.read().decode("utf-8", errors="replace")
    on_disk = HTML.read_text(encoding="utf-8")
    print("    Identiques  :", served == on_disk)
    print("    Taille disque :", len(on_disk))
    print("    Taille servi  :", len(served))
    if served != on_disk:
        # Premier endroit ou ca differe
        min_len = min(len(served), len(on_disk))
        diff_at = -1
        for i in range(min_len):
            if served[i] != on_disk[i]:
                diff_at = i
                break
        if diff_at >= 0:
            print("    Premiere difference a l'offset :", diff_at)
            print("    Disque :", repr(on_disk[diff_at:diff_at+80]))
            print("    Servi  :", repr(served[diff_at:diff_at+80]))
except Exception as e:
    print("    Erreur:", e)

print()
print("=" * 70)
print("Colle ce diagnostic complet.")
print("=" * 70)