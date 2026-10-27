"""
fix_confirmer_page.py
Reecrit professional_demande_confirmer.html avec le design unifie.
"""
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
CONF_HTML = STATIC / "professional_demande_confirmer.html"

shutil.copy2(CONF_HTML, CONF_HTML.with_suffix(".html.bak4"))
print("[OK] Backup ->", CONF_HTML.with_suffix(".html.bak4").name)

NEW_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Confirmer ma demande - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<link rel="stylesheet" href="/static/professional_common.css">
<style>
/* Mode grid */
.mode-grid{
  display:grid;grid-template-columns:1fr 1fr;gap:10px;
  margin:6px 0 18px;
}
.mode-btn{
  padding:16px 10px;border:2px solid var(--line);border-radius:14px;
  background:#fff;font-family:inherit;font-size:14px;font-weight:800;
  color:var(--ink);cursor:pointer;text-align:center;
  transition:.15s;display:flex;flex-direction:column;
  align-items:center;gap:6px;
}
.mode-btn:hover{border-color:var(--blue)}
.mode-btn.active{
  border-color:var(--blue);background:var(--blue-soft);color:var(--blue-dark);
}
.mode-btn .ico{font-size:22px}

/* Section titre */
.sec-title{
  font-size:11px;font-weight:800;color:var(--muted);
  text-transform:uppercase;letter-spacing:.08em;
  margin:22px 0 10px;display:flex;
  align-items:center;justify-content:space-between;
}
.count-badge{
  background:var(--blue);color:#fff;
  font-size:10px;font-weight:800;
  padding:3px 9px;border-radius:999px;
}

/* Items recap */
.rp-item{
  display:flex;align-items:flex-start;gap:12px;
  padding:14px;background:#fff;border:1px solid var(--line);
  border-radius:12px;margin-bottom:8px;
}
.rp-body{flex:1;min-width:0}
.rp-name{
  font-size:14px;font-weight:700;margin:0 0 3px;
  word-break:break-word;line-height:1.35;
}
.rp-meta{font-size:12px;color:var(--muted);font-family:Consolas,monospace}
.rp-price{
  font-size:14px;font-weight:800;color:var(--ink);
  white-space:nowrap;flex-shrink:0;
  font-family:Consolas,monospace;text-align:right;
}
.rp-price small{
  display:block;font-size:11px;color:var(--muted);font-weight:500;
}

/* Totaux */
.totals-card{
  background:#fff;border:1px solid var(--line);border-radius:14px;
  padding:16px;margin-top:14px;
}
.totals-line{
  display:flex;justify-content:space-between;align-items:center;
  padding:7px 0;font-size:14px;
}
.totals-line .lbl{color:var(--muted)}
.totals-line .val{
  font-weight:700;font-family:Consolas,monospace;color:var(--ink);
}
.totals-line.total{
  border-top:1px solid var(--line);
  margin-top:6px;padding-top:12px;
  font-size:16px;font-weight:800;
}
.totals-line.total .val{color:var(--blue-dark);font-size:18px}
.totals-line .val.confirm{color:var(--muted);font-weight:600;font-size:13px}

/* Champs */
.field{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.field label{
  font-size:12px;font-weight:800;color:var(--muted);
  text-transform:uppercase;letter-spacing:.06em;
}
.field input,.field textarea,.field select{
  padding:12px 14px;border:1px solid var(--line);border-radius:12px;
  font-family:inherit;font-size:15px;outline:none;
  background:#fff;color:var(--ink);width:100%;
  transition:.15s;
}
.field input:focus,.field textarea:focus,.field select:focus{
  border-color:var(--blue);box-shadow:0 0 0 3px var(--blue-soft);
}

/* GPS */
.gps-btn{
  padding:12px 14px;border:1px solid var(--line);border-radius:12px;
  background:#fff;color:var(--ink);font-family:inherit;
  font-size:13px;font-weight:700;cursor:pointer;
  margin-top:6px;width:100%;transition:.15s;
}
.gps-btn:hover{border-color:var(--blue);color:var(--blue)}
.gps-status{
  font-size:12px;color:var(--muted);margin-top:6px;line-height:1.5;
}
.gps-status.ok{color:var(--ok);font-weight:600}

/* Notes */
.notes{
  width:100%;padding:12px 14px;
  border:1px solid var(--line);border-radius:12px;
  font-family:inherit;font-size:14px;background:#fff;
  outline:none;resize:vertical;min-height:64px;
  color:var(--ink);
}
.notes:focus{border-color:var(--blue);box-shadow:0 0 0 3px var(--blue-soft)}

/* Actions */
.actions-stack{
  display:flex;flex-direction:column;gap:10px;
  margin-top:20px;padding-top:18px;border-top:1px solid var(--line);
}
.btn-block{
  display:flex;align-items:center;justify-content:center;gap:8px;
  width:100%;padding:16px;border:0;border-radius:13px;
  font-weight:800;font-size:15px;transition:.15s;
  cursor:pointer;text-decoration:none;font-family:inherit;
}
.btn-primary{background:var(--blue);color:#fff}
.btn-primary:hover:not(:disabled){background:var(--blue-dark);transform:translateY(-1px)}
.btn-primary:disabled{background:#c7d5e3;cursor:not-allowed;color:#fff}
.btn-ghost{background:#fff;color:var(--ink);border:1px solid var(--line)}
.btn-ghost:hover{border-color:var(--blue);color:var(--blue)}

/* Info */
.pg-info{
  background:var(--blue-soft);border:1px solid var(--blue-line);
  border-radius:12px;padding:12px 14px;
  font-size:12.5px;color:var(--blue-dark);
  margin-top:14px;line-height:1.55;
}
.pg-info strong{font-weight:800}

.hint-ok{
  background:var(--ok-soft);border:1px solid #c7e9dc;
  color:var(--ok);border-radius:12px;padding:12px 14px;
  font-size:12.5px;margin-bottom:14px;line-height:1.5;
  display:flex;align-items:center;gap:8px;
}
.hint-ok .ico{font-size:16px;flex-shrink:0}

/* Success */
.success-box{
  background:var(--ok-soft);border:1px solid #c7e9dc;
  border-radius:16px;padding:28px 22px;text-align:center;
  margin:24px 0;
}
.success-icon{
  width:64px;height:64px;border-radius:50%;
  background:var(--ok);color:#fff;font-size:32px;
  display:flex;align-items:center;justify-content:center;
  margin:0 auto 14px;
}
.success-box h2{margin:0 0 6px;font-size:18px;color:var(--ok)}
.success-box p{color:var(--muted);font-size:13.5px;margin:0 0 14px}
.success-ref{
  background:#fff;border:1px dashed var(--line);
  border-radius:10px;padding:12px;
  font-family:Consolas,monospace;font-weight:800;
  color:var(--blue-dark);font-size:14px;display:inline-block;
}

@media (max-width:400px){
  .mode-grid{grid-template-columns:1fr}
}
</style>
</head>
<body>

<header class="pro-header">
  <div class="pro-header-inner">
    <a class="pro-brand" href="/professionnel">
      <span class="pro-brand-mark">+</span>
      Elokinab
    </a>
    <a class="pro-bell" href="/professionnel/commandes" aria-label="Notifications">
      &#128276;
    </a>
  </div>
</header>

<main class="pro-main" id="main">
  <div style="text-align:center;padding:40px;color:var(--muted)">Chargement...</div>
</main>

<script src="/static/safe_locale.js"></script>
<script>
(function () {
  "use strict";
  var API = "/api";
  var $ = function (id) { return document.getElementById(id); };

  var state = {
    draft: null,
    summary: null,
    mode: "retrait",
    lat: null,
    lon: null,
    acc: null,
    address: "",
    estimate: null,
    estimateLoading: false
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
      method: method,
      credentials: "same-origin",
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

  // ============================================================
  // Chargement
  // ============================================================
  function load() {
    return api("GET", "/pro/organizations/me")
      .then(function (org) {
        if (org) {
          if (org.latitude && org.longitude) {
            state.lat = org.latitude;
            state.lon = org.longitude;
          }
          if (org.delivery_address) {
            state.address = org.delivery_address;
          } else if (org.address) {
            state.address = org.address;
          }
        }
        return api("GET", "/pro/requests/draft");
      })
      .then(function (draft) {
        state.draft = draft;
        return api("GET", "/pro/requests/" + encodeURIComponent(draft.reference) + "/summary");
      })
      .then(function (sum) {
        state.summary = sum;
        if (sum.items_count === 0 && sum.attachments_count === 0) {
          window.location.href = "/professionnel/demande";
          return;
        }
        render();
      })
      .catch(function (e) {
        $("main").innerHTML = '<div style="text-align:center;padding:40px;color:#dc2626">Erreur : ' +
          escapeHtml(e.message) + '</div>';
      });
  }

  // ============================================================
  // Rendu
  // ============================================================
  function render() {
    var s = state.summary;
    var subtotal = s.subtotal;
    var fee = (state.estimate && state.estimate.delivery_fee) || 0;
    var total = state.mode === "livraison" && state.estimate
      ? (state.estimate.total || subtotal + fee)
      : subtotal;

    var html = '';

    // Info GPS automatique
    if (state.mode === "livraison" && state.lat && state.lon) {
      html += '<div class="hint-ok"><span class="ico">&#10003;</span>' +
        'Adresse GPS de votre profil utilisee automatiquement. ' +
        'Vous pouvez la modifier ci-dessous.</div>';
    }

    // Recap
    html += '<h2 class="sec-title">' +
      'Recapitulatif <span class="count-badge">' + s.items_count + '</span>' +
    '</h2>';
    if (s.items) {
      s.items.forEach(function (it) {
        var priceHtml = it.unit_price > 0
          ? money(it.line_total) + '<small>' + money(it.unit_price) + ' / unite</small>'
          : '<small>Prix a confirmer</small>';
        html += '<div class="rp-item">' +
          '<div class="rp-body">' +
            '<div class="rp-name">' + escapeHtml(it.description) + '</div>' +
            '<div class="rp-meta">x ' + qtyLabel(it.requested_quantity) + '</div>' +
          '</div>' +
          '<div class="rp-price">' + priceHtml + '</div>' +
        '</div>';
      });
    }

    // Totaux
    html += '<div class="totals-card">' +
      '<div class="totals-line">' +
        '<span class="lbl">Sous-total</span>' +
        '<span class="val">' + money(subtotal) + '</span>' +
      '</div>';
    if (state.mode === "livraison") {
      if (state.estimate && state.estimate.source === "gps") {
        html +=
          '<div class="totals-line">' +
            '<span class="lbl">Distance</span>' +
            '<span class="val">' + state.estimate.distance_km + ' km</span>' +
          '</div>' +
          '<div class="totals-line">' +
            '<span class="lbl">Frais de livraison</span>' +
            '<span class="val">' + money(state.estimate.delivery_fee) + '</span>' +
          '</div>';
      } else if (state.estimate && state.estimate.source === "no_gps") {
        html +=
          '<div class="totals-line">' +
            '<span class="lbl">Frais de livraison</span>' +
            '<span class="val confirm">Activez le GPS</span>' +
          '</div>';
      } else if (state.estimate && state.estimate.source === "no_pharmacy") {
        html +=
          '<div class="totals-line">' +
            '<span class="lbl">Frais de livraison</span>' +
            '<span class="val confirm">A confirmer</span>' +
          '</div>';
      } else {
        html +=
          '<div class="totals-line">' +
            '<span class="lbl">Frais de livraison</span>' +
            '<span class="val confirm">En attente</span>' +
          '</div>';
      }
    } else {
      html +=
        '<div class="totals-line">' +
          '<span class="lbl">Frais de livraison</span>' +
          '<span class="val">Retrait - 0 F</span>' +
        '</div>';
    }
    html +=
      '<div class="totals-line total">' +
        '<span>Total' + (state.mode === "livraison" && !state.estimate ? ' estime' : '') + '</span>' +
        '<span class="val">' + money(total) + '</span>' +
      '</div>' +
    '</div>';

    // Mode
    html += '<h2 class="sec-title">Mode de recuperation</h2>';
    html += '<div class="mode-grid">' +
      '<button class="mode-btn ' + (state.mode === "retrait" ? "active" : "") + '" data-mode="retrait" type="button">' +
        '<span class="ico">&#127968;</span>Retrait' +
      '</button>' +
      '<button class="mode-btn ' + (state.mode === "livraison" ? "active" : "") + '" data-mode="livraison" type="button">' +
        '<span class="ico">&#128666;</span>Livraison' +
      '</button>' +
    '</div>';

    // Champs livraison
    if (state.mode === "livraison") {
      html += '<div class="field">' +
        '<label for="address">Adresse de livraison</label>' +
        '<textarea id="address" rows="2" placeholder="Quartier, rue, repere...">' +
          escapeHtml(state.address || "") +
        '</textarea>' +
      '</div>' +
      '<button type="button" class="gps-btn" id="gps-btn">' +
        (state.lat !== null
          ? '&#128205; Actualiser ma position GPS'
          : '&#128205; Utiliser ma position GPS actuelle') +
      '</button>' +
      '<div class="gps-status' + (state.lat !== null ? ' ok' : '') + '" id="gps-status">' +
        (state.lat !== null
          ? '&#10003; Position : ' + Number(state.lat).toFixed(4) + ', ' + Number(state.lon).toFixed(4)
          : '') +
      '</div>';
    }

    // Notes
    html += '<h2 class="sec-title">Notes (facultatif)</h2>';
    html += '<textarea class="notes" id="notes" placeholder="Instructions particulieres, delai souhaite..."></textarea>';

    // Actions
    html += '<div class="actions-stack">' +
      '<button class="btn-block btn-primary" id="submit-btn" type="button">' +
        'Continuer vers le paiement &#8594;' +
      '</button>' +
      '<a class="btn-block btn-ghost" href="/professionnel/demande">Retour</a>' +
    '</div>';

    // Info finale
    html += '<div class="pg-info">' +
      '<strong>Prochaine etape :</strong> vous serez redirige vers la page de paiement. ' +
      'Reglez par Mixx ou Flooz puis envoyez la preuve de paiement.' +
    '</div>';

    $("main").innerHTML = html;
    bindEvents();

    // Si livraison + GPS dispo -> calcul auto
    if (state.mode === "livraison" && state.lat !== null && !state.estimate && !state.estimateLoading) {
      computeEstimate();
    }
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
          if (newMode === "retrait") state.estimate = null;
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
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        state.lat = pos.coords.latitude;
        state.lon = pos.coords.longitude;
        state.acc = pos.coords.accuracy;
        b.disabled = false;
        b.innerHTML = "&#128205; Actualiser ma position GPS";
        var s = $("gps-status");
        if (s) {
          s.classList.add("ok");
          s.innerHTML = "&#10003; Position obtenue, calcul du frais...";
        }
        computeEstimate();
      },
      function () {
        b.disabled = false;
        b.innerHTML = "&#128205; Utiliser ma position GPS actuelle";
        var s = $("gps-status");
        if (s) s.textContent = "Position introuvable. Vous pouvez saisir l'adresse.";
      },
      { enableHighAccuracy: true, timeout: 15000 }
    );
  }

  function computeEstimate() {
    if (state.mode !== "livraison") return;
    if (state.estimateLoading) return;
    state.estimateLoading = true;

    api("POST", "/pro/requests/" + encodeURIComponent(state.draft.reference) + "/estimate-delivery", {
      delivery_mode: "livraison",
      latitude: state.lat,
      longitude: state.lon,
      location_accuracy: state.acc,
      address: state.address || "",
      notes: ""
    })
      .then(function (r) {
        state.estimate = r;
        state.estimateLoading = false;
        render();
      })
      .catch(function (e) {
        state.estimateLoading = false;
        console.error("estimate error", e);
      });
  }

  function submit() {
    var notes = $("notes") ? $("notes").value.trim() : "";
    var address = $("address") ? $("address").value.trim() : (state.address || "");

    if (state.mode === "livraison" && !address && state.lat === null) {
      alert("Adresse ou GPS obligatoire pour la livraison");
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

    api("POST", "/pro/requests/" + encodeURIComponent(state.draft.reference) + "/submit", payload)
      .then(function (r) {
        window.location.href = "/static/payment.html?ref=" + encodeURIComponent(r.order_reference);
      })
      .catch(function (e) {
        alert(e.message);
        btn.disabled = false;
        btn.innerHTML = "Continuer vers le paiement &#8594;";
      });
  }

  document.addEventListener("DOMContentLoaded", load);
})();
</script>
</body>
</html>
'''

CONF_HTML.write_text(NEW_HTML, encoding="utf-8")
print("[OK] professional_demande_confirmer.html reecrit")

print()
print("=" * 60)
print("PAGE CONFIRMER CORRIGEE")
print("=" * 60)
print()
print("Ameliorations :")
print("  - Design aligne sur le reste de l'espace pro")
print("  - GPS du profil utilise automatiquement")
print("  - Cards items + totaux detaillees")
print("  - Bouton Continuer vers le paiement")
print("  - Feedback visuel instantane")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur /professionnel/demande/confirmer")
print("=" * 60)