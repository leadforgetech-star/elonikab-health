/* Elonikab Health - Suivi de commande */
(function () {
/* Mapping paiement EN -> FR */
var PAYMENT_LABELS_FR = {
  "NONE": "Aucun",
  "PENDING": "En attente",
  "PROOF_SUBMITTED": "Preuve soumise",
  "VERIFIED": "Verifie",
  "REJECTED": "Refuse",
  "REFUND_REQUIRED": "Remboursement requis",
  "REFUNDED": "Rembourse"
};
function paymentLabelFR(s) {
  if (!s) return "Aucun";
  return PAYMENT_LABELS_FR[String(s).toUpperCase()] || s;
}

  var API = "/api";
  var $ = function (id) { return document.getElementById(id); };

  var STATUS_PILLS = {
    en_attente: "pill-pending",
    confirmee: "pill-confirmed",
    en_preparation: "pill-preparing",
    prete: "pill-ready",
    en_livraison: "pill-in-delivery",
    terminee: "pill-done",
    refusee: "pill-refused",
  };

  var PAYMENT_PILLS = {
    NONE: "pill-none",
    PENDING: "pill-pending",
    PROOF_SUBMITTED: "pill-submitted",
    VERIFIED: "pill-verified",
    REJECTED: "pill-rejected",
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

  function fmtDate(iso) {
    if (!iso) return "";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return String(iso);
      var day = d.getDate();
      var month = ["janv.","fevr.","mars","avr.","mai","juin",
                   "juil.","aout","sept.","oct.","nov.","dec."][d.getMonth()];
      var h = ("0" + d.getHours()).slice(-2);
      var m = ("0" + d.getMinutes()).slice(-2);
      return day + " " + month + " " + d.getFullYear() + " a " + h + ":" + m;
    } catch (e) { return String(iso); }
  }

  function fmtQty(q) {
    var n = Number(q) || 0;
    return (n === Math.floor(n)) ? String(n) : n.toFixed(2);
  }

  function renderEmptyList() {
    $("main").innerHTML =
      '<div class="pt-empty">' +
        '<div class="pt-empty-ico">&#128230;</div>' +
        '<h2>Aucune commande</h2>' +
        '<p>Vous n\'avez pas encore de commande.</p>' +
        '<a class="pt-btn pt-btn-primary" href="/?nav=catalog">Voir le catalogue</a>' +
      '</div>';
  }

  function renderList(list) {
    if (!list || list.length === 0) { renderEmptyList(); return; }

    var html = '<h1 class="pt-page-title">Mes commandes</h1>';
    html += '<p class="pt-page-sub">' + list.length + ' commande' +
            (list.length > 1 ? 's' : '') + '</p>';
    html += '<div style="margin-top:18px">';

    list.forEach(function (o) {
      var subtotal = Number(o.subtotal) || 0;
      var fee = Number(o.delivery_fee) || 0;
      var total = subtotal + fee;
      var stPill = 'pt-pill-' + (o.status || 'en_attente');
      var date = fmtDate(o.created_at);
      var nItems = o.items_count || 0;
      var qty = o.quantity || 1;

      html += '<a class="pt-order-card" href="/suivi?ref=' +
              encodeURIComponent(o.reference) + '">';
      html += '<div class="pt-order-head">';
      html += '<div><div class="pt-order-ref">' + escapeHtml(o.reference) + '</div>';
      html += '<div class="pt-order-date">' + escapeHtml(date) + '</div></div>';
      html += '<span class="pt-pill ' + stPill + '">' +
              escapeHtml(o.status_label || o.status) + '</span>';
      html += '</div>';
      html += '<div class="pt-order-body">';
      html += '<span class="pt-order-meta">' + qty + ' produit' +
              (qty > 1 ? 's' : '') + ' &middot; ' +
              (o.delivery_mode === 'livraison' ? 'Livraison' : 'Retrait') + '</span>';
      html += '<span class="pt-order-total">' + money(total) + '</span>';
      html += '</div>';
      html += '</a>';
    });

    html += '</div>';
    $("main").innerHTML = html;
  }

  function loadList() {
    // Charger la liste des commandes du patient (via /api/orders/mine)
    fetch(API + "/orders/mine", { credentials: "same-origin" })
      .then(function (r) {
        if (r.status === 401) {
          window.location.href = "/connexion?next=/suivi";
          return null;
        }
        return r.ok ? r.json() : [];
      })
      .then(function (list) {
        if (!list) return;
        // Enrichir avec status_label
        var STATUS_LABELS = {
          en_attente: "En attente", confirmee: "Confirmee",
          en_preparation: "En preparation", prete: "Prete",
          en_livraison: "En livraison", terminee: "Terminee",
          refusee: "Refusee"
        };
        (list || []).forEach(function (o) {
          o.status_label = STATUS_LABELS[o.status] || o.status;
        });
        renderList(list);
      })
      .catch(function () { renderEmptyList(); });
  }

  function render(tl) {
    $("page-ref").textContent = tl.reference;

    var html = '';

    // En-tete
    html += '<div class="sv-head">' +
              '<div class="sv-head-ref">' + escapeHtml(tl.reference) + '</div>' +
              '<div class="sv-head-date">Creee le ' + escapeHtml(fmtDate(tl.created_at)) + '</div>' +
            '</div>';

    // Bloc Paiement
    var payPill = PAYMENT_PILLS[tl.payment_status] || "pill-none";
    html += '<div class="sv-block">' +
              '<div class="sv-block-title"><span class="ico">&#128179;</span> Paiement</div>' +
              '<span class="sv-status-pill ' + payPill + '">' +
                escapeHtml(paymentLabelFR(tl.payment_status)) +
              '</span>' +
              '<div class="sv-amounts">' +
                '<span class="lbl">Montant</span>' +
                '<span class="val">' + money(tl.total) + '</span>' +
              '</div>';

    if (tl.payment_status === "REJECTED" && tl.payment && tl.payment.rejection_reason) {
      html += '<div class="sv-rejection">Motif du refus : ' + escapeHtml(tl.payment.rejection_reason) + '</div>';
    }


    var _isRefused = (tl.status === "refusee");


    var _payStatus = (tl.payment_status || "NONE").toUpperCase();


    if (tl.can_pay && !_isRefused) {


      html += '<div class="sv-actions">' +


                '<a class="sv-btn sv-btn-primary" href="/static/payment.html?ref=' +


                  encodeURIComponent(tl.reference) + '">' +


                  '<span>&#128179;</span> Aller au paiement' +


                '</a>' +


              '</div>';


    } else if (_isRefused && _payStatus !== "NONE" && _payStatus !== "") {


      var _msg = "Aucune action de votre part n'est requise.";


      if (_payStatus === "PROOF_SUBMITTED") _msg = "Votre preuve de paiement sera examinee par la pharmacie. Contactez-la pour toute question.";


      else if (_payStatus === "VERIFIED") _msg = "Un paiement a ete valide. La pharmacie va traiter le remboursement.";


      else if (_payStatus === "REFUND_REQUIRED") _msg = "Un remboursement est en cours de traitement par la pharmacie.";


      else if (_payStatus === "REJECTED") _msg = "Le paiement a ete refuse. Contactez la pharmacie.";


      html += '<div style="margin-top:12px;padding:12px 14px;background:#fff4e0;color:#8a5a00;border-radius:10px;font-size:13px;line-height:1.5">';


      html += '&#9432; ' + escapeHtml(_msg);


      html += '</div>';


    }
    html += '</div>';

    // Bloc Commande
    var ordPill = STATUS_PILLS[tl.status] || "pill-none";
    html += '<div class="sv-block">' +
              '<div class="sv-block-title"><span class="ico">&#128230;</span> Commande</div>' +
              '<span class="sv-status-pill ' + ordPill + '">' +
                escapeHtml(tl.status_label) +
              '</span>';

    // Hint selon statut
    var hints = {
      en_attente: "Votre demande a ete recue. La pharmacie va l'examiner.",
      confirmee: "La pharmacie a valide votre commande.",
      en_preparation: "Votre commande est en cours de preparation.",
      prete: "Votre commande est prete.",
      terminee: "Votre commande a ete remise ou livree.",
      refusee: "La pharmacie n'a pas pu donner suite a cette demande.",
    };
    if (hints[tl.status]) {
      html += '<div class="sv-status-hint">' + escapeHtml(hints[tl.status]) + '</div>';
    }
      // Motif du refus (lu depuis timeline.events.hint)
      if (tl.status === "refusee") {
        var _rejectNote = "";
        if (tl.events && tl.events.length > 0) {
          for (var _i = tl.events.length - 1; _i >= 0; _i--) {
            var _ev = tl.events[_i];
            var _lbl = (_ev.label || "").toLowerCase();
            if (_lbl.indexOf("refus") >= 0 && (_ev.hint || _ev.note)) {
              _rejectNote = _ev.hint || _ev.note;
              break;
            }
          }
        }
        html += '<div style="margin-top:10px;padding:12px 14px;background:#fee2e2;color:#b23c3c;border-radius:10px;font-size:13px;line-height:1.5">';
        html += '<strong>Commande refusee</strong>';
        if (_rejectNote) {
          html += '<br><span style="opacity:.85">Motif : </span>' + escapeHtml(_rejectNote);
        }
        html += '</div>';
      }
    html += '</div>';

    // Timeline
    if (tl.events && tl.events.length > 0) {
      html += '<div class="sv-block">' +
                '<div class="sv-block-title"><span class="ico">&#128200;</span> Progression</div>' +
                '<div class="sv-timeline">';

      tl.events.forEach(function (ev) {
        var state = ev.state || "done";
        var stateClass = state === "error" ? "error" : (state === "current" ? "current" : "done");
        var symbol = state === "error" ? "&#10005;" : (state === "current" ? "&#9679;" : "&#10003;");
        html += '<div class="sv-step ' + stateClass + '">' +
                  '<div class="sv-dot">' + symbol + '</div>' +
                  '<div class="sv-info">' +
                    '<div class="sv-label">' + escapeHtml(ev.label) + '</div>' +
                    (ev.hint ? '<div class="sv-hint">' + escapeHtml(ev.hint) + '</div>' : '') +
                    (ev.at ? '<div class="sv-date">' + escapeHtml(fmtDate(ev.at)) + '</div>' : '') +
                  '</div>' +
                '</div>';
      });

      html += '</div></div>';
    }

    // Detail produits
    if (tl.items && tl.items.length > 0) {
      html += '<div class="sv-block">' +
                '<div class="sv-block-title"><span class="ico">&#128138;</span> Details</div>';

      tl.items.forEach(function (it) {
        var qty = Number(it.quantity) || 0;
        var unit = Number(it.unit_price) || 0;
        var line = Number(it.subtotal) || (unit * qty);
        html += '<div class="sv-item">' +
                  '<div class="sv-item-body">' +
                    '<div class="sv-item-name">' + escapeHtml(it.product_name || "") + '</div>' +
                    '<div class="sv-item-meta">x ' + fmtQty(qty) + ' - ' + money(unit) + '</div>' +
                  '</div>' +
                  '<div class="sv-item-price">' + money(line) + '</div>' +
                '</div>';
      });

      // Totaux
      html += '<div class="sv-totals">' +
                '<div class="sv-totals-line">' +
                  '<span class="lbl">Sous-total</span>' +
                  '<span class="val">' + money(tl.subtotal) + '</span>' +
                '</div>' +
                '<div class="sv-totals-line">' +
                  '<span class="lbl">Frais de livraison</span>' +
                  '<span class="val">' +
                    (tl.delivery_mode === "retrait" ? "0 FCFA" : money(tl.delivery_fee)) +
                  '</span>' +
                '</div>' +
                '<div class="sv-totals-line total">' +
                  '<span>Total</span>' +
                  '<span class="val">' + money(tl.total) + '</span>' +
                '</div>' +
              '</div>';

      html += '</div>';
    }

    // Infos livraison
    if (tl.delivery_mode === "livraison" && tl.address) {
      html += '<div class="sv-block">' +
                '<div class="sv-block-title"><span class="ico">&#128205;</span> Livraison</div>' +
                '<div style="font-size:14px;line-height:1.6">' + escapeHtml(tl.address) + '</div>' +
                (tl.delivery_distance_km !== null && tl.delivery_distance_km !== undefined
                  ? '<div style="font-size:12px;color:#64748b;margin-top:6px">Distance : ' +
                    Number(tl.delivery_distance_km).toFixed(1) + ' km</div>'
                  : '') +
              '</div>';
    }

    // Actions
    html += '<div class="sv-block">' +
              '<div class="sv-actions">' +
                '<a class="sv-btn sv-btn-wa" href="https://wa.me/22871039904?text=' +
                  encodeURIComponent("Bonjour, j'ai une question sur ma commande " + tl.reference) +
                  '" target="_blank" rel="noopener">' +
                  '<span>&#128172;</span> Contacter la pharmacie' +
                '</a>' +
                '<a class="sv-btn sv-btn-ghost" href="/" >' +
                  'Retour a mes commandes' +
                '</a>' +
              '</div>' +
            '</div>';

    $("main").innerHTML = html;
  }

  function load() {
    var params = new URLSearchParams(window.location.search);
    var ref = params.get("ref");
    if (!ref) { loadList(); return; }

    fetch(API + "/orders/" + encodeURIComponent(ref) + "/timeline", {
      credentials: "same-origin"
    }).then(function (r) {
      if (r.status === 404) {
        $("main").innerHTML = '<div class="sv-error">Commande introuvable : ' +
          escapeHtml(ref) + '</div>';
        var back = document.createElement("a");
        back.className = "sv-btn sv-btn-ghost";
        back.href = "/";
        back.textContent = "Retour a mes commandes";
        $("main").appendChild(back);
        return null;
      }
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    }).then(function (tl) {
      if (tl) render(tl);
    }).catch(function (e) {
      $("main").innerHTML = '<div class="sv-error">Erreur : ' +
        escapeHtml(e.message) + '</div>';
    });
  }

  // Temps reel : recharger la timeline quand une notif SSE arrive
  document.addEventListener("eh:refresh", function (ev) {
    console.log("[suivi] eh:refresh recu", ev && ev.detail);
    try { load(); } catch (e) { console.error("[suivi] load error", e); }
    try {
      var main = document.getElementById("main");
      if (main) {
        main.classList.remove("eh-flash-update");
        void main.offsetWidth;
        main.classList.add("eh-flash-update");
      }
    } catch (e) {}
  });

  document.addEventListener("DOMContentLoaded", load);
})();
