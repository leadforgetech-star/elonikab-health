"""
disable_magic_link.py
Desactive completement le systeme de magic link.
- Retire les routes /api/admin/magic-link*, /acces/{token}
- Supprime le module magic_links.py
- Le generate_link.py ne fonctionnera plus
"""
from pathlib import Path
import datetime
import re
import shutil

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
MAGIC = BASE / "v3_modules" / "magic_links.py"
GENLINK = BASE / "generate_link.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_disable_magic_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAIN, backup / "main.py")
if MAGIC.exists():
    shutil.copy2(MAGIC, backup / "magic_links.py")
if GENLINK.exists():
    shutil.copy2(GENLINK, backup / "generate_link.py")
print("[OK] Backup ->", backup.name)

# 1. Retirer l'appel install_magic_links dans main.py
src = MAIN.read_text(encoding="utf-8")

patterns = [
    r'\nfrom v3_modules\.magic_links import install_magic_links\ninstall_magic_links\(app, get_db, require_role\)',
    r'\nfrom v3_modules\.magic_links import install_magic_links\s*\n\s*install_magic_links\(app, get_db, require_role\)\s*\n',
    r'\ninstall_magic_links\(app, get_db, require_role\)\s*\n',
    r'\nfrom v3_modules\.magic_links import install_magic_links\s*\n',
]

removed = 0
for p in patterns:
    new_src, n = re.subn(p, "\n", src)
    if n > 0:
        src = new_src
        removed += n

if removed > 0:
    MAIN.write_text(src, encoding="utf-8")
    print(f"[OK] main.py -> {removed} reference(s) magic_link retiree(s)")
else:
    print("[i] Aucune reference magic_link dans main.py")

# 2. Renommer magic_links.py pour le neutraliser
if MAGIC.exists():
    disabled = MAGIC.with_suffix(".py.disabled")
    if disabled.exists():
        disabled.unlink()
    MAGIC.rename(disabled)
    print(f"[OK] magic_links.py -> renomme en {disabled.name}")

# 3. Renommer generate_link.py
if GENLINK.exists():
    disabled_link = GENLINK.with_suffix(".py.disabled")
    if disabled_link.exists():
        disabled_link.unlink()
    GENLINK.rename(disabled_link)
    print(f"[OK] generate_link.py -> renomme en {disabled_link.name}")

# 4. Renommer restart_and_link.py si présent
RAL = BASE / "restart_and_link.py"
if RAL.exists():
    disabled_ral = RAL.with_suffix(".py.disabled")
    if disabled_ral.exists():
        disabled_ral.unlink()
    RAL.rename(disabled_ral)
    print(f"[OK] restart_and_link.py -> renomme en {disabled_ral.name}")

# Verification
check = MAIN.read_text(encoding="utf-8")
print()
print("Verification :")
print("  'magic_links' dans main.py :", "magic_links" in check)
print("  '/acces/' dans main.py     :", "/acces/" in check)
print("  magic_links.py existe      :", MAGIC.exists())
print("  generate_link.py existe    :", GENLINK.exists())

print()
print("=" * 60)
print("MAGIC LINK DESACTIVE")
print("=" * 60)
print()
print("Les utilisateurs doivent maintenant se connecter avec")
print("leur email + mot de passe sur /connexion.")
print()
print("Pour reactiver plus tard :")
print("  - Renommer v3_modules/magic_links.py.disabled en .py")
print("  - Remettre l'appel dans main.py depuis le backup")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --host 0.0.0.0 --port 8000")