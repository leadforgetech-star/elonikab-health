from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent
APPJS = BASE / "static" / "app.js"

js = APPJS.read_text(encoding="utf-8")
shutil.copy(APPJS, APPJS.with_suffix(".js.bak"))
print("[OK] sauvegarde ->", APPJS.with_suffix(".js.bak").name)

# Verifier l'etat actuel
if "OU d'utiliser votre localisation" in js or "OU d\u2019utiliser votre localisation" in js:
    print("[i] app.js semble deja patche (message present)")
if "Merci d'indiquer une adresse pour la livraison" in js:
    print("[i] ancien message toujours present -> reecriture complete de submitOrder")

new_func = r'''function submitOrder(ev) {
  ev.preventDefault();
  $("#form-error").classList.add("hidden");
  var form = $("#order-form");
  var data = new FormData(form);
  var mode = String(data.get("delivery_mode") || "retrait");
  var address = String(data.get("address") || "").trim();

  var latVal = data.get("latitude");
  var lonVal = data.get("longitude");
  var hasGps = latVal && lonVal &&
               String(latVal).length > 0 && String(lonVal).length > 0;

  if (mode === "livraison" && address === "" && !hasGps) {
    showError("Merci d'utiliser votre localisation GPS ou d'indiquer une adresse pour la livraison.");
    return;
  }

  ["latitude", "longitude", "location_accuracy"].forEach(function (k) {
    var v = data.get(k);
    if (v === null || v === "" || v === undefined) data.delete(k);
  });

  var btn = $("#submit-btn");
  btn.disabled = true;
  btn.textContent = "Envoi en cours...";

  fetch(API + "/orders", { method: "POST", body: data })
    .then(function (r) {
      return r.json().then(function (body) {
        if (!r.ok) {
          var msg = typeof body.detail === "string" ? body.detail : "Envoi impossible";
          throw new Error(msg);
        }
        return body;
      });
    })
    .then(function (order) {
      state.order = order;
      renderConfirmation(order);
      showView("confirm");
      form.reset();
      $("#address-row").classList.add("hidden");
      var addrBlock = document.getElementById("geo-address-block");
      if (addrBlock) addrBlock.classList.add("hidden");
      var geoStatus = document.getElementById("geo-status");
      if (geoStatus) {
        geoStatus.classList.add("hidden");
        geoStatus.innerHTML = "";
      }
      var geoBtn = document.getElementById("geo-btn");
      if (geoBtn) {
        geoBtn.innerHTML = '<span class="geo-icon">\u{1F4CD}</span> Utiliser ma localisation actuelle';
        geoBtn.disabled = false;
      }
    })
    .catch(function (err) {
      showError(err.message || "Une erreur est survenue.");
    })
    .then(function () {
      btn.disabled = false;
      btn.textContent = "Envoyer la demande";
    });
}
'''

start = js.find("function submitOrder(ev) {")
end = js.find("function summaryRow")
if start == -1 or end == -1 or end <= start:
    print("[!] impossible de localiser submitOrder / summaryRow")
    print("    submitOrder trouve :", start != -1)
    print("    summaryRow trouve  :", end != -1)
    raise SystemExit(1)

js_new = js[:start] + new_func + "\n\n" + js[end:]
APPJS.write_text(js_new, encoding="utf-8")
print("[OK] app.js -> submitOrder reecrit entierement")

# Verification post-ecriture
check = APPJS.read_text(encoding="utf-8")
if "OU d'utiliser votre localisation" in check:
    print("[OK] nouveau message present dans app.js")
else:
    print("[!] nouveau message absent (probleme d'encodage ?)")

if "Merci d'indiquer une adresse pour la livraison." in check:
    print("[!] ancien message encore present -> signaler")
else:
    print("[OK] ancien message elimine")

print()
print("Fix applique.")
print("Redemarre le serveur, puis dans le navigateur :")
print("  1. Ctrl+Shift+Suppr -> cocher 'Images et fichiers en cache' -> Effacer")
print("  2. Ctrl+Shift+R sur http://127.0.0.1:8000")