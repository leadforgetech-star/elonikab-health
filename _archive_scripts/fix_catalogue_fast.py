"""
fix_catalogue_fast.py
Optimise l'ajout au panier depuis le catalogue :
- Charge le draft reference UNE FOIS au demarrage
- UI optimiste (compteur +1 immediat, POST en arriere-plan)
- Pas de rechargement apres chaque ajout
- Queue sequentielle pour eviter les doublons
"""
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
CATJS = STATIC / "professional_catalogue.js"

shutil.copy2(CATJS, CATJS.with_suffix(".js.bak6"))
print("[OK] Backup ->", CATJS.with_suffix(".js.bak6").name)

NEW_JS = r'''/* Elokinab Health - Catalogue B2B (V9 - optimise) */
(function () {
  "use strict";
  var API = "/api";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  var state = {
    products: [],
    filtered: [],
    categories: [],
    draftRef: null,          // reference du draft, charge une fois
    draftItemsCount: 0,
    queue: [],               // queue d'ajouts pending
    inFlight: false,
    query: "",
    categoryFilter: "",
    availFilter: "",
    loading: false
  };

  function escapeHtml(s) {
    try {
      return String(s == null ? "" : s)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    } catch (e) { return ""; }
  }
  function toast(msg) {
    var t = document.createElement("div");
    t.className = "cat-toast";
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 2200);
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
        window.location.href = "/connexion?next=/professionnel/catalogue";
        throw new Error("Non authentifie");
      }
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    });
  }
  function normalize(s) {
    try {
      var str = String(s == null ? "" : s).toLowerCase();
      return str
        .replace(/\u00e0|\u00e2|\u00e4/g, "a")
        .replace(/\u00e9|\u00e8|\u00ea|\u00eb/g, "e")
        .replace(/\u00ee|\u00ef|\u00ed/g, "i")
        .replace(/\u00f4|\u00f6|\u00f3/g, "o")
        .replace(/\u00f9|\u00fb|\u00fc/g, "u")
        .replace(/\u00e7/g, "c");
    } catch (e) { return String(s || ""); }
  }
  function availabilityInfo(p) {
    var a = (p.availability || "").toLowerCase();
    if (a === "rupture" || a === "indisponible" || a === "indispo") {
      return { cls: "indispo", label: "Indisponible" };
    }
    if (a === "stock_limite" || a === "stock limité") {
      return { cls: "limite", label: "Stock limité" };
    }
    if (a === "a_confirmer" || a === "à confirmer") {
      return { cls: "confirmer", label: "À confirmer" };
    }
    return { cls: "dispo", label: "Disponible" };
  }
  function fmtPrice(v) {
    var n = Math.round(Number(v) || 0);
    try { return n.toLocaleString("fr-FR") + " F"; }
    catch (e) { return String(n) + " F"; }
  }

  // ============================================================
  // Chargements
  // ============================================================
  function loadProducts() {
    return api("GET", "/products").then(function (list) {
      state.products = Array.isArray(list) ? list : [];
    });
  }
  function loadCategories() {
    return api("GET", "/categories").then(function (list) {
      state.categories = Array.isArray(list) ? list : [];
    });
  }
  function loadDraftOnce() {
    // Recupere le draft ID et le compteur actuel UNE SEULE FOIS
    return api("GET", "/pro/requests/draft").then(function (draft) {
      if (draft && draft.reference) {
        state.draftRef = draft.reference;
        return api("GET", "/pro/requests/" + draft.reference).then(function (full) {
          state.draftItemsCount = (full.items || []).length + (full.attachments || []).length;
          updateNavCount();
        });
      }
    }).catch(function (e) {
      console.warn("[catalogue] draft non charge :", e.message);
      state.draftRef = null;
    });
  }

  // ============================================================
  // Enregistrement du draft (lazy, uniquement si necessaire)
  // ============================================================
  function ensureDraftRef() {
    if (state.draftRef) return Promise.resolve(state.draftRef);
    return api("GET", "/pro/requests/draft").then(function (draft) {
      state.draftRef = draft.reference;
      return state.draftRef;
    });
  }

  // ============================================================
  // Ajout optimiste (UI d'abord, POST en arriere-plan, queue sequentielle)
  // ============================================================
  function addToDraft(product, qty, btn) {
    // 1. UI optimiste IMMEDIATE
    state.draftItemsCount += 1;
    updateNavCount();
    if (btn) {
      btn.classList.add("done");
      btn.innerHTML = "&#10003; Ajoute";
      btn.disabled = true;
      setTimeout(function () {
        btn.classList.remove("done");
        btn.disabled = false;
        btn.innerHTML = "+ Ajouter a ma demande";
      }, 1200);
    }

    // 2. Push dans la queue
    state.queue.push({ product: product, qty: qty });
    processQueue();

    // Pas de toast pour chaque ajout (evite le spam) - feedback sur le bouton suffit
  }

  function processQueue() {
    if (state.inFlight) return;
    if (state.queue.length === 0) return;

    state.inFlight = true;
    var item = state.queue.shift();

    ensureDraftRef()
      .then(function (ref) {
        var desc = (item.product.name || "") + (item.product.presentation ? " - " + item.product.presentation : "");
        return api("POST", "/pro/requests/" + encodeURIComponent(ref) + "/items", {
          product_id: item.product.id,
          description: desc,
          requested_quantity: item.qty
        });
      })
      .then(function () {
        // Succes : rien a faire (deja increment)
        state.inFlight = false;
        processQueue();
      })
      .catch(function (e) {
        // Echec : decrement + toast
        console.error("[catalogue] erreur ajout", e);
        state.draftItemsCount = Math.max(0, state.draftItemsCount - 1);
        updateNavCount();
        toast(e.message || "Erreur d'ajout");
        state.inFlight = false;
        processQueue();
      });
  }

  function updateNavCount() {
    try {
      var c = document.getElementById("nav-count");
      if (!c) return;
      var n = state.draftItemsCount;
      if (n > 0) {
        c.textContent = n > 99 ? "99+" : String(n);
        c.classList.remove("hidden");
      } else {
        c.classList.add("hidden");
      }
    } catch (e) { console.error("[updateNavCount]", e); }
  }

  // ============================================================
  // Rendu categories / filtres / grille (inchange)
  // ============================================================
  function renderCategories() {
    var box = document.getElementById("cats");
    if (!box) return;
    box.innerHTML = "";
    var all = document.createElement("button");
    all.type = "button";
    all.className = "cat-chip active";
    all.textContent = "Tous";
    all.setAttribute("data-cat", "");
    box.appendChild(all);
    state.categories.forEach(function (c) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "cat-chip";
      b.textContent = c.name + " (" + c.total + ")";
      b.setAttribute("data-cat", c.name);
      box.appendChild(b);
    });
    $$(".cat-chip", box).forEach(function (b) {
      b.addEventListener("click", function () {
        $$(".cat-chip", box).forEach(function (x) { x.classList.remove("active"); });
        b.classList.add("active");
        state.categoryFilter = b.getAttribute("data-cat") || "";
        applyFilters();
      });
    });
  }

  function renderFilters() {
    var avail = document.getElementById("filter-avail");
    if (!avail) return;
    avail.innerHTML = "";
    var AVAILS = [
      ["", "Toutes"],
      ["disponible", "Disponible"],
      ["stock_limite", "Stock limité"],
      ["a_confirmer", "À confirmer"],
      ["rupture", "Indisponible"]
    ];
    AVAILS.forEach(function (pair) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "cat-filter-opt" + (state.availFilter === pair[0] ? " active" : "");
      b.textContent = pair[1];
      b.addEventListener("click", function () {
        state.availFilter = pair[0];
        renderFilters();
        applyFilters();
      });
      avail.appendChild(b);
    });
  }

  function applyFilters() {
    var q = normalize(state.query);
    var cat = state.categoryFilter;
    var av = state.availFilter;
    state.filtered = state.products.filter(function (p) {
      if (cat && p.category !== cat) return false;
      if (av && (p.availability || "").toLowerCase() !== av) return false;
      if (q) {
        var hay = normalize(
          (p.name || "") + " " + (p.presentation || "") + " " +
          (p.description || "") + " " + (p.category || "")
        );
        if (hay.indexOf(q) === -1) return false;
      }
      return true;
    });
    renderGrid();
  }

  function renderGrid() {
    var grid = document.getElementById("grid");
    var empty = document.getElementById("empty");
    var countEl = document.getElementById("count");
    if (!grid) return;
    grid.innerHTML = "";
    if (state.filtered.length === 0) {
      grid.classList.add("hidden");
      if (empty) empty.classList.remove("hidden");
      if (countEl) countEl.textContent = state.query ? 'Aucun résultat pour "' + state.query + '"' : "0 produit";
      return;
    }
    grid.classList.remove("hidden");
    if (empty) empty.classList.add("hidden");
    if (countEl) {
      countEl.innerHTML = "<strong>" + state.filtered.length + "</strong> produit" +
        (state.filtered.length > 1 ? "s" : "");
    }
    state.filtered.forEach(function (p) {
      grid.appendChild(productCard(p));
    });
  }

  function productCard(p) {
    var card = document.createElement("article");
    card.className = "cat-card";

    var avail = availabilityInfo(p);

    // Image
    var imgBox = document.createElement("div");
    imgBox.className = "cat-card-img";
    if (p.image_url) {
      var img = document.createElement("img");
      img.src = p.image_url;
      img.alt = p.name;
      img.loading = "lazy";
      img.onerror = function () {
        img.remove();
        imgBox.innerHTML = '<div class="cat-card-img-placeholder">' +
          escapeHtml((p.name || "?").charAt(0).toUpperCase()) + '</div>';
      };
      imgBox.appendChild(img);
    } else {
      imgBox.innerHTML = '<div class="cat-card-img-placeholder">' +
        escapeHtml((p.name || "?").charAt(0).toUpperCase()) + '</div>';
    }
    card.appendChild(imgBox);

    // Body
    var body = document.createElement("div");
    body.className = "cat-card-body";

    var name = document.createElement("h3");
    name.className = "cat-card-name";
    name.textContent = p.name || "";
    body.appendChild(name);

    var meta = document.createElement("div");
    meta.className = "cat-card-meta";
    meta.textContent = p.presentation || p.category || "";
    body.appendChild(meta);

    var badge = document.createElement("span");
    badge.className = "cat-badge " + avail.cls;
    badge.textContent = avail.label;
    body.appendChild(badge);

    var price = document.createElement("div");
    price.className = "cat-card-price";
    price.textContent = fmtPrice(p.price);
    body.appendChild(price);

    // Quantite
    var qtyWrap = document.createElement("div");
    qtyWrap.className = "cat-card-qty";
    var minus = document.createElement("button");
    minus.type = "button"; minus.textContent = "\u2212";
    var qtyIn = document.createElement("input");
    qtyIn.type = "text"; qtyIn.value = "1";
    var plus = document.createElement("button");
    plus.type = "button"; plus.textContent = "+";
    minus.addEventListener("click", function () {
      var v = parseInt(qtyIn.value) || 1;
      qtyIn.value = Math.max(1, v - 1);
    });
    plus.addEventListener("click", function () {
      var v = parseInt(qtyIn.value) || 1;
      qtyIn.value = v + 1;
    });
    qtyWrap.appendChild(minus); qtyWrap.appendChild(qtyIn); qtyWrap.appendChild(plus);
    body.appendChild(qtyWrap);

    // Bouton ajouter
    var add = document.createElement("button");
    add.type = "button";
    add.className = "cat-card-add";
    add.innerHTML = "+ Ajouter a ma demande";
    add.addEventListener("click", function () {
      var q = parseInt(qtyIn.value) || 1;
      addToDraft(p, q, add);
    });
    body.appendChild(add);

    card.appendChild(body);
    return card;
  }

  // ============================================================
  // Besoin personnalise
  // ============================================================
  function addCustom() {
    var desc = (document.getElementById("custom-desc").value || "").trim();
    var qtyRaw = (document.getElementById("custom-qty").value || "").trim();
    if (!desc) { toast("Decrivez votre besoin"); return; }
    var qty = parseInt(qtyRaw) || 1;
    var fakeProduct = { id: null, name: desc, presentation: "" };
    var btn = document.getElementById("custom-add");
    if (btn) { btn.disabled = true; btn.textContent = "Ajout..."; }

    ensureDraftRef()
      .then(function (ref) {
        return api("POST", "/pro/requests/" + encodeURIComponent(ref) + "/items", {
          product_id: null,
          description: desc,
          requested_quantity: qty
        });
      })
      .then(function () {
        state.draftItemsCount += 1;
        updateNavCount();
        document.getElementById("custom-desc").value = "";
        document.getElementById("custom-qty").value = "";
        toast("Besoin ajoute a votre demande");
      })
      .catch(function (e) { toast(e.message); })
      .then(function () {
        if (btn) { btn.disabled = false; btn.textContent = "+ Ajouter a ma demande"; }
      });
  }

  // ============================================================
  // Init
  // ============================================================
  function init() {
    var s = document.getElementById("search");
    if (s) {
      s.addEventListener("input", function () {
        state.query = s.value.trim();
        applyFilters();
      });
    }

    var filterBtn = document.getElementById("filter-btn");
    if (filterBtn) {
      filterBtn.addEventListener("click", function () {
        var f = document.getElementById("filters");
        if (f.classList.contains("hidden")) {
          f.classList.remove("hidden");
          filterBtn.classList.add("active");
        } else {
          f.classList.add("hidden");
          filterBtn.classList.remove("active");
        }
      });
    }

    var customAdd = document.getElementById("custom-add");
    if (customAdd) customAdd.addEventListener("click", addCustom);

    var emptyCustom = document.getElementById("empty-custom-btn");
    if (emptyCustom) {
      emptyCustom.addEventListener("click", function () {
        var custom = document.querySelector(".cat-custom");
        if (custom) custom.scrollIntoView({ behavior: "smooth" });
        setTimeout(function () {
          var d = document.getElementById("custom-desc");
          if (d) d.focus();
        }, 400);
      });
    }

    // Chargement initial (parallel)
    Promise.all([loadCategories(), loadProducts(), loadDraftOnce()])
      .then(function () {
        renderCategories();
        renderFilters();
        applyFilters();
      })
      .catch(function (e) {
        var count = document.getElementById("count");
        if (count) count.textContent = "Erreur de chargement";
        console.error("[catalogue] init error", e);
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
'''

CATJS.write_text(NEW_JS, encoding="utf-8")
print("[OK] professional_catalogue.js reecrit (optimise)")

print()
print("=" * 60)
print("OPTIMISATION CATALOGUE APPLIQUEE")
print("=" * 60)
print()
print("Avant :")
print("  - 3-4 requetes par clic (draft + post + reload)")
print("  - 1-2 secondes d'attente par produit")
print()
print("Apres :")
print("  - Draft charge UNE FOIS au demarrage")
print("  - UI optimiste : compteur +1 immediat")
print("  - POST en arriere-plan (queue sequentielle)")
print("  - Zero attente percue par l'utilisateur")
print()
print("PROCHAINE ETAPE :")
print("  1. Ctrl+Shift+R sur /professionnel/catalogue")
print("  2. Test : ajoute 5 produits rapidement, ca doit etre instantane")
print("=" * 60)