# phase3a_fix.py
# Phase 3a : AuthN/AuthZ - helpers exportables + patch 3 routes main.py
import os, re, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
AUTH = os.path.join(ROOT, "v3_modules", "auth.py")
MAIN = os.path.join(ROOT, "main.py")

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
bak = os.path.join(ROOT, f"_backup_phase3a_{ts}")
os.makedirs(bak, exist_ok=True)
shutil.copy2(AUTH, os.path.join(bak, "auth.py.bak"))
shutil.copy2(MAIN, os.path.join(bak, "main.py.bak"))
print(f"[BACKUP] {bak}")

# ============================================================
# 1) PATCH auth.py - helpers exportables (SANS toucher install_auth)
# ============================================================
auth_src = open(AUTH, "r", encoding="utf-8").read()

if "def can_access_order" in auth_src:
    print("[SKIP] auth.py deja patché")
else:
    HELPERS = '''

# ============================================================
# PHASE 3a - Helpers exportables (utilisables depuis main.py)
# ============================================================

def public_user(row):
    """Retourne dict user sans password_hash (ou None)."""
    if row is None:
        return None
    try:
        d = {k: row[k] for k in row.keys()}
    except Exception:
        d = dict(row)
    d.pop("password_hash", None)
    return d


def load_user_from_cookie(get_db, session_token):
    """Charge la ligne user via session_token (ou None)."""
    if not session_token:
        return None
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id"
            " WHERE s.token = ? AND s.expires_at > ?",
            (session_token, datetime.now().isoformat(timespec="seconds")),
        ).fetchone()
        return row
    finally:
        conn.close()


def make_current_user_dep(get_db):
    """Retourne un dependency FastAPI qui expose le user (dict) ou None."""
    def dep(session_token: Optional[str] = Cookie(None, alias=SESSION_COOKIE)):
        row = load_user_from_cookie(get_db, session_token)
        return public_user(row)
    return dep


def can_access_order(user, order):
    """Verifie que user peut lire/modifier order.

    Regles :
    - PHARMACIEN / ADMIN : acces total
    - Proprietaire direct (order.user_id == user.id)
    - Meme organisation (order.organization_id ou order.professional_id == user.organization_id)
    """
    if not user or not order:
        return False
    role = user.get("role")
    if role in ("PHARMACIEN", "ADMIN"):
        return True
    try:
        uid = user.get("id")
        o_uid = order.get("user_id")
        if uid and o_uid and int(uid) == int(o_uid):
            return True
        u_org = user.get("organization_id")
        if u_org:
            for k in ("organization_id", "professional_id"):
                o_val = order.get(k)
                if o_val and int(u_org) == int(o_val):
                    return True
    except Exception:
        pass
    return False
'''
    auth_src = auth_src.rstrip() + HELPERS + "\n"
    open(AUTH, "w", encoding="utf-8").write(auth_src)
    print("[OK] auth.py : 4 helpers ajoutes")

# ============================================================
# 2) PATCH main.py
# ============================================================
main_src = open(MAIN, "r", encoding="utf-8").read()

# 2a) Ajouter Depends a l'import fastapi
OLD_IMPORT = "from fastapi import Cookie, FastAPI, File, Form, HTTPException, Request, UploadFile"
NEW_IMPORT = "from fastapi import Cookie, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile"
if "Depends" in main_src.split('\n')[7]:
    print("[SKIP] Depends deja importe")
elif OLD_IMPORT in main_src:
    main_src = main_src.replace(OLD_IMPORT, NEW_IMPORT, 1)
    print("[OK] main.py : Depends importe")
else:
    print("[!] Import fastapi introuvable")

# 2b) Apres row_to_dict() : bootstrap du dep + can_access_order wrapper
MARKER = "def row_to_dict(row):\n    return {key: row[key] for key in row.keys()}"
BOOTSTRAP = MARKER + '''


# --- PHASE 3a : deps auth pour routes non protegees ---
from v3_modules.auth import make_current_user_dep, can_access_order as _can_access_order
get_current_user_dep = make_current_user_dep(get_db)


def can_access_order(user, order_row):
    """Wrapper : accepte sqlite3.Row ou dict, verifie ownership."""
    if isinstance(order_row, dict):
        order = order_row
    else:
        order = row_to_dict(order_row)
    return _can_access_order(user, order)
'''
if "get_current_user_dep = make_current_user_dep" not in main_src:
    main_src = main_src.replace(MARKER, BOOTSTRAP, 1)
    print("[OK] main.py : bootstrap dep insere")
else:
    print("[SKIP] bootstrap dep deja present")

# 2c) Patch GET /api/orders
OLD_LIST = '''@app.get("/api/orders")
def list_orders():
    conn = get_db()
    rows = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 100").fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]'''

NEW_LIST = '''@app.get("/api/orders")
def list_orders(user = Depends(get_current_user_dep)):
    if not user:
        raise HTTPException(401, "Non authentifie")
    role = user["role"]
    conn = get_db()
    if role in ("PHARMACIEN", "ADMIN"):
        rows = conn.execute(
            "SELECT * FROM orders ORDER BY id DESC LIMIT 100"
        ).fetchall()
    elif role == "PROFESSIONNEL":
        org = user.get("organization_id")
        if org:
            rows = conn.execute(
                "SELECT * FROM orders WHERE user_id = ?"
                " OR organization_id = ? OR professional_id = ?"
                " ORDER BY id DESC LIMIT 100",
                (user["id"], org, org)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM orders WHERE user_id = ?"
                " ORDER BY id DESC LIMIT 100",
                (user["id"],)
            ).fetchall()
    else:  # PATIENT
        rows = conn.execute(
            "SELECT * FROM orders WHERE user_id = ?"
            " ORDER BY id DESC LIMIT 100",
            (user["id"],)
        ).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]'''

if OLD_LIST in main_src:
    main_src = main_src.replace(OLD_LIST, NEW_LIST, 1)
    print("[OK] main.py : GET /api/orders patche")
else:
    print("[!] GET /api/orders introuvable ou deja patche")

# 2d) Patch GET /api/orders/{reference}
OLD_GET = '''@app.get("/api/orders/{reference}")
def get_order(reference: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE reference = ?", (reference,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    return row_to_dict(row)'''

NEW_GET = '''@app.get("/api/orders/{reference}")
def get_order(reference: str, user = Depends(get_current_user_dep)):
    if not user:
        raise HTTPException(401, "Non authentifie")
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE reference = ?", (reference,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if not can_access_order(user, row):
        raise HTTPException(403, "Acces refuse a cette commande")
    return row_to_dict(row)'''

if OLD_GET in main_src:
    main_src = main_src.replace(OLD_GET, NEW_GET, 1)
    print("[OK] main.py : GET /api/orders/{reference} patche")
else:
    print("[!] GET /api/orders/{reference} introuvable ou deja patche")

# 2e) Patch PATCH /status signature (fix NameError 'user')
OLD_PATCH = '''@app.patch("/api/orders/{reference}/status")
def update_order_status(reference: str, payload: StatusUpdate):
    new_status = payload.status.strip().lower()
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Statut invalide")

    conn = get_db()'''

NEW_PATCH = '''@app.patch("/api/orders/{reference}/status")
def update_order_status(
    reference: str,
    payload: StatusUpdate,
    user = Depends(get_current_user_dep),
):
    if not user or user["role"] not in ("PHARMACIEN", "ADMIN"):
        raise HTTPException(403, "Seul le pharmacien peut changer le statut")
    new_status = payload.status.strip().lower()
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Statut invalide")

    conn = get_db()'''

if OLD_PATCH in main_src:
    main_src = main_src.replace(OLD_PATCH, NEW_PATCH, 1)
    print("[OK] main.py : PATCH /status fix NameError + role check")
else:
    print("[!] PATCH /status signature introuvable")

open(MAIN, "w", encoding="utf-8").write(main_src)

# ============================================================
# 3) VERIFICATION
# ============================================================
print("\n[VERIF]")
check = open(MAIN, "r", encoding="utf-8").read()
check_auth = open(AUTH, "r", encoding="utf-8").read()

print(f"  Depends importe              : {'Depends' in check.split(chr(10))[7]}")
print(f"  bootstrap dep                : {'get_current_user_dep = make_current_user_dep' in check}")
print(f"  list_orders protege          : {'def list_orders(user = Depends' in check}")
print(f"  get_order protege            : {'def get_order(reference: str, user = Depends' in check}")
print(f"  PATCH /status role check     : 'PHARMACIEN\", \"ADMIN\"' in PATCH" if False else f"  PATCH /status role check     : {'Seul le pharmacien peut changer le statut' in check}")
print(f"  can_access_order (auth.py)   : {'def can_access_order' in check_auth}")
print(f"  make_current_user_dep        : {'def make_current_user_dep' in check_auth}")
print(f"  public_user (auth.py)        : {'def public_user' in check_auth}")

# Test import runtime
sys.path.insert(0, ROOT)
try:
    import importlib, v3_modules.auth as A
    importlib.reload(A)
    print(f"\n  [runtime] A.can_access_order   = {hasattr(A, 'can_access_order')}")
    print(f"  [runtime] A.make_current_user_dep = {hasattr(A, 'make_current_user_dep')}")
except Exception as e:
    print(f"\n  [runtime ERREUR] {type(e).__name__}: {e}")

print("\n[DONE] Phase 3a appliquee. Uvicorn --reload va recharger.")
print("[INFO] Si erreur import : uvicorn --reload affichera la trace.")