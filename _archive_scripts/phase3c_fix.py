# phase3c_fix.py - page /acces-refuse + protection PRO -> 403
import os, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
MAIN = os.path.join(ROOT, "main.py")
STATIC = os.path.join(ROOT, "static")
HTML = os.path.join(STATIC, "acces_refuse.html")

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
bak = os.path.join(ROOT, f"_backup_phase3c_{ts}")
os.makedirs(bak, exist_ok=True)
shutil.copy2(MAIN, os.path.join(bak, "main.py.bak"))
print(f"[BACKUP] {bak}")

# ============================================================
# 1) Creer la page HTML 403
# ============================================================
HTML_CONTENT = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Acces refuse - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
:root{
  --blue:#174A7E;--blue-dark:#0F3457;--blue-soft:#E8F0F8;
  --ink:#0F172A;--muted:#64748B;--line:#E2E8F0;--bg:#F5F8FC;
  --danger:#B23C3C;
}
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  font-family:-apple-system,"Segoe UI",system-ui,sans-serif;
  background:var(--bg);color:var(--ink);
  min-height:100vh;display:flex;align-items:center;justify-content:center;
  padding:20px;-webkit-font-smoothing:antialiased;
}
.card{
  width:100%;max-width:480px;background:#fff;border-radius:22px;
  padding:38px 30px;text-align:center;
  box-shadow:0 14px 44px rgba(15,23,42,.10);
}
.brand{
  display:flex;align-items:center;gap:12px;justify-content:center;
  margin-bottom:26px;
}
.brand-logo{
  width:44px;height:44px;border-radius:12px;
  background:linear-gradient(135deg,#174A7E,#2A6BA8);color:#fff;
  display:flex;align-items:center;justify-content:center;
  font-size:22px;font-weight:800;
}
.brand-name{font-size:16px;font-weight:800;line-height:1.1;text-align:left}
.brand-tag{
  font-size:10px;color:var(--muted);text-transform:uppercase;
  letter-spacing:.1em;margin-top:2px;text-align:left;
}
.icon-circle{
  width:82px;height:82px;border-radius:50%;
  background:#FDECEC;color:var(--danger);
  display:flex;align-items:center;justify-content:center;
  font-size:40px;margin:0 auto 20px;
  border:3px solid #F8D5D5;
}
h1{font-size:22px;font-weight:800;letter-spacing:-.02em;margin:0 0 10px;color:var(--ink)}
.sub{
  font-size:14px;color:var(--muted);margin:0 0 26px;
  line-height:1.55;max-width:380px;margin-left:auto;margin-right:auto;
}
.actions{
  display:flex;flex-direction:column;gap:10px;margin-bottom:22px;
}
.btn{
  width:100%;padding:15px;border:0;border-radius:12px;
  font-family:inherit;font-weight:800;font-size:14.5px;
  cursor:pointer;transition:.15s;text-decoration:none;
  display:flex;align-items:center;justify-content:center;gap:8px;
}
.btn-primary{
  background:var(--blue);color:#fff;
}
.btn-primary:hover{background:var(--blue-dark);transform:translateY(-1px)}
.btn-ghost{
  background:#fff;border:1.5px solid var(--line);color:var(--ink);
}
.btn-ghost:hover{border-color:var(--blue);color:var(--blue)}
.foot{
  font-size:12px;color:var(--muted);line-height:1.5;
  padding-top:18px;border-top:1px solid var(--line);
}
.foot a{color:var(--blue);font-weight:700;text-decoration:none}
</style>
</head>
<body>
<div class="card">
  <div class="brand">
    <div class="brand-logo">+</div>
    <div>
      <div class="brand-name">Elokinab Health</div>
      <div class="brand-tag">Healthcare Procurement</div>
    </div>
  </div>

  <div class="icon-circle">&#128683;</div>
  <h1>Espace reserve aux professionnels</h1>
  <p class="sub">
    Cette section est dediee aux etablissements de sante
    (cliniques, cabinets, laboratoires, hopitaux).
    Votre compte ne dispose pas des droits necessaires.
  </p>

  <div class="actions">
    <a class="btn btn-primary" href="/">Retour a l'accueil</a>
    <a class="btn btn-ghost" href="/connexion?next=/professionnel">
      Se connecter avec un compte professionnel
    </a>
  </div>

  <div class="foot">
    Besoin d'un compte professionnel ?
    <a href="/inscription">Creer un etablissement</a>
  </div>
</div>
</body>
</html>
'''

with open(HTML, "w", encoding="utf-8") as f:
    f.write(HTML_CONTENT)
print(f"[OK] {HTML} cree ({len(HTML_CONTENT)} octets)")

# ============================================================
# 2) Ajouter la route /acces-refuse dans main.py
# ============================================================
main_src = open(MAIN, "r", encoding="utf-8").read()

if '"/acces-refuse"' in main_src:
    print("[SKIP] route /acces-refuse deja presente")
else:
    MARKER = '''@app.api_route("/professionnel", methods=["GET", "HEAD"], include_in_schema=False)'''
    NEW = '''@app.api_route("/acces-refuse", methods=["GET", "HEAD"], include_in_schema=False)
def page_acces_refuse():
    return FileResponse(STATIC_DIR / "acces_refuse.html", status_code=403)


@app.api_route("/professionnel", methods=["GET", "HEAD"], include_in_schema=False)'''
    if MARKER in main_src:
        main_src = main_src.replace(MARKER, NEW, 1)
        print("[OK] main.py : route /acces-refuse ajoutee")
    else:
        print("[!] marqueur /professionnel introuvable")

# ============================================================
# 3) Modifier page_professionnel : patient -> /acces-refuse (403)
# ============================================================
OLD_PRO = '''    role = row["role"]
    if role != "PROFESSIONNEL":
        return RedirectResponse(url="/", status_code=302)'''
NEW_PRO = '''    role = row["role"]
    if role != "PROFESSIONNEL":
        return RedirectResponse(url="/acces-refuse", status_code=302)'''

if OLD_PRO in main_src:
    main_src = main_src.replace(OLD_PRO, NEW_PRO, 1)
    print("[OK] main.py : patient -> /acces-refuse")
elif 'url="/acces-refuse"' in main_src:
    print("[SKIP] patient -> /acces-refuse deja applique")
else:
    print("[!] bloc 'role != PROFESSIONNEL' introuvable")

open(MAIN, "w", encoding="utf-8").write(main_src)

# ============================================================
# 4) VERIF
# ============================================================
print("\n[VERIF]")
m = open(MAIN, "r", encoding="utf-8").read()
print(f"  HTML cree                : {os.path.exists(HTML)}")
print(f"  route /acces-refuse      : {'\"/acces-refuse\"' in m}")
print(f"  patient -> /acces-refuse : {'url=\"/acces-refuse\"' in m}")
print(f"  status_code=403          : {'status_code=403' in m}")

print("\n[DONE] Phase 3c appliquee. Uvicorn --reload va recharger.")