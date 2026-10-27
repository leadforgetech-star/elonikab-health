# -*- coding: utf-8 -*-
# verify_order_ref_scope.py
# Verifie que 'order' et 'reference' sont accessibles au point d'injection
import os, re
ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
P = os.path.join(ROOT, "v3_modules", "payments.py")
src = open(P, "r", encoding="utf-8").read()
lines = src.split("\n")

print("=" * 78)
print("VERIF SCOPE des variables order + reference")
print("=" * 78)

# Pour chaque fonction injectee, montrer les 15 lignes avant + 3 apres l'injection
for fn in ["upload_proof_json", "upload_proof_binary", "upload_proof"]:
    print(f"\n### {fn}() ###")
    # Trouver l'injection
    fn_pat = re.compile(rf'[ \t]*(?:async\s+)?def\s+{re.escape(fn)}\s*\(')
    m = fn_pat.search(src)
    if not m:
        print("  [!!] fonction introuvable")
        continue
    # Trouver le point d'injection
    block = src[m.start():m.start()+5000]
    inj_match = re.search(r'_notify_admins_proof\(conn', block)
    if not inj_match:
        print("  [!!] injection introuvable")
        continue

    inj_pos_abs = m.start() + inj_match.start()
    inj_line = src[:inj_pos_abs].count("\n")

    # Afficher 20 lignes avant, l'injection, 3 après
    for i in range(max(0, inj_line - 20), min(len(lines), inj_line + 5)):
        marker = ">>>" if i == inj_line else "   "
        print(f"{marker} {i+1:4}  {lines[i]}")
    print()

# Verifs specifiques
print("=" * 78)
print("VERIFICATIONS SPECIFIQUES")
print("=" * 78)

for fn in ["upload_proof_json", "upload_proof_binary", "upload_proof"]:
    # Chercher la fonction complete
    fn_pat = re.compile(rf'[ \t]*(?:async\s+)?def\s+{re.escape(fn)}\s*\(')
    m = fn_pat.search(src)
    if not m:
        continue
    # Bloc de la fonction
    end_pat = re.compile(r'\n(?=[ \t]{0,4}(?:@app\.|@router\.|def\s|async\s+def\s|class\s))')
    em = end_pat.search(src, m.start() + 10)
    block = src[m.start():em.start() if em else len(src)]

    # Verifier 'order =' dans le bloc
    has_order = bool(re.search(r'\border\s*=\s*conn\.execute', block))
    has_ref_param = bool(re.search(rf'def\s+{re.escape(fn)}\s*\([^)]*reference', block))

    print(f"\n{fn}() :")
    print(f"  [{'OK' if has_order else '!!'}] variable 'order' assignee dans la fonction")
    print(f"  [{'OK' if has_ref_param else '!!'}] parametre 'reference' dans la signature")