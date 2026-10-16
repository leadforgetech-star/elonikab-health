/* Elonikab Health - Page paiement (v10 - binaire + fallback) */
(function () {
  var API = "/api";
  var $ = function (id) { return document.getElementById(id); };

  var state = { ref: null, payment: null, file: null };
  var _loaded = false;
  var _timer = null;

  function escapeHtml(s) {
    try {
      return String(s == null ? "" : s)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    } catch (e) { return ""; }
  }

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

  function toast(msg, ok) {
    var t = document.createElement("div");
    t.className = "pay-toast" + (ok ? " ok" : "");
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 3200);
  }

  function showError(msg) {
    _loaded = true;
    if (_timer) { clearTimeout(_timer); _timer = null; }
    var main = $("main");
    if (main) {
      main.innerHTML = '<div class="pay-error">' + escapeHtml(msg) +
        '<br><br><a href="javascript:location.reload()" ' +
        'style="color:inherit;text-decoration:underline;font-weight:800">Recharger</a></div>';
    }
  }

  function b64EncodeUnicode(str) {
    try {
      return btoa(unescape(encodeURIComponent(str)));
    } catch (e) {
      return "";
    }
  }

  // ============================================================
  // Barre de progression DANS le bouton
  // ============================================================
  function setButtonProgress(percent, label) {
    var btn = $("submit-btn");
    if (!btn) return;
    var pct = Math.max(0, Math.min(100, Math.round(percent)));

    btn.style.position = "relative";
    btn.style.overflow = "hidden";
    btn.style.background = "#e8eef5";
    btn.style.padding = "0";
    btn.style.minHeight = "54px";
    btn.style.display = "flex";
    btn.style.alignItems = "center";
    btn.style.justifyContent = "center";
    btn.style.borderRadius = "12px";
    btn.style.border = "0";
    btn.style.cursor = "default";
    btn.disabled = true;

    btn.innerHTML =
      '<div style="position:absolute;top:0;left:0;bottom:0;' +
        'background:linear-gradient(90deg,#1a4a7f,#2a6ba8);' +
        'width:' + pct + '%;transition:width .4s cubic-bezier(.4,0,.2,1);z-index:0;"></div>' +
      '<div style="position:relative;z-index:1;display:flex;align-items:center;' +
        'justify-content:center;gap:8px;padding:16px 20px;width:100%;' +
        'color:#fff;font-weight:800;font-size:14px;text-shadow:0 1px 2px rgba(0,0,0,.15);">' +
        '<span>' + escapeHtml(label || "Envoi...") + '</span>' +
        '<span style="background:#fff;color:#123258;padding:2px 8px;border-radius:999px;' +
          'font-size:12px;font-weight:900;font-family:Consolas,monospace;">' + pct + '%</span>' +
      '</div>';
  }

  function resetButton() {
    var btn = $("submit-btn");
    if (!btn) return;
    btn.disabled = false;
    btn.style.cssText = "";
    btn.innerHTML = '<span>&#128172;</span> Envoyer la preuve';
  }

  // ============================================================
  // Chargement
  // ============================================================
  function load() {
    var params = new URLSearchParams(window.location.search);
    state.ref = params.get("ref");
    if (!state.ref) { showError("Reference manquante."); return; }
    var refEl = $("page-ref");
    if (refEl) refEl.textContent = state.ref;

    _timer = setTimeout(function () {
      if (!_loaded) showError("Le serveur ne repond pas.");
    }, 10000);
    fetchPayment();
  }

  function fetchPayment() {
    fetch(API + "/orders/" + encodeURIComponent(state.ref) + "/payment", {
      credentials: "same-origin"
    })
    .then(function (r) {
      if (r.status === 401) {
        showError("Vous n'etes pas connecte.");
        setTimeout(function () {
          window.location.href = "/connexion?next=" +
            encodeURIComponent(window.location.pathname + window.location.search);
        }, 2000);
        return null;
      }
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    })
    .then(function (p) {
      if (p === null) return;
      _loaded = true;
      if (_timer) { clearTimeout(_timer); _timer = null; }
      state.payment = p;
      render();
    })
    .catch(function (e) { showError(e.message); });
  }

  // ============================================================
  // Rendu
  // ============================================================
  function render() {
    var p = state.payment || {};
    var status = p.status || "NONE";

    var statusLabels = {
      NONE: "Non initie",
      PENDING: "En attente de preuve",
      PROOF_SUBMITTED: "Preuve en verification",
      VERIFIED: "Paiement verifie",
      REJECTED: "Paiement refuse"
    };

    var html = '';
    html += '<div class="pay-status-pill status-' + status + '">' +
            escapeHtml(statusLabels[status] || status) + '</div>';

    html += '<div class="pay-amount-card">' +
              '<p class="pay-amount-label">Montant a payer</p>' +
              '<p class="pay-amount-value">' + money(p.amount || 0) + '</p>' +
              '<p class="pay-amount-hint">' + escapeHtml(state.ref) + '</p>' +
            '</div>';

    var payNum = p.payment_number || "(non configure)";
    var payName = p.payment_name || "";
    html += '<div class="pay-number-card">' +
              '<p class="pay-number-label">Effectuez le transfert au</p>' +
              '<p class="pay-number-value">' + escapeHtml(payNum) + '</p>' +
              (payName ? '<p class="pay-number-name">' + escapeHtml(payName) + '</p>' : '') +
              '<button class="pay-copy-btn" type="button" id="copy-btn">Copier le numero</button>' +
            '</div>';

    html += '<div class="pay-steps">' +
              '<ol>' +
                '<li>Effectuez le transfert du montant exact.</li>' +
                '<li>Prenez une capture d\'ecran du recu.</li>' +
                '<li>Chargez la capture ci-dessous.</li>' +
                '<li>La pharmacie verifiera votre paiement.</li>' +
              '</ol>' +
            '</div>';

    if (status === "VERIFIED") {
      html += '<div class="pay-success">\u2713 Votre paiement a ete verifie.</div>';
      html += '<a class="pay-link" href="/suivi?ref=' + encodeURIComponent(state.ref) + '">Suivre ma commande &#8594;</a>';
      $("main").innerHTML = html;
      bindEvents();
      return;
    }

    if (status === "REJECTED" && p.rejection_reason) {
      html += '<div class="pay-error">Paiement refuse : ' + escapeHtml(p.rejection_reason) + '</div>';
    }

    html += '<div class="pay-field">' +
              '<label for="proof">Preuve de paiement</label>' +
              '<label class="pay-upload" for="proof">' +
                '<input type="file" id="proof" accept="image/*,application/pdf">' +
                '<div class="pay-upload-icon">&#128196;</div>' +
                '<p class="pay-upload-title">Choisir un fichier ou une photo</p>' +
                '<p class="pay-upload-hint">JPG, PNG, PDF - 25 Mo max</p>' +
              '</label>' +
              '<div id="file-info" class="pay-file-info hidden"></div>' +
            '</div>';

    html += '<button class="pay-submit" id="submit-btn" type="button" disabled>' +
              '<span>&#128172;</span> Envoyer la preuve' +
            '</button>';

    html += '<a class="pay-link" href="/suivi?ref=' + encodeURIComponent(state.ref) + '">Suivre ma commande &#8594;</a>';

    html += '<div class="pay-info">' +
              '<strong>A savoir :</strong> votre preuve sera examinee par la pharmacie. ' +
              'Vous recevrez une notification des que le paiement est valide.' +
            '</div>';

    if (p.proof_file) {
      html += '<div class="pay-info">Preuve envoyee : <a class="pay-proof-link" target="_blank" rel="noopener" href="' +
              escapeHtml(p.proof_file) + '">Voir la preuve</a></div>';
    }

    $("main").innerHTML = html;
    bindEvents();
  }

  function bindEvents() {
    var copyBtn = $("copy-btn");
    if (copyBtn) copyBtn.addEventListener("click", copyNumber);
    var fileInput = $("proof");
    if (fileInput) fileInput.addEventListener("change", onFileChange);
    var submit = $("submit-btn");
    if (submit) submit.addEventListener("click", send);
  }

  function copyNumber() {
    var n = (state.payment && state.payment.payment_number) || "";
    if (!n) { toast("Aucun numero configure"); return; }
    if (navigator.clipboard) {
      navigator.clipboard.writeText(n).then(function () { toast("Numero copie", true); });
    } else {
      toast("Copiez manuellement : " + n);
    }
  }

  function onFileChange(ev) {
    var f = ev.target.files && ev.target.files[0];
    var info = $("file-info");
    var submit = $("submit-btn");
    if (!f) {
      state.file = null;
      info.classList.add("hidden");
      submit.disabled = true;
      return;
    }
    state.file = f;
    info.innerHTML = '<span>\u2713</span>' + escapeHtml(f.name) +
                     ' - ' + Math.round(f.size / 1024) + ' Ko';
    info.classList.remove("hidden");
    submit.disabled = false;
    console.log("[payment] fichier :", f.name, Math.round(f.size / 1024) + " Ko");
  }

  // ============================================================
  // Compression (images uniquement)
  // ============================================================
  function compressImage(file) {
    return new Promise(function (resolve, reject) {
      if (!file.type || file.type.indexOf("image/") !== 0) { resolve(file); return; }
      if (file.size < 200 * 1024) { resolve(file); return; }

      var reader = new FileReader();
      reader.onerror = function () { reject(new Error("Lecture impossible")); };
      reader.onload = function (e) {
        var img = new Image();
        img.onerror = function () { reject(new Error("Image invalide")); };
        img.onload = function () {
          try {
            var w = img.width, h = img.height, maxDim = 800;
            if (w > maxDim || h > maxDim) {
              if (w > h) { h = Math.round(h * (maxDim / w)); w = maxDim; }
              else { w = Math.round(w * (maxDim / h)); h = maxDim; }
            }
            var canvas = document.createElement("canvas");
            canvas.width = w; canvas.height = h;
            var ctx = canvas.getContext("2d");
            ctx.fillStyle = "#ffffff";
            ctx.fillRect(0, 0, w, h);
            ctx.drawImage(img, 0, 0, w, h);
            canvas.toBlob(function (blob) {
              if (!blob || blob.size >= file.size) { resolve(file); return; }
              console.log("[payment] compression : " +
                Math.round(file.size/1024) + " Ko -> " + Math.round(blob.size/1024) + " Ko");
              var newName = (file.name || "image").replace(/\.[^.]+$/, "") + ".jpg";
              resolve(new File([blob], newName, { type: "image/jpeg" }));
            }, "image/jpeg", 0.5);
          } catch (err) { reject(err); }
        };
        img.src = e.target.result;
      };
      reader.readAsDataURL(file);
    });
  }

  // ============================================================
  // Upload binaire simple (1 seule requete)
  // ============================================================
  function uploadBinary(file, onProgress) {
    return new Promise(function (resolve, reject) {
      var xhr = new XMLHttpRequest();
      xhr.open("POST", API + "/orders/" + encodeURIComponent(state.ref) + "/payment/proof-binary", true);
      xhr.withCredentials = true;
      xhr.setRequestHeader("Content-Type", "application/octet-stream");
      // Encoder le nom de fichier en base64 (evite les problemes d'encoding header)
      xhr.setRequestHeader("X-Filename", b64EncodeUnicode(file.name || "proof.bin"));

      var start = Date.now();
      var progressTimer = setInterval(function () {
        var elapsed = Date.now() - start;
        // Progression estimee : 15% -> 90% sur 15 secondes max
        var pct = 15 + Math.min(75, Math.round((elapsed / 15000) * 75));
        if (onProgress) onProgress(pct);
      }, 300);

      xhr.upload.onprogress = function (e) {
        if (e.lengthComputable) {
          var pct = 15 + Math.round((e.loaded / e.total) * 80);
          if (onProgress) onProgress(pct);
        }
      };

      xhr.onload = function () {
        clearInterval(progressTimer);
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch (e) {
            resolve({});
          }
        } else {
          var msg = "Erreur " + xhr.status;
          try {
            var d = JSON.parse(xhr.responseText);
            if (d.detail) msg = d.detail;
          } catch (e) {}
          reject(new Error(msg));
        }
      };

      xhr.onerror = function () {
        clearInterval(progressTimer);
        reject(new Error("Erreur reseau"));
      };

      xhr.ontimeout = function () {
        clearInterval(progressTimer);
        reject(new Error("Delai depasse"));
      };

      xhr.timeout = 120000;
      xhr.send(file);
    });
  }

  // ============================================================
  // Envoi principal
  // ============================================================
  function send() {
    if (!state.file) { toast("Choisissez un fichier."); return; }

    var paymentRef = state.ref;

    setButtonProgress(3, "Initialisation...");

    // 1. Init paiement
    fetch(API + "/orders/" + encodeURIComponent(paymentRef) + "/payment", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payment_method: "MANUAL" })
    })
    .then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur init");
        return d;
      });
    })
    .then(function () {
      setButtonProgress(8, "Preparation...");
      return compressImage(state.file);
    })
    .then(function (finalFile) {
      console.log("[payment] upload binaire : " + Math.round(finalFile.size/1024) + " Ko");
      setButtonProgress(15, "Envoi...");

      return uploadBinary(finalFile, function (pct) {
        setButtonProgress(pct, "Envoi...");
      });
    })
    .then(function () {
      setButtonProgress(100, "\u2713 Envoyee !");
      toast("Preuve envoyee. En attente de verification.", true);
      setTimeout(function () {
        window.location.href = "/suivi?ref=" + encodeURIComponent(paymentRef);
      }, 1400);
    })
    .catch(function (e) {
      console.error("[send] erreur:", e);
      toast(e.message || "Erreur d'envoi");
      resetButton();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", load);
  } else {
    load();
  }

// Temps reel : recharger le statut paiement quand une notif SSE arrive
document.addEventListener("eh:refresh", function () {
  try { load(); } catch (e) { console.error("[payment] reload error", e); }
});

})();
