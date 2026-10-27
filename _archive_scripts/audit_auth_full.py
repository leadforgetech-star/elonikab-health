"""
audit_auth_full.py
Audit complet : auth, sessions, roles, permissions, ownership.
AUCUNE modification. Lecture seule.
"""
import re
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
MODULES = BASE / "v3_modules"
AUTH = MODULES / "auth.py"
DB = BASE / "database.db"


def sec(title):
    print()
    print("=" * 74)
    print(" " + title)
    print("=" * 74)
    print()


# ============================================================
# 1. TABLES + SCHEMA
# ============================================================
sec("1. TABLES ET SCHEMA")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

tables = [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()]

print(f"  {len(tables)} tables :")
for t in tables:
    try:
        n = conn.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
        print(f"    {t:30s} {n:>6} lignes")
    except Exception:
        print(f"    {t:30s} ???")

# Détail des tables sensibles
for t in ("users", "sessions", "professional_profiles", "orders"):
    if t not in tables:
        continue
    print(f"\n  Schema '{t}' :")
    for c in conn.execute(f"PRAGMA table_info({t})").fetchall():
        default = c[4] if c[4] is not None else ""
        notnull = "NOT NULL" if c[3] else ""
        print(f"    {c[1]:30s} {c[2]:12s} {notnull} {default}")

# ============================================================
# 2. ROLES UTILISES
# ============================================================
sec("2. ROLES EN BASE")

try:
    rows = conn.execute(
        "SELECT role, COUNT(*) AS n FROM users GROUP BY role ORDER BY n DESC"
    ).fetchall()
    for r in rows:
        print(f"    {r['role']:20s} {r['n']:>5} utilisateurs")
except Exception as e:
    print("  Erreur :", e)

# ============================================================
# 3. RELATION USER <-> ORGANISATION
# ============================================================
sec("3. RELATION USER <-> ETABLISSEMENT")

print("  users.organization_id :")
try:
    rows = conn.execute("""
        SELECT u.id, u.email, u.role, u.organization_id,
               p.structure_name
        FROM users u
        LEFT JOIN professional_profiles p ON p.id = u.organization_id
        WHERE u.role IN ('PROFESSIONNEL', 'PHARMACIEN', 'ADMIN')
        ORDER BY u.id LIMIT 20
    """).fetchall()
    for r in rows:
        org = r["organization_id"] or "—"
        name = r["structure_name"] or "(pas de structure)"
        print(f"    user {r['id']:>3} {r['email']:30s} {r['role']:15s} org={org} {name}")
except Exception as e:
    print("  Erreur :", e)

# ============================================================
# 4. OWNERSHIP : commandes et organisation
# ============================================================
sec("4. OWNERSHIP DES COMMANDES")

try:
    rows = conn.execute("""
        SELECT o.id, o.reference, o.user_id, o.professional_id,
               o.customer_type, o.created_at
        FROM orders o
        ORDER BY o.id DESC LIMIT 10
    """).fetchall()
    print(f"  10 dernieres commandes :")
    for r in rows:
        print(f"    {r['reference']:22s} user={r['user_id']} "
              f"prof={r['professional_id']} type={r['customer_type']}")
except Exception as e:
    print("  Erreur :", e)

# ============================================================
# 5. ROUTES D'AUTHENTIFICATION
# ============================================================
sec("5. ROUTES AUTH DANS main.py + auth.py")

for path, name in ((MAIN, "main.py"), (AUTH, "v3_modules/auth.py")):
    if not path.exists():
        print(f"  [!] {name} introuvable")
        continue
    src = path.read_text(encoding="utf-8")
    print(f"\n  --- {name} ---")
    routes = re.findall(
        r'@app\.(get|post|patch|delete|api_route)\("(/api/auth[^"]*|/[^"]*acces[^"]*|[^"]*connexion[^"]*|[^"]*inscription[^"]*|[^"]*logout[^"]*)"',
        src
    )
    if routes:
        for m, p in routes:
            print(f"    {m.upper():10s} {p}")
    else:
        print("    (aucune route auth detectee)")

# ============================================================
# 6. MIDDLEWARES / DEPENDENCIES
# ============================================================
sec("6. MIDDLEWARES / DEPENDENCIES")

if AUTH.exists():
    src = AUTH.read_text(encoding="utf-8")
    for m in ("require_role", "get_current_user", "SESSION_COOKIE", "SESSION_TTL_DAYS",
              "valid_roles", "VALID_ROLES", "hash_password", "verify_password"):
        count = src.count(m)
        print(f"  {m:30s} {count}x")
else:
    print("  [!] auth.py introuvable")

# ============================================================
# 7. VERIFICATION OWNERSHIP DANS LES ROUTES
# ============================================================
sec("7. VERIFICATION OWNERSHIP (analyse statique)")

src = MAIN.read_text(encoding="utf-8")
if MODULES.exists():
    for f in MODULES.glob("*.py"):
        src += "\n" + f.read_text(encoding="utf-8")

# Chercher les routes qui retournent des orders
order_routes = re.findall(
    r'@app\.(?:get|post|patch|delete)\("(/api/orders[^"]*)"',
    src
)
print(f"  {len(order_routes)} routes touchant les commandes :")
for r in set(order_routes):
    print(f"    {r}")

# Chercher les vérifications organization_id
checks = [
    ("WHERE user_id = ?", "Verifie l'appartenance par user_id"),
    ("WHERE organization_id = ?", "Verifie l'appartenance par organization_id"),
    ("WHERE reference = ? AND user_id = ?", "Verifie ref + user_id"),
]
print(f"\n  Verifications ownership dans le code :")
for pattern, desc in checks:
    n = src.count(pattern)
    marker = "OK" if n > 0 else "[!]"
    print(f"    {marker} {desc:45s} {n}x")

# ============================================================
# 8. LOGIN / REGISTER : REDIRECTIONS
# ============================================================
sec("8. REDIRECTIONS POST-LOGIN DANS LE CODE")

redirs = re.findall(
    r'window\.location(?:\.replace|\.href)?\s*=\s*["\']([^"\']+)["\']',
    (BASE / "static" / "auth.js").read_text(encoding="utf-8")
    if (BASE / "static" / "auth.js").exists() else ""
)
print("  auth.js :")
for r in redirs[:10]:
    print(f"    -> {r}")

# Redirect dans main.py (login route)
login_redirect = re.search(
    r'@app\.post\("/api/auth/login"\).*?(?=@app\.|\Z)',
    src, re.DOTALL
)
if login_redirect:
    print("\n  Route /api/auth/login (extrait) :")
    print("  " + login_redirect.group(0)[:300].replace("\n", "\n  "))

# ============================================================
# 9. OPEN REDIRECT : next= non validé ?
# ============================================================
sec("9. VERIFICATION next= (OPEN REDIRECT)")

has_next_check = (
    "startswith('/')" in src or
    "startswith(\"/\")" in src or
    "//" in src and "next" in src
)
print(f"  Validation de next= : {'PRESENTE' if has_next_check else 'ABSENTE [!]'}")
print()
print("  Si absent : un attaquant peut faire")
print("    /connexion?next=https://site-malveillant.com")
print("  et l'utilisateur finit redirige vers le site malveillant.")

# ============================================================
# 10. STATUT ACTUEL DES POINTS CRITIQUES
# ============================================================
sec("10. STATUT DES 5 POINTS CRITIQUES")

# 1. Cookie secure/samesite
auth_src = AUTH.read_text(encoding="utf-8") if AUTH.exists() else ""
samesite = re.findall(r'samesite\s*=\s*"([^"]+)"', auth_src)
secure = "secure=True" in auth_src
print(f"  1. Cookie SameSite : {set(samesite) or 'non defini'}")
print(f"     Cookie Secure   : {secure}")

# 2. Session TTL
ttl = re.search(r'SESSION_TTL_DAYS\s*=\s*(\d+)', auth_src)
print(f"  2. Session TTL      : {ttl.group(1) if ttl else '?'} jours")

# 3. Roles valides
valid_roles = re.search(
    r'VALID_ROLES\s*=\s*\{([^}]+)\}', auth_src, re.DOTALL
)
print(f"  3. Roles valides    : {valid_roles.group(1).strip()[:80] if valid_roles else '?'}")

# 4. Ownership des commandes
has_org_check = "organization_id" in src and "WHERE organization_id" in src
print(f"  4. Ownership org    : {'OK' if has_org_check else 'A AJOUTER [!]'}")

# 5. Route / avec redirection
has_smart_root = "root_page" in src or "redirect_role" in src
print(f"  5. Route / intelligente : {'OK' if has_smart_root else 'A CREER [!]'}")

conn.close()

# ============================================================
# RESUME
# ============================================================
sec("RESUME")

print("""
  Cet audit ne modifie RIEN. Il montre l'etat actuel.
  Partage-le au superviseur pour valider la Phase 2.
""")