# phase3a_dump_auth.py
# Dump auth.py complet + sections cles de main.py
# NE MODIFIE RIEN
import os

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
AUTH = os.path.join(ROOT, "v3_modules", "auth.py")
MAIN = os.path.join(ROOT, "main.py")
REPORT = os.path.join(ROOT, "phase3a_dump_auth.txt")

out = []
def log(s=""):
    print(s); out.append(s)

# ============================================================
# 1. auth.py COMPLET
# ============================================================
log("=" * 78)
log(f"FICHIER: {AUTH}")
log("=" * 78)
with open(AUTH, "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        log(f"{i:4}  {line.rstrip()}")

# ============================================================
# 2. main.py - 120 premieres lignes (imports + helpers + get_db)
# ============================================================
log("\n" + "=" * 78)
log(f"FICHIER: {MAIN}  (lignes 1-120)")
log("=" * 78)
with open(MAIN, "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines[:120], 1):
    log(f"{i:4}  {line.rstrip()}")

# ============================================================
# 3. main.py - bloc install_* (750-900)
# ============================================================
log("\n" + "=" * 78)
log(f"FICHIER: {MAIN}  (lignes 750-900)")
log("=" * 78)
for i, line in enumerate(lines[749:900], 750):
    log(f"{i:4}  {line.rstrip()}")

# ============================================================
# 4. main.py - toutes les occurrences install_auth / require_role / get_current_user
# ============================================================
log("\n" + "=" * 78)
log(f"[4] USAGE install_auth / require_role / get_current_user dans main.py")
log("=" * 78)
for i, line in enumerate(lines, 1):
    if any(k in line for k in ["install_auth", "get_current_user", "require_role"]):
        log(f"  {i:4}  {line.rstrip()}")

# ============================================================
# 5. Verification via import (test runtime)
# ============================================================
log("\n" + "=" * 78)
log("[5] TEST IMPORT RUNTIME")
log("=" * 78)
import sys
sys.path.insert(0, ROOT)
try:
    import v3_modules.auth as A
    log(f"  auth.__all__ = {getattr(A, '__all__', 'not defined')}")
    log(f"  auth.get_current_user = {getattr(A, 'get_current_user', 'ABSENT')}")
    log(f"  auth.install_auth     = {getattr(A, 'install_auth', 'ABSENT')}")
    log(f"  auth.require_role     = {getattr(A, 'require_role', 'ABSENT')}")
    log(f"  auth.SESSION_COOKIE   = {getattr(A, 'SESSION_COOKIE', 'ABSENT')}")
except Exception as e:
    log(f"  [ERREUR import] {type(e).__name__}: {e}")

# ============================================================
# Ecriture rapport
# ============================================================
with open(REPORT, "w", encoding="utf-8") as f:
    f.write("\n".join(out))

log("\n" + "=" * 78)
log(f"[RAPPORT] {REPORT}")
log("=" * 78)
log("\n>>> AUCUNE MODIFICATION. Colle le rapport complet.")