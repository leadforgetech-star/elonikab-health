"""
v6_auto_location.py
Si le pro a une position GPS / adresse enregistree dans son profil,
la page Confirmer l'utilise automatiquement sans demander.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
CONF_JS = STATIC / "professional_demande_confirmer.js"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_auto_loc_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(CONF_JS, backup / "professional_demande_confirmer.js")
print("[OK] Backup ->", backup.name)

# Nouvelle version complete du fichier
NEW_JS = r'''/* Elokinab Health - Confirmation demande (v6 - auto localisation) */
(function () {
  var API = "/api";
  var $ = function (id) { return document.getElementById(id); };

  var state = {
    draft: null,
    summary: null,
    org: null,           // <-- profil etablissement (avec GPS/adresse)
    mode: "retrait",
    lat: null,
    lon: null,
    acc: null,
    address: "",
    estimate: null,
    estimateLoading: false,
    autoLocation: false, // <-- true si GPS venu du profil
    submitted: false
  };

  function escapeHtml(s) {
    try {
      return String(s == null ? "" : s)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    } catch (e) { return ""; }
  }

  function money(v) {
    var n = Math.round(Number(v) || 0);
    try { return n.toLocaleString("fr-FR") + " F"; }
    catch (e) {
      var s = String(n), out = "";
      for (var i = 0; i < s.length; i++) {
        if (i > 0 && (s.length - i) % 3 === 0) out += " ";
        out += s.charAt(i);
      }
      return out + " F";
    }
  }

  function qtyLabel(q) {
    var n = Number(q) || 0;
    return (n === Math.floor(n)) ? String(n) : n.toFixed(2);
  }

  function api(method, path, body) {
    var opts = {
      method: method, credentials: "same-origin",
      headers: { "Accept": "application/json" }
    };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(API + path, opts).then(function (r) {
      if (r.status === 401) {
        window.location.href = "/connexion?next=/professionnel/demande";
        throw new Error("Non authentifie");
      }
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    });
  }

  function toast(msg) {
    var t = document.createElement("div");
    t.className = "pg-toast";
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 2400);
  }

  // ============================================================
  // Chargement
  // ============================================================
  function load() {
    // 1. Charger le profil etablissement (avec adresse/GPS enregistres)
    return api("GET", "/pro/organizations/me").then(function (org) {
      state.org = org;
      // Pre-charger le GPS / adresse si presents
      if (org && org.latitude && org.longitude) {
        state.lat = org.latitude;
        state.lon = org.longitude;
        state.autoLocation = true;
      }
      if (org && org.delivery_address) {
        state.address = org.delivery_address;
      } else if (org && org.address) {
        state.address = org.address;
      }
      return api("GET", "/pro/requests/draft");
    }).then(function (d) {
      state.draft = d;
      return api("GET", "/pro/requests/" + encodeURIComponent(d.reference) + "/summary");
    }).then(function (sum) {
      state.summary = sum;
      if (sum.items_count === 0 && sum.attachments_count === 0) {
        window.location.href = "/professionnel/demande";
        return;
      }
      render();
    }).catch(function (e) {
      $("main").innerHTML = '<div style="text-align:center;padding:40px;color:#dc2626">Erreur : ' +
        escapeHtml(e.message) + '</div>';
    });
  }

  // ============================================================
  // Rendu
  // ============================================================
  function render() {
    if (state.submitted) { renderSuccess(); return; }

    $("page-ref").textContent = state.summary.reference;

    var subtotal = state.summary.subtotal;
    var fee = state.estimate && state.estimate.delivery_fee ? state.estimate.delivery_fee : 0;
    var total = state.mode === "livraison" && state.estimate
      ? (state.estimate.total || subtotal + fee)
      : subtotal;

    // Ligne de livraison
    var deliveryLine = '';
    if (state.mode === "livraison") {
      if (state.estimate && state.estimate.source === "gps") {
        var r = state.estimate.rates || {};
        var formula = (r.base_fee || 1000) + ' F + ' +
                      state.estimate.distance_km + ' km x ' +
                      (r.price_per_km || 250) + ' F/km';
        deliveryLine =
          '<div class="totals-line">' +
            '<span class="lbl">Distance</span>' +
            '<span class="val">' + state.estimate.distance_km + ' km</span>' +
          '</div>' +
          '<div class="totals-line">' +
            '<span class="lbl">Tarif ' + (r.vehicle || 'VOITURE') + '</span>' +
            '<span class="val" style="font-size:12px;font-weight:600;color:#64748b">' + formula + '</span>' +
          '</div>' +
          '<div class="totals-line">' +
            '<span class="lbl">Frais livraison</span>' +
            '<span class="val">' + money(state.estimate.delivery_fee) + '</span>' +
          '</div>';
      } else if (state.estimate && state.estimate.source === "no_gps") {
        deliveryLine =
          '<div class="totals-line">' +
            '<span class="lbl">Frais livraison</span>' +
            '<span class="val confirm">Activez le GPS ou utilisez l\'adresse</span>' +
          '</div>';
      } else if (state.estimate && state.estimate.source === "no_pharmacy") {
        deliveryLine =
          '<div class="totals-line">' +
            '<span class="lbl">Frais livraison</span>' +
            '<span class="val confirm">A confirmer</span>' +
          '</div>';
      } else {
        deliveryLine =
          '<div class="totals-line">' +
            '<span class="lbl">Frais livraison</span>' +
            '<span class="val confirm">En attente</span>' +
          '</div>';
      }
    } else {
      deliveryLine =
        '<div class="totals-line">' +
          '<span class="lbl">Frais livraison</span>' +
          '<span class="val">Retrait en pharmacie - 0 F</span>' +
        '</div>';
    }

    var deliveryFields = state.mode === "livraison" ? '' : ' class="hidden"';

    // Info localisation
    var locInfo = "";
    if (state.mode === "livraison" && state.autoLocation && state.lat) {
      locInfo = '<div class="pg-info" style="background:#e6f7f1;border-color:#c7e9dc;color:#0a7a5a;margin-bottom:12px">' +
                '&#10003; <strong>Utilisation de l\'adresse enregistree dans votre profil.</strong> ' +
                'Vous pouvez la modifier ci-dessous si besoin.' +
                '</div>';
    }

    var html = '' +
      '<h2 class="pg-section-title">Recapitulatif</h2>' +
      itemsRender() +
      '<div class="totals-card">' +
        '<div class="totals-line">' +
          '<span class="lbl">Sous-total</span>' +
          '<span class="val">' + money(subtotal) + '</span>' +
        '</div>' +
        deliveryLine +
        '<div class="totals-line total">' +
          '<span>Total' + (state.mode === "livraison" && !state.estimate ? ' estime' : '') + '</span>' +
          '<span class="val">' + money(total) + '</span>' +
        '</div>' +
      '</div>' +

      '<h2 class="pg-section-title">Mode de recuperation</h2>' +
      '<div class="mode-grid">' +
        '<button class="mode-btn ' + (state.mode === "retrait" ? "active" : "") + '" data-mode="retrait" type="button">' +
          '<span class="ico">&#127968;</span>Retrait' +
        '</button>' +
        '<button class="mode-btn ' + (state.mode === "livraison" ? "active" : "") + '" data-mode="livraison" type="button">' +
          '<span class="ico">&#128666;</span>Livraison' +
        '</button>' +
      '</div>' +

      '<div id="delivery-fields"' + deliveryFields + '>' +
        locInfo +
        '<div class="field">' +
          '<label for="address">Adresse de livraison</label>' +
          '<textarea id="address" rows="2" placeholder="Quartier, rue, repere...">' +
            escapeHtml(state.address || "") +
          '</textarea>' +
        '</div>' +
        '<button type="button" class="gps-btn" id="gps-btn">' +
          (state.lat !== null ? '&#128205; Actualiser ma position GPS' : '&#128205; Utiliser ma position GPS actuelle') +
        '</button>' +
        '<div class="gps-status" id="gps-status">' +
          (state.lat !== null
            ? '&#10003; Position : ' + Number(state.lat).toFixed(4) + ', ' + Number(state.lon).toFixed(4) +
              ' (&plusmn; ' + Math.round(state.acc || 0) + ' m)'
            : '') +
        '</div>' +
      '</div>' +

      '<div class="notes-block">' +
        '<label for="notes">Notes (facultatif)</label>' +
        '<textarea class="notes" id="notes" placeholder="Instructions particulieres, delai souhaite..."></textarea>' +
      '</div>' +

      '<div class="pg-actions">' +
        '<button class="btn btn-primary" id="submit-btn" type="button">Continuer vers le paiement</button>' +
        '<a class="btn btn-ghost" href="/professionnel/demande">Retour</a>' +
      '</div>' +

      '<div class="pg-info">' +
        '<strong>Prochaine etape :</strong> vous serez redirige vers la page de paiement. ' +
        'La pharmacie confirmera ensuite la disponibilite et preparera votre commande.' +
      '</div>';

    $("main").innerHTML = html;
    bindEvents();

    // Auto-calcul si GPS deja disponible (profil)
    if (state.mode === "livraison" && state.lat !== null && !state.estimate && !state.estimateLoading) {
      computeEstimate();
    }
  }

  function itemsRender() {
    if (!state.summary.items || state.summary.items.length === 0) {
      return '<div class="pg-info">Aucun produit.</div>';
    }
    return state.summary.items.map(function (it) {
      var priceHtml = it.unit_price > 0
        ? money(it.line_total) + '<small>' + money(it.unit_price) + ' / unite</small>'
        : '<small>Prix a confirmer</small>';
      return '<div class="it-row">' +
        '<div class="it-body">' +
          '<div class="it-name">' + escapeHtml(it.description) + '</div>' +
          '<div class="it-qty">x ' + qtyLabel(it.requested_quantity) + '</div>' +
        '</div>' +
        '<div class="it-price">' + priceHtml + '</div>' +
      '</div>';
    }).join("");
  }

  // ============================================================
  // Evenements
  // ============================================================
  function bindEvents() {
    Array.prototype.forEach.call(document.querySelectorAll(".mode-btn"), function (b) {
      b.addEventListener("click", function () {
        var newMode = b.getAttribute("data-mode");
        if (newMode !== state.mode) {
          state.mode = newMode;
          if (newMode === "retrait") {
            state.estimate = null;
          }
          render();
        }
      });
    });

    var gpsBtn = $("gps-btn");
    if (gpsBtn) gpsBtn.addEventListener("click", askGPS);

    var addrEl = $("address");
    if (addrEl) {
      addrEl.addEventListener("input", function () {
        state.address = addrEl.value;
      });
    }

    var sub = $("submit-btn");
    if (sub) sub.addEventListener("click", submit);
  }

  function askGPS() {
    if (!navigator.geolocation) {
      var s = $("gps-status");
      if (s) s.textContent = "GPS indisponible.";
      return;
    }
    var b = $("gps-btn");
    b.disabled = true;
    b.textContent = "Localisation...";
    navigator.geolocation.getCurrentPosition(function (pos) {
      state.lat = pos.coords.latitude;
      state.lon = pos.coords.longitude;
      state.acc = pos.coords.accuracy;
      state.autoLocation = false;
      b.disabled = false;
      b.innerHTML = "&#128205; Actualiser ma position GPS";
      var s = $("gps-status");
      if (s) s.innerHTML = "&#10003; Position obtenue, calcul du frais...";
      computeEstimate();
    }, function () {
      b.disabled = false;
      b.innerHTML = "&#128205; Utiliser ma position GPS actuelle";
      var s = $("gps-status");
      if (s) s.textContent = "Position introuvable. Saisissez l'adresse.";
    }, { enableHighAccuracy: true, timeout: 15000 });
  }

  function computeEstimate() {
    if (state.mode !== "livraison") return;
    if (state.estimateLoading) return;
    state.estimateLoading = true;

    api("POST", "/pro/requests/" + state.draft.reference + "/estimate-delivery", {
      delivery_mode: "livraison",
      latitude: state.lat,
      longitude: state.lon,
      location_accuracy: state.acc,
      address: state.address || "",
      notes: ""
    }).then(function (r) {
      state.estimate = r;
      state.estimateLoading = false;
      render();
    }).catch(function (e) {
      state.estimateLoading = false;
      toast("Impossible de calculer le frais : " + e.message);
    });
  }

  function submit() {
    var notes = $("notes") ? $("notes").value.trim() : "";
    var address = $("address") ? $("address").value.trim() : (state.address || "");

    if (state.mode === "livraison" && !address && state.lat === null) {
      toast("Adresse ou GPS obligatoire pour la livraison");
      return;
    }

    var payload = {
      delivery_mode: state.mode,
      address: address,
      notes: notes
    };
    if (state.lat !== null && state.lon !== null) {
      payload.latitude = state.lat;
      payload.longitude = state.lon;
      payload.location_accuracy = state.acc;
    }

    var btn = $("submit-btn");
    btn.disabled = true;
    btn.textContent = "Envoi...";

    api("POST", "/pro/requests/" + state.draft.reference + "/submit", payload)
      .then(function (r) {
        state.submitted = true;
        window.location.href = "/static/payment.html?ref=" + encodeURIComponent(r.order_reference);
      })
      .catch(function (e) {
        toast(e.message);
        btn.disabled = false;
        btn.textContent = "Continuer vers le paiement";
      });
  }

  function renderSuccess() {
    $("main").innerHTML = '<div style="text-align:center;padding:40px;color:#64748b">Redirection...</div>';
  }

  document.addEventListener("DOMContentLoaded", load);
})();
'''

CONF_JS.write_text(NEW_JS, encoding="utf-8")
print("[OK] professional_demande_confirmer.js -> auto localisation")
print()
print("Comportement :")
print("  - Charge l'adresse + GPS depuis /api/pro/organizations/me")
print("  - Si GPS dans le profil -> auto-calcul distance/frais")
print("  - Pre-remplit l'adresse sans demander")
print("  - Bouton 'Utiliser ma position' devient 'Actualiser' si deja positionne")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur iPhone (ou navigation privee)")
print("  Pas besoin de redemarrer Uvicorn")