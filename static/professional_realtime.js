/* ============================================================
   SSE AUTH GUARD V3 - Fix Lot 1 (2026-10-15)
   V3 : queue les addEventListener (V2 les perdait).
   ============================================================ */
(function(){
  if (typeof window === "undefined" || !window.EventSource) return;
  if (window.__ehSseGuardV3Installed) return;
  window.__ehSseGuardV3Installed = true;

  var _Orig = window.EventSource;
  var STREAM_PATH = "/api/notifications/stream";
  window.ehUserAuthenticated = null;

  window.EventSource = function(url, config) {
    var u = String(url || "");
    if (u.indexOf(STREAM_PATH) < 0) {
      return new _Orig(url, config);
    }

    var real = null;
    var closed = false;
    var handlers = { onopen: null, onmessage: null, onerror: null };
    // Queue pour les listeners ajoutes AVANT que real existe
    var pendingListeners = [];

    function wrap(fn) {
      if (typeof fn !== "function") return fn;
      return function(ev) {
        if (window.ehUserAuthenticated === false) return;
        return fn.call(this, ev);
      };
    }

    function attachListener(t, fn) {
      var w = wrap(fn);
      if (real) {
        try { real.addEventListener(t, w); } catch(e) {}
      } else {
        pendingListeners.push([t, w]);
      }
    }

    function detachListener(t, fn) {
      // Retirer de la queue si pas encore attache
      pendingListeners = pendingListeners.filter(function(item) {
        return !(item[0] === t && item[1] === fn);
      });
      if (real) {
        try { real.removeEventListener(t, fn); } catch(e) {}
      }
    }

    var wrapper = {
      url: u,
      withCredentials: !!(config && config.withCredentials),
      readyState: 0,
      addEventListener: function(t, fn) { attachListener(t, fn); },
      removeEventListener: function(t, fn) { detachListener(t, fn); },
      dispatchEvent: function(ev) { return real ? real.dispatchEvent(ev) : true; },
      close: function() {
        closed = true;
        if (real) real.close();
        wrapper.readyState = 2;
      }
    };

    ["onopen", "onmessage", "onerror"].forEach(function(k) {
      Object.defineProperty(wrapper, k, {
        get: function() { return handlers[k]; },
        set: function(v) {
          var w = wrap(v);
          handlers[k] = w;
          if (real) real[k] = w;
        },
        configurable: true
      });
    });

    fetch("/api/auth/me", { credentials: "same-origin" })
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(user) {
        if (closed) return;
        if (!user) {
          window.ehUserAuthenticated = false;
          try { console.log("[sse-guard-v3] Non connecte -> onerror neutralise"); } catch(_) {}
          return;
        }
        window.ehUserAuthenticated = true;
        try {
          real = new _Orig(url, config);
          // Re-appliquer les on* handlers
          ["onopen", "onmessage", "onerror"].forEach(function(k) {
            if (handlers[k]) real[k] = handlers[k];
          });
          // Re-appliquer la queue de listeners
          pendingListeners.forEach(function(item) {
            try { real.addEventListener(item[0], item[1]); } catch(e) {}
          });
          try { console.log("[sse-guard-v3] Connecte -> SSE ouvert (" + pendingListeners.length + " listeners)"); } catch(_) {}
          pendingListeners = [];
          wrapper.readyState = 0;
        } catch(e) { try { console.log("[sse-guard-v3] Erreur creation:", e); } catch(_) {} }
      })
      .catch(function() {
        window.ehUserAuthenticated = false;
      });

    return wrapper;
  };

  window.EventSource.CONNECTING = 0;
  window.EventSource.OPEN = 1;
  window.EventSource.CLOSED = 2;
  window.EventSource.prototype = _Orig.prototype;
})();
/* ============================================================
   FIN SSE AUTH GUARD V3
   ============================================================ */





/* Elonikab Health - Temps reel pro V3 (SSE + toast + soft refresh via event) */
(function () {
  "use strict";

  var API = "/api";
  var _sse = null;
  var _retryTimer = null;
  var _toastId = 0;

  /* ============================================================
     TOAST
     ============================================================ */
  function ensureToastStyles() {
    if (document.getElementById("eh-pro-toast-style")) return;
    var s = document.createElement("style");
    s.id = "eh-pro-toast-style";
    s.textContent = [
      ".eh-pro-toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);",
      "background:#fff;border:1px solid #E2E8F0;border-left:4px solid #174A7E;",
      "border-radius:12px;padding:13px 18px;box-shadow:0 14px 40px rgba(15,23,42,.18);",
      "z-index:10000;max-width:min(420px,90vw);animation:ehProIn .25s ease-out;",
      "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;",
      "cursor:pointer}",
      ".eh-pro-toast-title{font-weight:800;font-size:13.5px;color:#0F172A;margin-bottom:3px}",
      ".eh-pro-toast-body{font-size:12.5px;color:#64748B;line-height:1.45}",
      ".eh-pro-toast.out{animation:ehProOut .28s ease-in forwards}",
      "@keyframes ehProIn{from{opacity:0;transform:translate(-50%,10px)}to{opacity:1;transform:translate(-50%,0)}}",
      "@keyframes ehProOut{from{opacity:1;transform:translate(-50%,0)}to{opacity:0;transform:translate(-50%,10px)}}",
      ".eh-flash-update{animation:ehFlash .8s ease-out!important}",
      "@keyframes ehFlash{0%{background:#FEF3C7}100%{background:transparent}}"
    ].join("");
    document.head.appendChild(s);
  }

  function showToast(title, body, orderId) {
    ensureToastStyles();
    var t = document.createElement("div");
    t.className = "eh-pro-toast";
    t.dataset.tid = String(++_toastId);
    var ttl = document.createElement("div");
    ttl.className = "eh-pro-toast-title";
    ttl.textContent = title || "Notification";
    var bd = document.createElement("div");
    bd.className = "eh-pro-toast-body";
    bd.textContent = body || "";
    t.appendChild(ttl);
    t.appendChild(bd);
    if (orderId) {
      t.addEventListener("click", function () {
        window.location.href = "/professionnel/commandes";
      });
    }
    document.body.appendChild(t);
    setTimeout(function () {
      t.classList.add("out");
      setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 300);
    }, 6000);
  }

  /* ============================================================
     BADGE
     ============================================================ */
  function refreshBadge() {
    fetch(API + "/notifications?unread_only=1", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (list) {
        if (!Array.isArray(list)) return;
        var n = list.length;
        // Cible UNIQUEMENT les badges de la navbar / header
        var ids = ["pt-bell-badge", "pn-cart-badge"];
        // Cible #pt-bell-badge si present
        var bell = document.getElementById("pt-bell-badge");
        if (bell) {
          if (n > 0) {
            bell.textContent = n > 99 ? "99+" : String(n);
            bell.classList.remove("hidden");
          } else {
            bell.textContent = "";
            bell.classList.add("hidden");
          }
        }
      })
      .catch(function () {});
  }

  /* ============================================================
     SSE
     ============================================================ */
  function connectSSE() {
    if (_sse) return;
    if (typeof EventSource === "undefined") return;
    try {
      _sse = new EventSource(API + "/notifications/stream", { withCredentials: true });
    } catch (e) { _sse = null; return; }

    _sse.addEventListener("message", function (ev) {
      try {
        var data = JSON.parse(ev.data);
        showToast(data.title, data.body, data.order_id);
        refreshBadge();
        // Soft refresh : signaler aux autres scripts
        try {
          document.dispatchEvent(new CustomEvent("eh:refresh", {
            detail: data
          }));
        } catch (e) {}
      } catch (e) {}
    });

    _sse.onerror = function () {
      if (_sse) { try { _sse.close(); } catch (e) {} _sse = null; }
      if (_retryTimer) clearTimeout(_retryTimer);
      _retryTimer = setTimeout(connectSSE, 4000);
    };
  }

  function init() {
    fetch(API + "/auth/me", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (user) {
        if (!user) return;
        refreshBadge();
        setTimeout(connectSSE, 300);
      })
      .catch(function () {});
  }

  // Safari iOS : reconnexion SSE au retour de veille/arriere-plan
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible") {
      if (_sse && _sse.readyState === EventSource.CLOSED) {
        _sse = null;
        connectSSE();
      } else if (!_sse) {
        connectSSE();
      }
    }
  });
  window.addEventListener("pageshow", function (ev) {
    // Safari iOS : evenement declenche au retour de back-forward cache
    if (!_sse) connectSSE();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
