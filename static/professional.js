/* Elonikab Health - Espace professionnel B2B */
(function () {
  var API = "/api";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  var state = {
    org: null,
    draft: null,
    items: [],
    attachments: [],
    history: [],
    catalogue: []
  };

  function toast(msg, ok) {
    var t = document.createElement("div");
    t.className = "pro-toast" + (ok ? " ok" : "");
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.style.opacity = "0"; t.style.transition = "opacity .3s"; }, 2200);
    setTimeout(function () { t.remove(); }, 2600);
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }

  function api(method, path, body) {
    var opts = {
      method: method,
      credentials: "same-origin",
      headers: { "Accept": "application/json" }
    };
    if (body instanceof FormData) {
      opts.body = body;
    } else if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(API + path, opts).then(function (r) {
      if (r.status === 401) {
        window.location.href = "/connexion?next=/professionnel";
        throw new Error("Non authentifie");
      }
      return r.json().then(function (data) {
        if (!r.ok) throw new Error(data.detail || "Erreur");
        return data;
      });
    });
  }

  // ============================================================
  // ORGANISATION
  // ============================================================
  function loadOrg() {
    return api("GET", "/pro/organizations/me").then(function (org) {
      state.org = org;
      renderOrg();
    });
  }

  function renderOrg() {
    if (!state.org) return;
    var nameEl = document.getElementById("org-name");
    var typeEl = document.getElementById("org-type");
    if (nameEl) nameEl.textContent = state.org.structure_name || "Mon établissement";
    if (typeEl) {
      var map = {
        CLINIQUE: "Clinique", HOPITAL: "Hôpital",
        CABINET_MEDICAL: "Cabinet médical", LABORATOIRE: "Laboratoire",
        CENTRE_SANTE: "Centre de santé", AUTRE: "Établissement"
      };
      typeEl.textContent = map[state.org.structure_type] || "Professionnel de santé";
    }
  }

  // ============================================================
  // DRAFT (demande en cours)
  // ============================================================
  function loadDraft() {
    return api("GET", "/pro/requests/draft").then(function (draft) {
      state.draft = draft;
      return reloadDraftContent();
    });
  }

  function reloadDraftContent() {
    if (!state.draft) return Promise.resolve();
    return api("GET", "/pro/requests/" + state.draft.reference).then(function (full) {
      state.items = full.items || [];
      state.attachments = full.attachments || [];
      renderDraft();
      return full;
    });
  }

  function renderDraft() {
    var refEl = document.getElementById("draft-ref");
    var countEl = document.getElementById("draft-count");
    var itemsBox = document.getElementById("draft-items");
    var attsBox = document.getElementById("draft-attachments");
    var sendBtn = document.getElementById("send-whatsapp");

    if (refEl) refEl.textContent = state.draft ? state.draft.reference : "—";
    var total = state.items.length + state.attachments.length;
    if (countEl) countEl.textContent = total + " élément" + (total > 1 ? "s" : "");

    // Notes
    if (state.draft && document.getElementById("draft-notes")) {
      var notesEl = document.getElementById("draft-notes");
      if (!notesEl.matches(":focus") && notesEl.value !== (state.draft.notes || "")) {
        notesEl.value = state.draft.notes || "";
      }
    }

    // Items
    itemsBox.innerHTML = "";
    if (state.items.length === 0) {
      itemsBox.innerHTML =
        '<div class="pro-empty">Aucun produit pour le moment.<br>' +
        'Utilisez les boutons ci-dessous.</div>';
    } else {
      state.items.forEach(function (it) {
        var row = document.createElement("div");
        row.className = "pro-item";
        var qty = it.requested_quantity;
        var qs = (qty && qty != 1) ? " × " + (Math.round(qty * 100) / 100) : (qty == 1 ? " × 1" : "");
        row.innerHTML =
          '<div class="pro-item-info">' +
            '<div class="pro-item-name">' + escapeHtml(it.description) + '</div>' +
            '<div class="pro-item-meta">' + (qs || "quantité à préciser") +
            (it.product_id ? " · depuis catalogue" : " · saisi manuellement") +
            '</div>' +
          '</div>' +
          '<div class="pro-item-actions">' +
            '<button class="pro-item-btn" data-edit="' + it.id + '" title="Modifier">✏️</button>' +
            '<button class="pro-item-btn del" data-del="' + it.id + '" title="Supprimer">✕</button>' +
          '</div>';
        itemsBox.appendChild(row);
      });

      // Handlers
      $$("[data-del]", itemsBox).forEach(function (b) {
        b.addEventListener("click", function () {
          var id = b.getAttribute("data-del");
          api("DELETE", "/pro/requests/" + state.draft.reference + "/items/" + id)
            .then(reloadDraftContent).catch(function (e) { toast(e.message); });
        });
      });
      $$("[data-edit]", itemsBox).forEach(function (b) {
        b.addEventListener("click", function () {
          var id = parseInt(b.getAttribute("data-edit"));
          var it = state.items.filter(function (x) { return x.id === id; })[0];
          if (!it) return;
          openManual(it);
        });
      });
    }

    // Attachments
    attsBox.innerHTML = "";
    state.attachments.forEach(function (a) {
      var row = document.createElement("div");
      row.className = "pro-att";
      var ico = a.type === "pdf" ? "📄" : "📷";
      row.innerHTML =
        '<div class="pro-att-icon">' + ico + '</div>' +
        '<div class="pro-att-body">' +
          '<div class="pro-att-name">' + escapeHtml(a.original_filename || a.storage_path) + '</div>' +
          '<div class="pro-att-meta">' + (a.type === "pdf" ? "PDF" : "Photo") +
          ' · ' + Math.round((a.size_bytes || 0) / 1024) + ' Ko</div>' +
        '</div>' +
        '<button class="pro-att-del" data-del-att="' + a.id + '" title="Supprimer">✕</button>';
      attsBox.appendChild(row);
    });
    $$("[data-del-att]", attsBox).forEach(function (b) {
      b.addEventListener("click", function () {
        var id = b.getAttribute("data-del-att");
        api("DELETE", "/pro/requests/" + state.draft.reference + "/attachments/" + id)
          .then(reloadDraftContent).catch(function (e) { toast(e.message); });
      });
    });

    // Bouton envoyer
    if (sendBtn) sendBtn.disabled = total === 0;
  }

  // Enregistrer les notes automatiquement (debounce)
  var notesTimer = null;
  function attachNotesHandler() {
    var el = document.getElementById("draft-notes");
    if (!el) return;
    el.addEventListener("input", function () {
      if (!state.draft) return;
      if (notesTimer) clearTimeout(notesTimer);
      notesTimer = setTimeout(function () {
        api("PATCH", "/pro/requests/" + state.draft.reference, { notes: el.value })
          .then(function (r) { state.draft.notes = r.notes; })
          .catch(function () {});
      }, 800);
    });
  }

  // ============================================================
  // AJOUT ITEM
  // ============================================================
  function addItem(desc, qty, productId) {
    if (!state.draft) return Promise.reject(new Error("Aucune demande"));
    return api("POST", "/pro/requests/" + state.draft.reference + "/items", {
      product_id: productId || null,
      description: desc,
      requested_quantity: qty
    }).then(function () { return reloadDraftContent(); });
  }

  function updateItem(id, desc, qty) {
    return api("PATCH", "/pro/requests/" + state.draft.reference + "/items/" + id, {
      description: desc,
      requested_quantity: qty
    }).then(function () { return reloadDraftContent(); });
  }

  // ============================================================
  // UPLOAD ATTACHMENTS
  // ============================================================
  function uploadAttachment(file, type) {
    var fd = new FormData();
    fd.append("file", file);
    return api("POST", "/pro/requests/" + state.draft.reference + "/attachments", fd)
      .then(function () { return reloadDraftContent(); });
  }

  // ============================================================
  // WHATSAPP
  // ============================================================
  function sendWhatsapp() {
    if (!state.draft) return;
    var btn = document.getElementById("send-whatsapp");
    if (btn) { btn.disabled = true; btn.textContent = "Préparation..."; }
    api("GET", "/pro/requests/" + state.draft.reference + "/whatsapp").then(function (d) {
      window.open(d.whatsapp_url, "_blank");
      toast("WhatsApp ouvert. Joignez les fichiers si nécessaire.", true);
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span>💬</span> Envoyer sur WhatsApp';
      }
      // Rafraichir l'historique
      loadHistory();
    }).catch(function (e) {
      toast(e.message);
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span>💬</span> Envoyer sur WhatsApp';
      }
    });
  }

  // ============================================================
  // HISTORIQUE
  // ============================================================
  function loadHistory() {
    return api("GET", "/pro/requests").then(function (list) {
      state.history = list;
      renderHistory();
    });
  }

  function renderHistory() {
    var box = document.getElementById("history");
    box.innerHTML = "";
    var list = (state.history || []).filter(function (r) { return r.status !== "DRAFT"; });
    if (list.length === 0) {
      box.innerHTML = '<div class="pro-empty">Vous n\'avez encore envoyé aucune demande.</div>';
      return;
    }
    list.slice(0, 20).forEach(function (r) {
      var d = new Date(r.created_at);
      var dateStr = isNaN(d) ? "" : d.toLocaleDateString("fr-FR", {
        day: "2-digit", month: "short", year: "numeric"
      });
      var row = document.createElement("div");
      row.className = "pro-history-item";
      row.innerHTML =
        '<div class="pro-history-body">' +
          '<div class="pro-history-title">' + r.items_count + ' produit' + (r.items_count > 1 ? "s" : "") +
          (r.attachments_count ? " + " + r.attachments_count + " pièce" + (r.attachments_count > 1 ? "s" : "") : "") +
          '</div>' +
          '<div class="pro-history-meta">' + (dateStr || "") + ' · ' + escapeHtml(r.reference) + '</div>' +
        '</div>' +
        '<span class="pro-badge ' + r.status + '">' + statusLabel(r.status) + '</span>';
      box.appendChild(row);
    });
  }

  function statusLabel(s) {
    var m = {
      DRAFT: "Brouillon", SUBMITTED: "Envoyée",
      UNDER_REVIEW: "En cours", CONFIRMED: "Confirmée",
      PARTIALLY_CONFIRMED: "Partielle", REJECTED: "Refusée"
    };
    return m[s] || s;
  }

  // ============================================================
  // CATALOGUE
  // ============================================================
  function loadCatalogue() {
    return api("GET", "/products").then(function (list) {
      state.catalogue = list || [];
    });
  }

  function renderCatalogue(query) {
    var box = document.getElementById("m-cat-list");
    box.innerHTML = "";
    var q = (query || "").trim().toLowerCase();
    var list = state.catalogue.filter(function (p) {
      if (!q) return true;
      return (p.name || "").toLowerCase().indexOf(q) >= 0 ||
             (p.presentation || "").toLowerCase().indexOf(q) >= 0 ||
             (p.category || "").toLowerCase().indexOf(q) >= 0;
    }).slice(0, 40);

    if (list.length === 0) {
      box.innerHTML = '<div class="pro-empty">Aucun produit trouvé.</div>';
      return;
    }

    list.forEach(function (p) {
      var row = document.createElement("div");
      row.className = "pro-catalogue-item";
      var thumb = p.image_url
        ? '<img src="' + escapeHtml(p.image_url) + '" alt="" onerror="this.remove();this.parentNode.textContent=\'' + escapeHtml((p.name || "?").charAt(0)) + '\'">'
        : escapeHtml((p.name || "?").charAt(0));
      var avail = {
        disponible: "Disponible", rupture: "Indisponible",
        stock_limite: "Stock limité"
      }[p.availability] || "À confirmer";

      row.innerHTML =
        '<div class="pro-catalogue-thumb">' + thumb + '</div>' +
        '<div class="pro-catalogue-body">' +
          '<div class="pro-catalogue-name">' + escapeHtml(p.name) + '</div>' +
          '<div class="pro-catalogue-meta">' + escapeHtml(p.presentation || "") + '</div>' +
          '<div class="pro-catalogue-meta">' + avail + '</div>' +
        '</div>' +
        '<div class="pro-qty">' +
          '<input type="text" placeholder="Qté" data-qty="' + p.id + '">' +
          '<button class="pro-add-btn" style="padding:8px 12px;font-size:12px" data-add="' + p.id + '">+</button>' +
        '</div>';
      box.appendChild(row);
    });

    $$("[data-add]", box).forEach(function (b) {
      b.addEventListener("click", function () {
        var pid = parseInt(b.getAttribute("data-add"));
        var input = box.querySelector('[data-qty="' + pid + '"]');
        var qty = input && input.value ? input.value : "1";
        var p = state.catalogue.filter(function (x) { return x.id === pid; })[0];
        if (!p) return;
        var desc = p.name + (p.presentation ? " — " + p.presentation : "");
        var qtyNum = parseFloat(qty);
        addItem(desc, isNaN(qtyNum) ? 1 : qtyNum, pid)
          .then(function () {
            toast("Ajouté : " + p.name, true);
            if (input) input.value = "";
          })
          .catch(function (e) { toast(e.message); });
      });
    });
  }

  // ============================================================
  // MODALES
  // ============================================================
  function openModal(id) {
    document.getElementById(id).classList.remove("hidden");
    document.body.style.overflow = "hidden";
  }
  function closeModals() {
    $$(".pro-modal").forEach(function (m) { m.classList.add("hidden"); });
    document.body.style.overflow = "";
  }

  function openSourceChoice() {
    openModal("m-source");
  }

  function openManual(item) {
    closeModals();
    var d = document.getElementById("m-manual-desc");
    var q = document.getElementById("m-manual-qty");
    d.value = item ? item.description : "";
    q.value = item ? (item.requested_quantity || "") : "";
    document.getElementById("m-manual-err").classList.add("hidden");
    d.dataset.editId = item ? item.id : "";
    openModal("m-manual");
    setTimeout(function () { d.focus(); }, 100);
  }

  function submitManual() {
    var d = document.getElementById("m-manual-desc").value.trim();
    var qv = document.getElementById("m-manual-qty").value.trim();
    var editId = document.getElementById("m-manual-desc").dataset.editId;
    var errBox = document.getElementById("m-manual-err");

    if (!d) {
      errBox.textContent = "Le nom du produit est obligatoire.";
      errBox.classList.remove("hidden");
      return;
    }
    var qty = parseFloat(qv);
    if (isNaN(qty) || qty <= 0) qty = 1;

    var p = editId
      ? updateItem(parseInt(editId), d, qty)
      : addItem(d, qty, null);

    p.then(function () {
      closeModals();
      toast(editId ? "Ligne mise à jour" : "Ligne ajoutée", true);
    }).catch(function (e) {
      errBox.textContent = e.message;
      errBox.classList.remove("hidden");
    });
  }

  function openCatalogue() {
    closeModals();
    openModal("m-catalogue");
    var s = document.getElementById("m-cat-search");
    s.value = "";
    renderCatalogue("");
    setTimeout(function () { s.focus(); }, 100);
  }

  function openPdf() {
    closeModals();
    document.getElementById("pdf-file").value = "";
    document.getElementById("m-pdf-err").classList.add("hidden");
    openModal("m-pdf");
  }
  function openPhoto() {
    closeModals();
    document.getElementById("photo-file").value = "";
    document.getElementById("m-photo-err").classList.add("hidden");
    openModal("m-photo");
  }

  function onPdfChosen(input) {
    var f = input.files && input.files[0];
    var err = document.getElementById("m-pdf-err");
    if (!f) return;
    if (!/\.pdf$/i.test(f.name) && f.type !== "application/pdf") {
      err.textContent = "Ce fichier n'est pas compatible. Veuillez sélectionner un PDF.";
      err.classList.remove("hidden");
      return;
    }
    if (f.size > 15 * 1024 * 1024) {
      err.textContent = "Fichier trop volumineux (max 15 Mo).";
      err.classList.remove("hidden");
      return;
    }
    uploadAttachment(f, "pdf").then(function () {
      closeModals();
      toast("PDF ajouté à la demande", true);
    }).catch(function (e) {
      err.textContent = e.message;
      err.classList.remove("hidden");
    });
  }

  function onPhotoChosen(input) {
    var f = input.files && input.files[0];
    var err = document.getElementById("m-photo-err");
    if (!f) return;
    if (!/^image\//.test(f.type)) {
      err.textContent = "Cette image n'est pas compatible. Veuillez choisir un JPG, PNG ou WEBP.";
      err.classList.remove("hidden");
      return;
    }
    if (f.size > 15 * 1024 * 1024) {
      err.textContent = "Fichier trop volumineux (max 15 Mo).";
      err.classList.remove("hidden");
      return;
    }
    uploadAttachment(f, "photo").then(function () {
      closeModals();
      toast("Photo ajoutée à la demande", true);
    }).catch(function (e) {
      err.textContent = e.message;
      err.classList.remove("hidden");
    });
  }

  // ============================================================
  // INIT
  // ============================================================
  function init() {
    // Boutons ajout
    document.getElementById("add-from-catalogue").addEventListener("click", openCatalogue);
    document.getElementById("add-manual").addEventListener("click", function () { openManual(null); });
    document.getElementById("add-pdf").addEventListener("click", openPdf);
    document.getElementById("add-photo").addEventListener("click", openPhoto);
    document.getElementById("nav-new").addEventListener("click", function (e) {
      e.preventDefault();
      document.getElementById("draft-card").scrollIntoView({ behavior: "smooth" });
    });

    // Send
    document.getElementById("send-whatsapp").addEventListener("click", sendWhatsapp);

    // Clear (vide la demande en cours)
    document.getElementById("clear-draft").addEventListener("click", function () {
      if (!state.draft || !confirm("Vider la demande en cours ?")) return;
      var items = state.items.slice();
      var atts = state.attachments.slice();
      var p = Promise.resolve();
      items.forEach(function (it) {
        p = p.then(function () {
          return api("DELETE", "/pro/requests/" + state.draft.reference + "/items/" + it.id);
        });
      });
      atts.forEach(function (a) {
        p = p.then(function () {
          return api("DELETE", "/pro/requests/" + state.draft.reference + "/attachments/" + a.id);
        });
      });
      p.then(reloadDraftContent).catch(function (e) { toast(e.message); });
    });

    // Modal source
    $$("#m-source .pro-choice").forEach(function (b) {
      b.addEventListener("click", function () {
        var s = b.getAttribute("data-source");
        if (s === "manual") openManual(null);
        else if (s === "catalogue") openCatalogue();
        else if (s === "pdf") openPdf();
        else if (s === "photo") openPhoto();
      });
    });

    // Close modals
    $$("[data-close-modal]").forEach(function (b) {
      b.addEventListener("click", closeModals);
    });

    // Manual add
    document.getElementById("m-manual-add").addEventListener("click", submitManual);

    // Catalogue search
    var catSearch = document.getElementById("m-cat-search");
    if (catSearch) {
      catSearch.addEventListener("input", function () {
        renderCatalogue(catSearch.value);
      });
    }

    // File inputs
    document.getElementById("pdf-file").addEventListener("change", function () {
      onPdfChosen(this);
    });
    document.getElementById("photo-file").addEventListener("change", function () {
      onPhotoChosen(this);
    });

    // Notes
    attachNotesHandler();

    // Charger les donnees
    loadOrg()
      .then(loadCatalogue)
      .then(loadDraft)
      .then(loadHistory)
      .catch(function (e) { toast(e.message); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
