/* Polyfills safe pour iOS Safari */
(function () {
  "use strict";
  function fmtN(n) {
    n = Math.round(Number(n) || 0);
    var neg = n < 0;
    var s = String(Math.abs(n));
    var out = "";
    for (var i = 0; i < s.length; i++) {
      if (i > 0 && (s.length - i) % 3 === 0) out += " ";
      out += s.charAt(i);
    }
    return (neg ? "-" : "") + out;
  }
  try {
    var o = Number.prototype.toLocaleString;
    Number.prototype.toLocaleString = function (l, op) {
      try { var r = o.call(this, l, op); if (typeof r === "string" && r.length) return r; } catch (e) {}
      return fmtN(this);
    };
  } catch (e) {}
  var M = ["janv.","fevr.","mars","avr.","mai","juin","juil.","aout","sept.","oct.","nov.","dec."];
  function fmtD(d) {
    if (!(d instanceof Date) || isNaN(d.getTime())) return "";
    return d.getDate() + " " + M[d.getMonth()] + " " + d.getFullYear();
  }
  try {
    var od = Date.prototype.toLocaleDateString;
    Date.prototype.toLocaleDateString = function (l, op) {
      try { var r = od.call(this, l, op); if (typeof r === "string" && r.length) return r; } catch (e) {}
      return fmtD(this);
    };
  } catch (e) {}
  window.safeLocaleNumber = fmtN;
  console.log("[safe_locale] actif");
})();