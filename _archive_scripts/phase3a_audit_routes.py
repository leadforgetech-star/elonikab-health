# phase3a_audit_routes.py
# Audit cible : dump du code des 22 routes commandes + config cookie
# NE MODIFIE RIEN
import os, re, sys, datetime

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
MAIN = os.path.join(ROOT, "main.py")
AUTH = os.path.join(ROOT, "v3_modules", "auth.py")
REPORT = os.path.join(ROOT, "phase3a_audit_report.txt")

if not os.path.exists(MAIN):
    print(f"[ERREUR] {MAIN} introuvable"); sys.exit(1)

src = open(MAIN, "r", encoding="utf-8").read()
lines = []
def log(s=""):
    print(s); lines.append(s)

log("=" * 78)
log(f"AUDIT PHASE 3a - {datetime.datetime.now()}")
log(f"Fichier : {MAIN}")
log("=" * 78)

# ============================================================
# 1. Extraire TOUTES les routes /api/orders*
# ============================================================
# Pattern : decorateur + def + corps jusqu'au prochain decorateur @app. ou @router.
route_pat = re.compile(
    r'(@(?:app|router)\.(?:get|post|patch|put|delete)\([^\n]*?\)\s*\n'
    r'(?:@[^\n]*\n)*'
    r'(?:async\s+)?def\s+\w+\s*\([^)]*\)\s*(?:->[^\n:]*)?:'
    r'(?:\n(?:[ \t]+.*)?)*)',
    re.MULTILINE
)

routes = list(route_pat.finditer(src))
order_routes = [m for m in routes if '/api/orders' in m.group(1)[:200]]

log(f"\n[1] {len(order_routes)} routes /api/orders detectees\n")

# Analyse ownership pour chaque route
def analyze_ownership(code):
    checks = {
        "user_id":       bool(re.search(r'user_id\s*==|user\[.id.\]\s*==|\.id\s*==\s*user|current_user\.id', code)),
        "organization":  bool(re.search(r'organization_id', code)),
        "is_pharmacien": bool(re.search(r'PHARMACIEN|pharmacien', code)),
        "is_admin":      bool(re.search(r'ADMIN|admin', code)),
        "require_role":  bool(re.search(r'require_role|Depends\(', code)),
    }
    return checks

for i, m in enumerate(order_routes, 1):
    code = m.group(1)
    # Premiere ligne = decorateur
    first = code.split('\n')[0].strip()
    # Extraire path
    path_m = re.search(r'["\']([^"\']+)["\']', first)
    path = path_m.group(1) if path_m else "?"
    method_m = re.search(r'\.(get|post|patch|put|delete)\(', first)
    method = method_m.group(1).upper() if method_m else "?"

    c = analyze_ownership(code)
    flag = "OK" if (c["user_id"] or c["organization"] or c["is_pharmacien"] or c["is_admin"]) else "!!! NO CHECK !!!"

    log(f"  [{i:2}] {method:<6} {path:<50} {flag}")

# ============================================================
# 2. Dump complet du code des routes SANS ownership
# ============================================================
log("\n" + "=" * 78)
log("[2] CODE COMPLET DES ROUTES SANS CHECK D'OWNERSHIP")
log("=" * 78)

suspects = []
for m in order_routes:
    code = m.group(1)
    c = analyze_ownership(code)
    if not (c["user_id"] or c["organization"] or c["is_pharmacien"] or c["is_admin"]):
        suspects.append(code)

if not suspects:
    log("  (aucune route suspecte detectee)")
else:
    for i, code in enumerate(suspects, 1):
        log(f"\n----- ROUTE SUSPECTE {i}/{len(suspects)} -----")
        log(code.rstrip())

# ============================================================
# 3. Config cookie (SameSite / secure / samesite)
# ============================================================
log("\n" + "=" * 78)
log("[3] CONFIG COOKIE (toutes occurrences)")
log("=" * 78)

for i, line in enumerate(src.split('\n'), 1):
    if re.search(r'set_cookie|SameSite|samesite|SESSION_COOKIE|SESSION_TTL', line):
        log(f"  main.py:{i:<5} {line.strip()}")

if os.path.exists(AUTH):
    auth_src = open(AUTH, "r", encoding="utf-8").read()
    log(f"\n--- v3_modules/auth.py ---")
    for i, line in enumerate(auth_src.split('\n'), 1):
        if re.search(r'set_cookie|SameSite|samesite|SESSION_COOKIE|SESSION_TTL', line):
            log(f"  auth.py:{i:<5} {line.strip()}")

# ============================================================
# 4. Validation next=
# ============================================================
log("\n" + "=" * 78)
log("[4] VALIDATION next= (open redirect)")
log("=" * 78)
for i, line in enumerate(src.split('\n'), 1):
    if 'next' in line.lower() and ('redirect' in line.lower() or 'valid' in line.lower() or 'startswith' in line):
        log(f"  main.py:{i:<5} {line.strip()}")

# ============================================================
# 5. Helpers existants (require_role / get_current_user / can_access)
# ============================================================
log("\n" + "=" * 78)
log("[5] HELPERS AUTH DISPONIBLES")
log("=" * 78)

for label, code in [("main.py", src)] + ([("auth.py", auth_src)] if os.path.exists(AUTH) else []):
    log(f"\n--- {label} ---")
    for i, line in enumerate(code.split('\n'), 1):
        if re.search(r'^\s*def\s+(require_role|get_current_user|can_access|_can|check_)', line):
            log(f"  {label}:{i:<5} {line.strip()}")

# ============================================================
# 6. Ecriture rapport
# ============================================================
with open(REPORT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

log("\n" + "=" * 78)
log(f"[RAPPORT] {REPORT}")
log("=" * 78)
log("\n>>> AUCUNE MODIFICATION. Colle le contenu de phase3a_audit_report.txt.")