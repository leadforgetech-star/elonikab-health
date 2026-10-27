"""
fix_reload_sse.py
Limite les connexions SSE a 20 secondes pour permettre le --reload d'Uvicorn.
Le client EventSource se reconnecte automatiquement (comportement standard).
"""
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent
SSE = BASE / "v3_modules" / "notifications_stream.py"

if not SSE.exists():
    print("[ERREUR] notifications_stream.py introuvable")
    raise SystemExit(1)

shutil.copy2(SSE, SSE.with_suffix(".py.bak"))
print("[OK] Backup ->", SSE.with_suffix(".py.bak").name)

src = SSE.read_text(encoding="utf-8")

# Remplacer la boucle infinie par une boucle a duree limitee
old_loop = '''        async def event_generator():
            last_id = 0
            # Envoyer un ping initial pour eviter les buffers proxy
            yield ": ping\\n\\n"
            idle = 0
            while True:
                if await request.is_disconnected():
                    break'''

new_loop = '''        async def event_generator():
            import time
            last_id = 0
            started = time.time()
            # Limiter la duree de la connexion a 20s pour permettre le reload uvicorn
            MAX_LIFETIME = 20.0
            # Envoyer un ping initial pour eviter les buffers proxy
            yield ": ping\\n\\n"
            idle = 0
            while True:
                if await request.is_disconnected():
                    break
                if time.time() - started > MAX_LIFETIME:
                    # Fermeture propre : le client se reconnectera automatiquement
                    yield ": reload-window\\n\\n"
                    break'''

if old_loop in src:
    src = src.replace(old_loop, new_loop, 1)
    SSE.write_text(src, encoding="utf-8")
    print("[OK] notifications_stream.py -> duree limitee a 20s")
elif "MAX_LIFETIME" in src:
    print("[i] deja patche")
else:
    print("[!] pattern de boucle introuvable")
    # afficher un extrait
    idx = src.find("async def event_generator")
    if idx > 0:
        print(src[idx:idx+600])

print()
print("=" * 60)
print("SSE LIMITE A 20 SECONDES")
print("=" * 60)
print()
print("Effet :")
print("  - Chaque connexion SSE se ferme automatiquement apres 20s")
print("  - Le client EventSource se reconnecte tout seul (natif)")
print("  - Uvicorn peut redemarrer proprement a chaque modif .py")
print()
print("PROCHAINE ETAPE :")
print("  Utilise --reload normalement dans dev.bat")