/* Elonikab Health - Page demande */
(function () {
  var API = "/api";
  var $ = function (id) { return document.getElementById(id); };

  var state = { draft: null, summary: null };

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
    if (n === Math.floor(n)) return String(n);
    return n.toFixed(2);
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
  function loadDraft() {
    return api("GET", "/pro/requests/draft").then(function (d) {
      state.draft = d;
      return api("GET", "/pro/requests/" + encodeURIComponent(d.reference) + "/summary");
    }).then(function (sum) {
      state.summary = sum;
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
    var sum = state.summary;
    if (!sum) return;

    $("page-ref").textContent = sum.reference;
    var navCount = $("nav-count");
    if (sum.items_count > 0) {
      navCount.textContent = sum.items_count > 99 ? "99+" : String(sum.items_count);
      navCount.classList.remove("hidden");
    } else {
      navCount.classList.add("hidden");
    }

    if (sum.items_count === 0 && sum.attachments_count === 0) {
      renderGateway();
    } else {
      renderReview();
    }
  }

  function renderGateway() {
    $("page-title").textContent = "Nouvelle demande";
    $("main").innerHTML = '' +
      '<div class="gw-hero">' +
        '<h1>Comment souhaitez-vous<br>passer votre demande ?</h1>' +
        '<p>Choisissez une methode selon votre besoin.</p>' +
      '</div>' +
      '<div class="gw-cards">' +
        '<a class="gw-card cat" href="/professionnel/catalogue">' +
          '<div class="gw-card-icon">&#128269;</div>' +
          '<h2 class="gw-card-title">Depuis le catalogue</h2>' +
          '<p class="gw-card-desc">Choisissez vos produits, quantites, et finalisez votre demande.</p>' +
          '<div class="gw-card-foot">' +
            '<span class="gw-card-cta">Parcourir le catalogue</span>' +
            '<span class="gw-card-arrow">&#8594;</span>' +
          '</div>' +
        '</a>' +
        '<div class="gw-or">ou</div>' +
        '<a class="gw-card wa" target="_blank" rel="noopener" ' +
           'href="https://wa.me/22871039904?text=Bonjour%20Elonikab%20Health%2C%20je%20souhaite%20passer%20une%20commande.%20Voici%20ma%20liste%20%3A%0A%0A">' +
          '<div class="gw-card-icon">&#128172;</div>' +
          '<h2 class="gw-card-title">Via WhatsApp</h2>' +
          '<p class="gw-card-desc">Envoyez votre liste, photo, PDF, message ou vocal directement.</p>' +
          '<div class="gw-card-foot">' +
            '<span class="gw-card-cta">Ouvrir WhatsApp</span>' +
            '<span class="gw-card-arrow">&#8594;</span>' +
          '</div>' +
        '</a>' +
      '</div>' +
      '<div class="pg-info">' +
        '<strong>Conseil :</strong> utilisez le catalogue pour les produits que vous connaissez, WhatsApp pour les listes libres ou les produits non references.' +
      '</div>';
  }

  function renderReview() {
    $("page-title").textContent = "Ma demande";
    var items = sum_items_render(state.summary);
    var atts = state.summary.attachments_count > 0
      ? '<div class="pg-info">' + state.summary.attachments_count +
        ' piece(s) jointe(s) dans votre demande.</div>'
      : '';

    var html = '' +
      '<h2 class="pg-section-title">' +
        'Ma demande <span class="pg-count">' + state.summary.items_count + '</span>' +
      '</h2>' +
      items +
      atts +
      '<div class="totals-card">' +
        '<div class="totals-line">' +
          '<span class="lbl">Sous-total</span>' +
          '<span class="val">' + money(state.summary.subtotal) + '</span>' +
        '</div>' +
        '<div class="totals-line">' +
          '<span class="lbl">Livraison</span>' +
          '<span class="val confirm">A confirmer</span>' +
        '</div>' +
        '<div class="totals-line total">' +
          '<span>Total</span>' +
          '<span class="val">' + money(state.summary.subtotal) + ' + livraison</span>' +
        '</div>' +
      '</div>' +
      '<div class="pg-info">' +
        '<strong>Prochaine etape :</strong> votre demande sera transmise a la pharmacie ' +
        'qui confirmera la disponibilite, les quantites et les prix finaux. ' +
        'Vous recevrez une confirmation avant paiement.' +
      '</div>' +
      '<div class="pg-actions">' +
        '<a class="btn btn-ghost" href="/professionnel/catalogue">+ Ajouter des produits</a>' +
        '<a class="btn btn-primary" href="/professionnel/demande/confirmer">Continuer &#8594;</a>' +
        '<button class="btn btn-danger" id="btn-clear" type="button">Vider ma demande</button>' +
      '</div>';

    $("main").innerHTML = html;

    // Handlers
    Array.prototype.forEach.call($("main").querySelectorAll("[data-del]"), function (b) {
      b.addEventListener("click", function () {
        var id = b.getAttribute("data-del");
        api("DELETE", "/pro/requests/" + state.draft.reference + "/items/" + id)
          .then(loadDraft).catch(function (e) { toast(e.message); });
      });
    });
    var clearBtn = $("btn-clear");
    if (clearBtn) clearBtn.addEventListener("click", clearAll);
  }

  function sum_items_render(sum) {
    if (!sum.items || sum.items.length === 0) {
      return '<div style="text-align:center;padding:24px;color:#64748b">Aucun produit.</div>';
    }
    return sum.items.map(function (it) {
      var priceHtml = it.unit_price > 0
        ? money(it.line_total) + '<small>' + money(it.unit_price) + ' / unite</small>'
        : '<small>Prix a confirmer</small>';
      return '<div class="it-row">' +
        '<div class="it-body">' +
          '<div class="it-name">' + escapeHtml(it.description) + '</div>' +
          '<div class="it-qty">x ' + qtyLabel(it.requested_quantity) + '</div>' +
        '</div>' +
        '<div class="it-price">' + priceHtml + '</div>' +
        '<button class="it-del" data-del="' + it.id + '" title="Retirer">&times;</button>' +
      '</div>';
    }).join("");
  }

  function clearAll() {
    if (!state.summary || !state.summary.items) return;
    if (!confirm("Vider toute votre demande ?")) return;
    var chain = Promise.resolve();
    state.summary.items.forEach(function (it) {
      chain = chain.then(function () {
        return api("DELETE", "/pro/requests/" + state.draft.reference + "/items/" + it.id);
      });
    });
    chain.then(loadDraft).catch(function (e) { toast(e.message); });
  }

  document.addEventListener("DOMContentLoaded", loadDraft);
})();
