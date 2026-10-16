var API = "/api";
var CURRENCY = " FCFA";
var pharmacySettings = { delivery_fee_default: 0 };

var state = { categories: [], products: [], product: null, category: "", order: null };

function $(sel) { return document.querySelector(sel); }

function money(v) {
  var n = Math.round(Number(v) || 0);
  return n.toLocaleString("fr-FR") + " FCFA";
}

function el(tag, className, text) {
  var node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

function showView(name) {
  // Retirer la classe anti-flash (le SPA prend le relais)
  try { document.documentElement.classList.remove("pt-preload-catalog"); } catch (e) {}
  var views = document.querySelectorAll(".view");
  Array.prototype.forEach.call(views, function (v) { v.classList.add("hidden"); });
  var target = document.getElementById("view-" + name);
  if (target) target.classList.remove("hidden");
  window.scrollTo(0, 0);
}

function apiGet(path) {
  return fetch(API + path).then(function (r) {
    if (!r.ok) throw new Error("Erreur serveur");
    return r.json();
  });
}

function availabilityTag(value) {
  var span = el("span", "tag");
  if (value === "disponible") {
    span.classList.add("tag-ok");
    span.textContent = "Disponible";
  } else {
    span.classList.add("tag-off");
    span.textContent = value === "rupture" ? "En rupture" : value;
  }
  return span;
}

function initials(name) {
  var parts = name.split(" ").filter(function (p) { return p.length > 0; });
  var out = "";
  if (parts.length > 0) out += parts[0].charAt(0);
  if (parts.length > 1) out += parts[1].charAt(0);
  return out.toUpperCase();
}

function productThumb(p, className) {
  var wrap = el("div", className);
  if (p.image_url) {
    var img = document.createElement("img");
    img.src = p.image_url;
    img.alt = p.name;
    img.loading = "lazy";
    img.decoding = "async";
    img.onerror = function () {
      img.remove();
      wrap.appendChild(el("div", "pt-product-thumb-ph", initials(p.name)));
    };
    wrap.appendChild(img);
  } else {
    wrap.appendChild(el("div", "pt-product-thumb-ph", initials(p.name)));
  }
  return wrap;
}

function productCard(p) {
  var card = el("article", "pt-product-card");
  // Thumb cliquable pour ouvrir le produit
  var thumb = productThumb(p, "pt-product-thumb");
  thumb.style.cursor = "pointer";
  thumb.addEventListener("click", function () { openProduct(p.id); });
  card.appendChild(thumb);
  var body = el("div", "pt-product-body");

  // Nom cliquable
  var name = el("h3", "pt-product-name", p.name);
  name.style.cursor = "pointer";
  name.addEventListener("click", function () { openProduct(p.id); });
  body.appendChild(name);

  body.appendChild(el("p", "pt-product-pres", p.presentation));
  var row = el("div", "pt-product-row");
  row.appendChild(el("span", "pt-product-price", money(p.price)));
  row.appendChild(availabilityTag(p.availability));
  body.appendChild(row);

  // Actions
  var actions = el("div", "pt-product-actions");

  var btn = el("button", "pt-btn pt-btn-ghost", "Voir");
  btn.addEventListener("click", function () { openProduct(p.id); });
  actions.appendChild(btn);

  if (p.availability === "disponible") {
    // Qty selector inline
    var qtyWrap = el("div", "pt-qty");
    var btnMinus = el("button", "pt-qty-btn", "−");
    btnMinus.type = "button";
    btnMinus.setAttribute("aria-label", "Diminuer");
    var qtyInput = el("input", "pt-qty-input");
    qtyInput.type = "number";
    qtyInput.min = "1";
    qtyInput.max = "99";
    qtyInput.value = "1";
    qtyInput.setAttribute("inputmode", "numeric");
    var btnPlus = el("button", "pt-qty-btn", "+");
    btnPlus.type = "button";
    btnPlus.setAttribute("aria-label", "Augmenter");

    function getQty() {
      var n = parseInt(qtyInput.value, 10);
      if (isNaN(n) || n < 1) n = 1;
      if (n > 99) n = 99;
      qtyInput.value = String(n);
      return n;
    }
    btnMinus.addEventListener("click", function () {
      var n = getQty() - 1;
      if (n < 1) n = 1;
      qtyInput.value = String(n);
    });
    btnPlus.addEventListener("click", function () {
      var n = getQty() + 1;
      if (n > 99) n = 99;
      qtyInput.value = String(n);
    });
    qtyInput.addEventListener("blur", function () { getQty(); });
    qtyWrap.appendChild(btnMinus);
    qtyWrap.appendChild(qtyInput);
    qtyWrap.appendChild(btnPlus);

    var addBtn = el("button", "pt-btn pt-btn-primary", "Ajouter");
    addBtn.addEventListener("click", function () {
      addToCartQty(p.id, getQty(), addBtn, qtyInput);
    });

    // Ligne unique : qty + ajouter cote a cote
    var addRow = el("div", "pt-add-row");
    addRow.appendChild(qtyWrap);
    addRow.appendChild(addBtn);
    body.appendChild(addRow);
  }

  body.appendChild(actions);
  card.appendChild(body);
  return card;
}

function addToCart(productId, btn) {
  addToCartQty(productId, 1, btn, null);
}

function addToCartQty(productId, qty, btn, qtyInput) {
  qty = Math.max(1, parseInt(qty, 10) || 1);

  // ==== OPTIMISTIC UI : feedback instantane AVANT le POST ====
  var prevBadge = 0;
  var badge = document.getElementById("cart-badge");
  if (badge) prevBadge = parseInt(badge.textContent || "0", 10) || 0;

  // Incrementer le badge immediatement
  updateCartBadge(prevBadge + qty);

  if (btn) {
    btn.disabled = true;
    btn.dataset.orig = btn.dataset.orig || btn.textContent;
    btn.textContent = "\u2713 Ajoute";
    btn.style.background = "#0A7A5A";
    btn.style.borderColor = "#0A7A5A";
  }
  if (qtyInput) qtyInput.value = "1";

  // Reset visuel rapide (400ms au lieu de 1200ms)
  var resetTimer = setTimeout(function () {
    if (btn) {
      btn.disabled = false;
      btn.textContent = btn.dataset.orig || "Ajouter";
      btn.style.background = "";
      btn.style.borderColor = "";
    }
  }, 400);

  // ==== POST en arriere-plan ====
  fetch(API + "/cart/items", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_id: productId, quantity: qty })
  }).then(function (r) {
    if (r.status === 401) {
      // Revert
      updateCartBadge(prevBadge);
      window.location.href = "/connexion?next=/cart.html";
      return null;
    }
    return r.json().then(function (d) {
      if (!r.ok) throw new Error(d.detail || "Erreur");
      // Confirmer avec le vrai compte serveur
      updateCartBadge(d.item_count);
      // Force sync avec le serveur (au cas ou d'autres onglets ont change)
      if (window.PatientNav && window.PatientNav.refreshCartBadge) {
        setTimeout(function () { window.PatientNav.refreshCartBadge(); }, 200);
      }
      return d;
    });
  }).catch(function (e) {
    // Revert visuel + badge
    updateCartBadge(prevBadge);
    clearTimeout(resetTimer);
    if (btn) {
      btn.disabled = false;
      btn.textContent = btn.dataset.orig || "Ajouter";
      btn.style.background = "";
      btn.style.borderColor = "";
    }
    // Toast discret au lieu d'alert
    showCartError(e.message || "Erreur d'ajout");
  });
}

function showCartError(msg) {
  var t = document.createElement("div");
  t.style.cssText = "position:fixed;bottom:100px;left:50%;transform:translateX(-50%);" +
    "background:#B23C3C;color:#fff;padding:12px 20px;border-radius:10px;" +
    "font-size:13.5px;font-weight:700;z-index:99999;box-shadow:0 8px 24px rgba(178,60,60,.3);" +
    "font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:90vw";
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(function () {
    t.style.opacity = "0";
    t.style.transition = "opacity .3s";
    setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 300);
  }, 3000);
}

function updateCartBadge(count) {
  var b = document.getElementById("cart-badge");
  if (b) {
    if (count > 0) { b.textContent = count > 99 ? "99+" : String(count); b.classList.remove("hidden"); }
    else { b.classList.add("hidden"); }
  }
  // Header.js (pages pro/anciennes)
  if (window.EHHeader && window.EHHeader.updateCartBadge) {
    window.EHHeader.updateCartBadge(count);
  }
  // Navbar basse patient
  if (window.PatientNav && window.PatientNav.updateCartBadge) {
    window.PatientNav.updateCartBadge(count);
  }
}

function loadCartBadge() {
  fetch(API + "/cart").then(function (r) {
    if (r.status === 401) return null;
    if (!r.ok) return null;
    return r.json();
  }).then(function (d) {
    if (d) updateCartBadge(d.item_count || 0);
  }).catch(function () {});
}

function renderHomeCategories() {
  var box = $("#home-categories");
  if (!box) return;
  box.innerHTML = "";
  state.categories.forEach(function (cat) {
    var card = el("a", "pt-cat");
    card.href = "#catalogue";
    card.setAttribute("data-nav", "catalog");
    card.setAttribute("data-category", cat.name);
    card.appendChild(el("span", "pt-cat-name", cat.name));
    card.appendChild(el("span", "pt-cat-count", cat.total + " produit" + (cat.total > 1 ? "s" : "")));
    // Prefetch au survol
    card.addEventListener("mouseenter", function () { prefetchOnHover(cat.name); });
    card.addEventListener("touchstart", function () { prefetchOnHover(cat.name); }, { passive: true });
    box.appendChild(card);
  });
}

function renderCatalogFilters() {
  var box = $("#catalog-filters");
  if (!box) return;
  box.innerHTML = "";
  var all = el("button", "pt-cat-chip" + (state.category === "" ? " active" : ""), "Tous");
  all.addEventListener("click", function () { state.category = ""; renderCatalogFilters(); loadProducts(); });
  box.appendChild(all);
  state.categories.forEach(function (cat) {
    var active = state.category === cat.name ? " active" : "";
    var chip = el("button", "pt-cat-chip" + active, cat.name);
    chip.addEventListener("click", function () {
      state.category = cat.name;
      renderCatalogFilters();
      loadProducts();
    });
    box.appendChild(chip);
  });
}

function renderCatalog() {
  var grid = $("#catalog-grid");
  if (!grid) return;
  grid.innerHTML = "";
  var empty = $("#catalog-empty");
  var count = $("#catalog-count");
  if (state.products.length === 0) {
    if (empty) empty.classList.remove("hidden");
    if (count) count.textContent = "0 produit";
    return;
  }
  if (empty) empty.classList.add("hidden");
  if (count) count.textContent = state.products.length + " produit" + (state.products.length > 1 ? "s" : "");
  state.products.forEach(function (p) { grid.appendChild(productCard(p)); });
}

var PAGE_SIZE = 20;
var _allProducts = [];

function loadProducts() {
  var params = new URLSearchParams();
  var q = $("#catalog-search").value.trim();
  if (q) params.set("q", q);
  if (state.category) params.set("category", state.category);
  apiGet("/products?" + params.toString()).then(function (list) {
    _allProducts = list || [];
    // N'afficher que la premiere page
    state.products = _allProducts.slice(0, PAGE_SIZE);
    renderCatalog();
    renderLoadMore();
  }).catch(function () {
    _allProducts = [];
    state.products = [];
    renderCatalog();
    renderLoadMore();
  });
}

function renderLoadMore() {
  var grid = $("#catalog-grid");
  if (!grid) return;
  var existing = document.getElementById("pt-load-more");
  if (existing) existing.remove();
  if (_allProducts.length <= state.products.length) return;

  var wrap = document.createElement("div");
  wrap.id = "pt-load-more";
  wrap.style.cssText = "text-align:center;margin-top:24px";
  var btn = document.createElement("button");
  btn.className = "pt-btn pt-btn-ghost";
  btn.type = "button";
  btn.textContent = "Charger plus (" + (state.products.length) + "/" + _allProducts.length + ")";
  btn.style.padding = "12px 28px";
  btn.addEventListener("click", function () {
    var next = _allProducts.slice(state.products.length, state.products.length + PAGE_SIZE);
    state.products = state.products.concat(next);
    renderCatalog();
    renderLoadMore();
  });
  wrap.appendChild(btn);
  grid.parentNode.appendChild(wrap);
}

function loadCategories() {
  // Cache 5 min en localStorage
  var CACHE_KEY = "eh_cats_cache";
  var TTL = 5 * 60 * 1000;
  try {
    var raw = localStorage.getItem(CACHE_KEY);
    if (raw) {
      var obj = JSON.parse(raw);
      if (obj && obj._at && (Date.now() - obj._at) < TTL && Array.isArray(obj.list)) {
        state.categories = obj.list;
        renderHomeCategories();
        renderCatalogFilters();
        // Refresh en arriere-plan
        setTimeout(function () {
          apiGet("/categories").then(function (list) {
            state.categories = list;
            try {
              localStorage.setItem(CACHE_KEY, JSON.stringify({ list: list, _at: Date.now() }));
            } catch (e) {}
          }).catch(function () {});
        }, 2000);
        return Promise.resolve();
      }
    }
  } catch (e) {}

  return apiGet("/categories").then(function (list) {
    state.categories = list;
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify({ list: list, _at: Date.now() }));
    } catch (e) {}
    renderHomeCategories();
    renderCatalogFilters();
  }).catch(function () {
    state.categories = [];
    renderHomeCategories();
    renderCatalogFilters();
  });
}

function goCatalog(category) {
  state.category = category || "";
  showView("catalog");
  renderCatalogFilters();
  loadProducts();
}

function openProduct(id) {
  apiGet("/products/" + id).then(function (p) {
    state.product = p;
    renderProduct(p);
    showView("product");
  });
}

function renderProduct(p) {
  var box = $("#product-detail");
  if (!box) return;
  box.innerHTML = "";

  // Image
  var media = el("div", "pt-detail-media");
  media.appendChild(productThumb(p, "pt-detail-thumb"));
  box.appendChild(media);

  // Info
  var info = el("div", "pt-detail-info");
  info.appendChild(el("h1", "pt-detail-name", p.name));
  if (p.presentation) {
    info.appendChild(el("p", "pt-detail-pres", p.presentation));
  }

  // Prix + disponibilité
  var row = el("div", "pt-detail-row");
  row.appendChild(el("span", "pt-detail-price", money(p.price)));
  row.appendChild(availabilityTag(p.availability));
  info.appendChild(row);

  // Ordonnance nécessaire ?
  if (p.requires_prescription === 1) {
    info.appendChild(el("div", "pt-detail-alert",
      "Ce produit necessite une ordonnance. Vous pourrez la joindre a votre commande."));
  }

  // Description
  if (p.description) {
    info.appendChild(el("p", "pt-detail-desc", p.description));
  }

  // === Qty + Ajouter au panier ===
  if (p.availability === "disponible") {
    var addRow = el("div", "pt-detail-add-row");
    var qtyWrap = el("div", "pt-qty");
    var btnMinus = el("button", "pt-qty-btn", "\u2212");
    btnMinus.type = "button";
    btnMinus.setAttribute("aria-label", "Diminuer");
    var qtyInput = el("input", "pt-qty-input");
    qtyInput.type = "number";
    qtyInput.min = "1";
    qtyInput.max = "99";
    qtyInput.value = "1";
    qtyInput.setAttribute("inputmode", "numeric");
    var btnPlus = el("button", "pt-qty-btn", "+");
    btnPlus.type = "button";
    btnPlus.setAttribute("aria-label", "Augmenter");

    function getQty() {
      var n = parseInt(qtyInput.value, 10);
      if (isNaN(n) || n < 1) n = 1;
      if (n > 99) n = 99;
      qtyInput.value = String(n);
      return n;
    }
    btnMinus.addEventListener("click", function () {
      var n = getQty() - 1;
      if (n < 1) n = 1;
      qtyInput.value = String(n);
    });
    btnPlus.addEventListener("click", function () {
      var n = getQty() + 1;
      if (n > 99) n = 99;
      qtyInput.value = String(n);
    });
    qtyInput.addEventListener("blur", function () { getQty(); });

    qtyWrap.appendChild(btnMinus);
    qtyWrap.appendChild(qtyInput);
    qtyWrap.appendChild(btnPlus);
    addRow.appendChild(qtyWrap);

    var addBtn = el("button", "pt-btn pt-btn-primary pt-btn-lg", "Ajouter au panier");
    addBtn.addEventListener("click", function () {
      addToCartQty(p.id, getQty(), addBtn, qtyInput);
    });
    addRow.appendChild(addBtn);
    info.appendChild(addRow);
  }

  // === Actions secondaires ===
  var actions = el("div", "pt-detail-actions");
  var back = el("button", "pt-btn pt-btn-ghost", "\u2190 Retour au catalogue");
  back.addEventListener("click", function () { goCatalog(""); });
  actions.appendChild(back);
  info.appendChild(actions);

  box.appendChild(info);
}

function ensureProductOptions() {
  var select = $("#f-product");
  if (!select) return Promise.resolve();
  if (select.options.length > 0) return Promise.resolve();
  return apiGet("/products").then(function (list) {
    select.innerHTML = "";
    list.forEach(function (p) {
      var opt = document.createElement("option");
      opt.value = String(p.id);
      opt.textContent = p.name + " - " + money(p.price);
      select.appendChild(opt);
    });
  });
}

function goOrder(productId) {
  showView("order");
  ensureProductOptions().then(function () {
    if (productId) $("#f-product").value = String(productId);
  });
}

function showError(message) {
  var box = $("#form-error");
  if (!box) return;
  box.textContent = message;
  box.classList.remove("hidden");
}

function summaryRow(dl, label, value) {
  dl.appendChild(el("dt", null, label));
  dl.appendChild(el("dd", null, String(value)));
}

function renderConfirmation(o) {
  var box = $("#confirm-box");
  if (!box) return;
  box.innerHTML = "";
  box.appendChild(el("div", "confirm-icon", "OK"));
  box.appendChild(el("h1", null, "Demande envoyee"));
  box.appendChild(el("p", "muted", "Votre demande a ete transmise a la pharmacie. Elle doit etre verifiee puis confirmee par un pharmacien avant delivrance."));

  var ref = el("div", "ref-box");
  ref.appendChild(el("span", "muted small", "Numero de demande"));
  ref.appendChild(el("strong", null, o.reference));
  box.appendChild(ref);

  var dl = el("dl", "summary");
  summaryRow(dl, "Client", o.customer_name);
  summaryRow(dl, "Telephone", o.phone);

  var qty = Number(o.quantity) || 1;
  var price = Number(o.price) || 0;
  var subtotal = (o.subtotal !== undefined && o.subtotal !== null) ? Number(o.subtotal) : (price * qty);
  var fee = Number(o.delivery_fee) || 0;
  var total = (o.total !== undefined && o.total !== null) ? Number(o.total) : (subtotal + fee);

  summaryRow(dl, "Produit", o.product_name + " (x" + qty + ")");
  if (o.delivery_distance_km !== null && o.delivery_distance_km !== undefined) {
    summaryRow(dl, "Distance", Number(o.delivery_distance_km).toFixed(1) + " km");
  }
  summaryRow(dl, "Sous-total", money(subtotal));
  summaryRow(dl, "Livraison", money(fee));
  summaryRow(dl, "Total", money(total));
  summaryRow(dl, "Mode", o.delivery_mode === "livraison" ? "Livraison a domicile" : "Retrait en pharmacie");
  if (o.address) summaryRow(dl, "Adresse", o.address);
  summaryRow(dl, "Ordonnance", o.prescription_file ? "Jointe" : "Non jointe");
  summaryRow(dl, "Statut", "En attente de confirmation");
  box.appendChild(dl);

  var actions = el("div", "confirm-actions");
  var bTrack = el("a", "btn btn-primary", "Suivre ma commande");
  bTrack.href = "/suivi?ref=" + encodeURIComponent(o.reference);
  var b1 = el("button", "btn btn-ghost", "Retour au catalogue");
  b1.addEventListener("click", function () { goCatalog(""); });
  var b2 = el("button", "btn btn-ghost", "Nouvelle demande");
  b2.addEventListener("click", function () { goOrder(null); });
  actions.appendChild(bTrack);
  actions.appendChild(b1);
  actions.appendChild(b2);
  box.appendChild(actions);
}

function submitOrder(ev) {
  ev.preventDefault();
  $("#form-error").classList.add("hidden");
  var form = $("#order-form");
  var data = new FormData(form);
  var mode = String(data.get("delivery_mode") || "retrait");
  var address = String(data.get("address") || "").trim();

  var latVal = data.get("latitude");
  var lonVal = data.get("longitude");
  var hasGps = latVal && lonVal && String(latVal).length > 0 && String(lonVal).length > 0;

  if (mode === "livraison" && address === "" && !hasGps) {
    showError("Merci d'utiliser votre localisation GPS ou d'indiquer une adresse pour la livraison.");
    return;
  }

  ["latitude", "longitude", "location_accuracy"].forEach(function (k) {
    var v = data.get(k);
    if (v === null || v === "" || v === undefined) data.delete(k);
  });

  var btn = $("#submit-btn");
  btn.disabled = true;
  btn.textContent = "Envoi en cours...";

  fetch(API + "/orders", { method: "POST", body: data })
    .then(function (r) {
      return r.json().then(function (body) {
        if (!r.ok) {
          var msg = typeof body.detail === "string" ? body.detail : "Envoi impossible";
          throw new Error(msg);
        }
        return body;
      });
    })
    .then(function (order) {
      state.order = order;
      renderConfirmation(order);
      showView("confirm");
      form.reset();
      $("#address-row").classList.add("hidden");
      var addrBlock = document.getElementById("geo-address-block");
      if (addrBlock) addrBlock.classList.add("hidden");
      var geoStatus = document.getElementById("geo-status");
      if (geoStatus) {
        geoStatus.classList.add("hidden");
        geoStatus.innerHTML = "";
      }
      var geoBtn = document.getElementById("geo-btn");
      if (geoBtn) {
        geoBtn.innerHTML = '<span class="geo-icon">\u{1F4CD}</span> Utiliser ma localisation actuelle';
        geoBtn.disabled = false;
      }
    })
    .catch(function (err) {
      showError(err.message || "Une erreur est survenue.");
    })
    .then(function () {
      btn.disabled = false;
      btn.textContent = "Envoyer la demande";
    });
}

// ====== GEOLOCALISATION & FRAIS ======

function initGeolocation() {
  var btn = document.getElementById("geo-btn");
  var status = document.getElementById("geo-status");
  var latInput = document.getElementById("f-latitude");
  var lonInput = document.getElementById("f-longitude");
  var accInput = document.getElementById("f-location-accuracy");
  if (!btn || !status || !latInput || !lonInput || !accInput) return;

  function setStatus(htmlMsg, cls) {
    status.className = "geo-status" + (cls ? " " + cls : "");
    status.innerHTML = htmlMsg;
    status.classList.remove("hidden");
  }
  function clearStatus() {
    status.classList.add("hidden");
    status.innerHTML = "";
  }
  function reset() {
    latInput.value = "";
    lonInput.value = "";
    accInput.value = "";
    clearStatus();
    btn.innerHTML = '<span class="geo-icon">\u{1F4CD}</span> Utiliser ma localisation actuelle';
    btn.disabled = false;
  }

  btn.addEventListener("click", function () {
    if (!navigator.geolocation) {
      setStatus("La geolocalisation n'est pas disponible sur ce navigateur. Vous pouvez continuer avec votre adresse.", "geo-error");
      return;
    }
    btn.disabled = true;
    btn.innerHTML = '<span class="geo-icon">\u23F3</span> Localisation en cours...';
    setStatus("Recuperation de votre position...", "geo-loading");

    var done = false;

    function onSuccess(pos) {
      if (done) return;
      done = true;
      var lat = pos.coords.latitude;
      var lon = pos.coords.longitude;
      var acc = pos.coords.accuracy;
      latInput.value = String(lat);
      lonInput.value = String(lon);
      accInput.value = String(acc);
      setStatus("&#10003; Localisation enregistree<br><span class='geo-coords'>" +
                lat.toFixed(5) + ", " + lon.toFixed(5) +
                " (&#177; " + Math.round(acc) + " m)</span>", "geo-success");
      btn.disabled = false;
      btn.innerHTML = '<span class="geo-icon">\u{1F4CD}</span> Actualiser ma localisation';
      if (typeof updateDeliveryFeeDisplay === "function") updateDeliveryFeeDisplay();
    }

    function onFinalError(err) {
      if (done) return;
      done = true;
      var msg = "Localisation indisponible.";
      if (err && err.code === 1) msg = "Vous avez refuse la localisation. Vous pouvez continuer avec votre adresse.";
      else if (err && err.code === 2) msg = "Position introuvable. Verifiez que le GPS ou la localisation est active sur votre appareil, puis reessayez.";
      else if (err && err.code === 3) msg = "La localisation met trop de temps. Essayez a l'exterieur, activez le GPS, ou continuez avec votre adresse.";
      setStatus(msg + "<br><span class='geo-coords'>Vous pouvez reessayer ou simplement remplir votre adresse.</span>", "geo-error");
      btn.disabled = false;
      btn.innerHTML = '<span class="geo-icon">\u{1F4CD}</span> Reessayer la localisation';
    }

    navigator.geolocation.getCurrentPosition(
      onSuccess,
      function (err1) {
        if (err1 && err1.code === 1) { onFinalError(err1); return; }
        setStatus("Position precise introuvable, tentative en mode standard...", "geo-loading");
        navigator.geolocation.getCurrentPosition(
          onSuccess,
          onFinalError,
          { enableHighAccuracy: false, timeout: 30000, maximumAge: 300000 }
        );
      },
      { enableHighAccuracy: true, timeout: 20000, maximumAge: 60000 }
    );
  });

  var radios = document.querySelectorAll("input[name=delivery_mode]");
  Array.prototype.forEach.call(radios, function (r) {
    r.addEventListener("change", function () {
      if (r.value === "retrait" && r.checked) reset();
    });
  });
}

function loadSettings() {
  return fetch(API + "/settings").then(function (r) {
    if (!r.ok) throw new Error("settings");
    return r.json();
  }).then(function (s) {
    pharmacySettings = s || { delivery_fee_default: 0 };
    return pharmacySettings;
  }).catch(function () {
    pharmacySettings = { delivery_fee_default: 0 };
    return pharmacySettings;
  });
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

function updateDeliveryFeeDisplay() {
  var box = document.getElementById("delivery-fee-info");
  if (!box) return;
  var checked = document.querySelector("input[name=delivery_mode]:checked");
  var isDelivery = checked && checked.value === "livraison";
  if (!isDelivery) {
    box.classList.add("hidden");
    box.innerHTML = "";
    return;
  }

  var s = pharmacySettings || {};
  var fallback = Math.round(Number(s.delivery_fee_default) || 0);
  var phLat = s.pharmacy_latitude;
  var phLon = s.pharmacy_longitude;
  var base = Number(s.delivery_base_fee);
  var perKm = Number(s.delivery_price_per_km);

  var latEl = document.getElementById("f-latitude");
  var lonEl = document.getElementById("f-longitude");
  var clientLat = latEl && latEl.value ? Number(latEl.value) : null;
  var clientLon = lonEl && lonEl.value ? Number(lonEl.value) : null;

  if (phLat === null || phLat === undefined || phLon === null || phLon === undefined || isNaN(phLat) || isNaN(phLon)) {
    box.innerHTML = "&#128666; Frais de livraison : <strong>" + fallback.toLocaleString("fr-FR") + " FCFA</strong>"
      + "<br><span class='muted small'>Position pharmacie non configuree.</span>";
    box.classList.remove("hidden");
    return;
  }

  if (clientLat === null || clientLon === null || isNaN(clientLat) || isNaN(clientLon)) {
    box.innerHTML = "&#128666; Frais de livraison estim&#233;s : <strong>" + fallback.toLocaleString("fr-FR") + " FCFA</strong>"
      + "<br><span class='muted small'>Activez la localisation pour un tarif bas&#233; sur la distance.</span>";
    box.classList.remove("hidden");
    return;
  }

  var dist = haversineKm(phLat, phLon, clientLat, clientLon);
  var b = isNaN(base) ? 300 : base;
  var p = isNaN(perKm) ? 100 : perKm;
  var fee = b + dist * p;
  fee = Math.round(fee / 50) * 50;

  box.innerHTML = "&#128666; Distance estim&#233;e : <strong>" + dist.toFixed(1) + " km</strong>"
    + "<br>&#128181; Frais de livraison : <strong>" + fee.toLocaleString("fr-FR") + " FCFA</strong>"
    + "<br><span class='muted small'>Distance &#224; vol d'oiseau, tarif indicatif. La pharmacie confirme.</span>";
  box.classList.remove("hidden");
}

function initDeliveryFeeDisplay() {
  var radios = document.querySelectorAll("input[name=delivery_mode]");
  Array.prototype.forEach.call(radios, function (r) {
    r.addEventListener("change", updateDeliveryFeeDisplay);
  });
  loadSettings().then(updateDeliveryFeeDisplay);
}

// ====== SUGGESTIONS ======

function attachSuggestions(input, box) {
  var items = [];
  var activeIndex = -1;
  var timer = null;
  var requestId = 0;

  function close() {
    box.classList.add("hidden");
    box.innerHTML = "";
    activeIndex = -1;
    items = [];
  }

  function highlight(idx) {
    var nodes = box.querySelectorAll(".sugg-item");
    Array.prototype.forEach.call(nodes, function (n, i) {
      if (i === idx) n.classList.add("active");
      else n.classList.remove("active");
    });
  }

  function choose(p) {
    close();
    input.value = p.name;
    openProduct(p.id);
  }

  function render(list) {
    box.innerHTML = "";
    items = list;
    activeIndex = -1;
    if (list.length === 0) {
      box.appendChild(el("div", "sugg-empty", "Aucun produit trouve"));
      box.classList.remove("hidden");
      return;
    }
    list.forEach(function (p) {
      var item = el("div", "sugg-item");
      var thumb = el("div", "sugg-thumb");
      if (p.image_url) {
        var img = document.createElement("img");
        img.src = p.image_url;
        img.alt = p.name;
        img.loading = "lazy";
        img.onerror = function () {
          img.remove();
          thumb.textContent = initials(p.name);
        };
        thumb.appendChild(img);
      } else {
        thumb.textContent = initials(p.name);
      }
      var info = el("div", "sugg-info");
      info.appendChild(el("div", "sugg-name", p.name));
      info.appendChild(el("div", "sugg-meta", p.category + " - " + p.presentation));
      var price = el("div", "sugg-price", money(p.price));
      item.appendChild(thumb);
      item.appendChild(info);
      item.appendChild(price);
      item.addEventListener("mousedown", function (ev) {
        ev.preventDefault();
        choose(p);
      });
      box.appendChild(item);
    });
    box.classList.remove("hidden");
  }

  input.addEventListener("input", function () {
    var q = input.value.trim();
    if (q.length === 0) { close(); return; }
    if (timer) clearTimeout(timer);
    var myReq = ++requestId;
    timer = setTimeout(function () {
      apiGet("/products?q=" + encodeURIComponent(q)).then(function (list) {
        if (myReq !== requestId) return;
        if (input.value.trim() !== q) return;
        render(list.slice(0, 6));
      }).catch(function () {
        if (myReq !== requestId) return;
        close();
      });
    }, 120);
  });

  input.addEventListener("keydown", function (ev) {
    if (box.classList.contains("hidden") || items.length === 0) return;
    if (ev.key === "ArrowDown") {
      ev.preventDefault();
      activeIndex = (activeIndex + 1) % items.length;
      highlight(activeIndex);
    } else if (ev.key === "ArrowUp") {
      ev.preventDefault();
      activeIndex = activeIndex <= 0 ? items.length - 1 : activeIndex - 1;
      highlight(activeIndex);
    } else if (ev.key === "Enter") {
      if (activeIndex >= 0 && items[activeIndex]) {
        ev.preventDefault();
        choose(items[activeIndex]);
      }
    } else if (ev.key === "Escape") {
      close();
    }
  });

  input.addEventListener("blur", function () { setTimeout(close, 150); });

  input.addEventListener("focus", function () {
    if (input.value.trim().length >= 1 && items.length > 0) {
      box.classList.remove("hidden");
    }
  });
}

function init() {
  document.addEventListener("click", function (ev) {
    var node = ev.target.closest ? ev.target.closest("[data-nav]") : null;
    if (!node) return;
    ev.preventDefault();
    var nav = node.getAttribute("data-nav");
    if (nav === "home") {
      showView("home");
      try { history.replaceState(null, "", "/"); } catch (e) {}
    } else if (nav === "catalog") {
      goCatalog(node.getAttribute("data-category") || "");
      try { history.replaceState(null, "", "/?nav=catalog"); } catch (e) {}
    } else if (nav === "order") {
      goOrder(null);
      try { history.replaceState(null, "", "/?nav=order"); } catch (e) {}
    }
  });

  $("#home-search").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var q = $("#home-search-input").value.trim();
    showView("catalog");
    $("#catalog-search").value = q;
    state.category = "";
    renderCatalogFilters();
    loadProducts();
  });

  $("#catalog-search").addEventListener("input", function () { loadProducts(); });
  $("#order-form").addEventListener("submit", submitOrder);

  var homeSugg = document.getElementById("home-suggestions");
  var catSugg = document.getElementById("catalog-suggestions");
  if (homeSugg) attachSuggestions($("#home-search-input"), homeSugg);
  if (catSugg) attachSuggestions($("#catalog-search"), catSugg);

  initGeolocation();
  initDeliveryFeeDisplay();

  var radios = document.querySelectorAll("input[name=delivery_mode]");
  Array.prototype.forEach.call(radios, function (r) {
    r.addEventListener("change", function () {
      var row = $("#address-row");
      if (r.value === "livraison" && r.checked) row.classList.remove("hidden");
      else if (r.value === "retrait" && r.checked) row.classList.add("hidden");
    });
  });



/* ============================================================
   Accueil : afficher les 3 dernieres notifications
   ============================================================ */
function loadHomeNotifs() {
  var section = document.getElementById("pt-home-notifs");
  var box = document.getElementById("pt-home-notifs-list");
  if (!section || !box) return;

  fetch("/api/notifications?unread_only=0", { credentials: "same-origin" })
    .then(function (r) { return r.ok ? r.json() : []; })
    .then(function (list) {
      list = Array.isArray(list) ? list : [];
      // Trier par id desc (les plus recentes)
      list.sort(function (a, b) { return (b.id || 0) - (a.id || 0); });
      var top = list.slice(0, 3);

      if (top.length === 0) {
        box.innerHTML = '<div class="pt-notif-empty">Aucune notification pour le moment.</div>';
        section.classList.remove("hidden");
        return;
      }

      box.innerHTML = "";
      top.forEach(function (n) {
        var a = document.createElement("a");
        a.className = "pt-notif" + (n.is_read ? "" : " unread");
        a.href = (n.order_reference || n.order_id) ? ("/suivi?ref=" + encodeURIComponent(n.order_reference || n.order_id)) : "/notifications.html";

        var ico = document.createElement("span");
        ico.className = "pt-notif-ico";
        ico.innerHTML = "&#128276;";

        var body = document.createElement("div");
        body.className = "pt-notif-body";
        var title = document.createElement("div");
        title.className = "pt-notif-title";
        title.textContent = n.title || "Notification";
        var msg = document.createElement("div");
        msg.className = "pt-notif-msg";
        msg.textContent = n.body || "";
        var time = document.createElement("div");
        time.className = "pt-notif-time";
        time.textContent = fmtRelative(n.created_at);
        body.appendChild(title);
        body.appendChild(msg);
        body.appendChild(time);

        a.appendChild(ico);
        a.appendChild(body);

        if (!n.is_read) {
          var dot = document.createElement("span");
          dot.className = "pt-notif-dot";
          a.appendChild(dot);
        }
        box.appendChild(a);
      });

      section.classList.remove("hidden");
    })
    .catch(function () {
      section.classList.add("hidden");
    });
}

function fmtRelative(iso) {
  if (!iso) return "";
  try {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    var diff = Math.floor((Date.now() - d.getTime()) / 1000);
    if (diff < 60) return "A l'instant";
    if (diff < 3600) return "Il y a " + Math.floor(diff / 60) + " min";
    if (diff < 86400) return "Il y a " + Math.floor(diff / 3600) + " h";
    if (diff < 604800) return "Il y a " + Math.floor(diff / 86400) + " j";
    var day = d.getDate();
    var m = ["janv.","fevr.","mars","avr.","mai","juin","juil.","aout","sept.","oct.","nov.","dec."][d.getMonth()];
    return day + " " + m;
  } catch (e) { return ""; }
}

// Recharger quand une notif SSE arrive
document.addEventListener("eh:refresh", function () {
  try { loadHomeNotifs(); } catch (e) {}
});

  // Charger en parallele : panier + categories
  var pCart = loadCartBadge();
  var pCats = loadCategories();

  loadHomeNotifs();
  Promise.all([pCart, pCats]).then(function () {
    try {
      var params = new URLSearchParams(window.location.search);
      var nav = params.get("nav");
      if (nav === "catalog") {
        state.category = "";
        showView("catalog");
        renderCatalogFilters();
        loadProducts();
        return;
      }
    } catch (e) {}
    showView("home");
  });

  // ---- Dashboard patient : greeting + actions rapides ----
  (function () {
    fetch("/api/auth/me", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (u) {
        var greeting = document.getElementById("pt-greeting");
        var sub = document.getElementById("pt-subtitle");
        var quick = document.getElementById("pt-quick");
        var pub = document.getElementById("pt-public-cta");

        if (u && u.role === "PATIENT") {
          if (greeting) {
            var first = String(u.full_name || "").trim().split(" ")[0] || "";
            greeting.textContent = "Bonjour" + (first ? " " + first : "") + " 👋";
          }
          if (sub) sub.textContent = "Que cherchez-vous aujourd'hui ?";
          if (quick) quick.classList.remove("hidden");
          if (pub) pub.classList.add("hidden");
          // Charger infos panier + commandes
          fetch("/api/cart", { credentials: "same-origin" })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (d) {
              var el = document.getElementById("pt-cart-info");
              if (!el) return;
              var n = (d && d.item_count) || 0;
              el.textContent = n === 0 ? "Aucun article" :
                n === 1 ? "1 article" : n + " articles";
            })
            .catch(function () {});
          fetch("/api/orders/mine", { credentials: "same-origin" })
            .then(function (r) { return r.ok ? r.json() : []; })
            .then(function (list) {
              var el = document.getElementById("pt-orders-info");
              if (!el) return;
              var n = Array.isArray(list) ? list.length : 0;
              var active = (list || []).filter(function (o) {
                return ["confirmee","en_preparation","prete","en_livraison"].indexOf(o.status) >= 0;
              }).length;
              if (n === 0) el.textContent = "Aucune commande";
              else if (active > 0) el.textContent = active + " en cours sur " + n;
              else el.textContent = n + " au total";
            })
            .catch(function () {});
        } else {
          if (sub) sub.textContent = "Trouvez vos produits de sante en quelques clics.";
          if (quick) quick.classList.add("hidden");
          if (pub) pub.classList.remove("hidden");
        }
        // Indiquer que l'auth est resolue -> reveler les blocs
        try { document.documentElement.classList.add("pt-auth-ready"); } catch (e) {}
      })
      .catch(function () {
        try { document.documentElement.classList.add("pt-auth-ready"); } catch (e) {}
      });
  })();
}



/* ============================================================
   Prefetch au hover : precharge les produits d'une categorie
   ============================================================ */
function prefetchOnHover(catName) {
  if (!catName) return;
  var key = "eh_prefetch_" + catName;
  var cache = window.__eh_prefetched = window.__eh_prefetched || {};
  if (cache[key]) return;
  cache[key] = true;
  try {
    fetch("/api/products?category=" + encodeURIComponent(catName), {
      credentials: "same-origin"
    }).catch(function () {});
  } catch (e) {}
}

/* Prefetch des images produit (petit hint navigateur) */
function prefetchImage(url) {
  if (!url) return;
  try {
    var i = new Image();
    i.src = url;
  } catch (e) {}
}

document.addEventListener("DOMContentLoaded", init);


// ====== Boutons pro sur l'accueil ======
(function () {
  var state = { whatsapp: "", structure: "", pharmacy: "Elonikab Health", user: null };

  function $(id) { return document.getElementById(id); }

  function showProButtons(user) {
    var box = $("pro-quick-actions");
    if (!box) return;
    if (user && user.role === "PROFESSIONNEL") {
      box.classList.remove("hidden");
    } else {
      box.classList.add("hidden");
    }
  }

  function loadInfo() {
    return fetch("/api/pro/whatsapp-info", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) return;
        state.whatsapp = d.whatsapp_number || "";
        state.structure = d.structure_name || "";
        state.pharmacy = d.pharmacy_name || "Elonikab Health";
        var info = $("home-wa-info");
        if (info) {
          if (state.whatsapp) {
            info.textContent = "Destinataire WhatsApp : " + state.whatsapp;
          } else {
            info.textContent = "Numero WhatsApp non configure. Contactez la pharmacie.";
          }
        }
      });
  }

  function buildDefaultList() {
    return [
      "Bonjour " + state.pharmacy + " \uD83D\uDC4B",
      "",
      "Nous souhaitons passer une commande pour notre structure.",
      "",
      "\uD83C\uDFE5 Structure : " + (state.structure || "................"),
      "",
      "\uD83D\uDCCB Liste :",
      "- ................... (quantite)",
      "- ................... (quantite)",
      "- ................... (quantite)",
      "",
      "Merci de nous confirmer la disponibilite, les prix et le delai de livraison."
    ].join("\n");
  }

  function openWa() {
    var ta = $("home-wa-text");
    if (ta && !ta.value) ta.value = buildDefaultList();
    var m = $("home-wa-modal");
    if (m) { m.classList.remove("hidden"); document.body.style.overflow = "hidden"; }
    loadInfo();
  }
  function closeWa() {
    var m = $("home-wa-modal");
    if (m) { m.classList.add("hidden"); document.body.style.overflow = ""; }
  }
  function sendWa() {
    if (!state.whatsapp) {
      alert("La pharmacie n'a pas encore configure son numero WhatsApp.");
      return;
    }
    var phone = String(state.whatsapp).replace(/\D/g, "");
    if (!phone) { alert("Numero WhatsApp invalide"); return; }
    var msg = ($("home-wa-text") || {}).value || "";
    window.open("https://wa.me/" + phone + "?text=" + encodeURIComponent(msg), "_blank");
    closeWa();
  }

  function reorder() {
    var btn = $("home-reorder-btn");
    if (!btn) return;
    var orig = btn.querySelector(".pro-quick-text strong");
    var oldTxt = orig ? orig.textContent : "";
    btn.disabled = true;
    if (orig) orig.textContent = "Recherche...";

    fetch("/api/orders/mine", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (list) {
        if (!list || list.length === 0) {
          alert("Aucune commande precedente.");
          btn.disabled = false;
          if (orig) orig.textContent = oldTxt;
          return;
        }
        var ref = list[0].reference;
        return fetch("/api/orders/" + encodeURIComponent(ref) + "/reorder", {
          method: "POST", credentials: "same-origin"
        }).then(function (r) {
          return r.json().then(function (d) {
            if (!r.ok) throw new Error(d.detail || "Erreur");
            return d;
          });
        }).then(function (d) {
          alert(d.added + " produit(s) ajoute(s) au panier." +
                (d.skipped > 0 ? " " + d.skipped + " indisponible(s)." : ""));
          window.location.href = "/static/cart.html";
        });
      })
      .catch(function (e) {
        alert(e.message || "Erreur");
        btn.disabled = false;
        if (orig) orig.textContent = oldTxt;
      });
  }

  function init() {
    // Detecter le role via /api/auth/me (utilise le cache header.js si dispo)
    fetch("/api/auth/me", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (user) {
        state.user = user;
        showProButtons(user);
      })
      .catch(function () { showProButtons(null); });

    var waBtn = $("home-wa-btn");
    if (waBtn) waBtn.addEventListener("click", openWa);
    var rdBtn = $("home-reorder-btn");
    if (rdBtn) rdBtn.addEventListener("click", reorder);

    var closes = document.querySelectorAll("[data-close-home-wa]");
    Array.prototype.forEach.call(closes, function (b) {
      b.addEventListener("click", closeWa);
    });
    var sendBtn = $("home-wa-send");
    if (sendBtn) sendBtn.addEventListener("click", sendWa);

    // Reagir au login/logout : ecoute les changements de page
    window.addEventListener("focus", function () {
      fetch("/api/auth/me", { credentials: "same-origin" })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(showProButtons)
        .catch(function () { showProButtons(null); });
    });
  }

  document.addEventListener("DOMContentLoaded", init);
})();


// ===== Footer dynamique (telephone + WhatsApp) =====
(function () {
  function hydrateFooter() {
    fetch("/api/settings", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (s) {
        if (!s) return;
        var phone = s.pharmacy_phone || s.whatsapp_number || "";
        var wa = s.whatsapp_number || s.pharmacy_phone || "";
        var addr = s.pharmacy_address || "";
        var phoneEl = document.getElementById("footer-phone");
        if (phoneEl && phone) phoneEl.textContent = phone;
        var waEl = document.getElementById("footer-whatsapp");
        if (waEl && wa) {
          var num = String(wa).replace(/\D/g, "");
          waEl.innerHTML = '<a href="https://wa.me/' + num + '" target="_blank" rel="noopener">WhatsApp : ' + wa + '</a>';
        }
        var addrEl = document.getElementById("footer-address");
        if (addrEl && addr) addrEl.textContent = addr;
      })
      .catch(function () {});
  }
  document.addEventListener("DOMContentLoaded", hydrateFooter);
})();
