/* Elonikab Health - Header unifie (injecteur) */
(function () {
  var API = "/api";

  function el(tag, cls, txt) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (txt !== undefined && txt !== null) n.textContent = txt;
    return n;
  }

  function fetchJson(path) {
    return fetch(API + path, { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
  }

  var ROLE_LABELS = {
    PATIENT: "Particulier",
    PROFESSIONNEL: "Professionnel",
    PHARMACIEN: "Pharmacien",
    ADMIN: "Administrateur",
    LIVREUR_MOTO: "Livreur moto",
    CHAUFFEUR: "Chauffeur"
  };

  function buildUserActions(user, cartCount, notifCount) {
    var wrap = el("div", "eh-user-actions");

    // Bouton Suivre ma commande
    var track = el("a", "eh-track-btn");
    track.href = "/suivi";
    track.title = "Suivre ma commande";
    track.innerHTML = '<span class="eh-track-icon">&#128230;</span> Suivre ma commande';
    wrap.appendChild(track);

    if (user) {
      if (user.role === "PATIENT" || user.role === "PROFESSIONNEL") {
        var cart = el("a", "eh-icon-btn");
        cart.href = "/static/cart.html";
        cart.title = "Panier";
        cart.innerHTML = '&#128722;';
        var cBadge = el("span", "eh-badge eh-cart-count" + (cartCount > 0 ? "" : " hidden"));
        cBadge.textContent = cartCount > 99 ? "99+" : String(cartCount);
        cart.appendChild(cBadge);
        wrap.appendChild(cart);
      }

      var bell = el("a", "eh-icon-btn");
      bell.href = "/static/notifications.html";
      bell.title = "Notifications";
      bell.innerHTML = '&#128276;';
      var nBadge = el("span", "eh-badge eh-notif-count" + (notifCount > 0 ? "" : " hidden"));
      nBadge.textContent = notifCount > 99 ? "99+" : String(notifCount);
      bell.appendChild(nBadge);
      wrap.appendChild(bell);

      var menu = el("div", "eh-user-menu");
      var trigger = el("button", "eh-user-trigger");
      trigger.type = "button";
      trigger.textContent = (user.full_name || user.email || "Compte").slice(0, 18);
      var dd = el("div", "eh-dropdown hidden");
      var head = el("div", "eh-drop-user");
      head.innerHTML = (user.full_name || user.email) +
        '<br><small>' + (ROLE_LABELS[user.role] || user.role) + '</small>';
      dd.appendChild(head);

      if (user.role === "PHARMACIEN" || user.role === "ADMIN") {
        var a = el("a", null, "Tableau de bord");
        a.href = "/pharmacien";
        dd.appendChild(a);
      }
      if (user.role === "PROFESSIONNEL") {
        var a = el("a", null, "Ma structure");
        a.href = "/professionnel";
        dd.appendChild(a);
      }
      var a2 = el("a", null, "Mes notifications");
      a2.href = "/static/notifications.html";
      dd.appendChild(a2);
      var a3 = el("a", null, "Mon panier");
      a3.href = "/static/cart.html";
      if (user.role === "PATIENT" || user.role === "PROFESSIONNEL") dd.appendChild(a3);
      var a4 = el("a", null, "Mes commandes");
      a4.href = "/suivi";
      dd.appendChild(a4);
      var a5 = el("a", null, "Site patient");
      a5.href = "/";
      dd.appendChild(a5);

      var logout = el("button", null, "Deconnexion");
      logout.type = "button";
      logout.addEventListener("click", function () {
        try { localStorage.removeItem("eh_user_cache"); } catch (e) {}
        fetch(API + "/auth/logout", { method: "POST", credentials: "same-origin" })
          .then(function () { window.location.href = "/"; });
      });
      dd.appendChild(logout);

      menu.appendChild(trigger);
      menu.appendChild(dd);
      wrap.appendChild(menu);

      trigger.addEventListener("click", function (e) {
        e.stopPropagation();
        dd.classList.toggle("hidden");
      });
      document.addEventListener("click", function (e) {
        if (!menu.contains(e.target)) dd.classList.add("hidden");
      });
    } else {
      var login = el("a", "eh-link-btn", "Connexion");
      login.href = "/connexion";
      var reg = el("a", "eh-link-btn primary", "Inscription");
      reg.href = "/inscription";
      wrap.appendChild(login);
      wrap.appendChild(reg);
    }

    return wrap;
  }

  // Cache local du user (evite 1 requete /auth/me a chaque page)
  function getCachedUser() {
    try {
      var raw = localStorage.getItem("eh_user_cache");
      if (!raw) return null;
      var obj = JSON.parse(raw);
      if (!obj || !obj._at) return null;
      if (Date.now() - obj._at > 5 * 60 * 1000) return null; // 5 min
      return obj.user || null;
    } catch (e) { return null; }
  }
  function setCachedUser(user) {
    try {
      if (user) {
        localStorage.setItem("eh_user_cache", JSON.stringify({ user: user, _at: Date.now() }));
      } else {
        localStorage.removeItem("eh_user_cache");
      }
    } catch (e) {}
  }

  function inject() {
    // Ne PAS injecter sur les pages a carte centree (auth-body)
    var SKIP_PAGES = [
      "/connexion",
      "/inscription",
      "/static/login.html",
      "/static/register.html",
      "/static/payment.html",
      "/static/professional.html",
      "/static/notifications.html",
      "/static/driver.html",
      "/professionnel",
      "/pharmacien",
      "/compte"
    ];
    // Si la page a la navbar patient -> skip (patient_nav.js fait tout)
    if (document.querySelector("script[src*='patient_nav.js']") ||
        document.body.classList.contains("pn-has-navbar")) {
      return;
    }
    var path = window.location.pathname;
    for (var i = 0; i < SKIP_PAGES.length; i++) {
      if (path.indexOf(SKIP_PAGES[i]) === 0) return;
    }
    // Si la page a deja un .auth-body, on saute aussi
    if (document.body.classList.contains("auth-body")) return;

    var cachedUser = getCachedUser();
    var promiseUser;
    if (cachedUser) {
      promiseUser = Promise.resolve(cachedUser);
    } else {
      promiseUser = fetchJson("/auth/me").then(function (u) {
        setCachedUser(u);
        return u;
      });
    }

    var _pUser = promiseUser;
    var _pCart = _pUser.then(function (u) {
      if (!u) return null;
      if (u.role !== "PATIENT" && u.role !== "PROFESSIONNEL") return null;
      return fetchJson("/cart");
    });
    Promise.all([
      _pUser,
      _pCart,
      fetchJson("/notifications?unread_only=1")
    ]).then(function (r) {
      var user = r[0];
      var cartCount = (r[1] && r[1].item_count) || 0;
      var notifCount = Array.isArray(r[2]) ? r[2].length : 0;
      var actions = buildUserActions(user, cartCount, notifCount);

      var inner = document.querySelector(".topbar .topbar-inner")
        || document.querySelector(".topbar")
        || document.querySelector(".eh-mini-bar");

      if (inner) {
        var existing = inner.querySelector(".eh-user-actions");
        if (existing) existing.remove();
        inner.appendChild(actions);
      } else {
        var bar = el("div", "eh-mini-bar");
        var brand = el("a", "eh-brand-mini");
        brand.href = "/";
        brand.innerHTML = '<span class="eh-brand-mark">+</span> Elonikab Health';
        bar.appendChild(brand);
        bar.appendChild(actions);
        document.body.insertBefore(bar, document.body.firstChild);
      }
    });
  }

  window.EHHeader = {
    refresh: inject,
    updateCartBadge: function (count) {
      var nodes = document.querySelectorAll(".eh-cart-count");
      Array.prototype.forEach.call(nodes, function (b) {
        if (count > 0) {
          b.textContent = count > 99 ? "99+" : String(count);
          b.classList.remove("hidden");
        } else {
          b.classList.add("hidden");
        }
      });
    },
    updateNotifBadge: function (count) {
      var nodes = document.querySelectorAll(".eh-notif-count");
      Array.prototype.forEach.call(nodes, function (b) {
        if (count > 0) {
          b.textContent = count > 99 ? "99+" : String(count);
          b.classList.remove("hidden");
        } else {
          b.classList.add("hidden");
        }
      });
    }
  };


  // ===== Notifications temps reel (SSE) =====
  var _sse = null;
  function connectSSE() {
    if (_sse) return;
    if (typeof EventSource === "undefined") return;
    try {
      _sse = new EventSource("/api/notifications/stream", { withCredentials: true });
    } catch (e) { _sse = null; return; }

    _sse.addEventListener("message", function (ev) {
      try {
        var data = JSON.parse(ev.data);
        // Mise a jour badge : incrementer le compteur courant
        var badges = document.querySelectorAll(".eh-notif-count");
        Array.prototype.forEach.call(badges, function (b) {
          var cur = parseInt(b.textContent || "0", 10);
          if (isNaN(cur)) cur = 0;
          var nxt = cur + 1;
          b.textContent = nxt > 99 ? "99+" : String(nxt);
          b.classList.remove("hidden");
        });
        // Toast visuel
        showToast(data.title, data.body, data.order_id);
      } catch (e) {}
    });

    _sse.onerror = function () {
      if (_sse) { try { _sse.close(); } catch (e) {} _sse = null; }
      setTimeout(connectSSE, 5000); // reconnexion auto apres 5s
    };
  }

  function showToast(title, body, orderId) {
    var t = document.createElement("div");
    t.className = "eh-toast";
    t.innerHTML =
      '<div class="eh-toast-title">' + (title || "Notification") + '</div>' +
      '<div class="eh-toast-body">' + (body || "") + '</div>';
    if (orderId) {
      t.style.cursor = "pointer";
      t.addEventListener("click", function () {
        window.location.href = "/suivi?ref=" + encodeURIComponent(orderId);
      });
    }
    document.body.appendChild(t);
    // Auto-dismiss
    setTimeout(function () {
      t.classList.add("eh-toast-out");
      setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 400);
    }, 7000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      inject();
      setTimeout(connectSSE, 800);
    });
  } else {
    inject();
    setTimeout(connectSSE, 800);
  }
})();
