"""
fix_recursion.py
Corrige le helper _set_session_cookie qui s'appelle lui-meme.
"""
from pathlib import Path
import re
import shutil

BASE = Path(__file__).resolve().parent
AUTH = BASE / "v3_modules" / "auth.py"

shutil.copy2(AUTH, AUTH.with_suffix(".py.bak"))
print("[OK] Backup ->", AUTH.with_suffix(".py.bak").name)

src = AUTH.read_text(encoding="utf-8")

# Nouveau helper propre
correct_helper = '''def _set_session_cookie(response, token, request):
    """Configure le cookie de session selon le contexte (HTTPS ou HTTP)."""
    is_https = _is_https(request)
    if is_https:
        # Via tunnel/proxy HTTPS : SameSite=None + secure
        response.set_cookie(
            SESSION_COOKIE, token,
            httponly=True, samesite="none", secure=True,
            max_age=SESSION_TTL_DAYS * 86400, path="/"
        )
    else:
        # HTTP local : SameSite=Lax + pas secure
        response.set_cookie(
            SESSION_COOKIE, token,
            httponly=True, samesite="lax", secure=False,
            max_age=SESSION_TTL_DAYS * 86400, path="/"
        )'''

# Remplacer la fonction cassee par la version propre
pattern = re.compile(
    r'def _set_session_cookie\(response, token, request\):.*?(?=\n\ndef |\n\nclass |\Z)',
    re.DOTALL,
)

if pattern.search(src):
    src = pattern.sub(correct_helper + "\n", src, count=1)
    AUTH.write_text(src, encoding="utf-8")
    print("[OK] _set_session_cookie corrige")
else:
    print("[!] _set_session_cookie introuvable")

# Verification
check = AUTH.read_text(encoding="utf-8")
# Compter les appels recursifs
recursive_calls = check.count("_set_session_cookie(response, token, request)")
# Il doit y avoir 2 appels legitimes (dans register et login) + la definition
definitions = check.count("def _set_session_cookie")

print()
print("Verification :")
print(f"  Definitions de _set_session_cookie : {definitions}")
print(f"  Appels a _set_session_cookie       : {recursive_calls}")

if definitions == 1 and recursive_calls == 2:
    print("[OK] Le fix est correct.")
elif definitions == 1 and recursive_calls > 2:
    print("[!] Il reste des appels recursifs.")
    print("    Verifie manuellement auth.py autour de la ligne 51.")
else:
    print("[i] Verifie le fichier")

print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print("  Puis recharge la page d'inscription et refais le test.")