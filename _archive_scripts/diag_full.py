"""
diag_full.py
Diagnostic complet du bug 'vieille interface avant redirection'.
Verifie : fichiers, headers, routes, contenu servi, caches.
"""
import re
import sqlite3
import sys
import urllib.request
import urllib.error
from pathlib import Path

BASE = Path(__file__).resolve().parent
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

# ============================================================
# 1. Fichiers HTML en place
# ============================================================
section("1. FICHIERS HTML SUR DISQUE")

html_files = sorted(STATIC.glob("*.html"))
for f in html_files:
    size = f.stat().st_size
    content = f.read_text(encoding="utf-8")
    # Detecter l'ancien design vs le nouveau
    has_acc_welcome = "acc-welcome" in content or "welcome" in content and "gw-hero" not in content
    has_gw = "gw-hero" in content
    has_recap = "recap-item" in content
    has_loaders = "eh-loader" in content
    has_meta_nostore = 'http-equiv="Cache-Control"' in content
    flags = []
    if has_gw: flags.append("gateway")
    if has_recap: flags.append("recap")
    if has_loaders: flags.append("loader")
    if has_meta_nostore: flags.append("meta-nostore")
    print(f"  {f.name:45s} {size:>7} o  [{', '.join(flags) if flags else 'basic'}]")

# Chercher des doublons
print()
print("  Doublons possibles :")
for name in ("professional.html", "index.html"):
    locations = list(BASE.rglob(name))
    if len(locations) > 1:
        print(f"  [!] '{name}' trouve {len(locations)} fois :")
        for loc in locations:
            print(f"      {loc.relative_to(BASE)}")
    else:
        print(f"  [OK] '{name}' unique : {locations[0].relative_to(BASE) if locations else 'absent'}")

# ============================================================
# 2. Routes servies
# ============================================================
section("2. ROUTES SERVIES (via HTTP local)")

ROUTES = ["/", "/professionnel", "/connexion", "/inscription",
          "/pharmacien", "/suivi", "/professionnel/demande",
          "/professionnel/catalogue", "/professionnel/commandes",
          "/professionnel/etablissement"]

for route in ROUTES:
    status, headers, body = get(route)
    ctype = headers.get("content-type", headers.get("Content-Type", "")).split(";")[0]
    cache = headers.get("cache-control", headers.get("Cache-Control", ""))
    csd = headers.get("clear-site-data", headers.get("Clear-Site-Data", ""))
    size = len(body)
    # Quels marqueurs dans le HTML servi ?
    markers = []
    if "acc-welcome" in body: markers.append("OLD-accueil")
    if "welcome" in body and "gw-hero" not in body and "acc-welcome" not in body:
        markers.append("has-welcome")
    if "gw-hero" in body: markers.append("gateway")
    if "recap-item" in body: markers.append("recap")
    if "Bienvenue" in body: markers.append("Bienvenue")
    if "Bonjour" in body: markers.append("Bonjour")
    if "Nouvelle demande" in body: markers.append("Nouvelle-demande")
    if "Comment commander" in body: markers.append("Comment-commander")
    print(f"  {route}")
    print(f"    status={status}  ctype={ctype}  size={size}o")
    print(f"    cache={cache[:60]}")
    print(f"    clear-site-data={csd}")
    print(f"    markers={markers}")

# ============================================================
# 3. Magic link — test de redirection
# ============================================================
section("3. MAGIC LINK — test d'une redirection fraiche")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
# Creer un magic link de test pour pro@test.tg
import secrets, datetime, base64
user = conn.execute("SELECT id FROM users WHERE email='pro@test.tg'").fetchone()
if user:
    token = secrets.token_urlsafe(32)
    now = datetime.datetime.now()
    exp = (now + datetime.timedelta(hours=1)).isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO magic_links (token, user_id, created_at, expires_at, max_uses, used_count, revoked, note)"
        " VALUES (?, ?, ?, ?, 0, 0, 0, 'diag')",
        (token, user["id"], now.isoformat(timespec="seconds"), exp)
    )
    conn.commit()
    print(f"  Magic link cree : /acces/{token[:20]}...")

    status, headers, body = get("/acces/" + token)
    print(f"  status={status}")
    print(f"  ctype={headers.get('content-type', headers.get('Content-Type', ''))}")
    print(f"  cache-control={headers.get('cache-control', headers.get('Cache-Control', ''))}")
    print(f"  clear-site-data={headers.get('clear-site-data', headers.get('Clear-Site-Data', ''))}")
    print(f"  size={len(body)}o")
    print()
    print("  Extrait du HTML servi (500 premiers caracteres) :")
    print("  " + body[:500].replace("\n", "\n  "))
else:
    print("  [!] pro@test.tg introuvable en base")
conn.close()

# ============================================================
# 4. Detecter les doublons dans les backups
# ============================================================
section("4. FICHIERS .bak QUI POURRAIENT CONFONDRE")

bak_files = list(STATIC.glob("*.bak*"))
if bak_files:
    print(f"  {len(bak_files)} fichiers .bak dans static/ :")
    for f in bak_files[:20]:
        print(f"    {f.name} ({f.stat().st_size}o)")
else:
    print("  Aucun .bak dans static/")

# ============================================================
# 5. Verifier les middlewares actifs
# ============================================================
section("5. MIDDLEWARES ENREGISTRES")

MAIN = BASE / "main.py"
src = MAIN.read_text(encoding="utf-8")
for mw in ("NoCacheAllStatic", "NoCacheHTMLMiddleware", "ClearSiteDataMiddleware", "GZipMiddleware"):
    count = src.count("add_middleware(" + mw)
    status = "OK" if count >= 1 else "MANQUANT"
    print(f"  {mw:30s} {status} ({count}x)")

# ============================================================
# 6. Extraire les headers pour /professionnel brut
# ============================================================
section("6. HEADERS BRUTS /professionnel")

status, headers, _ = get("/professionnel")
print(f"  status={status}")
for k, v in sorted(headers.items()):
    print(f"  {k}: {v}")

# ============================================================
# 7. Extraire les headers pour /acces/{token}
# ============================================================
section("7. HEADERS BRUTS /acces/{token}")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
user = conn.execute("SELECT id FROM users WHERE email='pro@test.tg'").fetchone()
if user:
    token = secrets.token_urlsafe(32)
    now = datetime.datetime.now()
    exp = (now + datetime.timedelta(hours=1)).isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO magic_links (token, user_id, created_at, expires_at, max_uses, used_count, revoked, note)"
        " VALUES (?, ?, ?, ?, 0, 0, 0, 'diag2')",
        (token, user["id"], now.isoformat(timespec="seconds"), exp)
    )
    conn.commit()
    status, headers, body = get("/acces/" + token)
    print(f"  status={status}")
    for k, v in sorted(headers.items()):
        print(f"  {k}: {v}")
conn.close()

print()
print("=" * 72)
print(" FIN DU DIAGNOSTIC")
print("=" * 72)
print()
print("Colle-moi le resultat complet de ce script.")