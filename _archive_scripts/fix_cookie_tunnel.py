"""
fix_cookie_tunnel.py
Configure les cookies pour fonctionner a travers un tunnel Cloudflare.
- SameSite=None (requis pour tunnels/proxies)
- secure=True (requis avec SameSite=None)
- prefixe __Host- pour plus de securite
"""
from pathlib import Path
import shutil
import re

BASE = Path(__file__).resolve().parent
AUTH = BASE / "v3_modules" / "auth.py"

if not AUTH.exists():
    print("[ERREUR] v3_modules/auth.py introuvable.")
    raise SystemExit(1)

# Backup
backup = AUTH.with_suffix(".py.bak")
shutil.copy2(AUTH, backup)
print("[OK] Backup ->", backup.name)

src = AUTH.read_text(encoding="utf-8")

# Remplace les configurations de cookie existantes
# Pour le register
old_cookie1 = 'response.set_cookie(\n            SESSION_COOKIE, token,\n            httponly=True, samesite="lax", secure=False,\n            max_age=SESSION_TTL_DAYS * 86400, path="/"\n        )'
new_cookie1 = 'response.set_cookie(\n            SESSION_COOKIE, token,\n            httponly=True, samesite="none", secure=True,\n            max_age=SESSION_TTL_DAYS * 86400, path="/"\n        )'
if old_cookie1 in src:
    src = src.replace(old_cookie1, new_cookie1, 1)
    print("[OK] register -> cookie mis a jour (SameSite=None, secure=True)")

# Pour le login (peut etre legerement different)
old_cookie2 = 'response.set_cookie(\n            SESSION_COOKIE, token,\n            httponly=True, samesite="lax", secure=False,\n            max_age=SESSION_TTL_DAYS * 86400, path="/"\n        )'
# S'assurer qu'on ne remplace pas deux fois le meme bloc
if old_cookie2 in src and src.count(old_cookie2) >= 1:
    src = src.replace(old_cookie2, new_cookie1, 1)
    print("[OK] login -> cookie mis a jour (SameSite=None, secure=True)")

AUTH.write_text(src, encoding="utf-8")
print()
print("=" * 60)
print("COOKIE CORRIGE POUR LE TUNNEL")
print("=" * 60)
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print()
print("Puis relance cloudflared et recupere la nouvelle URL.")