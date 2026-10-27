/* ============================================================
   Elonikab Health - Catalogue & Stock (Lot 7)
   ============================================================ */
(function () {
  "use strict";
  var API = "/api";
  var catState = { products: [], q: "", cat: "", status: "" };
  var stkState = { products: [], q: "", alerts: null, filter: "" };
  var editingProductId = null;

  function $(id) { return document.getElementById(id); }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function fmtPrice(v) {
    var n = Math.round(Number(v) || 0);
    try { return n.toLocaleString("fr-FR") + " FCFA"; }
    catch (e) { return n + " FCFA"; }
  }

  function toast(msg, kind) {
    var t = document.createElement("div");
    t.className = "ph-toast " + (kind || "");
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 3000);
  }

  function apiCall(method, path, body) {
    var opts = {
      method: method,
      credentials: "same-origin",
      headers: {}
    };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(API + path, opts).then(function (r) {
      return r.text().then(function (txt) {
        var d = null;
        try { d = txt ? JSON.parse(txt) : null; } catch (e) {}
        if (!r.ok) {
          var msg = (d && d.detail) || ("Erreur " + r.status);
          throw new Error(msg);
        }
        return d;
      });
    });
  }

  // ============================================================
  // CATALOGUE
  // ============================================================
  function loadCatalog() {
    var box = $("ph-cat-content");
    if (box) box.innerHTML = '<div class="ph-cat-card">Chargement...</div>';
    apiCall("GET", "/products").then(function (list) {
      catState.products = list || [];
      renderCatalog();
    }).catch(function (e) { toast(e.message, "err"); });
  }

  function renderCatalog() {
    var list = catState.products.slice();
    var q = (catState.q || "").toLowerCase();
    if (q) list = list.filter(function (p) {
      return (p.name || "").toLowerCase().indexOf(q) >= 0 ||
             (p.category || "").toLowerCase().indexOf(q) >= 0;
    });
    if (catState.cat) list = list.filter(function (p) { return p.category === catState.cat; });
    if (catState.status === "active")   list = list.filter(function (p) { return p.is_active == 1; });
    if (catState.status === "inactive") list = list.filter(function (p) { return p.is_active == 0; });
    if (catState.status === "rupture")  list = list.filter(function (p) { return (p.stock_quantity||0) <= 0; });
    if (catState.status === "low")      list = list.filter(function (p) {
      var q2 = p.stock_quantity, m = p.stock_min_threshold || 5;
      return q2 != null && q2 > 0 && q2 <= m;
    });

    // Populate categories
    var cats = {};
    catState.products.forEach(function (p) { if (p.category) cats[p.category] = 1; });
    var sel = $("ph-cat-cat");
    if (sel) {
      var current = sel.value;
      sel.innerHTML = '<option value="">Toutes catégories</option>';
      Object.keys(cats).sort().forEach(function (c) {
        sel.innerHTML += '<option value="' + esc(c) + '"' + (c===current?" selected":"") + '>' + esc(c) + '</option>';
      });
    }

    // Count
    var cnt = $("ph-cat-count");
    if (cnt) cnt.textContent = list.length + " produit(s)";

    // Desktop table
    var tbody = $("ph-cat-tbody");
    if (tbody) {
      if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:30px;color:#64748B">Aucun produit</td></tr>';
      } else {
        tbody.innerHTML = list.map(function (p) {
          var statusBadge = "";
          if (p.is_active == 0) statusBadge = '<span class="ph-badge ph-badge-muted">Archivé</span>';
          else if ((p.stock_quantity||0) <= 0) statusBadge = '<span class="ph-badge ph-badge-danger">Rupture</span>';
          else if (p.stock_quantity != null && p.stock_quantity <= (p.stock_min_threshold||5))
            statusBadge = '<span class="ph-badge ph-badge-warn">Stock faible</span>';
          else if (p.stock_quantity == null) statusBadge = '<span class="ph-badge ph-badge-muted">Non renseigné</span>';
          else statusBadge = '<span class="ph-badge ph-badge-ok">Actif</span>';
          return (
            '<tr data-id="' + p.id + '">' +
            '<td><div class="ph-cat-thumb">' + (p.image_url ? '<img src="' + esc(p.image_url) + '" onerror="this.style.display=\'none\'">' : '📦') + '</div></td>' +
            '<td><div class="ph-cat-name">' + esc(p.name) + '</div><div class="ph-cat-pres">' + esc(p.presentation || "") + '</div></td>' +
            '<td>' + esc(p.category || "—") + '</td>' +
            '<td class="ph-cat-price">' + fmtPrice(p.price) + '</td>' +
            '<td>' + (p.stock_quantity == null ? "—" : p.stock_quantity) + ' ' + statusBadge + '</td>' +
            '<td style="text-align:right;white-space:nowrap">' +
              '<button class="ph-btn ph-btn-ghost ph-btn-sm" data-act="edit" data-id="' + p.id + '">Modifier</button> ' +
              '<button class="ph-btn ph-btn-danger ph-btn-sm" data-act="archive" data-id="' + p.id + '">Archiver</button>' +
            '</td>' +
            '</tr>'
          );
        }).join("");
      }
    }

    // Mobile cards
    var cards = $("ph-cat-cards");
    if (cards) {
      if (list.length === 0) {
        cards.innerHTML = '<div style="text-align:center;padding:30px;color:#64748B">Aucun produit</div>';
      } else {
        cards.innerHTML = list.map(function (p) {
          return (
            '<div class="ph-cat-card" data-id="' + p.id + '">' +
            '<div class="ph-cat-card-thumb">' + (p.image_url ? '<img src="' + esc(p.image_url) + '" onerror="this.style.display=\'none\'">' : '📦') + '</div>' +
            '<div class="ph-cat-card-body">' +
              '<div class="ph-cat-name">' + esc(p.name) + '</div>' +
              '<div class="ph-cat-pres">' + esc(p.presentation || "") + '</div>' +
              '<div style="margin:6px 0;font-weight:800;color:#174A7E">' + fmtPrice(p.price) + '</div>' +
              '<div style="margin-bottom:8px">' + ((p.stock_quantity==null?"Stock N/R":p.stock_quantity+" en stock")) + '</div>' +
              '<button class="ph-btn ph-btn-ghost ph-btn-sm" data-act="edit" data-id="' + p.id + '">Modifier</button> ' +
              '<button class="ph-btn ph-btn-danger ph-btn-sm" data-act="archive" data-id="' + p.id + '">Archiver</button>' +
            '</div></div>'
          );
        }).join("");
      }
    }
  }

  // ============================================================
  // MODALE PRODUIT
  // ============================================================
  function openProductModal(product) {
    editingProductId = product ? product.id : null;
    var html = (
      '<div class="ph-modal-head">' +
        '<h3>' + (product ? "Modifier le produit" : "Nouveau produit") + '</h3>' +
        '<button type="button" class="ph-modal-close" data-close>×</button>' +
      '</div>' +
      '<div class="ph-modal-body">' +
        '<div class="ph-form-row"><label>Nom *</label><input id="f-name" type="text" value="' + esc(product ? product.name : "") + '"></div>' +
        '<div class="ph-form-2col">' +
          '<div class="ph-form-row"><label>Présentation</label><input id="f-pres" type="text" value="' + esc(product ? product.presentation : "") + '"></div>' +
          '<div class="ph-form-row"><label>Catégorie</label><input id="f-cat" type="text" value="' + esc(product ? product.category : "") + '"></div>' +
        '</div>' +
        '<div class="ph-form-2col">' +
          '<div class="ph-form-row"><label>Prix (FCFA) *</label><input id="f-price" type="number" min="0" step="50" value="' + (product ? product.price : 0) + '"></div>' +
          '<div class="ph-form-row"><label>Ordonnance</label><select id="f-presc"><option value="0"' + (!product||!product.requires_prescription?' selected':'') + '>Non</option><option value="1"' + (product&&product.requires_prescription?' selected':'') + '>Oui</option></select></div>' +
        '</div>' +
        '<div class="ph-form-2col">' +
          '<div class="ph-form-row"><label>Stock initial</label><input id="f-stock" type="number" min="0" value="' + (product && product.stock_quantity != null ? product.stock_quantity : "") + '" placeholder="Optionnel"></div>' +
          '<div class="ph-form-row"><label>Seuil alerte</label><input id="f-min" type="number" min="0" value="' + (product ? (product.stock_min_threshold||5) : 5) + '"></div>' +
        '</div>' +
        '<div class="ph-form-row"><label>Description</label><textarea id="f-desc" rows="3">' + esc(product ? product.description : "") + '</textarea></div>' +
        '<div class="ph-form-row"><label>Image principale <span style="color:#B23C3C">*</span></label>' +
          '<div class="ph-image-preview" id="f-img-prev">' +
            (product && product.image_url ? '<img src="' + esc(product.image_url) + '">' : '📷') +
          '</div>' +
          '<input type="file" id="f-img-input" accept="image/jpeg,image/png,image/webp" style="margin-top:6px;font-size:12px">' +
          '<small style="color:#94A3B8;font-size:11.5px;display:block;margin-top:4px">Formats acceptés : JPG, PNG, WEBP — max 5 Mo</small>' +
        '</div>' +
      '</div>' +
      '<div class="ph-modal-foot">' +
        '<button type="button" class="ph-btn ph-btn-ghost" data-close>Annuler</button>' +
        '<button type="button" class="ph-btn ph-btn-primary" id="f-save">' + (product ? "Enregistrer" : "Créer") + '</button>' +
      '</div>'
    );
    showModal(html);
    var btn = $("f-save");
    if (btn) btn.addEventListener("click", saveProduct);
    var imgInput = $("f-img-input");
    if (imgInput) imgInput.addEventListener("change", onImagePick);
  }

  function onImagePick(ev) {
    var file = ev.target.files && ev.target.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { toast("Image trop lourde (max 5 Mo)", "err"); return; }
    var reader = new FileReader();
    reader.onload = function (e) {
      var prev = $("f-img-prev");
      if (prev) prev.innerHTML = '<img src="' + e.target.result + '">';
    };
    reader.readAsDataURL(file);
  }

  function saveProduct() {
    var payload = {
      name: ($("f-name").value || "").trim(),
      presentation: ($("f-pres").value || "").trim(),
      category: ($("f-cat").value || "").trim() || "Divers",
      price: parseFloat($("f-price").value),
      description: ($("f-desc").value || "").trim(),
      requires_prescription: parseInt($("f-presc").value, 10) || 0,
      stock_min_threshold: parseInt($("f-min").value, 10) || 5
    };
    var stockRaw = $("f-stock").value;
    if (stockRaw !== "" && stockRaw !== null) {
      payload.stock_quantity = parseInt(stockRaw, 10);
    }
    if (!payload.name || payload.name.length < 2) { toast("Nom obligatoire", "err"); return; }
    if (isNaN(payload.price) || payload.price < 0) { toast("Prix invalide", "err"); return; }

    // Photo obligatoire pour la creation
    var isNewProduct = !editingProductId;
    var imgInputCheck = $("f-img-input");
    var hasFile = imgInputCheck && imgInputCheck.files && imgInputCheck.files[0];
    if (isNewProduct && !hasFile) {
      toast("Image obligatoire pour creer un produit", "err");
      return;
    }

    var btn = $("f-save");
    if (btn) { btn.disabled = true; btn.textContent = "..."; }

    var isNew = !editingProductId;
    var call = isNew
      ? apiCall("POST", "/admin/products", payload)
      : apiCall("PATCH", "/admin/products/" + editingProductId, payload);

    call.then(function (saved) {
      var pid = isNew ? saved.id : editingProductId;
      var imgInput = $("f-img-input");
      var file = imgInput && imgInput.files && imgInput.files[0];
      if (file && pid) {
        return uploadImage(pid, file).then(function () { return saved; });
      }
      return saved;
    }).then(function () {
      closeModal();
      toast(isNew ? "Produit créé" : "Produit modifié", "ok");
      loadCatalog();
    }).catch(function (e) {
      toast(e.message, "err");
      if (btn) { btn.disabled = false; btn.textContent = isNew ? "Créer" : "Enregistrer"; }
    });
  }

  function uploadImage(pid, file) {
    var form = new FormData();
    form.append("file", file);
    return fetch(API + "/admin/products/" + pid + "/images", {
      method: "POST", credentials: "same-origin", body: form
    }).then(function (r) {
      return r.text().then(function (t) {
        var d = null; try { d = t ? JSON.parse(t) : null; } catch (e) {}
        if (!r.ok) throw new Error((d && d.detail) || "Erreur upload");
        return d;
      });
    });
  }

  function archiveProduct(id) {
    if (!confirm("Archiver ce produit ?\n\nIl ne sera plus visible côté patient, mais les commandes existantes sont préservées.")) return;
    apiCall("DELETE", "/admin/products/" + id)
      .then(function () { toast("Produit archivé", "ok"); loadCatalog(); })
      .catch(function (e) { toast(e.message, "err"); });
  }

  // ============================================================
  // MODALE
  // ============================================================
  function showModal(html) {
    var back = $("ph-cat-modal");
    if (!back) return;
    back.querySelector(".ph-modal").innerHTML = html;
    back.classList.add("show");
    back.querySelectorAll("[data-close]").forEach(function (b) {
      b.addEventListener("click", closeModal);
    });
    back.addEventListener("click", function (e) {
      if (e.target === back) closeModal();
    });
  }

  function closeModal() {
    var back = $("ph-cat-modal");
    if (back) back.classList.remove("show");
    editingProductId = null;
  }

  // ============================================================
  // STOCK
  // ============================================================
  function loadStock() {
    var box = $("ph-stk-content");
    if (box) box.innerHTML = '<div style="text-align:center;padding:30px;color:#64748B">Chargement...</div>';
    Promise.all([
      apiCall("GET", "/admin/stock"),
      apiCall("GET", "/admin/stock/alerts"),
      apiCall("GET", "/admin/stock/movements?limit=50")
    ]).then(function (res) {
      stkState.products = res[0] || [];
      stkState.alerts = res[1] || {};
      stkState.movements = res[2] || [];
      renderStock();
    }).catch(function (e) {
      var box = $("ph-stk-content");
      if (box) box.innerHTML = '<div style="padding:30px;color:#B23C3C">Erreur : ' + esc(e.message) + '</div>';
      toast(e.message, "err");
    });
  }

  function renderStock() {
    var a = stkState.alerts || {};
    var rupt = (a.rupture || []).length;
    var low = (a.low_stock || []).length;
    var soon = (a.expiring_soon || []).length;

    var alertsBox = $("ph-stk-alerts");
    if (alertsBox) {
      alertsBox.innerHTML =
        '<div class="ph-stk-alert danger"><span class="ico">🚨</span><strong>' + rupt + '</strong><span>Ruptures</span></div>' +
        '<div class="ph-stk-alert warn"><span class="ico">⚠️</span><strong>' + low + '</strong><span>Stock faible</span></div>' +
        '<div class="ph-stk-alert"><span class="ico">📅</span><strong>' + soon + '</strong><span>Péremption ≤30j</span></div>' +
        '<div class="ph-stk-alert"><span class="ico">📦</span><strong>' + (stkState.products||[]).length + '</strong><span>Produits actifs</span></div>';
    }

    var q = (stkState.q || "").toLowerCase();
    var list = (stkState.products || []).slice();
    if (q) list = list.filter(function (p) { return (p.name||"").toLowerCase().indexOf(q) >= 0; });

    var tbody = $("ph-stk-tbody");
    if (tbody) {
      if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:30px;color:#64748B">Aucun produit</td></tr>';
      } else {
        tbody.innerHTML = list.map(function (p) {
          var badge = "";
          if (p.stock_quantity == null) badge = '<span class="ph-badge ph-badge-muted">Non renseigné</span>';
          else if (p.stock_quantity <= 0) badge = '<span class="ph-badge ph-badge-danger">Rupture</span>';
          else if (p.stock_quantity <= (p.stock_min_threshold||5)) badge = '<span class="ph-badge ph-badge-warn">Faible</span>';
          else badge = '<span class="ph-badge ph-badge-ok">OK</span>';
          return (
            '<tr>' +
            '<td><div class="ph-cat-name">' + esc(p.name) + '</div><div class="ph-cat-pres">' + esc(p.category||"") + '</div></td>' +
            '<td><strong>' + (p.stock_quantity == null ? "N/R" : p.stock_quantity) + '</strong></td>' +
            '<td>' + (p.stock_min_threshold||5) + '</td>' +
            '<td>' + badge + '</td>' +
            '<td style="text-align:right"><button class="ph-btn ph-btn-primary ph-btn-sm" data-act="move" data-id="' + p.id + '" data-name="' + esc(p.name) + '">Mouvement</button></td>' +
            '</tr>'
          );
        }).join("");
      }
    }

    var movBox = $("ph-stk-movements");
    if (movBox) {
      var mv = stkState.movements || [];
      if (mv.length === 0) {
        movBox.innerHTML = '<div style="text-align:center;padding:24px;color:#64748B">Aucun mouvement</div>';
      } else {
        movBox.innerHTML = '<table class="ph-cat-table"><thead><tr><th>Date</th><th>Produit</th><th>Type</th><th>Qté</th><th>Motif</th></tr></thead><tbody>' +
          mv.slice(0, 20).map(function (m) {
            var sign = m.quantity > 0 ? "+" : "";
            return '<tr><td style="font-size:12px">' + esc((m.created_at||"").slice(0,16)) + '</td>' +
              '<td>' + esc(m.product_name || "—") + '</td>' +
              '<td><span class="ph-badge ph-badge-info">' + esc(m.type) + '</span></td>' +
              '<td><strong style="color:' + (m.quantity>0?"#0A7A5A":"#B23C3C") + '">' + sign + m.quantity + '</strong></td>' +
              '<td style="font-size:12px">' + esc(m.reason || "—") + '</td></tr>';
          }).join("") + '</tbody></table>';
      }
    }
  }

  // Modale mouvement
  function openMovementModal(productId, productName) {
    var html =
      '<div class="ph-modal-head"><h3>Mouvement de stock</h3>' +
      '<button type="button" class="ph-modal-close" data-close>×</button></div>' +
      '<div class="ph-modal-body">' +
        '<div style="font-size:13.5px;color:#64748B;margin-bottom:12px">Produit : <strong>' + esc(productName) + '</strong></div>' +
        '<div class="ph-form-row"><label>Type *</label><select id="m-type">' +
          '<option value="IN">Entrée (+)</option>' +
          '<option value="OUT">Sortie (-)</option>' +
          '<option value="ADJUST">Ajustement (±)</option>' +
        '</select></div>' +
        '<div class="ph-form-row"><label>Quantité *</label><input id="m-qty" type="number" step="1" value="1"></div>' +
        '<div class="ph-form-row"><label>Motif</label><input id="m-reason" type="text" placeholder="Obligatoire pour ajustement"></div>' +
        '<div class="ph-form-row"><label>Référence</label><input id="m-ref" type="text" placeholder="Optionnel (ex: CMD-xxx, LOT-xxx)"></div>' +
      '</div>' +
      '<div class="ph-modal-foot">' +
        '<button type="button" class="ph-btn ph-btn-ghost" data-close>Annuler</button>' +
        '<button type="button" class="ph-btn ph-btn-primary" id="m-save">Enregistrer</button>' +
      '</div>';
    showModal(html);
    var btn = $("m-save");
    if (btn) btn.addEventListener("click", function () { saveMovement(productId); });
  }

  function saveMovement(productId) {
    var payload = {
      product_id: productId,
      type: $("m-type").value,
      quantity: parseInt($("m-qty").value, 10),
      reason: ($("m-reason").value || "").trim(),
      reference: ($("m-ref").value || "").trim()
    };
    if (!payload.quantity || isNaN(payload.quantity)) { toast("Quantité invalide", "err"); return; }
    var btn = $("m-save");
    if (btn) { btn.disabled = true; btn.textContent = "..."; }
    apiCall("POST", "/admin/stock/movements", payload)
      .then(function (r) {
        closeModal();
        toast("Stock mis à jour : " + r.new_quantity, "ok");
        loadStock();
      })
      .catch(function (e) {
        toast(e.message, "err");
        if (btn) { btn.disabled = false; btn.textContent = "Enregistrer"; }
      });
  }

  // ============================================================
  // EVENTS
  // ============================================================
  document.addEventListener("click", function (ev) {
    var t = ev.target;
    // Nouveau produit
    if (t.id === "ph-cat-add") { openProductModal(null); return; }
    // Actions tableau/cartes
    var btn = t.closest ? t.closest("[data-act]") : null;
    if (btn) {
      var act = btn.getAttribute("data-act");
      var id = parseInt(btn.getAttribute("data-id"), 10);
      if (act === "edit") {
        var p = catState.products.find(function (x) { return x.id === id; });
        if (p) openProductModal(p);
      } else if (act === "archive") {
        archiveProduct(id);
      } else if (act === "move") {
        openMovementModal(id, btn.getAttribute("data-name"));
      }
      return;
    }
    // Onglets
    var tab = t.closest ? t.closest("[data-ph-tab]") : null;
    if (tab) {
      var name = tab.getAttribute("data-ph-tab");
      if (name === "catalogue") setTimeout(loadCatalog, 100);
      if (name === "stock") setTimeout(loadStock, 100);
    }
  });

  // Recherche + filtres catalogue
  document.addEventListener("input", function (ev) {
    if (ev.target.id === "ph-cat-search") {
      clearTimeout(ev.target._t);
      ev.target._t = setTimeout(function () {
        catState.q = ev.target.value;
        renderCatalog();
      }, 200);
    }
    if (ev.target.id === "ph-stk-search") {
      clearTimeout(ev.target._t);
      ev.target._t = setTimeout(function () {
        stkState.q = ev.target.value;
        renderStock();
      }, 200);
    }
  });
  document.addEventListener("change", function (ev) {
    if (ev.target.id === "ph-cat-cat")   { catState.cat = ev.target.value; renderCatalog(); }
    if (ev.target.id === "ph-cat-status"){ catState.status = ev.target.value; renderCatalog(); }
  });

  // Init on load if already on page
  document.addEventListener("DOMContentLoaded", function () {
    setTimeout(function () {
      var page = document.body.getAttribute("data-active-page");
      if (page === "catalogue") loadCatalog();
      if (page === "stock") loadStock();
    }, 400);
  });

  window.phLoadCatalog = loadCatalog;
  window.phLoadStock = loadStock;
})();
