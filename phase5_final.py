# phase5_final.py
# 1) Backup  2) WhatsApp flottant  3) Banniere promo  4) Archive .py temp  5) E2E
import os, sys, json, shutil, sqlite3, datetime
import http.cookiejar, urllib.request, urllib.error

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
STATIC = os.path.join(ROOT, "static")
INDEX = os.path.join(STATIC, "index.html")
V6CSS = os.path.join(STATIC, "v6_extra.css")
BASE = "http://127.0.0.1:8000"
DB = os.path.join(ROOT, "database.db")
WHATSAPP = "+22871039904"

# ============================================================
# 0) BACKUP
# ============================================================
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
bak = os.path.join(ROOT, f"_backup_phase5_{ts}")
os.makedirs(bak, exist_ok=True)
if os.path.exists(INDEX):
    shutil.copy2(INDEX, os.path.join(bak, "index.html"))
print(f"[BACKUP] {bak}")

# ============================================================
# 1) CSS V6 EXTRA (bouton WhatsApp + banniere promo)
# ============================================================
EXTRA_CSS = '''/* v6_extra.css - WhatsApp flottant + banniere promo */
.eh-promo-banner{
  position:fixed;top:0;left:0;right:0;z-index:9998;
  background:linear-gradient(135deg,#174A7E,#2A6BA8);color:#fff;
  padding:10px 16px;text-align:center;font-size:13px;font-weight:700;
  letter-spacing:.02em;box-shadow:0 2px 10px rgba(15,23,42,.15);
  font-family:-apple-system,"Segoe UI",system-ui,sans-serif;
}
.eh-promo-banner .eh-code{
  background:#fff;color:#174A7E;padding:2px 8px;border-radius:6px;
  margin-left:6px;font-weight:800;
}
.eh-promo-banner .eh-close{
  position:absolute;right:10px;top:50%;transform:translateY(-50%);
  background:rgba(255,255,255,.15);border:0;color:#fff;
  width:24px;height:24px;border-radius:50%;cursor:pointer;
  font-size:14px;line-height:1;font-weight:800;
}
body.eh-has-promo{padding-top:0!important}
body.eh-has-promo>*:not(.eh-promo-banner):not(.eh-wa-float){
  margin-top:0!important;
}

.eh-wa-float{
  position:fixed;right:18px;bottom:22px;z-index:9999;
  width:56px;height:56px;border-radius:50%;
  background:#25D366;color:#fff!important;
  display:flex;align-items:center;justify-content:center;
  box-shadow:0 8px 24px rgba(37,211,102,.35);
  text-decoration:none!important;
  transition:.2s;font-family:-apple-system,"Segoe UI",system-ui,sans-serif;
}
.eh-wa-float:hover{transform:scale(1.08);box-shadow:0 12px 32px rgba(37,211,102,.45)}
.eh-wa-float svg{width:30px;height:30px;fill:#fff}
.eh-wa-float .eh-wa-tip{
  position:absolute;right:66px;top:50%;transform:translateY(-50%);
  background:#0F172A;color:#fff;padding:8px 12px;border-radius:8px;
  font-size:12.5px;font-weight:700;white-space:nowrap;
  opacity:0;pointer-events:none;transition:.2s;
}
.eh-wa-float:hover .eh-wa-tip{opacity:1}
@media(max-width:400px){
  .eh-wa-float{right:14px;bottom:14px;width:52px;height:52px}
  .eh-promo-banner{font-size:12px;padding:8px 40px 8px 12px}
}
'''

with open(V6CSS, "w", encoding="utf-8") as f:
    f.write(EXTRA_CSS)
print(f"[OK] {V6CSS} cree ({len(EXTRA_CSS)} octets)")

# ============================================================
# 2) INJECT HTML DANS index.html
# ============================================================
if not os.path.exists(INDEX):
    print("[!] index.html absent -> injection ignoree")
else:
    html = open(INDEX, "r", encoding="utf-8").read()

    # 2a) Link CSS extra
    if "v6_extra.css" not in html and "</head>" in html:
        html = html.replace(
            "</head>",
            '  <link rel="stylesheet" href="/static/v6_extra.css?v=6">\n</head>',
            1,
        )
        print("[OK] index.html : v6_extra.css lie")

    # 2b) Banniere promo + bouton WhatsApp avant </body>
    if "eh-promo-banner" not in html and "</body>" in html:
        inject = '''
<!-- EH Phase 5 : banniere promo + WhatsApp flottant -->
<div class="eh-promo-banner" id="eh-promo-banner">
  🎁 Livraison offerte des 15 000 FCFA — Code
  <span class="eh-code">ELONIKAB6</span>
  <button class="eh-close" onclick="this.parentNode.style.display='none';document.body.classList.remove('eh-has-promo');try{localStorage.setItem('eh_promo_off','1')}catch(e){}">×</button>
</div>

<a class="eh-wa-float" id="eh-wa-float"
   href="https://wa.me/''' + WHATSAPP + '''?text=Bonjour%20Elonikab%20Health%2C%20j%27ai%20une%20question."
   target="_blank" rel="noopener" aria-label="Contacter par WhatsApp">
  <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
  </svg>
  <span class="eh-wa-tip">Besoin d'aide ?</span>
</a>
<script>
(function(){
  try {
    if (localStorage.getItem("eh_promo_off") === "1") {
      var b = document.getElementById("eh-promo-banner");
      if (b) b.style.display = "none";
    }
  } catch(e){}
})();
</script>
'''
        html = html.replace("</body>", inject + "\n</body>", 1)
        print("[OK] index.html : banniere promo + WhatsApp flottant injectes")

    open(INDEX, "w", encoding="utf-8").write(html)

# ============================================================
# 3) ARCHIVER LES .PY TEMPORAIRES
# ============================================================
WHITELIST = {
    "main.py",
    "automation.py",
    "generate_link.py",
    "restart_and_link.py",
    "fix_upload_json.py",
    "phase5_final.py",  # ce script lui-meme
}

archive = os.path.join(ROOT, "_archive_scripts")
os.makedirs(archive, exist_ok=True)

moved = []
for f in sorted(os.listdir(ROOT)):
    if not f.endswith(".py"):
        continue
    if f in WHITELIST:
        continue
    if f.startswith("_"):
        continue
    src = os.path.join(ROOT, f)
    dst = os.path.join(archive, f)
    try:
        shutil.move(src, dst)
        moved.append(f)
    except Exception as e:
        print(f"  [!] {f} : {e}")

print(f"\n[ARCHIVE] {len(moved)} scripts .py deplaces vers _archive_scripts/")
for f in moved[:10]:
    print(f"     - {f}")
if len(moved) > 10:
    print(f"     ... et {len(moved)-10} autres")

# ============================================================
# 4) ARCHIVER LES .BAK
# ============================================================
bak_archive = os.path.join(archive, "backups")
os.makedirs(bak_archive, exist_ok=True)

moved_bak = 0
for f in sorted(os.listdir(ROOT)):
    if f.endswith(".bak"):
        try:
            shutil.move(os.path.join(ROOT, f), os.path.join(bak_archive, f))
            moved_bak += 1
        except Exception:
            pass
print(f"[ARCHIVE] {moved_bak} fichiers .bak deplaces vers _archive_scripts/backups/")

# ============================================================
# 5) E2E FINAL
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

results = []
def check(label, cond, detail=""):
    flag = "OK" if cond else "!!! ECHEC"
    results.append(cond)
    print(f"  [{flag}] {label}   {detail}")

print("\n" + "=" * 60)
print("E2E FINAL PHASE 5")
print("=" * 60)

# Racine accessible
cj = make_cj()
st, _ = get_nf(cj, "/")
check("GET / => 200", st == 200, f"({st})")

# 403 toujours OK
st, _ = get_nf(cj, "/acces-refuse")
check("/acces-refuse => 403", st == 403, f"({st})")

# Redirs OK
cj = make_cj()
st, loc = get_nf(cj, "/professionnel")
check("Anonyme -> /professionnel => 302 /connexion", st == 302 and "/connexion" in loc, f"({st})")

cj = make_cj(); login(cj, "pro@test.tg", "Test1234")
st, loc = get_nf(cj, "/professionnel")
check("PRO -> /professionnel => 200", st == 200, f"({st})")

# API orders
cj = make_cj()
st, _ = get_nf(cj, "/api/orders")
check("Anonyme /api/orders => 401", st == 401, f"({st})")

cj = make_cj(); login(cj, "pharmacien@test.tg", "Test1234")
st, _ = get_nf(cj, "/api/orders")
check("PHARMACIEN /api/orders => 200", st == 200, f"({st})")

# DB integrity
con = sqlite3.connect(DB)
integ = con.execute("PRAGMA integrity_check").fetchone()[0]
con.close()
check("DB integrity ok", integ == "ok", f"({integ})")

# Fichiers injectes
h = open(INDEX, "r", encoding="utf-8").read()
check("Banniere promo presente", "eh-promo-banner" in h)
check("WhatsApp flottant present", "eh-wa-float" in h)
check("v6_extra.css lie", "v6_extra.css" in h)

ok = sum(1 for r in results if r)
total = len(results)
print("\n" + "=" * 60)
print(f"RESULTAT FINAL : {ok}/{total} tests OK")
print("=" * 60)

# Etat racine
remaining = [f for f in os.listdir(ROOT) if f.endswith(".py") and not f.startswith("_")]
print(f"\n[PY A LA RACINE] {len(remaining)} fichiers :")
for f in sorted(remaining):
    print(f"     - {f}")

if ok == total:
    print("\n[DONE] Phase 5 terminee.")
    print("[INFO] Vide le cache Edge (Ctrl+Shift+R) et recharge https://linked-cycles-extras-non.trycloudflare.com/")
else:
    print(f"\n[!] {total-ok} test(s) en echec.")