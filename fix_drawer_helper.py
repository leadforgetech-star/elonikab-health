# -*- coding: utf-8 -*-
"""Fix : définir drawerRefreshIfOpen() dans pharmacien.js."""
import os, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
JS = os.path.join(ROOT, "static", "pharmacien.js")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_drawerhelper_{TS}")
os.makedirs(BAK, exist_ok=True)
shutil.copy2(JS, os.path.join(BAK, "pharmacien.js"))

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]"}[k]
    print(p, m)

def brace_diff(s): return s.count("{") - s.count("}")

print("=" * 78)
print(f"FIX DRAWER HELPER - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

src = open(JS, "r", encoding="utf-8").read()

# Diagnostic
n_def = src.count("function drawerRefreshIfOpen")
n_call = src.count("drawerRefreshIfOpen()")
print(f"[DIAG] Definitions : {n_def}")
print(f"[DIAG] Appels : {n_call}")

if n_def > 0:
    log("Fonction deja definie — verifier scope", "WARN")
else:
    log("Fonction MANQUANTE — on l'ajoute", "INFO")

    # Injecter juste avant window.EHModal ou a la fin
    HELPER = '''
/* V3 : recharge le drawer ouvert s'il existe (apres action paiement) */
function drawerRefreshIfOpen() {
  try {
    var d = document.getElementById("ph-drawer");
    if (!d || !d.classList.contains("open")) return;
    var refEl = document.getElementById("ph-drawer-ref");
    var ref = refEl ? (refEl.textContent || "").trim() : "";
    if (ref && typeof window.phOpenDrawer === "function") {
      setTimeout(function() { window.phOpenDrawer(ref); }, 150);
    }
  } catch(e) { console.warn("[drawer-refresh] " + e); }
}
window.drawerRefreshIfOpen = drawerRefreshIfOpen;

'''

    # Inserer avant window.EHModal = {
    anchor = "window.EHModal = {"
    if anchor in src:
        src = src.replace(anchor, HELPER + anchor, 1)
        log("Helper injecte avant EHModal", "OK")
    else:
        # Fallback : fin du fichier
        src = src + HELPER
        log("Helper injecte en fin de fichier", "OK")

# Verifier equilibre
diff = brace_diff(src)
if diff != 0:
    log(f"Deséquilibre ({diff}) - ROLLBACK", "ERR")
    shutil.copy2(os.path.join(BAK, "pharmacien.js"), JS)
    sys.exit(1)

open(JS, "w", encoding="utf-8").write(src)
log("pharmacien.js sauvegarde", "OK")

# Verification
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)
final = open(JS, "r", encoding="utf-8").read()
checks = [
    ("Fonction définie",    "function drawerRefreshIfOpen()" in final),
    ("Exposée sur window",  "window.drawerRefreshIfOpen = drawerRefreshIfOpen" in final),
    ("Appelée dans doValidate", final.count("drawerRefreshIfOpen()") >= 3),
    ("Accolades OK",        brace_diff(final) == 0),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

print()
print(f"[BACKUP] {BAK}")
print()
print("[CMD] Pas de restart Uvicorn (frontend only).")
print("[TEST] F12 > Clear site data + Ctrl+Shift+R sur /pharmacien")
print("  - Ouvrir une commande avec paiement PROOF_SUBMITTED")
print("  - Cliquer Valider -> plus d'erreur drawerRefreshIfOpen")
print("  - Le drawer doit se recharger")
print()
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\pharmacien.js" "{JS}"')