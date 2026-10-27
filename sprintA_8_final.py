# -*- coding: utf-8 -*-
"""
SPRINT A.8 - UI complete
=========================
A.5-fix : Badge vehicule dans .pt-fee-info (au bon endroit cette fois)
A.6-ui  : Bouton "Changer vehicule" dans drawer pharmacien
A.8     : Section "Livraison intelligente" dans Admin (4 seuils)
"""
import os, re, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
CHECKOUT = os.path.join(ROOT, "static", "checkout.js")
PHARM_JS = os.path.join(ROOT, "static", "pharmacien.js")
PHARM_HTML = os.path.join(ROOT, "static", "pharmacien.html")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_sprintA8_{TS}")
os.makedirs(BAK, exist_ok=True)

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]", "STEP": "\n###"}[k]
    print(p, m)

def brace_diff(s): return s.count("{") - s.count("}")

for p, n in [(CHECKOUT, "checkout.js"), (PHARM_JS, "pharmacien.js"), (PHARM_HTML, "pharmacien.html")]:
    if os.path.isfile(p):
        shutil.copy2(p, os.path.join(BAK, n))

print("=" * 78)
print(f"SPRINT A.8 - UI COMPLETE - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

# ============================================================
# PHASE 1 : A.5-FIX - Badge vehicule dans .pt-fee-info
# ============================================================
log("PHASE 1 : Badge vehicule dans .pt-fee-info", "STEP")

co_src = open(CHECKOUT, "r", encoding="utf-8").read()

# Trouver le bloc <div class="pt-fee-info">
OLD_FEE = '''      html += '<div class="pt-fee-info">Frais estimes : <strong>' + money(fee) + '</strong>';
      var d = computeDistance();
      if (d !== null) html += ' &middot; Distance : <strong>' + d.toFixed(1) + ' km</strong>';
      else html += '<br><small>Activez le GPS pour un tarif precis.</small>';
      html += '</div>';'''

NEW_FEE = '''      html += '<div class="pt-fee-info" id="eh-fee-info">Frais estimes : <strong>' + money(fee) + '</strong>';
      var d = computeDistance();
      if (d !== null) html += ' &middot; Distance : <strong>' + d.toFixed(1) + ' km</strong>';
      else html += '<br><small>Activez le GPS pour un tarif precis.</small>';
      html += '</div>';
      html += '<div id="eh-vehicle-info" class="eh-vehicle-badge">';
      html += '<span class="eh-vehicle-loading">Calcul du moyen de livraison...</span>';
      html += '</div>';'''

if 'id="eh-vehicle-info" class="eh-vehicle-badge"' in co_src:
    log("Badge dans pt-fee-info deja present", "WARN")
elif OLD_FEE in co_src:
    co_src = co_src.replace(OLD_FEE, NEW_FEE, 1)
    log("Badge injecte apres .pt-fee-info", "OK")
else:
    log("Bloc pt-fee-info introuvable", "ERR")

# Remplacer le helper ehRefreshVehicleInfo par une version qui ecrit dans eh-vehicle-info
OLD_HELPER_RE = re.compile(r'async function ehRefreshVehicleInfo[\s\S]*?window\.ehRefreshVehicleInfo = ehRefreshVehicleInfo;', re.DOTALL)

NEW_HELPER = '''async function ehRefreshVehicleInfo() {
  try {
    if (state.mode !== "livraison") return;
    var el = document.getElementById("eh-vehicle-info");
    if (!el) return;

    // Calculer les parametres depuis le panier
    var cart = state.cart || {};
    var items = cart.items || [];
    var units = items.reduce(function(s, it){ return s + (Number(it.quantity)||1); }, 0);
    var lines = items.length;
    var amount = items.reduce(function(s, it){
      return s + (Number(it.price)||Number(it.unit_price)||0) * (Number(it.quantity)||1);
    }, 0);

    var lat = (typeof state.lat === "number") ? state.lat : null;
    var lon = (typeof state.lng === "number") ? state.lng : null;
    if (lat === null || lon === null) {
      try {
        var g = (state.gps || state.location);
        if (g && g.lat != null) { lat = Number(g.lat); lon = Number(g.lng || g.lon); }
      } catch(e) {}
    }

    el.innerHTML = '<span class="eh-vehicle-loading">Calcul...</span>';

    var r = await fetch("/api/delivery/estimate", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      credentials: "same-origin",
      body: JSON.stringify({
        latitude: lat, longitude: lon,
        units: units, distinct_lines: lines, amount: amount
      })
    });
    if (!r.ok) throw new Error("HTTP " + r.status);
    var d = await r.json();

    if (d.available) {
      var isCar = d.vehicle_type === "CAR";
      var ico = isCar ? "🚗" : "🛵";
      var lbl = isCar ? "voiture" : "moto";
      var distTxt = (d.distance_km != null) ? " (" + d.distance_km + " km)" : "";
      var feeTxt = Math.round(d.fee).toLocaleString("fr-FR") + " FCFA";
      el.className = "eh-vehicle-badge " + (isCar ? "eh-vehicle-car" : "eh-vehicle-moto");
      el.innerHTML = ico + " Livraison par <strong>" + lbl + "</strong>" + distTxt
                   + " — <strong>" + feeTxt + "</strong>";
    } else {
      el.className = "eh-vehicle-badge eh-vehicle-error";
      el.innerHTML = "❌ Aucun moyen de livraison pour cette distance. Choisissez le retrait.";
    }
  } catch(e) {
    var el2 = document.getElementById("eh-vehicle-info");
    if (el2) el2.innerHTML = "";
  }
}
window.ehRefreshVehicleInfo = ehRefreshVehicleInfo;'''

if NEW_HELPER in co_src:
    log("Helper deja patche", "WARN")
elif OLD_HELPER_RE.search(co_src):
    co_src = OLD_HELPER_RE.sub(NEW_HELPER, co_src)
    log("Helper remplace (cible #eh-vehicle-info)", "OK")
else:
    # Pas de helper existant : inserer avant la fin de la IIFE
    last = co_src.rstrip().rfind("}")
    if last > 0:
        co_src = co_src[:last] + "\n" + NEW_HELPER + "\n" + co_src[last:]
        log("Helper insere", "OK")

# CSS pour le badge
if "eh-vehicle-badge" not in co_src:
    CSS_INJECT = '''
(function(){
  if (document.getElementById("eh-vehicle-style")) return;
  var s = document.createElement("style");
  s.id = "eh-vehicle-style";
  s.textContent = [
    ".eh-vehicle-badge{margin-top:8px;padding:10px 14px;border-radius:10px;font-size:13.5px;line-height:1.4;",
    "border:1px solid #E2E8F0;background:#F5F8FC;color:#0F172A;display:flex;align-items:center;gap:8px}",
    ".eh-vehicle-moto{border-color:#C7E9DC;background:#E6F7F1;color:#0A7A5A}",
    ".eh-vehicle-car{border-color:#C7D8EC;background:#E8F0F8;color:#174A7E}",
    ".eh-vehicle-error{border-color:#F6D2D2;background:#FDECEC;color:#B23C3C}",
    ".eh-vehicle-loading{color:#94A3B8;font-style:italic;font-size:12.5px}"
  ].join("");
  document.head.appendChild(s);
})();
'''
    co_src = CSS_INJECT + "\n" + co_src
    log("CSS badge injectee", "OK")

# Hook refresh vehicule : doit etre appele quand mode change ou GPS mis a jour
# Chercher si un appel existe deja
if "ehRefreshVehicleInfo()" not in co_src:
    HOOK = '''
// Hook : refresh vehicule sur changement mode/adresse/GPS
document.addEventListener("click", function(ev){
  var t = ev.target.closest ? ev.target.closest("[data-mode]") : null;
  if (t) setTimeout(function(){ if (window.ehRefreshVehicleInfo) window.ehRefreshVehicleInfo(); }, 250);
});
document.addEventListener("change", function(ev){
  if (state && state.mode === "livraison") {
    setTimeout(function(){ if (window.ehRefreshVehicleInfo) window.ehRefreshVehicleInfo(); }, 400);
  }
});
window.addEventListener("load", function(){
  if (state && state.mode === "livraison") {
    setTimeout(function(){ if (window.ehRefreshVehicleInfo) window.ehRefreshVehicleInfo(); }, 500);
  }
});
'''
    last = co_src.rstrip().rfind("}")
    if last > 0:
        co_src = co_src[:last] + "\n" + HOOK + "\n" + co_src[last:]
        log("Hook refresh vehicule ajoute", "OK")

# Verifier equilibre
if brace_diff(co_src) != 0:
    log(f"checkout.js desequilibre - ROLLBACK", "ERR")
    shutil.copy2(os.path.join(BAK, "checkout.js"), CHECKOUT)
else:
    open(CHECKOUT, "w", encoding="utf-8").write(co_src)
    log("checkout.js sauvegarde", "OK")

# ============================================================
# PHASE 2 : A.6-UI - Bouton changer vehicule dans drawer
# ============================================================
log("PHASE 2 : Bouton changer vehicule dans drawer", "STEP")

pharm = open(PHARM_JS, "r", encoding="utf-8").read()

# Ajouter le bouton dans le drawer si commande avec livraison + status en_attente/confirmee
OLD_DRAWER_ACTIONS = '''    // ---- Actions ----
    h += '<div class="ph-drawer-actions">';'''

NEW_DRAWER_ACTIONS = '''    // ---- Actions ----
    h += '<div class="ph-drawer-actions">';
    // Sprint A.6-UI : bouton changer vehicule
    if (o.delivery_mode === "livraison"
        && (o.status === "en_attente" || o.status === "confirmee")) {
      var vIco = (o.delivery_vehicle_type === "CAR") ? "&#128663;" : "&#128757;";
      var vLbl = (o.delivery_vehicle_type === "CAR") ? "voiture" : "moto";
      h += '<button type="button" class="ph-btn ph-btn-ghost" data-drawer-act="change_vehicle" data-ref="' + esc(o.reference) + '">'
        + vIco + ' Changer vehicule (' + vLbl + ')</button>';
    }'''

if "change_vehicle" in pharm:
    log("Bouton deja present", "WARN")
elif OLD_DRAWER_ACTIONS in pharm:
    pharm = pharm.replace(OLD_DRAWER_ACTIONS, NEW_DRAWER_ACTIONS, 1)
    log("Bouton 'Changer vehicule' ajoute dans drawer", "OK")
else:
    log("Ancre drawer actions introuvable", "WARN")

# Ajouter le handler pour change_vehicle
if "data-drawer-act === \"change_vehicle\"" not in pharm and "act === \"change_vehicle\"" not in pharm:
    # Trouver le handler d'actions drawer
    # Chercher "// Action dans le drawer" et ajouter avant
    ANCHOR = '''    // Action dans le drawer
    var act = ev.target.closest ? ev.target.closest("[data-drawer-act]") : null;'''

    NEW_ANCHOR = '''    // Sprint A.6-UI : changer vehicule
    var chBtn = ev.target.closest ? ev.target.closest('[data-drawer-act="change_vehicle"]') : null;
    if (chBtn) {
      ev.preventDefault();
      var chRef = chBtn.getAttribute("data-ref");
      if (window.EHModal && window.EHModal.prompt) {
        window.EHModal.prompt(
          "Changer le vehicule",
          "Commande : " + chRef + "\\n\\nSaisissez MOTO ou CAR (le tarif sera recalcule automatiquement).",
          { kind: "info", placeholder: "MOTO ou CAR", requireValue: true, confirmLabel: "Changer" }
        ).then(function(v){
          if (!v) return;
          var target = String(v).trim().toUpperCase();
          if (target !== "MOTO" && target !== "CAR") {
            window.EHModal.alert("Erreur", "Valeur invalide. Utilisez MOTO ou CAR.", "danger");
            return;
          }
          fetch("/api/orders/" + encodeURIComponent(chRef) + "/vehicle", {
            method: "PATCH",
            credentials: "same-origin",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ vehicle_type: target, reason: "Override manuel" })
          }).then(function(r){
            return r.json().then(function(d){
              if (!r.ok) throw new Error(d.detail || "Erreur");
              window.EHModal.alert("Vehicule modifie",
                "Nouveau tarif : " + Math.round(d.delivery_fee || 0).toLocaleString("fr-FR") + " FCFA",
                "success");
              if (window.phOpenDrawer) setTimeout(function(){ window.phOpenDrawer(chRef); }, 300);
              if (window.phLoadOrdersV2) setTimeout(function(){ window.phLoadOrdersV2(); }, 400);
            });
          }).catch(function(e){
            window.EHModal.alert("Erreur", e.message, "danger");
          });
        });
      }
      return;
    }

    // Action dans le drawer
    var act = ev.target.closest ? ev.target.closest("[data-drawer-act]") : null;'''

    if ANCHOR in pharm:
        pharm = pharm.replace(ANCHOR, NEW_ANCHOR, 1)
        log("Handler 'change_vehicle' ajoute", "OK")
    else:
        log("Ancre handler introuvable", "WARN")

if brace_diff(pharm) != 0:
    log(f"pharmacien.js desequilibre - ROLLBACK", "ERR")
    shutil.copy2(os.path.join(BAK, "pharmacien.js"), PHARM_JS)
else:
    open(PHARM_JS, "w", encoding="utf-8").write(pharm)
    log("pharmacien.js sauvegarde", "OK")

# ============================================================
# PHASE 3 : A.8 - Section seuils dans Admin HTML
# ============================================================
log("PHASE 3 : Section seuils dans Admin", "STEP")

html = open(PHARM_HTML, "r", encoding="utf-8").read()

if 'id="settings-delivery-intel"' in html:
    log("Section deja presente", "WARN")
else:
    SECTION = '''
      <!-- SPRINT A.8 : Livraison intelligente -->
      <div class="settings-sub" style="margin-top:24px">&#128666; Livraison intelligente</div>
      <p class="muted small">Bascule automatiquement moto &rarr; voiture selon les seuils.</p>
      <div id="settings-delivery-intel" style="display:flex;flex-direction:column;gap:12px;margin-top:10px">
        <div class="settings-row" style="align-items:center;gap:10px">
          <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
            <input type="checkbox" id="delivery-auto-switch" style="width:18px;height:18px">
            Activer la selection automatique moto/voiture
          </label>
        </div>
        <div class="settings-grid">
          <div>
            <label for="threshold-units">Seuil unites (voiture si &ge;)</label>
            <div class="settings-row">
              <input type="number" id="threshold-units" min="1" step="1" placeholder="40">
              <span class="muted">unites</span>
            </div>
          </div>
          <div>
            <label for="threshold-lines">Seuil lignes distinctes</label>
            <div class="settings-row">
              <input type="number" id="threshold-lines" min="1" step="1" placeholder="10">
              <span class="muted">produits</span>
            </div>
          </div>
          <div>
            <label for="threshold-amount">Seuil montant</label>
            <div class="settings-row">
              <input type="number" id="threshold-amount" min="0" step="1000" placeholder="80000">
              <span class="muted">FCFA</span>
            </div>
          </div>
        </div>
        <p class="muted small" style="font-size:12px;line-height:1.5">
          &#8505; Si <strong>un seul</strong> seuil est atteint &rarr; voiture. Sinon &rarr; moto.<br>
          Les tarifs moto et voiture sont configures plus haut.
        </p>
      </div>
'''

    # Inserer avant la fin du form settings
    anchor = '</form>'
    idx = html.find(anchor)
    if idx > 0:
        # Trouver le bon form (celui avec settings-form)
        # Chercher le 1er </form> apres settings-form
        form_idx = html.find('id="settings-form"')
        if form_idx > 0:
            end_form = html.find("</form>", form_idx)
            if end_form > 0:
                html = html[:end_form] + SECTION + html[end_form:]
                log("Section seuils injectee dans form", "OK")
            else:
                log("Fin form introuvable", "ERR")
        else:
            log("settings-form introuvable", "ERR")
    else:
        log("</form> introuvable", "ERR")

if "</form>" in html:
    pass  # deja sauvegarde ci-dessus

open(PHARM_HTML, "w", encoding="utf-8").write(html)
log("pharmacien.html sauvegarde", "OK")

# ============================================================
# PHASE 4 : A.8 - JS pour charger/sauver les seuils
# ============================================================
log("PHASE 4 : JS chargement/sauvegarde seuils", "STEP")

pharm = open(PHARM_JS, "r", encoding="utf-8").read()

# Ajouter le chargement dans loadSettingsDashboard
OLD_LOAD = '''    var pnum = document.getElementById("payment-number-input");
    if (pnum) pnum.value = s.payment_number || "";
    var pname = document.getElementById("payment-name-input");
    if (pname) pname.value = s.payment_name || "";'''

NEW_LOAD = '''    var pnum = document.getElementById("payment-number-input");
    if (pnum) pnum.value = s.payment_number || "";
    var pname = document.getElementById("payment-name-input");
    if (pname) pname.value = s.payment_name || "";

    // Sprint A.8 : seuils livraison intelligente
    var _das = document.getElementById("delivery-auto-switch");
    if (_das) _das.checked = (s.delivery_auto_switch === 1 || s.delivery_auto_switch === true);
    var _tu = document.getElementById("threshold-units");
    if (_tu) _tu.value = (s.threshold_units != null ? s.threshold_units : 40);
    var _tl = document.getElementById("threshold-lines");
    if (_tl) _tl.value = (s.threshold_distinct_lines != null ? s.threshold_distinct_lines : 10);
    var _ta = document.getElementById("threshold-amount");
    if (_ta) _ta.value = (s.threshold_amount != null ? s.threshold_amount : 80000);'''

if "threshold_units != null" in pharm:
    log("Chargement seuils deja present", "WARN")
elif OLD_LOAD in pharm:
    pharm = pharm.replace(OLD_LOAD, NEW_LOAD, 1)
    log("Chargement seuils ajoute", "OK")
else:
    log("loadSettingsDashboard introuvable", "WARN")

# Ajouter dans submitSettings
OLD_SUBMIT = '''  var payload = {
    delivery_fee_default: num("fallback-fee-input"),
    delivery_base_fee: num("base-fee-input"),
    delivery_price_per_km: num("per-km-input"),
    delivery_max_km: num("max-km-input"),
    pharmacy_latitude: num("ph-lat-input"),
    pharmacy_longitude: num("ph-lon-input"),'''

NEW_SUBMIT = '''  var _das = document.getElementById("delivery-auto-switch");
  var payload = {
    delivery_fee_default: num("fallback-fee-input"),
    delivery_base_fee: num("base-fee-input"),
    delivery_price_per_km: num("per-km-input"),
    delivery_max_km: num("max-km-input"),
    pharmacy_latitude: num("ph-lat-input"),
    pharmacy_longitude: num("ph-lon-input"),
    // Sprint A.8 : seuils
    delivery_auto_switch: (_das && _das.checked) ? 1 : 0,
    threshold_units: num("threshold-units"),
    threshold_distinct_lines: num("threshold-lines"),
    threshold_amount: num("threshold-amount"),'''

if "threshold_units: num" in pharm:
    log("Submit seuils deja present", "WARN")
elif OLD_SUBMIT in pharm:
    pharm = pharm.replace(OLD_SUBMIT, NEW_SUBMIT, 1)
    log("Submit seuils ajoute", "OK")
else:
    log("submitSettings introuvable", "WARN")

if brace_diff(pharm) != 0:
    log(f"pharmacien.js desequilibre - ROLLBACK", "ERR")
    shutil.copy2(os.path.join(BAK, "pharmacien.js"), PHARM_JS)
else:
    open(PHARM_JS, "w", encoding="utf-8").write(pharm)
    log("pharmacien.js sauvegarde", "OK")

# ============================================================
# VERIFICATION FINALE
# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)

final_co = open(CHECKOUT, "r", encoding="utf-8").read()
final_pharm = open(PHARM_JS, "r", encoding="utf-8").read()
final_html = open(PHARM_HTML, "r", encoding="utf-8").read()

checks = [
    ("checkout : id eh-vehicle-info",          'id="eh-vehicle-info"' in final_co),
    ("checkout : helper async",                "async function ehRefreshVehicleInfo" in final_co),
    ("checkout : appel API /delivery/estimate","/api/delivery/estimate" in final_co),
    ("checkout : CSS badge",                   "eh-vehicle-moto" in final_co),
    ("checkout : equilibre",                   brace_diff(final_co) == 0),
    ("pharm : bouton change_vehicle",          "change_vehicle" in final_pharm),
    ("pharm : handler PATCH /vehicle",         "/vehicle" in final_pharm),
    ("pharm : chargement seuils",              "threshold_units != null" in final_pharm),
    ("pharm : submit seuils",                  "threshold_units: num" in final_pharm),
    ("pharm : equilibre",                      brace_diff(final_pharm) == 0),
    ("html : section seuils",                  'id="settings-delivery-intel"' in final_html),
    ("html : checkbox auto_switch",            'id="delivery-auto-switch"' in final_html),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

passed = sum(1 for _, ok in checks if ok)
print(f"\n  RESULTAT : {passed}/{len(checks)}")

print()
print(f"[BACKUP] {BAK}")
print()
print("[CMD] Pas de restart Uvicorn (frontend only).")
print()
print("[TEST] Edge : F12 > Application > Clear site data + Ctrl+Shift+R")
print("  1) Patient checkout mode livraison -> badge 'Livraison par moto/voiture'")
print("  2) Pharmacien drawer commande livraison -> bouton 'Changer vehicule'")
print("  3) Admin -> section 'Livraison intelligente' avec 4 champs")
print()
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\checkout.js" "{CHECKOUT}"')
print(f'  copy "{BAK}\\pharmacien.js" "{PHARM_JS}"')
print(f'  copy "{BAK}\\pharmacien.html" "{PHARM_HTML}"')