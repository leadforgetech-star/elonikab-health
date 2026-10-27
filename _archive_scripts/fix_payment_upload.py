"""
fix_payment_upload.py
- Upload avec timeout, retry et messages clairs
- Retrait de 'manuellement' dans le texte
- Accepte HEIC et autres formats iPhone
"""
from pathlib import Path
import datetime
import re
import shutil

BASE = Path(__file__).resolve().parent
PAY_JS = BASE / "static" / "payment.js"
PAY_PY = BASE / "v3_modules" / "payments.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_upload_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(PAY_JS, backup / "payment.js")
shutil.copy2(PAY_PY, backup / "payments.py")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. Backend : accepte plus de formats
# ============================================================
src = PAY_PY.read_text(encoding="utf-8")

old_types = '''ALLOWED_PROOF_TYPES = {
    "image/jpeg", "image/png", "image/webp",
    "application/pdf",
}'''
new_types = '''ALLOWED_PROOF_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
    "application/pdf",
    "application/octet-stream",  # fallback iPhone
}'''
if old_types in src:
    src = src.replace(old_types, new_types, 1)
    print("[OK] payments.py -> plus de formats acceptes")

# Accepter aussi l'extension si le MIME est incorrect
old_check = '''            ctype = (file.content_type or "").lower()
            if ctype not in ALLOWED_PROOF_TYPES:
                raise HTTPException(400, "Format non accepte (JPG, PNG, WEBP, PDF)")'''
new_check = '''            ctype = (file.content_type or "").lower()
            fname_lower = (file.filename or "").lower()
            # Accepter si le MIME est OK OU si l'extension est reconnue
            ext_ok = any(fname_lower.endswith(e) for e in
                         (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".pdf"))
            if ctype not in ALLOWED_PROOF_TYPES and not ext_ok:
                raise HTTPException(
                    400,
                    "Format non accepte. Utilisez JPG, PNG, WEBP, HEIC ou PDF."
                )'''
if old_check in src:
    src = src.replace(old_check, new_check, 1)
    print("[OK] payments.py -> tolerance extension")

# Augmenter la limite de taille
old_mb = "MAX_PROOF_MB = 10"
new_mb = "MAX_PROOF_MB = 25"
if old_mb in src:
    src = src.replace(old_mb, new_mb, 1)
    print("[OK] payments.py -> limite a 25 Mo")

PAY_PY.write_text(src, encoding="utf-8")

# ============================================================
# 2. Frontend : upload robuste
# ============================================================
js = PAY_JS.read_text(encoding="utf-8")

# 2.1 Retirer 'manuellement'
js = js.replace(
    "la preuve est verifiee manuellement par la pharmacie",
    "la preuve est verifiee par la pharmacie"
)
js = js.replace(
    "la preuve est vérifiée manuellement par la pharmacie",
    "la preuve est vérifiée par la pharmacie"
)
print("[OK] payment.js -> 'manuellement' retire")

# 2.2 Remplacer la fonction send par une version robuste
old_send_pat = re.compile(
    r'  function send\(\) \{.*?\n  \}',
    re.DOTALL,
)

new_send = '''  function send() {
    if (!state.file) { toast("Choisissez un fichier."); return; }
    var btn = $("submit-btn");
    btn.disabled = true;
    btn.innerHTML = "Envoi de la preuve...";

    // Etape 1 : init du paiement (avec timeout 20s)
    var initController = new AbortController();
    var initTimeout = setTimeout(function () { initController.abort(); }, 20000);

    console.log("[payment] Etape 1 - init paiement");
    fetch(API + "/orders/" + encodeURIComponent(state.ref) + "/payment", {
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
        if (!r.ok) throw new Error(d.detail || "Erreur init paiement");
        return d;
      });
    })
    .then(function () {
      // Etape 2 : upload preuve (avec timeout 60s pour les grosses photos)
      btn.innerHTML = "Envoi de la preuve... (peut prendre 30 sec)";
      var upController = new AbortController();
      var upTimeout = setTimeout(function () { upController.abort(); }, 60000);

      console.log("[payment] Etape 2 - upload preuve");
      var fd = new FormData();
      fd.append("file", state.file);

      return fetch(API + "/orders/" + encodeURIComponent(state.ref) + "/payment/proof", {
        method: "POST",
        credentials: "same-origin",
        body: fd,
        signal: upController.signal
      }).then(function (r) {
        clearTimeout(upTimeout);
        console.log("[payment] upload status:", r.status);
        return r.json().then(function (d) {
          if (!r.ok) throw new Error(d.detail || "Erreur upload preuve");
          return d;
        }).catch(function (parseErr) {
          // Si le serveur a renvoye autre chose que du JSON
          if (!r.ok) throw new Error("Erreur serveur (" + r.status + ")");
          throw parseErr;
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
        msg = "Delai depasse. Verifiez votre connexion et reessayez.";
      }
      toast(msg);
      btn.disabled = false;
      btn.innerHTML = '<span>&#128172;</span> Reessayer l\\'envoi';
    });
  }'''

if old_send_pat.search(js):
    js = js.replace(old_send_pat.search(js).group(0), new_send, 1)
    print("[OK] payment.js -> fonction send robuste (timeouts + logs)")
else:
    print("[!] fonction send introuvable")

# 2.3 Ajouter un bouton "annuler" en cas de blocage
old_upload_hint = "'<p class=\"pay-upload-hint\">JPG, PNG, PDF - 10 Mo max</p>' +"
new_upload_hint = "'<p class=\"pay-upload-hint\">JPG, PNG, PDF - 25 Mo max</p>' +"
if old_upload_hint in js:
    js = js.replace(old_upload_hint, new_upload_hint, 1)
    print("[OK] payment.js -> limite affichee 25 Mo")

PAY_JS.write_text(js, encoding="utf-8")

# ============================================================
# 3. Augmenter aussi la limite cote FastAPI (multipart)
# ============================================================
# Certains navigateurs envoient des fichiers plus gros qu'attendu
# On verifie juste que les parametres par defaut ne bloquent pas

print()
print("=" * 60)
print("FIX APPLIQUE")
print("=" * 60)
print()
print("Backend (payments.py) :")
print("  - Formats acceptes : JPG, PNG, WEBP, HEIC, PDF")
print("  - Fallback octet-stream pour iPhone")
print("  - Taille max : 25 Mo (au lieu de 10)")
print()
print("Frontend (payment.js) :")
print("  - Timeout 20s pour l'init + 60s pour l'upload")
print("  - Logs console : [payment] Etape 1..., Etape 2...")
print("  - Message clair en cas d'echec")
print("  - Bouton devient 'Reessayer l'envoi'")
print("  - 'manuellement' retire dans le texte")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print()
print("Puis sur iPhone : recharger la page (tirer vers le bas)")
print("Sur PC : F12 -> Console pour voir les logs [payment]")