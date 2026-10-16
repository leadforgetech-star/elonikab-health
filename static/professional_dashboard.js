/* Elonikab Health - Accueil professionnel V7 */
(function () {
  "use strict";
  var API = "/api";
  var $ = function (id) { return document.getElementById(id); };

  var state = {
    org: null,
    orders: [],
    stats: {
      total: 0,
      last_order: null,
      alert_type: null,
      alert_order: null
    }
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
  function fmtDate(iso) {
    if (!iso) return "";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return String(iso);
      var day = d.getDate();
      var m = ["janv.","fevr.","mars","avr.","mai","juin",
               "juil.","aout","sept.","oct.","nov.","dec."][d.getMonth()];
      return day + " " + m + " " + d.getFullYear();
    } catch (e) { return String(iso); }
  }
  function api(path) {
    return fetch(API + path, { credentials: "same-origin" }).then(function (r) {
      if (r.status === 401) {
        window.location.href = "/connexion?next=/professionnel";
        throw new Error("Non authentifie");
      }
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    });
  }

  var STATUS_PILLS = {
    en_attente: "pill-pending", confirmee: "pill-confirmed",
    en_preparation: "pill-preparing", prete: "pill-ready",
    
    
    en_livraison: "En livraison",
en_livraison: "pill-in-delivery",
terminee: "pill-done", refusee: "pill-refused"
  };
  var STATUS_LABELS = {
    en_attente: "En attente", confirmee: "Confirmee",
    en_preparation: "En preparation", prete: "Prete",
    terminee: "Terminee", refusee: "Refusee"
  };
  var PAYMENT_PILLS = {
    NONE: "pill-none", PENDING: "pill-pending",
    PROOF_SUBMITTED: "pill-submitted",
    VERIFIED: "pill-verified", REJECTED: "pill-rejected"
  };

  // ============================================================
  // LOAD
  // ============================================================
  function load() {
    return Promise.all([
      api("/pro/organizations/me").catch(function () { return null; }),
      api("/orders/mine").catch(function () { return []; }),
      api("/notifications?unread_only=1").catch(function () { return []; })
    ]).then(function (r) {
      state.org = r[0];
      var orders = Array.isArray(r[1]) ? r[1] : [];
      var notifs = Array.isArray(r[2]) ? r[2] : [];

      state.orders = orders.filter(function (o) {
        return o.status !== "DRAFT" && o.status !== "draft";
      });

      renderBell(notifs.length);
      analyze();
      renderWelcome();
      renderAlert();
      renderReorder();
      renderGuide();
      renderActivity();
      loadNotifications();
    }).catch(function (e) {
      console.error("[accueil] load error", e);
    });
  }

  function renderBell(n) {
    var b = $("bell-badge");
    if (!b) return;
    if (n > 0) {
      b.textContent = n > 99 ? "99+" : String(n);
      b.classList.remove("hidden");
    } else {
      b.classList.add("hidden");
    }
  }

  function analyze() {
    var st = { total: state.orders.length, last_order: null,
               alert_type: null, alert_order: null };
    var sorted = state.orders.slice().sort(function (a, b) {
      return (b.created_at || "").localeCompare(a.created_at || "");
    });
    if (sorted.length > 0) st.last_order = sorted[0];

    var rejected = null, pending = null;
    sorted.forEach(function (o) {
      var ps = o.payment_status || "NONE";
      if (ps === "REJECTED" && !rejected) rejected = o;
      if (ps === "PENDING" && o.status !== "refusee" && !pending) pending = o;
    });
    if (rejected) { st.alert_type = "rejected"; st.alert_order = rejected; }
    else if (pending) { st.alert_type = "pending"; st.alert_order = pending; }

    state.stats = st;
  }

  // ============================================================
  // RENDERS
  // ============================================================
  function renderWelcome() {
    var h = $("hello");
    if (!h) return;
    var name = (state.org && state.org.structure_name) || "Professionnel";
    h.textContent = "Bonjour, " + name;
  }

  function renderAlert() {
    var box = $("alert-block");
    if (!box) return;
    box.innerHTML = "";
    if (!state.stats.alert_type || !state.stats.alert_order) return;

    var o = state.stats.alert_order;
    var total = (Number(o.subtotal) || 0) + (Number(o.delivery_fee) || 0);
    var isRejected = state.stats.alert_type === "rejected";

    var a = document.createElement("a");
    a.className = "alert-action" + (isRejected ? " rejected" : "");
    a.href = "/static/payment.html?ref=" + encodeURIComponent(o.reference);

    if (isRejected) {
      a.innerHTML =
        '<div class="alert-ico">&#9888;</div>' +
        '<div class="alert-body">' +
        '<h3 class="alert-title">Preuve de paiement refusee</h3>' +
        '<p class="alert-desc">Commande <strong>' + escapeHtml(o.reference) + '</strong> - ' + money(total) + '. Renvoyez une preuve valide.</p>' +
        '<span class="alert-cta">Renvoyer une preuve &#8594;</span>' +
        '</div>';
    } else {
      a.innerHTML =
        '<div class="alert-ico">&#9200;</div>' +
        '<div class="alert-body">' +
        '<h3 class="alert-title">Paiement en attente</h3>' +
        '<p class="alert-desc">Commande <strong>' + escapeHtml(o.reference) + '</strong> - ' + money(total) + '. Effectuez le transfert pour lancer la preparation.</p>' +
        '<span class="alert-cta">Payer maintenant &#8594;</span>' +
        '</div>';
    }
    box.appendChild(a);
  }

  function renderReorder() {
    var section = $("reorder-section");
    var box = $("reorder-block");
    if (!section || !box) return;
    var last = state.stats.last_order;
    if (!last) { section.classList.add("hidden"); return; }

    section.classList.remove("hidden");
    var itemsCount = last.items_count || 1;
    var a = document.createElement("a");
    a.className = "reorder-card";
    a.href = "/professionnel/commande/" + encodeURIComponent(last.reference) + "/reprendre";
    a.innerHTML =
      '<div class="reorder-icon">&#128257;</div>' +
      '<div class="reorder-body">' +
      '<div class="reorder-label">Derniere commande</div>' +
      '<div class="reorder-ref">' + escapeHtml(last.reference) + '</div>' +
      '<div class="reorder-meta">' + escapeHtml(fmtDate(last.created_at)) + ' - ' + itemsCount + ' produit' + (itemsCount > 1 ? 's' : '') + '</div>' +
      '</div>' +
      '<span class="reorder-arrow">&#8594;</span>';
    box.innerHTML = "";
    box.appendChild(a);
  }

  function renderGuide() {
    var section = $("guide-section");
    var box = $("guide-block");
    if (!section || !box) return;
    if (state.orders.length > 0) { section.classList.add("hidden"); return; }

    section.classList.remove("hidden");
    box.innerHTML =
      '<h3>Comment commander sur Elonikab ?</h3>' +
      '<div class="guide-steps">' +
        '<div class="guide-step">' +
          '<div class="guide-num">1</div>' +
          '<div class="guide-body">' +
            '<p class="guide-text">Ouvrez l\u2019onglet <strong>+ Demande</strong> puis choisissez votre methode :</p>' +
            '<p class="guide-sub">' +
              '<span class="item">&#8226; <strong>Catalogue</strong> : ajoutez vos produits un par un</span>' +
              '<span class="item">&#8226; <strong>WhatsApp</strong> : envoyez votre liste (texte, photo ou PDF)</span>' +
            '</p>' +
          '</div>' +
        '</div>' +
        '<div class="guide-step">' +
          '<div class="guide-num">2</div>' +
          '<div class="guide-body"><p class="guide-text">Validez le recapitulatif et envoyez votre demande.</p></div>' +
        '</div>' +
        '<div class="guide-step">' +
          '<div class="guide-num">3</div>' +
          '<div class="guide-body"><p class="guide-text">Reglez par <strong>Mixx</strong> ou <strong>Flooz</strong>, puis envoyez la preuve de paiement.</p></div>' +
        '</div>' +
        '<div class="guide-step">' +
          '<div class="guide-num">4</div>' +
          '<div class="guide-body"><p class="guide-text">Recevez votre commande apres validation de la pharmacie.</p></div>' +
        '</div>' +
      '</div>';
  }

  function renderActivity() {
    var box = $("activity");
    if (!box) return;

    var sorted = state.orders.slice().sort(function (a, b) {
      return (b.created_at || "").localeCompare(a.created_at || "");
    }).slice(0, 5);

    if (sorted.length === 0) {
      box.innerHTML =
        '<div class="empty-state">' +
          '<div class="icon">&#128230;</div>' +
          'Aucune commande pour le moment.<br>' +
          'Vos futures commandes apparaitront ici.' +
        '</div>';
      return;
    }

    var wrap = document.createElement("div");
    wrap.className = "activity-list";
    sorted.forEach(function (o) {
      var pill = STATUS_PILLS[o.status] || "pill-none";
      var lbl = STATUS_LABELS[o.status] || o.status;
      var total = (Number(o.subtotal) || 0) + (Number(o.delivery_fee) || 0);

      var a = document.createElement("a");
      a.className = "activity-item";
      a.href = "/suivi?ref=" + encodeURIComponent(o.reference);
      a.innerHTML =
        '<div class="activity-body">' +
          '<div class="activity-ref">' + escapeHtml(o.reference) + '</div>' +
          '<div class="activity-meta">' + escapeHtml(fmtDate(o.created_at)) + ' - ' + money(total) + '</div>' +
        '</div>' +
        '<span class="pill ' + pill + '">' + escapeHtml(lbl) + '</span>';
      wrap.appendChild(a);
    });
    box.innerHTML = "";
    box.appendChild(wrap);

    if (state.orders.length > 5) {
      var more = document.createElement("a");
      more.className = "link-more";
      more.href = "/professionnel/commandes";
      more.innerHTML = "Voir toute l\u2019activite &#8594;";
      box.appendChild(more);
    }
  }

  // ============================================================
  // NOTIFICATIONS
  // ============================================================
  function notifIcon(type) {
    if (type === "payment") return { cls: "payment", char: "\uD83D\uDCB0" };
    if (type === "order") return { cls: "order", char: "\uD83D\uDCE6" };
    if (type === "prescription") return { cls: "prescription", char: "\u2695\uFE0F" };
    return { cls: "default", char: "\uD83D\uDD14" };
  }
  function notifTypeFromData(n) {
    var t = String(n.title || "").toLowerCase();
    if (t.indexOf("paiement") >= 0) return "payment";
    if (t.indexOf("commande") >= 0) return "order";
    if (t.indexOf("ordonnance") >= 0) return "prescription";
    return "default";
  }

  function loadNotifications() {
    return api("/notifications?unread_only=1")
      .then(function (list) { renderNotifications(Array.isArray(list) ? list : []); })
      .catch(function () { renderNotifications([]); });
  }

  function renderNotifications(list) {
    var section = $("notifications-section");
    var box = $("notifications");
    if (!section || !box) return;

    if (!list || list.length === 0) {
      section.classList.add("hidden");
      box.innerHTML = "";
      return;
    }
    section.classList.remove("hidden");

    var wrap = document.createElement("div");
    wrap.className = "notif-list";

    list.slice(0, 4).forEach(function (n) {
      var icon = notifIcon(notifTypeFromData(n));
      var target = "/suivi";
      var m = String(n.body || "").match(/CMD-[0-9]{6}-[A-Z0-9]+/);
      if (m) target = "/suivi?ref=" + encodeURIComponent(m[0]);
      else if (n.order_id) target = "#";

      var dateStr = "";
      try {
        var d = new Date(n.created_at);
        if (!isNaN(d.getTime())) {
          var pad = function (x) { return x < 10 ? "0" + x : "" + x; };
          dateStr = pad(d.getDate()) + "/" + pad(d.getMonth() + 1) +
                    " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
        }
      } catch (e) {}

      var a = document.createElement("a");
      a.className = "notif-item";
      a.href = target;
      a.setAttribute("data-notif-id", String(n.id));
      a.innerHTML =
        '<div class="notif-icon ' + icon.cls + '">' + icon.char + '</div>' +
        '<div class="notif-body">' +
          '<div class="notif-title">' + escapeHtml(n.title || "Notification") + '</div>' +
          '<div class="notif-text">' + escapeHtml(n.body || "") + '</div>' +
          '<div class="notif-date">' + escapeHtml(dateStr) + '</div>' +
        '</div>';
      a.addEventListener("click", function () {
        var id = a.getAttribute("data-notif-id");
        if (!id) return;
        fetch(API + "/notifications/" + id + "/read", {
          method: "PATCH", credentials: "same-origin"
        }).catch(function () {});
      });
      wrap.appendChild(a);
    });

    box.innerHTML = "";
    box.appendChild(wrap);

    var btn = $("mark-all-read");
    if (btn) {
      var newBtn = btn.cloneNode(true);
      btn.parentNode.replaceChild(newBtn, btn);
      newBtn.addEventListener("click", function (ev) {
        ev.preventDefault();
        fetch(API + "/notifications/read-all", {
          method: "PATCH", credentials: "same-origin"
        }).then(function () {
          renderNotifications([]);
          renderBell(0);
        }).catch(function () {});
      });
    }
  }

  // ============================================================
  // NAV COUNT
  // ============================================================
  function loadNavCount() {
    fetch(API + "/pro/requests/draft", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) return;
        return fetch(API + "/pro/requests/" + d.reference, { credentials: "same-origin" })
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (full) {
            if (!full) return;
            var n = (full.items || []).length + (full.attachments || []).length;
            var c = $("nav-count");
            if (c && n > 0) {
              c.textContent = n > 99 ? "99+" : String(n);
              c.classList.remove("hidden");
            }
          });
      }).catch(function () {});
  }

  // ============================================================
  // INIT
  // ============================================================
  function init() {
    var btn = $("new-request");
    if (btn) {
      btn.addEventListener("click", function () {
        window.location.href = "/professionnel/demande";
      });
    }
    load();
    loadNavCount();

    // Soft refresh : reactualiser les donnees quand une notif SSE arrive
    document.addEventListener("eh:refresh", function () {
      try { load(); } catch (e) {}
      try { loadNavCount(); } catch (e) {}
      try {
        var act = document.getElementById("activity-list")
                || document.querySelector(".activity-list")
                || document.querySelector("[data-activity]");
        if (act) {
          act.classList.remove("eh-flash-update");
          void act.offsetWidth;
          act.classList.add("eh-flash-update");
        }
      } catch (e) {}
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
