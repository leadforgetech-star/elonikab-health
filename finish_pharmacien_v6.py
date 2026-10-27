# -*- coding: utf-8 -*-
# finish_pharmacien_v6.py
# Design V6 bleu pour l'espace pharmacien (override CSS safe + perfs)
import os, re, shutil, datetime

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
STATIC = os.path.join(ROOT, "static")
HTML = os.path.join(STATIC, "pharmacien.html")
CSS_MAIN = os.path.join(STATIC, "pharmacien.css")
CSS_NEW = os.path.join(STATIC, "pharmacien_common.css")

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
bak = os.path.join(ROOT, f"_backup_pharm_v6_{ts}")
os.makedirs(bak, exist_ok=True)
shutil.copy2(HTML, os.path.join(bak, "pharmacien.html.bak"))
shutil.copy2(CSS_MAIN, os.path.join(bak, "pharmacien.css.bak"))
print(f"[BACKUP] {bak}\n")

# ============================================================
# 1. CREER pharmacien_common.css (override V6 bleu)
# ============================================================
print("=" * 70)
print("[1] Creation pharmacien_common.css")
print("=" * 70)

V6_CSS = '''/* ============================================================
   Elonikab Health - Pharmacien V6 BLEU
   Override CSS : palette bleue coherente avec patient + pro
   Charge APRES pharmacien.css pour surcharger les anciens verts.
   ============================================================ */
:root{
  --ph-blue:#174A7E;
  --ph-blue-dark:#0F3457;
  --ph-blue-soft:#E8F0F8;
  --ph-blue-mid:#2A6BA8;
  --ph-ink:#0F172A;
  --ph-muted:#64748B;
  --ph-line:#E2E8F0;
  --ph-bg:#F5F8FC;
  --ph-white:#ffffff;
  --ph-ok:#0A7A5A;
  --ph-ok-soft:#E6F7F1;
  --ph-warn:#B26B00;
  --ph-warn-soft:#FFF4E0;
  --ph-danger:#B23C3C;
  --ph-danger-soft:#FDE8E8;

  /* Override des variables vertes existantes (fallback) */
  --blue:#174A7E;
  --blue-dark:#0F3457;
  --blue-soft:#E8F0F8;
  --green:#174A7E;
  --green-dark:#0F3457;
  --green-soft:#E8F0F8;
}

/* ============================================================
   FOND + TYPO
   ============================================================ */
html,body{
  background:var(--ph-bg)!important;
  color:var(--ph-ink)!important;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif!important;
}

/* ============================================================
   TOPBAR / HEADER
   ============================================================ */
.topbar{
  background:#fff!important;
  border-bottom:1px solid var(--ph-line)!important;
  box-shadow:0 2px 8px rgba(15,23,42,.04)!important;
}
.brand-logo{
  background:linear-gradient(135deg,var(--ph-blue),var(--ph-blue-mid))!important;
  color:#fff!important;
}
.brand-text strong{color:var(--ph-ink)!important}
.brand-text small{color:var(--ph-muted)!important}

/* ============================================================
   BOUTONS
   ============================================================ */
.btn-primary{
  background:var(--ph-blue)!important;
  border-color:var(--ph-blue)!important;
  color:#fff!important;
}
.btn-primary:hover:not(:disabled){
  background:var(--ph-blue-dark)!important;
  border-color:var(--ph-blue-dark)!important;
}
.btn-ghost{
  background:#fff!important;
  border-color:var(--ph-line)!important;
  color:var(--ph-ink)!important;
}
.btn-ghost:hover{
  border-color:var(--ph-blue)!important;
  color:var(--ph-blue)!important;
}
button.primary,
button[class*="primary"]{
  background:var(--ph-blue)!important;
}

/* ============================================================
   CHIPS / FILTRES
   ============================================================ */
.chip{
  background:#fff!important;
  border-color:var(--ph-line)!important;
  color:var(--ph-muted)!important;
}
.chip:hover{
  border-color:var(--ph-blue)!important;
  color:var(--ph-blue)!important;
}
.chip-active{
  background:var(--ph-blue)!important;
  border-color:var(--ph-blue)!important;
  color:#fff!important;
}

/* ============================================================
   CARDS COMMANDES
   ============================================================ */
.order-card,
.orders-grid > *,
[class*="order-card"],
[class*="card-order"]{
  background:#fff!important;
  border:1px solid var(--ph-line)!important;
  border-radius:14px!important;
  box-shadow:0 4px 16px rgba(15,23,42,.04)!important;
  transition:.15s!important;
}
.order-card:hover,
.orders-grid > *:hover{
  border-color:var(--ph-blue)!important;
  box-shadow:0 10px 28px rgba(23,74,126,.1)!important;
  transform:translateY(-2px)!important;
}

/* ============================================================
   STATS (dashboard)
   ============================================================ */
[class*="stat-"],
.stat-card,
.stat-box{
  background:#fff!important;
  border:1px solid var(--ph-line)!important;
  border-radius:14px!important;
}
[class*="stat-"] strong,
.stat-value{
  color:var(--ph-blue-dark)!important;
}

/* ============================================================
   PILLS STATUTS (override complets)
   ============================================================ */
[class*="pill-pending"],
.pill-pending,
[class*="statut-en_attente"]{
  background:var(--ph-warn-soft)!important;
  color:var(--ph-warn)!important;
}
[class*="pill-confirmed"],
.pill-confirmed,
[class*="statut-confirmee"],
[class*="pill-ok"]{
  background:var(--ph-ok-soft)!important;
  color:var(--ph-ok)!important;
}
[class*="pill-preparing"],
.pill-preparing,
[class*="statut-en_preparation"]{
  background:#F3E8FF!important;
  color:#6335B8!important;
}
[class*="pill-ready"],
.pill-ready,
[class*="statut-prete"]{
  background:var(--ph-ok-soft)!important;
  color:var(--ph-ok)!important;
}
[class*="pill-in-delivery"],
[class*="statut-en_livraison"],
.pill-in-delivery{
  background:#E0F2FE!important;
  color:#0369A1!important;
}
[class*="pill-done"],
.pill-done,
[class*="statut-terminee"]{
  background:#E2E8F0!important;
  color:#475569!important;
}
[class*="pill-refused"],
.pill-refused,
[class*="statut-refusee"]{
  background:var(--ph-danger-soft)!important;
  color:var(--ph-danger)!important;
}

/* ============================================================
   MODALS
   ============================================================ */
.modal-content{
  border-radius:16px!important;
  box-shadow:0 20px 60px rgba(15,23,42,.25)!important;
}
.modal-head{
  border-bottom:1px solid var(--ph-line)!important;
}
.modal-foot{
  border-top:1px solid var(--ph-line)!important;
  background:var(--ph-bg)!important;
}

/* ============================================================
   ALERTS
   ============================================================ */
.alert{
  background:var(--ph-danger-soft)!important;
  color:var(--ph-danger)!important;
  border-color:#f6d2d2!important;
}
.alert-info{
  background:var(--ph-blue-soft)!important;
  color:var(--ph-blue-dark)!important;
  border-color:#c7d8ec!important;
}

/* ============================================================
   INPUTS
   ============================================================ */
input[type="text"],
input[type="tel"],
input[type="number"],
input[type="email"],
textarea,
select{
  border:1.5px solid var(--ph-line)!important;
  border-radius:10px!important;
  font-family:inherit!important;
}
input:focus,
textarea:focus,
select:focus{
  border-color:var(--ph-blue)!important;
  box-shadow:0 0 0 3px var(--ph-blue-soft)!important;
  outline:none!important;
}

/* ============================================================
   SECTION TITLES
   ============================================================ */
.page-head h1,
.admin-title,
h1,h2,h3{
  color:var(--ph-ink);
}
.muted{color:var(--ph-muted)!important}

/* ============================================================
   RECHERCHE
   ============================================================ */
input[type="search"]{
  border:1.5px solid var(--ph-line)!important;
  border-radius:11px!important;
}
input[type="search"]:focus{
  border-color:var(--ph-blue)!important;
  box-shadow:0 0 0 3px var(--ph-blue-soft)!important;
}

/* ============================================================
   BACKGROUND UNIFIE
   ============================================================ */
.container{
  background:transparent!important;
}
.page-head{
  background:transparent!important;
}

/* ============================================================
   RESPONSIVE
   ============================================================ */
@media (max-width:720px){
  .page-head h1{font-size:22px}
  .admin-title{font-size:18px}
  .modal-content{
    max-width:95vw!important;
    border-radius:14px!important;
  }
}
'''

with open(CSS_NEW, "w", encoding="utf-8") as f:
    f.write(V6_CSS)
print(f"[OK] {CSS_NEW} cree ({len(V6_CSS)} octets)")

# ============================================================
# 2. HTML : preconnect + theme-color + lien CSS V6
# ============================================================
print("\n" + "=" * 70)
print("[2] Injection CSS V6 dans pharmacien.html")
print("=" * 70)

html = open(HTML, "r", encoding="utf-8").read()
changes = []

# 2a. Preconnect + theme-color
if 'rel="preconnect"' not in html:
    PRE = '''<link rel="preconnect" href="https://filed-sauce-tab-ensemble.trycloudflare.com" crossorigin>
<meta name="theme-color" content="#174A7E">
'''
    if "<head>" in html:
        html = html.replace("<head>", "<head>\n" + PRE, 1)
        changes.append("preconnect")

# 2b. Lien vers pharmacien_common.css (apres pharmacien.css)
if "pharmacien_common.css" not in html:
    # Chercher la ligne du pharmacien.css pour inserer juste apres
    match = re.search(r'<link[^>]*href="[^"]*pharmacien\.css[^"]*"[^>]*>', html)
    if match:
        insert_after = match.end()
        new_link = '\n  <link rel="stylesheet" href="/static/pharmacien_common.css?v=1">'
        html = html[:insert_after] + new_link + html[insert_after:]
        changes.append("pharmacien_common.css")
    else:
        # Fallback : avant </head>
        html = html.replace("</head>",
            '  <link rel="stylesheet" href="/static/pharmacien_common.css?v=1">\n</head>',
            1)
        changes.append("pharmacien_common.css (fallback)")

# 2c. Defer sur les scripts non-critiques
def add_defer(match):
    tag = match.group(0)
    if 'defer' in tag or 'async' in tag:
        return tag
    if 'safe_locale.js' in tag:
        return tag
    return tag.replace('<script ', '<script defer ')

html_before = html
html = re.sub(r'<script[^>]*\bsrc=[^>]*>', add_defer, html)
if html != html_before:
    changes.append("defer")

# 2d. Bump versions
html = re.sub(r'(pharmacien\.js\?v=)[\d.]+', r'\g<1>29', html)
html = re.sub(r'(pharmacien\.css\?v=)[\d.]+', r'\g<1>29', html)
html = re.sub(r'(header\.css\?v=)[\d.]+', r'\g<1>29', html)
html = re.sub(r'(style\.css\?v=)[\d.]+', r'\g<1>29', html)
html = re.sub(r'(mobile\.css\?v=)[\d.]+', r'\g<1>29', html)
changes.append("versions bump 29")

open(HTML, "w", encoding="utf-8").write(html)
print(f"[OK] Changes : {', '.join(changes)}")

# ============================================================
# 3. VERIF
# ============================================================
print("\n" + "=" * 70)
print("VERIFICATION")
print("=" * 70)

html_v = open(HTML, "r", encoding="utf-8").read()
css_v = open(CSS_NEW, "r", encoding="utf-8").read()

checks = [
    ("pharmacien_common.css existe", os.path.exists(CSS_NEW)),
    ("CSS : variables V6", "--ph-blue:#174A7E" in css_v),
    ("CSS : override .btn-primary", "btn-primary" in css_v),
    ("CSS : pills statuts", "pill-pending" in css_v and "pill-in-delivery" in css_v),
    ("HTML : lien pharmacien_common.css", "pharmacien_common.css" in html_v),
    ("HTML : preconnect", 'rel="preconnect"' in html_v),
    ("HTML : theme-color bleu", 'content="#174A7E"' in html_v),
    ("HTML : defer sur scripts", bool(re.search(r'<script[^>]*\bdefer\b', html_v))),
    ("HTML : version pharmacien.css=29", "pharmacien.css?v=29" in html_v),
]
all_ok = True
for label, ok in checks:
    if not ok: all_ok = False
    print(f"  [{'OK' if ok else '!!'}] {label}")

print("\n" + "=" * 70)
if all_ok:
    print("DESIGN V6 PHARMACIEN APPLIQUE")
else:
    print("PATCH PARTIEL - verifie ci-dessus")
print("=" * 70)

print(f"\n[BACKUP] {bak}")
print("\n[CMD] Pas de restart Uvicorn (static only).")
print("Edge > F12 > Network > Disable cache > Ctrl+Shift+R")
print("sur https://filed-sauce-tab-ensemble.trycloudflare.com/pharmacien")
print("\n[TEST]")
print("  - Header : logo bleu degrade")
print("  - Boutons primary : bleu V6")
print("  - Chips filtres : actif en bleu")
print("  - Cards commandes : bordure bleue au hover")
print("  - Pills statuts : memes couleurs que patient/pro")
print("  - Modales : propre + fond gris clair en bas")