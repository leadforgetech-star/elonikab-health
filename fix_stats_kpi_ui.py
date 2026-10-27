# -*- coding: utf-8 -*-
"""Ameliore le design des KPIs stats : icones, couleurs, labels."""
import os, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
CSS = os.path.join(ROOT, "static", "pharmacien_v6.css")
JS  = os.path.join(ROOT, "static", "pharmacien_stats.js")

TS  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, "_backup_kpi_ui_" + TS)
os.makedirs(BAK, exist_ok=True)

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]"}[k]
    print(p, m)

shutil.copy2(CSS, os.path.join(BAK, "pharmacien_v6.css"))
shutil.copy2(JS,  os.path.join(BAK, "pharmacien_stats.js"))

print("=" * 78)
print("FIX KPI UI - " + TS)
print("=" * 78)
print("[BACKUP] " + BAK + "\n")

# ============================================================
# 1. CSS : refonte des cartes KPI
# ============================================================
log("PHASE 1 : CSS refonte KPI", "INFO")

css_src = open(CSS, "r", encoding="utf-8").read()

OLD_CSS = '''.ph-stats-kpis{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
  gap:12px;margin-bottom:18px;
}
.ph-kpi{
  background:#fff;border:1px solid var(--ph-line);
  border-radius:14px;padding:16px 18px;
  display:flex;flex-direction:column;gap:4px;
}
.ph-kpi strong{
  font-size:26px;font-weight:800;color:var(--ph-blue-dark);
  line-height:1.1;
}
.ph-kpi span{
  font-size:11.5px;font-weight:700;color:var(--ph-muted);
  text-transform:uppercase;letter-spacing:.05em;
}
.ph-kpi-warn strong{color:#B26B00}
.ph-kpi-danger strong{color:#B23C3C}
.ph-kpi-ok strong{color:#0A7A5A}'''

NEW_CSS = '''.ph-stats-kpis{
  display:grid;
  grid-template-columns:repeat(4,1fr);
  gap:14px;margin-bottom:22px;
}
@media (max-width:800px){
  .ph-stats-kpis{grid-template-columns:repeat(2,1fr);gap:10px}
}
.ph-kpi{
  background:#fff;
  border:1px solid var(--ph-line);
  border-left:4px solid var(--ph-blue);
  border-radius:14px;
  padding:18px 18px 16px;
  display:flex;
  flex-direction:column;
  gap:6px;
  box-shadow:0 2px 8px rgba(15,23,42,.03);
  position:relative;
}
.ph-kpi-ico{
  font-size:22px;
  line-height:1;
  margin-bottom:2px;
}
.ph-kpi strong{
  font-size:28px;
  font-weight:800;
  color:var(--ph-ink);
  line-height:1.05;
  letter-spacing:-.02em;
  word-break:break-word;
}
.ph-kpi small{
  font-size:12px;
  font-weight:700;
  color:var(--ph-muted);
  text-transform:uppercase;
  letter-spacing:.06em;
  line-height:1.3;
}
.ph-kpi.ph-kpi-ok{border-left-color:#0A7A5A}
.ph-kpi.ph-kpi-ok strong{color:#0A7A5A}
.ph-kpi.ph-kpi-warn{border-left-color:#B26B00}
.ph-kpi.ph-kpi-warn strong{color:#B26B00}
.ph-kpi.ph-kpi-danger{border-left-color:#B23C3C}
.ph-kpi.ph-kpi-danger strong{color:#B23C3C}
.ph-kpi.ph-kpi-money strong{font-size:22px}

@media (max-width:720px){
  .ph-kpi{padding:14px 14px 12px}
  .ph-kpi strong{font-size:22px}
  .ph-kpi.ph-kpi-money strong{font-size:18px}
  .ph-kpi small{font-size:11px}
  .ph-kpi-ico{font-size:18px}
}'''

if NEW_CSS in css_src:
    log("CSS deja patche", "WARN")
elif OLD_CSS in css_src:
    css_src = css_src.replace(OLD_CSS, NEW_CSS, 1)
    open(CSS, "w", encoding="utf-8").write(css_src)
    log("CSS KPI refait", "OK")
else:
    log("Ancien CSS KPI introuvable", "WARN")

# ============================================================
# 2. JS : renderKPIs avec icones + labels propres
# ============================================================
log("PHASE 2 : JS renderKPIs", "INFO")

js_src = open(JS, "r", encoding="utf-8").read()

OLD_JS = '''  function renderKPIs(data) {
    var box = $("ph-stats-kpis");
    if (!box) return;
    var pays = data.payments_by_status || {};
    var verified = pays["VERIFIED"] || {count: 0, amount: 0};
    box.innerHTML = '';
    box.innerHTML =
      '<div class="ph-kpi ph-kpi-ok"><strong>' + (data.today_orders || 0) + '</strong><span>Aujourd hui</span></div>' +
      '<div class="ph-kpi"><strong>' + (data.total_orders || 0) + '</strong><span>Total commandes</span></div>' +
      '<div class="ph-kpi"><strong>' + fmtMoney(data.avg_basket || 0) + '</strong><span>Panier moyen</span></div>' +
      '<div class="ph-kpi ph-kpi-warn"><strong>' + (data.pending_verify || 0) + '</strong><span>A valider</span></div>';
  }'''

NEW_JS = '''  function renderKPIs(data) {
    var box = $("ph-stats-kpis");
    if (!box) return;
    box.innerHTML =
      '<div class="ph-kpi ph-kpi-ok">' +
        '<span class="ph-kpi-ico">&#128197;</span>' +
        '<strong>' + (data.today_orders || 0) + '</strong>' +
        '<small>Commandes aujourd&#39;hui</small>' +
      '</div>' +
      '<div class="ph-kpi">' +
        '<span class="ph-kpi-ico">&#128230;</span>' +
        '<strong>' + (data.total_orders || 0) + '</strong>' +
        '<small>Total commandes</small>' +
      '</div>' +
      '<div class="ph-kpi ph-kpi-money">' +
        '<span class="ph-kpi-ico">&#128176;</span>' +
        '<strong>' + fmtMoney(data.avg_basket || 0) + '</strong>' +
        '<small>Panier moyen</small>' +
      '</div>' +
      '<div class="ph-kpi ph-kpi-warn">' +
        '<span class="ph-kpi-ico">&#9203;</span>' +
        '<strong>' + (data.pending_verify || 0) + '</strong>' +
        '<small>Paiements a valider</small>' +
      '</div>';
  }'''

if "ph-kpi-ico" in js_src and "Commandes aujourd" in js_src:
    log("JS deja patche", "WARN")
elif OLD_JS in js_src:
    js_src = js_src.replace(OLD_JS, NEW_JS, 1)
    open(JS, "w", encoding="utf-8").write(js_src)
    log("renderKPIs ameliore", "OK")
else:
    log("Ancien renderKPIs introuvable", "WARN")

# ============================================================
# Verification
# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)

final_css = open(CSS, "r", encoding="utf-8").read()
final_js  = open(JS,  "r", encoding="utf-8").read()

checks = [
    ("CSS : border-left accent",     "border-left:4px solid var(--ph-blue)" in final_css),
    ("CSS : grille 4 colonnes",      "grid-template-columns:repeat(4,1fr)" in final_css),
    ("CSS : couleurs par statut",    ".ph-kpi-ok{border-left-color:#0A7A5A}" in final_css.replace(" ", "") or "ph-kpi-ok{border-left-color:#0A7A5A}" in final_css.replace(" ", "")),
    ("JS : icones injectees",        "ph-kpi-ico" in final_js),
    ("JS : label corrige",           "Commandes aujourd&#39;hui" in final_js),
    ("JS : KPI money stylise",       "ph-kpi-money" in final_js),
]
for label, ok in checks:
    print("  [" + ("OK" if ok else "!!") + "] " + label)

print()
print("[BACKUP] " + BAK)
print()
print("[CMD] Pas de restart Uvicorn (static only).")
print("[TEST] Edge : F12 > Application > Clear site data + Disable cache + Ctrl+Shift+R")
print("  1) /pharmacien -> onglet Stats")
print("  2) Les 4 cartes doivent avoir :")
print("     - Une bordure gauche coloree")
print("     - Une icone en haut")
print("     - Le chiffre en gros")
print("     - Le libelle en dessous (petites majuscules)")
print()
print("[ROLLBACK] :")
print('  copy "' + BAK + '\\pharmacien_v6.css" "' + CSS + '"')
print('  copy "' + BAK + '\\pharmacien_stats.js" "' + JS + '"')