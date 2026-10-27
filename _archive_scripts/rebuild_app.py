from pathlib import Path

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

js = r'''var API = "/api";

var state = {
  categories: [],
  products: [],
  product: null,
  category: "",
  order: null
};

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
  grid.innerHTML = "";
  var empty = $("#catalog-empty");
  if (state.products.length === 0) {
    empty.classList.remove("hidden");
    $("#catalog-count").textContent = "0 produit";
    return;
  }
  empty.classList.add("hidden");
  $("#catalog-count").textContent = state.products.length + " produit" + (state.products.length > 1 ? "s" : "");
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
  box.textContent = message;
  box.classList.remove("hidden");
}

function submitOrder(ev) {
  ev.preventDefault();
  $("#form-error").classList.add("hidden");
  var form = $("#order-form");
  var data = new FormData(form);
  var mode = String(data.get("delivery_mode") || "retrait");
  var address = String(data.get("address") || "").trim();
  if (mode === "livraison" && address === "") {
    showError("Merci d'indiquer une adresse pour la livraison.");
    return;
  }
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
    })
    .catch(function (err) {
      showError(err.message || "Une erreur est survenue.");
    })
    .then(function () {
      btn.disabled = false;
      btn.textContent = "Envoyer la demande";
    });
}

function summaryRow(dl, label, value) {
  dl.appendChild(el("dt", null, label));
  dl.appendChild(el("dd", null, String(value)));
}

function renderConfirmation(o) {
  var box = $("#confirm-box");
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
  summaryRow(dl, "Produit", o.product_name);
  summaryRow(dl, "Quantite", o.quantity);
  summaryRow(dl, "Mode", o.delivery_mode === "livraison" ? "Livraison a domicile" : "Retrait en pharmacie");
  if (o.address) summaryRow(dl, "Adresse", o.address);
  summaryRow(dl, "Total estime", money(o.total));
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

function attachSuggestions(input, box) {
  var items = [];
  var activeIndex = -1;
  var lastQuery = "__init__";
  var timer = null;

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
    lastQuery = p.name;
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
    if (q === lastQuery) return;
    lastQuery = q;
    if (q.length < 1) { close(); return; }
    if (timer) clearTimeout(timer);
    timer = setTimeout(function () {
      apiGet("/products?q=" + encodeURIComponent(q)).then(function (list) {
        if (input.value.trim() !== q) return;
        render(list.slice(0, 6));
      }).catch(function () { close(); });
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

  input.addEventListener("blur", function () {
    setTimeout(close, 150);
  });

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

target = STATIC / "app.js"
target.write_text(js, encoding="utf-8")

size = target.stat().st_size
print("[OK] static/app.js regenere :", size, "octets")

# Verification rapide : aucun '%%' ne doit subsister
content = target.read_text(encoding="utf-8")
if "%%" in content:
    print("[!] ATTENTION : un '%%' subsiste dans app.js")
else:
    print("[OK] aucun '%%' parasite")

# Verifier que les ancres existent dans index.html
html = (STATIC / "index.html").read_text(encoding="utf-8")
for anchor in ("home-suggestions", "catalog-suggestions", "home-search-input", "catalog-search"):
    if anchor in html:
        print("[OK] index.html contient :", anchor)
    else:
        print("[!] MANQUE dans index.html :", anchor)

css = (STATIC / "style.css").read_text(encoding="utf-8")
if "Suggestions de recherche" in css:
    print("[OK] style.css contient les styles suggestions")
else:
    print("[!] style.css ne contient PAS les styles suggestions")

print()
print("Termine. Fais Ctrl+Shift+R dans le navigateur (pas besoin de redemarrer le serveur).")