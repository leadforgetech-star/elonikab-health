"""
fix_cookie_adaptive.py
Cookie adaptatif : secure=True si HTTPS, secure=False si HTTP.
Detecte via X-Forwarded-Proto (envoye par Cloudflare Tunnel).
"""
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent
AUTH = BASE / "v3_modules" / "auth.py"

shutil.copy2(AUTH, AUTH.with_suffix(".py.bak"))
print("[OK] Backup ->", AUTH.with_suffix(".py.bak").name)

src = AUTH.read_text(encoding="utf-8")

# 1. Verifier que Request est importe
if "from fastapi import Cookie, HTTPException, Response" in src:
    src = src.replace(
        "from fastapi import Cookie, HTTPException, Response",
        "from fastapi import Cookie, HTTPException, Request, Response",
        1,
    )
    print("[OK] import Request ajoute")
elif "Request" not in src.split("from fastapi import")[1].split("\n")[0]:
    src = src.replace(
        "from fastapi import Cookie, HTTPException, Response",
        "from fastapi import Cookie, HTTPException, Request, Response",
        1,
    )

# 2. Ajouter la fonction helper pour detecter HTTPS
helper = '''

def _is_https(request):
    """Detecte si la requete arrive via HTTPS (direct ou via tunnel/proxy)."""
    try:
        if request.url.scheme == "https":
            return True
        # Cloudflare envoie X-Forwarded-Proto
        proto = request.headers.get("x-forwarded-proto", "")
        if proto.lower() == "https":
            return True
        # Header Cloudflare specifique
        cf_visitor = request.headers.get("cf-visitor", "")
        if "https" in cf_visitor.lower():
            return True
    except Exception:
        pass
    return False


def _set_session_cookie(response, token, request):
    """Configure le cookie de session selon le contexte (HTTPS ou HTTP)."""
    is_https = _is_https(request)
    if is_https:
        # Via tunnel/proxy HTTPS : SameSite=None + secure (necessaire)
        response.set_cookie(
            SESSION_COOKIE, token,
            httponly=True, samesite="none", secure=True,
            max_age=SESSION_TTL_DAYS * 86400, path="/"
        )
    else:
        # HTTP local : SameSite=Lax + pas secure (compatible)
        response.set_cookie(
            SESSION_COOKIE, token,
            httponly=True, samesite="lax", secure=False,
            max_age=SESSION_TTL_DAYS * 86400, path="/"
        )
'''

if "_is_https" not in src:
    # Inserer apres les constantes, avant la premiere fonction
    anchor = "def hash_password"
    if anchor in src:
        src = src.replace(anchor, helper + "\n\n" + anchor, 1)
        print("[OK] helper _is_https + _set_session_cookie ajoute")

# 3. Remplacer les 2 blocs de set_cookie par l'appel au helper
old_cookie1 = '''        response.set_cookie(
            SESSION_COOKIE, token,
            httponly=True, samesite="none", secure=True,
            max_age=SESSION_TTL_DAYS * 86400, path="/"
        )'''
new_cookie = '''        _set_session_cookie(response, token, request)'''

count = src.count(old_cookie1)
if count > 0:
    src = src.replace(old_cookie1, new_cookie)
    print(f"[OK] {count} bloc(s) set_cookie remplaces")

# 4. Ajouter le parametre 'request: Request' aux fonctions login et register
old_sig_register = '''    def register(payload: RegisterRequest, response: Response):'''
new_sig_register = '''    def register(payload: RegisterRequest, response: Response, request: Request):'''
if old_sig_register in src:
    src = src.replace(old_sig_register, new_sig_register, 1)
    print("[OK] register -> request ajoute")

old_sig_login = '''    def login(payload: LoginRequest, response: Response):'''
new_sig_login = '''    def login(payload: LoginRequest, response: Response, request: Request):'''
if old_sig_login in src:
    src = src.replace(old_sig_login, new_sig_login, 1)
    print("[OK] login -> request ajoute")

AUTH.write_text(src, encoding="utf-8")

# Verification
check = AUTH.read_text(encoding="utf-8")
if "_set_session_cookie(response, token, request)" in check:
    print("[OK] Fix applique")
else:
    print("[!] Le remplacement a echoue")

if "def register(payload: RegisterRequest, response: Response, request: Request)" in check:
    print("[OK] register signature OK")
if "def login(payload: LoginRequest, response: Response, request: Request)" in check:
    print("[OK] login signature OK")

print()
print("=" * 60)
print("COOKIE ADAPTATIF APPLIQUE")
print("=" * 60)
print()
print("Comportement :")
print("  - Local HTTP    -> SameSite=Lax, secure=False (fonctionne)")
print("  - Tunnel HTTPS  -> SameSite=None, secure=True (fonctionne)")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print("  python test_pro_e2e.py")