"""
fix_chunked_upload.py
Upload de preuve en morceaux de 25 Ko (contourne HTTP/2 tunnel).
- Table pending_uploads
- 3 endpoints : init / chunk / finalize
- Compression forcee JPEG 800px 50%
- Progress affiche a l'utilisateur
"""
from pathlib import Path
import datetime
import re
import shutil
import sqlite3

BASE = Path(__file__).resolve().parent
DB = BASE / "database.db"
PAY_PY = BASE / "v3_modules" / "payments.py"
PAY_JS = BASE / "static" / "payment.js"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_chunked_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(DB, backup / "database.db")
shutil.copy2(PAY_PY, backup / "payments.py")
shutil.copy2(PAY_JS, backup / "payment.js")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. Table pending_uploads
# ============================================================
conn = sqlite3.connect(DB)
conn.execute("""
    CREATE TABLE IF NOT EXISTS pending_uploads (
        id TEXT PRIMARY KEY,
        order_id INTEGER,
        payment_id INTEGER,
        user_id INTEGER,
        filename TEXT,
        content_type TEXT,
        total_chunks INTEGER,
        received_chunks INTEGER DEFAULT 0,
        data_base64 TEXT DEFAULT '',
        created_at TEXT
    )
""")
conn.execute("CREATE INDEX IF NOT EXISTS idx_pu_order ON pending_uploads(order_id)")
conn.commit()

# Nettoyer les uploads orphelins (> 1h)
cutoff = (datetime.datetime.now() - datetime.timedelta(hours=1)).isoformat(timespec="seconds")
n = conn.execute("DELETE FROM pending_uploads WHERE created_at < ?", (cutoff,)).rowcount
conn.commit()
conn.close()
print(f"[OK] Table pending_uploads (nettoyage : {n} orphelins)")

# ============================================================
# 2. Backend : endpoints chunked
# ============================================================
src = PAY_PY.read_text(encoding="utf-8")

if "proof-chunked" not in src:
    # Modeles
    if "class ChunkInit" not in src:
        src = src.replace(
            "class ProofUpload(BaseModel):",
            '''class ChunkInit(BaseModel):
    filename: str = "proof.jpg"
    content_type: str = "image/jpeg"
    total_chunks: int = 1
    total_bytes: int = 0


class ChunkData(BaseModel):
    upload_id: str
    index: int
    data_base64: str  # morceau encode en base64


class ChunkFinalize(BaseModel):
    upload_id: str


class ProofUpload(BaseModel):''',
            1,
        )
        print("[OK] payments.py -> modeles chunked")

    # Endpoints chunked - inserer avant @app.post("/api/orders/{reference}/payment/proof")
    chunked_block = '''
    @app.post("/api/orders/{reference}/payment/proof-chunked/init")
    def chunked_init(reference: str, payload: ChunkInit,
                     user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        """Demarre un upload par morceaux."""
        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE reference = ? AND user_id = ?",
                (reference, user["id"]),
            ).fetchone()
            if order is None:
                raise HTTPException(404, "Commande introuvable")

            payment = conn.execute(
                "SELECT * FROM payments WHERE order_id = ? ORDER BY id DESC LIMIT 1",
                (order["id"],),
            ).fetchone()
            if payment is None:
                raise HTTPException(400, "Initialisez le paiement d'abord")
            if payment["status"] == "VERIFIED":
                raise HTTPException(400, "Paiement deja verifie")
            if payment["status"] == "REJECTED":
                conn.execute(
                    "UPDATE payments SET status='PENDING', rejection_reason='' WHERE id=?",
                    (payment["id"],),
                )

            # Limiter la taille totale
            if payload.total_bytes > MAX_PROOF_MB * 1024 * 1024:
                raise HTTPException(
                    400, "Fichier trop volumineux (max " + str(MAX_PROOF_MB) + " Mo)"
                )

            upload_id = uuid.uuid4().hex
            now = datetime.now().isoformat(timespec="seconds")
            conn.execute(
                "INSERT INTO pending_uploads (id, order_id, payment_id, user_id,"
                " filename, content_type, total_chunks, received_chunks, data_base64, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, 0, '', ?)",
                (upload_id, order["id"], payment["id"], user["id"],
                 payload.filename, payload.content_type,
                 max(1, payload.total_chunks), now)
            )
            conn.commit()
        finally:
            conn.close()
        return {"upload_id": upload_id}


    @app.post("/api/orders/{reference}/payment/proof-chunked/chunk")
    def chunked_upload(reference: str, payload: ChunkData,
                       user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        """Recoit un morceau."""
        conn = get_db()
        try:
            up = conn.execute(
                "SELECT * FROM pending_uploads WHERE id=? AND user_id=?",
                (payload.upload_id, user["id"]),
            ).fetchone()
            if up is None:
                raise HTTPException(404, "Upload introuvable")

            # Concatener le morceau
            new_data = (up["data_base64"] or "") + payload.data_base64
            # Limiter la taille totale en memoire
            if len(new_data) > MAX_PROOF_MB * 2 * 1024 * 1024:
                raise HTTPException(400, "Fichier trop volumineux")

            conn.execute(
                "UPDATE pending_uploads SET data_base64=?, received_chunks=received_chunks+1"
                " WHERE id=?",
                (new_data, payload.upload_id)
            )
            conn.commit()
            received = up["received_chunks"] + 1
            total = up["total_chunks"]
        finally:
            conn.close()
        return {"received": received, "total": total}


    @app.post("/api/orders/{reference}/payment/proof-chunked/finalize")
    def chunked_finalize(reference: str, payload: ChunkFinalize,
                         user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        """Assemble les morceaux et enregistre la preuve."""
        conn = get_db()
        try:
            up = conn.execute(
                "SELECT * FROM pending_uploads WHERE id=? AND user_id=?",
                (payload.upload_id, user["id"]),
            ).fetchone()
            if up is None:
                raise HTTPException(404, "Upload introuvable")

            # Decoder le base64 complet
            try:
                raw = up["data_base64"] or ""
                data = base64.b64decode(raw)
            except Exception:
                raise HTTPException(400, "Donnees invalides")

            if len(data) == 0:
                raise HTTPException(400, "Fichier vide")
            if len(data) > MAX_PROOF_MB * 1024 * 1024:
                raise HTTPException(400, "Fichier trop volumineux")

            ext = Path(up["filename"] or "proof").suffix.lower()
            if ext not in (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".pdf"):
                ext = ".jpg"
            fname = uuid.uuid4().hex + ext
            target = UPLOAD_DIR / fname
            target.write_bytes(data)

            now = datetime.now().isoformat(timespec="seconds")
            conn.execute(
                "UPDATE payments SET proof_file=?, status='PROOF_SUBMITTED', submitted_at=? WHERE id=?",
                ("/uploads/proofs/" + fname, now, up["payment_id"])
            )
            conn.execute(
                "UPDATE orders SET payment_status='PROOF_SUBMITTED' WHERE id=?",
                (up["order_id"],)
            )
            # Supprimer l'upload temporaire
            conn.execute("DELETE FROM pending_uploads WHERE id=?", (payload.upload_id,))
            conn.commit()
            updated = conn.execute(
                "SELECT * FROM payments WHERE id=?", (up["payment_id"],)
            ).fetchone()
        finally:
            conn.close()
        return _row(updated)


    @app.post("/api/orders/{reference}/payment/proof")'''

    anchor = '    @app.post("/api/orders/{reference}/payment/proof")'
    if anchor in src:
        src = src.replace(anchor, chunked_block, 1)
        PAY_PY.write_text(src, encoding="utf-8")
        print("[OK] payments.py -> endpoints chunked ajoutes")
else:
    print("[i] payments.py -> endpoints chunked deja presents")

# ============================================================
# 3. Frontend : compression forcee + upload chunked
# ============================================================
NEW_JS = r'''/* Elokinab Health - Page paiement (v7 chunked) */
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

  // ============================================================
  // API
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
      html += '<div class="pay-success">&#10003; Votre paiement a ete verifie.</div>';
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
              '<strong>Important :</strong> la preuve est verifiee par la pharmacie.' +
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
    info.innerHTML = '<span>&#10003;</span>' + escapeHtml(f.name) +
                     ' - ' + Math.round(f.size / 1024) + ' Ko';
    info.classList.remove("hidden");
    submit.disabled = false;
  }

  // ============================================================
  // Compression forcee : JPEG 800px 50%, toujours plus petit
  // ============================================================
  function compressImage(file) {
    return new Promise(function (resolve, reject) {
      // Non-image : renvoyer tel quel
      if (!file.type || file.type.indexOf("image/") !== 0) {
        resolve({ file: file, base64: null });
        return;
      }

      var reader = new FileReader();
      reader.onerror = function () { reject(new Error("Lecture impossible")); };
      reader.onload = function (e) {
        var img = new Image();
        img.onerror = function () { reject(new Error("Image invalide")); };
        img.onload = function () {
          try {
            var w = img.width;
            var h = img.height;
            var maxDim = 800;
            if (w > maxDim || h > maxDim) {
              if (w > h) { h = Math.round(h * (maxDim / w)); w = maxDim; }
              else { w = Math.round(w * (maxDim / h)); h = maxDim; }
            }
            var canvas = document.createElement("canvas");
            canvas.width = w;
            canvas.height = h;
            var ctx = canvas.getContext("2d");
            // Fond blanc (utile pour PNG transparents convertis en JPEG)
            ctx.fillStyle = "#ffffff";
            ctx.fillRect(0, 0, w, h);
            ctx.drawImage(img, 0, 0, w, h);
            canvas.toBlob(function (blob) {
              if (!blob) { reject(new Error("Compression echouee")); return; }
              var origKB = Math.round(file.size / 1024);
              var newKB = Math.round(blob.size / 1024);
              console.log("[payment] compression forcee : " + origKB + " Ko -> " + newKB + " Ko");
              var newName = (file.name || "image").replace(/\.[^.]+$/, "") + ".jpg";
              var newFile = new File([blob], newName, { type: "image/jpeg" });
              resolve({ file: newFile, base64: null });
            }, "image/jpeg", 0.5);
          } catch (err) { reject(err); }
        };
        img.src = e.target.result;
      };
      reader.readAsDataURL(file);
    });
  }

  function readAsBase64(file) {
    return new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onload = function () {
        var d = reader.result || "";
        var i = d.indexOf(",");
        resolve(i >= 0 ? d.substring(i + 1) : d);
      };
      reader.onerror = function () { reject(new Error("Lecture fichier impossible")); };
      reader.readAsDataURL(file);
    });
  }

  // ============================================================
  // Upload par morceaux (25 Ko par requete)
  // ============================================================
  var CHUNK_SIZE = 25000;  // ~25 Ko de base64 par morceau

  function send() {
    if (!state.file) { toast("Choisissez un fichier."); return; }
    var btn = $("submit-btn");
    btn.disabled = true;
    btn.innerHTML = "Preparation...";

    var paymentRef = state.ref;

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
      // Etape 2 : compresser
      btn.innerHTML = "Compression...";
      return compressImage(state.file);
    })
    .then(function (result) {
      var finalFile = result.file;
      var sizeKB = Math.round(finalFile.size / 1024);
      console.log("[payment] fichier compresse : " + sizeKB + " Ko");

      // Etape 3 : lire en base64
      btn.innerHTML = "Lecture...";
      return readAsBase64(finalFile).then(function (b64) {
        return { file: finalFile, base64: b64, sizeKB: sizeKB };
      });
    })
    .then(function (payload) {
      // Decouper en morceaux
      var chunks = [];
      var b64 = payload.base64;
      for (var i = 0; i < b64.length; i += CHUNK_SIZE) {
        chunks.push(b64.substring(i, i + CHUNK_SIZE));
      }
      console.log("[payment] " + chunks.length + " morceaux de " + CHUNK_SIZE + " car.");

      // Init upload
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

      // Envoyer les morceaux sequentiellement
      var chain = Promise.resolve();
      chunks.forEach(function (chunk, idx) {
        chain = chain.then(function () {
          btn.innerHTML = "Envoi " + (idx + 1) + "/" + total + "...";
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
                throw new Error(d.detail || "Erreur morceau " + (idx + 1));
              });
            }
            return r.json();
          });
        });
      });
      return chain.then(function () { return uploadId; });
    })
    .then(function (uploadId) {
      // Finaliser
      btn.innerHTML = "Finalisation...";
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
      toast("Preuve envoyee. En attente de verification.", true);
      btn.innerHTML = "&#10003; Envoyee ! Redirection...";
      setTimeout(function () {
        window.location.href = "/suivi?ref=" + encodeURIComponent(paymentRef);
      }, 1800);
    })
    .catch(function (e) {
      console.error("[payment] erreur:", e);
      toast(e.message || "Erreur");
      btn.disabled = false;
      btn.innerHTML = '<span>&#128172;</span> Reessayer l\'envoi';
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", load);
  } else {
    load();
  }
})();
'''
PAY_JS.write_text(NEW_JS, encoding="utf-8")
print("[OK] payment.js -> upload chunked complet")

print()
print("=" * 60)
print("UPLOAD CHUNKED LIVRE")
print("=" * 60)
print()
print("Changements :")
print("  - Compression forcee : 800px / JPEG 50% (toujours plus petit)")
print("  - Decoupage en morceaux de 25 Ko")
print("  - Envoi sequentiel : Envoi 1/14, 2/14, ...")
print("  - Reassemblage cote serveur")
print("  - Progress affiche a l'utilisateur")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print()
print("Puis teste sur iPhone : la progression doit s'afficher")
print("Envoi 1/14... Envoi 2/14... etc.")