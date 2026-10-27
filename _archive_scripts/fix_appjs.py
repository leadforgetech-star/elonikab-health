from pathlib import Path

BASE = Path(__file__).resolve().parent
APPJS = BASE / "static" / "app.js"

js = r'''var API = "/api";
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
    img.onerror = function () {
      img.remove();
      wrap.appendChild(el("div", "thumb-placeholder", initials(p.name)));
    };
    wrap.appendChild(img);
  } else {
    wrap.appendChild(el("div", "thumb-placeholder", initials(p.name)));
  }
  return wrap;
}

function productCard(p) {
  var card = el("article", "product-card");
  card.appendChild(productThumb(p, "thumb"));
  var body = el("div", "product-body");
  body.appendChild(el("h3", "product-name", p.name));
  body.appendChild(el("p", "muted small", p.presentation));
  var row = el("div", "product-row");
  row.appendChild(el("span", "price", money(p.price)));
  row.appendChild(availabilityTag(p.availability));
  body.appendChild(row);
  var btn = el("button", "btn btn-primary btn-block", "Voir le produit");
  btn.addEventListener("click", function () { openProduct(p.id); });
  body.appendChild(btn);
  card.appendChild(body);
  return card;
}

function renderHomeCategories() {
  var box = $("#home-categories");
  if (!box) return;
  box.innerHTML = "";
  state.categories.forEach(function (cat) {
    var card = el("a", "category-card");
    card.href = "#catalogue";
    card.setAttribute("data-nav", "catalog");
    card.setAttribute("data-category", cat.name);
    card.appendChild(el("h3", null, cat.name));
    card.appendChild(el("p", "muted small", cat.total + " produit" + (cat.total > 1 ? "s" : "")));
    box.appendChild(card);
  });
}

function renderCatalogFilters() {
  var box = $("#catalog-filters");
  if (!box) return;
  box.innerHTML = "";
  var all = el("button", "chip" + (state.category === "" ? " chip-active" : ""), "Tous");
  all.addEventListener("click", function () { state.category = ""; renderCatalogFilters(); loadProducts(); });
  box.appendChild(all);
  state.categories.forEach(function (cat) {
    var active = state.category === cat.name ? " chip-active" : "";
    var chip = el("button", "chip" + active, cat.name);
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

function loadProducts() {
  var params = new URLSearchParams();
  var q = $("#catalog-search").value.trim();
  if (q) params.set("q", q);
  if (state.category) params.set("category", state.category);
  apiGet("/products?" + params.toString()).then(function (list) {
    state.products = list;
    renderCatalog();
  }).catch(function () {
    state.products = [];
    renderCatalog();
  });
}

function loadCategories() {
  return apiGet("/categories").then(function (list) {
    state.categories = list;
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
  var media = el("div", "detail-media");
  media.appendChild(productThumb(p, "detail-thumb"));
  var info = el("div", "detail-info");
  info.appendChild(el("h1", null, p.name));
  info.appendChild(el("p", "muted", p.presentation));
  var row = el("div", "product-row");
  row.appendChild(el("span", "price big", money(p.price)));
  row.appendChild(availabilityTag(p.availability));
  info.appendChild(row);
  if (p.requires_prescription === 1) {
    info.appendChild(el("div", "alert alert-info", "Ce produit necessite une ordonnance. Vous pourrez la joindre a votre demande."));
  }
  info.appendChild(el("p", "description", p.description));
  var btn = el("button", "btn btn-primary btn-lg", "Faire une demande");
  btn.addEventListener("click", function () { goOrder(p.id); });
  info.appendChild(btn);
  box.appendChild(media);
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
  var b1 = el("button", "btn btn-primary", "Retour au catalogue");
  b1.addEventListener("click", function () { goCatalog(""); });
  var b2 = el("button", "btn btn-ghost", "Nouvelle demande");
  b2.addEventListener("click", function () { goOrder(null); });
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
    if (nav === "home") showView("home");
    else if (nav === "catalog") goCatalog(node.getAttribute("data-category") || "");
    else if (nav === "order") goOrder(null);
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

  loadCategories().then(function () { showView("home"); });
}

document.addEventListener("DOMContentLoaded", init);
'''

APPJS.write_text(js, encoding="utf-8")
print("[OK] app.js reecrit entierement (", len(js), "caracteres )")