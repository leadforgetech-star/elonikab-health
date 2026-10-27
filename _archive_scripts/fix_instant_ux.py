"""
fix_instant_ux.py
1. Cree static/prefetch.js : prefetch au survol/touch + cache API + feedback instantane
2. Injecte <script src="/static/prefetch.js"> dans toutes les pages pro
3. Ajoute CSS feedback dans professional_common.css
"""
from pathlib import Path

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

# ============================================================
# 1. Fichier prefetch.js
# ============================================================
PREFETCH_JS = r'''/* Elokinab Health - Prefetch + Cache + Feedback instantane */
(function () {
  "use strict";

  // ============================================================
  // 1. Cache memoire des requetes GET /api/*
  // ============================================================
  var apiCache = new Map();
  var CACHE_TTL = 15000; // 15 secondes

  var originalFetch = window.fetch;
  window.fetch = function (url, opts) {
    var isGetApi = (!opts || !opts.method || opts.method.toUpperCase() === "GET") &&
                   typeof url === "string" &&
                   url.indexOf("/api/") !== -1;

    if (isGetApi) {
      var key = url;
      var cached = apiCache.get(key);
      if (cached && Date.now() - cached.at < CACHE_TTL) {
        // Reponse cachee : clone pour eviter la consommation
        return Promise.resolve(new Response(cached.body, {
          status: 200,
          headers: { "Content-Type": "application/json" }
        }));
      }
      return originalFetch.apply(this, arguments).then(function (r) {
        // Cache uniquement les 200 OK
        if (r.ok) {
          var clone = r.clone();
          clone.text().then(function (body) {
            apiCache.set(key, { body: body, at: Date.now() });
          }).catch(function () {});
        }
        return r;
      });
    }

    // Requetes non-GET : invalider le cache API
    if (opts && opts.method && opts.method.toUpperCase() !== "GET") {
      apiCache.clear();
    }
    return originalFetch.apply(this, arguments);
  };

  // Nettoyer le cache toutes les 30s
  setInterval(function () {
    var now = Date.now();
    apiCache.forEach(function (v, k) {
      if (now - v.at > CACHE_TTL) apiCache.delete(k);
    });
  }, 30000);

  // ============================================================
  // 2. Prefetch pages au survol/touch
  // ============================================================
  var prefetched = new Set();

  function prefetch(href) {
    if (!href || prefetched.has(href)) return;
    if (href.indexOf("http") === 0 && href.indexOf(window.location.origin) !== 0) return;
    if (href.indexOf("#") === 0 || href.indexOf("javascript:") === 0) return;
    if (href.indexOf("/api/") === 0) return; // deja cache

    prefetched.add(href);

    // Prefetch HTML
    var link = document.createElement("link");
    link.rel = "prefetch";
    link.href = href;
    link.as = "document";
    document.head.appendChild(link);
  }

  // Au survol
  document.addEventListener("mouseover", function (ev) {
    var a = ev.target.closest ? ev.target.closest("a[href]") : null;
    if (a) prefetch(a.getAttribute("href"));
  }, { passive: true });

  // Au touch (avant le clic)
  document.addEventListener("touchstart", function (ev) {
    var a = ev.target.closest ? ev.target.closest("a[href]") : null;
    if (a) prefetch(a.getAttribute("href"));
  }, { passive: true });

  // Au mousedown (debut du clic)
  document.addEventListener("mousedown", function (ev) {
    var a = ev.target.closest ? ev.target.closest("a[href]") : null;
    if (a) prefetch(a.getAttribute("href"));
  }, { passive: true });

  // ============================================================
  // 3. Prefetch proactif des pages critiques (apres 800ms idle)
  // ============================================================
  var CRITICAL_PAGES = [
    "/professionnel",
    "/professionnel/demande",
    "/professionnel/catalogue",
    "/professionnel/commandes",
    "/professionnel/etablissement"
  ];

  function preloadCritical() {
    // Uniquement les pages pro (pas sur le site patient)
    if (window.location.pathname.indexOf("/professionnel") !== 0 &&
        window.location.pathname.indexOf("/suivi") !== 0 &&
        window.location.pathname.indexOf("/pharmacien") !== 0) {
      return;
    }
    CRITICAL_PAGES.forEach(function (p) {
      if (p !== window.location.pathname) prefetch(p);
    });
  }

  if (document.readyState === "complete") {
    setTimeout(preloadCritical, 800);
  } else {
    window.addEventListener("load", function () {
      setTimeout(preloadCritical, 800);
    }, { once: true });
  }

  // ============================================================
  // 4. Feedback visuel instantane sur tous les boutons/liens
  // ============================================================
  var style = document.createElement("style");
  style.textContent = [
    "a, button, [role=button]{",
    "  -webkit-tap-highlight-color: transparent;",
    "  touch-action: manipulation;",
    "  transition: transform .08s ease, opacity .08s ease;",
    "}",
    "a:active, button:active:not(:disabled), [role=button]:active{",
    "  transform: scale(.97);",
    "  opacity: .9;",
    "}"
  ].join("\n");
  document.head.appendChild(style);

  // ============================================================
  // 5. Notification console (debug)
  // ============================================================
  console.log("[prefetch] cache API + prefetch actifs");
})();
'''

(STATIC / "prefetch.js").write_text(PREFETCH_JS, encoding="utf-8")
print("[OK] prefetch.js cree")

# ============================================================
# 2. Injecter prefetch.js dans toutes les pages HTML pro
# ============================================================
PAGES = [
    "professional.html",
    "professional_demande.html",
    "professional_demande_confirmer.html",
    "professional_catalogue.html",
    "professional_commandes.html",
    "professional_etablissement.html",
    "professional_reprendre.html",
    "login.html",
    "register.html",
    "suivi.html",
    "payment.html",
    "notifications.html",
    "driver.html",
    "index.html",
]

count = 0
for page in PAGES:
    p = STATIC / page
    if not p.exists():
        continue
    html = p.read_text(encoding="utf-8")
    if "/static/prefetch.js" in html:
        print(f"[SKIP] {page}")
        continue
    # Inserer juste avant </head>
    if "</head>" in html:
        html = html.replace(
            "</head>",
            '<script src="/static/prefetch.js"></script>\n</head>',
            1
        )
        p.write_text(html, encoding="utf-8")
        count += 1
        print(f"[OK] {page}")

print()
print(f"[OK] prefetch.js injecte dans {count} pages")

# ============================================================
# 3. Ajouter un hint visuel dans le CSS (skeleton)
# ============================================================
CSS_PATH = STATIC / "professional_common.css"
if CSS_PATH.exists():
    css = CSS_PATH.read_text(encoding="utf-8")
    if "/* SKELETON HINT */" not in css:
        hint = '''
/* SKELETON HINT - chargement instantane */
.skeleton{
  background:linear-gradient(90deg,#f0f4f8 25%,#e2e8f0 50%,#f0f4f8 75%);
  background-size:200% 100%;
  animation:skeleton-shimmer 1.4s infinite;
  border-radius:8px;
}
@keyframes skeleton-shimmer{
  0%{background-position:200% 0}
  100%{background-position:-200% 0}
}
/* Reduit les repaints */
body{
  -webkit-font-smoothing:antialiased;
  text-rendering:optimizeSpeed;
}
'''
        css += hint
        CSS_PATH.write_text(css, encoding="utf-8")
        print("[OK] professional_common.css : styles skeleton")
    else:
        print("[i] styles skeleton deja presents")

print()
print("=" * 60)
print("UX INSTANTANE ACTIVE")
print("=" * 60)
print()
print("Ce qui se passe maintenant :")
print("  1. Cache API 15s : 2eme visite instantanee sur la meme page")
print("  2. Prefetch au survol/touch/mousedown : page deja en cache quand tu cliques")
print("  3. Prefetch proactif : les 5 pages pro sont precharges 800ms apres le load")
print("  4. Feedback visuel : tout bouton/lien 's'enfonce' au clic")
print()
print("PROCHAINE ETAPE :")
print("  1. Ctrl+Shift+R sur /professionnel")
print("  2. Navigue entre les pages : devrait etre quasi instantane")
print("  3. F12 -> Console -> tu dois voir '[prefetch] cache API + prefetch actifs'")
print("=" * 60)