# -*- coding: utf-8 -*-
"""
1. Retire le bouton "Changer vehicule" du drawer
2. Diagnostic PRO : ou se trouve le checkout pro (demande/confirmer)?
"""
import os, re, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
PHARM_JS = os.path.join(ROOT, "static", "pharmacien.js")
STATIC = os.path.join(ROOT, "static")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_removebtn_{TS}")
os.makedirs(BAK, exist_ok=True)

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]"}[k]
    print(p, m)

def brace_diff(s): return s.count("{") - s.count("}")

shutil.copy2(PHARM_JS, os.path.join(BAK, "pharmacien.js"))
print("=" * 78)
print(f"REMOVE BTN + DIAG PRO - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

# ============================================================
# 1. Retirer le bouton "Changer vehicule"
# ============================================================
log("ACTION 1 : Retrait du bouton 'Changer vehicule'", "INFO")

pharm = open(PHARM_JS, "r", encoding="utf-8").read()

# Bouton dans drawer
BTN_BLOCK = '''    // Sprint A.6-UI : bouton changer vehicule
    if (o.delivery_mode === "livraison"
        && (o.status === "en_attente" || o.status === "confirmee")) {
      var vIco = (o.delivery_vehicle_type === "CAR") ? "&#128663;" : "&#128757;";
      var vLbl = (o.delivery_vehicle_type === "CAR") ? "voiture" : "moto";
      h += '<button type="button" class="ph-btn ph-btn-ghost" data-drawer-act="change_vehicle" data-ref="' + esc(o.reference) + '">'
        + vIco + ' Changer vehicule (' + vLbl + ')</button>';
    }
'''

if BTN_BLOCK in pharm:
    pharm = pharm.replace(BTN_BLOCK, "", 1)
    log("Bouton retire du drawer", "OK")
else:
    log("Bloc bouton introuvable", "WARN")

# Handler correspondant
HANDLER = '''    // Sprint A.6-UI : changer vehicule
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

'''

if HANDLER in pharm:
    pharm = pharm.replace(HANDLER, "", 1)
    log("Handler retire", "OK")
else:
    log("Handler introuvable", "WARN")

if brace_diff(pharm) != 0:
    log("pharmacien.js desequilibre - ROLLBACK", "ERR")
    shutil.copy2(os.path.join(BAK, "pharmacien.js"), PHARM_JS)
else:
    open(PHARM_JS, "w", encoding="utf-8").write(pharm)
    log("pharmacien.js sauvegarde", "OK")

# ============================================================
# 2. DIAGNOSTIC : ou est le checkout PRO ?
# ============================================================
print()
log("ACTION 2 : Diagnostic checkout PRO", "INFO")

# Chercher tous les fichiers PRO qui contiennent "livraison" ou "fee"
PRO_FILES = [
    "professional_demande.html",
    "professional_demande.js",
    "professional_demande_confirmer.html",
    "professional_demande_confirmer.js",
    "professional_commandes.html",
    "professional_catalogue.js",
    "professional_dashboard.js",
]

print("\n" + "=" * 78)
print("RECHERCHE : livraison / fee dans les fichiers PRO")
print("=" * 78)

found_any = False
for fname in PRO_FILES:
    fpath = os.path.join(STATIC, fname)
    if not os.path.isfile(fpath):
        continue
    src = open(fpath, "r", encoding="utf-8", errors="ignore").read()

    matches = []
    for kw in ["delivery_fee", "frais de livraison", "Frais de livraison",
               "livraison", "computeFee", "delivery/estimate", "delivery-vehicle",
               "vehicle_type"]:
        count = src.count(kw)
        if count > 0:
            matches.append((kw, count))

    if matches:
        found_any = True
        print(f"\n### {fname} ({len(src)} car.)")
        for kw, count in matches:
            print(f"  '{kw}': {count}")

        # Afficher les lignes cles
        for kw in ["delivery_fee", "computeFee", "delivery/estimate", "frais de livraison"]:
            for m in re.finditer(re.escape(kw), src):
                ln = src[:m.start()].count("\n") + 1
                line = src.split("\n")[ln - 1].strip()[:120]
                print(f"    L{ln}: {line}")
                break  # 1 seul exemple par mot-cle

if not found_any:
    print("\n  [!!] Aucun fichier PRO ne contient de logique de livraison")
    print("  -> Le calcul est peut-etre cote backend uniquement")

# Chercher dans le HTML pro la structure du recap
print("\n" + "=" * 78)
print("STRUCTURE du recap dans professional_demande_confirmer.html")
print("=" * 78)

conf_html = os.path.join(STATIC, "professional_demande_confirmer.html")
if os.path.isfile(conf_html):
    html = open(conf_html, "r", encoding="utf-8").read()
    # Chercher "recap", "total", "resume"
    for kw in ["recap", "resume", "total", "summary", "confirmer"]:
        for m in re.finditer(kw, html, re.IGNORECASE):
            ln = html[:m.start()].count("\n") + 1
            line = html.split("\n")[ln - 1].strip()[:120]
            if len(line) > 10:
                print(f"  L{ln}: {line}")
                break

# Chercher function render dans professional_demande_confirmer.js
print("\n" + "=" * 78)
print("Fonctions dans professional_demande_confirmer.js")
print("=" * 78)

conf_js = os.path.join(STATIC, "professional_demande_confirmer.js")
if os.path.isfile(conf_js):
    js = open(conf_js, "r", encoding="utf-8").read()
    for m in re.finditer(r"function\s+(\w+)\s*\(", js):
        ln = js[:m.start()].count("\n") + 1
        print(f"  L{ln}: function {m.group(1)}()")

    # Chercher "delivery" ou "fee" dans le JS
    for kw in ["delivery", "fee", "livraison"]:
        for m in re.finditer(kw, js, re.IGNORECASE):
            ln = js[:m.start()].count("\n") + 1
            line = js.split("\n")[ln - 1].strip()[:120]
            print(f"  [{kw}] L{ln}: {line}")
            break

print()
print("=" * 78)
print(f"[BACKUP] {BAK}")
print("[CMD] Pas de restart Uvicorn (frontend only).")
print("[TEST] F12 > Clear site data + Ctrl+Shift+R sur /pharmacien")
print("  -> Le bouton 'Changer vehicule' ne doit plus apparaitre")
print()
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\pharmacien.js" "{PHARM_JS}"')