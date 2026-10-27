# phase3b_fix.py
# Phase 3b : fix auth.py (org_id) + protege /professionnel + dump login.js
import os, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
AUTH = os.path.join(ROOT, "v3_modules", "auth.py")
MAIN = os.path.join(ROOT, "main.py")
STATIC = os.path.join(ROOT, "static")
LOGIN_JS = os.path.join(STATIC, "login.js")
DUMP = os.path.join(ROOT, "phase3b_login_js_dump.txt")

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
bak = os.path.join(ROOT, f"_backup_phase3b_{ts}")
os.makedirs(bak, exist_ok=True)
shutil.copy2(AUTH, os.path.join(bak, "auth.py.bak"))
shutil.copy2(MAIN, os.path.join(bak, "main.py.bak"))
print(f"[BACKUP] {bak}")

# ============================================================
# 1) FIX auth.py : lier user a organization_id
# ============================================================
auth_src = open(AUTH, "r", encoding="utf-8").read()

OLD_BLOCK = '''                conn.execute(
                    "INSERT INTO professional_profiles"
                    " (user_id, structure_name, structure_type, manager_name,"
                    "  phone, email, address, status, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, 'APPROVED', ?)",
                    (user_id, sname, stype, sresp,
                     payload.phone.strip(), email, scity, now),
                )'''

NEW_BLOCK = '''                cur2 = conn.execute(
                    "INSERT INTO professional_profiles"
                    " (user_id, structure_name, structure_type, manager_name,"
                    "  phone, email, address, status, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, 'APPROVED', ?)",
                    (user_id, sname, stype, sresp,
                     payload.phone.strip(), email, scity, now),
                )
                # Phase 3b : lier l'utilisateur a son etablissement
                conn.execute(
                    "UPDATE users SET organization_id = ? WHERE id = ?",
                    (cur2.lastrowid, user_id),
                )'''

if "cur2.lastrowid, user_id" in auth_src:
    print("[SKIP] auth.py : fix org_id deja applique")
elif OLD_BLOCK in auth_src:
    auth_src = auth_src.replace(OLD_BLOCK, NEW_BLOCK, 1)
    open(AUTH, "w", encoding="utf-8").write(auth_src)
    print("[OK] auth.py : organization_id lie apres INSERT profil")
else:
    print("[!] auth.py : bloc INSERT professional_profiles introuvable")

# ============================================================
# 2) PROTECTION route /professionnel dans main.py
# ============================================================
main_src = open(MAIN, "r", encoding="utf-8").read()

OLD_PRO = '''@app.api_route("/professionnel", methods=["GET", "HEAD"], include_in_schema=False)
def page_professionnel():
    return FileResponse(STATIC_DIR / "professional.html")'''

NEW_PRO = '''@app.api_route("/professionnel", methods=["GET", "HEAD"], include_in_schema=False)
def page_professionnel(request: Request):
    # Phase 3b : acces protege + redirection si profil incomplet
    from v3_modules.auth import SESSION_COOKIE, load_user_from_cookie
    token = request.cookies.get(SESSION_COOKIE)
    row = load_user_from_cookie(get_db, token)
    if row is None:
        return RedirectResponse(url="/connexion?next=/professionnel", status_code=302)
    role = row["role"]
    if role != "PROFESSIONNEL":
        return RedirectResponse(url="/", status_code=302)
    if not row["organization_id"]:
        return RedirectResponse(url="/professionnel/etablissement", status_code=302)
    return FileResponse(STATIC_DIR / "professional.html")'''

if "def page_professionnel(request: Request):" in main_src:
    print("[SKIP] main.py : /professionnel deja protege")
elif OLD_PRO in main_src:
    main_src = main_src.replace(OLD_PRO, NEW_PRO, 1)
    open(MAIN, "w", encoding="utf-8").write(main_src)
    print("[OK] main.py : /professionnel protege")
else:
    print("[!] main.py : route /professionnel introuvable")

# ============================================================
# 3) DUMP login.js
# ============================================================
out = []
if os.path.exists(LOGIN_JS):
    with open(LOGIN_JS, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            out.append(f"{i:4}  {line.rstrip()}")
    with open(DUMP, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"[DUMP] {DUMP}")
    print("---- login.js (extrait 60 lignes) ----")
    print("\n".join(out[:60]))
    print("---- /extrait ----")
else:
    print(f"[!] {LOGIN_JS} absent")

# ============================================================
# 4) VERIF
# ============================================================
print("\n[VERIF]")
a = open(AUTH, "r", encoding="utf-8").read()
m = open(MAIN, "r", encoding="utf-8").read()
print(f"  auth.py fix org_id             : {'cur2.lastrowid, user_id' in a}")
print(f"  main.py /professionnel protege : {'def page_professionnel(request: Request):' in m}")
print(f"  RedirectResponse import        : {'RedirectResponse' in m.split(chr(10))[8]}")

# Test import runtime
sys.path.insert(0, ROOT)
try:
    import importlib, v3_modules.auth as A
    importlib.reload(A)
    print(f"  [runtime] A.load_user_from_cookie = {hasattr(A, 'load_user_from_cookie')}")
except Exception as e:
    print(f"  [runtime ERREUR] {type(e).__name__}: {e}")

print("\n[DONE] Phase 3b appliquee. Uvicorn --reload va recharger.")