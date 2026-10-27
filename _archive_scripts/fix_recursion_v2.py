"""
fix_recursion_v2.py
Corrige _set_session_cookie par manipulation ligne par ligne.
"""
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent
AUTH = BASE / "v3_modules" / "auth.py"

shutil.copy2(AUTH, AUTH.with_suffix(".py.bak"))
print("[OK] Backup ->", AUTH.with_suffix(".py.bak").name)

lines = AUTH.read_text(encoding="utf-8").splitlines()

# Trouver les indices de la fonction _set_session_cookie
start = None
end = None
for i, line in enumerate(lines):
    if line.startswith("def _set_session_cookie("):
        start = i
        continue
    if start is not None and end is None:
        # La fin est la premiere ligne non-indentee qui suit (hors ligne vide)
        if line and not line.startswith(" ") and not line.startswith("\t"):
            end = i
            break

if start is None:
    print("[!] _set_session_cookie introuvable")
    raise SystemExit(1)

if end is None:
    end = len(lines)

print(f"[i] Fonction trouvee : lignes {start+1} a {end}")

# Afficher l'ancien contenu pour debug
print("[i] Ancien contenu :")
for i in range(start, min(end, start + 12)):
    print(f"    {i+1}: {lines[i]}")

# Nouveau bloc correct
new_block = [
    "def _set_session_cookie(response, token, request):",
    '    """Configure le cookie de session selon HTTPS ou HTTP."""',
    "    is_https = _is_https(request)",
    "    if is_https:",
    "        response.set_cookie(",
    "            SESSION_COOKIE, token,",
    '            httponly=True, samesite="none", secure=True,',
    "            max_age=SESSION_TTL_DAYS * 86400, path=\"/\"",
    "        )",
    "    else:",
    "        response.set_cookie(",
    "            SESSION_COOKIE, token,",
    '            httponly=True, samesite="lax", secure=False,',
    "            max_age=SESSION_TTL_DAYS * 86400, path=\"/\"",
    "        )",
    "",
]

# Reconstruire le fichier
new_lines = lines[:start] + new_block + lines[end:]
AUTH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
print("[OK] _set_session_cookie remplace")

# Verifications
result = AUTH.read_text(encoding="utf-8")
count_def = result.count("def _set_session_cookie(")
count_recursive = result.count("        _set_session_cookie(response, token, request)")

print()
print(f"Definitions : {count_def}")
print(f"Appels recursifs internes (indentation 8) : {count_recursive}")

if count_def == 1 and count_recursive == 0:
    print("[OK] FIX APPLIQUE — plus de recursion")
else:
    print("[!] Verification echouee")
    print("    Colle-moi le resultat ci-dessus")

# Verifier qu'il y a bien 2 appels legitimes (dans register et login)
count_calls = result.count("_set_session_cookie(response, token, request)")
print(f"Appels totaux (dont register + login) : {count_calls}")

print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print("  Puis recharge et retente l'inscription.")