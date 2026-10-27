# -*- coding: utf-8 -*-
# replace_elonikab.py
# Remplace globalement Elonikab -> Elonikab (et elonikab -> elonikab)
# Scan recursif de .py, .html, .css, .js, .json
# Ignore : _archive_scripts, _backup_*, venv, __pycache__, backups, .git
import os, re, shutil, datetime

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"

# ============================================================
# 0. DOSSIERS A IGNORER
# ============================================================
SKIP_DIRS = {
    "_archive_scripts", "venv", "__pycache__", ".git", "backups",
    "node_modules", ".vscode",
}
def should_skip(dirpath):
    parts = dirpath.replace("\\", "/").split("/")
    for p in parts:
        if p in SKIP_DIRS:
            return True
        if p.startswith("_backup_") or p.startswith("_archive_"):
            return True
    return False

# ============================================================
# 1. BACKUP GLOBAL
# ============================================================
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
bak = os.path.join(ROOT, f"_backup_rename_{ts}")
os.makedirs(bak, exist_ok=True)
print(f"[BACKUP] {bak}\n")

# ============================================================
# 2. SCAN ET REMPLACEMENT
# ============================================================
EXT = {".py", ".html", ".css", ".js", ".json", ".txt", ".md"}

# Patterns : on remplace Elonikab -> Elonikab partout, et elonikab -> elonikab
REPLACEMENTS = [
    ("Elonikab", "Elonikab"),
    ("elonikab", "elonikab"),
    ("ELONIKAB", "ELONIKAB"),
]

files_changed = []
files_scanned = 0
total_replacements = 0
report = []

for dirpath, dirnames, filenames in os.walk(ROOT):
    if should_skip(dirpath):
        dirnames[:] = []  # ne pas descendre
        continue
    # Filtrer les sous-dossiers
    dirnames[:] = [d for d in dirnames if not should_skip(os.path.join(dirpath, d))]

    for fname in filenames:
        ext = os.path.splitext(fname)[1].lower()
        if ext not in EXT:
            continue
        full = os.path.join(dirpath, fname)
        rel = os.path.relpath(full, ROOT)

        try:
            with open(full, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            continue  # binaire -> skip
        except Exception as e:
            print(f"  [!!] {rel} : {e}")
            continue

        files_scanned += 1
        original = content
        count_before = 0
        for old, new in REPLACEMENTS:
            n = content.count(old)
            if n > 0:
                count_before += n
                content = content.replace(old, new)

        if content != original:
            # Backup fichier
            bak_path = os.path.join(bak, rel.replace("\\", "__").replace("/", "__"))
            try:
                shutil.copy2(full, bak_path)
            except Exception:
                pass
            # Ecrire
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)
            files_changed.append((rel, count_before))
            total_replacements += count_before
            print(f"  [OK] {rel}  ({count_before} remplacement(s))")

# ============================================================
# 3. RESUME
# ============================================================
print("\n" + "=" * 70)
print(f"RESUME")
print("=" * 70)
print(f"  Fichiers scannes   : {files_scanned}")
print(f"  Fichiers modifies  : {len(files_changed)}")
print(f"  Remplacements      : {total_replacements}")
print(f"  Backup             : {bak}")

if files_changed:
    print(f"\n  Detail :")
    for rel, n in files_changed[:30]:
        print(f"    {rel}  ({n})")
    if len(files_changed) > 30:
        print(f"    ... et {len(files_changed) - 30} autres")

# ============================================================
# 4. VERIF : plus aucune occurrence de Elonikab
# ============================================================
print("\n" + "=" * 70)
print("VERIFICATION POST-REMPLACEMENT")
print("=" * 70)

leftovers = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    if should_skip(dirpath):
        dirnames[:] = []
        continue
    dirnames[:] = [d for d in dirnames if not should_skip(os.path.join(dirpath, d))]
    for fname in filenames:
        ext = os.path.splitext(fname)[1].lower()
        if ext not in EXT:
            continue
        full = os.path.join(dirpath, fname)
        try:
            with open(full, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue
        for old, _ in REPLACEMENTS:
            if old in content:
                n = content.count(old)
                rel = os.path.relpath(full, ROOT)
                leftovers.append((rel, old, n))
                break

if leftovers:
    print(f"  [!!] {len(leftovers)} fichier(s) contiennent ENCORE 'Elonikab'/'elonikab' :")
    for rel, pat, n in leftovers[:20]:
        print(f"     - {rel}  ({pat} x{n})")
else:
    print(f"  [OK] Aucune occurrence de 'Elonikab' residuelle")

# ============================================================
# 5. NOTE COOKIE
# ============================================================
print("\n" + "=" * 70)
print("ATTENTION")
print("=" * 70)
print("""
Le cookie de session a ete renomme :
  elonikab_session -> elonikab_session

=> TOUS les utilisateurs sont DECONNECTES.
   Il faudra se reconnecter avec :
     patient@test.tg   / Test1234
     pharmacien@test.tg / Test1234
     pro@test.tg       / Test1234

[CMD] Restart Uvicorn OBLIGATOIRE :
  taskkill /F /IM uvicorn.exe 2>nul
  taskkill /F /IM python.exe 2>nul
  timeout /t 2
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
""")

print(f"[BACKUP] {bak}")