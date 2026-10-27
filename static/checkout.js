/* Elonikab Health - Page checkout (mode + adresse + creation commande) */
(function () {
  "use strict";

  var API = "/api";
  var state = {
    cart: null,
    settings: null,
    mode: "retrait",
    lat: null,
    lon: null,
    acc: null,
    user: null
  };

  function $(id) { return document.getElementById(id); }

  function money(v) {
    var n = Math.round(Number(v) || 0);
    try { return n.toLocaleString("fr-FR") + " FCFA"; }
    catch (e) {
      var s = String(n), out = "";
      for (var i = 0; i < s.length; i++) {
        if (i > 0 && (s.length - i) % 3 === 0) out += " ";
        out += s.charAt(i);
      }
      return out + " FCFA";
    }
  }

  function escapeHtml(s) {
    try {
      return String(s == null ? "" : s)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    } catch (e) { return ""; }
  }

  function haversineKm(lat1, lon1, lat2, lon2) {
    var R = 6371.0;
    var dLat = (lat2 - lat1) * Math.PI / 180;
    var dLon = (lon2 - lon1) * Math.PI / 180;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2)
          + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180)
          * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 2 * R * Math.asin(Math.sqrt(a));
  }

  function computeFee() {
    if (state.mode !== "livraison") return 0;
    var s = state.settings || {};
    var phLat = Number(s.pharmacy_latitude);
    var phLon = Number(s.pharmacy_longitude);
    var base = Number(s.delivery_base_fee);
    var perKm = Number(s.delivery_price_per_km);
    if (isNaN(phLat) || isNaN(phLon)) return null;
    if (state.lat === null || state.lon === null) return null;  // Pas de GPS = pas de tarif
    var dist = haversineKm(phLat, phLon, state.lat, state.lon);
    var b = isNaN(base) ? 300 : base;
    var p = isNaN(perKm) ? 100 : perKm;
    var fee = b + dist * p;
    fee = Math.round(fee / 50) * 50;
    return fee;
  }

  function computeDistance() {
    if (state.mode !== "livraison") return null;
    var s = state.settings || {};
    var phLat = Number(s.pharmacy_latitude);
    var phLon = Number(s.pharmacy_longitude);
    if (isNaN(phLat) || isNaN(phLon)) return null;
    if (state.lat === null || state.lon === null) return null;
    return haversineKm(phLat, phLon, state.lat, state.lon);
  }

  function render() {
    var cart = state.cart;
    if (!cart || !cart.items || cart.items.length === 0) {
      $("main").innerHTML =
        '<div class="pt-empty">' +
          '<div class="pt-empty-ico">&#128722;</div>' +
          '<h2>Votre panier est vide</h2>' +
          '<a class="pt-btn pt-btn-primary" href="/?nav=catalog" style="margin-top:14px">Voir le catalogue</a>' +
        '</div>';
      return;
    }

    var u = state.user || {};
    var subtotal = Number(cart.subtotal) || 0;
    var fee = computeFee();
    var total = subtotal + fee;

    var html = '<h1 class="pt-page-title">Finaliser ma commande</h1>';
    html += '<p class="pt-page-sub">' + cart.items.length +
            ' article' + (cart.items.length > 1 ? 's' : '') + '</p>';

    // ===== Mode de livraison =====
    html += '<div class="pt-card" style="margin-top:18px">';
    html += '<p class="pt-block-title">Mode de retrait</p>';
    html += '<div class="pt-mode-grid">';
    html += '<button type="button" class="pt-mode' + (state.mode === 'retrait' ? ' active' : '') +
            '" data-mode="retrait">' +
            '<span class="pt-mode-ico">&#127974;</span>' +
            '<strong>Retrait</strong>' +
            '<small>En pharmacie</small>' +
            '</button>';
    html += '<button type="button" class="pt-mode' + (state.mode === 'livraison' ? ' active' : '') +
            '" data-mode="livraison">' +
            '<span class="pt-mode-ico">&#128666;</span>' +
            '<strong>Livraison</strong>' +
            '<small>A domicile</small>' +
            '</button>';
    html += '</div>';

    // ===== Si livraison : adresse + GPS =====
    if (state.mode === 'livraison') {
      html += '<div class="pt-fee-info" id="eh-fee-info">Frais estimes : <strong>' + money(fee) + '</strong>';
      var d = computeDistance();
      if (d !== null) html += ' &middot; Distance : <strong>' + d.toFixed(1) + ' km</strong>';
      else html += '<br><small>Activez le GPS pour un tarif precis.</small>';
      html += '</div>';
      html += '<div id="eh-vehicle-info" class="eh-vehicle-badge">';
      html += '<span class="eh-vehicle-loading">Calcul du moyen de livraison...</span>';
      html += '</div>';

      html += '<div class="pt-form-row">';
      html += '<label>Localisation</label>';
      html += '<button type="button" class="pt-btn pt-btn-ghost pt-geo-btn" id="geo-btn">';
      html += '<span>&#128205;</span> ' +
              (state.lat !== null ? 'Actualiser ma position' : 'Utiliser ma localisation');
      html += '</button>';
      html += '<div id="geo-status" class="pt-geo-status hidden"></div>';
      html += '</div>';

      
          }
    html += '</div>';

    // ===== Infos client =====
    html += '<div class="pt-card">';
    html += '<p class="pt-block-title">Vos informations</p>';
    html += '<div class="pt-form-row">';
    html += '<label>Nom complet *</label>';
    html += '<input type="text" id="f-name" value="' +
            escapeHtml(u.full_name || '') + '" placeholder="Ex: Awa Diallo">';
    html += '</div>';
    html += '<div class="pt-form-row">';
    html += '<label>Telephone *</label>';
    html += '<input type="tel" id="f-phone" value="' +
            escapeHtml(u.phone || '') + '" placeholder="Ex: 90 00 00 00">';
    html += '</div>';
    html += '</div>';

    // ===== Recapitulatif des articles =====
    html += '<div class="pt-card">';
    html += '<p class="pt-block-title">Votre commande</p>';
    cart.items.forEach(function (it) {
      var lineTotal = (it.line_total !== undefined && it.line_total !== null)
        ? Number(it.line_total)
        : Number(it.price) * Number(it.quantity);
      html += '<div class="pt-ck-item">';
      html += '<div class="pt-ck-thumb">';
      if (it.image_url) {
        html += '<img loading="lazy" decoding="async" src="' + escapeHtml(it.image_url) + '" alt="' + escapeHtml(it.product_name) + '">';
      } else {
        html += '<span class="pt-ck-thumb-ph">' + escapeHtml((it.product_name || "?").charAt(0).toUpperCase()) + '</span>';
      }
      html += '</div>';
      html += '<div class="pt-ck-info">';
      html += '<div class="pt-ck-name">' + escapeHtml(it.product_name || "") + '</div>';
      html += '<div class="pt-ck-meta">x ' + it.quantity + ' &middot; ' + money(it.price) + '</div>';
      html += '</div>';
      html += '<div class="pt-ck-price">' + money(lineTotal) + '</div>';
      html += '</div>';
    });
    html += '</div>';

    // ===== Recapitulatif =====
    html += '<div class="pt-totals">';
    html += '<div class="pt-totals-row"><span class="lbl">Sous-total</span>' +
            '<span class="val">' + money(subtotal) + '</span></div>';
    html += '<div class="pt-totals-row"><span class="lbl">Livraison</span>' +
            '<span class="val">' +
            (state.mode === 'retrait' ? '0 FCFA' : money(fee)) +
            '</span></div>';
    html += '<div class="pt-totals-row pt-totals-total"><span>Total</span>' +
            '<span class="val">' + money(total) + '</span></div>';
    html += '</div>';

    // ===== Bouton valider =====
    html += '<div style="margin-top:18px">';
    html += '<button type="button" class="pt-btn pt-btn-primary pt-btn-block" id="btn-confirm" style="width:100%;padding:15px">';
    html += 'Valider et payer ' + money(total);
    html += '</button>';
    html += '</div>';

    $("main").innerHTML = html;
    bindEvents();
  }

  function bindEvents() {
    // Mode selection
    document.querySelectorAll("[data-mode]").forEach(function (b) {
      b.addEventListener("click", function () {
        state.mode = b.getAttribute("data-mode");
        state.lat = null;
        state.lon = null;
        state.acc = null;
        render();
      });
    });

    // GPS
    var geoBtn = $("geo-btn");
    if (geoBtn) {
      geoBtn.addEventListener("click", function () {
        if (!navigator.geolocation) {
          setGeoStatus("GPS non disponible", "err");
          return;
        }
        geoBtn.disabled = true;
        geoBtn.innerHTML = '<span>&#8987;</span> Localisation...';
        setGeoStatus("Recuperation de votre position...", "wait");
        navigator.geolocation.getCurrentPosition(
          function (pos) {
            state.lat = pos.coords.latitude;
            state.lon = pos.coords.longitude;
            state.acc = pos.coords.accuracy;
            setGeoStatus("&#10003; Position enregistree (" + Math.round(state.acc) + " m)", "ok");
            geoBtn.disabled = false;
            geoBtn.innerHTML = '<span>&#128205;</span> Actualiser ma position';
            // Update fee display
            setTimeout(function () {
              render();
              // Scroll automatique vers le bouton "Valider et payer"
              setTimeout(function () {
                var ck = document.getElementById("btn-confirm");
                if (ck) {
                  try {
                    ck.scrollIntoView({ behavior: "smooth", block: "center" });
                  } catch (e) {
                    var y = ck.getBoundingClientRect().top + window.pageYOffset - 120;
                    window.scrollTo({ top: y, behavior: "smooth" });
                  }
                }
              }, 350);
            }, 400);
          },
          function (err) {
            var msg = "Erreur de localisation";
            if (err.code === 1) msg = "Vous avez refuse la localisation.";
            else if (err.code === 2) msg = "Position introuvable.";
            else if (err.code === 3) msg = "Delai depasse.";
            setGeoStatus(msg, "err");
            geoBtn.disabled = false;
            geoBtn.innerHTML = '<span>&#128205;</span> Reessayer';
          },
          { enableHighAccuracy: true, timeout: 20000, maximumAge: 60000 }
        );
      });
    }    // Confirm
    var ck = $("btn-confirm");
    if (ck) ck.addEventListener("click", confirmOrder);
  }

  function setGeoStatus(msg, type) {
    var s = $("geo-status");
    if (!s) return;
    s.className = "pt-geo-status" + (type ? " pt-geo-" + type : "");
    s.innerHTML = msg;
    s.classList.remove("hidden");
  }

  function confirmOrder() {
    var name = ($("f-name") && $("f-name").value || "").trim();
    var phone = ($("f-phone") && $("f-phone").value || "").trim();
    var address = "";  // adresse retiree (GPS obligatoire)

    if (!name) { showToast("Nom obligatoire", "#B23C3C"); return; }
    if (!phone) { showToast("Telephone obligatoire", "#B23C3C"); return; }

    if (state.mode === "livraison") {
      // GPS OBLIGATOIRE pour la livraison (pas d'adresse manuelle)
      if (state.lat === null || state.lon === null) {
        showToast("Veuillez activer votre localisation GPS pour la livraison", "#B23C3C");
        return;
      }
    }

    var btn = $("btn-confirm");
    btn.disabled = true;
    btn.textContent = "Creation de la commande...";

    var payload = {
      delivery_mode: state.mode,
      customer_name: name,
      phone: phone,
      address: "",
      latitude: state.lat,
      longitude: state.lon,
      location_accuracy: state.acc,
      prescription_file: ""
    };

    fetch(API + "/orders/v2", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
    .then(function (r) {
      return r.json().then(function (d) {
        if (r.status === 401) {
          window.location.href = "/connexion?next=/checkout";
          throw new Error("_redirect");
        }
        if (!r.ok) throw new Error(d.detail || "Erreur de creation");
        return d;
      });
    })
    .then(function (order) {
      if (!order || !order.reference) throw new Error("Reference manquante");
      // Redirection vers paiement avec la VRAIE reference
      window.location.href = "/payment.html?ref=" + encodeURIComponent(order.reference);
    })
    .catch(function (e) {
      if (e && e.message === "_redirect") return;
      btn.disabled = false;
      btn.textContent = "Valider et payer";
      showToast(e.message || "Erreur", "#B23C3C");
    });
  }

  function showToast(msg, color) {
    var t = document.createElement("div");
    t.style.cssText = "position:fixed;bottom:100px;left:50%;transform:translateX(-50%);" +
      "background:" + (color || "#174A7E") + ";color:#fff;padding:12px 20px;border-radius:10px;" +
      "font-size:13.5px;font-weight:700;z-index:99999;box-shadow:0 8px 24px rgba(15,23,42,.2);" +
      "font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:90vw;text-align:center";
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () {
      t.style.opacity = "0"; t.style.transition = "opacity .3s";
      setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 300);
    }, 3000);
  }

  function init() {
    // 1. Auth
    fetch(API + "/auth/me", { credentials: "same-origin" })
      .then(function (r) {
        if (r.status === 401) {
          window.location.href = "/connexion?next=/checkout";
          return null;
        }
        return r.ok ? r.json() : null;
      })
      .then(function (u) {
        if (!u) return;
        state.user = u;
        // 2. Cart
        return fetch(API + "/cart", { credentials: "same-origin" })
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (c) {
            state.cart = c;
            // 3. Settings
            return fetch(API + "/settings", { credentials: "same-origin" })
              .then(function (r) { return r.ok ? r.json() : null; })
              .then(function (s) {
                state.settings = s || {};
                render();
              });
          });
      })
      .catch(function (e) {
        $("main").innerHTML = '<div class="pt-empty"><h2>Erreur</h2><p>' +
                              escapeHtml(e.message) + '</p></div>';
      });
  }

  document.addEventListener("DOMContentLoaded", init);


// ============================================================
// SPRINT A.5 : Affichage du vehicule de livraison
// ============================================================
async function ehRefreshVehicleInfo() {
  try {
    if (state.mode !== "livraison") return;
    var el = document.getElementById("eh-vehicle-info");
    if (!el) return;

    // Calculer les parametres depuis le panier
    var cart = state.cart || {};
    var items = cart.items || [];
    var units = items.reduce(function(s, it){ return s + (Number(it.quantity)||1); }, 0);
    var lines = items.length;
    var amount = items.reduce(function(s, it){
      return s + (Number(it.price)||Number(it.unit_price)||0) * (Number(it.quantity)||1);
    }, 0);

    var lat = (typeof state.lat === "number") ? state.lat : null;
    var lon = (typeof state.lng === "number") ? state.lng : null;
    if (lat === null || lon === null) {
      try {
        var g = (state.gps || state.location);
        if (g && g.lat != null) { lat = Number(g.lat); lon = Number(g.lng || g.lon); }
      } catch(e) {}
    }

    el.innerHTML = '<span class="eh-vehicle-loading">Calcul...</span>';

    var r = await fetch("/api/delivery/estimate", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      credentials: "same-origin",
      body: JSON.stringify({
        latitude: lat, longitude: lon,
        units: units, distinct_lines: lines, amount: amount
      })
    });
    if (!r.ok) throw new Error("HTTP " + r.status);
    var d = await r.json();

    if (d.available) {
      var isCar = d.vehicle_type === "CAR";
      var ico = isCar ? "🚗" : "🛵";
      var lbl = isCar ? "voiture" : "moto";
      var distTxt = (d.distance_km != null) ? " (" + d.distance_km + " km)" : "";
      var feeTxt = Math.round(d.fee).toLocaleString("fr-FR") + " FCFA";
      el.className = "eh-vehicle-badge " + (isCar ? "eh-vehicle-car" : "eh-vehicle-moto");
      el.innerHTML = ico + " Livraison par <strong>" + lbl + "</strong>" + distTxt
                   + " — <strong>" + feeTxt + "</strong>";
    } else {
      el.className = "eh-vehicle-badge eh-vehicle-error";
      el.innerHTML = "❌ Aucun moyen de livraison pour cette distance. Choisissez le retrait.";
    }
  } catch(e) {
    var el2 = document.getElementById("eh-vehicle-info");
    if (el2) el2.innerHTML = "";
  }
}
window.ehRefreshVehicleInfo = ehRefreshVehicleInfo;

})();
