/* Elonikab Health - Prefetch + Cache + Feedback instantane */
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
