"""
fix_checkout_recap.py
Ajoute dans le checkout :
  - Recapitulatif des produits
  - Distance + frais de livraison en temps reel
  - Decompte subtotal / livraison / total
"""
from pathlib import Path
import datetime
import shutil
import re

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
CART_HTML = STATIC / "cart.html"
CART_JS = STATIC / "cart.js"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_checkout_recap_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(CART_HTML, backup / "cart.html")
shutil.copy2(CART_JS, backup / "cart.js")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. Remplacer le bloc checkout dans cart.html
# ============================================================
html = CART_HTML.read_text(encoding="utf-8")

# Chercher le bloc complet du checkout panel
start = html.find('<div id="checkout-panel"')
end = html.find('</div>', html.find('<div class="checkout-actions"'))
# On cherche jusqu'a la fermeture complete : dernier </div> apres checkout-actions
tail = html[start:]
# Trouver la fin : le </div> qui ferme checkout-panel
# Compter les <div> ouverts vs fermes
depth = 0
i = 0
end_pos = -1
while i < len(tail):
    if tail[i:i+4] == "<div":
        depth += 1
        i += 4
    elif tail[i:i+6] == "</div>":
        depth -= 1
        i += 6
        if depth == 0:
            end_pos = i
            break
    else:
        i += 1

if end_pos > 0:
    old_block = tail[:end_pos]
    new_block = '''<div id="checkout-panel" class="checkout-card hidden">
    <h2 style="margin:0 0 6px;font-size:17px">Finaliser la commande</h2>
    <p class="muted small" style="margin:0 0 10px">Verifiez les produits puis choisissez le mode.</p>

    <!-- Recapitulatif des produits -->
    <div id="co-items" class="co-items"></div>

    <!-- Mode -->
    <div class="checkout-modes">
      <button type="button" class="mode-btn active" data-mode="retrait">&#127968; Retrait</button>
      <button type="button" class="mode-btn" data-mode="livraison">&#128666; Livraison</button>
    </div>

    <!-- Coordonnees client -->
    <div class="checkout-field">
      <label for="co-name">Nom complet</label>
      <input type="text" id="co-name" placeholder="Votre nom">
    </div>
    <div class="checkout-field">
      <label for="co-phone">Telephone</label>
      <input type="tel" id="co-phone" placeholder="Ex : 90 00 00 00">
    </div>

    <!-- Champs livraison -->
    <div id="co-delivery-fields" class="hidden">
      <div class="checkout-field">
        <label for="co-address">Adresse (optionnelle si GPS)</label>
        <textarea id="co-address" rows="2" placeholder="Quartier, rue, repere..."></textarea>
      </div>
      <div class="checkout-field">
        <button type="button" class="auth-btn" id="co-gps" style="background:#6c8a80">&#128205; Utiliser ma position GPS</button>
        <div id="co-gps-status" class="muted small"></div>
      </div>
      <div id="co-delivery-info" class="co-delivery-info hidden"></div>
    </div>

    <!-- Totaux detailles -->
    <div id="co-totals" class="co-totals">
      <div class="co-line"><span>Sous-total</span><span id="co-subtotal">0 FCFA</span></div>
      <div class="co-line hidden" id="co-line-shipping"><span>Livraison</span><span id="co-shipping">0 FCFA</span></div>
      <div class="co-line co-total"><span>Total</span><span id="co-total">0 FCFA</span></div>
    </div>

    <div id="co-error" class="auth-msg hidden"></div>
    <div class="checkout-actions">
      <button type="button" class="auth-btn" id="co-cancel" style="background:#6c8a80">Annuler</button>
      <button type="button" class="auth-btn" id="co-confirm">Confirmer la commande</button>
    </div>
  </div>'''
    html = html.replace(old_block, new_block, 1)
    print("[OK] cart.html -> nouveau bloc checkout")
else:
    print("[!] bloc checkout-panel introuvable")

# Ajouter les styles specifiques au recap
STYLE_ADD = '''<style>
  .co-items{
    background:#fafdfb;border:1px solid #ddece6;border-radius:12px;
    padding:12px;margin-bottom:14px;
  }
  .co-item{
    display:flex;justify-content:space-between;align-items:flex-start;
    gap:10px;padding:6px 0;font-size:13px;
    border-bottom:1px dashed #e8f2ee;
  }
  .co-item:last-child{border-bottom:0}
  .co-item-name{flex:1;font-weight:600;color:#0f2620}
  .co-item-meta{font-size:11px;color:#6c8a80;font-weight:500;margin-top:2px}
  .co-item-price{font-weight:800;color:#0a7a5a;white-space:nowrap}
  .co-totals{
    background:#fff;border:1px solid #ddece6;border-radius:12px;
    padding:12px 14px;margin:12px 0;
  }
  .co-line{
    display:flex;justify-content:space-between;align-items:center;
    padding:6px 0;font-size:14px;color:#0f2620;
  }
  .co-line.co-total{
    border-top:1px solid #ddece6;margin-top:6px;padding-top:10px;
    font-size:16px;font-weight:800;color:#0a7a5a;
  }
  .co-line.co-total span:last-child{font-size:18px}
  .co-delivery-info{
    background:#e8f7f1;border:1px solid #c7e9dc;border-radius:12px;
    padding:12px 14px;margin-top:8px;font-size:13px;color:#0a7a5a;
    line-height:1.5;
  }
  .co-delivery-info strong{color:#0a7a5a}
  .co-delivery-info.warn{background:#fff4e0;border-color:#f2d9b3;color:#b26b00}
  .co-delivery-info.warn strong{color:#b26b00}
</style>
'''
if ".co-items" not in html:
    html = html.replace("</head>", STYLE_ADD + "</head>", 1)
    print("[OK] cart.html -> styles recap")

CART_HTML.write_text(html, encoding="utf-8")

# ============================================================
# 2. Reecriture complete de cart.js
# ============================================================
NEW_JS = r'''(function () {
  function $(id) { return document.getElementById(id); }
  function money(v) { return Math.round(Number(v) || 0).toLocaleString("fr-FR") + " FCFA"; }
  function showMsg(t) { var m = $("msg"); if (!m) return; m.textContent = t; m.className = "auth-msg"; }
  function hideMsg() { var m = $("msg"); if (m) m.className = "auth-msg hidden"; }
  function showCoErr(t) { var m = $("co-error"); if (!m) return; m.textContent = t; m.classList.remove("hidden"); }
  function hideCoErr() { var m = $("co-error"); if (m) m.classList.add("hidden"); }

  var state = {
    mode: "retrait",
    lat: null, lon: null, acc: null,
    subtotal: 0,
    items: [],
    settings: { delivery_base_fee: 300, delivery_price_per_km: 100,
                delivery_fee_default: 500,
                pharmacy_latitude: null, pharmacy_longitude: null }
  };

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

  function haversineKm(lat1, lon1, lat2, lon2) {
    var R = 6371.0;
    var dLat = (lat2 - lat1) * Math.PI / 180;
    var dLon = (lon2 - lon1) * Math.PI / 180;
    var a = Math.sin(dLat/2) * Math.sin(dLat/2)
          + Math.cos(lat1 * Math.PI/180) * Math.cos(lat2 * Math.PI/180)
          * Math.sin(dLon/2) * Math.sin(dLon/2);
    return 2 * R * Math.asin(Math.sqrt(a));
  }

  function computeDelivery() {
    var s = state.settings;
    var fallback = Number(s.delivery_fee_default) || 0;
    var phLat = s.pharmacy_latitude, phLon = s.pharmacy_longitude;
    if (phLat === null || phLat === undefined || phLon === null || phLon === undefined) {
      return { fee: fallback, distance: null, reason: "no_pharmacy" };
    }
    if (state.lat === null || state.lon === null) {
      return { fee: fallback, distance: null, reason: "no_gps" };
    }
    var dist = haversineKm(phLat, phLon, state.lat, state.lon);
    var base = Number(s.delivery_base_fee) || 300;
    var perKm = Number(s.delivery_price_per_km) || 100;
    var fee = Math.round((base + dist * perKm) / 50) * 50;
    return { fee: fee, distance: dist, reason: "ok" };
  }

  function renderCoItems() {
    var box = $("co-items");
    if (!box) return;
    box.innerHTML = "";
    if (state.items.length === 0) {
      box.appendChild(elText("div", "co-item-name", "Panier vide"));
      return;
    }
    state.items.forEach(function (it) {
      var row = document.createElement("div");
      row.className = "co-item";
      var left = document.createElement("div");
      left.style.flex = "1";
      var name = document.createElement("div");
      name.className = "co-item-name";
      name.textContent = it.product_name;
      var meta = document.createElement("div");
      meta.className = "co-item-meta";
      meta.textContent = it.quantity + " x " + money(it.price);
      left.appendChild(name);
      left.appendChild(meta);
      var right = document.createElement("div");
      right.className = "co-item-price";
      right.textContent = money(it.line_total);
      row.appendChild(left);
      row.appendChild(right);
      box.appendChild(row);
    });
  }

  function elText(tag, cls, txt) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (txt) n.textContent = txt;
    return n;
  }

  function updateTotals() {
    $("co-subtotal").textContent = money(state.subtotal);
    var lineShip = $("co-line-shipping");
    var shipVal = $("co-shipping");
    var totalVal = $("co-total");
    var info = $("co-delivery-info");

    if (state.mode === "retrait") {
      lineShip.classList.add("hidden");
      if (info) info.classList.add("hidden");
      totalVal.textContent = money(state.subtotal);
      return;
    }

    var res = computeDelivery();
    lineShip.classList.remove("hidden");
    shipVal.textContent = money(res.fee);
    totalVal.textContent = money(state.subtotal + res.fee);

    if (!info) return;
    info.classList.remove("hidden");
    if (res.reason === "no_pharmacy") {
      info.className = "co-delivery-info warn";
      info.innerHTML = "&#9888;&#65039; La pharmacie n'a pas encore configure sa position.<br>Frais de secours appliques : <strong>" +
        money(res.fee) + "</strong>";
    } else if (res.reason === "no_gps") {
      info.className = "co-delivery-info warn";
      info.innerHTML = "&#9888;&#65039; Sans GPS, les frais sont estimes a <strong>" +
        money(res.fee) + "</strong>.<br>Utilisez <strong>Utiliser ma position GPS</strong> pour un tarif precis.";
    } else {
      info.className = "co-delivery-info";
      info.innerHTML = "&#128666; Distance estimee : <strong>" +
        res.distance.toFixed(1) + " km</strong><br>" +
        "&#128181; Frais de livraison : <strong>" + money(res.fee) + "</strong>";
    }
  }

  function render(data) {
    var box = $("cart-body");
    box.innerHTML = "";
    state.subtotal = data.subtotal || 0;
    state.items = data.items || [];

    if (state.items.length === 0) {
      box.innerHTML = '<div class="empty-cart">Votre panier est vide.</div>';
      $("cart-total").classList.add("hidden");
      $("checkout").disabled = true;
      if ($("checkout-panel")) $("checkout-panel").classList.add("hidden");
      return;
    }
    $("checkout").disabled = false;

    state.items.forEach(function (it) {
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
        '<div class="cart-price">' + money(it.price) + ' \u00D7 ' + it.quantity +
        ' = ' + money(it.line_total) + '</div>';
      var qty = document.createElement("div");
      qty.className = "qty";
      var minus = document.createElement("button"); minus.textContent = "\u2212";
      var input = document.createElement("input"); input.type = "number";
      input.value = it.quantity; input.min = "1";
      var plus = document.createElement("button"); plus.textContent = "+";
      minus.onclick = function () { setQty(it.id, Math.max(1, it.quantity - 1)); };
      plus.onclick = function () { setQty(it.id, it.quantity + 1); };
      input.onchange = function () { setQty(it.id, Math.max(1, parseInt(input.value) || 1)); };
      var del = document.createElement("button");
      del.textContent = "\u2715";
      del.style.cssText = "background:none;border:0;color:#b23c3c;font-size:18px;cursor:pointer;padding:0 4px";
      del.onclick = function () { removeItem(it.id); };
      qty.appendChild(minus); qty.appendChild(input); qty.appendChild(plus);
      card.appendChild(thumb); card.appendChild(info); card.appendChild(qty); card.appendChild(del);
      box.appendChild(card);
    });
    $("subtotal").textContent = money(data.subtotal);
    $("cart-total").classList.remove("hidden");

    renderCoItems();
    updateTotals();
  }

  function load() {
    hideMsg();
    call("GET", "/api/cart").then(render).catch(function (e) {
      if (String(e.message).indexOf("Non authentifie") >= 0 || String(e.message).indexOf("authent") >= 0) {
        window.location.href = "/static/login.html?next=/static/cart.html";
      } else { showMsg(e.message); }
    });
  }

  function loadSettings() {
    fetch("/api/settings").then(function (r) { return r.ok ? r.json() : null; })
      .then(function (s) { if (s) { state.settings = s; updateTotals(); } })
      .catch(function () {});
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
    updateTotals();
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
    updateTotals();
  }

  function getGPS() {
    if (!navigator.geolocation) { $("co-gps-status").textContent = "GPS indisponible"; return; }
    var b = $("co-gps");
    b.disabled = true; b.textContent = "Localisation...";
    navigator.geolocation.getCurrentPosition(function (pos) {
      state.lat = pos.coords.latitude;
      state.lon = pos.coords.longitude;
      state.acc = pos.coords.accuracy;
      $("co-gps-status").innerHTML = "\u2713 Position : " +
        state.lat.toFixed(4) + ", " + state.lon.toFixed(4) +
        " (\u00B1 " + Math.round(state.acc) + " m)";
      b.disabled = false; b.textContent = "\uD83D\uDCCD Actualiser ma position";
      updateTotals();
    }, function () {
      b.disabled = false; b.textContent = "\uD83D\uDCCD Utiliser ma position GPS";
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
    if (state.mode === "livraison" && !address && (state.lat === null || state.lon === null)) {
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
    loadSettings();
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

CART_JS.write_text(NEW_JS, encoding="utf-8")
print("[OK] cart.js reecrit")

print()
print("=" * 60)
print("FIX CHECKOUT RECAP APPLIQUE")
print("=" * 60)
print()
print("Nouveautes :")
print("  - Recapitulatif des produits dans le checkout")
print("  - Distance estimee affichee en mode Livraison")
print("  - Frais de livraison calcules en temps reel")
print("  - Decompte : Sous-total / Livraison / Total")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur l'iPhone")