# -*- coding: utf-8 -*-
# verify_fix_livraison.py - Diagnostic + fix des 2 patches partiels
import os, re, shutil, datetime, ast

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
MAIN = os.path.join(ROOT, "main.py")
STATIC = os.path.join(ROOT, "static")
CMD = os.path.join(STATIC, "professional_commandes.html")

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
bak = os.path.join(ROOT, f"_backup_fix_liv_{ts}")
os.makedirs(bak, exist_ok=True)
shutil.copy2(MAIN, os.path.join(bak, "main.py.bak"))
shutil.copy2(CMD, os.path.join(bak, "professional_commandes.html.bak"))
print(f"[BACKUP] {bak}\n")

# ============================================================
# 1. DIAGNOSTIC main.py
# ============================================================
print("=" * 70)
print("[1] DIAGNOSTIC main.py")
print("=" * 70)
main = open(MAIN, "r", encoding="utf-8").read()

# Trouver ALLOWED_TRANSITIONS
m = re.search(r'ALLOWED_TRANSITIONS\s*=\s*\{([\s\S]*?)\n\}', main)
if m:
    print("\nALLOWED_TRANSITIONS actuel :")
    for line in m.group(0).split("\n"):
        print(f"  {line}")
    if '"en_livraison"' in m.group(1):
        print("\n  -> en_livraison deja present")
    else:
        print("\n  -> en_livraison MANQUANT")
else:
    print("  [!!] ALLOWED_TRANSITIONS introuvable")

# ============================================================
# 2. FIX main.py : ALLOWED_TRANSITIONS
# ============================================================
if m and '"en_livraison"' not in m.group(1):
    block = m.group(1)
    print("\n[FIX] main.py ALLOWED_TRANSITIONS")

    # Chercher une ligne "prete": {...} pour y ajouter en_livraison
    pat = re.compile(r'(\s*)("prete"|\'prete\')\s*:\s*\{([^}]*)\}')
    match = pat.search(block)
    if match:
        indent = match.group(1)
        inner = match.group(3).strip()
        if inner:
            # Ajouter en_livraison dans le set
            inner_new = inner.rstrip().rstrip(",") + ', "en_livraison"'
        else:
            inner_new = '"en_livraison"'
        new_line = f'{indent}"prete": {{{inner_new}}}'
        block_new = block[:match.start()] + new_line + block[match.end():]
        print(f"  [OK] ajout dans prete : {inner_new}")

        # Ajouter ligne en_livraison -> terminee
        pat2 = re.compile(r'(\s*)("prete"|\'prete\')\s*:\s*\{[^}]*\},?\s*\n')
        m2 = pat2.search(block_new)
        if m2:
            insert_pos = m2.end()
            new_entry = f'{indent}"en_livraison": {{"terminee"}},\n'
            block_new = block_new[:insert_pos] + new_entry + block_new[insert_pos:]
            print(f"  [OK] entree en_livraison -> terminee ajoutee")

        main = main[:m.start(1)] + block_new + main[m.end(1):]

        try:
            ast.parse(main)
            open(MAIN, "w", encoding="utf-8").write(main)
            print("  [OK] main.py sauvegarde")
        except SyntaxError as e:
            print(f"  [!!] SyntaxError ligne {e.lineno}: {e.msg}")
    else:
        print("  [!!] ligne 'prete' introuvable dans ALLOWED_TRANSITIONS")

# Re-verif
main = open(MAIN, "r", encoding="utf-8").read()
m = re.search(r'ALLOWED_TRANSITIONS\s*=\s*\{([\s\S]*?)\n\}', main)
print("\n[VERIF] main.py ALLOWED_TRANSITIONS :")
for line in m.group(0).split("\n"):
    print(f"  {line}")

# ============================================================
# 3. DIAGNOSTIC professional_commandes.html
# ============================================================
print("\n" + "=" * 70)
print("[2] DIAGNOSTIC professional_commandes.html")
print("=" * 70)
h = open(CMD, "r", encoding="utf-8").read()

# Trouver STATUS_PILLS et STATUS_LABELS
for var in ("STATUS_PILLS", "STATUS_LABELS"):
    m = re.search(rf'var {var}\s*=\s*\{{([\s\S]*?)\}};', h)
    if m:
        print(f"\n{var} actuel :")
        for line in m.group(0).split("\n")[:8]:
            print(f"  {line}")
    else:
        print(f"  [!!] {var} introuvable")

# ============================================================
# 4. FIX professional_commandes.html
# ============================================================
print("\n[FIX] professional_commandes.html")
if "en_livraison" in h:
    print("  [SKIP] en_livraison deja present")
else:
    # Status pills
    pat_pills = re.compile(
        r'(prete\s*:\s*"[^"]+"\s*,)',
    )
    m1 = pat_pills.search(h)
    if m1:
        h = h[:m1.end()] + '\n      en_livraison: "pill-in-delivery",' + h[m1.end():]
        print("  [OK] en_livraison ajoute a STATUS_PILLS")
    else:
        print("  [!!] STATUS_PILLS prete introuvable")

    # Status labels
    pat_lbls = re.compile(
        r'(prete\s*:\s*"Pr[eê]te"\s*,)',
    )
    m2 = pat_lbls.search(h)
    if m2:
        h = h[:m2.end()] + '\n      en_livraison: "En livraison",' + h[m2.end():]
        print("  [OK] en_livraison ajoute a STATUS_LABELS")
    else:
        print("  [!!] STATUS_LABELS prete introuvable")

    open(CMD, "w", encoding="utf-8").write(h)

# ============================================================
# 5. VERIF FINALE
# ============================================================
print("\n" + "=" * 70)
print("[3] VERIFICATION FINALE")
print("=" * 70)
main = open(MAIN, "r", encoding="utf-8").read()
h = open(CMD, "r", encoding="utf-8").read()

checks = [
    ("main.py : VALID_STATUSES en_livraison", '"en_livraison"' in main or "'en_livraison'" in main),
    ("main.py : ALLOWED_TRANSITIONS en_livraison", 'ALLOWED_TRANSITIONS' in main and 'en_livraison' in main.split('ALLOWED_TRANSITIONS')[1][:500]),
    ("commandes : en_livraison dans STATUS_PILLS", 'en_livraison' in h),
    ("commandes : 'En livraison' label", "En livraison" in h or "en livraison" in h),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

print(f"\n[BACKUP] {bak}")
print("\n[CMD] Restart Uvicorn OBLIGATOIRE :")
print("  taskkill /F /IM uvicorn.exe 2>nul")
print("  taskkill /F /IM python.exe 2>nul")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")