# -*- coding: utf-8 -*-
"""
Fix : toast/alert fallback pour pages sans EHModal.
+ Etat visuel sur bouton + quand max atteint.
"""
import os, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
APP = os.path.join(ROOT, "static", "app.js")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_alertfb_{TS}")
os.makedirs(BAK, exist_ok=True)
shutil.copy2(APP, os.path.join(BAK, "app.js"))

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]"}[k]
    print(p, m)

def brace_diff(s): return s.count("{") - s.count("}")

print("=" * 78)
print(f"FIX ALERT FALLBACK - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

src = open(APP, "r", encoding="utf-8").read()

# ============================================================
# 1. Injecter un helper global ehAlert() avec fallback toast
# ============================================================
log("Fix 1 : Helper ehAlert()", "INFO")

HELPER = '''
/* ============================================================
   LOT 7 : Helper alert avec fallback (modal > toast > alert)
   ============================================================ */
(function(){
  if (window.ehAlert) return;

  // Injecter CSS toast une seule fois
  if (!document.getElementById("eh-alert-toast-style")) {
    var style = document.createElement("style");
    style.id = "eh-alert-toast-style";
    style.textContent = [
      ".eh-alert-toast{position:fixed;top:20px;left:50%;transform:translateX(-50%) translateY(-120%);",
      "background:#fff;border:1px solid #E2E8F0;border-left:4px solid #174A7E;",
      "border-radius:12px;padding:14px 18px;box-shadow:0 12px 40px rgba(15,23,42,.15);",
      "z-index:99999;max-width:min(440px,90vw);font-family:system-ui,sans-serif;",
      "transition:transform .25s ease;display:flex;gap:12px;align-items:flex-start}",
      ".eh-alert-toast.show{transform:translateX(-50%) translateY(0)}",
      ".eh-alert-toast.warn{border-left-color:#B26B00}",
      ".eh-alert-toast.danger{border-left-color:#B23C3C}",
      ".eh-alert-toast-ico{font-size:22px;line-height:1;flex-shrink:0}",
      ".eh-alert-toast-title{font-size:13.5px;font-weight:800;color:#0F172A;margin:0 0 4px}",
      ".eh-alert-toast-body{font-size:13px;color:#64748B;line-height:1.45;margin:0}",
      ".eh-alert-toast-close{background:none;border:0;font-size:18px;color:#94A3B8;cursor:pointer;padding:0 4px;margin-left:auto;flex-shrink:0}"
    ].join("");
    document.head.appendChild(style);
  }

  window.ehAlert = function(title, message, kind) {
    kind = kind || "info";
    // 1. Si EHModal existe (pharmacien), l'utiliser
    if (window.EHModal && typeof window.EHModal.alert === "function") {
      try { return window.EHModal.alert(title, message, kind); } catch(e) {}
    }
    // 2. Fallback : toast custom
    var t = document.createElement("div");
    t.className = "eh-alert-toast " + kind;
    var ico = kind === "danger" ? "⚠️" : (kind === "warn" ? "⏳" : "ℹ️");
    t.innerHTML =
      '<div class="eh-alert-toast-ico">' + ico + '</div>' +
      '<div style="flex:1;min-width:0">' +
        '<p class="eh-alert-toast-title">' + (title || "") + '</p>' +
        '<p class="eh-alert-toast-body">' + (message || "") + '</p>' +
      '</div>' +
      '<button type="button" class="eh-alert-toast-close" aria-label="Fermer">×</button>';
    document.body.appendChild(t);
    setTimeout(function(){ t.classList.add("show"); }, 20);

    function close(){
      t.classList.remove("show");
      setTimeout(function(){ if (t.parentNode) t.parentNode.removeChild(t); }, 300);
    }
    t.querySelector(".eh-alert-toast-close").addEventListener("click", close);
    setTimeout(close, 5000);
  };
})();
'''

if "window.ehAlert" in src:
    log("ehAlert deja present", "WARN")
else:
    # Inserer au tout debut (avant le helper ehProductAvailable existant)
    src = HELPER + "\n" + src
    log("Helper ehAlert injecte", "OK")

# ============================================================
# 2. Remplacer window.EHModal.alert par ehAlert() partout
# ============================================================
log("Fix 2 : Remplacement alertes", "INFO")

# Compter les remplacements
n_before = src.count("window.EHModal.alert(")

# Patch 1 : dans le pre-check addToCartQty
OLD1 = '''    if (window.EHModal) {
      var _msgPre = (_maxQty === 1)
        ? "Ce produit n'est actuellement disponible qu'en 1 unité. Veuillez ajuster votre quantité."
        : "Ce produit n'est actuellement disponible qu'en " + _maxQty + " unités. Veuillez ajuster votre quantité.";
      window.EHModal.alert("Disponibilité limitée", _msgPre, "warn");
    }'''

NEW1 = '''    var _msgPre = (_maxQty === 1)
      ? "Ce produit n'est actuellement disponible qu'en 1 unité. Veuillez ajuster votre quantité."
      : "Ce produit n'est actuellement disponible qu'en " + _maxQty + " unités. Veuillez ajuster votre quantité.";
    window.ehAlert("Disponibilité limitée", _msgPre, "warn");'''

if OLD1 in src:
    src = src.replace(OLD1, NEW1, 1)
    log("Pre-check addToCartQty : ehAlert()", "OK")

# Patch 2 : dans le bouton +
OLD2 = '''      if (n > _max2) {
        n = _max2;
        if (window.EHModal) {
          var _msgPlus = (_max2 === 1)
            ? "Ce produit n'est actuellement disponible qu'en 1 unité."
            : "Ce produit n'est actuellement disponible qu'en " + _max2 + " unités.";
          window.EHModal.alert("Disponibilité limitée", _msgPlus, "warn");
        }
      }'''

NEW2 = '''      if (n > _max2) {
        n = _max2;
        var _msgPlus = (_max2 === 1)
          ? "Ce produit n'est actuellement disponible qu'en 1 unité."
          : "Ce produit n'est actuellement disponible qu'en " + _max2 + " unités.";
        window.ehAlert("Disponibilité limitée", _msgPlus, "warn");
      }'''

if OLD2 in src:
    src = src.replace(OLD2, NEW2, 1)
    log("Bouton + : ehAlert()", "OK")

# Patch 3 : dans le change listener
OLD3 = '''      if (v > _max3) {
        qtyInput.value = String(_max3);
        if (window.EHModal) {
          var _msgChg = (_max3 === 1)
            ? "Ce produit n'est actuellement disponible qu'en 1 unité. Votre quantité a été ajustée."
            : "Ce produit n'est actuellement disponible qu'en " + _max3 + " unités. Votre quantité a été ajustée.";
          window.EHModal.alert("Disponibilité limitée", _msgChg, "warn");
        }
      }'''

NEW3 = '''      if (v > _max3) {
        qtyInput.value = String(_max3);
        var _msgChg = (_max3 === 1)
          ? "Ce produit n'est actuellement disponible qu'en 1 unité. Votre quantité a été ajustée."
          : "Ce produit n'est actuellement disponible qu'en " + _max3 + " unités. Votre quantité a été ajustée.";
        window.ehAlert("Disponibilité limitée", _msgChg, "warn");
      }'''

if OLD3 in src:
    src = src.replace(OLD3, NEW3, 1)
    log("Change listener : ehAlert()", "OK")

# Patch 4 : dans getQty()
OLD4 = '''      if (n > _max) {
        n = _max;
        if (window.EHModal) window.EHModal.alert("Quantité limitée",
          "Maximum disponible : " + _max, "warn");
      }'''

NEW4 = '''      if (n > _max) {
        n = _max;
        window.ehAlert("Disponibilité limitée",
          "Ce produit n'est actuellement disponible qu'en " + _max + " unité(s).", "warn");
      }'''

if OLD4 in src:
    src = src.replace(OLD4, NEW4, 1)
    log("getQty : ehAlert()", "OK")

# Patch 5 : dans le click intercepteur rupture
OLD5 = '''          if (window.EHModal) window.EHModal.alert("Indisponible", msg, "danger");
          else alert(msg);'''

NEW5 = '''          window.ehAlert("Indisponible", msg, "danger");'''

if OLD5 in src:
    src = src.replace(OLD5, NEW5, 1)
    log("Intercepteur rupture : ehAlert()", "OK")

# ============================================================
# 3. Desactiver visuellement le bouton + quand max atteint
# ============================================================
log("Fix 3 : Etat visuel bouton +", "INFO")

# Ajouter un effet visuel quand on atteint le max
OLD_CLICK = '''    btnPlus.addEventListener("click", function () {
      var n = getQty() + 1;
      var _max2 = parseInt(qtyInput.max || "99", 10) || 99;
      if (n > _max2) {
        n = _max2;'''

NEW_CLICK = '''    btnPlus.addEventListener("click", function () {
      var n = getQty() + 1;
      var _max2 = parseInt(qtyInput.max || "99", 10) || 99;
      if (n > _max2) {
        n = _max2;
        // Feedback visuel sur le bouton
        btnPlus.style.opacity = "0.5";
        btnPlus.style.cursor = "not-allowed";
        setTimeout(function() {
          btnPlus.style.opacity = "";
          btnPlus.style.cursor = "";
        }, 800);'''

if "Feedback visuel sur le bouton" in src:
    log("Feedback visuel deja present", "WARN")
elif OLD_CLICK in src:
    src = src.replace(OLD_CLICK, NEW_CLICK, 1)
    log("Feedback visuel bouton + ajoute", "OK")
else:
    log("Pattern bouton + introuvable", "WARN")

# ============================================================
# 4. Verifier equilibre
# ============================================================
diff = brace_diff(src)
if diff != 0:
    log(f"Deséquilibre ({diff}) - ROLLBACK", "ERR")
    shutil.copy2(os.path.join(BAK, "app.js"), APP)
    sys.exit(1)

open(APP, "w", encoding="utf-8").write(src)
log("app.js sauvegarde", "OK")

# ============================================================
# Verification
# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)
final = open(APP, "r", encoding="utf-8").read()
checks = [
    ("Helper ehAlert",              "window.ehAlert = function" in final),
    ("CSS toast injectee",          "eh-alert-toast" in final),
    ("Pre-check utilise ehAlert",   "window.ehAlert(\"Disponibilité limitée\", _msgPre" in final),
    ("Bouton + utilise ehAlert",    "window.ehAlert(\"Disponibilité limitée\", _msgPlus" in final),
    ("Change utilise ehAlert",      "window.ehAlert(\"Disponibilité limitée\", _msgChg" in final),
    ("Rupture utilise ehAlert",     "window.ehAlert(\"Indisponible\"" in final),
    ("Feedback visuel bouton",      "Feedback visuel sur le bouton" in final),
    ("Accolades OK",                brace_diff(final) == 0),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

print()
print(f"[BACKUP] {BAK}")
print()
print("[CMD] Pas de restart Uvicorn (frontend only).")
print()
print("[TEST] Edge : F12 > Clear site data + Ctrl+Shift+R")
print("  1) Produit stock=3 : cliquer + jusqu'a 3, puis encore + -> message toast")
print("  2) Saisir 5 -> input corrige a 3 + message toast")
print("  3) Ajouter au panier avec qty > stock -> message toast")
print()
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\app.js" "{APP}"')