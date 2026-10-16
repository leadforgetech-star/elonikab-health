/* Elonikab Health - Navbar basse patient (v2 propre) */
(function () {
  "use strict";

  var API = "/api";

  // Pages ou la navbar NE doit PAS apparaitre
  var SKIP = [
    "/static/login.html",
    "/connexion",
    "/inscription",
    "/static/register.html",
    "/static/payment.html",
    "/static/professional.html",
    "/professionnel",
    "/pharmacien",
    "/static/driver.html"
  ];

  function shouldSkip() {
    var p = window.location.pathname;
    for (var i = 0; i < SKIP.length; i++) {
      if (p.indexOf(SKIP[i]) === 0) return true;
    }
    return false;
  }

  function activeTab() {
    var p = window.location.pathname;
    var s = window.location.search;
    if (p === "/" && s.indexOf("nav=catalog") < 0) return "home";
    if (p === "/" && s.indexOf("nav=catalog") >= 0) return "catalog";
    if (p.indexOf("/static/cart") === 0) return "cart";
    if (p.indexOf("/suivi") === 0) return "suivi";
    if (p.indexOf("/compte") === 0) return "compte";
    return "home";
  }

  function makeLink(href, ico, lbl, key, active) {
    var a = document.createElement("a");
    a.href = href;
    a.setAttribute("data-pn", key);
    if (active === key) a.className = "active";
    var ic = document.createElement("span");
    ic.className = "pn-ico";
    ic.innerHTML = ico;
    var lb = document.createElement("span");
    lb.className = "pn-lbl";
    lb.textContent = lbl;
    a.appendChild(ic);
    a.appendChild(lb);
    if (key === "cart") {
      var b = document.createElement("span");
      b.className = "pn-badge hidden";
      b.id = "pn-cart-badge";
      a.appendChild(b);
    }
    return a;
  }

  function refreshCartBadge() {
    fetch(API + "/cart", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        var b = document.getElementById("pn-cart-badge");
        if (!b) return;
        var n = (d && d.item_count) || 0;
        if (n > 0) {
          b.textContent = n > 99 ? "99+" : String(n);
          b.classList.remove("hidden");
        } else {
          b.textContent = "";
          b.classList.add("hidden");
        }
      })
      .catch(function () {});
  }

  function refreshBellBadge() {
    fetch(API + "/notifications?unread_only=1", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (list) {
        var b = document.getElementById("pt-bell-badge");
        if (!b) return;
        var n = Array.isArray(list) ? list.length : 0;
        if (n > 0) {
          b.textContent = n > 99 ? "99+" : String(n);
          b.classList.remove("hidden");
        } else {
          b.textContent = "";
          b.classList.add("hidden");
        }
      })
      .catch(function () {});
  }

  function inject() {
    if (shouldSkip()) return;
    if (document.querySelector(".pn-navbar")) return;
    if (document.querySelector(".pro-navbar")) return;

    var active = activeTab();
    var nav = document.createElement("nav");
    nav.className = "pn-navbar";
    nav.setAttribute("aria-label", "Navigation principale");

    nav.appendChild(makeLink("/", "&#127968;", "Accueil", "home", active));
    nav.appendChild(makeLink("/?nav=catalog", "&#128269;", "Catalogue", "catalog", active));
    nav.appendChild(makeLink("/static/cart.html", "&#128722;", "Panier", "cart", active));
    nav.appendChild(makeLink("/suivi", "&#128230;", "Suivi", "suivi", active));
    nav.appendChild(makeLink("/compte", "&#128100;", "Compte", "compte", active));

    document.body.appendChild(nav);
    document.body.classList.add("pn-has-navbar");

    refreshCartBadge();
    refreshBellBadge();

    document.addEventListener("eh:refresh", refreshCartBadge);
    window.addEventListener("focus", refreshCartBadge);
  }

  // Listeners globaux pour la cloche
  document.addEventListener("eh:refresh", refreshBellBadge);
  window.addEventListener("focus", refreshBellBadge);
  document.addEventListener("DOMContentLoaded", function () {
    setTimeout(refreshBellBadge, 500);
  });



/* Prefetch des pages au survol de la navbar */
function prefetchHref(href) {
  if (!href || href === "#" || href.indexOf("http") === 0) return;
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
  if (a) prefetchHref(a.getAttribute("href"));
}, { passive: true });
document.addEventListener("touchstart", function (ev) {
  var a = ev.target && ev.target.closest ? ev.target.closest(".pn-navbar a") : null;
  if (a) prefetchHref(a.getAttribute("href"));
}, { passive: true });

  // API publique
  window.PatientNav = {
    updateCartBadge: function (count) {
      var b = document.getElementById("pn-cart-badge");
      if (!b) return;
      var n = Number(count) || 0;
      if (n > 0) {
        b.textContent = n > 99 ? "99+" : String(n);
        b.classList.remove("hidden");
      } else {
        b.classList.add("hidden");
      }
    },
    refreshCartBadge: refreshCartBadge,
    refreshBellBadge: refreshBellBadge
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", inject);
  } else {
    inject();
  }
})();
