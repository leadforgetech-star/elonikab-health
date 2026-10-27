"""
v3_install_ui_mobile.py
- Ameliore l'affichage mobile (toutes les pages)
- Redirige le premier visiteur vers register.html
- Remplace les prompt() par un vrai formulaire de checkout
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_v3_mobile_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. CSS mobile global
# ============================================================
MOBILE_CSS = '''
/* ============================================================
   Elokinab Health - Mobile
   ============================================================ */
@media (max-width: 720px){
  body{font-size:15px}
  .topbar-inner{flex-wrap:wrap;height:auto;padding:10px 0;gap:8px}
  .topnav{gap:4px;flex-wrap:wrap}
  .topnav a{padding:8px 10px;font-size:13px}
  .eh-user-actions{gap:6px}
  .eh-icon-btn{width:34px;height:34px;font-size:15px}
  .eh-user-trigger{max-width:110px;font-size:12px;padding:7px 10px}
  .container{padding:0 14px}
  .hero{padding:20px}
  .hero h1{font-size:24px}
  .hero p{font-size:15px}
  .searchbar{flex-direction:column;gap:6px}
  .searchbar button{width:100%;padding:12px}
  .card{padding:18px}
  .product-grid{grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px}
  .product-card{font-size:13px}
  .product-name{font-size:14px}
  .price{font-size:15px}
  .btn{padding:10px 14px;font-size:13px}
  .btn-lg{padding:12px 18px;font-size:14px}
  .product-detail{grid-template-columns:1fr;gap:16px;padding:16px}
  .detail-media{min-height:220px}
  .summary{grid-template-columns:1fr}
  .summary dt{font-size:12px;margin-top:8px}
  .auth-card{padding:22px;border-radius:16px}
  .auth-card h1{font-size:19px}
  .modal-content{max-width:100%;border-radius:14px}
  .modal-head{padding:14px 16px}
  .modal-head h2{font-size:15px}
  .modal-body,.assign-body{padding:12px 14px}
  .orders-grid{grid-template-columns:1fr}
  .stats{grid-template-columns:repeat(2,1fr);gap:10px}
  .stat-value{font-size:24px}
  .cart-item{padding:10px;gap:8px}
  .cart-thumb{width:46px;height:46px}
  .cart-name{font-size:13px}
  .qty input{width:38px}
}
@media (max-width: 400px){
  .hero h1{font-size:20px}
  .product-grid{grid-template-columns:1fr}
  .stats{grid-template-columns:1fr 1fr}
  .stat-value{font-size:20px}
  .stat-label{font-size:10px}
  .btn,.auth-btn{font-size:12px;padding:9px 12px}
}
/* Checkout : style du formulaire */
.checkout-card{
  background:#fff;border:1px solid #ddece6;border-radius:14px;
  padding:18px;margin-top:14px;
}
.checkout-modes{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:10px 0}
.mode-btn{
  padding:14px;border:2px solid #ddece6;border-radius:12px;background:#fff;
  font-family:inherit;font-size:14px;font-weight:700;cursor:pointer;
  color:#0f2620;text-align:center;transition:.15s;
}
.mode-btn:hover{border-color:#0f9d76}
.mode-btn.active{border-color:#0f9d76;background:#e8f7f1;color:#0a7a5a}
.checkout-field{display:flex;flex-direction:column;gap:6px;margin:10px 0}
.checkout-field label{font-size:13px;font-weight:700}
.checkout-field input,.checkout-field textarea{
  padding:12px 14px;border:1px solid #ddece6;border-radius:11px;
  font-family:inherit;font-size:15px;outline:none;
}
.checkout-field input:focus,.checkout-field textarea:focus{border-color:#0f9d76}
.checkout-total{
  background:#e8f7f1;border:1px solid #c7e9dc;border-radius:12px;
  padding:14px;margin-top:12px;font-weight:700;color:#0a7a5a;
  display:flex;justify-content:space-between;font-size:15px;
}
.checkout-actions{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap}
.checkout-actions .auth-btn{flex:1;min-width:140px}
'''
(STATIC / "mobile.css").write_text(MOBILE_CSS, encoding="utf-8")
print("[OK] static/mobile.css")

# ============================================================
# 2. Auto-redirect pour premier visiteur
# ============================================================
FIRST_VISIT_JS = '''/* Elokinab Health - Auto-redirect premier visiteur */
(function () {
  var KEY = "eh_visited";
  var SKIP_PAGES = ["/static/register.html", "/static/login.html",
                    "/static/payment.html", "/static/driver.html",
                    "/pharmacien", "/suivi"];
  var path = window.location.pathname;
  for (var i = 0; i < SKIP_PAGES.length; i++) {
    if (path.indexOf(SKIP_PAGES[i]) === 0) return;
  }

  var seen = null;
  try { seen = localStorage.getItem(KEY); } catch (e) {}

  if (seen) return;

  // Verifier si un compte est deja connecte
  fetch("/api/auth/me", { credentials: "same-origin" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (user) {
      try { localStorage.setItem(KEY, "1"); } catch (e) {}
      if (!user && path === "/") {
        window.location.href = "/static/register.html";
      }
    })
    .catch(function () {
      try { localStorage.setItem(KEY, "1"); } catch (e) {}
    });
})();
'''
(STATIC / "first_visit.js").write_text(FIRST_VISIT_JS, encoding="utf-8")
print("[OK] static/first_visit.js")

# ============================================================
# 3. Injecter mobile.css + first_visit.js dans toutes les pages
# ============================================================
PAGES = ["index.html", "cart.html", "payment.html", "professional.html",
         "driver.html", "suivi.html", "pharmacien.html",
         "login.html", "register.html", "notifications.html"]

LINK = '<link rel="stylesheet" href="/static/mobile.css">'
SCRIPT_FV = '<script src="/static/first_visit.js"></script>'

injected = 0
for page in PAGES:
    p = STATIC / page
    if not p.exists():
        continue
    c = p.read_text(encoding="utf-8")
    changed = False

    if LINK not in c and "</head>" in c:
        c = c.replace("</head>", LINK + "\n</head>", 1)
        changed = True

    # Injecter first_visit.js seulement sur l'accueil pour eviter les boucles
    if page == "index.html" and SCRIPT_FV not in c and "</body>" in c:
        c = c.replace("</body>", SCRIPT_FV + "\n</body>", 1)
        changed = True

    if changed:
        p.write_text(c, encoding="utf-8")
        injected += 1
        print("[OK] " + page)
print("[OK] " + str(injected) + " pages mises a jour")

# ============================================================
# 4. Nouveau checkout (formulaire propre, sans prompt)
# ============================================================
CART_HTML = STATIC / "cart.html"
html = CART_HTML.read_text(encoding="utf-8")

# Retirer l'ancien bouton Commander direct et remplacer par un bloc formulaire
old_actions = '''  <div class="cart-actions">
    <a class="btn-ghost" href="/">← Continuer mes achats</a>
    <button class="auth-btn" id="checkout" style="flex:1;min-width:160px">Commander</button>
  </div>'''
new_actions = '''  <div class="cart-actions">
    <a class="btn-ghost" href="/">← Continuer mes achats</a>
    <button class="auth-btn" id="checkout" style="flex:1;min-width:160px">Commander</button>
  </div>

  <div id="checkout-panel" class="checkout-card hidden">
    <h2 style="margin:0 0 6px;font-size:17px">Finaliser la commande</h2>
    <p class="muted small" style="margin:0 0 10px">Choisissez comment recuperer votre commande.</p>

    <div class="checkout-modes">
      <button type="button" class="mode-btn active" data-mode="retrait">🏠 Retrait</button>
      <button type="button" class="mode-btn" data-mode="livraison">🚚 Livraison</button>
    </div>

    <div class="checkout-field">
      <label for="co-name">Nom complet</label>
      <input type="text" id="co-name" placeholder="Votre nom">
    </div>
    <div class="checkout-field">
      <label for="co-phone">Telephone</label>
      <input type="tel" id="co-phone" placeholder="Ex : 90 00 00 00">
    </div>

    <div id="co-delivery-fields" class="hidden">
      <div class="checkout-field">
        <label for="co-address">Adresse (optionnelle si GPS)</label>
        <textarea id="co-address" rows="2" placeholder="Quartier, rue, repere..."></textarea>
      </div>
      <div class="checkout-field">
        <button type="button" class="auth-btn" id="co-gps" style="background:#6c8a80">📍 Utiliser ma position GPS</button>
        <div id="co-gps-status" class="muted small"></div>
      </div>
    </div>

    <div class="checkout-total">
      <span>Total</span><span id="co-total">0 FCFA</span>
    </div>
    <div id="co-error" class="auth-msg hidden"></div>
    <div class="checkout-actions">
      <button type="button" class="auth-btn" id="co-cancel" style="background:#6c8a80">Annuler</button>
      <button type="button" class="auth-btn" id="co-confirm">Confirmer la commande</button>
    </div>
  </div>'''

if old_actions in html and "checkout-panel" not in html:
    html = html.replace(old_actions, new_actions, 1)
    CART_HTML.write_text(html, encoding="utf-8")
    print("[OK] cart.html -> formulaire de commande")
elif "checkout-panel" in html:
    print("[i] cart.html deja patche")
else:
    print("[!] anchor cart-actions introuvable")

# ============================================================
# 5. Rewrite cart.js avec le nouveau checkout
# ============================================================
CART_JS = STATIC / "cart.js"
js = CART_JS.read_text(encoding="utf-8")

# Retirer l'ancienne fonction checkout/sendOrder basee sur prompt
if "function checkout()" in js:
    # Remplacement complet : plus simple de tout reecrire
    new_js = '''(function () {
  function $(id) { return document.getElementById(id); }
  function money(v) { return Math.round(Number(v) || 0).toLocaleString("fr-FR") + " FCFA"; }
  function showMsg(t) { var m = $("msg"); if (!m) return; m.textContent = t; m.className = "auth-msg"; }
  function hideMsg() { var m = $("msg"); if (m) m.className = "auth-msg hidden"; }
  function showCoErr(t) { var m = $("co-error"); if (!m) return; m.textContent = t; m.classList.remove("hidden"); }
  function hideCoErr() { var m = $("co-error"); if (m) m.classList.add("hidden"); }

  var state = { mode: "retrait", lat: null, lon: null, acc: null, subtotal: 0 };

  function call(m, p, b) {
    return fetch(p, {
      method: m,
      credentials: "same-origin",
      headers: b ? { "Content-Type": "application/json" } : {},
      body: b ? JSON.stringify(b) : undefined
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    });
  }

  function render(data) {
    var box = $("cart-body");
    box.innerHTML = "";
    state.subtotal = data.subtotal || 0;
    if (!data.items || data.items.length === 0) {
      box.innerHTML = '<div class="empty-cart">Votre panier est vide.</div>';
      $("cart-total").classList.add("hidden");
      $("checkout").disabled = true;
      if ($("checkout-panel")) $("checkout-panel").classList.add("hidden");
      return;
    }
    $("checkout").disabled = false;
    data.items.forEach(function (it) {
      var card = document.createElement("div");
      card.className = "cart-item";
      var thumb = document.createElement("div");
      thumb.className = "cart-thumb";
      if (it.image_url) {
        var img = document.createElement("img");
        img.src = it.image_url; img.alt = it.product_name;
        img.onerror = function () { img.remove(); thumb.textContent = it.product_name.charAt(0); };
        thumb.appendChild(img);
      } else { thumb.textContent = it.product_name.charAt(0); }
      var info = document.createElement("div");
      info.className = "cart-info";
      info.innerHTML = '<div class="cart-name">' + it.product_name + '</div>' +
        '<div class="cart-meta">' + (it.presentation || "") + '</div>' +
        '<div class="cart-price">' + money(it.price) + ' × ' + it.quantity +
        ' = ' + money(it.line_total) + '</div>';
      var qty = document.createElement("div");
      qty.className = "qty";
      var minus = document.createElement("button"); minus.textContent = "−";
      var input = document.createElement("input"); input.type = "number";
      input.value = it.quantity; input.min = "1";
      var plus = document.createElement("button"); plus.textContent = "+";
      minus.onclick = function () { setQty(it.id, Math.max(1, it.quantity - 1)); };
      plus.onclick = function () { setQty(it.id, it.quantity + 1); };
      input.onchange = function () { setQty(it.id, Math.max(1, parseInt(input.value) || 1)); };
      var del = document.createElement("button");
      del.textContent = "✕";
      del.style.cssText = "background:none;border:0;color:#b23c3c;font-size:18px;cursor:pointer;padding:0 4px";
      del.onclick = function () { removeItem(it.id); };
      qty.appendChild(minus); qty.appendChild(input); qty.appendChild(plus);
      card.appendChild(thumb); card.appendChild(info); card.appendChild(qty); card.appendChild(del);
      box.appendChild(card);
    });
    $("subtotal").textContent = money(data.subtotal);
    $("cart-total").classList.remove("hidden");
    if ($("co-total")) $("co-total").textContent = money(data.subtotal);
  }

  function load() {
    hideMsg();
    call("GET", "/api/cart").then(render).catch(function (e) {
      if (String(e.message).indexOf("Non authentifie") >= 0 || String(e.message).indexOf("authent") >= 0) {
        window.location.href = "/static/login.html?next=/static/cart.html";
      } else { showMsg(e.message); }
    });
  }

  function setQty(id, q) {
    call("PATCH", "/api/cart/items/" + id, { quantity: q }).then(render).catch(function (e) { showMsg(e.message); });
  }
  function removeItem(id) {
    call("DELETE", "/api/cart/items/" + id).then(render).catch(function (e) { showMsg(e.message); });
  }

  function openCheckout() {
    if (state.subtotal === 0) { showMsg("Panier vide"); return; }
    $("checkout-panel").classList.remove("hidden");
    $("checkout-panel").scrollIntoView({ behavior: "smooth" });
    // Pre-remplir le nom/tel depuis /api/auth/me
    fetch("/api/auth/me", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (u) {
        if (u) {
          if ($("co-name") && !$("co-name").value) $("co-name").value = u.full_name || "";
          if ($("co-phone") && !$("co-phone").value) $("co-phone").value = u.phone || "";
        }
      });
  }

  function selectMode(mode) {
    state.mode = mode;
    var modes = document.querySelectorAll(".mode-btn");
    Array.prototype.forEach.call(modes, function (b) {
      b.classList.toggle("active", b.getAttribute("data-mode") === mode);
    });
    var fields = $("co-delivery-fields");
    if (mode === "livraison") fields.classList.remove("hidden");
    else fields.classList.add("hidden");
  }

  function getGPS() {
    if (!navigator.geolocation) { $("co-gps-status").textContent = "GPS indisponible"; return; }
    var b = $("co-gps");
    b.disabled = true; b.textContent = "Localisation...";
    navigator.geolocation.getCurrentPosition(function (pos) {
      state.lat = pos.coords.latitude;
      state.lon = pos.coords.longitude;
      state.acc = pos.coords.accuracy;
      $("co-gps-status").innerHTML = "✓ Position : " +
        state.lat.toFixed(4) + ", " + state.lon.toFixed(4) +
        " (± " + Math.round(state.acc) + " m)";
      b.disabled = false; b.textContent = "📍 Actualiser ma position";
    }, function () {
      b.disabled = false; b.textContent = "📍 Utiliser ma position GPS";
      $("co-gps-status").textContent = "Position introuvable. Vous pouvez saisir l'adresse.";
    }, { enableHighAccuracy: true, timeout: 15000 });
  }

  function confirmOrder() {
    hideCoErr();
    var name = ($("co-name").value || "").trim();
    var phone = ($("co-phone").value || "").trim();
    var address = ($("co-address") ? $("co-address").value : "").trim();
    if (!name) { showCoErr("Nom obligatoire"); return; }
    if (!phone) { showCoErr("Telephone obligatoire"); return; }
    if (state.mode === "livraison" && !address && !state.lat) {
      showCoErr("Adresse OU GPS obligatoire pour la livraison");
      return;
    }
    var payload = {
      delivery_mode: state.mode,
      customer_name: name,
      phone: phone,
      address: address
    };
    if (state.lat !== null && state.lon !== null) {
      payload.latitude = state.lat;
      payload.longitude = state.lon;
      payload.location_accuracy = state.acc;
    }
    var btn = $("co-confirm");
    btn.disabled = true; btn.textContent = "Envoi...";
    call("POST", "/api/orders/v2", payload).then(function (o) {
      window.location.href = "/static/payment.html?ref=" + encodeURIComponent(o.reference);
    }).catch(function (e) {
      showCoErr(e.message);
      btn.disabled = false; btn.textContent = "Confirmer la commande";
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    load();
    $("checkout").addEventListener("click", openCheckout);
    if ($("co-cancel")) $("co-cancel").addEventListener("click", function () {
      $("checkout-panel").classList.add("hidden");
    });
    var modes = document.querySelectorAll(".mode-btn");
    Array.prototype.forEach.call(modes, function (b) {
      b.addEventListener("click", function () { selectMode(b.getAttribute("data-mode")); });
    });
    if ($("co-gps")) $("co-gps").addEventListener("click", getGPS);
    if ($("co-confirm")) $("co-confirm").addEventListener("click", confirmOrder);
  });
})();
'''
    CART_JS.write_text(new_js, encoding="utf-8")
    print("[OK] cart.js -> checkout propre sans prompt()")
else:
    print("[i] cart.js pas de prompt a remplacer (deja propre)")

# ============================================================
# RESUME
# ============================================================
print()
print("=" * 60)
print("UI MOBILE + AUTO-INSCRIPTION + CHECKOUT PROPRE")
print("=" * 60)
print()
print("Fichiers crees :")
print("  static/mobile.css        (responsive toutes pages)")
print("  static/first_visit.js    (redirection 1er visiteur)")
print()
print("Fichiers modifies :")
print("  static/cart.html         (formulaire de commande)")
print("  static/cart.js           (checkout sans prompt)")
print("  Toutes les pages HTML    (mobile.css inclus)")
print()
print("Comportement :")
print("  1. Premier visiteur sur / -> redirige vers /static/register.html")
print("  2. Apres inscription, l'utilisateur reste connecte (cookie)")
print("  3. Page panier : formulaire avec boutons Retrait/Livraison,")
print("     adresse, GPS - plus de prompt() ni de saisie clavier brute")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R dans le navigateur (pas besoin de redemarrer le serveur)")