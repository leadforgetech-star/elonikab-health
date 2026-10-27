"""
rename_app.py - Renomme l'application dans tous les fichiers concernes.

Usage :
    python rename_app.py             # dry-run (aucune ecriture)
    python rename_app.py --commit    # applique les changements

Remplacements :
    'Pharmacie du Parc'  ->  'Elonikab Health'
    'Pharmacie pilote'   ->  'Elonikab Health'
    'Pharmacie Pilote'   ->  'Elonikab Health'
"""
import argparse
import shutil
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent

TARGET_FILES = [
    BASE / "main.py",
    BASE / "static" / "index.html",
    BASE / "static" / "suivi.html",
    BASE / "static" / "pharmacien.html",
    BASE / "static" / "style.css",
    BASE / "static" / "suivi.css",
    BASE / "static" / "pharmacien.css",
    BASE / "static" / "app.js",
    BASE / "static" / "suivi.js",
    BASE / "static" / "pharmacien.js",
]

REPLACEMENTS = [
    ("Pharmacie du Parc", "Elonikab Health"),
    ("Pharmacie Pilote",  "Elonikab Health"),
    ("Pharmacie pilote",  "Elonikab Health"),
    ("PHARMACIE DU PARC", "ELONIKAB HEALTH"),
    ("PHARMACIE PILOTE",  "ELONIKAB HEALTH"),
]

def count_occurrences(text):
    total = 0
    for old, _ in REPLACEMENTS:
        total += text.count(old)
    return total

def apply_replacements(text):
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    return text

def main():
    ap = argparse.ArgumentParser(description="Renomme l'application.")
    ap.add_argument("--commit", action="store_true", help="Applique reellement.")
    args = ap.parse_args()

    print("=" * 55)
    print("RENAME APP -> Elonikab Health")
    print("=" * 55)
    print("Mode :", "COMMIT" if args.commit else "DRY-RUN")
    print()

    backup_dir = BASE / "_backup_rename" / datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.commit:
        backup_dir.mkdir(parents=True, exist_ok=True)
        print("[INFO] Sauvegardes dans :", backup_dir.relative_to(BASE))
        print()

    total_files = 0
    total_repl = 0

    for path in TARGET_FILES:
        if not path.exists():
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print("  [SKIP] " + str(path.relative_to(BASE)) + " (encodage non UTF-8)")
            continue

        n = count_occurrences(original)
        rel = str(path.relative_to(BASE))

        if n == 0:
            print("  [ - ] " + rel + "  (0 occurrence)")
            continue

        total_files += 1
        total_repl += n

        if args.commit:
            shutil.copy2(path, backup_dir / path.name)
            new_text = apply_replacements(original)
            path.write_text(new_text, encoding="utf-8")
            print("  [OK] " + rel + "  (" + str(n) + " remplacement(s))")
        else:
            print("  [DRY] " + rel + "  (" + str(n) + " remplacement(s))")

    print()
    print("=" * 55)
    print("  Fichiers concernes : " + str(total_files))
    print("  Remplacements      : " + str(total_repl))
    print("=" * 55)

    if not args.commit:
        print()
        print("Mode DRY-RUN : aucune ecriture effectuee.")
        print("Pour appliquer : python rename_app.py --commit")
        print()
        print("Apres le commit : Ctrl+Shift+R dans le navigateur.")


if __name__ == "__main__":
    main()