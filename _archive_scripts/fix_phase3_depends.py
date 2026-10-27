"""
fix_phase3_depends.py
Corrige la Phase 3 : enveloppe require_role(...) dans Depends(...).
"""
from pathlib import Path
import datetime
import re
import shutil

BASE = Path(__file__).resolve().parent
PROS = BASE / "v3_modules" / "professionals.py"

if not PROS.exists():
    print("[ERREUR] professionals.py introuvable. Relance d'abord v3_install_phase3.py")
    raise SystemExit(1)

# Backup
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_v3_p3_fix_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(PROS, backup / "professionals.py")
print("[OK] Backup ->", backup.name)

src = PROS.read_text(encoding="utf-8")

# 1. S'assurer que Depends est importe
if "from fastapi import Depends" not in src:
    src = src.replace(
        "from fastapi import HTTPException",
        "from fastapi import Depends, HTTPException",
        1,
    )
    print("[OK] import Depends ajoute")

# 2. Envelopper require_role(...) dans Depends(...) dans les signatures
# Match : "user=require_role(" ... ")"  →  "user=Depends(require_role(...))"
def wrap(match):
    return match.group(1) + "Depends(" + match.group(2) + ")"

pattern = re.compile(r'(user=)(require_role\([^)]*\))')
src, n = pattern.subn(wrap, src)

if n == 0:
    print("[!] Aucune occurrence 'user=require_role(...)' trouvee.")
    print("    Verif manuelle de professionals.py requise.")
else:
    print("[OK] " + str(n) + " signatures corrigees (Depends ajoute)")

PROS.write_text(src, encoding="utf-8")

# 3. Verification
check = PROS.read_text(encoding="utf-8")
count_depends = check.count("Depends(require_role")
count_raw = len(re.findall(r'(?<!Depends\()user=require_role', check))
print()
print("Verification :")
print("  Depends(require_role...) : " + str(count_depends))
print("  user=require_role(...) nu : " + str(count_raw))

if count_raw == 0 and count_depends >= 6:
    print("[OK] Le fix est correct.")
else:
    print("[!] Anomalie detectee. Relance le script ou signale-le.")

print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  python main.py")
print("  python test_phase3.py   (dans un autre CMD)")