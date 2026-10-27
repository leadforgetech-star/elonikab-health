from pathlib import Path
import re
import shutil

BASE = Path(__file__).resolve().parent
APPJS = BASE / "static" / "app.js"

js = APPJS.read_text(encoding="utf-8")
shutil.copy(APPJS, APPJS.with_suffix(".js.bak"))
print("[OK] sauvegarde ->", APPJS.with_suffix(".js.bak").name)

# Nouvelle version de la fonction de recuperation, avec fallback automatique
new_body = r'''  btn.addEventListener("click", function () {
    if (!navigator.geolocation) {
      setStatus("La geolocalisation n'est pas disponible sur ce navigateur. Vous pouvez continuer avec votre adresse.", "geo-error");
      return;
    }
    btn.disabled = true;
    btn.innerHTML = '<span class="geo-icon">&#8987;</span> Localisation en cours...';
    setStatus("Recuperation de votre position...<br><span class='geo-coords'>Si rien ne se passe, autorisez la localisation dans votre navigateur.</span>", "geo-loading");

    var done = false;

    function onSuccess(pos) {
      if (done) return;
      done = true;
      var lat = pos.coords.latitude;
      var lon = pos.coords.longitude;
      var acc = pos.coords.accuracy;
      latInput.value = String(lat);
      lonInput.value = String(lon);
      accInput.value = String(acc);
      setStatus("&#10003; Localisation enregistree<br><span class='geo-coords'>" +
                lat.toFixed(5) + ", " + lon.toFixed(5) +
                " (&#177; " + Math.round(acc) + " m)</span>", "geo-success");
      btn.disabled = false;
      btn.innerHTML = '<span class="geo-icon">&#128205;</span> Actualiser ma localisation';
    }

    function onFinalError(err) {
      if (done) return;
      done = true;
      var msg = "Localisation indisponible.";
      if (err && err.code === 1) {
        msg = "Vous avez refuse la localisation. Vous pouvez continuer avec votre adresse.";
      } else if (err && err.code === 2) {
        msg = "Position introuvable. Verifiez que le GPS ou la localisation est active sur votre appareil, puis reessayez.";
      } else if (err && err.code === 3) {
        msg = "La localisation met trop de temps. Essayez a l'exterieur, activez le GPS, ou continuez avec votre adresse.";
      }
      setStatus(msg + "<br><span class='geo-coords'>Vous pouvez reessayer ou simplement remplir votre adresse.</span>", "geo-error");
      btn.disabled = false;
      btn.innerHTML = '<span class="geo-icon">&#128205;</span> Reessayer la localisation';
    }

    // Tentative 1 : haute precision, timeout long
    navigator.geolocation.getCurrentPosition(
      onSuccess,
      function (err1) {
        // En cas d'erreur (sauf refus explicite), tenter en mode basse precision
        if (err1 && err1.code === 1) {
          onFinalError(err1);
          return;
        }
        setStatus("Position precise introuvable, tentative en mode standard...", "geo-loading");
        navigator.geolocation.getCurrentPosition(
          onSuccess,
          onFinalError,
          { enableHighAccuracy: false, timeout: 30000, maximumAge: 300000 }
        );
      },
      { enableHighAccuracy: true, timeout: 20000, maximumAge: 60000 }
    );
  });
'''

# Remplacer le contenu entre btn.addEventListener("click", function () { et la fin du bloc
pattern = re.compile(
    r'  btn\.addEventListener\("click", function \(\) \{.*?\n  \}\);\n',
    re.DOTALL,
)

if pattern.search(js):
    js = pattern.sub(new_body, js, count=1)
    APPJS.write_text(js, encoding="utf-8")
    print("[OK] app.js -> logique GPS amelioree (double tentative)")
    print("[OK] Tentative 1 : haute precision, timeout 20s")
    print("[OK] Tentative 2 : standard, timeout 30s (si la 1 echoue)")
else:
    print("[!] pattern btn.addEventListener introuvable dans app.js")

print()
print("Redemarre le serveur, puis Ctrl+Shift+R.")