/* ============================================================
   Elonikab Health - Sprint B+C Frontend
   Compta + Fournisseurs + Achats + Vue Direction
   ============================================================ */
(function () {
  "use strict";
  var API = "/api";

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function fmtMoney(v) {
    var n = Math.round(Number(v) || 0);
    try { return n.toLocaleString("fr-FR") + " FCFA"; }
    catch (e) { return n + " FCFA"; }
  }
  function fmtDate(iso) {
    if (!iso) return "";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return iso;
      var pad = function(n){ return n < 10 ? "0" + n : "" + n; };
      return pad(d.getDate()) + "/" + pad(d.getMonth()+1) + "/" + d.getFullYear();
    } catch (e) { return iso; }
  }
  function toast(msg, kind) {
    var t = document.createElement("div");
    t.className = "ph-compta-toast " + (kind || "");
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 3000);
  }
  function apiCall(method, path, body) {
    var opts = { method: method, credentials: "same-origin", headers: {} };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(API + path, opts).then(function (r) {
      return r.text().then(function (txt) {
        var d = null;
        try { d = txt ? JSON.parse(txt) : null; } catch (e) {}
        if (!r.ok) throw new Error((d && d.detail) || ("Erreur " + r.status));
        return d;
      });
    });
  }

  var currentMonth = (function(){
    var d = new Date();
    return d.getFullYear() + "-" + String(d.getMonth()+1).padStart(2,"0");
  })();
  var currentTab = "direction";

  // ============================================================
  // DIRECTION (dashboard mixte)
  // ============================================================
  function loadDirection() {
    var box = $("ph-compta-direction-content");
    if (box) box.innerHTML = '<div class="ph-compta-empty">Chargement...</div>';
    apiCall("GET", "/compta/dashboard").then(function (d) {
      if (!box) return;
      var benef = (d.benefice || 0);
      var benefCls = benef >= 0 ? "ok" : "danger";
      box.innerHTML =
        '<div class="ph-compta-kpis">' +
          '<div class="ph-compta-kpi"><strong>' + fmtMoney(d.recettes) + '</strong><small>Recettes du mois</small></div>' +
          '<div class="ph-compta-kpi warn"><strong>' + fmtMoney(d.depenses) + '</strong><small>Depenses du mois</small></div>' +
          '<div class="ph-compta-kpi ' + benefCls + '"><strong>' + fmtMoney(benef) + '</strong><small>Benefice</small></div>' +
          '<div class="ph-compta-kpi"><strong>' + fmtMoney(d.stock_value) + '</strong><small>Valeur stock</small></div>' +
        '</div>' +
        '<div class="ph-compta-bilan">' +
          '<div class="ph-compta-bilan-card">' +
            '<h3>Produits dormants</h3>' +
            '<div class="val">' + (d.dormant_products || 0) + ' produits</div>' +
            '<small>Aucune vente depuis 60 jours</small>' +
          '</div>' +
          '<div class="ph-compta-bilan-card">' +
            '<h3>Mois</h3>' +
            '<div class="val">' + esc(d.month || "") + '</div>' +
            '<small>Periode analysee</small>' +
          '</div>' +
          '<div class="ph-compta-bilan-card">' +
            '<h3>Marge estimee</h3>' +
            '<div class="val">' + (d.recettes > 0 ? Math.round(benef / d.recettes * 100) : 0) + '%</div>' +
            '<small>Benefice / Recettes</small>' +
          '</div>' +
        '</div>';
    }).catch(function (e) {
      if (box) box.innerHTML = '<div class="ph-compta-empty" style="color:#B23C3C">Erreur : ' + esc(e.message) + '</div>';
    });
  }

  // ============================================================
  // BILAN
  // ============================================================
  function loadBilan() {
    var box = $("ph-compta-bilan-content");
    if (box) box.innerHTML = '<div class="ph-compta-empty">Chargement...</div>';
    apiCall("GET", "/compta/summary?month=" + encodeURIComponent(currentMonth)).then(function (d) {
      if (!box) return;
      var benef = (d.benefice || 0);
      var benefCls = benef >= 0 ? "ok" : "danger";
      var catsHtml = "";
      var cats = d.depenses_par_categorie || {};
      var catKeys = Object.keys(cats);
      if (catKeys.length > 0) {
        catsHtml = '<div class="ph-compta-table-wrap"><table class="ph-compta-table">' +
          '<thead><tr><th>Categorie</th><th style="text-align:right">Montant</th></tr></thead><tbody>';
        catKeys.forEach(function (k) {
          catsHtml += '<tr><td>' + esc(k) + '</td><td class="num neg">' + fmtMoney(cats[k]) + '</td></tr>';
        });
        catsHtml += '</tbody></table></div>';
      }
      box.innerHTML =
        '<div class="ph-compta-kpis">' +
          '<div class="ph-compta-kpi ok"><strong>' + fmtMoney(d.recettes) + '</strong><small>Recettes (' + (d.recettes_count||0) + ' cmd)</small></div>' +
          '<div class="ph-compta-kpi warn"><strong>' + fmtMoney(d.depenses) + '</strong><small>Depenses (' + (d.depenses_count||0) + ')</small></div>' +
          '<div class="ph-compta-kpi ' + benefCls + '"><strong>' + fmtMoney(benef) + '</strong><small>Benefice net</small></div>' +
          '<div class="ph-compta-kpi"><strong>' + (d.marge_pct || 0) + '%</strong><small>Marge estimee</small></div>' +
        '</div>' +
        (catKeys.length > 0 ? '<h3 style="font-size:13px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:#64748B;margin:20px 0 10px">Depenses par categorie</h3>' + catsHtml : '');
    }).catch(function (e) {
      if (box) box.innerHTML = '<div class="ph-compta-empty" style="color:#B23C3C">Erreur : ' + esc(e.message) + '</div>';
    });
  }

  // ============================================================
  // DEPENSES
  // ============================================================
  var expensesCache = [];

  function loadExpenses() {
    var box = $("ph-compta-expenses-content");
    if (box) box.innerHTML = '<div class="ph-compta-empty">Chargement...</div>';
    apiCall("GET", "/compta/expenses?month=" + encodeURIComponent(currentMonth)).then(function (list) {
      expensesCache = list || [];
      renderExpenses();
    }).catch(function (e) {
      if (box) box.innerHTML = '<div class="ph-compta-empty" style="color:#B23C3C">Erreur : ' + esc(e.message) + '</div>';
    });
  }

  function renderExpenses() {
    var box = $("ph-compta-expenses-content");
    if (!box) return;
    var cats = ["Loyer","Salaires","Electricite","Eau","Internet","Fournitures","Transport","Entretien","Taxes","Autre"];
    var catOpts = cats.map(function(c){ return '<option value="' + c + '">' + c + '</option>'; }).join("");
    var h = '';
    h += '<div class="ph-compta-form">';
    h += '<h3>Ajouter une depense</h3>';
    h += '<div class="ph-compta-form-row">';
    h += '<div class="ph-compta-field"><label>Categorie *</label><select id="exp-cat">' + catOpts + '</select></div>';
    h += '<div class="ph-compta-field"><label>Libelle *</label><input id="exp-label" placeholder="Ex: Loyer Octobre"></div>';
    h += '</div>';
    h += '<div class="ph-compta-form-row">';
    h += '<div class="ph-compta-field"><label>Montant (FCFA) *</label><input id="exp-amount" type="number" min="1" step="50" placeholder="50000"></div>';
    h += '<div class="ph-compta-field"><label>Date *</label><input id="exp-date" type="date" value="' + new Date().toISOString().slice(0,10) + '"></div>';
    h += '</div>';
    h += '<div class="ph-compta-form-row">';
    h += '<div class="ph-compta-field"><label>Fournisseur (optionnel)</label><input id="exp-supplier" placeholder="Ex: Npower"></div>';
    h += '<div class="ph-compta-field"><label>Reference (optionnel)</label><input id="exp-ref" placeholder="Facture #123"></div>';
    h += '</div>';
    h += '<div class="ph-compta-actions"><button type="button" class="ph-compta-btn ph-compta-btn-primary" id="exp-add-btn">+ Ajouter</button></div>';
    h += '</div>';

    // Tableau
    h += '<div class="ph-compta-table-wrap"><table class="ph-compta-table">';
    h += '<thead><tr><th>Date</th><th>Categorie</th><th>Libelle</th><th style="text-align:right">Montant</th><th></th></tr></thead><tbody>';
    if (expensesCache.length === 0) {
      h += '<tr><td colspan="5" style="text-align:center;padding:30px;color:#94A3B8">Aucune depense ce mois</td></tr>';
    } else {
      expensesCache.forEach(function(e){
        h += '<tr>';
        h += '<td>' + esc(fmtDate(e.expense_date)) + '</td>';
        h += '<td>' + esc(e.category) + '</td>';
        h += '<td>' + esc(e.label) + '</td>';
        h += '<td class="num neg">' + fmtMoney(e.amount) + '</td>';
        h += '<td style="text-align:right"><button type="button" class="ph-compta-btn ph-compta-btn-danger ph-compta-btn-sm" data-del-exp="' + e.id + '">Suppr.</button></td>';
        h += '</tr>';
      });
    }
    h += '</tbody></table></div>';
    box.innerHTML = h;
    var addBtn = $("exp-add-btn");
    if (addBtn) addBtn.addEventListener("click", addExpense);
  }

  function addExpense() {
    var payload = {
      category: $("exp-cat").value,
      label: ($("exp-label").value || "").trim(),
      amount: parseFloat($("exp-amount").value),
      expense_date: $("exp-date").value,
      supplier_name: ($("exp-supplier").value || "").trim(),
      reference: ($("exp-ref").value || "").trim(),
    };
    if (!payload.label) { toast("Libelle obligatoire", "err"); return; }
    if (!payload.amount || payload.amount <= 0) { toast("Montant invalide", "err"); return; }
    if (!payload.expense_date) { toast("Date obligatoire", "err"); return; }
    var btn = $("exp-add-btn");
    if (btn) { btn.disabled = true; btn.textContent = "..."; }
    apiCall("POST", "/compta/expenses", payload).then(function () {
      toast("Depense ajoutee", "ok");
      loadExpenses();
    }).catch(function (e) {
      toast(e.message, "err");
      if (btn) { btn.disabled = false; btn.textContent = "+ Ajouter"; }
    });
  }

  // ============================================================
  // JOURNAL DE CAISSE
  // ============================================================
  function loadJournal() {
    var box = $("ph-compta-journal-content");
    if (box) box.innerHTML = '<div class="ph-compta-empty">Chargement...</div>';
    apiCall("GET", "/compta/journal?month=" + encodeURIComponent(currentMonth)).then(function (list) {
      if (!box) return;
      if (!list || list.length === 0) {
        box.innerHTML = '<div class="ph-compta-empty">Aucune ecriture ce mois</div>';
        return;
      }
      var h = '<div class="ph-compta-table-wrap"><table class="ph-compta-table">';
      h += '<thead><tr><th>Date</th><th>Type</th><th>Libelle</th><th>Ref.</th><th style="text-align:right">Montant</th></tr></thead><tbody>';
      list.forEach(function(j){
        var isIn = j.type === "IN";
        var cls = isIn ? "pos" : "neg";
        h += '<tr>';
        h += '<td>' + esc((j.created_at||"").slice(0,10)) + '</td>';
        h += '<td><span style="padding:3px 10px;border-radius:999px;font-size:11px;font-weight:800;background:' + (isIn ? '#E6F7F1' : '#FDECEC') + ';color:' + (isIn ? '#0A7A5A' : '#B23C3C') + '">' + esc(j.type) + '</span></td>';
        h += '<td>' + esc(j.label) + '</td>';
        h += '<td style="font-family:Consolas,monospace;font-size:11.5px;color:#64748B">' + esc(j.reference || "—") + '</td>';
        h += '<td class="num ' + cls + '">' + (isIn ? "+" : "−") + fmtMoney(j.amount) + '</td>';
        h += '</tr>';
      });
      h += '</tbody></table></div>';
      box.innerHTML = h;
    }).catch(function (e) {
      if (box) box.innerHTML = '<div class="ph-compta-empty" style="color:#B23C3C">Erreur : ' + esc(e.message) + '</div>';
    });
  }

  // ============================================================
  // FOURNISSEURS
  // ============================================================
  function loadSuppliers() {
    var box = $("ph-suppliers-content");
    if (!box) return;
    box.innerHTML = '<div class="ph-compta-empty">Chargement...</div>';
    apiCall("GET", "/admin/suppliers").then(function (list) {
      var h = '';
      h += '<div class="ph-compta-form"><h3>Ajouter un fournisseur</h3>';
      h += '<div class="ph-compta-form-row">';
      h += '<div class="ph-compta-field"><label>Nom *</label><input id="sup-name" placeholder="Ex: Grossiste Medora"></div>';
      h += '<div class="ph-compta-field"><label>Telephone</label><input id="sup-phone" placeholder="+228..."></div>';
      h += '</div>';
      h += '<div class="ph-compta-form-row">';
      h += '<div class="ph-compta-field"><label>Contact</label><input id="sup-contact" placeholder="Nom du contact"></div>';
      h += '<div class="ph-compta-field"><label>Email</label><input id="sup-email" type="email" placeholder="contact@..."></div>';
      h += '</div>';
      h += '<div class="ph-compta-actions"><button type="button" class="ph-compta-btn ph-compta-btn-primary" id="sup-add-btn">+ Ajouter</button></div>';
      h += '</div>';
      h += '<div class="ph-compta-table-wrap"><table class="ph-compta-table">';
      h += '<thead><tr><th>Nom</th><th>Contact</th><th>Telephone</th><th>Email</th><th></th></tr></thead><tbody>';
      if (!list || list.length === 0) {
        h += '<tr><td colspan="5" style="text-align:center;padding:30px;color:#94A3B8">Aucun fournisseur</td></tr>';
      } else {
        list.forEach(function(s){
          h += '<tr><td><strong>' + esc(s.name) + '</strong></td>';
          h += '<td>' + esc(s.contact_name || "—") + '</td>';
          h += '<td>' + esc(s.phone || "—") + '</td>';
          h += '<td>' + esc(s.email || "—") + '</td>';
          h += '<td style="text-align:right"><button type="button" class="ph-compta-btn ph-compta-btn-danger ph-compta-btn-sm" data-del-sup="' + s.id + '">Archiver</button></td></tr>';
        });
      }
      h += '</tbody></table></div>';
      box.innerHTML = h;
      var btn = $("sup-add-btn");
      if (btn) btn.addEventListener("click", addSupplier);
    }).catch(function (e) {
      box.innerHTML = '<div class="ph-compta-empty" style="color:#B23C3C">Erreur : ' + esc(e.message) + '</div>';
    });
  }

  function addSupplier() {
    var payload = {
      name: ($("sup-name").value || "").trim(),
      contact_name: ($("sup-contact").value || "").trim(),
      phone: ($("sup-phone").value || "").trim(),
      email: ($("sup-email").value || "").trim(),
    };
    if (!payload.name || payload.name.length < 2) { toast("Nom obligatoire", "err"); return; }
    var btn = $("sup-add-btn");
    if (btn) { btn.disabled = true; btn.textContent = "..."; }
    apiCall("POST", "/admin/suppliers", payload).then(function () {
      toast("Fournisseur ajoute", "ok");
      loadSuppliers();
    }).catch(function (e) {
      toast(e.message, "err");
      if (btn) { btn.disabled = false; btn.textContent = "+ Ajouter"; }
    });
  }

  // ============================================================
  // COMMANDES D'ACHAT
  // ============================================================
  function loadPurchaseOrders() {
    var box = $("ph-po-content");
    if (!box) return;
    box.innerHTML = '<div class="ph-compta-empty">Chargement...</div>';
    apiCall("GET", "/admin/purchase-orders").then(function (list) {
      var h = '<div class="ph-compta-toolbar">';
      h += '<button type="button" class="ph-compta-btn ph-compta-btn-primary" id="po-new-btn">+ Nouvelle commande</button>';
      h += '</div>';
      h += '<div class="ph-compta-table-wrap"><table class="ph-compta-table">';
      h += '<thead><tr><th>Reference</th><th>Fournisseur</th><th>Statut</th><th style="text-align:right">Montant</th><th></th></tr></thead><tbody>';
      if (!list || list.length === 0) {
        h += '<tr><td colspan="5" style="text-align:center;padding:30px;color:#94A3B8">Aucune commande d\'achat</td></tr>';
      } else {
        list.forEach(function(po){
          var stLbl = {draft:"Brouillon", received:"Recue", cancelled:"Annulee"}[po.status] || po.status;
          var stCol = po.status === "received" ? "#0A7A5A" : (po.status === "draft" ? "#B26B00" : "#64748B");
          h += '<tr>';
          h += '<td style="font-family:Consolas,monospace;font-weight:800;color:#174A7E">' + esc(po.reference) + '</td>';
          h += '<td>' + esc(po.supplier_name || "—") + '</td>';
          h += '<td><span style="padding:3px 10px;border-radius:999px;font-size:11px;font-weight:800;background:#E2E8F0;color:' + stCol + '">' + esc(stLbl) + '</span></td>';
          h += '<td class="num">' + fmtMoney(po.total_amount) + '</td>';
          h += '<td style="text-align:right">';
          if (po.status === "draft") {
            h += '<button type="button" class="ph-compta-btn ph-compta-btn-ghost ph-compta-btn-sm" data-po-receive="' + po.id + '">Recevoir</button>';
          }
          h += '</td></tr>';
        });
      }
      h += '</tbody></table></div>';
      box.innerHTML = h;
      var nb = $("po-new-btn");
      if (nb) nb.addEventListener("click", openNewPO);
    }).catch(function (e) {
      box.innerHTML = '<div class="ph-compta-empty" style="color:#B23C3C">Erreur : ' + esc(e.message) + '</div>';
    });
  }

  function openNewPO() {
    apiCall("GET", "/admin/suppliers").then(function (sups) {
      if (!sups || sups.length === 0) {
        toast("Creez d'abord un fournisseur", "err");
        return;
      }
      var opts = sups.map(function(s){ return '<option value="' + s.id + '">' + esc(s.name) + '</option>'; }).join("");
      var html =
        '<div class="ph-compta-modal-head"><h3>Nouvelle commande d\'achat</h3>' +
        '<button type="button" class="ph-compta-modal-close" data-po-close>&times;</button></div>' +
        '<div class="ph-compta-modal-body">' +
          '<div class="ph-compta-field"><label>Fournisseur *</label><select id="po-sup">' + opts + '</select></div>' +
          '<div class="ph-compta-field" style="margin-top:12px"><label>Notes</label><textarea id="po-notes" rows="2"></textarea></div>' +
        '</div>' +
        '<div class="ph-compta-modal-foot">' +
          '<button type="button" class="ph-compta-btn ph-compta-btn-ghost" data-po-close>Annuler</button>' +
          '<button type="button" class="ph-compta-btn ph-compta-btn-primary" id="po-create-btn">Creer</button>' +
        '</div>';
      showModal(html);
      var cb = $("po-create-btn");
      if (cb) cb.addEventListener("click", function(){
        var sid = parseInt($("po-sup").value, 10);
        var notes = ($("po-notes").value || "").trim();
        apiCall("POST", "/admin/purchase-orders", {supplier_id: sid, notes: notes})
          .then(function(){
            closeModal();
            toast("Commande creee", "ok");
            loadPurchaseOrders();
          }).catch(function(e){ toast(e.message, "err"); });
      });
    });
  }

  // ============================================================
  // STOCK : VALORISATION + PREVISIONS
  // ============================================================
  function loadValuation() {
    var box = $("ph-stock-valuation");
    if (!box) return;
    box.innerHTML = '<div class="ph-compta-empty">Chargement...</div>';
    apiCall("GET", "/admin/stock/valuation").then(function (d) {
      var h = '<div class="ph-compta-kpis">' +
        '<div class="ph-compta-kpi"><strong>' + fmtMoney(d.total_purchase) + '</strong><small>Valeur achat</small></div>' +
        '<div class="ph-compta-kpi ok"><strong>' + fmtMoney(d.total_sell) + '</strong><small>Valeur vente</small></div>' +
        '<div class="ph-compta-kpi ' + ((d.potential_margin >= 0) ? 'ok' : 'danger') + '"><strong>' + fmtMoney(d.potential_margin) + '</strong><small>Marge potentielle</small></div>' +
        '</div>';
      var items = (d.items || []).filter(function(i){ return i.quantity > 0; });
      if (items.length > 0) {
        h += '<div class="ph-compta-table-wrap" style="margin-top:16px"><table class="ph-compta-table"><thead>';
        h += '<tr><th>Produit</th><th style="text-align:right">Qte</th><th style="text-align:right">Prix achat</th><th style="text-align:right">Prix vente</th><th style="text-align:right">Valeur</th></tr></thead><tbody>';
        items.slice(0, 50).forEach(function(it){
          h += '<tr><td>' + esc(it.name) + '</td>';
          h += '<td class="num">' + it.quantity + '</td>';
          h += '<td class="num">' + (it.purchase_price ? fmtMoney(it.purchase_price) : "—") + '</td>';
          h += '<td class="num">' + fmtMoney(it.sell_price) + '</td>';
          h += '<td class="num">' + fmtMoney(it.value_purchase) + '</td></tr>';
        });
        h += '</tbody></table></div>';
      } else {
        h += '<p class="ph-compta-empty">Aucun produit en stock</p>';
      }
      box.innerHTML = h;
    }).catch(function (e) {
      box.innerHTML = '<div class="ph-compta-empty" style="color:#B23C3C">Erreur : ' + esc(e.message) + '</div>';
    });
  }

  function loadForecast() {
    var box = $("ph-stock-forecast");
    if (!box) return;
    box.innerHTML = '<div class="ph-compta-empty">Chargement...</div>';
    apiCall("GET", "/admin/stock/forecast?days=30").then(function (d) {
      var items = (d.items || []).filter(function(i){ return i.sold_period > 0 || i.urgent; });
      if (items.length === 0) {
        box.innerHTML = '<div class="ph-compta-empty">Pas assez de donnees de vente pour prevoir</div>';
        return;
      }
      var h = '<div class="ph-compta-table-wrap"><table class="ph-compta-table"><thead>';
      h += '<tr><th>Produit</th><th style="text-align:right">Stock</th><th style="text-align:right">Vendus (30j)</th><th style="text-align:right">Jours restants</th><th style="text-align:right">Reappro</th></tr></thead><tbody>';
      items.sort(function(a,b){
        var da = a.days_left === null ? 9999 : a.days_left;
        var db = b.days_left === null ? 9999 : b.days_left;
        return da - db;
      });
      items.slice(0, 30).forEach(function(it){
        var daysTxt = it.days_left !== null ? (it.days_left + " j") : "—";
        var daysCls = (it.urgent) ? "neg" : "";
        h += '<tr>';
        h += '<td>' + esc(it.name) + (it.urgent ? ' <span style="color:#B23C3C;font-weight:800;font-size:11px">⚠ URGENT</span>' : '') + '</td>';
        h += '<td class="num">' + it.stock + '</td>';
        h += '<td class="num">' + it.sold_period + '</td>';
        h += '<td class="num ' + daysCls + '">' + daysTxt + '</td>';
        h += '<td class="num">' + (it.reorder_qty ? ("+" + it.reorder_qty) : "—") + '</td>';
        h += '</tr>';
      });
      h += '</tbody></table></div>';
      box.innerHTML = h;
    }).catch(function (e) {
      box.innerHTML = '<div class="ph-compta-empty" style="color:#B23C3C">Erreur : ' + esc(e.message) + '</div>';
    });
  }

  // ============================================================
  // Modal global
  // ============================================================
  function showModal(html) {
    var back = $("ph-compta-modal");
    if (!back) return;
    back.querySelector(".ph-compta-modal").innerHTML = html;
    back.classList.add("show");
    back.querySelectorAll("[data-po-close]").forEach(function(b){
      b.addEventListener("click", closeModal);
    });
    back.addEventListener("click", function(ev){
      if (ev.target === back) closeModal();
    });
  }
  function closeModal() {
    var back = $("ph-compta-modal");
    if (back) back.classList.remove("show");
  }

  // ============================================================
  // TABS
  // ============================================================
  function showTab(name) {
    currentTab = name;
    document.querySelectorAll(".ph-compta-tab").forEach(function(t){
      t.classList.toggle("active", t.getAttribute("data-compta-tab") === name);
    });
    document.querySelectorAll(".ph-compta-panel").forEach(function(p){
      p.classList.toggle("active", p.getAttribute("data-compta-panel") === name);
    });
    if (name === "direction") loadDirection();
    if (name === "bilan") loadBilan();
    if (name === "expenses") loadExpenses();
    if (name === "journal") loadJournal();
  }

  // ============================================================
  // EVENT DELEGATION
  // ============================================================
  document.addEventListener("click", function (ev) {
    var t = ev.target;
    var tab = t.closest ? t.closest("[data-compta-tab]") : null;
    if (tab) {
      ev.preventDefault();
      showTab(tab.getAttribute("data-compta-tab"));
      return;
    }
    // Nav principale : ouvrir compta
    var navTab = t.closest ? t.closest("[data-ph-tab]") : null;
    if (navTab) {
      var tn = navTab.getAttribute("data-ph-tab");
      if (tn === "compta") setTimeout(function(){ showTab(currentTab || "direction"); }, 150);
    }
    // Supprimer depense
    var delExp = t.closest ? t.closest("[data-del-exp]") : null;
    if (delExp) {
      ev.preventDefault();
      var eid = delExp.getAttribute("data-del-exp");
      if (confirm("Supprimer cette depense ?")) {
        apiCall("DELETE", "/compta/expenses/" + eid).then(function(){
          toast("Depense supprimee", "ok");
          loadExpenses();
        }).catch(function(e){ toast(e.message, "err"); });
      }
      return;
    }
    // Supprimer fournisseur
    var delSup = t.closest ? t.closest("[data-del-sup]") : null;
    if (delSup) {
      ev.preventDefault();
      var sid = delSup.getAttribute("data-del-sup");
      if (confirm("Archiver ce fournisseur ?")) {
        apiCall("DELETE", "/admin/suppliers/" + sid).then(function(){
          toast("Fournisseur archive", "ok");
          loadSuppliers();
        }).catch(function(e){ toast(e.message, "err"); });
      }
      return;
    }
    // Recevoir commande achat
    var recv = t.closest ? t.closest("[data-po-receive]") : null;
    if (recv) {
      ev.preventDefault();
      var poid = recv.getAttribute("data-po-receive");
      if (confirm("Recevoir cette commande ? Le stock sera mis a jour et la depense enregistree.")) {
        apiCall("PATCH", "/admin/purchase-orders/" + poid + "/receive", { update_stock: true, create_lots: true })
          .then(function(d){
            toast("Commande receptionnee (" + d.received + " articles)", "ok");
            loadPurchaseOrders();
          }).catch(function(e){ toast(e.message, "err"); });
      }
      return;
    }
    // Export CSV
    if (t.id === "ph-compta-export-btn") {
      ev.preventDefault();
      window.open("/api/compta/export.csv?month=" + encodeURIComponent(currentMonth), "_blank");
      return;
    }
  });

  // Changement de mois
  document.addEventListener("change", function (ev) {
    if (ev.target && ev.target.id === "ph-compta-month") {
      currentMonth = ev.target.value;
      if (currentTab === "bilan") loadBilan();
      else if (currentTab === "expenses") loadExpenses();
      else if (currentTab === "journal") loadJournal();
    }
  });

  // Init quand on ouvre compta
  document.addEventListener("DOMContentLoaded", function () {
    setTimeout(function () {
      if (document.body.getAttribute("data-active-page") === "compta") {
        showTab("direction");
      }
    }, 400);
  });

  window.phLoadCompta = loadDirection;
  window.phLoadSuppliers = loadSuppliers;
  window.phLoadPurchaseOrders = loadPurchaseOrders;
  window.phLoadValuation = loadValuation;
  window.phLoadForecast = loadForecast;
})();
