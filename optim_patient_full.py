# -*- coding: utf-8 -*-
# optim_patient_full.py - Optimisation globale patient
import os, re, shutil, datetime

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
STATIC = os.path.join(ROOT, "static")

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
bak = os.path.join(ROOT, f"_backup_optim_full_{ts}")
os.makedirs(bak, exist_ok=True)

PAGES = [
    "index.html", "cart.html", "checkout.html", "payment.html",
    "suivi.html", "notifications.html", "patient_compte.html",
]

# Backup
for name in PAGES:
    p = os.path.join(STATIC, name)
    if os.path.exists(p):
        shutil.copy2(p, os.path.join(bak, name))
print(f"[BACKUP] {bak}\n")

# ============================================================
# AUDIT INITIAL
# ============================================================
print("=" * 70)
print("[AUDIT] Etat actuel")
print("=" * 70)

for name in PAGES:
    p = os.path.join(STATIC, name)
    if not os.path.exists(p):
        continue
    h = open(p, "r", encoding="utf-8").read()
    nb_css = len(re.findall(r'<link[^>]*\.css', h))
    nb_js = len(re.findall(r'<script[^>]*src=', h))
    nb_defer = len(re.findall(r'<script[^>]*\bdefer\b', h))
    nb_lazy = len(re.findall(r'loading="lazy"', h))
    print(f"  {name:<25} CSS:{nb_css}  JS:{nb_js}  defer:{nb_defer}  lazy:{nb_lazy}")

# ============================================================
# 1. Optimiser chaque HTML
# ============================================================
print("\n" + "=" * 70)
print("[1] Optimisation HTML")
print("=" * 70)

for name in PAGES:
    p = os.path.join(STATIC, name)
    if not os.path.exists(p):
        continue
    h = open(p, "r", encoding="utf-8").read()
    orig = h
    changes = []

    # --- 1a. Preconnect + dns-prefetch en haut du <head> ---
    if 'rel="preconnect"' not in h:
        PRECONNECT = '''<link rel="preconnect" href="https://con-vic-laboratory-coins.trycloudflare.com" crossorigin>
<link rel="dns-prefetch" href="https://con-vic-laboratory-coins.trycloudflare.com">
<meta name="theme-color" content="#174A7E">
'''
        if "<head>" in h:
            h = h.replace("<head>", "<head>\n" + PRECONNECT, 1)
            changes.append("preconnect")

    # --- 1b. Preload du CSS principal ---
    if 'rel="preload"' not in h and 'patient_common.css' in h:
        # Preload du CSS patient_common (critique pour toutes les pages)
        PRELOAD = '<link rel="preload" href="/static/patient_common.css?v=8" as="style">\n'
        if "</head>" in h:
            h = h.replace("</head>", PRELOAD + "</head>", 1)
            changes.append("preload css")

    # --- 1c. Defer sur les scripts non-critiques ---
    # safe_locale.js doit rester sync (polyfills)
    # Les autres peuvent etre defer
    def add_defer(match):
        tag = match.group(0)
        if 'defer' in tag or 'async' in tag:
            return tag
        if 'safe_locale.js' in tag:
            return tag
        # Ajouter defer
        return tag.replace('<script ', '<script defer ')

    h2 = re.sub(r'<script[^>]*\bsrc=[^>]*>', add_defer, h)
    if h2 != h:
        h = h2
        changes.append("defer")

    # --- 1d. Fetchpriority sur le logo (s'il y en a un visible) ---
    if 'fetchpriority' not in h and 'pt-mini-logo' in h:
        # Le logo est un span, pas une img. Skip.

    # --- 1e. Meta viewport avec interactive-widget si form ---
    if 'order-form' in h or 'f-phone' in h:
        if 'interactive-widget' not in h:
            h = h.replace(
                'content="width=device-width,initial-scale=1"',
                'content="width=device-width,initial-scale=1,interactive-widget=resizes-content"',
                1
            )
            changes.append("viewport widget")

    if h != orig:
        open(p, "w", encoding="utf-8").write(h)
        print(f"  [OK] {name} : {', '.join(changes)}")
    else:
        print(f"  [SKIP] {name} : deja optimise")

# ============================================================
# 2. Skeleton loaders CSS + JS
# ============================================================
print("\n" + "=" * 70)
print("[2] Skeleton loaders")
print("=" * 70)

# CSS skeleton dans patient_common.css
CSS = os.path.join(STATIC, "patient_common.css")
css = open(CSS, "r", encoding="utf-8").read()

if ".pt-skeleton" in css:
    print("  [SKIP] CSS skeleton deja present")
else:
    SKELETON_CSS = '''

/* ============================================================
   Skeleton loaders (perception de vitesse)
   ============================================================ */
.pt-skeleton{
  background:linear-gradient(90deg,#EEF2F7 25%,#E2E8F0 50%,#EEF2F7 75%);
  background-size:200% 100%;
  animation:ptShimmer 1.4s infinite linear;
  border-radius:8px;
}
@keyframes ptShimmer{
  0%{background-position:200% 0}
  100%{background-position:-200% 0}
}
.pt-skeleton-card{
  background:#fff;border:1px solid #E2E8F0;border-radius:14px;
  padding:16px;margin-bottom:12px;
}
.pt-skeleton-line{
  height:12px;margin-bottom:8px;
}
.pt-skeleton-line.short{width:40%}
.pt-skeleton-line.medium{width:70%}
.pt-skeleton-title{
  height:16px;width:60%;margin-bottom:14px;
}
.pt-skeleton-thumb{
  width:56px;height:56px;border-radius:10px;
}
.pt-skeleton-row{
  display:flex;gap:12px;align-items:center;margin-bottom:14px;
}

/* Cart item skeleton */
.pt-skeleton-item{
  display:grid;grid-template-columns:60px 1fr auto;gap:12px;
  align-items:center;padding:16px 0;
  border-bottom:1px solid #E2E8F0;
}
.pt-skeleton-item:last-child{border-bottom:0}
.pt-skeleton-item .pt-skeleton-thumb{
  width:60px;height:60px;
}
.pt-skeleton-item .pt-skeleton-body{
  display:flex;flex-direction:column;gap:8px;
}

/* Optimisation rendu des longues listes */
.pt-product-card,
.pt-notif,
.pt-order-card{
  content-visibility:auto;
  contain-intrinsic-size:auto 120px;
}
.pt-product-card{contain-intrinsic-size:auto 280px}

/* Optimisation animations */
.pt-mini-header,
.pn-navbar,
.pt-btn,
.pt-product-card,
.pt-notif{
  will-change:transform;
  backface-visibility:hidden;
  -webkit-backface-visibility:hidden;
}
'''
    css = css.rstrip() + SKELETON_CSS
    open(CSS, "w", encoding="utf-8").write(css)
    print("  [OK] patient_common.css : skeleton + content-visibility")

# ============================================================
# 3. Remplacer "Chargement..." par des skeletons
# ============================================================
print("\n" + "=" * 70)
print("[3] Remplacement des loaders bruts")
print("=" * 70)

SKELETON_HTML = '''<div class="pt-skeleton-card">
    <div class="pt-skeleton pt-skeleton-title"></div>
    <div class="pt-skeleton-row">
      <div class="pt-skeleton pt-skeleton-thumb"></div>
      <div style="flex:1">
        <div class="pt-skeleton pt-skeleton-line medium"></div>
        <div class="pt-skeleton pt-skeleton-line short"></div>
      </div>
    </div>
    <div class="pt-skeleton-row">
      <div class="pt-skeleton pt-skeleton-thumb"></div>
      <div style="flex:1">
        <div class="pt-skeleton pt-skeleton-line medium"></div>
        <div class="pt-skeleton pt-skeleton-line short"></div>
      </div>
    </div>
    <div class="pt-skeleton-row">
      <div class="pt-skeleton pt-skeleton-thumb"></div>
      <div style="flex:1">
        <div class="pt-skeleton pt-skeleton-line medium"></div>
        <div class="pt-skeleton pt-skeleton-line short"></div>
      </div>
    </div>
  </div>'''

for name in ("cart.html", "checkout.html", "patient_compte.html"):
    p = os.path.join(STATIC, name)
    if not os.path.exists(p):
        continue
    h = open(p, "r", encoding="utf-8").read()

    # Remplacer <div class="pt-loading">Chargement...</div>
    OLD_LOADING = re.compile(r'<div class="pt-loading">Chargement\.\.\.</div>')
    NEW_LOADING = '<div id="main">' + SKELETON_HTML + '</div>'

    # Attention : ne pas doubler le div main
    if '<div class="pt-loading">Chargement...</div>' in h:
        h = h.replace(
            '<div class="pt-loading">Chargement...</div>',
            SKELETON_HTML,
            1
        )
        open(p, "w", encoding="utf-8").write(h)
        print(f"  [OK] {name} : loader -> skeleton")

# ============================================================
# 4. Lazy loading images dans app.js + cart.js
# ============================================================
print("\n" + "=" * 70)
print("[4] Lazy loading images")
print("=" * 70)

for name in ("app.js", "cart.js", "checkout.js"):
    p = os.path.join(STATIC, name)
    if not os.path.exists(p):
        continue
    js = open(p, "r", encoding="utf-8").read()
    orig = js

    # Ajouter loading="lazy" decoding="async" sur les <img> creees
    # Dans app.js : img.loading = "lazy" existe deja
    if 'img.loading = "lazy"' in js and 'img.decoding' not in js:
        js = js.replace(
            'img.loading = "lazy";',
            'img.loading = "lazy";\n    img.decoding = "async";\n    img.fetchPriority = "low";',
            1
        )
        print(f"  [OK] {name} : decoding async sur img")

    # Pour cart.js / checkout.js : img creees via innerHTML
    if 'loading="lazy"' not in js and '<img' in js:
        # Ajouter loading="lazy" decoding="async" dans les templates
        js = js.replace('<img ', '<img loading="lazy" decoding="async" ', 5)
        print(f"  [OK] {name} : loading lazy dans templates")

    if js != orig:
        open(p, "w", encoding="utf-8").write(js)

# ============================================================
# 5. Prefetch au touch sur la navbar
# ============================================================
print("\n" + "=" * 70)
print("[5] Prefetch navigation")
print("=" * 70)

NAV = os.path.join(STATIC, "patient_nav.js")
if os.path.exists(NAV):
    nav = open(NAV, "r", encoding="utf-8").read()
    if "prefetchHref" in nav:
        print("  [SKIP] patient_nav.js : prefetch deja present")
    else:
        PREFETCH_FN = '''

/* Prefetch des pages au survol/touch de la navbar */
function prefetchHref(href) {
  if (!href || href === "#") return;
  if (href.indexOf("http") === 0) return;
  try {
    var link = document.createElement("link");
    link.rel = "prefetch";
    link.href = href;
    link.as = "document";
    document.head.appendChild(link);
  } catch (e) {}
}

document.addEventListener("mouseover", function (ev) {
  var a = ev.target && ev.target.closest ? ev.target.closest(".pn-navbar a") : null;
  if (a && a.href) prefetchHref(a.getAttribute("href"));
}, { passive: true });

document.addEventListener("touchstart", function (ev) {
  var a = ev.target && ev.target.closest ? ev.target.closest(".pn-navbar a") : null;
  if (a && a.href) prefetchHref(a.getAttribute("href"));
}, { passive: true });
'''
        # Inserer avant window.PatientNav
        MARKER = "  // API publique"
        if MARKER in nav:
            nav = nav.replace(MARKER, PREFETCH_FN + "\n" + MARKER, 1)
            open(NAV, "w", encoding="utf-8").write(nav)
            print("  [OK] patient_nav.js : prefetch navigation")

# ============================================================
# 6. Bump versions partout
# ============================================================
print("\n" + "=" * 70)
print("[6] Bump versions")
print("=" * 70)

NEW_VER = "18"
for name in PAGES:
    p = os.path.join(STATIC, name)
    if not os.path.exists(p):
        continue
    h = open(p, "r", encoding="utf-8").read()
    orig = h
    h = re.sub(r'(app\.js\?v=)[\d.]+', r'\g<1>' + NEW_VER, h)
    h = re.sub(r'(cart\.js\?v=)[\d.]+', r'\g<1>' + NEW_VER, h)
    h = re.sub(r'(checkout\.js\?v=)[\d.]+', r'\g<1>' + NEW_VER, h)
    h = re.sub(r'(payment\.js\?v=)[\d.]+', r'\g<1>' + NEW_VER, h)
    h = re.sub(r'(suivi\.js\?v=)[\d.]+', r'\g<1>' + NEW_VER, h)
    h = re.sub(r'(notifications\.js\?v=)[\d.]+', r'\g<1>' + NEW_VER, h)
    h = re.sub(r'(patient_nav\.js\?v=)[\d.]+', r'\g<1>10', h)
    h = re.sub(r'(professional_realtime\.js\?v=)[\d.]+', r'\g<1>8', h)
    h = re.sub(r'(patient_common\.css\?v=)[\d.]+', r'\g<1>9', h)
    h = re.sub(r'(patient_nav\.css\?v=)[\d.]+', r'\g<1>8', h)
    h = re.sub(r'(patient_home\.css\?v=)[\d.]+', r'\g<1>3', h)
    if h != orig:
        open(p, "w", encoding="utf-8").write(h)
print(f"  [OK] versions bumpees (v={NEW_VER})")

# ============================================================
# VERIF FINALE
# ============================================================
print("\n" + "=" * 70)
print("VERIFICATION FINALE")
print("=" * 70)

for name in PAGES:
    p = os.path.join(STATIC, name)
    if not os.path.exists(p):
        continue
    h = open(p, "r", encoding="utf-8").read()
    checks = [
        ("preconnect", 'rel="preconnect"' in h),
        ("defer", bool(re.search(r'<script[^>]*\bdefer\b', h))),
        ("v=18", "?v=18" in h or "?v=10" in h),
    ]
    flags = "".join("[OK]" if ok else "[--]" for _, ok in checks)
    print(f"  {flags} {name}")

print(f"\n[BACKUP] {bak}")
print("\n[CMD] Pas de restart Uvicorn.")
print("Edge > F12 > Network > Disable cache > Ctrl+Shift+R")
print("\n[TEST]")
print("  1) / : chargement plus rapide (defer + preconnect)")
print("  2) /static/cart.html : skeleton shimmer pendant le chargement")
print("  3) Hover sur la navbar : prefetch des pages")
print("  4) F12 Network : verifier que les CSS/JS se chargent en parallele")