var API = "/api";

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

var STATUS_LABELS = {
  en_attente: "En attente",
  confirmee: "Confirmee",
  en_preparation: "En preparation",
  prete: "Prete",
  terminee: "Terminee",
  refusee: "Refusee"
};

var NEXT_ACTIONS = {
  en_attente: [
    { label: "Confirmer", next: "confirmee", kind: "primary" },
    { label: "Refuser", next: "refusee", kind: "danger" }
  ],
  confirmee: [
    { label: "Preparer", next: "en_preparation", kind: "primary" },
    { label: "Refuser", next: "refusee", kind: "danger" }
  ],
  en_preparation: [
    { label: "Prete", next: "prete", kind: "primary" },
    { label: "Refuser", next: "refusee", kind: "danger" }
  ],
  prete: [
    { label: "Terminee", next: "terminee", kind: "primary" },
    { label: "En livraison", next: "en_livraison", kind: "primary" },
  ],
  "en_livraison": [
    { label: "Terminee", next: "terminee", kind: "primary" }
  ],
  terminee: [],
  refusee: []
};

var state = { orders: [], filter: "" };

function $(sel){ return document.querySelector(sel); }

function el(tag, cls, txt){
  var n = document.createElement(tag);
  if (cls) n.className = cls;
  if (txt !== undefined && txt !== null) n.textContent = txt;
  return n;
}

function formatDate(iso){
  if (!iso) return "";
  var d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  var pad = function(n){ return n < 10 ? "0" + n : "" + n; };
  return pad(d.getDate()) + "/" + pad(d.getMonth()+1) + "/" + d.getFullYear()
    + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
}

function loadOrders(){
  return fetch(API + "/orders").then(function(r){
    if (!r.ok) throw new Error("Erreur serveur");
    return r.json();
  }).then(function(list){
    state.orders = list;
    render();
  });
}

function changeStatus(reference, newStatus){
  return fetch(API + "/orders/" + encodeURIComponent(reference) + "/status", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: newStatus })
  }).then(function(r){
    return r.json().then(function(body){
      if (!r.ok){
        var msg = typeof body.detail === "string" ? body.detail : "Mise a jour impossible";
        throw new Error(msg);
      }
      return body;
    });
  });
}

function computeStats(){
  var s = { en_attente:0, en_preparation:0, prete:0, total: state.orders.length };
  state.orders.forEach(function(o){
    if (o.status === "en_attente") s.en_attente++;
    else if (o.status === "en_preparation") s.en_preparation++;
    else if (o.status === "prete") s.prete++;
  });
  return s;
}

function renderStats(){
  var s = computeStats();
  $("#stat-pending").textContent = s.en_attente;
  $("#stat-preparing").textContent = s.en_preparation;
  $("#stat-ready").textContent = s.prete;
  $("#stat-total").textContent = s.total;
}

function renderFilters(){
  var box = $("#status-filters");
  box.innerHTML = "";
  var options = [["", "Toutes"]];
  Object.keys(STATUS_LABELS).forEach(function(k){
    options.push([k, STATUS_LABELS[k]]);
  });
  options.forEach(function(pair){
    var active = state.filter === pair[0] ? " chip-active" : "";
    var chip = el("button", "chip" + active, pair[1]);
    chip.type = "button";
    chip.addEventListener("click", function(){
      state.filter = pair[0];
      render();
    });
    box.appendChild(chip);
  });
}

function actionButton(label, nextStatus, kind, ref){
  var cls = "btn ";
  if (kind === "danger") cls += "btn-danger";
  else if (kind === "primary") cls += "btn-primary";
  else cls += "btn-ghost";
  var btn = el("button", cls, label);
  btn.type = "button";
  btn.addEventListener("click", function(){
    btn.disabled = true;
    btn.textContent = "...";
    changeStatus(ref, nextStatus).then(function(){
      return loadOrders();
    }).catch(function(err){
      alert(err.message || "Erreur");
      btn.disabled = false;
      btn.textContent = label;
    });
  });
  return btn;
}

function orderCard(o){
  var card = el("article", "order-card");

  var head = el("div", "order-head");
  var left = el("div");
  left.appendChild(el("div", "order-ref", o.reference));
  left.appendChild(el("div", "order-date", formatDate(o.created_at)));
  var badge = el("span", "status-badge status-" + o.status,
                 STATUS_LABELS[o.status] || o.status);
  head.appendChild(left);
  head.appendChild(badge);
  card.appendChild(head);

  var dl = el("dl", "order-body");
  function row(label, value){
    dl.appendChild(el("dt", null, label));
    dl.appendChild(el("dd", null, value));
  }
  row("Client", o.customer_name);
  row("Telephone", o.phone);
  row("Produit", o.product_name);
  row("Quantite", o.quantity);
  row("Mode", o.delivery_mode === "livraison" ? "Livraison" : "Retrait");
  var _qty = Number(o.quantity) || 1;
  var _price = Number(o.price) || 0;
  var _subtotal = (o.subtotal !== undefined && o.subtotal !== null)
    ? Number(o.subtotal) : (_price * _qty);
  var _fee = Number(o.delivery_fee || 0);
  var _total = (o.total !== undefined && o.total !== null)
    ? Number(o.total) : (_subtotal + _fee);
  row("Sous-total", Math.round(_subtotal).toLocaleString("fr-FR") + " FCFA");
  row("Livraison", Math.round(_fee).toLocaleString("fr-FR") + " FCFA");
  row("Total", Math.round(_total).toLocaleString("fr-FR") + " FCFA");
  if (o.delivery_mode === "livraison" && o.address) row("Adresse", o.address);
  card.appendChild(dl);

  var presc = el("div", "order-prescription");
  if (o.prescription_file){
    var link = el("a", "btn btn-ghost", "Voir l'ordonnance");
    link.href = "/uploads/" + o.prescription_file;
    link.target = "_blank";
    link.rel = "noopener";
    presc.appendChild(link);
  } else {
    presc.appendChild(el("span", "muted small", "Aucune ordonnance jointe"));
  }
  card.appendChild(presc);

  if (o.latitude !== null && o.latitude !== undefined &&
      o.longitude !== null && o.longitude !== undefined) {
    var geo = el("div", "order-geo");
    var mapLink = el("a", "btn btn-ghost", "📍 Voir la localisation");
    mapLink.href = "https://www.google.com/maps?q=" + o.latitude + "," + o.longitude;
    mapLink.target = "_blank";
    mapLink.rel = "noopener";
    geo.appendChild(mapLink);
    if (o.location_accuracy !== null && o.location_accuracy !== undefined) {
      geo.appendChild(el("span", "muted small",
        "Precision ± " + Math.round(o.location_accuracy) + " m"));
    }
    card.appendChild(geo);
  } else if (o.delivery_mode === "livraison") {
    card.appendChild(el("div", "muted small", "Localisation non fournie"));
  }

  if (o.delivery_mode === "livraison") {
    var driverBox = el("div", "order-driver");
    var driverBtn = el("button", "btn btn-primary", "\uD83D\uDE9A Envoyer au livreur");
    driverBtn.type = "button";
    driverBtn.addEventListener("click", function () { openDriverModal(o); });
    driverBox.appendChild(driverBtn);

    card.appendChild(driverBox);
  }

  var actions = NEXT_ACTIONS[o.status] || [];
  if (actions.length > 0){
    var actBox = el("div", "order-actions");
    actions.forEach(function(a){
      actBox.appendChild(actionButton(a.label, a.next, a.kind, o.reference));
    });
    card.appendChild(actBox);
  }

  return card;
}

var driversCache = null;

function formatPhoneDisplay(raw) {
  return String(raw || "").replace(/\D/g, "");
}

function normalizePhone(raw) {
  var DEFAULT_COUNTRY_CODE = "228";
  if (!raw) return "";
  var s = String(raw).trim();
  var hasPlus = s.charAt(0) === "+";
  s = s.replace(/\D/g, "");
  if (!s) return "";
  if (hasPlus && s.indexOf(DEFAULT_COUNTRY_CODE) === 0) return s;
  if (s.indexOf(DEFAULT_COUNTRY_CODE) === 0) return s;
  if (s.charAt(0) === "0") s = s.substring(1);
  return DEFAULT_COUNTRY_CODE + s;
}

function buildWhatsappMessage(o) {
  var lines = [];
  lines.push("\uD83D\uDCE6 LIVRAISON \u2014 " + o.reference);
  lines.push("");
  lines.push("\uD83D\uDC64 Client : " + (o.customer_name || ""));
  lines.push("\uD83D\uDCDE T\u00E9l\u00E9phone client : " + (o.phone || ""));
  lines.push("\uD83D\uDC8A Produit : " + (o.product_name || "") + " \u00D7 " + (o.quantity || 1));

  var qty = Number(o.quantity) || 1;
  var price = Number(o.price) || 0;
  var subtotal = (o.subtotal !== undefined && o.subtotal !== null)
    ? Number(o.subtotal) : (price * qty);
  var fee = Number(o.delivery_fee) || 0;
  var total = (o.total !== undefined && o.total !== null)
    ? Number(o.total) : (subtotal + fee);

  lines.push("\uD83D\uDCB5 Sous-total : " + Math.round(subtotal).toLocaleString("fr-FR") + " FCFA");
  lines.push("\uD83D\uDE9A Livraison : " + Math.round(fee).toLocaleString("fr-FR") + " FCFA");
  lines.push("\uD83D\uDCB0 TOTAL : " + Math.round(total).toLocaleString("fr-FR") + " FCFA");
  lines.push("");

  var addr = String(o.address || "").trim();
  lines.push("\uD83D\uDCCD Adresse :");
  lines.push(addr ? addr : "Non renseign\u00E9e");
  lines.push("");

  lines.push("\uD83D\uDDFA\uFE0F Localisation GPS :");
  if (o.latitude !== null && o.latitude !== undefined &&
      o.longitude !== null && o.longitude !== undefined) {
    lines.push("https://www.google.com/maps?q=" + o.latitude + "," + o.longitude);
  } else {
    lines.push("Non fournie");
  }
  return lines.join("\n");
}


function openDriverModal(order) {
  var modal = document.getElementById("driver-modal");
  if (!modal) return;
  modal.classList.remove("hidden");
  modal._order = order;
  modal._selectedDriver = null;

  var selectedBox = document.getElementById("driver-selected");
  if (selectedBox) { selectedBox.classList.add("hidden"); selectedBox.innerHTML = ""; }
  var sendBtn = document.getElementById("driver-send-btn");
  if (sendBtn) sendBtn.classList.add("hidden");

  loadDrivers();
}

function loadDrivers() {
  var list = document.getElementById("driver-list");
  if (!list) return;
  list.innerHTML = '<div class="muted small" style="padding:14px;text-align:center">Chargement...</div>';
  fetch(API + "/drivers").then(function(r) {
    if (!r.ok) throw new Error("Erreur serveur");
    return r.json();
  }).then(function(drivers) {
    driversCache = drivers;
    renderDriversList(drivers);
  }).catch(function() {
    list.innerHTML = '<div class="muted small" style="padding:14px;text-align:center">Erreur de chargement.</div>';
  });
}

function renderDriversList(drivers) {
  var list = document.getElementById("driver-list");
  list.innerHTML = "";
  if (!drivers || drivers.length === 0) {
    list.appendChild(el("div", "muted small", "Aucun livreur actif n'est enregistr\u00E9."));
    return;
  }
  drivers.forEach(function(d) {
    var row = el("div", "driver-row");
    var radio = document.createElement("input");
    radio.type = "radio";
    radio.name = "driver-choice";
    radio.value = String(d.id);
    radio.id = "driver-" + d.id;

    var label = el("label", "driver-label");
    label.htmlFor = "driver-" + d.id;
    label.appendChild(el("span", "driver-name", d.name));
    label.appendChild(el("span", "driver-phone", formatPhoneDisplay(d.phone)));

    row.appendChild(radio);
    row.appendChild(label);

    row.addEventListener("click", function(ev) {
      if (ev.target !== radio) radio.checked = true;
      selectDriver(d);
    });

    list.appendChild(row);
  });
}

function selectDriver(d) {
  var modal = document.getElementById("driver-modal");
  if (!modal) return;
  modal._selectedDriver = d;

  var selectedBox = document.getElementById("driver-selected");
  if (selectedBox) {
    selectedBox.classList.remove("hidden");
    selectedBox.innerHTML = "";
    selectedBox.appendChild(el("div", "muted small", "Livreur s\u00E9lectionn\u00E9"));
    selectedBox.appendChild(el("div", "driver-selected-name",
      "\uD83D\uDE9A " + d.name + " \u2014 " + formatPhoneDisplay(d.phone)));
  }
  var sendBtn = document.getElementById("driver-send-btn");
  if (sendBtn) sendBtn.classList.remove("hidden");
}

function openWhatsappForDriver(order, driver) {
  var phone = normalizePhone(driver.phone);
  if (!phone || phone.length < 8) {
    alert("Num\u00E9ro du livreur invalide.");
    return;
  }
  var message = buildWhatsappMessage(order);
  var url = "https://wa.me/" + phone + "?text=" + encodeURIComponent(message);
  window.open(url, "_blank", "noopener");

  var selectedBox = document.getElementById("driver-selected");
  if (selectedBox) {
    selectedBox.innerHTML = "";
    selectedBox.appendChild(el("div", "muted small",
      "WhatsApp ouvert pour " + driver.name));
  }
  setTimeout(closeDriverModal, 1400);
}

function closeDriverModal() {
  var modal = document.getElementById("driver-modal");
  if (modal) {
    modal.classList.add("hidden");
    modal._order = null;
    modal._selectedDriver = null;
  }
}

function initDriverModal() {
  var modal = document.getElementById("driver-modal");
  if (!modal) return;

  var closeBtns = modal.querySelectorAll("[data-close-modal]");
  Array.prototype.forEach.call(closeBtns, function(b) {
    b.addEventListener("click", closeDriverModal);
  });

  var sendBtn = document.getElementById("driver-send-btn");
  if (sendBtn) {
    sendBtn.addEventListener("click", function() {
      if (!modal._selectedDriver || !modal._order) return;
      openWhatsappForDriver(modal._order, modal._selectedDriver);
    });
  }
}

function render(){
  renderStats();
  renderFilters();
  var grid = $("#orders-grid");
  grid.innerHTML = "";
  var empty = $("#orders-empty");
  var list = state.orders;
  if (state.filter){
    list = list.filter(function(o){ return o.status === state.filter; });
  }
  if (list.length === 0){
    empty.classList.remove("hidden");
  } else {
    empty.classList.add("hidden");
    list.forEach(function(o){ grid.appendChild(orderCard(o)); });
  }
}

function setLastRefresh(){
  var now = new Date();
  var pad = function(n){ return n < 10 ? "0" + n : "" + n; };
  $("#last-refresh").textContent =
    "Derniere actualisation : "
    + pad(now.getHours()) + ":" + pad(now.getMinutes()) + ":" + pad(now.getSeconds());
}

function refresh(){
    function safeCall(fn) {
      if (typeof fn !== "function") return Promise.resolve();
      return Promise.resolve().then(function () {
        return fn();
      }).catch(function (e) {
        console.warn("[pharmacien] " + fn.name + " error:", e);
      });
    }

    var p1 = safeCall(loadOrders);
    var p2 = safeCall(typeof loadPaymentsDashboard !== "undefined" ? loadPaymentsDashboard : null);
    var p3 = safeCall(typeof loadPrescriptionsDashboard !== "undefined" ? loadPrescriptionsDashboard : null);
    var p4 = safeCall(typeof loadDriversAdmin !== "undefined" ? loadDriversAdmin : null);

    return Promise.all([p1, p2, p3, p4]).then(function () {
      try { setLastRefresh(); } catch (e) {}
    });
  }

function init(){
  initDriverModal();
  $("#refresh-btn").addEventListener("click", function(){
    refresh().catch(function(){ if(window.EHModal) window.EHModal.alert("Erreur","Actualisation impossible","danger"); });
  });
  refresh().catch(function(){});
  // V10 : setInterval retire (SSE gere le temps reel, evite les reloads visuels)
}


// ====== V2.3 Admin livreurs + settings ======

function loadSettingsDashboard() {
  fetch(API + "/settings").then(function (r) {
    if (!r.ok) throw new Error("settings");
    return r.json();
  }).then(function (s) {
    function setVal(id, v, digits) {
      var el = document.getElementById(id);
      if (!el) return;
      if (v === null || v === undefined || v === "") { el.value = ""; return; }
      el.value = digits !== undefined ? Number(v).toFixed(digits) : String(Math.round(Number(v)));
    }
    setVal("fallback-fee-input", s.delivery_fee_default);
    setVal("base-fee-input", s.delivery_base_fee);
    setVal("per-km-input", s.delivery_price_per_km);
    setVal("max-km-input", s.delivery_max_km);
    setVal("ph-lat-input", s.pharmacy_latitude, 5);
    setVal("ph-lon-input", s.pharmacy_longitude, 5);
    var waEl = document.getElementById("whatsapp-input");
    if (waEl) waEl.value = s.whatsapp_number || "";

    function setField(id, v) {
      var el = document.getElementById(id);
      if (!el) return;
      el.value = (v === null || v === undefined) ? "" : String(Math.round(Number(v)));
    }
    setField("car-base-fee", s.car_base_fee);
    setField("car-price-per-km", s.car_price_per_km);
    setField("car-minimum-fee", s.car_minimum_fee);
    setField("moto-base-fee", s.motorbike_base_fee);
    setField("moto-price-per-km", s.motorbike_price_per_km);
    setField("moto-minimum-fee", s.motorbike_minimum_fee);

    var pnum = document.getElementById("payment-number-input");
    if (pnum) pnum.value = s.payment_number || "";
    var pname = document.getElementById("payment-name-input");
    if (pname) pname.value = s.payment_name || "";

    // Sprint A.8 : seuils livraison intelligente
    var _das = document.getElementById("delivery-auto-switch");
    if (_das) _das.checked = (s.delivery_auto_switch === 1 || s.delivery_auto_switch === true);
    var _tu = document.getElementById("threshold-units");
    if (_tu) _tu.value = (s.threshold_units != null ? s.threshold_units : 40);
    var _tl = document.getElementById("threshold-lines");
    if (_tl) _tl.value = (s.threshold_distinct_lines != null ? s.threshold_distinct_lines : 10);
    var _ta = document.getElementById("threshold-amount");
    if (_ta) _ta.value = (s.threshold_amount != null ? s.threshold_amount : 80000);
  }).catch(function () {});
}


  function str(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    var v = String(el.value || "").trim();
    return v === "" ? null : v;
  }

function submitSettings(ev) {
  ev.preventDefault();
  var status = document.getElementById("settings-status");

  function num(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    var raw = String(el.value).trim();
    if (raw === "") return null;
    var n = Number(raw);
    return isNaN(n) ? null : n;
  }

  var _das = document.getElementById("delivery-auto-switch");
  var payload = {
    delivery_fee_default: num("fallback-fee-input"),
    delivery_base_fee: num("base-fee-input"),
    delivery_price_per_km: num("per-km-input"),
    delivery_max_km: num("max-km-input"),
    pharmacy_latitude: num("ph-lat-input"),
    pharmacy_longitude: num("ph-lon-input"),
    // Sprint A.8 : seuils
    delivery_auto_switch: (_das && _das.checked) ? 1 : 0,
    threshold_units: num("threshold-units"),
    threshold_distinct_lines: num("threshold-lines"),
    threshold_amount: num("threshold-amount"),
    // Tarifs VOITURE
    car_base_fee: num("car-base-fee"),
    car_price_per_km: num("car-price-per-km"),
    car_minimum_fee: num("car-minimum-fee"),
    // Tarifs MOTO
    motorbike_base_fee: num("moto-base-fee"),
    motorbike_price_per_km: num("moto-price-per-km"),
    motorbike_minimum_fee: num("moto-minimum-fee"),
    // Paiement
    payment_number: str("payment-number-input"),
    payment_name: str("payment-name-input"),
    // WhatsApp
    whatsapp_number: str("whatsapp-input")
  };
  Object.keys(payload).forEach(function (k) {
    if (payload[k] === null) delete payload[k];
  });

  fetch(API + "/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  }).then(function (r) {
    return r.json().then(function (body) {
      if (!r.ok) throw new Error(body.detail || "Erreur");
      return body;
    });
  }).then(function () {
    if (status) {
      status.textContent = "\u2713 Param\u00E8tres enregistr\u00E9s";
      setTimeout(function () { status.textContent = ""; }, 3000);
    }
    loadSettingsDashboard();
  }).catch(function (err) {
    if (status) status.textContent = err.message || "Erreur";
  });
}


function loadDriversAdmin() {
  var list = document.getElementById("drivers-admin-list");
  if (!list) return;
  list.innerHTML = '<div class="muted small" style="padding:8px">Chargement...</div>';
  fetch(API + "/drivers?include_inactive=1").then(function (r) {
    if (!r.ok) throw new Error("drivers");
    return r.json();
  }).then(function (drivers) {
    list.innerHTML = "";
    if (!drivers || drivers.length === 0) {
      list.appendChild(el("div", "muted small", "Aucun livreur enregistr\u00E9."));
      return;
    }
    drivers.forEach(function (d) { list.appendChild(driverAdminRow(d)); });
  }).catch(function () {
    list.innerHTML = '<div class="muted small" style="padding:8px">Erreur de chargement.</div>';
  });
}

function driverAdminRow(d) {
  var row = el("div", "driver-admin-row");
  var info = el("div", "driver-admin-info");
  info.appendChild(el("div", "driver-admin-name", d.name));
  info.appendChild(el("div", "driver-admin-phone", String(d.phone || "").replace(/\D/g, "")));
  var badge = el("span", "driver-admin-status " + (d.is_active ? "status-active" : "status-inactive"),
                 d.is_active ? "\uD83D\uDFE2 Actif" : "\uD83D\uDD34 Inactif");
  var btn = el("button", "btn " + (d.is_active ? "btn-ghost" : "btn-primary"),
               d.is_active ? "Desactiver" : "Activer");
  btn.type = "button";
  btn.addEventListener("click", function () {
    btn.disabled = true;
    toggleDriver(d.id, !d.is_active).then(function () {
      loadDriversAdmin();
    }).catch(function () {
      btn.disabled = false;
      alert("Erreur");
    });
  });
  row.appendChild(info);
  row.appendChild(badge);
  row.appendChild(btn);
  return row;
}

function toggleDriver(id, newActive) {
  return fetch(API + "/drivers/" + id, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_active: !!newActive })
  }).then(function (r) {
    if (!r.ok) throw new Error("toggle");
    return r.json();
  });
}

function openAddDriverModal() {
  var modal = document.getElementById("add-driver-modal");
  if (!modal) return;
  modal.classList.remove("hidden");
  var form = document.getElementById("add-driver-form");
  if (form) form.reset();
  var err = document.getElementById("add-driver-error");
  if (err) { err.classList.add("hidden"); err.textContent = ""; }
  setTimeout(function () {
    var n = document.getElementById("new-driver-name");
    if (n) n.focus();
  }, 60);
}

function closeAddDriverModal() {
  var modal = document.getElementById("add-driver-modal");
  if (modal) modal.classList.add("hidden");
}

function submitNewDriver(ev) {
  ev.preventDefault();
  var nameEl = document.getElementById("new-driver-name");
  var phoneEl = document.getElementById("new-driver-phone");
  var errEl = document.getElementById("add-driver-error");
  var name = (nameEl.value || "").trim();
  var phone = (phoneEl.value || "").replace(/\D/g, "");
  if (!name) {
    errEl.textContent = "Le nom est obligatoire.";
    errEl.classList.remove("hidden");
    return;
  }
  if (phone.length < 6) {
    errEl.textContent = "Numero de telephone invalide.";
    errEl.classList.remove("hidden");
    return;
  }
  fetch(API + "/drivers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: name, phone: phone })
  }).then(function (r) {
    return r.json().then(function (body) {
      if (!r.ok) throw new Error(body.detail || "Erreur");
      return body;
    });
  }).then(function () {
    closeAddDriverModal();
    loadDriversAdmin();
  }).catch(function (err) {
    errEl.textContent = err.message || "Erreur";
    errEl.classList.remove("hidden");
  });
}

function initAdmin() {
  var addBtn = document.getElementById("add-driver-btn");
  if (addBtn) addBtn.addEventListener("click", openAddDriverModal);

  var settingsForm = document.getElementById("settings-form");
  if (settingsForm) settingsForm.addEventListener("submit", submitSettings);

  var addForm = document.getElementById("add-driver-form");
  if (addForm) addForm.addEventListener("submit", submitNewDriver);

  var modal = document.getElementById("add-driver-modal");
  if (modal) {
    var closeEls = modal.querySelectorAll("[data-close-add-driver]");
    Array.prototype.forEach.call(closeEls, function (b) {
      b.addEventListener("click", closeAddDriverModal);
    });
  }

  loadDriversAdmin();
  loadSettingsDashboard();
}

document.addEventListener("DOMContentLoaded", initAdmin);

document.addEventListener("DOMContentLoaded", init);

function initPharmacyGeo() {
  var btn = document.getElementById("ph-geo-btn");
  if (!btn) return;
  btn.addEventListener("click", function () {
    if (!navigator.geolocation) {
      alert("Geolocalisation indisponible sur ce navigateur.");
      return;
    }
    btn.disabled = true;
    btn.textContent = "\u23F3 Localisation...";
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        var lat = document.getElementById("ph-lat-input");
        var lon = document.getElementById("ph-lon-input");
        if (lat) lat.value = pos.coords.latitude.toFixed(5);
        if (lon) lon.value = pos.coords.longitude.toFixed(5);
        btn.disabled = false;
        btn.innerHTML = "\uD83D\uDCCD Utiliser ma position";
      },
      function () {
        btn.disabled = false;
        btn.innerHTML = "\uD83D\uDCCD Utiliser ma position";
        alert("Localisation indisponible. Autorisez la geolocalisation puis reessayez.");
      },
      { enableHighAccuracy: true, timeout: 20000, maximumAge: 60000 }
    );
  });
}
document.addEventListener("DOMContentLoaded", initPharmacyGeo);


// ====== V3 : Paiements ======
function loadPaymentsDashboard() {
  var box = document.getElementById("payments-admin-list");
  if (!box) return;
  box.innerHTML = '<div class="muted small" style="padding:8px">Chargement...</div>';
  fetch(API + "/payments?status=PROOF_SUBMITTED").then(function (r) {
    if (!r.ok) throw new Error("payments");
    return r.json();
  }).then(function (list) {
    box.innerHTML = "";
    if (!list || list.length === 0) {
      box.appendChild(el("div", "muted small", "Aucune preuve en attente."));
      return;
    }
    list.forEach(function (p) { box.appendChild(paymentAdminRow(p)); });
  }).catch(function () {
    box.innerHTML = '<div class="muted small" style="padding:8px">Erreur de chargement.</div>';
  });
}

function paymentAdminRow(p) {
  var row = el("div", "payment-admin-row");
  var info = el("div", "payment-admin-info");
  info.appendChild(el("div", "payment-admin-ref", p.order_reference));
  info.appendChild(el("div", "payment-admin-meta",
    (p.customer_name || "") + " - " + Math.round(p.total || 0).toLocaleString("fr-FR") + " FCFA"));
  info.appendChild(el("div", "payment-admin-method", p.payment_method));
  var link = el("a", "btn btn-ghost", "Voir preuve");
  link.href = p.proof_file;
  link.target = "_blank"; link.rel = "noopener";
  var ok = el("button", "btn btn-primary", "Valider");
  ok.type = "button";
  ok.addEventListener("click", function () {
    if (!confirm("Confirmer que le paiement de " + p.order_reference + " a bien ete recu ?")) return;
    fetch(API + "/payments/" + p.id + "/verify", { method: "PATCH" })
      .then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(loadPaymentsDashboard).catch(function () { alert("Erreur"); });
  });
  var ko = el("button", "btn-danger", "Refuser");
  ko.type = "button";
  ko.addEventListener("click", function () {
    var reason = prompt("Motif du refus :");
    if (!reason) return;
    fetch(API + "/payments/" + p.id + "/reject", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rejection_reason: reason })
    }).then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(loadPaymentsDashboard).catch(function () { alert("Erreur"); });
  });
  var actions = el("div", "payment-admin-actions");
  actions.appendChild(link);
  actions.appendChild(ok);
  actions.appendChild(ko);
  row.appendChild(info);
  row.appendChild(actions);
  return row;
}

document.addEventListener("DOMContentLoaded", function () {
  setTimeout(loadPaymentsDashboard, 300);
});


// ====== V3 : Ordonnances ======
function loadPrescriptionsDashboard() {
  var box = document.getElementById("prescriptions-admin-list");
  if (!box) return;
  box.innerHTML = '<div class="muted small" style="padding:8px">Chargement...</div>';
  fetch(API + "/prescriptions?status=PENDING").then(function (r) {
    if (!r.ok) throw new Error();
    return r.json();
  }).then(function (list) {
    box.innerHTML = "";
    if (!list || list.length === 0) {
      box.appendChild(el("div", "muted small", "Aucune ordonnance en attente."));
      return;
    }
    list.forEach(function (p) { box.appendChild(prescAdminRow(p)); });
  }).catch(function () {
    box.innerHTML = '<div class="muted small" style="padding:8px">Erreur de chargement.</div>';
  });
}

function prescAdminRow(p) {
  var row = el("div", "presc-admin-row");
  var info = el("div", "presc-admin-info");
  info.appendChild(el("div", "presc-admin-ref", p.order_reference));
  info.appendChild(el("div", "presc-admin-meta", (p.customer_name || "") + " - " + (p.phone || "")));
  var link = el("a", "btn btn-ghost", "Voir l'ordonnance");
  link.href = p.file_path; link.target = "_blank"; link.rel = "noopener";
  var ok = el("button", "btn btn-primary", "Approuver");
  ok.type = "button";
  ok.addEventListener("click", function () {
    if (!confirm("Approuver cette ordonnance ?")) return;
    fetch(API + "/prescriptions/" + p.id + "/review", {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "APPROVED", comment: "" })
    }).then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(loadPrescriptionsDashboard).catch(function () { alert("Erreur"); });
  });
  var ko = el("button", "btn-danger", "Refuser");
  ko.type = "button";
  ko.addEventListener("click", function () {
    var reason = prompt("Motif du refus :");
    if (!reason) return;
    fetch(API + "/prescriptions/" + p.id + "/review", {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "REJECTED", comment: reason })
    }).then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(loadPrescriptionsDashboard).catch(function () { alert("Erreur"); });
  });
  var review = el("button", "btn btn-ghost", "A revoir");
  review.type = "button";
  review.addEventListener("click", function () {
    var reason = prompt("Message pour le patient :", "Merci de renvoyer une photo plus nette.");
    if (!reason) return;
    fetch(API + "/prescriptions/" + p.id + "/review", {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "NEEDS_REVIEW", comment: reason })
    }).then(function (r) { if (!r.ok) throw new Error(); return r.json(); })
      .then(loadPrescriptionsDashboard).catch(function () { alert("Erreur"); });
  });
  var actions = el("div", "presc-admin-actions");
  actions.appendChild(link); actions.appendChild(ok);
  actions.appendChild(review); actions.appendChild(ko);
  row.appendChild(info); row.appendChild(actions);
  return row;
}

document.addEventListener("DOMContentLoaded", function () {
  setTimeout(loadPrescriptionsDashboard, 400);
});


// ====== V3 : Assignation livreur ======
function openAssignModal(order) {
  var modal = document.getElementById("assign-modal");
  if (!modal) return;
  modal.classList.remove("hidden");
  modal._order = order;

  var refEl = document.getElementById("assign-ref");
  if (refEl) refEl.textContent = "Commande : " + (order.reference || "");

  var list = document.getElementById("assign-list");
  list.innerHTML = '<div class="muted small" style="padding:14px;text-align:center">Chargement...</div>';

  fetch(API + "/drivers").then(function (r) {
    if (!r.ok) throw new Error();
    return r.json();
  }).then(function (drivers) {
    list.innerHTML = "";
    if (!drivers || drivers.length === 0) {
      list.appendChild(el("div", "muted small", "Aucun livreur actif."));
      return;
    }
    drivers.forEach(function (d) {
      var row = el("div", "assign-row");
      var info = el("div", "assign-info");
      info.appendChild(el("div", "assign-name", d.name));
      info.appendChild(el("div", "assign-phone", String(d.phone || "").replace(/\D/g, "")));
      var btn = el("button", "btn btn-primary", "Assigner");
      btn.type = "button";
      btn.addEventListener("click", function () {
        btn.disabled = true;
        btn.textContent = "Assignation...";
        fetch(API + "/orders/" + encodeURIComponent(order.reference) + "/assign", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ driver_id: d.id })
        }).then(function (r) {
          return r.json().then(function (b) {
            if (!r.ok) throw new Error(b.detail || "Erreur");
            return b;
          });
        }).then(function () {
          row.innerHTML = '<div class="assign-info"><div class="assign-name">\u2713 ' +
            d.name + '</div><div class="assign-phone">Livreur assigne</div></div>';
          setTimeout(closeAssignModal, 1000);
        }).catch(function (e) {
          btn.disabled = false;
          btn.textContent = "Assigner";
          alert(e.message);
        });
      });
      row.appendChild(info);
      row.appendChild(btn);
      list.appendChild(row);
    });
  }).catch(function () {
    list.innerHTML = '<div class="muted small" style="padding:14px;text-align:center">Erreur de chargement.</div>';
  });
}

function closeAssignModal() {
  var modal = document.getElementById("assign-modal");
  if (modal) modal.classList.add("hidden");
}

document.addEventListener("DOMContentLoaded", function () {
  var modal = document.getElementById("assign-modal");
  if (!modal) return;
  var closers = modal.querySelectorAll("[data-close-assign]");
  Array.prototype.forEach.call(closers, function (b) {
    b.addEventListener("click", closeAssignModal);
  });
});

/* ============================================================
   TEMPS REEL : ecouter eh:refresh (emis par professional_realtime.js)
   Strategie robuste : click sur #refresh-btn (toujours fonctionnel)
   ============================================================ */
(function () {
  "use strict";

  var _lastRefreshAt = 0;
  var _refreshTimer = null;
  var _refreshCount = 0;

  function triggerRefresh() {
    _refreshCount++;
    console.log("[pharmacien] refresh #" + _refreshCount);

    // Appel direct des fonctions de chargement (pas de dependance a #refresh-btn)
    var promises = [];

    // 1. Dashboard accueil (nouveau module)
    if (typeof window.phLoadHome === "function") {
      try { promises.push(Promise.resolve(window.phLoadHome())); } catch (e) {}
    }

    // 2. Vue Commandes V2 (nouveau module)
    if (typeof window.phLoadOrdersV2 === "function") {
      try { promises.push(Promise.resolve(window.phLoadOrdersV2())); } catch (e) {}
    }

    // 3. Fonctions existantes (paiements, ordonnances, drivers)
    if (typeof loadPaymentsDashboard === "function") {
      try { promises.push(Promise.resolve(loadPaymentsDashboard())); } catch (e) {}
    }
    if (typeof loadPrescriptionsDashboard === "function") {
      try { promises.push(Promise.resolve(loadPrescriptionsDashboard())); } catch (e) {}
    }

    // Pas de Promise.all car les fonctions retournent parfois undefined
    // On ne fait que declencher les chargements en parallele
  }

  function debouncedRefresh() {
    if (_refreshTimer) clearTimeout(_refreshTimer);
    _refreshTimer = setTimeout(function () {
      var now = Date.now();
      if (now - _lastRefreshAt < 500) return;
      _lastRefreshAt = now;
      triggerRefresh();
    }, 300);
  }

  document.addEventListener("eh:refresh", function (ev) {
    console.log("[pharmacien] eh:refresh recu", ev && ev.detail);
    debouncedRefresh();
  });

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible" && Date.now() - _lastRefreshAt > 3000) {
      debouncedRefresh();
    }
  });

  window.addEventListener("focus", function () {
    if (Date.now() - _lastRefreshAt > 3000) {
      debouncedRefresh();
    }
  });
})();

/* ============================================================
   PHARMACIEN V6 - Navigation basse + Dashboard Accueil
   ============================================================ */
(function () {
  "use strict";

  var API = "/api";
  var CURRENT_PAGE = "home";

  function setPage(name) {
    CURRENT_PAGE = name;
    document.body.dataset.activePage = name;
    // Onglet actif
    document.querySelectorAll(".ph-navbar > a").forEach(function (a) {
      a.classList.toggle("active", a.getAttribute("data-ph-tab") === name);
    });
    // Scroll top
    window.scrollTo(0, 0);
    // Si on ouvre une autre page, recharger les donnees
    if (name === "paiements" && typeof window.phLoadPayments === "function") {
      try { window.phLoadPayments(); } catch (e) {}
    } else if (name === "ordonnances" && typeof window.phLoadPrescriptions === "function") {
      try { window.phLoadPrescriptions(); } catch (e) {}
    }
  }

  // Click sur les onglets navbar
  document.addEventListener("click", function (ev) {
    var tab = ev.target.closest ? ev.target.closest("[data-ph-tab]") : null;
    if (tab) {
      ev.preventDefault();
      setPage(tab.getAttribute("data-ph-tab"));
      return;
    }
    var jump = ev.target.closest ? ev.target.closest("[data-ph-jump]") : null;
    if (jump) {
      ev.preventDefault();
      var target = jump.getAttribute("data-ph-jump");
      setPage(target);
    }
  });

  // ============================================================
  // Charger stats + actions + commandes recentes
  // ============================================================
  function loadHome() {
    // /api/orders/mine ou /api/orders selon role - on essaie /api/orders (pharmacien)
    fetch(API + "/orders", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (list) {
        list = Array.isArray(list) ? list : [];
        renderHomeStats(list);
        renderHomeActions(list);
        renderHomeRecent(list);
      })
      .catch(function () {
        var el = document.getElementById("ph-home-recent");
        if (el) el.innerHTML = '<div class="ph-home-empty">Erreur de chargement.</div>';
      });
  }

  function countByStatus(list, status) {
    return list.filter(function (o) { return o.status === status; }).length;
  }

  function renderHomeStats(list) {
    var pending = countByStatus(list, "en_attente");
    var preparing = countByStatus(list, "en_preparation");
    var ready = countByStatus(list, "prete") + countByStatus(list, "en_livraison");
    var total = list.length;

    var el;
    if ((el = document.getElementById("ph-home-stat-pending"))) el.textContent = pending;
    if ((el = document.getElementById("ph-home-stat-preparing"))) el.textContent = preparing;
    if ((el = document.getElementById("ph-home-stat-ready"))) el.textContent = ready;
    if ((el = document.getElementById("ph-home-stat-total"))) el.textContent = total;

    // Badge navbar Commandes = en attente
    var b = document.getElementById("ph-nav-badge-orders");
    if (b) {
      if (pending > 0) {
        b.textContent = pending > 99 ? "99+" : String(pending);
        b.classList.remove("hidden");
      } else {
        b.classList.add("hidden");
      }
    }
  }

  function renderHomeActions(list) {
    var pending = countByStatus(list, "en_attente");
    var ordEl = document.getElementById("ph-action-orders-count");
    if (ordEl) ordEl.textContent = pending === 0 ? "Aucune" : (pending + " en attente");

    // Paiements : chercher via API
    fetch(API + "/payments", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (payments) {
        payments = Array.isArray(payments) ? payments : [];
        var toVerify = payments.filter(function (p) {
          return p.status === "PROOF_SUBMITTED";
        }).length;
        var payEl = document.getElementById("ph-action-payments-count");
        if (payEl) payEl.textContent = toVerify === 0 ? "Aucune" : (toVerify + " a valider");
        var badge = document.getElementById("ph-nav-badge-payments");
        if (badge) {
          if (toVerify > 0) {
            badge.textContent = toVerify > 99 ? "99+" : String(toVerify);
            badge.classList.remove("hidden");
          } else {
            badge.classList.add("hidden");
          }
        }
      })
      .catch(function () {});

    // Ordonnances : chercher via API
    fetch(API + "/prescriptions", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (prescs) {
        prescs = Array.isArray(prescs) ? prescs : [];
        var pending = prescs.filter(function (p) {
          return p.status === "PENDING" || p.status === "NEEDS_REVIEW";
        }).length;
        var el = document.getElementById("ph-action-prescriptions-count");
        if (el) el.textContent = pending === 0 ? "Aucune" : (pending + " a verifier");
        var badge = document.getElementById("ph-nav-badge-presc");
        if (badge) {
          if (pending > 0) {
            badge.textContent = pending > 99 ? "99+" : String(pending);
            badge.classList.remove("hidden");
          } else {
            badge.classList.add("hidden");
          }
        }
      })
      .catch(function () {});
  }

  function fmtMoney(v) {
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

  var STATUS_LABELS = {
    en_attente: "En attente",
    confirmee: "Confirmee",
    en_preparation: "En preparation",
    prete: "Prete",
    en_livraison: "En livraison",
    terminee: "Terminee",
    refusee: "Refusee"
  };

  function renderHomeRecent(list) {
    var box = document.getElementById("ph-home-recent");
    if (!box) return;
    if (list.length === 0) {
      box.innerHTML = '<div class="ph-home-empty">Aucune commande.</div>';
      return;
    }
    // Trier par date desc (approx : id desc)
    var sorted = list.slice().sort(function (a, b) {
      return (b.id || 0) - (a.id || 0);
    });
    var top5 = sorted.slice(0, 5);
    box.innerHTML = "";
    top5.forEach(function (o) {
      var a = document.createElement("a");
      a.className = "ph-home-order";
      a.href = "#";
      a.setAttribute("data-ph-jump", "commandes");
      var total = (Number(o.subtotal) || 0) + (Number(o.delivery_fee) || 0);
      var statusLbl = STATUS_LABELS[o.status] || o.status;
      a.innerHTML =
        '<div class="ph-home-order-main">' +
          '<div class="ph-home-order-ref">' + (o.reference || "") + '</div>' +
          '<div class="ph-home-order-meta">' +
            (o.customer_name || "Client") + " &middot; " + statusLbl +
          '</div>' +
        '</div>' +
        '<div class="ph-home-order-total">' + fmtMoney(total) + '</div>';
      box.appendChild(a);
    });
  }

  // Exposer pour refresh depuis SSE
  window.phLoadHome = loadHome;

  // Init : page home par defaut
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      setPage("home");
      loadHome();
    });
  } else {
    setPage("home");
    loadHome();
  }

})();

/* ============================================================
   PHARMACIEN V6 - Vue Commandes (Step 2)
   Recherche + tri + 5 filtres + cartes compactes + actions
   ============================================================ */
(function () {
  "use strict";

  var API = "/api";
  var state2 = {
    orders: [],
    q: "",
    filter: "all",
    sort: "date_desc"
  };

  // Mapping des 5 filtres visuels vers les 7 statuts backend
  var FILTER_MAP = {
    all: null,  // tous
    todo: ["en_attente"],
    progress: ["confirmee", "en_preparation", "prete", "en_livraison"],
    done: ["terminee"],
    refused: ["refusee"]
  };

  var STATUS_LABELS = {
    en_attente: "En attente",
    confirmee: "Confirmee",
    en_preparation: "En preparation",
    prete: "Prete",
    en_livraison: "En livraison",
    terminee: "Terminee",
    refusee: "Refusee"
  };

  var STATUS_PILL = {
    en_attente: "ph-pill-pending",
    confirmee: "ph-pill-confirmed",
    en_preparation: "ph-pill-preparing",
    prete: "ph-pill-ready",
    en_livraison: "ph-pill-in-delivery",
    terminee: "ph-pill-done",
    refusee: "ph-pill-refused"
  };

  function $(id) { return document.getElementById(id); }

  function fmtMoney(v) {
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
      if (isNaN(d.getTime())) return iso;
      var pad = function (n) { return n < 10 ? "0" + n : "" + n; };
      return pad(d.getDate()) + "/" + pad(d.getMonth()+1) + "/" + d.getFullYear()
        + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
    } catch (e) { return iso; }
  }

  function escapeHtml(s) {
    try {
      return String(s == null ? "" : s)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    } catch (e) { return ""; }
  }

  // Normalise un numero pour la recherche
  function normalizePhone(s) {
    return String(s || "").replace(/\D/g, "");
  }

  // Cherche si la commande match la recherche q
  function matchesQuery(o, q) {
    if (!q) return true;
    var ql = q.toLowerCase().trim();
    var qDigits = normalizePhone(q);
    // Reference
    if ((o.reference || "").toLowerCase().indexOf(ql) >= 0) return true;
    // Client
    if ((o.customer_name || "").toLowerCase().indexOf(ql) >= 0) return true;
    // Telephone
    var phone = normalizePhone(o.phone);
    if (qDigits.length >= 3 && phone.indexOf(qDigits) >= 0) return true;
    return false;
  }

  // Filtre + tri
  function applyFilters(list) {
    var out = list.slice();

    // Filtre statut
    var allowed = FILTER_MAP[state2.filter];
    if (allowed) {
      out = out.filter(function (o) {
        return allowed.indexOf(o.status) >= 0;
      });
    }

    // Recherche
    if (state2.q) {
      out = out.filter(function (o) { return matchesQuery(o, state2.q); });
    }

    // Tri : date desc par defaut
    out.sort(function (a, b) {
      var ka = a.created_at || "";
      var kb = b.created_at || "";
      if (ka && kb) return kb.localeCompare(ka);
      return (b.id || 0) - (a.id || 0);
    });

    return out;
  }

  // Badges contextuels sur la carte
  function buildBadges(o) {
    var badges = [];
    if (o.payment_status === "PROOF_SUBMITTED") {
      badges.push({ txt: "Preuve a verifier", cls: "ph-badge-warn" });
    }
    if (o.prescription_status === "PENDING") {
      badges.push({ txt: "Ordonnance a examiner", cls: "ph-badge-info" });
    }
    // Action requise : en attente depuis > 24h
    if (o.status === "en_attente" && o.created_at) {
      try {
        var d = new Date(o.created_at);
        if (!isNaN(d.getTime()) && (Date.now() - d.getTime()) > 24*3600*1000) {
          badges.push({ txt: "Action requise", cls: "ph-badge-danger" });
        }
      } catch (e) {}
    }
    return badges;
  }

  // Actions rapides selon le statut
  function buildQuickActions(o) {
    var actions = [];
    if (o.status === "en_attente") {
      actions.push({ label: "Confirmer", kind: "primary", act: "confirm" });
      actions.push({ label: "Refuser", kind: "danger", act: "refuse" });
    } else if (o.status === "confirmee") {
      actions.push({ label: "Preparer", kind: "primary", act: "prepare" });
      actions.push({ label: "Refuser", kind: "danger", act: "refuse" });
    } else if (o.status === "en_preparation") {
      actions.push({ label: "Prete", kind: "primary", act: "ready" });
      actions.push({ label: "Refuser", kind: "danger", act: "refuse" });
    } else if (o.status === "prete") {
      if (o.delivery_mode === "livraison") {
        actions.push({ label: "En livraison", kind: "primary", act: "shipped" });
      }
      actions.push({ label: "Terminee", kind: "primary", act: "complete" });
    } else if (o.status === "en_livraison") {
      actions.push({ label: "Terminee", kind: "primary", act: "complete" });
    }
    return actions;
  }

  // Carte compacte
  function renderCard(o) {
    var card = document.createElement("article");
    card.className = "ph-oc";
    card.setAttribute("data-ref", o.reference || "");

    var total = (Number(o.subtotal) || 0) + (Number(o.delivery_fee) || 0);
    var statusLbl = STATUS_LABELS[o.status] || o.status;
    var statusCls = STATUS_PILL[o.status] || "ph-pill-pending";
    var badges = buildBadges(o);
    var actions = buildQuickActions(o);

    // Head : ref + status + total
    var html = '<div class="ph-oc-head">' +
      '<div class="ph-oc-ref">' + escapeHtml(o.reference || "") + '</div>' +
      '<span class="ph-pill ' + statusCls + '">' + escapeHtml(statusLbl) + '</span>' +
      '<div class="ph-oc-total">' + fmtMoney(total) + '</div>' +
    '</div>';

    // Meta : client + tel
    var meta = [];
    if (o.customer_name) meta.push('&#128100; ' + escapeHtml(o.customer_name));
    if (o.phone) meta.push('&#128222; ' + escapeHtml(o.phone));
    if (meta.length) {
      html += '<div class="ph-oc-meta">' + meta.join(' <span class="ph-dot">·</span> ') + '</div>';
    }

    // Produits + mode
    var line2 = [];
    if (o.product_name) {
      var qty = o.quantity || 1;
      line2.push(qty + '× ' + escapeHtml(o.product_name));
    }
    line2.push(o.delivery_mode === "livraison" ? '&#128666; Livraison' : '&#127974; Retrait');
    html += '<div class="ph-oc-products">' + line2.join(' <span class="ph-dot">·</span> ') + '</div>';

    // Badges contextuels
    if (badges.length) {
      html += '<div class="ph-oc-badges">';
      badges.forEach(function (b) {
        html += '<span class="ph-badge ' + b.cls + '">' + escapeHtml(b.txt) + '</span>';
      });
      html += '</div>';
    }

    // Date
    if (o.created_at) {
      html += '<div class="ph-oc-date">' + escapeHtml(fmtDate(o.created_at)) + '</div>';
    }

    // Actions
    html += '<div class="ph-oc-actions">';
    actions.forEach(function (a) {
      html += '<button type="button" class="ph-btn ph-btn-' + a.kind + '" data-ph-act="' + a.act + '" data-ph-ref="' + escapeHtml(o.reference) + '">' + a.label + '</button>';
    });
    html += '<button type="button" class="ph-btn ph-btn-ghost" data-ph-act="open" data-ph-ref="' + escapeHtml(o.reference) + '">Ouvrir &rsaquo;</button>';
    html += '</div>';

    card.innerHTML = html;
    return card;
  }

  function renderList() {
    var box = $("ph-orders-list");
    var countEl = $("ph-orders-count");
    if (!box) return;

    var filtered = applyFilters(state2.orders);

    if (countEl) {
      if (state2.orders.length === 0) {
        countEl.textContent = "Aucune commande";
      } else {
        countEl.textContent = filtered.length + " sur " + state2.orders.length + " commande(s)";
      }
    }

    if (filtered.length === 0) {
      box.innerHTML = '<div class="ph-orders-empty">' +
        '<div class="ph-orders-empty-ico">&#128230;</div>' +
        '<h3>Aucune commande</h3>' +
        '<p>' + (state2.q ? "Aucun resultat pour votre recherche." : "Aucune commande dans ce filtre.") + '</p>' +
        '</div>';
      return;
    }

    box.innerHTML = "";
    filtered.forEach(function (o) { box.appendChild(renderCard(o)); });
  }

  function load() {
    var box = $("ph-orders-list");
    if (box && state2.orders.length === 0) {
      box.innerHTML = '<div class="ph-orders-empty">Chargement...</div>';
    }
    fetch(API + "/orders", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (list) {
        state2.orders = Array.isArray(list) ? list : [];
        renderList();
      })
      .catch(function () {
        if (box) box.innerHTML = '<div class="ph-orders-empty">Erreur de chargement.</div>';
      });
  }

  // Toast interne
  function showToast(msg, kind) {
    var t = $("ph-orders-toast");
    if (!t) return;
    t.textContent = msg;
    t.className = "ph-toast ph-toast-" + (kind || "info");
    setTimeout(function () { t.classList.add("hidden"); }, 3000);
  }

  // Action : changeStatus via API existante
  function changeStatus(ref, newStatus, note) {
    return fetch(API + "/orders/" + encodeURIComponent(ref) + "/status", {
      method: "PATCH",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus, note: note || "" })
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    });
  }

  // Handler actions
  var ACTIONS = {
    confirm: { next: "confirmee", label: "Confirmer", needConfirm: true },
    refuse: { next: "refusee", label: "Refuser", needConfirm: true, needMotif: true },
    prepare: { next: "en_preparation", label: "Marquer en preparation", needConfirm: false },
    ready: { next: "prete", label: "Marquer prete", needConfirm: false },
    shipped: { next: "en_livraison", label: "Marquer en livraison", needConfirm: false },
    complete: { next: "terminee", label: "Marquer terminee", needConfirm: false }
  };

  function handleAction(act, ref) {
    if (act === "open") {
      // Ouvre la fiche commande (etape 3 viendra plus tard) -> pour l'instant, scroll + surlignage
      var card = document.querySelector('.ph-oc[data-ref="' + ref + '"]');
      if (card) {
        card.style.transition = "background .3s";
        card.style.background = "#E8F0F8";
        setTimeout(function () { card.style.background = ""; }, 800);
      }
      return;
    }

    var cfg = ACTIONS[act];
    if (!cfg) return;

    function execChange(note) {
      changeStatus(ref, cfg.next, note || "")
        .then(function () {
          showToast(cfg.label + " : " + ref, "success");
          load();
          if (window.phLoadHome) window.phLoadHome();
        })
        .catch(function (e) {
          showToast(e.message || "Erreur", "error");
        });
    }

    if (cfg.needMotif) {
      window.EHModal.prompt(
        "Motif du refus",
        "Cette commande sera refusee. Le motif sera enregistre.",
        {
          kind: "danger",
          placeholder: "Ex: Rupture de stock, Ordonnance invalide...",
          requireValue: true,
          confirmLabel: "Refuser",
          danger: true,
          maxLength: 500
        }
      ).then(function (motif) {
        if (motif === null) return;
        if (!window.EHModal) { execChange(motif); return; }
        // Confirmation finale dans le meme flow : juste executer
        execChange(motif);
      });
    } else if (cfg.needConfirm) {
      window.EHModal.confirm(cfg.label + " ?", "Commande " + ref).then(function (ok) {
        if (ok) execChange("");
      });
    } else {
      execChange("");
    }
  }

  // Event delegation
  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest ? ev.target.closest("[data-ph-act]") : null;
    if (!btn) return;
    var act = btn.getAttribute("data-ph-act");
    var ref = btn.getAttribute("data-ph-ref");
    if (act && ref) {
      ev.preventDefault();
      handleAction(act, ref);
    }
  });

  // Recherche live (debounce 200ms)
  var searchTimer = null;
  document.addEventListener("input", function (ev) {
    if (ev.target && ev.target.id === "ph-orders-search") {
      if (searchTimer) clearTimeout(searchTimer);
      var val = ev.target.value;
      searchTimer = setTimeout(function () {
        state2.q = val;
        renderList();
      }, 200);
    }
  });

  // Chips
  document.addEventListener("click", function (ev) {
    var chip = ev.target.closest ? ev.target.closest("[data-ph-filter]") : null;
    if (!chip) return;
    ev.preventDefault();
    var f = chip.getAttribute("data-ph-filter");
    state2.filter = f;
    // Refresh actif
    var all = document.querySelectorAll("[data-ph-filter]");
    for (var i = 0; i < all.length; i++) {
      all[i].classList.toggle("active", all[i] === chip);
    }
    renderList();
  });

  // Charger + recharger
  window.phLoadOrdersV2 = load;

  // Init
  function init() {
    setTimeout(function () {
      // Ne charger que si l'onglet commandes ou home est actif
      var body = document.body;
      if (body.getAttribute("data-active-page") === "home" ||
          body.getAttribute("data-active-page") === "commandes" ||
          !body.hasAttribute("data-active-page")) {
        load();
      }
    }, 600);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }


  // Recharger quand on clique sur l'onglet Commandes
  document.addEventListener("click", function (ev) {
    var tab = ev.target.closest ? ev.target.closest('[data-ph-tab="commandes"]') : null;
    if (tab) {
      setTimeout(load, 50);
    }
  });
})();

/* ============================================================
   PHARMACIEN V6 - Drawer fiche commande (Step 3)
   ============================================================ */
(function () {
  "use strict";
  var API = "/api";

  function $(id) { return document.getElementById(id); }

  function esc(s) {
    try {
      return String(s == null ? "" : s)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    } catch (e) { return ""; }
  }

  function fmtMoney(v) {
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
      if (isNaN(d.getTime())) return iso;
      var pad = function (n) { return n < 10 ? "0" + n : "" + n; };
      return pad(d.getDate()) + "/" + pad(d.getMonth()+1) + "/" + d.getFullYear()
        + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
    } catch (e) { return iso; }
  }

  var STATUS_LABELS = {
    en_attente: "En attente", confirmee: "Confirmee",
    en_preparation: "En preparation", prete: "Prete",
    en_livraison: "En livraison", terminee: "Terminee", refusee: "Refusee"
  };

  var STATUS_PILL = {
    en_attente: "ph-pill-pending", confirmee: "ph-pill-confirmed",
    en_preparation: "ph-pill-preparing", prete: "ph-pill-ready",
    en_livraison: "ph-pill-in-delivery", terminee: "ph-pill-done",
    refusee: "ph-pill-refused"
  };

  function buildWhatsappMessageClient(o) {
    var lines = [];
    lines.push("Bonjour " + (o.customer_name || "") + ",");
    lines.push("");
    lines.push("Votre commande " + (o.reference || "") + " :");
    lines.push("Statut : " + (STATUS_LABELS[o.status] || o.status));
    var total = (Number(o.subtotal) || 0) + (Number(o.delivery_fee) || 0);
    lines.push("Montant : " + fmtMoney(total));
    lines.push("");
    lines.push("Merci de votre confiance.");
    lines.push("Elonikab Health");
    return lines.join("\n");
  }

  function openDrawer(ref) {
    var d = $("ph-drawer");
    var ov = $("ph-drawer-overlay");
    var body = $("ph-drawer-body");
    if (!d || !body) return;

    $("ph-drawer-ref").textContent = ref;
    $("ph-drawer-status").innerHTML = "";
    body.innerHTML = '<div class="ph-drawer-loading">Chargement...</div>';

    d.classList.add("open");
    d.setAttribute("aria-hidden", "false");
    if (ov) ov.classList.remove("hidden");
    document.body.style.overflow = "hidden";

    // Deep-link
    try {
      var url = new URL(window.location.href);
      url.searchParams.set("ref", ref);
      history.replaceState(null, "", url.toString());
    } catch (e) {}

    // Charger toutes les donnees en parallele
    Promise.all([
      fetch(API + "/orders/" + encodeURIComponent(ref), { credentials: "same-origin" }).then(function(r){return r.ok?r.json():null;}),
      fetch(API + "/orders/" + encodeURIComponent(ref) + "/items", { credentials: "same-origin" }).then(function(r){return r.ok?r.json():[];}).catch(function(){return [];}),
      fetch(API + "/orders/" + encodeURIComponent(ref) + "/timeline", { credentials: "same-origin" }).then(function(r){return r.ok?r.json():null;}).catch(function(){return null;}),
      fetch(API + "/pharmacien/orders/" + encodeURIComponent(ref) + "/payment", { credentials: "same-origin" }).then(function(r){return r.ok?r.json():null;}).catch(function(){return null;}),
      fetch(API + "/pharmacien/orders/" + encodeURIComponent(ref) + "/prescription", { credentials: "same-origin" }).then(function(r){return r.ok?r.json():null;}).catch(function(){return null;}),
      fetch(API + "/orders/" + encodeURIComponent(ref) + "/notes", { credentials: "same-origin" }).then(function(r){return r.ok?r.json():[];}).catch(function(){return [];})
    ]).then(function (r) {
      var o = r[0];
      if (!o) { body.innerHTML = '<div class="ph-drawer-loading">Commande introuvable.</div>'; return; }
      var payment = (r[3] && r[3].payment) ? r[3].payment : null;
      var presc = (r[4] && r[4].prescription) ? r[4].prescription : null;
      renderDrawer(o, r[1] || [], r[2], payment, presc, r[5] || []);
    }).catch(function () {
      body.innerHTML = '<div class="ph-drawer-loading">Erreur de chargement.</div>';
    });
  }

  function closeDrawer() {
    var d = $("ph-drawer");
    var ov = $("ph-drawer-overlay");
    if (d) { d.classList.remove("open"); d.setAttribute("aria-hidden", "true"); }
    if (ov) ov.classList.add("hidden");
    document.body.style.overflow = "";
    try {
      var url = new URL(window.location.href);
      url.searchParams.delete("ref");
      history.replaceState(null, "", url.toString());
    } catch (e) {}
  }

  function renderDrawer(o, items, timeline, payment, presc, notes) {
    var body = $("ph-drawer-body");
    if (!body) return;

    var total = (Number(o.subtotal) || 0) + (Number(o.delivery_fee) || 0);
    var statusLbl = STATUS_LABELS[o.status] || o.status;
    var statusCls = STATUS_PILL[o.status] || "ph-pill-pending";

    $("ph-drawer-status").innerHTML = '<span class="ph-pill ' + statusCls + '">' + esc(statusLbl) + '</span>';

    var h = '';

    // ---- Client ----
    h += '<div class="ph-drawer-block">';
    h += '<div class="ph-drawer-lbl">Client</div>';
    h += '<div class="ph-drawer-line"><strong>' + esc(o.customer_name || "") + '</strong></div>';
    if (o.phone) h += '<div class="ph-drawer-line">&#128222; ' + esc(o.phone) + '</div>';
    if (o.delivery_mode === "livraison" && o.address) h += '<div class="ph-drawer-line">&#128205; ' + esc(o.address) + '</div>';
    h += '</div>';

    // ---- Produits ----
    h += '<div class="ph-drawer-block">';
    h += '<div class="ph-drawer-lbl">Produits</div>';
    if (items.length === 0) {
      h += '<div class="ph-drawer-line">' + esc(o.product_name || "") + ' &times; ' + (o.quantity || 1) + '</div>';
    } else {
      items.forEach(function (it) {
        h += '<div class="ph-drawer-line ph-drawer-product">';
        h += '<span>' + (it.quantity || 1) + '&times; ' + esc(it.product_name || "") + '</span>';
        h += '<span>' + fmtMoney(it.subtotal || (Number(it.unit_price) * Number(it.quantity))) + '</span>';
        h += '</div>';
      });
    }
    h += '<div class="ph-drawer-total-line"><span>Sous-total</span><span>' + fmtMoney(o.subtotal) + '</span></div>';
    if (o.delivery_mode === "livraison") {
      h += '<div class="ph-drawer-total-line"><span>Livraison</span><span>' + fmtMoney(o.delivery_fee) + '</span></div>';
    }
    h += '<div class="ph-drawer-total-line ph-drawer-grand"><span>Total</span><span>' + fmtMoney(total) + '</span></div>';
    h += '</div>';

    // ---- Paiement ----
    h += '<div class="ph-drawer-block">';
    h += '<div class="ph-drawer-lbl">Paiement</div>';
    if (!payment) {
      h += '<div class="ph-drawer-line" style="color:#64748b">Aucun paiement initie</div>';
    } else {
      var payStatus = payment.status || "PENDING";
      h += '<div class="ph-drawer-line">Statut : <strong>' + esc(paymentLabelFR(payStatus)) + '</strong></div>';
      if (payment.amount) h += '<div class="ph-drawer-line">Montant : ' + fmtMoney(payment.amount) + '</div>';
      if (payment.proof_file) {
        var proofUrl = payment.proof_file.indexOf("/uploads/") === 0
          ? payment.proof_file.replace("/uploads/", "/api/files/")
          : payment.proof_file;
        h += '<div class="ph-drawer-line">';
        h += '<a href="' + esc(proofUrl) + '" target="_blank" rel="noopener" class="ph-drawer-proof">';
        h += '<img src="' + esc(proofUrl) + '" alt="Preuve" loading="lazy" onerror="this.style.display=\'none\'">';
        h += '<span>Voir la preuve</span></a>';
        h += '</div>';
      }
      // Boutons d'action paiement (V7 - ajout dans drawer)
      if (payStatus === "PROOF_SUBMITTED") {
        h += '<div class="ph-drawer-actions drawer-pay-actions" style="margin-top:10px">';
        h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-pay="verify" data-pay-id="' + payment.id + '" data-pay-ref="' + esc(o.reference) + '">Valider le paiement</button>';
        h += '<button type="button" class="ph-btn ph-btn-danger" data-drawer-pay="reject" data-pay-id="' + payment.id + '" data-pay-ref="' + esc(o.reference) + '">Refuser</button>';
        h += '</div>';
      } else if (payStatus === "REFUND_REQUIRED") {
        h += '<div class="ph-drawer-actions drawer-pay-actions" style="margin-top:10px">';
        h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-pay="refund" data-pay-id="' + payment.id + '" data-pay-ref="' + esc(o.reference) + '">Marquer rembourse</button>';
        h += '</div>';
      }
    }
    h += '</div>';

    // ---- Ordonnance ----
    h += '<div class="ph-drawer-block">';
    h += '<div class="ph-drawer-lbl">Ordonnance</div>';
    if (!presc || !presc.file_path) {
      h += '<div class="ph-drawer-line" style="color:#64748b">Aucune ordonnance jointe</div>';
    } else {
      var prescUrl = presc.file_path.indexOf("/uploads/") === 0
        ? presc.file_path.replace("/uploads/", "/api/files/")
        : presc.file_path;
      h += '<div class="ph-drawer-line">Statut : <strong>' + esc(presc.status || "PENDING") + '</strong></div>';
      h += '<div class="ph-drawer-line"><a href="' + esc(prescUrl) + '" target="_blank" rel="noopener" class="ph-drawer-proof">';
      h += '<img src="' + esc(prescUrl) + '" alt="Ordonnance" loading="lazy" onerror="this.style.display=\'none\'">';
      h += '<span>Voir l\'ordonnance</span></a></div>';
    }
    h += '</div>';

    // ---- Historique (timeline) ----
    if (timeline && timeline.events && timeline.events.length > 0) {
      h += '<div class="ph-drawer-block">';
      h += '<div class="ph-drawer-lbl">Historique</div>';
      timeline.events.forEach(function (ev) {
        h += '<div class="ph-drawer-line" style="font-size:12.5px">';
        h += '<span>' + esc(ev.label || "") + '</span>';
        if (ev.at) h += '<span style="color:#94a3b8">' + esc(fmtDate(ev.at)) + '</span>';
        h += '</div>';
      });
      h += '</div>';
    }

    // ---- Notes internes ----
    h += '<div class="ph-drawer-block">';
    h += '<div class="ph-drawer-lbl">Notes internes <span class="ph-drawer-badge">PRIVE</span></div>';
    if (notes.length === 0) {
      h += '<div class="ph-drawer-line" style="color:#64748b">Aucune note</div>';
    } else {
      notes.forEach(function (n) {
        h += '<div class="ph-drawer-note">';
        h += '<div>' + esc(n.body) + '</div>';
        h += '<div class="ph-drawer-note-meta">' + esc(n.author || "") + ' &middot; ' + esc(fmtDate(n.created_at)) + '</div>';
        h += '</div>';
      });
    }
    h += '<div class="ph-drawer-note-form">';
    h += '<textarea id="ph-drawer-note-input" rows="2" placeholder="Ajouter une note interne..." maxlength="2000"></textarea>';
    h += '<button type="button" class="ph-btn ph-btn-primary" id="ph-drawer-note-add">Ajouter</button>';
    h += '</div>';
    h += '</div>';

    // ---- Checklist avant remise (Lot 4) ----
    if (o.status === "prete") {
      h += '<div class="ph-drawer-block drawer-checklist">';
      h += '<div class="ph-drawer-lbl">Controle avant remise</div>';
      h += '<label style="display:block;font-size:13.5px;padding:6px 0"><input type="checkbox" class="ph-check" data-check="1"> Produits verifies</label>';
      h += '<label style="display:block;font-size:13.5px;padding:6px 0"><input type="checkbox" class="ph-check" data-check="2"> Ordonnance conforme</label>';
      h += '<label style="display:block;font-size:13.5px;padding:6px 0"><input type="checkbox" class="ph-check" data-check="3"> Paiement valide</label>';
      h += '<div style="margin-top:8px;font-size:12px;color:#64748b" id="ph-check-hint">Cochez les 3 points avant de marquer terminee</div>';
      h += '</div>';
    }

    // ---- Actions ----
    h += '<div class="ph-drawer-actions">';
    // Actions selon statut
    if (o.status === "en_attente") {
      h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-act="confirmee" data-ref="' + esc(o.reference) + '">Confirmer</button>';
      h += '<button type="button" class="ph-btn ph-btn-danger" data-drawer-act="refusee" data-ref="' + esc(o.reference) + '">Refuser</button>';
    } else if (o.status === "confirmee") {
      h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-act="en_preparation" data-ref="' + esc(o.reference) + '">Preparer</button>';
      h += '<button type="button" class="ph-btn ph-btn-danger" data-drawer-act="refusee" data-ref="' + esc(o.reference) + '">Refuser</button>';
    } else if (o.status === "en_preparation") {
      h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-act="prete" data-ref="' + esc(o.reference) + '">Prete</button>';
      h += '<button type="button" class="ph-btn ph-btn-danger" data-drawer-act="refusee" data-ref="' + esc(o.reference) + '">Refuser</button>';
    } else if (o.status === "prete") {
      if (o.delivery_mode === "livraison") {
        h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-act="en_livraison" data-ref="' + esc(o.reference) + '">En livraison</button>';
      }
      h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-act="terminee" data-ref="' + esc(o.reference) + '">Terminee</button>';
    } else if (o.status === "en_livraison") {
      h += '<button type="button" class="ph-btn ph-btn-primary" data-drawer-act="terminee" data-ref="' + esc(o.reference) + '">Terminee</button>';
    }
    // WhatsApp client
    if (o.phone) {
      h += '<button type="button" class="ph-btn ph-btn-ghost" data-drawer-act="wa" data-ref="' + esc(o.reference) + '">WhatsApp</button>';
    }
    // Imprimer
    h += '<button type="button" class="ph-btn ph-btn-ghost" data-drawer-act="print" data-ref="' + esc(o.reference) + '">Imprimer</button>';
    h += '</div>';

    body.innerHTML = h;

    // Bind note add
    var addBtn = $("ph-drawer-note-add");
    if (addBtn) {
      addBtn.addEventListener("click", function () {
        var inp = $("ph-drawer-note-input");
        if (!inp) return;
        var body_ = (inp.value || "").trim();
        if (!body_) return;
        addBtn.disabled = true;
        fetch(API + "/orders/" + encodeURIComponent(o.reference) + "/notes", {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ body: body_ })
        }).then(function (r) { return r.ok ? r.json() : null; })
          .then(function () { openDrawer(o.reference); })
          .catch(function () { addBtn.disabled = false; });
      });
    }
  }

  // Event delegation
  document.addEventListener("click", function (ev) {
    // Ouvrir drawer
    var open = ev.target.closest ? ev.target.closest('[data-ph-act="open"]') : null;
    if (open) {
      ev.preventDefault();
      var ref = open.getAttribute("data-ph-ref");
      if (ref) openDrawer(ref);
      return;
    }
    // Fermer
    var closeBtn = ev.target.closest ? ev.target.closest("[data-ph-close-drawer]") : null;
    if (closeBtn) {
      ev.preventDefault();
      closeDrawer();
      return;
    }
    // Paiement depuis le drawer (V8 : utilise window.*)
    var payBtn = ev.target.closest ? ev.target.closest("[data-drawer-pay]") : null;
    if (payBtn) {
      ev.preventDefault();
      var pAction = payBtn.getAttribute("data-drawer-pay");
      var pPayId  = payBtn.getAttribute("data-pay-id");
      var pRef    = payBtn.getAttribute("data-pay-ref");
      console.log("[drawer-pay] click", pAction, "pay_id=", pPayId, "ref=", pRef);
      if (!pPayId || pPayId === "undefined" || pPayId === "null") {
        if (window.EHModal) window.EHModal.alert("Erreur", "ID paiement manquant", "danger");
        else alert("ID paiement manquant");
        return;
      }
      try {
        if (pAction === "verify" && typeof window.ehPhValidatePayment === "function") {
          window.ehPhValidatePayment(pPayId, pRef);
          return;
        }
        if (pAction === "reject" && typeof window.ehPhRejectPayment === "function") {
          window.ehPhRejectPayment(pPayId, pRef);
          return;
        }
        if (pAction === "refund" && typeof window.ehPhRefundPayment === "function") {
          window.ehPhRefundPayment(pPayId, pRef);
          return;
        }
        // Fallback : appels directs si les fonctions ne sont pas encore chargees
        if (pAction === "verify") {
          if (!confirm("Valider le paiement de " + pRef + " ?")) return;
          fetch(API + "/payments/" + pPayId + "/verify", { method: "PATCH", credentials: "same-origin" })
            .then(function(r){ return r.json().then(function(d){ if(!r.ok) throw new Error(d.detail||"Erreur"); return d; }); })
            .then(function(){ if (window.phLoadOrdersV2) window.phLoadOrdersV2(); if (window.phLoadHome) window.phLoadHome(); if (window.phOpenDrawer) window.phOpenDrawer(pRef); })
            .catch(function(e){ if (window.EHModal) window.EHModal.alert("Erreur", e.message, "danger"); else alert(e.message); });
          return;
        }
        if (pAction === "reject") {
          var motif = prompt("Motif du refus :");
          if (!motif) return;
          fetch(API + "/payments/" + pPayId + "/reject", { method: "PATCH", credentials: "same-origin", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ rejection_reason: motif }) })
            .then(function(r){ return r.json().then(function(d){ if(!r.ok) throw new Error(d.detail||"Erreur"); return d; }); })
            .then(function(){ if (window.phLoadOrdersV2) window.phLoadOrdersV2(); if (window.phOpenDrawer) window.phOpenDrawer(pRef); })
            .catch(function(e){ if (window.EHModal) window.EHModal.alert("Erreur", e.message, "danger"); else alert(e.message); });
          return;
        }
        if (pAction === "refund") {
          if (!confirm("Marquer ce paiement comme rembourse ?")) return;
          fetch(API + "/payments/" + pPayId + "/refund", { method: "PATCH", credentials: "same-origin" })
            .then(function(r){ return r.json().then(function(d){ if(!r.ok) throw new Error(d.detail||"Erreur"); return d; }); })
            .then(function(){ if (window.phLoadOrdersV2) window.phLoadOrdersV2(); if (window.phOpenDrawer) window.phOpenDrawer(pRef); })
            .catch(function(e){ if (window.EHModal) window.EHModal.alert("Erreur", e.message, "danger"); else alert(e.message); });
          return;
        }
        console.warn("[drawer-pay] action inconnue ou fonction indisponible", pAction);
      } catch (err) {
        console.error("[drawer-pay] exception", err);
        if (window.EHModal) window.EHModal.alert("Erreur", String(err), "danger");
      }
      return;
    }
    // Action dans le drawer
    var act = ev.target.closest ? ev.target.closest("[data-drawer-act]") : null;
    if (act) {
      var a = act.getAttribute("data-drawer-act");
      var r = act.getAttribute("data-ref");
      if (a === "print") {
        window.open("/api/orders/" + encodeURIComponent(r) + "/print", "_blank");
        return;
      }
      if (a === "wa") {
        // Recuperer les infos via API puis ouvrir wa.me
        fetch(API + "/orders/" + encodeURIComponent(r), { credentials: "same-origin" })
          .then(function (res) { return res.ok ? res.json() : null; })
          .then(function (o) {
            if (!o || !o.phone) return;
            var phone = String(o.phone).replace(/\D/g, "");
            var msg = buildWhatsappMessageClient(o);
            var url = "https://wa.me/" + phone + "?text=" + encodeURIComponent(msg);
            window.open(url, "_blank");
          });
        return;
      }
      // Changement de statut (via EHModal)
      var statusLabels = {
        confirmee: "Confirmer",
        en_preparation: "Marquer en preparation",
        prete: "Marquer prete",
        en_livraison: "Marquer en livraison",
        terminee: "Marquer terminee"
      };

      function doChange(note) {
        fetch(API + "/orders/" + encodeURIComponent(r) + "/status", {
          method: "PATCH",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: a, note: note || "" })
        }).then(function (res) {
          if (res.ok) {
            openDrawer(r);
            if (window.phLoadOrdersV2) window.phLoadOrdersV2();
            if (window.phLoadHome) window.phLoadHome();
          } else {
            return res.json().then(function (d) {
              window.EHModal.alert("Erreur", d.detail || "Mise a jour impossible", "danger");
            });
          }
        }).catch(function () {
          window.EHModal.alert("Erreur reseau", "Verifiez votre connexion", "danger");
        });
      }

      if (a === "refusee") {
        // 1. Prompt motif obligatoire
        window.EHModal.prompt(
          "Motif du refus",
          "Expliquez pourquoi cette commande est refusee (visible dans l'historique).",
          {
            kind: "danger",
            placeholder: "Ex: Rupture de stock, Ordonnance invalide...",
            requireValue: true,
            confirmLabel: "Continuer",
            maxLength: 500
          }
        ).then(function (motif) {
          if (motif === null) return;  // annule
          // 2. Confirmation finale
          window.EHModal.confirmDanger(
            "Refuser la commande ?",
            "La commande " + r + " sera refusee. Motif : " + motif,
            "Refuser"
          ).then(function (ok) {
            if (ok) doChange(motif);
          });
        });
      } else {
        var lbl = statusLabels[a] || ("Marquer : " + a);
        window.EHModal.confirm(lbl + " ?", "Commande " + r).then(function (ok) {
          if (ok) doChange("");
        });
      }
    }
  });

  // Escape pour fermer
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") {
      var d = document.getElementById("ph-drawer");
      if (d && d.classList.contains("open")) {
        ev.preventDefault();
        closeDrawer();
      }
    }
  });

  // Deep-link : ouvrir si ?ref=
  function checkDeepLink() {
    try {
      var params = new URLSearchParams(window.location.search);
      var ref = params.get("ref");
      if (ref) {
        setTimeout(function () { openDrawer(ref); }, 500);
      }
    } catch (e) {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", checkDeepLink);
  } else {
    checkDeepLink();
  }

  // Exposer
  window.phOpenDrawer = openDrawer;
  window.phCloseDrawer = closeDrawer;
})();

/* ============================================================
   EHModal : modales custom (remplacent confirm/prompt/alert)
   ============================================================ */
(function () {
  "use strict";

  // Creer le conteneur
  function ensureRoot() {
    var r = document.getElementById("eh-modal-root");
    if (r) return r;
    r = document.createElement("div");
    r.id = "eh-modal-root";
    document.body.appendChild(r);
    return r;
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  /**
   * Affiche une modale
   * @param {Object} opts { kind, title, sub, body, confirmLabel, cancelLabel, danger, requireValue }
   * @returns {Promise} resolves { ok: true/false, value: string }
   */
  function open(opts) {
    opts = opts || {};
    var root = ensureRoot();
    var kind = opts.kind || "info";
    var isPrompt = !!opts.prompt;
    var isAlert = !!opts.alert;
    var danger = !!opts.danger;

    var ico = { info: "&#128161;", danger: "&#9888;", success: "&#10003;", warn: "&#9888;" }[kind] || "&#128161;";

    var html = '';
    html += '<div class="eh-modal-backdrop">';
    html += '<div class="eh-modal" role="dialog" aria-modal="true">';
    html += '<div class="eh-modal-head">';
    html += '<div class="eh-modal-ico ' + kind + '">' + ico + '</div>';
    html += '<div class="eh-modal-title-wrap">';
    if (opts.title) html += '<h3 class="eh-modal-title">' + esc(opts.title) + '</h3>';
    if (opts.sub) html += '<p class="eh-modal-sub">' + esc(opts.sub) + '</p>';
    html += '</div>';
    html += '</div>';

    if (isPrompt) {
      html += '<div class="eh-modal-body">';
      if (opts.body) html += '<p style="font-size:13.5px;color:#64748b;margin:0 0 10px">' + esc(opts.body) + '</p>';
      html += '<textarea id="eh-modal-input" rows="3" placeholder="' + esc(opts.placeholder || "") + '" maxlength="' + (opts.maxLength || 2000) + '">' + (opts.defaultValue || "") + '</textarea>';
      html += '<p style="font-size:11.5px;color:#94a3b8;margin:6px 0 0">Entree = valider  •  Shift+Entree = nouvelle ligne</p>';
      html += '</div>';
    } else if (opts.body && !isAlert) {
      html += '<div class="eh-modal-body">';
      html += '<p style="font-size:14px;color:#0f172a;margin:0;line-height:1.55">' + esc(opts.body) + '</p>';
      html += '</div>';
    } else if (opts.body && isAlert) {
      html += '<div class="eh-modal-body">';
      html += '<p style="font-size:14px;color:#0f172a;margin:0;line-height:1.55">' + esc(opts.body) + '</p>';
      html += '</div>';
    }

    html += '<div class="eh-modal-error" id="eh-modal-error"></div>';

    html += '<div class="eh-modal-actions">';
    if (!isAlert) {
      html += '<button type="button" class="eh-modal-btn eh-modal-btn-ghost" data-eh-modal-cancel>' + esc(opts.cancelLabel || "Annuler") + '</button>';
    }
    var confirmCls = danger ? "eh-modal-btn-danger" : "eh-modal-btn-primary";
    html += '<button type="button" class="eh-modal-btn ' + confirmCls + '" data-eh-modal-confirm>' + esc(opts.confirmLabel || "Confirmer") + '</button>';
    html += '</div>';

    html += '</div></div>';

    root.innerHTML = html;

    var backdrop = root.querySelector(".eh-modal-backdrop");
    var input = root.querySelector("#eh-modal-input");
    var error = root.querySelector("#eh-modal-error");
    var btnConfirm = root.querySelector("[data-eh-modal-confirm]");
    var btnCancel = root.querySelector("[data-eh-modal-cancel]");

    setTimeout(function () { backdrop.classList.add("show"); }, 10);
    if (input) setTimeout(function () { input.focus(); }, 250);

    return new Promise(function (resolve) {
      function close(result) {
        // Retirer la classe show -> animation disparition
        backdrop.classList.remove("show");
        // NE PAS vider root.innerHTML ici : une 2e modal peut s'ouvrir juste apres
        // (le prochain open() fera root.innerHTML = html de toute facon)
        // Retirer le listener keydown si encore attache
        try { document.removeEventListener("keydown", onKey); } catch (e) {}
        // Si result est null, c'est une annulation -> nettoyer _current
        try {
          if (!window.EHModal._current || window.EHModal._current._fromThisModal) {
            // Rien
          }
        } catch (e) {}
        resolve(result);
      }

      function onCancel() { close({ ok: false, value: null }); }

      function onConfirm() {
        if (isPrompt) {
          var v = (input.value || "").trim();
          if (opts.requireValue && !v) {
            error.textContent = "Ce champ est obligatoire";
            error.classList.add("show");
            input.focus();
            return;
          }
          close({ ok: true, value: v });
        } else {
          close({ ok: true, value: null });
        }
      }

      // === EXPOSE POUR LE LISTENER GLOBAL ===
      try {
        window.EHModal._current = {
          onConfirm: onConfirm,
          onCancel: onCancel
        };
      } catch (e) {}


      function onKey(ev) {
        if (ev.key === "Escape") {
          ev.preventDefault();
          ev.stopPropagation();
          try { ev.stopImmediatePropagation(); } catch (e) {}
          onCancel();
          return;
        }
        if (ev.key === "Enter" && !ev.shiftKey) {
          ev.preventDefault();
          ev.stopPropagation();
          try { ev.stopImmediatePropagation(); } catch (e) {}
          onConfirm();
          return;
        }
      }

      btnConfirm.addEventListener("click", onConfirm);
      if (btnCancel) btnCancel.addEventListener("click", onCancel);
      backdrop.addEventListener("click", function (ev) {
        if (ev.target === backdrop) onCancel();
      });
    });
  }

  /* V3 : recharge le drawer ouvert s'il existe (apres action paiement) */
function drawerRefreshIfOpen() {
  try {
    var d = document.getElementById("ph-drawer");
    if (!d || !d.classList.contains("open")) return;
    var refEl = document.getElementById("ph-drawer-ref");
    var ref = refEl ? (refEl.textContent || "").trim() : "";
    if (ref && typeof window.phOpenDrawer === "function") {
      setTimeout(function() { window.phOpenDrawer(ref); }, 150);
    }
  } catch(e) { console.warn("[drawer-refresh] " + e); }
}

window.drawerRefreshIfOpen = drawerRefreshIfOpen;


window.EHModal = {
    confirm: function (title, sub) {
      return open({
        kind: "info",
        title: title,
        sub: sub,
        confirmLabel: "Confirmer",
        cancelLabel: "Annuler",
      }).then(function (r) { return r.ok; });
    },
    confirmDanger: function (title, sub, confirmLabel) {
      return open({
        kind: "danger",
        title: title,
        sub: sub,
        confirmLabel: confirmLabel || "Confirmer",
        cancelLabel: "Annuler",
        danger: true,
      }).then(function (r) { return r.ok; });
    },
    prompt: function (title, body, opts) {
      opts = opts || {};

  /* ============================================================
     ATTACHE GLOBAL : keydown pour les modales
     Appelle directement les callbacks stockes (pas via .click())
     ============================================================ */
  (function attachGlobalKeydown() {
    function globalKeydown(ev) {
      // Sortir si aucune modal ouverte
      var backdrop = document.querySelector(".eh-modal-backdrop");
      if (!backdrop) return;
      // Sortir si aucun callback enregistre
      var cb = (window.EHModal && window.EHModal._current) || null;
      if (!cb) return;

      if (ev.key === "Escape") {
        ev.preventDefault();
        ev.stopPropagation();
        try { ev.stopImmediatePropagation(); } catch (e) {}
        try { if (cb.onCancel) cb.onCancel(); } catch (e) {}
        return;
      }
      if (ev.key === "Enter" && !ev.shiftKey) {
        ev.preventDefault();
        ev.stopPropagation();
        try { ev.stopImmediatePropagation(); } catch (e) {}
        try { if (cb.onConfirm) cb.onConfirm(); } catch (e) {}
        return;
      }
    }
    document.addEventListener("keydown", globalKeydown, true);
  })();


      return open({
        kind: opts.kind || "info",
        title: title,
        body: body,
        prompt: true,
        placeholder: opts.placeholder,
        maxLength: opts.maxLength,
        requireValue: opts.requireValue !== false,
        confirmLabel: opts.confirmLabel || "Valider",
        cancelLabel: "Annuler",
        danger: opts.danger,
      }).then(function (r) { return r.ok ? r.value : null; });
    },
    alert: function (title, body, kind) {
      return open({
        kind: kind || "info",
        title: title,
        body: body,
        alert: true,
        confirmLabel: "OK",
      }).then(function () { return true; });
    },
  };
})();

/* ============================================================
   PHARMACIEN V6 - Vue Paiements (Step 4)
   ============================================================ */
(function () {
  "use strict";
  var API = "/api";
  var state4 = {
    payments: [],
    filter: "todo"
  };

  var PAY_STATUS_LABELS = {
    "PROOF_SUBMITTED": "Preuve soumise",
    "REFUND_REQUIRED": "Remboursement requis",
    "VERIFIED": "Verifie",
    "REJECTED": "Refuse",
    "REFUNDED": "Rembourse",
    "PENDING": "En attente",
    "NONE": "Aucun"
  };

  var REJECT_REASONS = [
    "Montant incorrect",
    "Preuve illisible",
    "Preuve non conforme",
    "Paiement non recu",
    "Autre (precisez)"
  ];

  function $(id) { return document.getElementById(id); }

  function fmtMoney(v) {
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

  function esc(s) {
    try {
      return String(s == null ? "" : s)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    } catch (e) { return ""; }
  }

  function payLabel(s) {
    return PAY_STATUS_LABELS[String(s || "").toUpperCase()] || s || "Aucun";
  }

  function openLightbox(url) {
    var lb = $("ph-pay-lightbox");
    if (!lb) {
      lb = document.createElement("div");
      lb.id = "ph-pay-lightbox";
      lb.className = "ph-pay-lightbox hidden";
      lb.innerHTML = '<button class="ph-pay-lightbox-close" aria-label="Fermer">&times;</button><img alt="Preuve">';
      document.body.appendChild(lb);
      lb.addEventListener("click", function (ev) {
        if (ev.target === lb || ev.target.classList.contains("ph-pay-lightbox-close")) {
          lb.classList.add("hidden");
        }
      });
      document.addEventListener("keydown", function (ev) {
        if (ev.key === "Escape") lb.classList.add("hidden");
      });
    }
    var img = lb.querySelector("img");
    img.src = url;
    lb.classList.remove("hidden");
  }

  // Construire une URL protegee pour la preuve
  function proofUrl(proofFile) {
    if (!proofFile) return "";
    if (proofFile.indexOf("/api/files/") === 0) return proofFile;
    if (proofFile.indexOf("/uploads/") === 0) {
      return proofFile.replace("/uploads/", "/api/files/");
    }
    return proofFile;
  }

  // Filtrer selon state4.filter
  function applyFilter(list) {
    if (state4.filter === "todo") {
      return list.filter(function (p) {
        return p.status === "PROOF_SUBMITTED" || p.status === "REFUND_REQUIRED";
      });
    }
    if (state4.filter === "history") {
      return list.filter(function (p) {
        return p.status !== "PROOF_SUBMITTED" && p.status !== "REFUND_REQUIRED";
      });
    }
    return list;
  }

  function renderCard(p) {
    var card = document.createElement("article");
    card.className = "ph-pay-card";
    var pu = proofUrl(p.proof_file);
    var total = (Number(p.total) || 0);
    var declared = (Number(p.amount) || 0);

    var html = '';

    // Colonne 1 : preuve
    if (pu) {
      html += '<div class="ph-pay-proof" data-ph-open-proof="' + esc(pu) + '">';
      html += '<img src="' + esc(pu) + '" alt="Preuve" loading="lazy" onerror="this.parentNode.innerHTML=\'&#128196;\'">';
      html += '<span class="ph-pay-proof-zoom">&#128269;</span>';
      html += '</div>';
    } else {
      html += '<div class="ph-pay-proof"><span class="ph-pay-proof-ph">&#128196;</span></div>';
    }

    // Colonne 2 : infos
    html += '<div class="ph-pay-info">';
    html += '<div class="ph-pay-ref">' + esc(p.order_reference || "") + '</div>';
    html += '<div class="ph-pay-client">' + esc(p.customer_name || "Client") + '</div>';
    if (p.phone) {
      html += '<div class="ph-pay-meta">&#128222; ' + esc(p.phone) + '</div>';
    }
    html += '<span class="ph-pay-pill ph-pay-pill-' + esc((p.status || "").toUpperCase()) + '">' + esc(payLabel(p.status)) + '</span>';
    html += '<div class="ph-pay-amounts">';
    html += '<span><span class="lbl">Attendu :</span> <strong>' + fmtMoney(total) + '</strong></span>';
    if (declared && declared !== total) {
      html += '<span><span class="lbl">Declare :</span> <strong style="color:#B26B00">' + fmtMoney(declared) + '</strong></span>';
    }
    html += '</div>';
    if (p.rejection_reason) {
      html += '<div style="margin-top:6px;font-size:12px;color:#64748B">Motif : ' + esc(p.rejection_reason) + '</div>';
    }
    html += '</div>';

    // Colonne 3 : actions
    html += '<div class="ph-pay-actions">';
    if (p.status === "PROOF_SUBMITTED" && p.order_status !== "refusee") {
      html += '<button type="button" class="ph-btn ph-btn-primary" data-ph-validate="' + p.id + '" data-ph-ref="' + esc(p.order_reference) + '">Valider</button>';
      html += '<button type="button" class="ph-btn ph-btn-danger" data-ph-reject="' + p.id + '" data-ph-ref="' + esc(p.order_reference) + '">Refuser</button>';
    } else if (p.status === "REFUND_REQUIRED") {
      html += '<div style="font-size:12px;color:#B26B00;font-weight:700;text-align:center">Remboursement<br>a traiter</div>';
      html += '<button type="button" class="ph-btn ph-btn-ghost" data-ph-refund="' + p.id + '" data-ph-ref="' + esc(p.order_reference) + '">Marquer rembourse</button>';
    } else {
      html += '<div style="font-size:12px;color:#64748B;text-align:center">Aucune action</div>';
    }
    html += '</div>';

    card.innerHTML = html;
    return card;
  }

  function renderList() {
    var box = $("ph-pay-list");
    var countEl = $("ph-pay-count");
    if (!box) return;
    var filtered = applyFilter(state4.payments);

    if (countEl) {
      countEl.textContent = filtered.length + " paiement" + (filtered.length > 1 ? "s" : "");
    }

    if (filtered.length === 0) {
      box.innerHTML = '<div class="ph-pay-empty">' +
        '<span class="ph-pay-empty-ico">&#128179;</span>' +
        '<strong>Aucun paiement</strong>' +
        '</div>';
      return;
    }
    box.innerHTML = "";
    filtered.forEach(function (p) { box.appendChild(renderCard(p)); });
  }

  function load() {
    var box = $("ph-pay-list");
    if (box) box.innerHTML = '<div class="ph-pay-empty">Chargement...</div>';
    fetch(API + "/payments", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (list) {
        state4.payments = Array.isArray(list) ? list : [];
        renderList();
        updateBadge();
      })
      .catch(function () {
        if (box) box.innerHTML = '<div class="ph-pay-empty">Erreur de chargement</div>';
      });
  }

  function updateBadge() {
    var todo = state4.payments.filter(function (p) {
      return p.status === "PROOF_SUBMITTED" || p.status === "REFUND_REQUIRED";
    }).length;
    var b = $("ph-nav-badge-payments");
    if (b) {
      if (todo > 0) {
        b.textContent = todo > 99 ? "99+" : String(todo);
        b.classList.remove("hidden");
      } else {
        b.classList.add("hidden");
      }
    }
  }

  // Actions
  function validatePayment(paymentId, ref) {
    if (!window.EHModal) {
      if (!confirm("Valider le paiement de " + ref + " ?")) return;
      doValidate(paymentId);
      return;
    }
    window.EHModal.confirm("Valider le paiement ?",
      "Commande " + ref + " - cette action est definitive.")
      .then(function (ok) { if (ok) doValidate(paymentId); });
  }

  function doValidate(paymentId) {
    fetch(API + "/payments/" + paymentId + "/verify", {
      method: "PATCH",
      credentials: "same-origin"
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    }).then(function () {
      load();
      if (window.phLoadOrdersV2) window.phLoadOrdersV2();
      drawerRefreshIfOpen();
    }).catch(function (e) {
      if (window.EHModal) window.EHModal.alert("Erreur", e.message, "danger");
      else alert(e.message);
    });
  }
  // V2 : exposer sur window pour le drawer
  window.ehPhValidatePayment = validatePayment;

  function rejectPayment(paymentId, ref) {
    var html = '<div class="ph-pay-reasons">';
    REJECT_REASONS.forEach(function (r, i) {
      html += '<label><input type="radio" name="ph-reason" value="' + esc(r) + '"' + (i === 0 ? ' checked' : '') + '> ' + esc(r) + '</label>';
    });
    html += '</div>';
    html += '<div style="margin-top:10px">';
    html += '<label style="font-size:12px;font-weight:700;color:#0f172a;display:block;margin-bottom:6px">Precision (obligatoire pour Autre)</label>';
    html += '<textarea id="ph-reject-detail" rows="2" maxlength="300" placeholder="Detail..." style="width:100%;padding:10px 12px;border:1.5px solid #e2e8f0;border-radius:10px;font-family:inherit;font-size:13.5px;resize:vertical"></textarea>';
    html += '</div>';

    if (!window.EHModal) {
      var reason = prompt("Motif du refus :");
      if (!reason) return;
      doReject(paymentId, reason);
      return;
    }

    // Modale custom
    var modal = document.createElement("div");
    modal.className = "ph-pay-reject-backdrop";
    modal.style.cssText = "position:fixed !important;top:0 !important;left:0 !important;right:0 !important;bottom:0 !important;z-index:10002 !important;background:rgba(15,23,42,.55) !important;display:flex !important;align-items:center !important;justify-content:center !important;padding:16px !important;opacity:1 !important;pointer-events:auto !important;";
    modal.innerHTML =
      '<div style="background:#fff;border-radius:16px;max-width:440px;width:100%;box-shadow:0 24px 60px rgba(15,23,42,.3);max-height:90vh;overflow-y:auto">' +
        '<div style="padding:18px 22px 8px"><h3 style="font-size:17px;font-weight:800;color:#0F172A;margin:0 0 4px">Refuser le paiement</h3>' +
        '<p style="font-size:13.5px;color:#64748B;margin:0">Commande ' + esc(ref) + '</p></div>' +
        '<div style="padding:12px 22px">' + html + '</div>' +
        '<div style="padding:14px 22px 20px;display:flex;gap:8px;justify-content:flex-end">' +
          '<button type="button" class="ph-cancel-btn" style="padding:11px 20px;border-radius:10px;border:1px solid #E2E8F0;background:#fff;font-family:inherit;font-size:14px;font-weight:800;cursor:pointer">Annuler</button>' +
          '<button type="button" class="ph-reject-btn" style="padding:11px 20px;border-radius:10px;border:0;background:#B23C3C;color:#fff;font-family:inherit;font-size:14px;font-weight:800;cursor:pointer">Refuser</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(modal);

    function close() { if (modal.parentNode) modal.parentNode.removeChild(modal); }

    modal.querySelector(".ph-cancel-btn").addEventListener("click", close);

    modal.querySelector(".ph-reject-btn").addEventListener("click", function () {
      var sel = modal.querySelector('input[name="ph-reason"]:checked');
      var reason = sel ? sel.value : "";
      var detail = (modal.querySelector("#ph-reject-detail").value || "").trim();
      if (!reason) { alert("Choisissez un motif"); return; }
      if (reason === "Autre (precisez)" && !detail) {
        alert("Precisez le motif");
        return;
      }
      var finalReason = reason === "Autre (precisez)" ? detail : reason + (detail ? " - " + detail : "");
      doReject(paymentId, finalReason, close);
    });

    modal.addEventListener("click", function (ev) {
      if (ev.target === modal) close();
    });
  }

  function doReject(paymentId, reason, onDone) {
    fetch(API + "/payments/" + paymentId + "/reject", {
      method: "PATCH",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rejection_reason: reason })
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    }).then(function () {
      if (onDone) onDone();
      load();
      if (window.phLoadOrdersV2) window.phLoadOrdersV2();
      drawerRefreshIfOpen();
    }).catch(function (e) {
      if (window.EHModal) window.EHModal.alert("Erreur", e.message, "danger");
      else alert(e.message);
    });
  }
  // V2 : exposer sur window pour le drawer
  window.ehPhRejectPayment = rejectPayment;

  function refundPayment(paymentId, ref) {
    if (!window.EHModal) {
      if (!confirm("Marquer rembourse ?")) return;
      doRefund(paymentId);
      return;
    }
    window.EHModal.confirmDanger("Marquer comme rembourse ?",
      "Commande " + ref + " - action definitive, a utiliser apres remboursement effectif.",
      "Marquer rembourse").then(function (ok) { if (ok) doRefund(paymentId); });
  }

  function doRefund(paymentId) {
    fetch(API + "/payments/" + paymentId + "/refund", {
      method: "PATCH",
      credentials: "same-origin"
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    }).then(function () {
      load();
      drawerRefreshIfOpen();
    }).catch(function (e) {
      if (window.EHModal) window.EHModal.alert("Erreur", e.message, "danger");
      else alert(e.message);
    });
  }
  // V2 : exposer sur window pour le drawer
  window.ehPhRefundPayment = refundPayment;

  // Event delegation
  document.addEventListener("click", function (ev) {
    var t = ev.target;
    var proof = t.closest ? t.closest("[data-ph-open-proof]") : null;
    if (proof) {
      ev.preventDefault();
      openLightbox(proof.getAttribute("data-ph-open-proof"));
      return;
    }
    var v = t.closest ? t.closest("[data-ph-validate]") : null;
    if (v) {
      ev.preventDefault();
      validatePayment(v.getAttribute("data-ph-validate"), v.getAttribute("data-ph-ref"));
      return;
    }
    var r = t.closest ? t.closest("[data-ph-reject]") : null;
    if (r) {
      ev.preventDefault();
      rejectPayment(r.getAttribute("data-ph-reject"), r.getAttribute("data-ph-ref"));
      return;
    }
    var rf = t.closest ? t.closest("[data-ph-refund]") : null;
    if (rf) {
      ev.preventDefault();
      refundPayment(rf.getAttribute("data-ph-refund"), rf.getAttribute("data-ph-ref"));
      return;
    }
    var chip = t.closest ? t.closest("[data-ph-pay-filter]") : null;
    if (chip) {
      ev.preventDefault();
      var f = chip.getAttribute("data-ph-pay-filter");
      state4.filter = f;
      document.querySelectorAll("[data-ph-pay-filter]").forEach(function (c) {
        c.classList.toggle("active", c === chip);
      });
      renderList();
      return;
    }
  });

  // Init
  function init() {
    // Verifier que le conteneur existe
    var page = document.querySelector('[data-ph-page="paiements"]');
    if (!page) return;
    if ($("ph-pay-list")) return;  // deja injecte

    // Construire la structure
    page.innerHTML =
      '<div class="ph-pay-page"><div class="ph-pay-wrap">' +
        '<div class="ph-pay-head">' +
          '<div>' +
            '<h1 class="ph-pay-title">Paiements</h1>' +
            '<p class="ph-pay-sub" id="ph-pay-count">—</p>' +
          '</div>' +
        '</div>' +
        '<div class="ph-pay-chips">' +
          '<button type="button" class="ph-pay-chip active" data-ph-pay-filter="todo">A traiter</button>' +
          '<button type="button" class="ph-pay-chip" data-ph-pay-filter="history">Historique</button>' +
          '<button type="button" class="ph-pay-chip" data-ph-pay-filter="all">Tous</button>' +
        '</div>' +
        '<div id="ph-pay-list" class="ph-pay-list"></div>' +
      '</div></div>';
    load();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Recharger quand on clique sur l'onglet Paiements
  document.addEventListener("click", function (ev) {
    var tab = ev.target.closest ? ev.target.closest('[data-ph-tab="paiements"]') : null;
    if (tab) setTimeout(load, 50);
  });

  // SSE
  document.addEventListener("eh:refresh", function () {
    if (document.body.getAttribute("data-active-page") === "paiements") {
      load();
    } else {
      // Mettre a jour juste le badge
      fetch(API + "/payments", { credentials: "same-origin" })
        .then(function (r) { return r.ok ? r.json() : []; })
        .then(function (list) {
          state4.payments = Array.isArray(list) ? list : [];
          updateBadge();
        })
        .catch(function () {});
    }
  });
})();

/* ============================================================
   PHARMACIEN V6 - Vue Ordonnances (Step 5)
   ============================================================ */
(function () {
  "use strict";
  var API = "/api";
  var state5 = { presc: [], filter: "todo" };

  var PRESC_LABELS = {
    "PENDING": "En attente",
    "NEEDS_REVIEW": "A verifier",
    "APPROVED": "Approuvee",
    "REJECTED": "Refusee"
  };

  function $(id) { return document.getElementById(id); }

  function fmtDate(iso) {
    if (!iso) return "";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return iso;
      var pad = function (n) { return n < 10 ? "0" + n : "" + n; };
      return pad(d.getDate()) + "/" + pad(d.getMonth()+1) + "/" + d.getFullYear()
        + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
    } catch (e) { return iso; }
  }

  function esc(s) {
    try {
      return String(s == null ? "" : s)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    } catch (e) { return ""; }
  }

  function fileUrl(f) {
    if (!f) return "";
    if (f.indexOf("/api/files/") === 0) return f;
    if (f.indexOf("/uploads/") === 0) return f.replace("/uploads/", "/api/files/");
    return f;
  }

  function applyFilter(list) {
    if (state5.filter === "todo") {
      return list.filter(function (p) {
        return p.status === "PENDING" || p.status === "NEEDS_REVIEW";
      });
    }
    if (state5.filter === "history") {
      return list.filter(function (p) {
        return p.status !== "PENDING" && p.status !== "NEEDS_REVIEW";
      });
    }
    return list;
  }

  function renderCard(p) {
    var card = document.createElement("article");
    card.className = "ph-presc-card";
    var url = fileUrl(p.file_path);
    var h = '';

    // Thumb
    if (url) {
      h += '<div class="ph-presc-thumb" data-ph-open-presc="' + esc(url) + '">';
      h += '<img src="' + esc(url) + '" alt="Ordonnance" loading="lazy" onerror="this.parentNode.innerHTML=\'&#128196;\'">';
      h += '<span class="ph-presc-zoom">&#128269;</span>';
      h += '</div>';
    } else {
      h += '<div class="ph-presc-thumb"><span class="ph-presc-ph">&#128196;</span></div>';
    }

    // Info
    h += '<div class="ph-presc-info">';
    h += '<div class="ph-presc-ref">' + esc(p.order_reference || "") + '</div>';
    h += '<div class="ph-presc-client">' + esc(p.customer_name || "Client") + '</div>';
    if (p.phone) h += '<div class="ph-presc-meta">&#128222; ' + esc(p.phone) + '</div>';
    h += '<span class="ph-presc-pill ph-presc-pill-' + esc((p.status||"").toUpperCase()) + '">' + esc(PRESC_LABELS[p.status] || p.status) + '</span>';
    if (p.comment) {
      h += '<div style="margin-top:6px;font-size:12px;color:#64748B">Motif : ' + esc(p.comment) + '</div>';
    }
    if (p.created_at) {
      h += '<div style="margin-top:6px;font-size:11.5px;color:#94a3b8">' + esc(fmtDate(p.created_at)) + '</div>';
    }
    h += '</div>';

    // Actions
    h += '<div class="ph-presc-actions">';
    if (p.status === "PENDING" || p.status === "NEEDS_REVIEW") {
      h += '<button type="button" class="ph-btn ph-btn-primary" data-ph-pa="approve" data-ph-pid="' + p.id + '" data-ph-ref="' + esc(p.order_reference) + '">Approuver</button>';
      h += '<button type="button" class="ph-btn ph-btn-danger" data-ph-pa="reject" data-ph-pid="' + p.id + '" data-ph-ref="' + esc(p.order_reference) + '">Rejeter</button>';
      h += '<button type="button" class="ph-btn ph-btn-ghost" data-ph-pa="clarify" data-ph-pid="' + p.id + '" data-ph-ref="' + esc(p.order_reference) + '">Demander clarification</button>';
    } else {
      h += '<div style="font-size:12px;color:#64748B;text-align:center">Traitee</div>';
    }
    h += '</div>';

    card.innerHTML = h;
    return card;
  }

  function renderList() {
    var box = $("ph-presc-list");
    if (!box) return;
    var filtered = applyFilter(state5.presc);
    var countEl = $("ph-presc-count");
    if (countEl) {
      countEl.textContent = filtered.length + " ordonnance" + (filtered.length > 1 ? "s" : "");
    }
    if (filtered.length === 0) {
      box.innerHTML = '<div class="ph-presc-empty">' +
        '<span style="font-size:48px;opacity:.35;display:block;margin-bottom:12px">&#128203;</span>' +
        '<strong>Aucune ordonnance</strong></div>';
      return;
    }
    box.innerHTML = "";
    filtered.forEach(function (p) { box.appendChild(renderCard(p)); });
  }

  function load() {
    var box = $("ph-presc-list");
    if (box) box.innerHTML = '<div class="ph-presc-empty">Chargement...</div>';
    fetch(API + "/prescriptions", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (list) {
        state5.presc = Array.isArray(list) ? list : [];
        renderList();
        updateBadge();
      })
      .catch(function () {
        if (box) box.innerHTML = '<div class="ph-presc-empty">Erreur de chargement</div>';
      });
  }

  function updateBadge() {
    var todo = state5.presc.filter(function (p) {
      return p.status === "PENDING" || p.status === "NEEDS_REVIEW";
    }).length;
    var b = $("ph-nav-badge-presc");
    if (b) {
      if (todo > 0) {
        b.textContent = todo > 99 ? "99+" : String(todo);
        b.classList.remove("hidden");
      } else {
        b.classList.add("hidden");
      }
    }
  }

  function openLightbox(url) {
    var lb = $("ph-pay-lightbox");
    if (!lb) {
      // Reuse from payments if exists, else create
      lb = document.createElement("div");
      lb.id = "ph-pay-lightbox";
      lb.className = "ph-pay-lightbox hidden";
      lb.innerHTML = '<button class="ph-pay-lightbox-close" aria-label="Fermer">&times;</button><img alt="Apercu">';
      document.body.appendChild(lb);
      lb.addEventListener("click", function (ev) {
        if (ev.target === lb || ev.target.classList.contains("ph-pay-lightbox-close")) {
          lb.classList.add("hidden");
        }
      });
      document.addEventListener("keydown", function (ev) {
        if (ev.key === "Escape") lb.classList.add("hidden");
      });
    }
    lb.querySelector("img").src = url;
    lb.classList.remove("hidden");
  }

  function doReview(presId, action, comment, onDone) {
    var body = { status: action };
    if (comment) body.comment = comment;
    fetch(API + "/prescriptions/" + presId + "/review", {
      method: "PATCH",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    }).then(function () {
      if (onDone) onDone();
      load();
    }).catch(function (e) {
      if (window.EHModal) window.EHModal.alert("Erreur", e.message, "danger");
      else alert(e.message);
    });
  }

  function handleApprove(id, ref) {
    if (window.EHModal) {
      window.EHModal.confirm("Approuver l'ordonnance ?",
        "Commande " + ref).then(function (ok) {
        if (ok) doReview(id, "APPROVED", "");
      });
    } else if (confirm("Approuver " + ref + " ?")) {
      doReview(id, "APPROVED", "");
    }
  }

  function handleReject(id, ref) {
    // Prompt motif obligatoire
    if (window.EHModal && window.EHModal.prompt) {
      window.EHModal.prompt(
        "Motif du rejet",
        "Cette ordonnance sera rejetee. Le motif sera enregistre.",
        { kind: "danger", placeholder: "Ex: Illisible, incomplete...",
          requireValue: true, confirmLabel: "Rejeter", danger: true,
          maxLength: 500 }
      ).then(function (motif) {
        if (motif) doReview(id, "REJECTED", motif);
      });
    } else {
      var m = (prompt("Motif du rejet (obligatoire) :") || "").trim();
      if (m) doReview(id, "REJECTED", m);
    }
  }

  function handleClarify(id, ref) {
    if (window.EHModal && window.EHModal.prompt) {
      window.EHModal.prompt(
        "Demander une clarification",
        "Message envoye au client pour cette ordonnance.",
        { kind: "info", placeholder: "Ex: Merci d'envoyer une photo plus nette...",
          requireValue: true, confirmLabel: "Envoyer", maxLength: 500 }
      ).then(function (msg) {
        if (msg) doReview(id, "NEEDS_REVIEW", msg);
      });
    } else {
      var m = (prompt("Clarification :") || "").trim();
      if (m) doReview(id, "NEEDS_REVIEW", m);
    }
  }

  document.addEventListener("click", function (ev) {
    var t = ev.target;
    var thumb = t.closest ? t.closest("[data-ph-open-presc]") : null;
    if (thumb) {
      ev.preventDefault();
      openLightbox(thumb.getAttribute("data-ph-open-presc"));
      return;
    }
    var btn = t.closest ? t.closest("[data-ph-pa]") : null;
    if (btn) {
      ev.preventDefault();
      var action = btn.getAttribute("data-ph-pa");
      var id = btn.getAttribute("data-ph-pid");
      var ref = btn.getAttribute("data-ph-ref");
      if (action === "approve") handleApprove(id, ref);
      else if (action === "reject") handleReject(id, ref);
      else if (action === "clarify") handleClarify(id, ref);
      return;
    }
    var chip = t.closest ? t.closest("[data-ph-presc-filter]") : null;
    if (chip) {
      ev.preventDefault();
      state5.filter = chip.getAttribute("data-ph-presc-filter");
      document.querySelectorAll("[data-ph-presc-filter]").forEach(function (c) {
        c.classList.toggle("active", c === chip);
      });
      renderList();
    }
  });

  function init() {
    var page = document.querySelector('[data-ph-page="ordonnances"]');
    if (!page) return;
    if ($("ph-presc-list")) return;

    page.innerHTML =
      '<div class="ph-presc-page"><div class="ph-presc-wrap">' +
        '<div class="ph-presc-head">' +
          '<h1 class="ph-presc-title">Ordonnances</h1>' +
          '<p class="ph-presc-sub" id="ph-presc-count">—</p>' +
        '</div>' +
        '<div class="ph-presc-chips">' +
          '<button type="button" class="ph-presc-chip active" data-ph-presc-filter="todo">A traiter</button>' +
          '<button type="button" class="ph-presc-chip" data-ph-presc-filter="history">Historique</button>' +
          '<button type="button" class="ph-presc-chip" data-ph-presc-filter="all">Toutes</button>' +
        '</div>' +
        '<div id="ph-presc-list" class="ph-presc-list"></div>' +
      '</div></div>';
    load();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  document.addEventListener("click", function (ev) {
    var tab = ev.target.closest ? ev.target.closest('[data-ph-tab="ordonnances"]') : null;
    if (tab) setTimeout(load, 50);
  });

  document.addEventListener("eh:refresh", function () {
    if (document.body.getAttribute("data-active-page") === "ordonnances") {
      load();
    } else {
      fetch(API + "/prescriptions", { credentials: "same-origin" })
        .then(function (r) { return r.ok ? r.json() : []; })
        .then(function (list) {
          state5.presc = Array.isArray(list) ? list : [];
          updateBadge();
        })
        .catch(function () {});
    }
  });
})();

/* ============================================================
   PHARMACIEN V6 - Admin tabs (Step 6) + Finitions (Step 7)
   ============================================================ */
(function () {
  "use strict";

  function $(id) { return document.getElementById(id); }

  // ---- Admin sub-tabs ----
  function setupAdminTabs() {
    // V10 : desactive - les sous-onglets etaient inutiles
    return;
    // eslint-disable-next-line no-unreachable
    var page = document.querySelector('[data-ph-page="admin"]');
    if (!page) return;
    if (page.querySelector(".ph-admin-tabs")) return;

    // Trouver les sections existantes
    var prescSec = document.getElementById("prescriptions-section");
    var paySec = document.getElementById("payments-section");
    var drvSec = document.getElementById("drivers-section");
    var setSec = document.getElementById("settings-section");

    // Creer une structure de tabs
    var tabs = document.createElement("div");
    tabs.className = "ph-admin-tabs";
    tabs.innerHTML =
      '<button class="ph-admin-tab active" data-ph-admin="pharmacie">Pharmacie</button>' +
      '<button class="ph-admin-tab" data-ph-admin="tarifs">Tarifs</button>' +
      '<button class="ph-admin-tab" data-ph-admin="paiement">Paiement</button>';

    page.insertBefore(tabs, page.firstChild);

    // Trouver les champs GPS dans settings-section pour les regrouper
    // Approche simple : on garde settings-section comme "pharmacie" par defaut
    // et on cree des panels vides pour tarifs/paiement (a completer plus tard)

    function showPanel(name) {
      var panels = page.querySelectorAll(".ph-admin-panel");
      panels.forEach(function (p) {
        p.classList.toggle("active", p.getAttribute("data-ph-admin-panel") === name);
      });
      tabs.querySelectorAll(".ph-admin-tab").forEach(function (t) {
        t.classList.toggle("active", t.getAttribute("data-ph-admin") === name);
      });
    }

    // Wrap settings-section en panel
    if (setSec) {
      var panel1 = document.createElement("div");
      panel1.className = "ph-admin-panel active";
      panel1.setAttribute("data-ph-admin-panel", "pharmacie");
      setSec.parentNode.insertBefore(panel1, setSec);
      panel1.appendChild(setSec);
    }

    // Creer 2 panels vides (l'utilisateur pourra completer)
    var panel2 = document.createElement("div");
    panel2.className = "ph-admin-panel";
    panel2.setAttribute("data-ph-admin-panel", "tarifs");
    panel2.innerHTML = '<p style="color:#64748B;padding:20px 0">Parametres tarifaires : voir la section Pharmacie.</p>';
    page.appendChild(panel2);

    var panel3 = document.createElement("div");
    panel3.className = "ph-admin-panel";
    panel3.setAttribute("data-ph-admin-panel", "paiement");
    panel3.innerHTML = '<p style="color:#64748B;padding:20px 0">Parametres paiement : voir la section Pharmacie.</p>';
    page.appendChild(panel3);

    // V9 : afficher la section livreurs
    if (drvSec) {
      drvSec.style.display = "";
    }

    // Event handler
    tabs.addEventListener("click", function (ev) {
      var t = ev.target.closest ? ev.target.closest("[data-ph-admin]") : null;
      if (!t) return;
      ev.preventDefault();
      showPanel(t.getAttribute("data-ph-admin"));
    });
  }

  // ---- Bouton Export CSV ----
  function addExportButtons() {
    // Ajouter sur Commandes
    var ordHead = document.querySelector('[data-ph-page="commandes"] .ph-orders-head');
    if (ordHead && !ordHead.querySelector(".ph-export-btn")) {
      var btn = document.createElement("a");
      btn.className = "ph-export-btn";
      btn.href = "/api/export/orders.csv";
      btn.innerHTML = "&#128229; Exporter CSV";
      btn.style.cssText = "float:right";
      ordHead.appendChild(btn);
    }
    // Ajouter sur Paiements
    var payHead = document.querySelector('[data-ph-page="paiements"] .ph-pay-head');
    if (payHead && !payHead.querySelector(".ph-export-btn")) {
      var btn2 = document.createElement("a");
      btn2.className = "ph-export-btn";
      btn2.href = "/api/export/payments.csv";
      btn2.innerHTML = "&#128229; Exporter CSV";
      payHead.appendChild(btn2);
    }
  }

  // ---- Raccourcis clavier ----
  function setupKeyboard() {
    document.addEventListener("keydown", function (ev) {
      // Ne pas interferer avec les inputs
      var tag = (ev.target.tagName || "").toUpperCase();
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
      // Ne pas interferer avec les modales
      if (document.querySelector(".eh-modal-backdrop")) return;

      if (ev.key === "r" || ev.key === "R") {
        // Refresh selon la page active
        var page = document.body.getAttribute("data-active-page") || "home";
        if (page === "commandes" && window.phLoadOrdersV2) window.phLoadOrdersV2();
        else if (page === "paiements") {
          var evt = new Event("eh:refresh");
          document.dispatchEvent(evt);
        } else if (page === "ordonnances") {
          var evt2 = new Event("eh:refresh");
          document.dispatchEvent(evt2);
        } else if (window.phLoadHome) window.phLoadHome();
        ev.preventDefault();
      } else if (ev.key === "/") {
        // Focus recherche
        var s = document.querySelector("#ph-orders-search, input[type=search]");
        if (s) { s.focus(); ev.preventDefault(); }
      }
    });
  }

  function init() {
    setupAdminTabs();
    addExportButtons();
    setupKeyboard();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      setTimeout(init, 800);
    });
  } else {
    setTimeout(init, 800);
  }

  // Re-setup a chaque changement de page (les onglets sont crees dynamiquement)
  document.addEventListener("click", function (ev) {
    var tab = ev.target.closest ? ev.target.closest("[data-ph-tab]") : null;
    if (tab) {
      setTimeout(function () {
        addExportButtons();
      }, 200);
    }
  });
})();
