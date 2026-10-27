"""
v5_payment_blue.py
Aligne la page de paiement sur la palette bleue Elokinab.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_payment_blue_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(STATIC / "payment.html", backup / "payment.html")
shutil.copy2(STATIC / "payment.js", backup / "payment.js")
print("[OK] Backup ->", backup.name)

# ============================================================
# Nouvelle page payment.html (bleu)
# ============================================================
PAYMENT_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Paiement - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
:root{
  --blue:#1a4a7f;--blue-dark:#123258;--blue-soft:#eaf1f9;
  --wa:#25d366;--wa-dark:#1da851;
  --ink:#0f172a;--muted:#64748b;--line:#e6ebf1;--bg:#f7fafc;
  --radius:14px;
}
*,*::before,*::after{box-sizing:border-box}
html,body{overflow-x:clip;margin:0;padding:0}
body{
  font-family:-apple-system,"Segoe UI",system-ui,sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.5;font-size:15px;
  -webkit-font-smoothing:antialiased;padding-bottom:40px;
}
a{color:inherit;text-decoration:none}
button{font-family:inherit;cursor:pointer}
.hidden{display:none !important}

.pay-header{
  background:#fff;border-bottom:1px solid var(--line);
  position:sticky;top:0;z-index:50;
}
.pay-header-inner{
  max-width:560px;margin:0 auto;padding:12px 16px;
  display:flex;align-items:center;gap:12px;
}
.pay-back{
  width:36px;height:36px;border-radius:10px;border:1px solid var(--line);
  background:#fff;color:var(--ink);font-size:18px;
  display:flex;align-items:center;justify-content:center;text-decoration:none;
}
.pay-title{font-size:15px;font-weight:800;flex:1}
.pay-ref{margin-left:auto;font-family:Consolas,monospace;font-size:11px;color:var(--muted)}

.pay-main{max-width:560px;margin:0 auto;padding:18px 16px}

.pay-status-pill{
  display:inline-flex;align-items:center;gap:6px;
  padding:5px 12px;border-radius:999px;
  font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;
  margin-bottom:14px;
}
.pay-status-pill::before{
  content:"";width:7px;height:7px;border-radius:50%;background:currentColor;
}
.status-NONE{background:#e2e8f0;color:#475569}
.status-PENDING{background:#fff7e6;color:#8a5a00}
.status-PROOF_SUBMITTED{background:var(--blue-soft);color:var(--blue-dark)}
.status-VERIFIED{background:#e6f7f1;color:#0a7a5a}
.status-REJECTED{background:#fee2e2;color:#b23c3c}

.pay-amount-card{
  background:#fff;border:1px solid var(--line);border-radius:var(--radius);
  padding:20px;text-align:center;margin-bottom:14px;
}
.pay-amount-label{
  font-size:11px;font-weight:800;color:var(--muted);
  text-transform:uppercase;letter-spacing:.08em;margin:0 0 6px;
}
.pay-amount-value{
  font-size:32px;font-weight:800;color:var(--blue-dark);
  font-family:Consolas,monospace;line-height:1;margin:0;
}
.pay-amount-hint{
  font-size:12px;color:var(--muted);margin:8px 0 0;
}

.pay-number-card{
  background:#fff;border:2px dashed var(--blue);border-radius:var(--radius);
  padding:20px;text-align:center;margin-bottom:14px;
}
.pay-number-label{
  font-size:11px;font-weight:800;color:var(--muted);
  text-transform:uppercase;letter-spacing:.08em;margin:0 0 8px;
}
.pay-number-value{
  font-size:22px;font-weight:800;color:var(--ink);
  font-family:Consolas,monospace;letter-spacing:.05em;margin:0;
}
.pay-number-name{
  font-size:13px;color:var(--muted);margin:6px 0 14px;
}
.pay-copy-btn{
  background:var(--blue);color:#fff;border:0;
  padding:10px 18px;border-radius:10px;
  font-weight:800;font-size:13px;
}
.pay-copy-btn:hover{background:var(--blue-dark)}

.pay-steps{
  background:#fff;border:1px solid var(--line);border-radius:var(--radius);
  padding:16px 18px;margin-bottom:14px;
}
.pay-steps ol{
  margin:0;padding-left:22px;
  font-size:13.5px;color:var(--ink);line-height:1.7;
}
.pay-steps li{margin-bottom:6px}
.pay-steps li:last-child{margin-bottom:0}

.pay-field{display:flex;flex-direction:column;gap:8px;margin-bottom:14px}
.pay-field label{
  font-size:12px;font-weight:800;color:var(--muted);
  text-transform:uppercase;letter-spacing:.06em;
}
.pay-upload{
  border:2px dashed var(--line);border-radius:12px;
  padding:22px 16px;text-align:center;background:#fafbfc;
  cursor:pointer;display:block;
}
.pay-upload:hover{border-color:var(--blue);background:var(--blue-soft)}
.pay-upload input{display:none}
.pay-upload-icon{font-size:28px;margin-bottom:6px;color:var(--blue)}
.pay-upload-title{font-size:14px;font-weight:700;margin:0 0 4px;color:var(--ink)}
.pay-upload-hint{font-size:12px;color:var(--muted);margin:0}
.pay-file-info{
  margin-top:10px;padding:10px 12px;
  background:var(--blue-soft);color:var(--blue-dark);
  border-radius:10px;font-size:13px;font-weight:700;
  display:flex;align-items:center;gap:8px;
}

.pay-submit{
  width:100%;padding:15px;border:0;border-radius:13px;
  background:var(--blue);color:#fff;font-weight:800;font-size:15px;
  display:flex;align-items:center;justify-content:center;gap:8px;
  transition:.15s;margin-top:6px;
}
.pay-submit:hover:not(:disabled){background:var(--blue-dark);transform:translateY(-1px)}
.pay-submit:disabled{background:#c7d5e3;cursor:not-allowed}

.pay-link{
  display:block;text-align:center;margin-top:16px;
  font-size:13px;font-weight:700;color:var(--blue);
}
.pay-link:hover{color:var(--blue-dark)}

.pay-proof-link{
  display:inline-flex;align-items:center;gap:6px;
  margin-top:8px;font-size:13px;font-weight:700;color:var(--blue);
}

.pay-info{
  background:var(--blue-soft);border:1px solid #cddff0;
  border-radius:12px;padding:12px 14px;
  font-size:12.5px;color:var(--blue-dark);
  margin-top:14px;line-height:1.5;
}
.pay-info strong{font-weight:800}

.pay-error{
  background:#fee2e2;color:#b23c3c;border:1px solid #f6d2d2;
  border-radius:12px;padding:12px 14px;
  font-size:13px;margin-top:12px;
}
.pay-success{
  background:#e6f7f1;color:#0a7a5a;border:1px solid #c7e9dc;
  border-radius:12px;padding:12px 14px;
  font-size:13px;margin-top:12px;
}

.pay-toast{
  position:fixed;left:50%;bottom:24px;transform:translateX(-50%);
  background:#0f172a;color:#fff;padding:12px 18px;border-radius:12px;
  font-size:13px;font-weight:600;z-index:1000;
  box-shadow:0 10px 30px rgba(0,0,0,.2);
  max-width:calc(100vw - 32px);text-align:center;
}
.pay-toast.ok{background:#0a7a5a}
</style>
</head>
<body>

<header class="pay-header">
  <div class="pay-header-inner">
    <a class="pay-back" href="/professionnel/commandes" aria-label="Retour">&#8592;</a>
    <span class="pay-title">Paiement</span>
    <span class="pay-ref" id="page-ref">—</span>
  </div>
</header>

<main class="pay-main" id="main">
  <div style="text-align:center;padding:40px;color:#64748b">Chargement...</div>
</main>

<script src="/static/safe_locale.js"></script>
<script src="/static/payment.js"></script>
</body>
</html>
'''
(STATIC / "payment.html").write_text(PAYMENT_HTML, encoding="utf-8")
print("[OK] payment.html -> palette bleue")

# ============================================================
# Nouveau payment.js (aligne avec le nouveau HTML)
# ============================================================
PAYMENT_JS = r'''/* Elokinab Health - Page paiement */
(function () {
  var API = "/api";
  var $ = function (id) { return document.getElementById(id); };

  var state = {
    ref: null,
    payment: null,
    file: null
  };

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

  function api(method, path, body) {
    var opts = {
      method: method, credentials: "same-origin",
      headers: { "Accept": "application/json" }
    };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(API + path, opts).then(function (r) {
      if (r.status === 401) {
        window.location.href = "/connexion?next=" + encodeURIComponent(window.location.pathname + window.location.search);
        throw new Error("Non authentifie");
      }
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    });
  }

  function toast(msg, ok) {
    var t = document.createElement("div");
    t.className = "pay-toast" + (ok ? " ok" : "");
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 2600);
  }

  // ============================================================
  // Chargement
  // ============================================================
  function load() {
    var params = new URLSearchParams(window.location.search);
    state.ref = params.get("ref");
    if (!state.ref) {
      $("main").innerHTML = '<div class="pay-error">Reference de commande manquante.</div>';
      return;
    }
    $("page-ref").textContent = state.ref;
    fetchPayment();
  }

  function fetchPayment() {
    return fetch(API + "/orders/" + encodeURIComponent(state.ref) + "/payment", {
      credentials: "same-origin"
    }).then(function (r) {
      if (r.status === 401) {
        window.location.href = "/connexion?next=" +
          encodeURIComponent(window.location.pathname + window.location.search);
        throw new Error("Non authentifie");
      }
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    }).then(function (p) {
      state.payment = p;
      render();
    }).catch(function (e) {
      $("main").innerHTML = '<div class="pay-error">Erreur : ' + escapeHtml(e.message) + '</div>';
    });
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

    // Statut
    html += '<div class="pay-status-pill status-' + status + '">' +
            escapeHtml(statusLabels[status] || status) + '</div>';

    // Montant
    html += '<div class="pay-amount-card">' +
              '<p class="pay-amount-label">Montant a payer</p>' +
              '<p class="pay-amount-value">' + money(p.amount || 0) + '</p>' +
              '<p class="pay-amount-hint">' + escapeHtml(state.ref) + '</p>' +
            '</div>';

    // Numero de paiement
    var payNum = p.payment_number || "(non configure)";
    var payName = p.payment_name || "";
    html += '<div class="pay-number-card">' +
              '<p class="pay-number-label">Effectuez le transfert au</p>' +
              '<p class="pay-number-value">' + escapeHtml(payNum) + '</p>' +
              (payName ? '<p class="pay-number-name">' + escapeHtml(payName) + '</p>' : '') +
              '<button class="pay-copy-btn" type="button" id="copy-btn">Copier le numero</button>' +
            '</div>';

    // Etapes
    html += '<div class="pay-steps">' +
              '<ol>' +
                '<li>Effectuez le transfert du montant exact.</li>' +
                '<li>Prenez une capture d\\'ecran du recu.</li>' +
                '<li>Chargez la capture ci-dessous.</li>' +
                '<li>La pharmacie verifiera votre paiement.</li>' +
              '</ol>' +
            '</div>';

    // Statut verifie
    if (status === "VERIFIED") {
      html += '<div class="pay-success">&#10003; Votre paiement a ete verifie par la pharmacie. Votre commande est en cours de preparation.</div>';
      html += '<a class="pay-link" href="/suivi?ref=' + encodeURIComponent(state.ref) + '">Suivre ma commande &#8594;</a>';
      $("main").innerHTML = html;
      bindEvents();
      return;
    }

    if (status === "REJECTED" && p.rejection_reason) {
      html += '<div class="pay-error">Paiement refuse : ' + escapeHtml(p.rejection_reason) + '</div>';
    }

    // Upload preuve
    html += '<div class="pay-field">' +
              '<label for="proof">Preuve de paiement</label>' +
              '<label class="pay-upload" for="proof">' +
                '<input type="file" id="proof" accept="image/*,application/pdf">' +
                '<div class="pay-upload-icon">&#128196;</div>' +
                '<p class="pay-upload-title">Choisir un fichier ou une photo</p>' +
                '<p class="pay-upload-hint">JPG, PNG, PDF · 10 Mo max</p>' +
              '</label>' +
              '<div id="file-info" class="pay-file-info hidden"></div>' +
            '</div>';

    // Bouton envoyer
    html += '<button class="pay-submit" id="submit-btn" type="button" disabled>' +
              '<span>&#128172;</span> Envoyer la preuve' +
            '</button>';

    // Lien vers suivi
    html += '<a class="pay-link" href="/suivi?ref=' + encodeURIComponent(state.ref) + '">Suivre ma commande &#8594;</a>';

    // Info
    html += '<div class="pay-info">' +
              '<strong>Important :</strong> la preuve de paiement est verifiee manuellement par la pharmacie. ' +
              'Vous serez notifie une fois le paiement valide.' +
            '</div>';

    // Preuve existante
    if (p.proof_file) {
      html += '<div class="pay-info">' +
                'Preuve envoyee : <a class="pay-proof-link" target="_blank" rel="noopener" href="' + escapeHtml(p.proof_file) + '">Voir la preuve</a>' +
              '</div>';
    }

    $("main").innerHTML = html;
    bindEvents();
  }

  // ============================================================
  // Evenements
  // ============================================================
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
      navigator.clipboard.writeText(n).then(function () {
        toast("Numero copie", true);
      });
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
    info.innerHTML = '<span>&#10003;</span>' + escapeHtml(f.name) +
                     ' · ' + Math.round(f.size / 1024) + ' Ko';
    info.classList.remove("hidden");
    submit.disabled = false;
  }

  function send() {
    if (!state.file) { toast("Choisissez un fichier."); return; }
    var btn = $("submit-btn");
    btn.disabled = true;
    btn.innerHTML = "Envoi en cours...";

    // 1. Initier le paiement
    api("POST", "/orders/" + encodeURIComponent(state.ref) + "/payment", {
      payment_method: "MANUAL"
    }).then(function () {
      // 2. Upload la preuve
      var fd = new FormData();
      fd.append("file", state.file);
      return fetch(API + "/orders/" + encodeURIComponent(state.ref) + "/payment/proof", {
        method: "POST",
        credentials: "same-origin",
        body: fd
      }).then(function (r) {
        return r.json().then(function (d) {
          if (!r.ok) throw new Error(d.detail || "Erreur");
          return d;
        });
      });
    }).then(function () {
      toast("Preuve envoyee. En attente de verification.", true);
      setTimeout(function () {
        window.location.href = "/suivi?ref=" + encodeURIComponent(state.ref);
      }, 1500);
    }).catch(function (e) {
      toast(e.message);
      btn.disabled = false;
      btn.innerHTML = '<span>&#128172;</span> Envoyer la preuve';
    });
  }

  document.addEventListener("DOMContentLoaded", load);
})();
'''
(STATIC / "payment.js").write_text(PAYMENT_JS, encoding="utf-8")
print("[OK] payment.js -> palette bleue")

print()
print("=" * 60)
print("PAGE PAIEMENT ALIGNEE SUR LE BLEU")
print("=" * 60)
print()
print("Changements :")
print("  - Fond gris clair (au lieu de gradient vert)")
print("  - Cartes blanches avec bordures fines")
print("  - Bleu #1a4a7f pour le montant + boutons")
print("  - Statut affiche en pilule (6 couleurs selon etat)")
print("  - Numero de paiement dans une carte bordure pointillee bleue")
print("  - Upload avec zone dashed")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur le navigateur")
print("  (pas besoin de redemarrer Uvicorn)")