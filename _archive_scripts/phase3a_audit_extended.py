# phase3a_audit_extended.py
# Audit etendu : toutes les routes /api/orders* dans v3_modules/ + validation next= dans static/
# NE MODIFIE RIEN
import os, re, sys, datetime

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
V3   = os.path.join(ROOT, "v3_modules")
STATIC = os.path.join(ROOT, "static")
REPORT = os.path.join(ROOT, "phase3a_audit_extended.txt")

lines = []
def log(s=""):
    print(s); lines.append(s)

log("=" * 78)
log(f"AUDIT PHASE 3a ETENDU - {datetime.datetime.now()}")
log("=" * 78)

# ============================================================
# 1. Scanner TOUS les .py dans v3_modules + main.py
# ============================================================
files_to_scan = [("main.py", os.path.join(ROOT, "main.py"))]
if os.path.isdir(V3):
    for f in sorted(os.listdir(V3)):
        if f.endswith(".py") and not f.startswith("_"):
            files_to_scan.append((f"v3_modules/{f}", os.path.join(V3, f)))

route_pat = re.compile(
    r'(@(?:app|router)\.(?:get|post|patch|put|delete)\([^\n]*?\)\s*\n'
    r'(?:@[^\n]*\n)*'
    r'(?:async\s+)?def\s+\w+\s*\([^)]*\)\s*(?:->[^\n:]*)?:'
    r'(?:\n(?:[ \t]+.*)?)*)',
    re.MULTILINE
)

order_routes = []  # (file, code)

for label, path in files_to_scan:
    if not os.path.exists(path):
        continue
    src = open(path, "r", encoding="utf-8").read()
    for m in route_pat.finditer(src):
        code = m.group(1)
        first = code.split('\n')[0]
        if '/api/orders' in first:
            order_routes.append((label, code))

log(f"\n[1] {len(order_routes)} routes /api/orders detectees\n")

# Analyse ownership
def analyze_ownership(code):
    return {
        "user_id":       bool(re.search(r'user\["id"\]|user\[.id.\]|current_user|user_id\s*==', code)),
        "organization":  bool(re.search(r'organization_id', code)),
        "is_pharmacien": bool(re.search(r'PHARMACIEN', code)),
        "is_admin":      bool(re.search(r'ADMIN', code)),
        "require_role":  bool(re.search(r'require_role|Depends\(', code)),
        "has_user_param":bool(re.search(r'\buser\b\s*[:=]|=\s*Depends', code)),
    }

suspects = []
ok_routes = []
for label, code in order_routes:
    first = code.split('\n')[0]
    path_m = re.search(r'["\']([^"\']+)["\']', first)
    path = path_m.group(1) if path_m else "?"
    method_m = re.search(r'\.(get|post|patch|put|delete)\(', first)
    method = method_m.group(1).upper() if method_m else "?"

    c = analyze_ownership(code)
    has_any = c["user_id"] or c["organization"] or c["is_pharmacien"] or c["is_admin"] or c["require_role"]
    flag = "OK" if has_any else "!!! NO CHECK !!!"

    entry = f"  [{label:<28}] {method:<6} {path:<52} {flag}"
    log(entry)
    if has_any:
        ok_routes.append((label, method, path))
    else:
        suspects.append((label, method, path, code))

# ============================================================
# 2. Code des routes SANS check
# ============================================================
log("\n" + "=" * 78)
log(f"[2] CODE DES {len(suspects)} ROUTES SANS CHECK")
log("=" * 78)
for i, (label, method, path, code) in enumerate(suspects, 1):
    log(f"\n----- [{i}/{len(suspects)}] {method} {path}  ({label}) -----")
    log(code.rstrip())

# ============================================================
# 3. Validation next= dans static/ (JS)
# ============================================================
log("\n" + "=" * 78)
log("[3] VALIDATION next= DANS static/*.js")
log("=" * 78)
if os.path.isdir(STATIC):
    for f in sorted(os.listdir(STATIC)):
        if f.endswith(".js"):
            p = os.path.join(STATIC, f)
            try:
                js = open(p, "r", encoding="utf-8").read()
            except Exception:
                continue
            for i, line in enumerate(js.split('\n'), 1):
                if re.search(r'next\s*[=:]|location\.href|window\.location', line):
                    if 'next' in line.lower():
                        log(f"  {f}:{i:<5} {line.strip()[:120]}")

# ============================================================
# 4. set_cookie / delete_cookie dans tous les modules
# ============================================================
log("\n" + "=" * 78)
log("[4] TOUTES LES OCCURRENCES set_cookie / delete_cookie")
log("=" * 78)
for label, path in files_to_scan:
    if not os.path.exists(path):
        continue
    src = open(path, "r", encoding="utf-8").read()
    for i, line in enumerate(src.split('\n'), 1):
        if re.search(r'set_cookie|delete_cookie', line):
            log(f"  {label}:{i:<5} {line.strip()}")

# ============================================================
# 5. Ou est defini get_current_user + require_role
# ============================================================
log("\n" + "=" * 78)
log("[5] OU SONT DEFINIS LES HELPERS")
log("=" * 78)
for label, path in files_to_scan:
    if not os.path.exists(path):
        continue
    src = open(path, "r", encoding="utf-8").read()
    for i, line in enumerate(src.split('\n'), 1):
        if re.search(r'^\s*def\s+(get_current_user|require_role|require_permission|can_access)', line):
            log(f"  {label}:{i:<5} {line.strip()}")

# ============================================================
# 6. IMPORT de get_current_user dans main.py
# ============================================================
log("\n" + "=" * 78)
log("[6] IMPORTS get_current_user DANS main.py")
log("=" * 78)
main_src = open(os.path.join(ROOT, "main.py"), "r", encoding="utf-8").read()
for i, line in enumerate(main_src.split('\n'), 1):
    if re.search(r'get_current_user|require_role|from v3_modules', line):
        log(f"  main.py:{i:<5} {line.strip()}")

# ============================================================
# 7. Ecriture rapport
# ============================================================
with open(REPORT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

log("\n" + "=" * 78)
log(f"[RAPPORT] {REPORT}")
log("=" * 78)
log("\n>>> AUCUNE MODIFICATION. Colle le contenu du rapport.")