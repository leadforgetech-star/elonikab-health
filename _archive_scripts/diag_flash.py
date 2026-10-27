"""
diag_flash.py
Diagnostic du bug "vieille interface avant redirection".
Verifie : service worker, cache HTML, middleware, headers, contenu servi.
"""
import sqlite3
import urllib.request
import urllib.error
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
STATIC = BASE / "static"
DB = BASE / "database.db"
API = "http://127.0.0.1:8000"


def section(t):
    print()
    print("=" * 72)
    print(" " + t)
    print("=" * 72)
    print()


def get(path, method="GET"):
    try:
        req = urllib.request.Request(API + path, method=method)
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, {}, "ERREUR: " + str(e)


# ================================================================
# 1. Fichiers HTML sur disque
# ================================================================
section("1. FICHIERS HTML SUR DISQUE")

for name in ("index.html", "professional.html", "suivi.html", "payment.html"):
    p = STATIC / name
    if not p.exists():
        print(f"  [!] {name} MANQUANT")
        continue
    content = p.read_text(encoding="utf-8")
    size = len(content)
    flags = []
    if "eh-loader" in content: flags.append("loader")
    if "safe_locale" in content: flags.append("safe_locale")
    if "sw_kill" in content.lower(): flags.append("sw-kill")
    if "serviceworker" in content.lower(): flags.append("SW-REG")
    if "Cache-Control" in content: flags.append("meta-cache")
    print(f"  {name:25s} {size:>7d} o  [{', '.join(flags) if flags else 'basique'}]")

# ================================================================
# 2. Service Worker
# ================================================================
section("2. SERVICE WORKER")

sw_files = list(STATIC.glob("sw*.js")) + list(STATIC.glob("service-worker*.js"))
if sw_files:
    for f in sw_files:
        print(f"  [!] {f.name} present ({f.stat().st_size} o)")
else:
    print("  [OK] Aucun service worker detecte sur disque")

# ================================================================
# 3. Routes HTML dans main.py
# ================================================================
section("3. ROUTES HTML DANS main.py")

src = MAIN.read_text(encoding="utf-8")

routes = re.findall(r'@app\.(get|api_route)\("(/[^"]*)"', src)
html_routes = [(m, p) for m, p in routes if not p.startswith("/api/") and not p.startswith("/static/")]
for method, path in html_routes:
    print(f"  {method.upper():10s} {path}")

# ================================================================
# 4. Middlewares actifs
# ================================================================
section("4. MIDDLEWARES DANS main.py")

middlewares = [
    "NoCacheAllStatic",
    "NoCacheHTMLMiddleware",
    "ClearSiteDataMiddleware",
    "StaticCacheMiddleware",
    "GZipMiddleware",
    "NoCacheStaticFiles",
]
for mw in middlewares:
    count = src.count("add_middleware(" + mw)
    status = "OK" if count >= 1 else "absent"
    print(f"  {mw:30s} {status} ({count}x)")

# ================================================================
# 5. Headers servis par le serveur
# ================================================================
section("5. HEADERS SERVIS (localhost)")

for route in ("/", "/professionnel", "/connexion", "/inscription"):
    status, headers, _ = get(route)
    cc = headers.get("cache-control", headers.get("Cache-Control", ""))
    csd = headers.get("clear-site-data", headers.get("Clear-Site-Data", ""))
    ctype = headers.get("content-type", headers.get("Content-Type", ""))[:40]
    print(f"  {route:20s} status={status} ctype={ctype}")
    print(f"    cache-control={cc[:70]}")
    print(f"    clear-site-data={csd}")

# ================================================================
# 6. Contenu HTML servi vs disque
# ================================================================
section("6. CONTENU SERVI vs DISQUE")

status, headers, served = get("/")
on_disk = (STATIC / "index.html").read_text(encoding="utf-8")

print(f"  Taille disque : {len(on_disk)}")
print(f"  Taille servi  : {len(served)}")
print(f"  Identiques    : {served == on_disk}")

if served != on_disk:
    min_len = min(len(served), len(on_disk))
    diff_at = -1
    for i in range(min_len):
        if served[i] != on_disk[i]:
            diff_at = i
            break
    if diff_at >= 0:
        print(f"  Premiere diff a l'offset {diff_at}")
        print(f"    disque : {repr(on_disk[diff_at:diff_at+80])}")
        print(f"    servi  : {repr(served[diff_at:diff_at+80])}")

# ================================================================
# 7. Detecter le vieux contenu
# ================================================================
section("7. MARQUEURS VIEUX vs NOUVEAU")

status, _, served = get("/")
markers = {
    "gateway (V6)": "gw-card" in served or "acc-welcome" in served,
    "guide V6": "acc-guide" in served,
    "loader (eh-loader)": "eh-loader" in served,
    "old placeholder style": "Votre pharmacie, en ligne" in served,
    "old design (vert)": "#0f9d76" in served and "1a4a7f" not in served,
    "nouveau bleu": "1a4a7f" in served or "--blue" in served,
    "catalogue direct link": "pro-quick" in served,
}
for label, ok in markers.items():
    print(f"  {'OK ' if ok else '[!]'} {label}: {ok}")

# ================================================================
# 8. Magic link + redirection
# ================================================================
section("8. MAGIC LINK (test de redirection)")

try:
    import secrets, datetime
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT id FROM users WHERE email='pro@test.tg'").fetchone()
    if user:
        token = secrets.token_urlsafe(16)
        now = datetime.datetime.now()
        exp = (now + datetime.timedelta(hours=1)).isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO magic_links (token, user_id, created_at, expires_at, max_uses, used_count, revoked, note)"
            " VALUES (?, ?, ?, ?, 0, 0, 0, 'diag')",
            (token, user["id"], now.isoformat(timespec="seconds"), exp),
        )
        conn.commit()
        print(f"  Magic link cree : /acces/{token[:20]}...")
        status, headers, body = get("/acces/" + token)
        print(f"  status={status}")
        print(f"  location={headers.get('location', headers.get('Location', ''))}")
        print(f"  cache-control={headers.get('cache-control', headers.get('Cache-Control', ''))[:60]}")
        print(f"  ctype={headers.get('content-type', headers.get('Content-Type', ''))[:40]}")
        print(f"  taille={len(body)}")
        print()
        print("  Extrait du body :")
        print("  " + body[:300].replace("\n", "\n  "))
    else:
        print("  [!] pro@test.tg introuvable")
    conn.close()
except Exception as e:
    print("  Erreur magic link :", e)

# ================================================================
# 9. Fichiers suspects
# ================================================================
section("9. FICHIERS SUSPECTS")

baks = list(STATIC.glob("*.bak")) + list(STATIC.glob("*.bak*"))
print(f"  {len(baks)} fichier(s) .bak dans static/")
for f in baks[:10]:
    print(f"    {f.name}")

# Chercher d'autres index.html (doublons)
dups = list(BASE.rglob("index.html"))
print(f"\n  {len(dups)} index.html trouves :")
for d in dups:
    print(f"    {d.relative_to(BASE)} ({d.stat().st_size} o)")

# ================================================================
section("FIN")
print("  Colle-moi l'integralite du resultat ci-dessus.")