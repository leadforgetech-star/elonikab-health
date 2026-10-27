# phase3b_dump_register.py - dump du flux inscription actuel
# NE MODIFIE RIEN
import os

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
STATIC = os.path.join(ROOT, "static")
REPORT = os.path.join(ROOT, "phase3b_dump_register.txt")

TARGETS = ["register.html", "register.js", "auth.js", "login.html"]

out = []
def log(s=""):
    print(s); out.append(s)

for name in TARGETS:
    p = os.path.join(STATIC, name)
    log("=" * 78)
    log(f"FICHIER: {name}  (existe: {os.path.exists(p)})")
    log("=" * 78)
    if not os.path.exists(p):
        log("  (absent)\n")
        continue
    with open(p, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            log(f"{i:4}  {line.rstrip()}")
    log("")

# Extra : cherche le code exact de register() dans auth.py
AUTH = os.path.join(ROOT, "v3_modules", "auth.py")
log("=" * 78)
log(f"[EXTRA] auth.py — bloc register() lignes 183-245")
log("=" * 78)
with open(AUTH, "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines[182:245], 183):
    log(f"{i:4}  {line.rstrip()}")

with open(REPORT, "w", encoding="utf-8") as f:
    f.write("\n".join(out))

log(f"\n[RAPPORT] {REPORT}")
log(">>> AUCUNE MODIFICATION. Colle le rapport complet.")