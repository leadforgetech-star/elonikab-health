/* Elonikab Health - Panier (refonte V6 bleu) */
(function () {
  var API = "/api";

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

  function initials(name) {
    name = String(name || "").trim();
    if (!name) return "?";
    var p = name.split(" ").filter(function (x) { return x.length > 0; });
    var out = (p[0] || "").charAt(0);
    if (p.length > 1) out += p[1].charAt(0);
    return out.toUpperCase();
  }

  function renderEmpty() {
    $("main").innerHTML =
      '<div class="pt-empty">' +
        '<div class="pt-empty-ico">&#128722;</div>' +
        '<h2>Votre panier est vide</h2>' +
        '<p>Parcourez le catalogue pour ajouter des produits.</p>' +
        '<a class="pt-btn pt-btn-primary" href="/?nav=catalog">Voir le catalogue</a>' +
      '</div>';
  }

  function renderCart(d) {
    var items = (d && d.items) || [];
    if (items.length === 0) { renderEmpty(); return; }

    var html = '<h1 class="pt-page-title">Mon panier</h1>';
    html += '<p class="pt-page-sub">' + items.length +
            ' article' + (items.length > 1 ? 's' : '') + '</p>';
    html += '<div class="pt-card" style="margin-top:18px">';

    items.forEach(function (it) {
      var lineTotal = (it.line_total !== undefined && it.line_total !== null)
        ? Number(it.line_total)
        : Number(it.price) * Number(it.quantity);

      html += '<div class="pt-cart-item" data-id="' + it.id + '">';
      // Thumb
      html += '<div class="pt-cart-thumb">';
      if (it.image_url) {
        html += '<img loading="lazy" decoding="async" src="' + escapeHtml(it.image_url) +
                '" alt="' + escapeHtml(it.product_name) + '">';
      } else {
        html += '<div class="pt-cart-thumb-ph">' + escapeHtml(initials(it.product_name)) + '</div>';
      }
      html += '</div>';
      // Info
      html += '<div class="pt-cart-info">';
      html += '<h3 class="pt-cart-name">' + escapeHtml(it.product_name) + '</h3>';
      if (it.presentation) {
        html += '<p class="pt-cart-meta">' + escapeHtml(it.presentation) + '</p>';
      }
      html += '<div class="pt-cart-qty">';
      html += '<button data-action="dec" data-id="' + it.id +
              '"' + (it.quantity <= 1 ? ' disabled' : '') + '>&minus;</button>';
      html += '<span>' + it.quantity + '</span>';
      html += '<button data-action="inc" data-id="' + it.id + '">+</button>';
      html += '</div>';
      html += '</div>';
      // Price + delete
      html += '<div>';
      html += '<div class="pt-cart-price">' + money(lineTotal) + '</div>';
      html += '<button class="pt-cart-delete" data-action="del" data-id="' +
              it.id + '" aria-label="Supprimer">&#128465;</button>';
      html += '</div>';
      html += '</div>';
    });
    html += '</div>';

    // Totaux
    var subtotal = Number(d.subtotal) || 0;
    html += '<div class="pt-totals">';
    html += '<div class="pt-totals-row"><span class="lbl">Sous-total</span>' +
            '<span class="val">' + money(subtotal) + '</span></div>';
    html += '<div class="pt-totals-row"><span class="lbl">Livraison</span>' +
            '<span class="val">Calcul a l\'etape suivante</span></div>';
    html += '<div class="pt-totals-row pt-totals-total"><span>Total</span>' +
            '<span class="val">' + money(subtotal) + '</span></div>';
    html += '</div>';

    // Actions
    html += '<div class="pt-cart-actions">';
    html += '<button class="pt-btn pt-btn-danger" id="clear-cart">Vider le panier</button>';
    html += '<button class="pt-btn pt-btn-primary" id="checkout">Passer la commande</button>';
    html += '</div>';

    html += '<p style="text-align:center;margin-top:18px">' +
            '<a href="/?nav=catalog" style="color:var(--pt-blue);font-weight:700;font-size:14px">' +
            '&larr; Continuer mes achats</a></p>';

    $("main").innerHTML = html;
    bindActions();
  }

  function reload() {
    fetch(API + "/cart", { credentials: "same-origin" })
      .then(function (r) {
        if (r.status === 401) {
          window.location.href = "/connexion?next=/cart.html";
          return null;
        }
        return r.ok ? r.json() : null;
      })
      .then(function (d) {
        if (!d) { renderEmpty(); return; }
        renderCart(d);
      })
      .catch(function () { renderEmpty(); });
  }

  function updateQty(itemId, qty) {
    fetch(API + "/cart/items/" + itemId, {
      method: "PATCH",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quantity: qty })
    }).then(function (r) { return r.ok ? r.json() : null; })
      .then(function () { reload(); })
      .catch(function () {});
  }

  function removeItem(itemId) {
    fetch(API + "/cart/items/" + itemId, {
      method: "DELETE",
      credentials: "same-origin"
    }).then(function () { reload(); })
      .catch(function () {});
  }

  function clearCart() {
    if (!confirm("Vider le panier ?")) return;
    fetch(API + "/cart", { method: "DELETE", credentials: "same-origin" })
      .then(function () { reload(); })
      .catch(function () {});
  }

  function bindActions() {
    var main = $("main");
    main.querySelectorAll("[data-action]").forEach(function (b) {
      b.addEventListener("click", function () {
        var id = b.getAttribute("data-id");
        var act = b.getAttribute("data-action");
        var item = main.querySelector('[data-id="' + id + '"]');
        var qty = item ? Number(item.querySelector(".pt-cart-qty span").textContent) : 1;
        if (act === "inc") updateQty(id, qty + 1);
        else if (act === "dec") updateQty(id, Math.max(1, qty - 1));
        else if (act === "del") removeItem(id);
      });
    });

    var clr = $("clear-cart");
    if (clr) clr.addEventListener("click", clearCart);

    var ck = $("checkout");
    if (ck) ck.addEventListener("click", function () {
      checkout(ck);
    });
  }



  /* ============================================================
     FLUX DE COMMANDE
     1. POST /api/orders/v2 avec infos panier
     2. Recupere la reference reelle
     3. Redirige vers /payment.html?ref=<reference>
     ============================================================ */
  function checkout(btn) {
    window.location.href = "/checkout";
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
      t.style.opacity = "0";
      t.style.transition = "opacity .3s";
      setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 300);
    }, 3000);
  }

  document.addEventListener("DOMContentLoaded", reload);

  // Recharger si une notif arrive
  document.addEventListener("eh:refresh", reload);
})();
