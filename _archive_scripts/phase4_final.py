# phase4_final.py
# 1) Fix test 3c  2) Injecte CSS V6 dans index.html  3) Test E2E complet
import os, re, sys, json, shutil, sqlite3, datetime
import http.cookiejar, urllib.request, urllib.error

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
STATIC = os.path.join(ROOT, "static")
INDEX = os.path.join(STATIC, "index.html")
V6CSS = os.path.join(STATIC, "v6_override.css")
BASE  = "http://127.0.0.1:8000"
DB    = os.path.join(ROOT, "database.db")

# ============================================================
# 0) BACKUP
# ============================================================
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
bak = os.path.join(ROOT, f"_backup_phase4_{ts}")
os.makedirs(bak, exist_ok=True)
for name in ("index.html", "app.js", "style.css"):
    src = os.path.join(STATIC, name)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(bak, name))
print(f"[BACKUP] {bak}")

# ============================================================
# 1) INJECTER CSS V6 DANS index.html
# ============================================================
V6_CONTENT = '''/* v6_override.css - Palette Elokinab Health V6 (injecte par phase4_final.py) */
:root{
  --blue:#174A7E!important;
  --blue-dark:#0F3457!important;
  --blue-soft:#E8F0F8!important;
  --primary:#174A7E!important;
  --primary-color:#174A7E!important;
  --ink:#0F172A!important;
  --muted:#64748B!important;
  --line:#E2E8F0!important;
  --bg:#F5F8FC!important;
}
html,body{
  background:var(--bg)!important;
  color:var(--ink)!important;
  font-family:-apple-system,"Segoe UI",system-ui,sans-serif!important;
  -webkit-font-smoothing:antialiased!important;
}
/* Header sticky bleu */
header,.eh-header,header.site-header{
  background:linear-gradient(135deg,#174A7E,#2A6BA8)!important;
  box-shadow:0 4px 16px rgba(15,23,42,.08)!important;
  color:#fff!important;
}
header a, .eh-header a{color:#fff!important}
/* Boutons */
button,.btn,.eh-btn{
  border-radius:11px!important;
  font-weight:700!important;
  transition:.15s!important;
}
button.primary,.btn-primary,.eh-btn-primary{
  background:var(--blue)!important;
  color:#fff!important;
  border:0!important;
}
button.primary:hover,.btn-primary:hover{
  background:var(--blue-dark)!important;
  transform:translateY(-1px)!important;
}
/* Cartes produits */
.product-card,.card,.eh-card{
  border-radius:16px!important;
  box-shadow:0 6px 20px rgba(15,23,42,.06)!important;
  border:1px solid var(--line)!important;
  background:#fff!important;
  transition:.2s!important;
}
.product-card:hover,.card:hover{
  box-shadow:0 12px 32px rgba(23,74,126,.12)!important;
  transform:translateY(-2px)!important;
}
/* Inputs / recherche */
input,textarea,select{
  border-radius:10px!important;
  border:1.5px solid var(--line)!important;
  font-family:inherit!important;
}
input:focus,textarea:focus,select:focus{
  border-color:var(--blue)!important;
  box-shadow:0 0 0 3px var(--blue-soft)!important;
  outline:none!important;
}
/* Prix / accents */
.price,.product-price,.eh-price{color:var(--blue-dark)!important;font-weight:800!important}
/* Liens */
a{color:var(--blue)}
a:hover{color:var(--blue-dark)}
'''

with open(V6CSS, "w", encoding="utf-8") as f:
    f.write(V6_CONTENT)
print(f"[OK] {V6CSS} cree ({len(V6_CONTENT)} octets)")

if not os.path.exists(INDEX):
    print(f"[!] index.html absent -> pas d'injection")
else:
    html = open(INDEX, "r", encoding="utf-8").read()
    if 'v6_override.css' in html:
        print("[SKIP] v6_override.css deja injecte dans index.html")
    elif "</head>" in html:
        inject = '  <link rel="stylesheet" href="/static/v6_override.css?v=6">\n</head>'
        html = html.replace("</head>", inject, 1)
        open(INDEX, "w", encoding="utf-8").write(html)
        print("[OK] index.html : v6_override.css injecte")
    else:
        print("[!] </head> introuvable dans index.html")

# ============================================================
# 2) TEST E2E
# ============================================================
def make_cj():
    return http.cookiejar.CookieJar()

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def op_with(cj, follow=True):
    handlers = [urllib.request.HTTPCookieProcessor(cj)]
    if not follow:
        handlers.append(NoRedirect())
    return urllib.request.build_opener(*handlers)

def login(cj, email, pwd):
    op = op_with(cj)
    req = urllib.request.Request(
        BASE + "/api/auth/login",
        data=json.dumps({"email": email, "password": pwd}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with op.open(req, timeout=8) as r:
        return json.loads(r.read())

def get_nf(cj, path):
    op = op_with(cj, follow=False)
    try:
        with op.open(urllib.request.Request(BASE + path), timeout=8) as r:
            return r.status, r.headers.get("Location", "")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location", "")

def get_json(cj, path):
    op = op_with(cj, follow=True)
    try:
        with op.open(urllib.request.Request(BASE + path), timeout=8) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None

results = []
def check(label, cond, detail=""):
    flag = "OK" if cond else "!!! ECHEC"
    results.append(cond)
    print(f"  [{flag}] {label}   {detail}")

print("\n" + "=" * 60)
print("TEST E2E PHASE 4")
print("=" * 60)

# --- 3c : redirect + 403 ---
print("\n--- 3c : Redirects + 403 ---")
cj = make_cj()
st, loc = get_nf(cj, "/professionnel")
check("Anonyme -> /professionnel => 302 /connexion", st == 302 and "/connexion" in loc, f"({st}, {loc})")

cj = make_cj(); login(cj, "patient@test.tg", "Test1234")
st, loc = get_nf(cj, "/professionnel")
check("PATIENT -> /professionnel => 302 /acces-refuse", st == 302 and loc.endswith("/acces-refuse"), f"({st}, {loc})")

st, _ = get_nf(cj, "/acces-refuse")
check("/acces-refuse direct => 403", st == 403, f"({st})")

cj = make_cj(); login(cj, "pro@test.tg", "Test1234")
st, loc = get_nf(cj, "/professionnel")
check("PRO (org=1) -> /professionnel => 200/302 stable", st in (200, 302) and not loc.endswith("/acces-refuse"), f"({st}, {loc})")

# --- 3a : ownership /api/orders ---
print("\n--- 3a : Ownership /api/orders ---")
cj = make_cj()
st, _ = get_json(cj, "/api/orders")
check("Anonyme GET /api/orders => 401", st == 401, f"({st})")

cj = make_cj(); login(cj, "patient@test.tg", "Test1234")
st, body = get_json(cj, "/api/orders")
check("PATIENT GET /api/orders => 200 + []", st == 200 and isinstance(body, list) and len(body) == 0, f"({st})")

cj = make_cj(); login(cj, "pro@test.tg", "Test1234")
st, body = get_json(cj, "/api/orders")
check("PRO GET /api/orders => 200 + []", st == 200 and isinstance(body, list) and len(body) == 0, f"({st})")

cj = make_cj(); login(cj, "pharmacien@test.tg", "Test1234")
st, body = get_json(cj, "/api/orders")
check("PHARMACIEN GET /api/orders => 200 + []", st == 200 and isinstance(body, list) and len(body) == 0, f"({st})")

# --- Login flow complet ---
print("\n--- Login flow ---")
for email, role in [
    ("patient@test.tg", "PATIENT"),
    ("pro@test.tg", "PROFESSIONNEL"),
    ("pharmacien@test.tg", "PHARMACIEN"),
    ("admin@test.tg", "ADMIN"),
]:
    cj = make_cj()
    try:
        d = login(cj, email, "Test1234")
        got = d.get("user", {}).get("role")
        check(f"login {email} => role {role}", got == role, f"({got})")
    except Exception as e:
        check(f"login {email} => role {role}", False, f"(erreur: {e})")

# --- DB integrity ---
print("\n--- DB integrity ---")
con = sqlite3.connect(DB)
integ = con.execute("PRAGMA integrity_check").fetchone()[0]
fk = len(con.execute("PRAGMA foreign_key_check").fetchall())
users = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
pros_with_org = con.execute(
    "SELECT COUNT(*) FROM users WHERE role='PROFESSIONNEL' AND organization_id IS NOT NULL"
).fetchone()[0]
con.close()
check("integrity_check ok", integ == "ok", f"({integ})")
check("foreign_key_check 0", fk == 0, f"({fk})")
check("4 users seed", users == 4, f"({users})")
check("pro@test.tg a organization_id", pros_with_org >= 1, f"({pros_with_org})")

# ============================================================
# RESUME
# ============================================================
ok = sum(1 for r in results if r)
total = len(results)
print("\n" + "=" * 60)
print(f"RESULTAT : {ok}/{total} tests OK")
print("=" * 60)

if ok == total:
    print("\n[DONE] Phase 3a + 3b + 3c + 4 : TOUT VALIDE.")
else:
    print(f"\n[!] {total - ok} test(s) en echec. Envoie-moi la sortie.")

print("\n[INFO] Uvicorn --reload recharge auto.")
print("[INFO] Vide le cache Edge (Ctrl+Shift+R) pour voir la V6.")