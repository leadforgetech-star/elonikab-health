# -*- coding: utf-8 -*-
"""
LOT 2 p2 - AUDIT COHERENCE FRONT/BACK
======================================
Compare :
  - Les transitions autorisees cote serveur (ALLOWED_TRANSITIONS)
  - Les actions affichees cote frontend par statut
Genere rapport_coherence.txt
"""
import os, re, datetime

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
MAIN = os.path.join(ROOT, "main.py")
JS   = os.path.join(ROOT, "static", "pharmacien.js")
SUIVI = os.path.join(ROOT, "static", "suivi.js")
PRO_CMD = os.path.join(ROOT, "static", "professional_commandes.html")
PRO_RT = os.path.join(ROOT, "static", "professional_realtime.js")
PAY = os.path.join(ROOT, "static", "payment.js")

OUT = os.path.join(ROOT, "rapport_coherence.txt")

lines = []
def hr(t): lines.append("=" * 78); lines.append(t); lines.append("=" * 78)
def sub(t): lines.append(""); lines.append("-" * 78); lines.append(t); lines.append("-" * 78)

lines.append("AUDIT COHERENCE FRONT/BACK - " + datetime.datetime.now().isoformat(timespec="seconds"))
lines.append("")

# ============================================================
# 1. Transitions serveur (source de verite)
# ============================================================
hr("[1] SERVEUR : ALLOWED_TRANSITIONS (source de verite)")

if os.path.isfile(MAIN):
    src = open(MAIN, "r", encoding="utf-8").read()
    idx = src.find("ALLOWED_TRANSITIONS")
    if idx >= 0:
        end = src.find("}", idx + 20)
        # Trouver la fin du dict (double accolade)
        end = src.find("}\n", idx)
        while end > 0 and src[idx:end].count("{") > src[idx:end].count("}"):
            end = src.find("}\n", end + 1)
        block = src[idx:end+2]
        lines.append(block)
    else:
        lines.append("[!!] ALLOWED_TRANSITIONS introuvable")
else:
    lines.append("[!!] main.py introuvable")

# ============================================================
# 2. Actions frontend pharmacien.js
# ============================================================
hr("[2] FRONTEND PHARMACIEN : NEXT_ACTIONS et buildQuickActions")

if os.path.isfile(JS):
    src = open(JS, "r", encoding="utf-8").read()

    # NEXT_ACTIONS (pharmacien.js V1 legacy)
    sub("NEXT_ACTIONS (legacy, ligne ~30)")
    m = re.search(r"var NEXT_ACTIONS\s*=\s*\{[\s\S]*?\n\};", src)
    if m:
        lines.append(m.group(0))
    else:
        lines.append("  [pas de NEXT_ACTIONS trouve]")

    sub("buildQuickActions (V6, drawer)")
    m2 = re.search(r"function buildQuickActions[\s\S]*?\n  \}", src)
    if m2:
        lines.append(m2.group(0))
    else:
        lines.append("  [buildQuickActions introuvable]")

    sub("ACTIONS object (V6, drawer commandes)")
    m3 = re.search(r"var ACTIONS\s*=\s*\{[\s\S]*?\n  \};", src)
    if m3:
        lines.append(m3.group(0))
    else:
        lines.append("  [ACTIONS introuvable]")

    sub("Actions avec data-drawer-act")
    acts = set(re.findall(r'data-drawer-act="([^"]+)"', src))
    lines.append("  " + ", ".join(sorted(acts)) if acts else "  [aucun]")
else:
    lines.append("[!!] pharmacien.js introuvable")

# ============================================================
# 3. Actions patient (suivi.js)
# ============================================================
hr("[3] FRONTEND PATIENT : actions disponibles selon statut")

if os.path.isfile(SUIVI):
    src = open(SUIVI, "r", encoding="utf-8").read()
    # Statuts pills
    sub("STATUS_PILLS")
    m = re.search(r"var STATUS_PILLS[\s\S]*?\n\s*\};", src)
    if m:
        lines.append(m.group(0))
    # can_pay
    sub("Zones conditionnelles sur statut (can_pay, can_cancel, ...)")
    for match in re.finditer(r"(tl\.\w+|o\.status\s*===?\s*[\"']\w+[\"'])[\s\S]{0,80}", src):
        t = match.group(0)
        if any(k in t for k in ["can_pay", "can_cancel", "can_", "==="]):
            line_no = src[:match.start()].count("\n") + 1
            lines.append(f"  L{line_no}: {t[:100].strip()}")
else:
    lines.append("[!!] suivi.js introuvable")

# ============================================================
# 4. Actions PRO (professional_commandes.html)
# ============================================================
hr("[4] FRONTEND PRO : NEXT_ACTIONS / STATUS")

if os.path.isfile(PRO_CMD):
    src = open(PRO_CMD, "r", encoding="utf-8").read()
    sub("Extraits NEXT_ACTIONS / STATUS_PILLS")
    for m in re.finditer(r"(NEXT_ACTIONS|STATUS_PILLS|STATUS_LABELS)\s*=\s*\{[\s\S]{0,600}?\n\s*\};", src):
        lines.append(m.group(0)[:700])
        lines.append("")
else:
    lines.append("[pas de professional_commandes.html]")

# ============================================================
# 5. Payment actions
# ============================================================
hr("[5] FRONTEND PAYMENT : conditions d'affichage")

if os.path.isfile(PAY):
    src = open(PAY, "r", encoding="utf-8").read()
    sub("Blocs conditionnels sur status")
    for m in re.finditer(r"if\s*\([^)]*status[^)]*\)[\s\S]{0,150}", src):
        line_no = src[:m.start()].count("\n") + 1
        lines.append(f"  L{line_no}: {m.group(0)[:150].strip()}")
        lines.append("")
else:
    lines.append("[pas de payment.js]")

# ============================================================
# 6. Resume automatique
# ============================================================
hr("[6] SYNTHESE")

# Extraire les transitions depuis main.py
if os.path.isfile(MAIN):
    src = open(MAIN, "r", encoding="utf-8").read()
    m = re.search(r"ALLOWED_TRANSITIONS\s*=\s*\{([\s\S]*?)\n\}", src)
    if m:
        block = m.group(1)
        transitions = {}
        for line in block.split("\n"):
            mm = re.match(r'\s*"(\w+)":\s*\{([^}]*)\}', line)
            if mm:
                from_st = mm.group(1)
                tos = re.findall(r'"(\w+)"', mm.group(2))
                transitions[from_st] = set(tos)
        lines.append("")
        lines.append("Transitions AUTORISEES cote serveur :")
        for k in sorted(transitions.keys()):
            lines.append(f"  {k:20s} -> {sorted(transitions[k])}")

report = "\n".join(lines)
open(OUT, "w", encoding="utf-8").write(report)
print("=" * 78)
print("[OK] Rapport : " + OUT)
print("     " + str(len(report)) + " caracteres")
print("=" * 78)
print()
print("Ouvre-le : start notepad rapport_coherence.txt")
print()
print("Ensuite, envoie-moi le contenu pour analyse.")