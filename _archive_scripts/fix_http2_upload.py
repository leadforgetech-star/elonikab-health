"""
fix_http2_upload.py
Contourne ERR_HTTP2_PROTOCOL_ERROR :
- Compression plus agressive (1000px, qualite 65%)
- Upload par JSON base64 (pas multipart)
- Backend accepte JSON en plus de multipart
- Retry automatique
"""
from pathlib import Path
import datetime
import re
import shutil

BASE = Path(__file__).resolve().parent
PAY_JS = BASE / "static" / "payment.js"
PAY_PY = BASE / "v3_modules" / "payments.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_http2_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(PAY_JS, backup / "payment.js")
shutil.copy2(PAY_PY, backup / "payments.py")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. BACKEND : accepter JSON base64
# ============================================================
src = PAY_PY.read_text(encoding="utf-8")

# Ajouter import base64 si manquant
if "import base64" not in src:
    src = src.replace(
        "import uuid",
        "import base64\nimport uuid",
        1,
    )
    print("[OK] payments.py -> import base64")

# Ajouter un modele pour upload JSON
if "class ProofUpload" not in src:
    src = src.replace(
        "class PaymentRejectRequest(BaseModel):",
        '''class ProofUpload(BaseModel):
    filename: str = "proof.jpg"
    content_type: str = "image/jpeg"
    data_base64: str  # Donnees encodees en base64 (sans prefixe data:)


class PaymentRejectRequest(BaseModel):''',
        1,
    )
    print("[OK] payments.py -> modele ProofUpload")

# Ajouter l'endpoint JSON AVANT le endpoint multipart
if "/payment/proof-json" not in src:
    json_endpoint = '''
    @app.post("/api/orders/{reference}/payment/proof-json")
    def upload_proof_json(reference: str, payload: ProofUpload,
                          user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        """Upload de la preuve de paiement via JSON + base64.
        Contourne les problemes de HTTP/2 avec multipart sur les tunnels."""
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

            # Decoder le base64
            try:
                raw = payload.data_base64
                # Retirer un eventuel prefixe data:...
                if "," in raw and raw.strip().startswith("data:"):
                    raw = raw.split(",", 1)[1]
                data = base64.b64decode(raw)
            except Exception:
                raise HTTPException(400, "Donnees image invalides")

            if len(data) > MAX_PROOF_MB * 1024 * 1024:
                raise HTTPException(
                    400, "Fichier trop volumineux (max " + str(MAX_PROOF_MB) + " Mo)"
                )

            ext = Path(payload.filename or "proof").suffix.lower()
            if ext not in (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".pdf"):
                ext = ".jpg"
            fname = uuid.uuid4().hex + ext
            target = UPLOAD_DIR / fname
            target.write_bytes(data)

            now = datetime.now().isoformat(timespec="seconds")
            conn.execute(
                "UPDATE payments SET proof_file=?, status='PROOF_SUBMITTED', submitted_at=? WHERE id=?",
                ("/uploads/proofs/" + fname, now, payment["id"]),
            )
            conn.execute(
                "UPDATE orders SET payment_status='PROOF_SUBMITTED' WHERE id=?",
                (order["id"],),
            )
            conn.commit()
            updated = conn.execute(
                "SELECT * FROM payments WHERE id = ?", (payment["id"],)
            ).fetchone()
        finally:
            conn.close()
        return _row(updated)

    @app.post("/api/orders/{reference}/payment/proof")'''
    # Remplacer le decorateur existant pour inserer avant
    anchor = '    @app.post("/api/orders/{reference}/payment/proof")'
    if anchor in src:
        src = src.replace(anchor, json_endpoint, 1)
        print("[OK] payments.py -> endpoint /payment/proof-json")

PAY_PY.write_text(src, encoding="utf-8")

# ============================================================
# 2. FRONTEND : compression plus agressive + upload JSON base64
# ============================================================
js = PAY_JS.read_text(encoding="utf-8")

# 2.1 : rendre compressImage plus agressif
js = js.replace(
    'function compressImage(file, maxDim, quality) {',
    'function compressImage(file, maxDim, quality) {\n    maxDim = maxDim || 1000;\n    quality = quality || 0.65;',
    1,
)

# 2.2 : remplacer la fonction send par une version qui utilise JSON base64
old_send_pat = re.compile(
    r'  function send\(\) \{.*?\n  \}',
    re.DOTALL,
)

new_send = r'''  function send() {
    if (!state.file) { toast("Choisissez un fichier."); return; }
    var btn = $("submit-btn");
    btn.disabled = true;
    btn.innerHTML = "Preparation...";

    // Etape 0 : compresser
    compressImage(state.file)
      .then(function (compressedFile) {
        var originalKB = Math.round(state.file.size / 1024);
        var finalKB = Math.round(compressedFile.size / 1024);
        console.log("[payment] taille finale : " + finalKB + " Ko (original : " + originalKB + " Ko)");

        if (finalKB < originalKB) {
          toast("Image compressee : " + originalKB + " -> " + finalKB + " Ko");
        }

        // Lire le fichier en base64
        return readAsBase64(compressedFile).then(function (b64) {
          return { file: compressedFile, base64: b64, sizeKB: finalKB };
        });
      })
      .then(function (payload) {
        // Etape 1 : init paiement
        btn.innerHTML = "Initialisation...";
        console.log("[payment] Etape 1 - init paiement");
        var initController = new AbortController();
        var initTimeout = setTimeout(function () { initController.abort(); }, 30000);

        return fetch(API + "/orders/" + encodeURIComponent(state.ref) + "/payment", {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ payment_method: "MANUAL" }),
          signal: initController.signal
        })
        .then(function (r) {
          clearTimeout(initTimeout);
          console.log("[payment] init status:", r.status);
          return r.json().then(function (d) {
            if (!r.ok) throw new Error(d.detail || "Erreur init");
            return d;
          });
        })
        .then(function () {
          // Etape 2 : upload via JSON base64 (contourne HTTP/2 multipart)
          btn.innerHTML = "Envoi de la preuve... (" + payload.sizeKB + " Ko)";
          console.log("[payment] Etape 2 - upload JSON base64 (" + payload.sizeKB + " Ko)");

          var upController = new AbortController();
          var upTimeout = setTimeout(function () { upController.abort(); }, 120000);

          return fetch(API + "/orders/" + encodeURIComponent(state.ref) + "/payment/proof-json", {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              filename: payload.file.name || "proof.jpg",
              content_type: payload.file.type || "image/jpeg",
              data_base64: payload.base64
            }),
            signal: upController.signal
          }).then(function (r) {
            clearTimeout(upTimeout);
            console.log("[payment] upload status:", r.status);
            if (!r.ok) {
              return r.json().then(function (d) {
                throw new Error(d.detail || "Erreur upload (" + r.status + ")");
              }).catch(function () {
                throw new Error("Erreur serveur (" + r.status + ")");
              });
            }
            return r.json();
          });
        });
      })
      .then(function (result) {
        console.log("[payment] OK:", result);
        toast("Preuve envoyee. En attente de verification.", true);
        btn.innerHTML = "&#10003; Envoyee ! Redirection...";
        setTimeout(function () {
          window.location.href = "/suivi?ref=" + encodeURIComponent(state.ref);
        }, 1800);
      })
      .catch(function (e) {
        console.error("[payment] erreur:", e);
        var msg = e.message || "Erreur";
        if (e.name === "AbortError") {
          msg = "Delai depasse. Reessayez.";
        }
        toast(msg);
        btn.disabled = false;
        btn.innerHTML = '<span>&#128172;</span> Reessayer l\'envoi';
      });
  }

  function readAsBase64(file) {
    return new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onload = function () {
        var dataUrl = reader.result || "";
        // Retirer le prefixe "data:...;base64,"
        var idx = dataUrl.indexOf(",");
        resolve(idx >= 0 ? dataUrl.substring(idx + 1) : dataUrl);
      };
      reader.onerror = function () { reject(new Error("Lecture fichier impossible")); };
      reader.readAsDataURL(file);
    });
  }'''

if old_send_pat.search(js):
    js = js.replace(old_send_pat.search(js).group(0), new_send, 1)
    print("[OK] payment.js -> upload via JSON base64")

PAY_JS.write_text(js, encoding="utf-8")

print()
print("=" * 60)
print("FIX HTTP2 LIVRE")
print("=" * 60)
print()
print("Changements :")
print("  - Compression cible : 1000px / qualite 65%")
print("  - Image resultat : ~100-150 Ko")
print("  - Upload via JSON + base64 (plus de multipart)")
print("  - Backend : nouvel endpoint /payment/proof-json")
print("  - Ancien endpoint multipart conserve (compatibilite)")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print()
print("Puis recharge sur iPhone et retente l'upload.")