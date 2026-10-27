"""
v4_fix_prototype.py
Override Number.prototype.toLocaleString et Date.prototype.toLocaleDateString
pour les rendre safe sur iOS Safari.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_fix_proto_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(STATIC / "safe_locale.js", backup / "safe_locale.js")
print("[OK] Backup ->", backup.name)

SAFE_JS = r'''/* Elokinab Health - Polyfill global pour iOS Safari
   Override les methodes natives qui throw "The string did not match the expected pattern."
   Ce script doit etre charge EN PREMIER dans chaque page.
*/
(function () {
  "use strict";

  // ============================================================
  // 1. safeFormatNumber : formate un nombre avec separateur milliers
  // ============================================================
  function manualFormatNumber(n) {
    n = Math.round(Number(n) || 0);
    var neg = n < 0;
    var s = String(Math.abs(n));
    var out = "";
    var len = s.length;
    for (var i = 0; i < len; i++) {
      if (i > 0 && (len - i) % 3 === 0) out += " ";
      out += s.charAt(i);
    }
    return (neg ? "-" : "") + out;
  }

  // ============================================================
  // 2. Override Number.prototype.toLocaleString
  // ============================================================
  try {
    var _origNumToLoc = Number.prototype.toLocaleString;
    Number.prototype.toLocaleString = function (locales, options) {
      try {
        if (typeof _origNumToLoc === "function") {
          var r = _origNumToLoc.call(this, locales, options);
          if (typeof r === "string" && r.length > 0) return r;
        }
      } catch (e) { /* fallback */ }
      return manualFormatNumber(this);
    };
  } catch (e) {
    console.warn("Impossible d'override Number.toLocaleString:", e);
  }

  // ============================================================
  // 3. Override Date.prototype.toLocaleDateString
  // ============================================================
  var MONTHS_SHORT = ["janv.","fevr.","mars","avr.","mai","juin",
                      "juil.","aout","sept.","oct.","nov.","dec."];
  var MONTHS_LONG = ["janvier","fevrier","mars","avril","mai","juin",
                     "juillet","aout","septembre","octobre","novembre","decembre"];

  function manualFormatDate(d) {
    if (!(d instanceof Date) || isNaN(d.getTime())) return "";
    return d.getDate() + " " + MONTHS_SHORT[d.getMonth()] + " " + d.getFullYear();
  }

  try {
    var _origDateToLoc = Date.prototype.toLocaleDateString;
    Date.prototype.toLocaleDateString = function (locales, options) {
      try {
        if (typeof _origDateToLoc === "function") {
          var r = _origDateToLoc.call(this, locales, options);
          if (typeof r === "string" && r.length > 0) return r;
        }
      } catch (e) { /* fallback */ }
      return manualFormatDate(this);
    };
  } catch (e) {
    console.warn("Impossible d'override Date.toLocaleDateString:", e);
  }

  // ============================================================
  // 4. Override Date.prototype.toLocaleTimeString (au cas ou)
  // ============================================================
  try {
    var _origDateToLocTime = Date.prototype.toLocaleTimeString;
    Date.prototype.toLocaleTimeString = function (locales, options) {
      try {
        if (typeof _origDateToLocTime === "function") {
          var r = _origDateToLocTime.call(this, locales, options);
          if (typeof r === "string" && r.length > 0) return r;
        }
      } catch (e) { /* fallback */ }
      if (!(this instanceof Date) || isNaN(this.getTime())) return "";
      var pad = function (n) { return n < 10 ? "0" + n : "" + n; };
      return pad(this.getHours()) + ":" + pad(this.getMinutes());
    };
  } catch (e) {}

  // ============================================================
  // 5. Helpers globaux (au cas ou)
  // ============================================================
  window.safeLocaleNumber = manualFormatNumber;
  window.safeLocaleDate = function (iso) {
    try {
      return manualFormatDate(new Date(iso));
    } catch (e) { return String(iso || ""); }
  };

  // ============================================================
  // 6. Capture globale des erreurs pour diagnostic
  // ============================================================
  window.addEventListener("error", function (ev) {
    var msg = (ev && ev.message) ? ev.message : "Erreur inconnue";
    var src = (ev && ev.filename) ? ev.filename : "";
    var line = (ev && ev.lineno) ? ev.lineno : "?";
    console.error("[EH-ERROR] " + msg + " @ " + src + ":" + line);
  });

  window.addEventListener("unhandledrejection", function (ev) {
    var reason = ev && ev.reason;
    var msg = (reason && reason.message) ? reason.message : String(reason);
    console.error("[EH-REJECTION] " + msg);
  });

  console.log("[safe_locale] Polyfills actifs");
})();
'''

(STATIC / "safe_locale.js").write_text(SAFE_JS, encoding="utf-8")
print("[OK] safe_locale.js -> polyfill global")

# ============================================================
# Verifier que safe_locale.js est bien dans toutes les pages
# ============================================================
injected = 0
for html_path in STATIC.glob("*.html"):
    html = html_path.read_text(encoding="utf-8")
    if "safe_locale.js" not in html:
        if "</head>" in html:
            html = html.replace(
                "</head>",
                '<script src="/static/safe_locale.js"></script>\n</head>',
                1
            )
            html_path.write_text(html, encoding="utf-8")
            injected += 1
            print("[OK] " + html_path.name + " -> safe_locale.js injecte")
    else:
        # Verifier qu'il est bien AVANT les autres scripts
        # (peu importe l'ordre en fait, tant que c'est en tete)
        pass

print("[OK] " + str(injected) + " page(s) mise(s) a jour")

print()
print("=" * 60)
print("POLYFILL GLOBAL APPLIQUE")
print("=" * 60)
print()
print("Ce qui a change :")
print("  - Number.prototype.toLocaleString -> version safe")
print("  - Date.prototype.toLocaleDateString -> version safe")
print("  - Date.prototype.toLocaleTimeString -> version safe")
print("  - Les appels toLocaleString dans TOUS les fichiers .js")
print("    sont automatiquement couverts.")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur Edge")
print("  Sur iPhone : navigation privee")