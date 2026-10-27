# -*- coding: utf-8 -*-
"""
Fix cohérence livraison/retrait :
1. Cartes : "En livraison" UNIQUEMENT si mode livraison
2. Drawer : idem + ajout bouton "Terminee" sur prete
3. Serveur : bloquer prete -> en_livraison si mode retrait
Atomic, rollback auto.
"""
import os, re, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
MAIN = os.path.join(ROOT, "main.py")
JS   = os.path.join(ROOT, "static", "pharmacien.js")

TS  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, "_backup_delivery_" + TS)
os.makedirs(BAK, exist_ok=True)

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]", "STEP": "\n###"}[k]
    print(p, m)

def syntax_ok(path):
    try:
        with open(path, "rb") as f:
            compile(f.read(), path, "exec")
        return True, None
    except SyntaxError as e:
        return False, "L" + str(e.lineno) + ": " + e.msg

def brace_diff(s): return s.count("{") - s.count("}")

for p, n in [(MAIN, "main.py"), (JS, "pharmacien.js")]:
    shutil.copy2(p, os.path.join(BAK, n))

print("=" * 78)
print("FIX DELIVERY FLOW - " + TS)
print("=" * 78)
print("[BACKUP] " + BAK + "\n")

# ============================================================
# 1. Cartes : En livraison UNIQUEMENT si mode livraison
# ============================================================
log("PHASE 1 : Cartes - buildQuickActions", "STEP")

js_src = open(JS, "r", encoding="utf-8").read()

OLD_CARDS = '''    } else if (o.status === "prete") {
      actions.push({ label: "En livraison", kind: "primary", act: "shipped" });
      actions.push({ label: "Terminee", kind: "primary", act: "complete" });
    } else if (o.status === "en_livraison") {'''

NEW_CARDS = '''    } else if (o.status === "prete") {
      if (o.delivery_mode === "livraison") {
        actions.push({ label: "En livraison", kind: "primary", act: "shipped" });
      }
      actions.push({ label: "Terminee", kind: "primary", act: "complete" });
    } else if (o.status === "en_livraison") {'''

if NEW_CARDS in js_src:
    log("Cartes deja patchees", "WARN")
elif OLD_CARDS in js_src:
    js_src = js_src.replace(OLD_CARDS, NEW_CARDS, 1)
    log("Cartes : condition livraison ajoutee", "OK")
else:
    log("Pattern cartes introuvable", "WARN")

# ============================================================
# 2. Drawer : idem + bouton Terminee ajoute sur prete
# ============================================================
log("PHASE 2 : Drawer - renderDrawer", "STEP")

# Trouver le bloc "prete" dans renderDrawer
m = re.search(
    r'(\} else if \(o\.status === "prete"\) \{\s*\n\s*h \+= .[^;]*"en_livraison"[^;]*;[^}]*\})',
    js_src
)

OLD_DRAWER_PATTERN = r'''} else if (o.status === "prete") {
      h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-act="en_livraison" data-ref="' + esc(o.reference) + '">En livraison</button>';
    }'''

NEW_DRAWER = '''} else if (o.status === "prete") {
      if (o.delivery_mode === "livraison") {
        h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-act="en_livraison" data-ref="' + esc(o.reference) + '">En livraison</button>';
      }
      h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-act="terminee" data-ref="' + esc(o.reference) + '">Terminee</button>';
    }'''

if 'data-drawer-act="terminee"' in js_src and 'if (o.delivery_mode === "livraison") {\n        h += \'<button type="button" class="ph-btn ph-btn-primary" data-drawer-act="en_livraison"' in js_src:
    log("Drawer deja patche", "WARN")
elif OLD_DRAWER_PATTERN in js_src:
    js_src = js_src.replace(OLD_DRAWER_PATTERN, NEW_DRAWER, 1)
    log("Drawer : condition + Terminee ajoutes", "OK")
else:
    # Essayer une version plus souple
    m2 = re.search(
        r'(\} else if \(o\.status === "prete"\) \{[\s\S]{0,400}?data-drawer-act="en_livraison"[\s\S]{0,200}?\})',
        js_src
    )
    if m2:
        old_block = m2.group(1)
        new_block = '''} else if (o.status === "prete") {
      if (o.delivery_mode === "livraison") {
        h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-act="en_livraison" data-ref="' + esc(o.reference) + '">En livraison</button>';
      }
      h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-act="terminee" data-ref="' + esc(o.reference) + '">Terminee</button>';
    }'''
        js_src = js_src.replace(old_block, new_block, 1)
        log("Drawer : pattern variante patche", "OK")
    else:
        log("Pattern drawer introuvable - dump manuel requis", "WARN")

# Verifier equilibre
if brace_diff(js_src) != 0:
    log("pharmacien.js desequilibre - ROLLBACK", "ERR")
    shutil.copy2(os.path.join(BAK, "pharmacien.js"), JS)
    sys.exit(1)

open(JS, "w", encoding="utf-8").write(js_src)
log("pharmacien.js sauvegarde", "OK")

# ============================================================
# 3. Serveur : bloquer prete -> en_livraison si mode retrait
# ============================================================
log("PHASE 3 : Serveur - check mode livraison", "STEP")

main_src = open(MAIN, "r", encoding="utf-8").read()

if "transition refusee : commande en retrait" in main_src:
    log("Serveur deja patche", "WARN")
else:
    # Ajouter la verification apres le check ALLOWED_TRANSITIONS
    OLD_SRV = '''    current_status = row["status"]
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        conn.close()
        raise HTTPException(status_code=400, detail="Transition de statut non autorisee")'''

    NEW_SRV = '''    current_status = row["status"]
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        conn.close()
        raise HTTPException(status_code=400, detail="Transition de statut non autorisee")

    # Check metier : pas de livraison si mode retrait
    if new_status == "en_livraison" and row["delivery_mode"] != "livraison":
        conn.close()
        raise HTTPException(status_code=400,
            "transition refusee : commande en retrait, pas de livraison possible")'''

    if OLD_SRV in main_src:
        main_src = main_src.replace(OLD_SRV, NEW_SRV, 1)
        open(MAIN, "w", encoding="utf-8").write(main_src)
        ok, err = syntax_ok(MAIN)
        if not ok:
            log("main.py ERREUR : " + str(err), "ERR")
            shutil.copy2(os.path.join(BAK, "main.py"), MAIN)
            shutil.copy2(os.path.join(BAK, "pharmacien.js"), JS)
            sys.exit(1)
        log("Serveur : check retrait ajoute", "OK")
    else:
        log("Pattern serveur introuvable", "WARN")

# ============================================================
# Verification
# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)

final_js = open(JS, "r", encoding="utf-8").read()
final_main = open(MAIN, "r", encoding="utf-8").read()

checks = [
    ("Cartes : condition livraison",      'if (o.delivery_mode === "livraison") {' in final_js.split('buildQuickActions')[1].split("return actions")[0] if 'buildQuickActions' in final_js else False),
    ("Cartes : Terminee toujours la",     'label: "Terminee"' in final_js),
    ("Drawer : Terminee ajoute",          'data-drawer-act="terminee"' in final_js),
    ("Serveur : check retrait",           "transition refusee : commande en retrait" in final_main),
    ("pharmacien.js equilibre",           brace_diff(final_js) == 0),
    ("main.py syntaxe OK",                syntax_ok(MAIN)[0]),
]
for label, ok in checks:
    print("  [" + ("OK" if ok else "!!") + "] " + label)

print()
print("[BACKUP] " + BAK)
print()
print("[CMD] Restart Uvicorn OBLIGATOIRE (main.py modifie) :")
print("  taskkill /F /IM uvicorn.exe 2>nul")
print("  taskkill /F /IM python.exe 2>nul")
print("  cd \"" + ROOT + "\"")
print("  python -m uvicorn main:app --host 0.0.0.0 --port 8000")
print()
print("[TEST] Edge : F12 > Application > Clear site data + Disable cache + Ctrl+Shift+R")
print("  1) Commande RETRAIT 'prete' -> boutons : Terminee SEULEMENT")
print("  2) Commande LIVRAISON 'prete' -> boutons : En livraison + Terminee")
print("  3) Drawer : meme logique")
print()
print("[ROLLBACK] :")
print('  copy "' + BAK + '\\main.py" "' + MAIN + '"')
print('  copy "' + BAK + '\\pharmacien.js" "' + JS + '"')