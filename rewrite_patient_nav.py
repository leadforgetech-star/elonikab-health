# -*- coding: utf-8 -*-
# rewrite_patient_nav.py - Reecriture propre de patient_nav.js
import os, re, shutil, datetime

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
NAV = os.path.join(ROOT, "static", "patient_nav.js")
INDEX = os.path.join(ROOT, "static", "index.html")

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
bak = os.path.join(ROOT, f"_backup_rw_nav_{ts}")
os.makedirs(bak, exist_ok=True)
shutil.copy2(NAV, os.path.join(bak, "patient_nav.js.bak"))
print(f"[BACKUP] {bak}\n")

CLEAN_JS = '''/* Elonikab Health - Navbar basse patient (v2 propre) */
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
'''

open(NAV, "w", encoding="utf-8").write(CLEAN_JS)
print(f"[OK] patient_nav.js reecrit ({len(CLEAN_JS)} octets)")

# Verif syntaxe basique
ob, cb = CLEAN_JS.count("{"), CLEAN_JS.count("}")
op_, cp = CLEAN_JS.count("("), CLEAN_JS.count(")")
print(f"[SYNTAXE] accolades : {ob} / {cb}  {'OK' if ob == cb else '!!'}")
print(f"[SYNTAXE] parentheses : {op_} / {cp}  {'OK' if op_ == cp else '!!'}")

# Bump versions
if os.path.exists(INDEX):
    h = open(INDEX, "r", encoding="utf-8").read()
    h = re.sub(r'(patient_nav\.js\?v=)[\d.]+', r'\g<1>9', h)
    open(INDEX, "w", encoding="utf-8").write(h)
    print("[OK] index.html : patient_nav.js v=9")

# Verif finale
n = open(NAV, "r", encoding="utf-8").read()
checks = [
    ("plus de '} else {' orphelin", "} else {\n        b.classList.add(\"hidden\");\n      }\n    })" not in n),
    ("refreshBellBadge unique", n.count("function refreshBellBadge") == 1),
    ("refreshCartBadge unique", n.count("function refreshCartBadge") == 1),
    ("injectFloatBell supprime", "injectFloatBell" not in n),
    ("refreshNotifBadge supprime", "refreshNotifBadge" not in n),
]
print("\n[VERIF]")
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

print(f"\n[BACKUP] {bak}")
print("\n[CMD] Pas de restart Uvicorn (static only).")
print("Edge > F12 > Network > Disable cache > Ctrl+Shift+R")
print("\n[TEST]")
print("  1) /notifications.html : plus de chiffres dans les ronds")
print("  2) Cloche en haut : badge rouge avec bon nombre")
print("  3) Navbar basse : badge panier correct")