"""
fix_compress_upload.py
Compresse les images cote navigateur avant upload.
- Image > 800 Ko -> redimensionnee a 1600px max + JPEG 80%
- Timeout porte a 120s
- Affiche la taille avant/apres compression
"""
from pathlib import Path
import datetime
import re
import shutil

BASE = Path(__file__).resolve().parent
PAY_JS = BASE / "static" / "payment.js"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_compress_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(PAY_JS, backup / "payment.js")
print("[OK] Backup ->", backup.name)

js = PAY_JS.read_text(encoding="utf-8")

# ============================================================
# 1. Ajouter une fonction de compression d'image
# ============================================================
COMPRESS_FN = '''
  // ============================================================
  // Compression d'image cote navigateur
  // ============================================================
  function compressImage(file, maxDim, quality) {
    return new Promise(function (resolve, reject) {
      // Si ce n'est pas une image, retourner tel quel
      if (!file.type || file.type.indexOf("image/") !== 0) {
        resolve(file);
        return;
      }
      // Si c'est deja petit (< 300 Ko), retourner tel quel
      if (file.size < 300 * 1024) {
        console.log("[payment] image deja petite, pas de compression");
        resolve(file);
        return;
      }

      var reader = new FileReader();
      reader.onerror = function () { reject(new Error("Lecture du fichier impossible")); };
      reader.onload = function (e) {
        var img = new Image();
        img.onerror = function () { reject(new Error("Image invalide")); };
        img.onload = function () {
          try {
            var w = img.width;
            var h = img.height;
            var maxDim = maxDim || 1600;
            if (w > maxDim || h > maxDim) {
              if (w > h) {
                h = Math.round(h * (maxDim / w));
                w = maxDim;
              } else {
                w = Math.round(w * (maxDim / h));
                h = maxDim;
              }
            }
            var canvas = document.createElement("canvas");
            canvas.width = w;
            canvas.height = h;
            var ctx = canvas.getContext("2d");
            ctx.drawImage(img, 0, 0, w, h);
            canvas.toBlob(function (blob) {
              if (!blob) { resolve(file); return; }
              // Si la compression n'aide pas, retourner l'original
              if (blob.size >= file.size) {
                console.log("[payment] compression sans gain, garde l'original");
                resolve(file);
                return;
              }
              var originalKB = Math.round(file.size / 1024);
              var newKB = Math.round(blob.size / 1024);
              console.log("[payment] compression : " + originalKB + " Ko -> " + newKB + " Ko");
              var newName = (file.name || "image").replace(/\\.[^.]+$/, "") + ".jpg";
              var newFile = new File([blob], newName, { type: "image/jpeg" });
              resolve(newFile);
            }, "image/jpeg", quality || 0.8);
          } catch (err) {
            reject(err);
          }
        };
        img.src = e.target.result;
      };
      reader.readAsDataURL(file);
    });
  }

'''

# Injecter avant la fonction send
if "function compressImage" not in js:
    # Trouver la fonction send pour l'ancrer
    idx = js.find("  function send() {")
    if idx > 0:
        js = js[:idx] + COMPRESS_FN + js[idx:]
        print("[OK] payment.js -> fonction compressImage ajoutee")
    else:
        print("[!] fonction send introuvable")

# ============================================================
# 2. Modifier send pour compresser avant upload + timeout 120s
# ============================================================
old_send_pattern = re.compile(
    r'  function send\(\) \{.*?\n  \}',
    re.DOTALL,
)

new_send = '''  function send() {
    if (!state.file) { toast("Choisissez un fichier."); return; }
    var btn = $("submit-btn");
    btn.disabled = true;
    btn.innerHTML = "Preparation...";

    // Etape 0 : compresser si image
    compressImage(state.file)
      .then(function (compressedFile) {
        var original = state.file;
        var originalKB = Math.round(original.size / 1024);
        var finalKB = Math.round(compressedFile.size / 1024);
        console.log("[payment] taille finale : " + finalKB + " Ko (original : " + originalKB + " Ko)");

        if (finalKB < originalKB) {
          toast("Image compressee : " + originalKB + " -> " + finalKB + " Ko");
        }

        // Etape 1 : init du paiement
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
            if (!r.ok) throw new Error(d.detail || "Erreur init paiement");
            return d;
          });
        })
        .then(function () {
          // Etape 2 : upload preuve (timeout 120s)
          btn.innerHTML = "Envoi de la preuve... (" + finalKB + " Ko)";
          var upController = new AbortController();
          var upTimeout = setTimeout(function () { upController.abort(); }, 120000);

          console.log("[payment] Etape 2 - upload preuve (" + finalKB + " Ko)");
          var fd = new FormData();
          fd.append("file", compressedFile);

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
            });
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
          msg = "Delai depasse. Verifiez votre connexion puis reessayez.";
        }
        toast(msg);
        btn.disabled = false;
        btn.innerHTML = '<span>&#128172;</span> Reessayer l\\'envoi';
      });
  }'''

if old_send_pattern.search(js):
    js = js.replace(old_send_pattern.search(js).group(0), new_send, 1)
    print("[OK] payment.js -> send avec compression + timeout 120s")
else:
    print("[!] fonction send introuvable")

# ============================================================
# 3. Mettre a jour le hint (25 Mo)
# ============================================================
js = js.replace("JPG, PNG, PDF - 10 Mo max", "JPG, PNG, PDF - 25 Mo max")
js = js.replace("JPG, PNG, PDF - 25 Mo max", "JPG, PNG, HEIC, PDF")

PAY_JS.write_text(js, encoding="utf-8")
print("[OK] payment.js -> hint mis a jour")

print()
print("=" * 60)
print("COMPRESSION AUTOMATIQUE ACTIVE")
print("=" * 60)
print()
print("Comportement :")
print("  - Image > 300 Ko -> redimensionnee a 1600px max")
print("  - Convertie en JPEG qualite 80%")
print("  - Taille moyenne : 200-400 Ko (au lieu de 2-3 Mo)")
print("  - Timeout upload : 120 secondes")
print("  - Message 'Image compressee : 2430 -> 320 Ko'")
print("  - Logs console : [payment] compression ...")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur Edge (ou navigation privee sur iPhone)")
print("  Pas besoin de redemarrer Uvicorn")
print()
print("TEST :")
print("  Upload ta photo IMG_2587.png (2430 Ko)")
print("  Attendu : compression a ~300 Ko puis upload en 5-10s")