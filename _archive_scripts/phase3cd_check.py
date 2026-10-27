# phase3cd_check.py
# Test Phase 3c + dump index.html/app.js pour preparer Phase 3d
import os, sys, json, http.cookiejar, urllib.request, urllib.error

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
STATIC = os.path.join(ROOT, "static")
BASE = "http://127.0.0.1:8000"
DUMP = os.path.join(ROOT, "phase3d_index_dump.txt")

def make_op():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def login(op, email, pwd):
    req = urllib.request.Request(
        BASE + "/api/auth/login",
        data=json.dumps({"email": email, "password": pwd}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with op.open(req, timeout=8) as r:
        return json.loads(r.read())

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def get_nofollow(op, path):
    op2 = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(
            op.handlers[0].cookiejar
        ),
        NoRedirect(),
    )
    req = urllib.request.Request(BASE + path)
    try:
        with op2.open(req, timeout=8) as r:
            return r.status, r.headers.get("Location", ""), ""
    except urllib.error.HTTPError as e:
        body = ""
        try: body = e.read().decode("utf-8", "replace")[:200]
        except: pass
        return e.code, e.headers.get("Location", ""), body

print("=" * 60)
print("CHECK PHASE 3c")
print("=" * 60)

# T1 : anonyme -> /professionnel => 302 /connexion
op = make_op()
st, loc, _ = get_nofollow(op, "/professionnel")
print(f"\n[T1] Anonyme /professionnel : status={st} location={loc}")
print(f"  {'OK' if st == 302 and '/connexion' in loc else '!!! ECHEC'}")

# T2 : patient -> /professionnel => 302 /acces-refuse
op = make_op()
login(op, "patient@test.tg", "Test1234")
st, loc, _ = get_nofollow(op, "/professionnel")
print(f"\n[T2] PATIENT /professionnel : status={st} location={loc}")
print(f"  {'OK' if st == 302 and loc.endswith('/acces-refuse') else '!!! ECHEC'}")

# T3 : /acces-refuse direct => 403
op = make_op()
st, loc, body = get_nofollow(op, "/acces-refuse")
print(f"\n[T3] /acces-refuse : status={st}")
print(f"  body[:200]={body[:200]}")
print(f"  {'OK' if st == 403 else '!!! ECHEC (attendu 403)'}")

# ============================================================
# DUMP index.html + app.js
# ============================================================
print("\n" + "=" * 60)
print("DUMP pour Phase 3d")
print("=" * 60)

out = []
def log(s=""):
    print(s); out.append(s)

for name in ("index.html", "app.js", "style.css", "header.js", "header.css"):
    p = os.path.join(STATIC, name)
    log("=" * 78)
    log(f"FICHIER: {name}  (existe={os.path.exists(p)}, size={os.path.getsize(p) if os.path.exists(p) else 0})")
    log("=" * 78)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()
        # Pour index.html et style.css on dump tout ; pour app.js on peut tronquer
        if name == "app.js" and len(content) > 6000:
            log(content[:6000])
            log(f"\n[... tronque, total {len(content)} caracteres ...]")
        else:
            log(content)
    log("")

with open(DUMP, "w", encoding="utf-8") as f:
    f.write("\n".join(out))

print(f"\n[RAPPORT] {DUMP}")
print(f"[TAILLE]  {os.path.getsize(DUMP)} octets")
print("\n>>> Colle-moi le contenu complet du rapport.")