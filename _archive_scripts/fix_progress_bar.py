"""
fix_progress_bar.py
Remplace "Envoi 1/19" par une barre de progression avec pourcentage.
"""
from pathlib import Path
import datetime
import re
import shutil

BASE = Path(__file__).resolve().parent
PAY_JS = BASE / "static" / "payment.js"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_progress_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(PAY_JS, backup / "payment.js")
print("[OK] Backup ->", backup.name)

js = PAY_JS.read_text(encoding="utf-8")

# ============================================================
# 1. Ajouter les helpers de progress bar AVANT la fonction send
# ============================================================
HELPERS = '''
  // ============================================================
  // Barre de progression
  // ============================================================
  function showProgress(percent, label) {
    var box = document.getElementById("upload-progress");
    if (!box) {
      // Creer la barre si elle n'existe pas
      box = document.createElement("div");
      box.id = "upload-progress";
      box.className = "pay-progress";
      box.innerHTML =
        '<div class="pay-progress-label" id="upload-progress-label">Preparation...</div>' +
        '<div class="pay-progress-track">' +
          '<div class="pay-progress-fill" id="upload-progress-fill" style="width:0%"></div>' +
        '</div>' +
        '<div class="pay-progress-percent" id="upload-progress-percent">0%</div>';
      var btn = document.getElementById("submit-btn");
      if (btn && btn.parentNode) {
        btn.parentNode.insertBefore(box, btn);
      }
    }
    box.classList.remove("hidden");
    var fill = document.getElementById("upload-progress-fill");
    var pct = document.getElementById("upload-progress-percent");
    var lbl = document.getElementById("upload-progress-label");
    if (fill) fill.style.width = Math.max(0, Math.min(100, percent)) + "%";
    if (pct) pct.textContent = Math.round(percent) + "%";
    if (lbl && label) lbl.textContent = label;
  }

  function hideProgress() {
    var box = document.getElementById("upload-progress");
    if (box) box.classList.add("hidden");
  }

'''

if "function showProgress" not in js:
    anchor = "  function send() {"
    if anchor in js:
        js = js.replace(anchor, HELPERS + anchor, 1)
        print("[OK] payment.js -> helpers progress ajoutes")

# ============================================================
# 2. Remplacer la fonction send par une version avec barre
# ============================================================
old_send_pat = re.compile(
    r'  function send\(\) \{.*?\n  \}\n\n  function readAsBase64',
    re.DOTALL,
)

new_send = r'''  function send() {
    if (!state.file) { toast("Choisissez un fichier."); return; }
    var btn = $("submit-btn");
    btn.disabled = true;
    btn.innerHTML = "Preparation...";

    var paymentRef = state.ref;

    showProgress(2, "Initialisation du paiement...");

    // Etape 1 : init paiement
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
      showProgress(8, "Compression de l'image...");
      return compressImage(state.file);
    })
    .then(function (result) {
      var finalFile = result.file;
      var sizeKB = Math.round(finalFile.size / 1024);
      console.log("[payment] fichier compresse : " + sizeKB + " Ko");

      showProgress(15, "Lecture du fichier...");
      return readAsBase64(finalFile).then(function (b64) {
        return { file: finalFile, base64: b64, sizeKB: sizeKB };
      });
    })
    .then(function (payload) {
      var chunks = [];
      var b64 = payload.base64;
      for (var i = 0; i < b64.length; i += CHUNK_SIZE) {
        chunks.push(b64.substring(i, i + CHUNK_SIZE));
      }
      console.log("[payment] " + chunks.length + " morceaux");

      showProgress(20, "Preparation de l'envoi...");
      return fetch(API + "/orders/" + encodeURIComponent(paymentRef) + "/payment/proof-chunked/init", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: payload.file.name,
          content_type: payload.file.type || "image/jpeg",
          total_chunks: chunks.length,
          total_bytes: payload.file.size
        })
      })
      .then(function (r) {
        return r.json().then(function (d) {
          if (!r.ok) throw new Error(d.detail || "Erreur init upload");
          return { upload_id: d.upload_id, chunks: chunks };
        });
      });
    })
    .then(function (ctx) {
      var uploadId = ctx.upload_id;
      var chunks = ctx.chunks;
      var total = chunks.length;

      // Envoyer les morceaux avec progression
      var chain = Promise.resolve();
      chunks.forEach(function (chunk, idx) {
        chain = chain.then(function () {
          // Progression : de 20% a 95%
          var pct = 20 + Math.round(((idx) / total) * 75);
          showProgress(pct, "Envoi en cours...");
          return fetch(API + "/orders/" + encodeURIComponent(paymentRef) + "/payment/proof-chunked/chunk", {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              upload_id: uploadId,
              index: idx,
              data_base64: chunk
            })
          })
          .then(function (r) {
            if (!r.ok) {
              return r.json().then(function (d) {
                throw new Error(d.detail || "Erreur");
              });
            }
            return r.json();
          });
        });
      });
      return chain.then(function () {
        showProgress(96, "Finalisation...");
        return uploadId;
      });
    })
    .then(function (uploadId) {
      return fetch(API + "/orders/" + encodeURIComponent(paymentRef) + "/payment/proof-chunked/finalize", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upload_id: uploadId })
      })
      .then(function (r) {
        return r.json().then(function (d) {
          if (!r.ok) throw new Error(d.detail || "Erreur finalisation");
          return d;
        });
      });
    })
    .then(function () {
      showProgress(100, "&#10003; Envoyee !");
      toast("Preuve envoyee. En attente de verification.", true);
      setTimeout(function () {
        window.location.href = "/suivi?ref=" + encodeURIComponent(paymentRef);
      }, 1200);
    })
    .catch(function (e) {
      console.error("[payment] erreur:", e);
      hideProgress();
      toast(e.message || "Erreur");
      btn.disabled = false;
      btn.innerHTML = '<span>&#128172;</span> Reessayer l\'envoi';
    });
  }

  function readAsBase64'''

if old_send_pat.search(js):
    js = js.replace(old_send_pat.search(js).group(0), new_send, 1)
    print("[OK] payment.js -> send avec barre de progression")
else:
    print("[!] fonction send introuvable")

PAY_JS.write_text(js, encoding="utf-8")

# ============================================================
# 3. CSS : styles de la barre
# ============================================================
CSS_PATH = BASE / "static" / "payment.css"
# Le CSS est inline dans payment.html -> on l'ajoute dans le HTML
HTML_PATH = BASE / "static" / "payment.html"
html = HTML_PATH.read_text(encoding="utf-8")
shutil.copy2(HTML_PATH, backup / "payment.html")

PROGRESS_CSS = '''
/* -------- Barre de progression upload -------- */
.pay-progress{
  background:#fff;border:1px solid var(--line);
  border-radius:12px;padding:14px 16px;margin-top:14px;
}
.pay-progress.hidden{display:none !important}
.pay-progress-label{
  font-size:13px;font-weight:700;color:var(--ink);
  margin:0 0 10px;display:flex;align-items:center;gap:6px;
}
.pay-progress-track{
  height:8px;background:#eef2f7;border-radius:999px;overflow:hidden;
}
.pay-progress-fill{
  height:100%;background:linear-gradient(90deg,var(--blue),#2a6ba8);
  border-radius:999px;transition:width .3s cubic-bezier(.4,0,.2,1);
  box-shadow:0 0 8px rgba(26,74,127,.3);
}
.pay-progress-percent{
  font-size:13px;font-weight:800;color:var(--blue-dark);
  text-align:right;margin-top:8px;
  font-family:Consolas,monospace;
}
'''

if ".pay-progress" not in html:
    html = html.replace("</style>", PROGRESS_CSS + "\n</style>", 1)
    HTML_PATH.write_text(html, encoding="utf-8")
    print("[OK] payment.html -> styles barre de progression")
else:
    print("[i] styles barre deja presents")

print()
print("=" * 60)
print("BARRE DE PROGRESSION LIVREE")
print("=" * 60)
print()
print("Affichage pendant l'upload :")
print("  - Label : 'Envoi en cours...', 'Compression...', etc.")
print("  - Barre qui se remplit progressivement")
print("  - Pourcentage : 2%, 8%, 15%, 20%, 45%, 70%, 96%, 100%")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur iPhone (ou navigation privee)")
print("  Pas besoin de redemarrer Uvicorn")