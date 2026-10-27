# -*- coding: utf-8 -*-
"""
Fix delivery flow V2 (corrige le bug HTTPException)
====================================================
1. Cartes : En livraison UNIQUEMENT si mode livraison + Terminee sur prete
2. Drawer : ajoute Refuser sur confirmee et en_preparation
3. Drawer : condition livraison + ajoute Terminee sur prete
4. Serveur : check prete -> en_livraison si mode retrait (syntaxe Python CORRIGEE)
Atomic, rollback auto.
"""
import os, re, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
MAIN = os.path.join(ROOT, "main.py")
JS   = os.path.join(ROOT, "static", "pharmacien.js")

TS  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, "_backup_delivery_v2_" + TS)
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
print("FIX DELIVERY FLOW V2 - " + TS)
print("=" * 78)
print("[BACKUP] " + BAK + "\n")

# ============================================================
# 1. Serveur : check retrait (syntaxe CORRIGEE)
# ============================================================
log("PHASE 1 : Serveur - check retrait", "STEP")

main_src = open(MAIN, "r", encoding="utf-8").read()

if "commande en retrait, pas de livraison possible" in main_src:
    log("Serveur deja patche", "WARN")
else:
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
        raise HTTPException(
            status_code=400,
            detail="Commande en retrait : pas de livraison possible"
        )'''

    if OLD_SRV in main_src:
        main_src = main_src.replace(OLD_SRV, NEW_SRV, 1)
        open(MAIN, "w", encoding="utf-8").write(main_src)
        ok, err = syntax_ok(MAIN)
        if not ok:
            log("main.py ERREUR : " + str(err), "ERR")
            shutil.copy2(os.path.join(BAK, "main.py"), MAIN)
            shutil.copy2(os.path.join(BAK, "pharmacien.js"), JS)
            sys.exit(1)
        log("main.py : check retrait ajoute (syntaxe OK)", "OK")
    else:
        log("Pattern serveur introuvable", "WARN")

# ============================================================
# 2. Cartes : condition livraison + Terminee
# ============================================================
log("PHASE 2 : Cartes - buildQuickActions", "STEP")

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
# 3. Drawer : confirmee -> + Refuser
# ============================================================
log("PHASE 3 : Drawer - confirmee + Refuser", "STEP")

OLD_D_CONF = '''    } else if (o.status === "confirmee") {
      h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-act="en_preparation" data-ref="' + esc(o.reference) + '">Preparer</button>';
    } else if (o.status === "en_preparation") {'''

NEW_D_CONF = '''    } else if (o.status === "confirmee") {
      h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-act="en_preparation" data-ref="' + esc(o.reference) + '">Preparer</button>';
      h += '<button type="button" class="ph-btn ph-btn-danger" data-drawer-act="refusee" data-ref="' + esc(o.reference) + '">Refuser</button>';
    } else if (o.status === "en_preparation") {'''

if 'data-drawer-act="refusee"' in js_src and 'data-drawer-act="en_preparation"' in js_src:
    # Verifier si le Refuser est deja dans le bloc confirmee
    chunk = js_src[js_src.find('o.status === "confirmee"'):js_src.find('o.status === "en_preparation"')]
    if "refusee" in chunk:
        log("Drawer confirmee : Refuser deja present", "WARN")
    else:
        js_src = js_src.replace(OLD_D_CONF, NEW_D_CONF, 1)
        log("Drawer confirmee : Refuser ajoute", "OK")
elif OLD_D_CONF in js_src:
    js_src = js_src.replace(OLD_D_CONF, NEW_D_CONF, 1)
    log("Drawer confirmee : Refuser ajoute", "OK")
else:
    log("Pattern drawer confirmee introuvable", "WARN")

# ============================================================
# 4. Drawer : en_preparation -> + Refuser
# ============================================================
log("PHASE 4 : Drawer - en_preparation + Refuser", "STEP")

OLD_D_PREP = '''    } else if (o.status === "en_preparation") {
      h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-act="prete" data-ref="' + esc(o.reference) + '">Prete</button>';
    } else if (o.status === "prete") {'''

NEW_D_PREP = '''    } else if (o.status === "en_preparation") {
      h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-act="prete" data-ref="' + esc(o.reference) + '">Prete</button>';
      h += '<button type="button" class="ph-btn ph-btn-danger" data-drawer-act="refusee" data-ref="' + esc(o.reference) + '">Refuser</button>';
    } else if (o.status === "prete") {'''

if OLD_D_PREP in js_src:
    js_src = js_src.replace(OLD_D_PREP, NEW_D_PREP, 1)
    log("Drawer en_preparation : Refuser ajoute", "OK")
else:
    log("Pattern drawer en_preparation introuvable (ou deja patche)", "WARN")

# ============================================================
# 5. Drawer : prete -> condition livraison + Terminee
# ============================================================
log("PHASE 5 : Drawer - prete condition + Terminee", "STEP")

OLD_D_PRE = '''    } else if (o.status === "prete") {
      h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-act="en_livraison" data-ref="' + esc(o.reference) + '">En livraison</button>';
    } else if (o.status === "en_livraison") {'''

NEW_D_PRE = '''    } else if (o.status === "prete") {
      if (o.delivery_mode === "livraison") {
        h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-act="en_livraison" data-ref="' + esc(o.reference) + '">En livraison</button>';
      }
      h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-act="terminee" data-ref="' + esc(o.reference) + '">Terminee</button>';
    } else if (o.status === "en_livraison") {'''

if OLD_D_PRE in js_src:
    js_src = js_src.replace(OLD_D_PRE, NEW_D_PRE, 1)
    log("Drawer prete : condition + Terminee ajoutes", "OK")
else:
    log("Pattern drawer prete introuvable (ou deja patche)", "WARN")

# ============================================================
# 6. Verifier equilibre + sauvegarder
# ============================================================
if brace_diff(js_src) != 0:
    log("pharmacien.js desequilibre (" + str(brace_diff(js_src)) + ") - ROLLBACK", "ERR")
    shutil.copy2(os.path.join(BAK, "main.py"), MAIN)
    shutil.copy2(os.path.join(BAK, "pharmacien.js"), JS)
    sys.exit(1)

open(JS, "w", encoding="utf-8").write(js_src)
log("pharmacien.js sauvegarde", "OK")

# ============================================================
# Verification
# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)

final_js = open(JS, "r", encoding="utf-8").read()
final_main = open(MAIN, "r", encoding="utf-8").read()

# Extraire le bloc drawer
drawer_start = final_js.find("function renderDrawer")
drawer_end = final_js.find("// Event delegation", drawer_start)
drawer = final_js[drawer_start:drawer_end] if drawer_start > 0 else ""

checks = [
    ("Serveur : check retrait",             "Commande en retrait" in final_main),
    ("Serveur syntaxe OK",                  syntax_ok(MAIN)[0]),
    ("Cartes : condition livraison",        'if (o.delivery_mode === "livraison")' in final_js),
    ("Drawer confirmee : Refuser",          'o.status === "confirmee"' in drawer and drawer.split('o.status === "confirmee"')[1].split("} else")[0].count("refusee") > 0),
    ("Drawer en_preparation : Refuser",     'o.status === "en_preparation"' in drawer and drawer.split('o.status === "en_preparation"')[1].split("} else")[0].count("refusee") > 0),
    ("Drawer prete : condition livraison",  'o.status === "prete"' in drawer and 'if (o.delivery_mode === "livraison")' in drawer.split('o.status === "prete"')[1].split("} else")[0]),
    ("Drawer prete : Terminee",             'o.status === "prete"' in drawer and 'data-drawer-act="terminee"' in drawer.split('o.status === "prete"')[1].split("} else")[0]),
    ("Accolades equilibrees",               brace_diff(final_js) == 0),
]
for label, ok in checks:
    print("  [" + ("OK" if ok else "!!") + "] " + label)

print()
print("[BACKUP] " + BAK)
print()
print("[CMD] Restart Uvicorn OBLIGATOIRE :")
print("  taskkill /F /IM uvicorn.exe 2>nul")
print("  taskkill /F /IM python.exe 2>nul")
print("  cd \"" + ROOT + "\"")
print("  python -m uvicorn main:app --host 0.0.0.0 --port 8000")
print()
print("[TEST] Edge : F12 > Application > Clear site data + Disable cache + Ctrl+Shift+R")
print()
print("  Retrait 'confirmee' -> Preparer + Refuser")
print("  Retrait 'en_preparation' -> Prete + Refuser")
print("  Retrait 'prete' -> Terminee SEULEMENT")
print("  Livraison 'prete' -> En livraison + Terminee")
print()
print("  Meme logique dans le drawer.")
print()
print("[ROLLBACK] :")
print('  copy "' + BAK + '\\main.py" "' + MAIN + '"')
print('  copy "' + BAK + '\\pharmacien.js" "' + JS + '"')