# -*- coding: utf-8 -*-
"""
SPRINT B+C - FRONTEND COMPLET
==============================
- Nouvel onglet "Compta" dans la sidebar
- Vue Direction (dashboard recettes + stock)
- Comptabilite (bilan, depenses, journal, export)
- Fournisseurs + Commandes d'achat (dans Admin)
- Valorisation + Previsions stock (dans Stock)

Atomic + rollback auto.
"""
import os, re, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
HTML = os.path.join(ROOT, "static", "pharmacien.html")
CSS  = os.path.join(ROOT, "static", "compta_fournisseurs.css")
JS   = os.path.join(ROOT, "static", "compta_fournisseurs.js")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_sprintBCfe_{TS}")
os.makedirs(BAK, exist_ok=True)

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]", "STEP": "\n###"}[k]
    print(p, m)

def brace_diff(s): return s.count("{") - s.count("}")

shutil.copy2(HTML, os.path.join(BAK, "pharmacien.html"))
print("=" * 78)
print(f"SPRINT B+C FRONTEND - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

# ============================================================
# CSS - compta_fournisseurs.css
# ============================================================
CSS_CODE = """/* ============================================================
   Elonikab Health - Compta / Fournisseurs / Achats (Sprint B+C)
   ============================================================ */
body[data-active-page="compta"] [data-ph-page="compta"]{display:block !important}

.ph-compta-page{
  min-height:calc(100vh - 66px); background:var(--ph-bg);
  padding:22px 18px 60px;
}
.ph-compta-inner{max-width:1240px; margin:0 auto}

.ph-compta-head{
  display:flex; justify-content:space-between; align-items:flex-start;
  gap:12px; margin-bottom:18px; flex-wrap:wrap;
}
.ph-compta-title{
  font-size:24px; font-weight:800; letter-spacing:-.02em;
  color:var(--ph-ink); margin:0 0 4px;
}
.ph-compta-sub{font-size:14px; color:var(--ph-muted); margin:0}

/* Navigation interne */
.ph-compta-nav{
  display:flex; gap:6px; flex-wrap:wrap;
  margin-bottom:18px;
  border-bottom:1px solid var(--ph-line);
  padding-bottom:0;
}
.ph-compta-tab{
  border:0; background:transparent;
  padding:10px 16px; font-family:inherit;
  font-size:13.5px; font-weight:800; color:var(--ph-muted);
  cursor:pointer; border-bottom:2px solid transparent;
  margin-bottom:-1px; transition:.15s;
}
.ph-compta-tab:hover{color:var(--ph-blue)}
.ph-compta-tab.active{color:var(--ph-blue); border-bottom-color:var(--ph-blue)}

.ph-compta-panel{display:none}
.ph-compta-panel.active{display:block}

/* KPIs */
.ph-compta-kpis{
  display:grid;
  grid-template-columns:repeat(4,1fr);
  gap:14px; margin-bottom:22px;
}
@media (max-width:900px){
  .ph-compta-kpis{grid-template-columns:repeat(2,1fr);gap:10px}
}
@media (max-width:500px){
  .ph-compta-kpis{grid-template-columns:1fr}
}

.ph-compta-kpi{
  background:#fff; border:1px solid var(--ph-line);
  border-left:4px solid var(--ph-blue);
  border-radius:14px; padding:16px 18px;
  display:flex; flex-direction:column; gap:6px;
  box-shadow:0 2px 8px rgba(15,23,42,.03);
}
.ph-compta-kpi strong{
  font-size:24px; font-weight:800; color:var(--ph-ink);
  line-height:1.05; letter-spacing:-.02em;
}
.ph-compta-kpi small{
  font-size:11.5px; font-weight:700; color:var(--ph-muted);
  text-transform:uppercase; letter-spacing:.05em;
}
.ph-compta-kpi.ok{border-left-color:#0A7A5A}
.ph-compta-kpi.ok strong{color:#0A7A5A}
.ph-compta-kpi.warn{border-left-color:#B26B00}
.ph-compta-kpi.warn strong{color:#B26B00}
.ph-compta-kpi.danger{border-left-color:#B23C3C}
.ph-compta-kpi.danger strong{color:#B23C3C}

/* Toolbar */
.ph-compta-toolbar{
  display:flex; gap:10px; align-items:center; flex-wrap:wrap;
  margin-bottom:14px;
}
.ph-compta-month{
  padding:10px 14px; border:1.5px solid var(--ph-line);
  border-radius:10px; font-family:inherit; font-size:14px;
  background:#fff;
}
.ph-compta-select{
  padding:10px 14px; border:1.5px solid var(--ph-line);
  border-radius:10px; background:#fff; font-family:inherit;
  font-size:14px; cursor:pointer;
}

/* Tableau */
.ph-compta-table-wrap{
  background:#fff; border:1px solid var(--ph-line);
  border-radius:14px; overflow:hidden;
  margin-bottom:16px;
}
.ph-compta-table{
  width:100%; border-collapse:collapse; font-size:13.5px;
}
.ph-compta-table th{
  background:#F5F8FC; text-align:left; padding:12px 14px;
  font-size:11.5px; text-transform:uppercase; letter-spacing:.05em;
  color:var(--ph-muted); font-weight:800;
  border-bottom:1px solid var(--ph-line);
}
.ph-compta-table td{
  padding:12px 14px; border-bottom:1px solid #F1F5F9;
  vertical-align:middle;
}
.ph-compta-table tr:last-child td{border-bottom:0}
.ph-compta-table tr:hover td{background:#FAFBFC}
.ph-compta-table td.num{text-align:right;font-weight:800;color:var(--ph-ink)}
.ph-compta-table td.pos{color:#0A7A5A}
.ph-compta-table td.neg{color:#B23C3C}

/* Footer bilan */
.ph-compta-bilan{
  display:grid; grid-template-columns:repeat(3,1fr);
  gap:14px; margin-bottom:20px;
}
@media (max-width:700px){.ph-compta-bilan{grid-template-columns:1fr}}
.ph-compta-bilan-card{
  background:#fff; border:1px solid var(--ph-line);
  border-radius:14px; padding:18px;
}
.ph-compta-bilan-card h3{
  font-size:12px; font-weight:800; color:var(--ph-muted);
  text-transform:uppercase; letter-spacing:.06em;
  margin:0 0 8px;
}
.ph-compta-bilan-card .val{
  font-size:22px; font-weight:800; color:var(--ph-ink);
}
.ph-compta-bilan-card .val.pos{color:#0A7A5A}
.ph-compta-bilan-card .val.neg{color:#B23C3C}
.ph-compta-bilan-card small{
  font-size:12px; color:var(--ph-muted);
  display:block; margin-top:4px;
}

/* Formulaire inline */
.ph-compta-form{
  background:#fff; border:1px solid var(--ph-line);
  border-radius:14px; padding:18px;
  margin-bottom:16px;
}
.ph-compta-form h3{
  font-size:14px; font-weight:800; color:var(--ph-ink);
  margin:0 0 14px; text-transform:uppercase; letter-spacing:.04em;
}
.ph-compta-form-row{
  display:grid; grid-template-columns:1fr 1fr; gap:12px;
  margin-bottom:12px;
}
@media (max-width:600px){.ph-compta-form-row{grid-template-columns:1fr}}
.ph-compta-field label{
  display:block; font-size:12px; font-weight:700;
  color:var(--ph-ink); margin-bottom:5px;
}
.ph-compta-field input,
.ph-compta-field select,
.ph-compta-field textarea{
  width:100%; box-sizing:border-box;
  border:1.5px solid var(--ph-line); border-radius:10px;
  padding:10px 12px; font-size:14px; font-family:inherit;
  outline:none; transition:.15s;
}
.ph-compta-field input:focus,
.ph-compta-field select:focus,
.ph-compta-field textarea:focus{
  border-color:var(--ph-blue);
  box-shadow:0 0 0 3px var(--ph-blue-soft);
}
.ph-compta-actions{
  display:flex; gap:8px; justify-content:flex-end;
  margin-top:8px;
}

/* Boutons reutilises */
.ph-compta-btn{
  display:inline-flex; align-items:center; justify-content:center;
  gap:6px; padding:10px 16px; border-radius:10px;
  font-family:inherit; font-size:13.5px; font-weight:700;
  cursor:pointer; border:1px solid transparent; transition:.15s;
  white-space:nowrap;
}
.ph-compta-btn-primary{background:var(--ph-blue); color:#fff; border-color:var(--ph-blue)}
.ph-compta-btn-primary:hover{background:var(--ph-blue-dark)}
.ph-compta-btn-primary:disabled{opacity:.5; cursor:not-allowed}
.ph-compta-btn-ghost{background:#fff; color:var(--ph-ink); border-color:var(--ph-line)}
.ph-compta-btn-ghost:hover{border-color:var(--ph-blue); color:var(--ph-blue)}
.ph-compta-btn-danger{background:#fff; color:#B23C3C; border-color:var(--ph-line)}
.ph-compta-btn-danger:hover{background:#FDECEC; border-color:#B23C3C}
.ph-compta-btn-sm{padding:7px 12px; font-size:12.5px}

/* Modal simple */
.ph-compta-modal-backdrop{
  position:fixed; inset:0; z-index:10000;
  background:rgba(15,23,42,.5);
  display:none; align-items:center; justify-content:center;
  padding:16px;
}
.ph-compta-modal-backdrop.show{display:flex}
.ph-compta-modal{
  background:#fff; border-radius:16px;
  max-width:560px; width:100%; max-height:90vh;
  display:flex; flex-direction:column;
  box-shadow:0 24px 60px rgba(15,23,42,.3);
}
.ph-compta-modal-head{
  padding:16px 20px; border-bottom:1px solid var(--ph-line);
  display:flex; justify-content:space-between; align-items:center; gap:12px;
}
.ph-compta-modal-head h3{margin:0; font-size:17px; font-weight:800}
.ph-compta-modal-close{
  width:32px; height:32px; border-radius:8px;
  border:1px solid var(--ph-line); background:#fff;
  cursor:pointer; font-size:18px; color:var(--ph-muted);
  display:flex; align-items:center; justify-content:center;
}
.ph-compta-modal-body{padding:18px 20px; overflow-y:auto; flex:1}
.ph-compta-modal-foot{
  padding:14px 20px; border-top:1px solid var(--ph-line);
  display:flex; justify-content:flex-end; gap:8px;
}

/* Toast */
.ph-compta-toast{
  position:fixed; bottom:90px; left:50%; transform:translateX(-50%);
  background:var(--ph-ink); color:#fff; padding:12px 20px;
  border-radius:11px; font-size:13.5px; font-weight:700;
  box-shadow:0 10px 30px rgba(15,23,42,.25);
  z-index:99999; max-width:90vw; text-align:center;
}
.ph-compta-toast.ok{background:#0A7A5A}
.ph-compta-toast.err{background:#B23C3C}

/* Empty state */
.ph-compta-empty{
  text-align:center; padding:40px 20px;
  color:var(--ph-muted); font-size:13.5px;
}
"""

open(CSS, "w", encoding="utf-8").write(CSS_CODE)
log("compta_fournisseurs.css cree", "OK")

# ============================================================
# JS - compta_fournisseurs.js
# ============================================================
JS_CODE = r'''/* ============================================================
   Elonikab Health - Sprint B+C Frontend
   Compta + Fournisseurs + Achats + Vue Direction
   ============================================================ */
(function () {
  "use strict";
  var API = "/api";

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function fmtMoney(v) {
    var n = Math.round(Number(v) || 0);
    try { return n.toLocaleString("fr-FR") + " FCFA"; }
    catch (e) { return n + " FCFA"; }
  }
  function fmtDate(iso) {
    if (!iso) return "";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return iso;
      var pad = function(n){ return n < 10 ? "0" + n : "" + n; };
      return pad(d.getDate()) + "/" + pad(d.getMonth()+1) + "/" + d.getFullYear();
    } catch (e) { return iso; }
  }
  function toast(msg, kind) {
    var t = document.createElement("div");
    t.className = "ph-compta-toast " + (kind || "");
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 3000);
  }
  function apiCall(method, path, body) {
    var opts = { method: method, credentials: "same-origin", headers: {} };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(API + path, opts).then(function (r) {
      return r.text().then(function (txt) {
        var d = null;
        try { d = txt ? JSON.parse(txt) : null; } catch (e) {}
        if (!r.ok) throw new Error((d && d.detail) || ("Erreur " + r.status));
        return d;
      });
    });
  }

  var currentMonth = (function(){
    var d = new Date();
    return d.getFullYear() + "-" + String(d.getMonth()+1).padStart(2,"0");
  })();
  var currentTab = "direction";

  // ============================================================
  // DIRECTION (dashboard mixte)
  // ============================================================
  function loadDirection() {
    var box = $("ph-compta-direction-content");
    if (box) box.innerHTML = '<div class="ph-compta-empty">Chargement...</div>';
    apiCall("GET", "/compta/dashboard").then(function (d) {
      if (!box) return;
      var benef = (d.benefice || 0);
      var benefCls = benef >= 0 ? "ok" : "danger";
      box.innerHTML =
        '<div class="ph-compta-kpis">' +
          '<div class="ph-compta-kpi"><strong>' + fmtMoney(d.recettes) + '</strong><small>Recettes du mois</small></div>' +
          '<div class="ph-compta-kpi warn"><strong>' + fmtMoney(d.depenses) + '</strong><small>Depenses du mois</small></div>' +
          '<div class="ph-compta-kpi ' + benefCls + '"><strong>' + fmtMoney(benef) + '</strong><small>Benefice</small></div>' +
          '<div class="ph-compta-kpi"><strong>' + fmtMoney(d.stock_value) + '</strong><small>Valeur stock</small></div>' +
        '</div>' +
        '<div class="ph-compta-bilan">' +
          '<div class="ph-compta-bilan-card">' +
            '<h3>Produits dormants</h3>' +
            '<div class="val">' + (d.dormant_products || 0) + ' produits</div>' +
            '<small>Aucune vente depuis 60 jours</small>' +
          '</div>' +
          '<div class="ph-compta-bilan-card">' +
            '<h3>Mois</h3>' +
            '<div class="val">' + esc(d.month || "") + '</div>' +
            '<small>Periode analysee</small>' +
          '</div>' +
          '<div class="ph-compta-bilan-card">' +
            '<h3>Marge estimee</h3>' +
            '<div class="val">' + (d.recettes > 0 ? Math.round(benef / d.recettes * 100) : 0) + '%</div>' +
            '<small>Benefice / Recettes</small>' +
          '</div>' +
        '</div>';
    }).catch(function (e) {
      if (box) box.innerHTML = '<div class="ph-compta-empty" style="color:#B23C3C">Erreur : ' + esc(e.message) + '</div>';
    });
  }

  // ============================================================
  // BILAN
  // ============================================================
  function loadBilan() {
    var box = $("ph-compta-bilan-content");
    if (box) box.innerHTML = '<div class="ph-compta-empty">Chargement...</div>';
    apiCall("GET", "/compta/summary?month=" + encodeURIComponent(currentMonth)).then(function (d) {
      if (!box) return;
      var benef = (d.benefice || 0);
      var benefCls = benef >= 0 ? "ok" : "danger";
      var catsHtml = "";
      var cats = d.depenses_par_categorie || {};
      var catKeys = Object.keys(cats);
      if (catKeys.length > 0) {
        catsHtml = '<div class="ph-compta-table-wrap"><table class="ph-compta-table">' +
          '<thead><tr><th>Categorie</th><th style="text-align:right">Montant</th></tr></thead><tbody>';
        catKeys.forEach(function (k) {
          catsHtml += '<tr><td>' + esc(k) + '</td><td class="num neg">' + fmtMoney(cats[k]) + '</td></tr>';
        });
        catsHtml += '</tbody></table></div>';
      }
      box.innerHTML =
        '<div class="ph-compta-kpis">' +
          '<div class="ph-compta-kpi ok"><strong>' + fmtMoney(d.recettes) + '</strong><small>Recettes (' + (d.recettes_count||0) + ' cmd)</small></div>' +
          '<div class="ph-compta-kpi warn"><strong>' + fmtMoney(d.depenses) + '</strong><small>Depenses (' + (d.depenses_count||0) + ')</small></div>' +
          '<div class="ph-compta-kpi ' + benefCls + '"><strong>' + fmtMoney(benef) + '</strong><small>Benefice net</small></div>' +
          '<div class="ph-compta-kpi"><strong>' + (d.marge_pct || 0) + '%</strong><small>Marge estimee</small></div>' +
        '</div>' +
        (catKeys.length > 0 ? '<h3 style="font-size:13px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:#64748B;margin:20px 0 10px">Depenses par categorie</h3>' + catsHtml : '');
    }).catch(function (e) {
      if (box) box.innerHTML = '<div class="ph-compta-empty" style="color:#B23C3C">Erreur : ' + esc(e.message) + '</div>';
    });
  }

  // ============================================================
  // DEPENSES
  // ============================================================
  var expensesCache = [];

  function loadExpenses() {
    var box = $("ph-compta-expenses-content");
    if (box) box.innerHTML = '<div class="ph-compta-empty">Chargement...</div>';
    apiCall("GET", "/compta/expenses?month=" + encodeURIComponent(currentMonth)).then(function (list) {
      expensesCache = list || [];
      renderExpenses();
    }).catch(function (e) {
      if (box) box.innerHTML = '<div class="ph-compta-empty" style="color:#B23C3C">Erreur : ' + esc(e.message) + '</div>';
    });
  }

  function renderExpenses() {
    var box = $("ph-compta-expenses-content");
    if (!box) return;
    var cats = ["Loyer","Salaires","Electricite","Eau","Internet","Fournitures","Transport","Entretien","Taxes","Autre"];
    var catOpts = cats.map(function(c){ return '<option value="' + c + '">' + c + '</option>'; }).join("");
    var h = '';
    h += '<div class="ph-compta-form">';
    h += '<h3>Ajouter une depense</h3>';
    h += '<div class="ph-compta-form-row">';
    h += '<div class="ph-compta-field"><label>Categorie *</label><select id="exp-cat">' + catOpts + '</select></div>';
    h += '<div class="ph-compta-field"><label>Libelle *</label><input id="exp-label" placeholder="Ex: Loyer Octobre"></div>';
    h += '</div>';
    h += '<div class="ph-compta-form-row">';
    h += '<div class="ph-compta-field"><label>Montant (FCFA) *</label><input id="exp-amount" type="number" min="1" step="50" placeholder="50000"></div>';
    h += '<div class="ph-compta-field"><label>Date *</label><input id="exp-date" type="date" value="' + new Date().toISOString().slice(0,10) + '"></div>';
    h += '</div>';
    h += '<div class="ph-compta-form-row">';
    h += '<div class="ph-compta-field"><label>Fournisseur (optionnel)</label><input id="exp-supplier" placeholder="Ex: Npower"></div>';
    h += '<div class="ph-compta-field"><label>Reference (optionnel)</label><input id="exp-ref" placeholder="Facture #123"></div>';
    h += '</div>';
    h += '<div class="ph-compta-actions"><button type="button" class="ph-compta-btn ph-compta-btn-primary" id="exp-add-btn">+ Ajouter</button></div>';
    h += '</div>';

    // Tableau
    h += '<div class="ph-compta-table-wrap"><table class="ph-compta-table">';
    h += '<thead><tr><th>Date</th><th>Categorie</th><th>Libelle</th><th style="text-align:right">Montant</th><th></th></tr></thead><tbody>';
    if (expensesCache.length === 0) {
      h += '<tr><td colspan="5" style="text-align:center;padding:30px;color:#94A3B8">Aucune depense ce mois</td></tr>';
    } else {
      expensesCache.forEach(function(e){
        h += '<tr>';
        h += '<td>' + esc(fmtDate(e.expense_date)) + '</td>';
        h += '<td>' + esc(e.category) + '</td>';
        h += '<td>' + esc(e.label) + '</td>';
        h += '<td class="num neg">' + fmtMoney(e.amount) + '</td>';
        h += '<td style="text-align:right"><button type="button" class="ph-compta-btn ph-compta-btn-danger ph-compta-btn-sm" data-del-exp="' + e.id + '">Suppr.</button></td>';
        h += '</tr>';
      });
    }
    h += '</tbody></table></div>';
    box.innerHTML = h;
    var addBtn = $("exp-add-btn");
    if (addBtn) addBtn.addEventListener("click", addExpense);
  }

  function addExpense() {
    var payload = {
      category: $("exp-cat").value,
      label: ($("exp-label").value || "").trim(),
      amount: parseFloat($("exp-amount").value),
      expense_date: $("exp-date").value,
      supplier_name: ($("exp-supplier").value || "").trim(),
      reference: ($("exp-ref").value || "").trim(),
    };
    if (!payload.label) { toast("Libelle obligatoire", "err"); return; }
    if (!payload.amount || payload.amount <= 0) { toast("Montant invalide", "err"); return; }
    if (!payload.expense_date) { toast("Date obligatoire", "err"); return; }
    var btn = $("exp-add-btn");
    if (btn) { btn.disabled = true; btn.textContent = "..."; }
    apiCall("POST", "/compta/expenses", payload).then(function () {
      toast("Depense ajoutee", "ok");
      loadExpenses();
    }).catch(function (e) {
      toast(e.message, "err");
      if (btn) { btn.disabled = false; btn.textContent = "+ Ajouter"; }
    });
  }

  // ============================================================
  // JOURNAL DE CAISSE
  // ============================================================
  function loadJournal() {
    var box = $("ph-compta-journal-content");
    if (box) box.innerHTML = '<div class="ph-compta-empty">Chargement...</div>';
    apiCall("GET", "/compta/journal?month=" + encodeURIComponent(currentMonth)).then(function (list) {
      if (!box) return;
      if (!list || list.length === 0) {
        box.innerHTML = '<div class="ph-compta-empty">Aucune ecriture ce mois</div>';
        return;
      }
      var h = '<div class="ph-compta-table-wrap"><table class="ph-compta-table">';
      h += '<thead><tr><th>Date</th><th>Type</th><th>Libelle</th><th>Ref.</th><th style="text-align:right">Montant</th></tr></thead><tbody>';
      list.forEach(function(j){
        var isIn = j.type === "IN";
        var cls = isIn ? "pos" : "neg";
        h += '<tr>';
        h += '<td>' + esc((j.created_at||"").slice(0,10)) + '</td>';
        h += '<td><span style="padding:3px 10px;border-radius:999px;font-size:11px;font-weight:800;background:' + (isIn ? '#E6F7F1' : '#FDECEC') + ';color:' + (isIn ? '#0A7A5A' : '#B23C3C') + '">' + esc(j.type) + '</span></td>';
        h += '<td>' + esc(j.label) + '</td>';
        h += '<td style="font-family:Consolas,monospace;font-size:11.5px;color:#64748B">' + esc(j.reference || "—") + '</td>';
        h += '<td class="num ' + cls + '">' + (isIn ? "+" : "−") + fmtMoney(j.amount) + '</td>';
        h += '</tr>';
      });
      h += '</tbody></table></div>';
      box.innerHTML = h;
    }).catch(function (e) {
      if (box) box.innerHTML = '<div class="ph-compta-empty" style="color:#B23C3C">Erreur : ' + esc(e.message) + '</div>';
    });
  }

  // ============================================================
  // FOURNISSEURS
  // ============================================================
  function loadSuppliers() {
    var box = $("ph-suppliers-content");
    if (!box) return;
    box.innerHTML = '<div class="ph-compta-empty">Chargement...</div>';
    apiCall("GET", "/admin/suppliers").then(function (list) {
      var h = '';
      h += '<div class="ph-compta-form"><h3>Ajouter un fournisseur</h3>';
      h += '<div class="ph-compta-form-row">';
      h += '<div class="ph-compta-field"><label>Nom *</label><input id="sup-name" placeholder="Ex: Grossiste Medora"></div>';
      h += '<div class="ph-compta-field"><label>Telephone</label><input id="sup-phone" placeholder="+228..."></div>';
      h += '</div>';
      h += '<div class="ph-compta-form-row">';
      h += '<div class="ph-compta-field"><label>Contact</label><input id="sup-contact" placeholder="Nom du contact"></div>';
      h += '<div class="ph-compta-field"><label>Email</label><input id="sup-email" type="email" placeholder="contact@..."></div>';
      h += '</div>';
      h += '<div class="ph-compta-actions"><button type="button" class="ph-compta-btn ph-compta-btn-primary" id="sup-add-btn">+ Ajouter</button></div>';
      h += '</div>';
      h += '<div class="ph-compta-table-wrap"><table class="ph-compta-table">';
      h += '<thead><tr><th>Nom</th><th>Contact</th><th>Telephone</th><th>Email</th><th></th></tr></thead><tbody>';
      if (!list || list.length === 0) {
        h += '<tr><td colspan="5" style="text-align:center;padding:30px;color:#94A3B8">Aucun fournisseur</td></tr>';
      } else {
        list.forEach(function(s){
          h += '<tr><td><strong>' + esc(s.name) + '</strong></td>';
          h += '<td>' + esc(s.contact_name || "—") + '</td>';
          h += '<td>' + esc(s.phone || "—") + '</td>';
          h += '<td>' + esc(s.email || "—") + '</td>';
          h += '<td style="text-align:right"><button type="button" class="ph-compta-btn ph-compta-btn-danger ph-compta-btn-sm" data-del-sup="' + s.id + '">Archiver</button></td></tr>';
        });
      }
      h += '</tbody></table></div>';
      box.innerHTML = h;
      var btn = $("sup-add-btn");
      if (btn) btn.addEventListener("click", addSupplier);
    }).catch(function (e) {
      box.innerHTML = '<div class="ph-compta-empty" style="color:#B23C3C">Erreur : ' + esc(e.message) + '</div>';
    });
  }

  function addSupplier() {
    var payload = {
      name: ($("sup-name").value || "").trim(),
      contact_name: ($("sup-contact").value || "").trim(),
      phone: ($("sup-phone").value || "").trim(),
      email: ($("sup-email").value || "").trim(),
    };
    if (!payload.name || payload.name.length < 2) { toast("Nom obligatoire", "err"); return; }
    var btn = $("sup-add-btn");
    if (btn) { btn.disabled = true; btn.textContent = "..."; }
    apiCall("POST", "/admin/suppliers", payload).then(function () {
      toast("Fournisseur ajoute", "ok");
      loadSuppliers();
    }).catch(function (e) {
      toast(e.message, "err");
      if (btn) { btn.disabled = false; btn.textContent = "+ Ajouter"; }
    });
  }

  // ============================================================
  // COMMANDES D'ACHAT
  // ============================================================
  function loadPurchaseOrders() {
    var box = $("ph-po-content");
    if (!box) return;
    box.innerHTML = '<div class="ph-compta-empty">Chargement...</div>';
    apiCall("GET", "/admin/purchase-orders").then(function (list) {
      var h = '<div class="ph-compta-toolbar">';
      h += '<button type="button" class="ph-compta-btn ph-compta-btn-primary" id="po-new-btn">+ Nouvelle commande</button>';
      h += '</div>';
      h += '<div class="ph-compta-table-wrap"><table class="ph-compta-table">';
      h += '<thead><tr><th>Reference</th><th>Fournisseur</th><th>Statut</th><th style="text-align:right">Montant</th><th></th></tr></thead><tbody>';
      if (!list || list.length === 0) {
        h += '<tr><td colspan="5" style="text-align:center;padding:30px;color:#94A3B8">Aucune commande d\'achat</td></tr>';
      } else {
        list.forEach(function(po){
          var stLbl = {draft:"Brouillon", received:"Recue", cancelled:"Annulee"}[po.status] || po.status;
          var stCol = po.status === "received" ? "#0A7A5A" : (po.status === "draft" ? "#B26B00" : "#64748B");
          h += '<tr>';
          h += '<td style="font-family:Consolas,monospace;font-weight:800;color:#174A7E">' + esc(po.reference) + '</td>';
          h += '<td>' + esc(po.supplier_name || "—") + '</td>';
          h += '<td><span style="padding:3px 10px;border-radius:999px;font-size:11px;font-weight:800;background:#E2E8F0;color:' + stCol + '">' + esc(stLbl) + '</span></td>';
          h += '<td class="num">' + fmtMoney(po.total_amount) + '</td>';
          h += '<td style="text-align:right">';
          if (po.status === "draft") {
            h += '<button type="button" class="ph-compta-btn ph-compta-btn-ghost ph-compta-btn-sm" data-po-receive="' + po.id + '">Recevoir</button>';
          }
          h += '</td></tr>';
        });
      }
      h += '</tbody></table></div>';
      box.innerHTML = h;
      var nb = $("po-new-btn");
      if (nb) nb.addEventListener("click", openNewPO);
    }).catch(function (e) {
      box.innerHTML = '<div class="ph-compta-empty" style="color:#B23C3C">Erreur : ' + esc(e.message) + '</div>';
    });
  }

  function openNewPO() {
    apiCall("GET", "/admin/suppliers").then(function (sups) {
      if (!sups || sups.length === 0) {
        toast("Creez d'abord un fournisseur", "err");
        return;
      }
      var opts = sups.map(function(s){ return '<option value="' + s.id + '">' + esc(s.name) + '</option>'; }).join("");
      var html =
        '<div class="ph-compta-modal-head"><h3>Nouvelle commande d\'achat</h3>' +
        '<button type="button" class="ph-compta-modal-close" data-po-close>&times;</button></div>' +
        '<div class="ph-compta-modal-body">' +
          '<div class="ph-compta-field"><label>Fournisseur *</label><select id="po-sup">' + opts + '</select></div>' +
          '<div class="ph-compta-field" style="margin-top:12px"><label>Notes</label><textarea id="po-notes" rows="2"></textarea></div>' +
        '</div>' +
        '<div class="ph-compta-modal-foot">' +
          '<button type="button" class="ph-compta-btn ph-compta-btn-ghost" data-po-close>Annuler</button>' +
          '<button type="button" class="ph-compta-btn ph-compta-btn-primary" id="po-create-btn">Creer</button>' +
        '</div>';
      showModal(html);
      var cb = $("po-create-btn");
      if (cb) cb.addEventListener("click", function(){
        var sid = parseInt($("po-sup").value, 10);
        var notes = ($("po-notes").value || "").trim();
        apiCall("POST", "/admin/purchase-orders", {supplier_id: sid, notes: notes})
          .then(function(){
            closeModal();
            toast("Commande creee", "ok");
            loadPurchaseOrders();
          }).catch(function(e){ toast(e.message, "err"); });
      });
    });
  }

  // ============================================================
  // STOCK : VALORISATION + PREVISIONS
  // ============================================================
  function loadValuation() {
    var box = $("ph-stock-valuation");
    if (!box) return;
    box.innerHTML = '<div class="ph-compta-empty">Chargement...</div>';
    apiCall("GET", "/admin/stock/valuation").then(function (d) {
      var h = '<div class="ph-compta-kpis">' +
        '<div class="ph-compta-kpi"><strong>' + fmtMoney(d.total_purchase) + '</strong><small>Valeur achat</small></div>' +
        '<div class="ph-compta-kpi ok"><strong>' + fmtMoney(d.total_sell) + '</strong><small>Valeur vente</small></div>' +
        '<div class="ph-compta-kpi ' + ((d.potential_margin >= 0) ? 'ok' : 'danger') + '"><strong>' + fmtMoney(d.potential_margin) + '</strong><small>Marge potentielle</small></div>' +
        '</div>';
      var items = (d.items || []).filter(function(i){ return i.quantity > 0; });
      if (items.length > 0) {
        h += '<div class="ph-compta-table-wrap" style="margin-top:16px"><table class="ph-compta-table"><thead>';
        h += '<tr><th>Produit</th><th style="text-align:right">Qte</th><th style="text-align:right">Prix achat</th><th style="text-align:right">Prix vente</th><th style="text-align:right">Valeur</th></tr></thead><tbody>';
        items.slice(0, 50).forEach(function(it){
          h += '<tr><td>' + esc(it.name) + '</td>';
          h += '<td class="num">' + it.quantity + '</td>';
          h += '<td class="num">' + (it.purchase_price ? fmtMoney(it.purchase_price) : "—") + '</td>';
          h += '<td class="num">' + fmtMoney(it.sell_price) + '</td>';
          h += '<td class="num">' + fmtMoney(it.value_purchase) + '</td></tr>';
        });
        h += '</tbody></table></div>';
      } else {
        h += '<p class="ph-compta-empty">Aucun produit en stock</p>';
      }
      box.innerHTML = h;
    }).catch(function (e) {
      box.innerHTML = '<div class="ph-compta-empty" style="color:#B23C3C">Erreur : ' + esc(e.message) + '</div>';
    });
  }

  function loadForecast() {
    var box = $("ph-stock-forecast");
    if (!box) return;
    box.innerHTML = '<div class="ph-compta-empty">Chargement...</div>';
    apiCall("GET", "/admin/stock/forecast?days=30").then(function (d) {
      var items = (d.items || []).filter(function(i){ return i.sold_period > 0 || i.urgent; });
      if (items.length === 0) {
        box.innerHTML = '<div class="ph-compta-empty">Pas assez de donnees de vente pour prevoir</div>';
        return;
      }
      var h = '<div class="ph-compta-table-wrap"><table class="ph-compta-table"><thead>';
      h += '<tr><th>Produit</th><th style="text-align:right">Stock</th><th style="text-align:right">Vendus (30j)</th><th style="text-align:right">Jours restants</th><th style="text-align:right">Reappro</th></tr></thead><tbody>';
      items.sort(function(a,b){
        var da = a.days_left === null ? 9999 : a.days_left;
        var db = b.days_left === null ? 9999 : b.days_left;
        return da - db;
      });
      items.slice(0, 30).forEach(function(it){
        var daysTxt = it.days_left !== null ? (it.days_left + " j") : "—";
        var daysCls = (it.urgent) ? "neg" : "";
        h += '<tr>';
        h += '<td>' + esc(it.name) + (it.urgent ? ' <span style="color:#B23C3C;font-weight:800;font-size:11px">⚠ URGENT</span>' : '') + '</td>';
        h += '<td class="num">' + it.stock + '</td>';
        h += '<td class="num">' + it.sold_period + '</td>';
        h += '<td class="num ' + daysCls + '">' + daysTxt + '</td>';
        h += '<td class="num">' + (it.reorder_qty ? ("+" + it.reorder_qty) : "—") + '</td>';
        h += '</tr>';
      });
      h += '</tbody></table></div>';
      box.innerHTML = h;
    }).catch(function (e) {
      box.innerHTML = '<div class="ph-compta-empty" style="color:#B23C3C">Erreur : ' + esc(e.message) + '</div>';
    });
  }

  // ============================================================
  // Modal global
  // ============================================================
  function showModal(html) {
    var back = $("ph-compta-modal");
    if (!back) return;
    back.querySelector(".ph-compta-modal").innerHTML = html;
    back.classList.add("show");
    back.querySelectorAll("[data-po-close]").forEach(function(b){
      b.addEventListener("click", closeModal);
    });
    back.addEventListener("click", function(ev){
      if (ev.target === back) closeModal();
    });
  }
  function closeModal() {
    var back = $("ph-compta-modal");
    if (back) back.classList.remove("show");
  }

  // ============================================================
  // TABS
  // ============================================================
  function showTab(name) {
    currentTab = name;
    document.querySelectorAll(".ph-compta-tab").forEach(function(t){
      t.classList.toggle("active", t.getAttribute("data-compta-tab") === name);
    });
    document.querySelectorAll(".ph-compta-panel").forEach(function(p){
      p.classList.toggle("active", p.getAttribute("data-compta-panel") === name);
    });
    if (name === "direction") loadDirection();
    if (name === "bilan") loadBilan();
    if (name === "expenses") loadExpenses();
    if (name === "journal") loadJournal();
  }

  // ============================================================
  // EVENT DELEGATION
  // ============================================================
  document.addEventListener("click", function (ev) {
    var t = ev.target;
    var tab = t.closest ? t.closest("[data-compta-tab]") : null;
    if (tab) {
      ev.preventDefault();
      showTab(tab.getAttribute("data-compta-tab"));
      return;
    }
    // Nav principale : ouvrir compta
    var navTab = t.closest ? t.closest("[data-ph-tab]") : null;
    if (navTab) {
      var tn = navTab.getAttribute("data-ph-tab");
      if (tn === "compta") setTimeout(function(){ showTab(currentTab || "direction"); }, 150);
    }
    // Supprimer depense
    var delExp = t.closest ? t.closest("[data-del-exp]") : null;
    if (delExp) {
      ev.preventDefault();
      var eid = delExp.getAttribute("data-del-exp");
      if (confirm("Supprimer cette depense ?")) {
        apiCall("DELETE", "/compta/expenses/" + eid).then(function(){
          toast("Depense supprimee", "ok");
          loadExpenses();
        }).catch(function(e){ toast(e.message, "err"); });
      }
      return;
    }
    // Supprimer fournisseur
    var delSup = t.closest ? t.closest("[data-del-sup]") : null;
    if (delSup) {
      ev.preventDefault();
      var sid = delSup.getAttribute("data-del-sup");
      if (confirm("Archiver ce fournisseur ?")) {
        apiCall("DELETE", "/admin/suppliers/" + sid).then(function(){
          toast("Fournisseur archive", "ok");
          loadSuppliers();
        }).catch(function(e){ toast(e.message, "err"); });
      }
      return;
    }
    // Recevoir commande achat
    var recv = t.closest ? t.closest("[data-po-receive]") : null;
    if (recv) {
      ev.preventDefault();
      var poid = recv.getAttribute("data-po-receive");
      if (confirm("Recevoir cette commande ? Le stock sera mis a jour et la depense enregistree.")) {
        apiCall("PATCH", "/admin/purchase-orders/" + poid + "/receive", { update_stock: true, create_lots: true })
          .then(function(d){
            toast("Commande receptionnee (" + d.received + " articles)", "ok");
            loadPurchaseOrders();
          }).catch(function(e){ toast(e.message, "err"); });
      }
      return;
    }
    // Export CSV
    if (t.id === "ph-compta-export-btn") {
      ev.preventDefault();
      window.open("/api/compta/export.csv?month=" + encodeURIComponent(currentMonth), "_blank");
      return;
    }
  });

  // Changement de mois
  document.addEventListener("change", function (ev) {
    if (ev.target && ev.target.id === "ph-compta-month") {
      currentMonth = ev.target.value;
      if (currentTab === "bilan") loadBilan();
      else if (currentTab === "expenses") loadExpenses();
      else if (currentTab === "journal") loadJournal();
    }
  });

  // Init quand on ouvre compta
  document.addEventListener("DOMContentLoaded", function () {
    setTimeout(function () {
      if (document.body.getAttribute("data-active-page") === "compta") {
        showTab("direction");
      }
    }, 400);
  });

  window.phLoadCompta = loadDirection;
  window.phLoadSuppliers = loadSuppliers;
  window.phLoadPurchaseOrders = loadPurchaseOrders;
  window.phLoadValuation = loadValuation;
  window.phLoadForecast = loadForecast;
})();
'''

open(JS, "w", encoding="utf-8").write(JS_CODE)
log("compta_fournisseurs.js cree", "OK")

# ============================================================
# HTML - Ajouter onglet + section Compta + sections Admin + sections Stock
# ============================================================
log("PHASE HTML : Onglet + Sections", "STEP")

html = open(HTML, "r", encoding="utf-8").read()

# 1. Onglet "Compta" dans la sidebar
if 'data-ph-tab="compta"' not in html:
    OLD_NAV = '''  <a href="#" data-ph-tab="stats">
    <span class="ph-nav-ico">&#128200;</span>
    <span class="ph-nav-lbl">Stats</span>
  </a>'''
    NEW_NAV = '''  <a href="#" data-ph-tab="stats">
    <span class="ph-nav-ico">&#128200;</span>
    <span class="ph-nav-lbl">Stats</span>
  </a>
  <a href="#" data-ph-tab="compta">
    <span class="ph-nav-ico">&#128176;</span>
    <span class="ph-nav-lbl">Compta</span>
  </a>'''
    if OLD_NAV in html:
        html = html.replace(OLD_NAV, NEW_NAV, 1)
        log("Onglet Compta ajoute", "OK")
    else:
        log("Ancre nav Stats introuvable", "WARN")
else:
    log("Onglet Compta deja present", "WARN")

# 2. Section Compta
if 'data-ph-page="compta"' not in html:
    COMPTA_SECTION = '''
<!-- SPRINT B+C : Comptabilite -->
<section data-ph-page="compta" class="ph-compta-page">
  <div class="ph-compta-inner">
    <div class="ph-compta-head">
      <div>
        <h1 class="ph-compta-title">Comptabilite</h1>
        <p class="ph-compta-sub">Bilan, depenses, journal de caisse</p>
      </div>
      <div style="display:flex;gap:8px">
        <input type="month" id="ph-compta-month" class="ph-compta-month" value="">
        <button type="button" id="ph-compta-export-btn" class="ph-compta-btn ph-compta-btn-ghost">&#128229; Export CSV</button>
      </div>
    </div>
    <div class="ph-compta-nav">
      <button type="button" class="ph-compta-tab active" data-compta-tab="direction">Vue Direction</button>
      <button type="button" class="ph-compta-tab" data-compta-tab="bilan">Bilan mensuel</button>
      <button type="button" class="ph-compta-tab" data-compta-tab="expenses">Depenses</button>
      <button type="button" class="ph-compta-tab" data-compta-tab="journal">Journal caisse</button>
    </div>
    <div class="ph-compta-panel active" data-compta-panel="direction">
      <div id="ph-compta-direction-content"></div>
    </div>
    <div class="ph-compta-panel" data-compta-panel="bilan">
      <div id="ph-compta-bilan-content"></div>
    </div>
    <div class="ph-compta-panel" data-compta-panel="expenses">
      <div id="ph-compta-expenses-content"></div>
    </div>
    <div class="ph-compta-panel" data-compta-panel="journal">
      <div id="ph-compta-journal-content"></div>
    </div>
  </div>
</section>
'''
    anchor = '<div id="driver-modal"'
    if anchor in html:
        html = html.replace(anchor, COMPTA_SECTION + "\n" + anchor, 1)
        log("Section Compta ajoutee", "OK")

# 3. Sections Fournisseurs + Commandes d'achat dans Admin
if 'id="ph-suppliers-content"' not in html:
    ADMIN_ADD = '''
  <section data-ph-page="admin" class="admin-section" id="suppliers-section">
    <h2 class="admin-title">&#128230; Fournisseurs</h2>
    <div id="ph-suppliers-content"></div>
  </section>

  <section data-ph-page="admin" class="admin-section" id="po-section">
    <h2 class="admin-title">&#128722; Commandes d'achat</h2>
    <div id="ph-po-content"></div>
  </section>
'''
    # Inserer avant </main> ou avant le modal
    anchor = '<div id="driver-modal"'
    if anchor in html:
        html = html.replace(anchor, ADMIN_ADD + "\n" + anchor, 1)
        log("Sections Admin ajoutees", "OK")

# 4. Sections Valorisation + Previsions dans Stock
if 'id="ph-stock-valuation"' not in html:
    STOCK_ADD = '''
    <div class="ph-stk-block" style="margin-top:16px">
      <h2 style="font-size:18px;font-weight:800;margin:24px 0 12px;color:var(--ph-ink)">Valorisation du stock</h2>
      <div id="ph-stock-valuation"></div>
    </div>

    <div class="ph-stk-block" style="margin-top:16px">
      <h2 style="font-size:18px;font-weight:800;margin:24px 0 12px;color:var(--ph-ink)">Previsions de reapprovisionnement</h2>
      <div id="ph-stock-forecast"></div>
    </div>
'''
    # Inserer dans la section stock, avant la fin
    # Chercher la section stock
    m = re.search(r'<section data-ph-page="stock"[\s\S]*?</section>', html)
    if m:
        # Inserer avant </section>
        block = m.group(0)
        new_block = block.replace("</section>", STOCK_ADD + "\n</section>", 1)
        html = html.replace(block, new_block, 1)
        log("Sections Stock ajoutees", "OK")
    else:
        log("Section stock introuvable", "WARN")

# 5. Reference CSS + JS
if "compta_fournisseurs.css" not in html:
    if "</head>" in html:
        html = html.replace("</head>",
            '<link rel="stylesheet" href="/static/compta_fournisseurs.css?v=' + TS + '">\n</head>', 1)
        log("CSS reference", "OK")

if "compta_fournisseurs.js" not in html:
    if "</body>" in html:
        html = html.replace("</body>",
            '<script defer src="/static/compta_fournisseurs.js?v=' + TS + '"></script>\n</body>', 1)
        log("JS reference", "OK")

# 6. Bump version
html = re.sub(r'(\?v=)\d+', r'\g<1>' + TS, html)

# 7. Modal Compta
if 'id="ph-compta-modal"' not in html:
    MODAL = '''
<div class="ph-compta-modal-backdrop" id="ph-compta-modal">
  <div class="ph-compta-modal"></div>
</div>
'''
    if "</body>" in html:
        html = html.replace("</body>", MODAL + "\n</body>", 1)
        log("Modal Compta ajoute", "OK")

open(HTML, "w", encoding="utf-8").write(html)
log("pharmacien.html sauvegarde", "OK")

# ============================================================
# VERIFICATION
# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)

final_html = open(HTML, "r", encoding="utf-8").read()
final_css = open(CSS, "r", encoding="utf-8").read()
final_js = open(JS, "r", encoding="utf-8").read()

checks = [
    ("CSS cree",                     os.path.isfile(CSS)),
    ("JS cree",                      os.path.isfile(JS)),
    ("Onglet Compta HTML",           'data-ph-tab="compta"' in final_html),
    ("Section Compta HTML",          'data-ph-page="compta"' in final_html),
    ("Section Fournisseurs HTML",    'id="ph-suppliers-content"' in final_html),
    ("Section Commandes achat HTML", 'id="ph-po-content"' in final_html),
    ("Section Valorisation Stock",   'id="ph-stock-valuation"' in final_html),
    ("Section Previsions Stock",     'id="ph-stock-forecast"' in final_html),
    ("Modal Compta",                 'id="ph-compta-modal"' in final_html),
    ("CSS reference",                "compta_fournisseurs.css" in final_html),
    ("JS reference",                 "compta_fournisseurs.js" in final_html),
    ("CSS valide",                   ".ph-compta-page" in final_css),
    ("JS valide",                    "phLoadCompta" in final_js),
    ("JS equilibre",                 brace_diff(final_js) == 0),
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
print("[TEST] Edge : F12 > Clear site data + Ctrl+Shift+R")
print("  1) Sidebar : nouvel onglet 'Compta' (entre Stats et Admin)")
print("  2) Compta -> onglets Direction / Bilan / Depenses / Journal")
print("  3) Compta -> Depenses : creer + supprimer")
print("  4) Compta -> Vue Direction : KPIs recettes + stock")
print("  5) Admin -> Fournisseurs + Commandes d'achat")
print("  6) Stock -> Valorisation + Previsions")
print()
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\pharmacien.html" "{HTML}"')
print(f'  del "{CSS}"')
print(f'  del "{JS}"')