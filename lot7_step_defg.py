# -*- coding: utf-8 -*-
"""
LOT 7 - ETAPES D+E+F+G : Interface catalogue + stock + design + tests
======================================================================
- Cree static/catalogue.css
- Cree static/catalogue.js
- Ajoute 2 onglets "Catalogue" et "Stock" dans pharmacien.html
- Atomic, rollback auto
"""
import os, re, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
HTML = os.path.join(ROOT, "static", "pharmacien.html")
CSS  = os.path.join(ROOT, "static", "catalogue.css")
JS   = os.path.join(ROOT, "static", "catalogue.js")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_lot7_stepDEFG_{TS}")
os.makedirs(BAK, exist_ok=True)

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]", "STEP": "\n###"}[k]
    print(p, m)

shutil.copy2(HTML, os.path.join(BAK, "pharmacien.html"))
print("=" * 78)
print(f"LOT 7 - ETAPES D+E+F+G - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

# ============================================================
# 1. CSS - catalogue.css
# ============================================================
CSS_CODE = """/* ============================================================
   Elonikab Health - Catalogue & Stock (Lot 7)
   ============================================================ */
body[data-active-page="catalogue"] [data-ph-page="catalogue"],
body[data-active-page="stock"]     [data-ph-page="stock"]{display:block !important}

.ph-cat-page, .ph-stk-page{
  min-height:calc(100vh - 66px); background:var(--ph-bg);
  padding:22px 18px 60px;
}
.ph-cat-inner, .ph-stk-inner{max-width:1240px; margin:0 auto}

.ph-cat-head, .ph-stk-head{
  display:flex; justify-content:space-between; align-items:flex-start;
  gap:12px; margin-bottom:18px; flex-wrap:wrap;
}
.ph-cat-title, .ph-stk-title{
  font-size:24px; font-weight:800; letter-spacing:-.02em;
  color:var(--ph-ink); margin:0 0 4px;
}
.ph-cat-sub, .ph-stk-sub{font-size:14px; color:var(--ph-muted); margin:0}

/* Toolbar */
.ph-cat-toolbar, .ph-stk-toolbar{
  display:flex; gap:10px; align-items:center; margin-bottom:14px;
  flex-wrap:wrap;
}
.ph-cat-search, .ph-stk-search{
  flex:1 1 260px; min-width:200px;
  display:flex; align-items:center; gap:8px;
  background:#fff; border:1.5px solid var(--ph-line);
  border-radius:11px; padding:0 12px;
}
.ph-cat-search:focus-within, .ph-stk-search:focus-within{
  border-color:var(--ph-blue);
  box-shadow:0 0 0 3px var(--ph-blue-soft);
}
.ph-cat-search input, .ph-stk-search input{
  flex:1; border:0; background:transparent; outline:none;
  padding:11px 0; font-size:14.5px; font-family:inherit;
}
.ph-cat-select, .ph-stk-select{
  padding:11px 14px; border:1.5px solid var(--ph-line);
  border-radius:11px; background:#fff; font-family:inherit;
  font-size:14px; color:var(--ph-ink); cursor:pointer;
}

/* Boutons */
.ph-btn{
  display:inline-flex; align-items:center; justify-content:center;
  gap:6px; padding:10px 16px; border-radius:10px;
  font-family:inherit; font-size:13.5px; font-weight:700;
  cursor:pointer; border:1px solid transparent; transition:.15s;
  white-space:nowrap;
}
.ph-btn-primary{background:var(--ph-blue); color:#fff; border-color:var(--ph-blue)}
.ph-btn-primary:hover{background:var(--ph-blue-dark)}
.ph-btn-primary:disabled{opacity:.5; cursor:not-allowed}
.ph-btn-ghost{background:#fff; color:var(--ph-ink); border-color:var(--ph-line)}
.ph-btn-ghost:hover{border-color:var(--ph-blue); color:var(--ph-blue)}
.ph-btn-danger{background:#fff; color:#B23C3C; border-color:var(--ph-line)}
.ph-btn-danger:hover{background:#FDECEC; border-color:#B23C3C}
.ph-btn-sm{padding:7px 12px; font-size:12.5px}

/* Tableau desktop */
.ph-cat-table-wrap{background:#fff; border:1px solid var(--ph-line); border-radius:14px; overflow:hidden}
.ph-cat-table{
  width:100%; border-collapse:collapse; font-size:13.5px;
}
.ph-cat-table th{
  background:#F5F8FC; text-align:left; padding:12px 14px;
  font-size:11.5px; text-transform:uppercase; letter-spacing:.05em;
  color:var(--ph-muted); font-weight:800;
  border-bottom:1px solid var(--ph-line);
}
.ph-cat-table td{
  padding:12px 14px; border-bottom:1px solid #F1F5F9;
  vertical-align:middle;
}
.ph-cat-table tr:last-child td{border-bottom:0}
.ph-cat-table tr:hover td{background:#FAFBFC}
.ph-cat-thumb{
  width:44px; height:44px; border-radius:9px; overflow:hidden;
  background:#F5F8FC; display:flex; align-items:center; justify-content:center;
  flex-shrink:0;
}
.ph-cat-thumb img{width:100%; height:100%; object-fit:contain}
.ph-cat-name{font-weight:700; color:var(--ph-ink)}
.ph-cat-pres{font-size:12px; color:var(--ph-muted); margin-top:2px}
.ph-cat-price{font-weight:800; color:var(--ph-blue-dark); white-space:nowrap}

/* Badges */
.ph-badge{
  display:inline-flex; align-items:center; gap:4px;
  padding:3px 10px; border-radius:999px;
  font-size:10.5px; font-weight:800; text-transform:uppercase;
  letter-spacing:.04em; white-space:nowrap;
}
.ph-badge-ok{background:#E6F7F1; color:#0A7A5A}
.ph-badge-warn{background:#FFF4E0; color:#B26B00}
.ph-badge-danger{background:#FDECEC; color:#B23C3C}
.ph-badge-info{background:#E8F0F8; color:#174A7E}
.ph-badge-muted{background:#E2E8F0; color:#475569}

/* Cartes mobile */
.ph-cat-cards{display:none}
.ph-cat-card{
  background:#fff; border:1px solid var(--ph-line);
  border-radius:14px; padding:14px; margin-bottom:10px;
  display:grid; grid-template-columns:64px 1fr; gap:12px;
}
.ph-cat-card-thumb{
  width:64px; height:64px; border-radius:11px; overflow:hidden;
  background:#F5F8FC; display:flex; align-items:center; justify-content:center;
}
.ph-cat-card-thumb img{width:100%; height:100%; object-fit:contain}
.ph-cat-card-body{min-width:0}

/* Alertes stock */
.ph-stk-alerts{
  display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:12px; margin-bottom:18px;
}
.ph-stk-alert{
  background:#fff; border:1px solid var(--ph-line);
  border-left:4px solid var(--ph-blue);
  border-radius:12px; padding:14px 16px;
}
.ph-stk-alert.warn{border-left-color:#B26B00}
.ph-stk-alert.danger{border-left-color:#B23C3C}
.ph-stk-alert.ico{font-size:20px; margin-bottom:6px; display:block}
.ph-stk-alert strong{font-size:22px; font-weight:800; color:var(--ph-ink); display:block; line-height:1.1}
.ph-stk-alert span{font-size:11.5px; font-weight:700; color:var(--ph-muted); text-transform:uppercase; letter-spacing:.05em}

/* Modale */
.ph-modal-backdrop{
  position:fixed; inset:0; z-index:10000;
  background:rgba(15,23,42,.5);
  display:none; align-items:center; justify-content:center;
  padding:16px;
}
.ph-modal-backdrop.show{display:flex}
.ph-modal{
  background:#fff; border-radius:16px;
  max-width:560px; width:100%; max-height:90vh;
  display:flex; flex-direction:column;
  box-shadow:0 24px 60px rgba(15,23,42,.3);
  overflow:hidden;
}
.ph-modal-head{
  padding:16px 20px; border-bottom:1px solid var(--ph-line);
  display:flex; align-items:center; justify-content:space-between; gap:12px;
}
.ph-modal-head h3{margin:0; font-size:17px; font-weight:800}
.ph-modal-close{
  width:32px; height:32px; border-radius:8px;
  border:1px solid var(--ph-line); background:#fff;
  cursor:pointer; font-size:18px; color:var(--ph-muted);
  display:flex; align-items:center; justify-content:center;
}
.ph-modal-body{
  padding:18px 20px; overflow-y:auto; flex:1;
}
.ph-modal-foot{
  padding:14px 20px; border-top:1px solid var(--ph-line);
  display:flex; justify-content:flex-end; gap:8px;
}
.ph-form-row{margin-bottom:14px}
.ph-form-row label{
  display:block; font-size:12.5px; font-weight:700;
  color:var(--ph-ink); margin-bottom:5px;
}
.ph-form-row input, .ph-form-row select, .ph-form-row textarea{
  width:100%; box-sizing:border-box;
  border:1.5px solid var(--ph-line); border-radius:10px;
  padding:10px 12px; font-size:14px; font-family:inherit;
  outline:none; transition:.15s;
}
.ph-form-row input:focus, .ph-form-row select:focus, .ph-form-row textarea:focus{
  border-color:var(--ph-blue); box-shadow:0 0 0 3px var(--ph-blue-soft);
}
.ph-form-2col{display:grid; grid-template-columns:1fr 1fr; gap:12px}

.ph-image-preview{
  width:100%; max-width:180px; height:140px; border-radius:10px;
  border:1.5px dashed var(--ph-line); background:#F5F8FC;
  display:flex; align-items:center; justify-content:center;
  overflow:hidden; margin-top:6px; cursor:pointer;
}
.ph-image-preview img{width:100%; height:100%; object-fit:contain}

.ph-toast{
  position:fixed; bottom:90px; left:50%; transform:translateX(-50%);
  background:var(--ph-ink); color:#fff; padding:12px 20px;
  border-radius:11px; font-size:13.5px; font-weight:700;
  box-shadow:0 10px 30px rgba(15,23,42,.25);
  z-index:99999; max-width:90vw; text-align:center;
}
.ph-toast.ok{background:#0A7A5A}
.ph-toast.err{background:#B23C3C}

/* Responsive */
@media (max-width:800px){
  .ph-cat-page, .ph-stk-page{padding:16px 12px 40px}
  .ph-cat-title, .ph-stk-title{font-size:20px}
  .ph-cat-table-wrap{display:none}
  .ph-cat-cards{display:block}
  .ph-form-2col{grid-template-columns:1fr}
}
"""

open(CSS, "w", encoding="utf-8").write(CSS_CODE)
log("catalogue.css cree", "OK")

# ============================================================
# 2. JS - catalogue.js
# ============================================================
JS_CODE = r"""/* ============================================================
   Elonikab Health - Catalogue & Stock (Lot 7)
   ============================================================ */
(function () {
  "use strict";
  var API = "/api";
  var catState = { products: [], q: "", cat: "", status: "" };
  var stkState = { products: [], q: "", alerts: null, filter: "" };
  var editingProductId = null;

  function $(id) { return document.getElementById(id); }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function fmtPrice(v) {
    var n = Math.round(Number(v) || 0);
    try { return n.toLocaleString("fr-FR") + " FCFA"; }
    catch (e) { return n + " FCFA"; }
  }

  function toast(msg, kind) {
    var t = document.createElement("div");
    t.className = "ph-toast " + (kind || "");
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 3000);
  }

  function apiCall(method, path, body) {
    var opts = {
      method: method,
      credentials: "same-origin",
      headers: {}
    };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(API + path, opts).then(function (r) {
      return r.text().then(function (txt) {
        var d = null;
        try { d = txt ? JSON.parse(txt) : null; } catch (e) {}
        if (!r.ok) {
          var msg = (d && d.detail) || ("Erreur " + r.status);
          throw new Error(msg);
        }
        return d;
      });
    });
  }

  // ============================================================
  // CATALOGUE
  // ============================================================
  function loadCatalog() {
    var box = $("ph-cat-content");
    if (box) box.innerHTML = '<div class="ph-cat-card">Chargement...</div>';
    apiCall("GET", "/products").then(function (list) {
      catState.products = list || [];
      renderCatalog();
    }).catch(function (e) { toast(e.message, "err"); });
  }

  function renderCatalog() {
    var list = catState.products.slice();
    var q = (catState.q || "").toLowerCase();
    if (q) list = list.filter(function (p) {
      return (p.name || "").toLowerCase().indexOf(q) >= 0 ||
             (p.category || "").toLowerCase().indexOf(q) >= 0;
    });
    if (catState.cat) list = list.filter(function (p) { return p.category === catState.cat; });
    if (catState.status === "active")   list = list.filter(function (p) { return p.is_active == 1; });
    if (catState.status === "inactive") list = list.filter(function (p) { return p.is_active == 0; });
    if (catState.status === "rupture")  list = list.filter(function (p) { return (p.stock_quantity||0) <= 0; });
    if (catState.status === "low")      list = list.filter(function (p) {
      var q2 = p.stock_quantity, m = p.stock_min_threshold || 5;
      return q2 != null && q2 > 0 && q2 <= m;
    });

    // Populate categories
    var cats = {};
    catState.products.forEach(function (p) { if (p.category) cats[p.category] = 1; });
    var sel = $("ph-cat-cat");
    if (sel) {
      var current = sel.value;
      sel.innerHTML = '<option value="">Toutes catégories</option>';
      Object.keys(cats).sort().forEach(function (c) {
        sel.innerHTML += '<option value="' + esc(c) + '"' + (c===current?" selected":"") + '>' + esc(c) + '</option>';
      });
    }

    // Count
    var cnt = $("ph-cat-count");
    if (cnt) cnt.textContent = list.length + " produit(s)";

    // Desktop table
    var tbody = $("ph-cat-tbody");
    if (tbody) {
      if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:30px;color:#64748B">Aucun produit</td></tr>';
      } else {
        tbody.innerHTML = list.map(function (p) {
          var statusBadge = "";
          if (p.is_active == 0) statusBadge = '<span class="ph-badge ph-badge-muted">Archivé</span>';
          else if ((p.stock_quantity||0) <= 0) statusBadge = '<span class="ph-badge ph-badge-danger">Rupture</span>';
          else if (p.stock_quantity != null && p.stock_quantity <= (p.stock_min_threshold||5))
            statusBadge = '<span class="ph-badge ph-badge-warn">Stock faible</span>';
          else if (p.stock_quantity == null) statusBadge = '<span class="ph-badge ph-badge-muted">Stock N/R</span>';
          else statusBadge = '<span class="ph-badge ph-badge-ok">Actif</span>';
          return (
            '<tr data-id="' + p.id + '">' +
            '<td><div class="ph-cat-thumb">' + (p.image_url ? '<img src="' + esc(p.image_url) + '" onerror="this.style.display=\'none\'">' : '📦') + '</div></td>' +
            '<td><div class="ph-cat-name">' + esc(p.name) + '</div><div class="ph-cat-pres">' + esc(p.presentation || "") + '</div></td>' +
            '<td>' + esc(p.category || "—") + '</td>' +
            '<td class="ph-cat-price">' + fmtPrice(p.price) + '</td>' +
            '<td>' + (p.stock_quantity == null ? "—" : p.stock_quantity) + ' ' + statusBadge + '</td>' +
            '<td style="text-align:right;white-space:nowrap">' +
              '<button class="ph-btn ph-btn-ghost ph-btn-sm" data-act="edit" data-id="' + p.id + '">Modifier</button> ' +
              '<button class="ph-btn ph-btn-danger ph-btn-sm" data-act="archive" data-id="' + p.id + '">Archiver</button>' +
            '</td>' +
            '</tr>'
          );
        }).join("");
      }
    }

    // Mobile cards
    var cards = $("ph-cat-cards");
    if (cards) {
      if (list.length === 0) {
        cards.innerHTML = '<div style="text-align:center;padding:30px;color:#64748B">Aucun produit</div>';
      } else {
        cards.innerHTML = list.map(function (p) {
          return (
            '<div class="ph-cat-card" data-id="' + p.id + '">' +
            '<div class="ph-cat-card-thumb">' + (p.image_url ? '<img src="' + esc(p.image_url) + '" onerror="this.style.display=\'none\'">' : '📦') + '</div>' +
            '<div class="ph-cat-card-body">' +
              '<div class="ph-cat-name">' + esc(p.name) + '</div>' +
              '<div class="ph-cat-pres">' + esc(p.presentation || "") + '</div>' +
              '<div style="margin:6px 0;font-weight:800;color:#174A7E">' + fmtPrice(p.price) + '</div>' +
              '<div style="margin-bottom:8px">' + ((p.stock_quantity==null?"Stock N/R":p.stock_quantity+" en stock")) + '</div>' +
              '<button class="ph-btn ph-btn-ghost ph-btn-sm" data-act="edit" data-id="' + p.id + '">Modifier</button> ' +
              '<button class="ph-btn ph-btn-danger ph-btn-sm" data-act="archive" data-id="' + p.id + '">Archiver</button>' +
            '</div></div>'
          );
        }).join("");
      }
    }
  }

  // ============================================================
  // MODALE PRODUIT
  // ============================================================
  function openProductModal(product) {
    editingProductId = product ? product.id : null;
    var html = (
      '<div class="ph-modal-head">' +
        '<h3>' + (product ? "Modifier le produit" : "Nouveau produit") + '</h3>' +
        '<button type="button" class="ph-modal-close" data-close>×</button>' +
      '</div>' +
      '<div class="ph-modal-body">' +
        '<div class="ph-form-row"><label>Nom *</label><input id="f-name" type="text" value="' + esc(product ? product.name : "") + '"></div>' +
        '<div class="ph-form-2col">' +
          '<div class="ph-form-row"><label>Présentation</label><input id="f-pres" type="text" value="' + esc(product ? product.presentation : "") + '"></div>' +
          '<div class="ph-form-row"><label>Catégorie</label><input id="f-cat" type="text" value="' + esc(product ? product.category : "") + '"></div>' +
        '</div>' +
        '<div class="ph-form-2col">' +
          '<div class="ph-form-row"><label>Prix (FCFA) *</label><input id="f-price" type="number" min="0" step="50" value="' + (product ? product.price : 0) + '"></div>' +
          '<div class="ph-form-row"><label>Ordonnance</label><select id="f-presc"><option value="0"' + (!product||!product.requires_prescription?' selected':'') + '>Non</option><option value="1"' + (product&&product.requires_prescription?' selected':'') + '>Oui</option></select></div>' +
        '</div>' +
        '<div class="ph-form-2col">' +
          '<div class="ph-form-row"><label>Stock initial</label><input id="f-stock" type="number" min="0" value="' + (product && product.stock_quantity != null ? product.stock_quantity : "") + '" placeholder="Optionnel"></div>' +
          '<div class="ph-form-row"><label>Seuil alerte</label><input id="f-min" type="number" min="0" value="' + (product ? (product.stock_min_threshold||5) : 5) + '"></div>' +
        '</div>' +
        '<div class="ph-form-row"><label>Description</label><textarea id="f-desc" rows="3">' + esc(product ? product.description : "") + '</textarea></div>' +
        (product ? (
          '<div class="ph-form-row"><label>Image principale</label>' +
          '<div class="ph-image-preview" id="f-img-prev">' +
            (product.image_url ? '<img src="' + esc(product.image_url) + '">' : '📷') +
          '</div>' +
          '<input type="file" id="f-img-input" accept="image/jpeg,image/png,image/webp" style="margin-top:6px;font-size:12px">' +
          '</div>'
        ) : '') +
      '</div>' +
      '<div class="ph-modal-foot">' +
        '<button type="button" class="ph-btn ph-btn-ghost" data-close>Annuler</button>' +
        '<button type="button" class="ph-btn ph-btn-primary" id="f-save">' + (product ? "Enregistrer" : "Créer") + '</button>' +
      '</div>'
    );
    showModal(html);
    var btn = $("f-save");
    if (btn) btn.addEventListener("click", saveProduct);
    var imgInput = $("f-img-input");
    if (imgInput) imgInput.addEventListener("change", onImagePick);
  }

  function onImagePick(ev) {
    var file = ev.target.files && ev.target.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { toast("Image trop lourde (max 5 Mo)", "err"); return; }
    var reader = new FileReader();
    reader.onload = function (e) {
      var prev = $("f-img-prev");
      if (prev) prev.innerHTML = '<img src="' + e.target.result + '">';
    };
    reader.readAsDataURL(file);
  }

  function saveProduct() {
    var payload = {
      name: ($("f-name").value || "").trim(),
      presentation: ($("f-pres").value || "").trim(),
      category: ($("f-cat").value || "").trim() || "Divers",
      price: parseFloat($("f-price").value),
      description: ($("f-desc").value || "").trim(),
      requires_prescription: parseInt($("f-presc").value, 10) || 0,
      stock_min_threshold: parseInt($("f-min").value, 10) || 5
    };
    var stockRaw = $("f-stock").value;
    if (stockRaw !== "" && stockRaw !== null) {
      payload.stock_quantity = parseInt(stockRaw, 10);
    }
    if (!payload.name || payload.name.length < 2) { toast("Nom obligatoire", "err"); return; }
    if (isNaN(payload.price) || payload.price < 0) { toast("Prix invalide", "err"); return; }

    var btn = $("f-save");
    if (btn) { btn.disabled = true; btn.textContent = "..."; }

    var isNew = !editingProductId;
    var call = isNew
      ? apiCall("POST", "/api/admin/products", payload)
      : apiCall("PATCH", "/api/admin/products/" + editingProductId, payload);

    call.then(function (saved) {
      var pid = isNew ? saved.id : editingProductId;
      var imgInput = $("f-img-input");
      var file = imgInput && imgInput.files && imgInput.files[0];
      if (file && pid) {
        return uploadImage(pid, file).then(function () { return saved; });
      }
      return saved;
    }).then(function () {
      closeModal();
      toast(isNew ? "Produit créé" : "Produit modifié", "ok");
      loadCatalog();
    }).catch(function (e) {
      toast(e.message, "err");
      if (btn) { btn.disabled = false; btn.textContent = isNew ? "Créer" : "Enregistrer"; }
    });
  }

  function uploadImage(pid, file) {
    var form = new FormData();
    form.append("file", file);
    return fetch(API + "/api/admin/products/" + pid + "/images", {
      method: "POST", credentials: "same-origin", body: form
    }).then(function (r) {
      return r.text().then(function (t) {
        var d = null; try { d = t ? JSON.parse(t) : null; } catch (e) {}
        if (!r.ok) throw new Error((d && d.detail) || "Erreur upload");
        return d;
      });
    });
  }

  function archiveProduct(id) {
    if (!confirm("Archiver ce produit ?\n\nIl ne sera plus visible côté patient, mais les commandes existantes sont préservées.")) return;
    apiCall("DELETE", "/api/admin/products/" + id)
      .then(function () { toast("Produit archivé", "ok"); loadCatalog(); })
      .catch(function (e) { toast(e.message, "err"); });
  }

  // ============================================================
  // MODALE
  // ============================================================
  function showModal(html) {
    var back = $("ph-cat-modal");
    if (!back) return;
    back.querySelector(".ph-modal").innerHTML = html;
    back.classList.add("show");
    back.querySelectorAll("[data-close]").forEach(function (b) {
      b.addEventListener("click", closeModal);
    });
    back.addEventListener("click", function (e) {
      if (e.target === back) closeModal();
    });
  }

  function closeModal() {
    var back = $("ph-cat-modal");
    if (back) back.classList.remove("show");
    editingProductId = null;
  }

  // ============================================================
  // STOCK
  // ============================================================
  function loadStock() {
    var box = $("ph-stk-content");
    if (box) box.innerHTML = '<div style="text-align:center;padding:30px;color:#64748B">Chargement...</div>';
    Promise.all([
      apiCall("GET", "/api/admin/stock"),
      apiCall("GET", "/api/admin/stock/alerts"),
      apiCall("GET", "/api/admin/stock/movements?limit=50")
    ]).then(function (res) {
      stkState.products = res[0] || [];
      stkState.alerts = res[1] || {};
      stkState.movements = res[2] || [];
      renderStock();
    }).catch(function (e) {
      var box = $("ph-stk-content");
      if (box) box.innerHTML = '<div style="padding:30px;color:#B23C3C">Erreur : ' + esc(e.message) + '</div>';
      toast(e.message, "err");
    });
  }

  function renderStock() {
    var a = stkState.alerts || {};
    var rupt = (a.rupture || []).length;
    var low = (a.low_stock || []).length;
    var soon = (a.expiring_soon || []).length;

    var alertsBox = $("ph-stk-alerts");
    if (alertsBox) {
      alertsBox.innerHTML =
        '<div class="ph-stk-alert danger"><span class="ico">🚨</span><strong>' + rupt + '</strong><span>Ruptures</span></div>' +
        '<div class="ph-stk-alert warn"><span class="ico">⚠️</span><strong>' + low + '</strong><span>Stock faible</span></div>' +
        '<div class="ph-stk-alert"><span class="ico">📅</span><strong>' + soon + '</strong><span>Péremption ≤30j</span></div>' +
        '<div class="ph-stk-alert"><span class="ico">📦</span><strong>' + (stkState.products||[]).length + '</strong><span>Produits actifs</span></div>';
    }

    var q = (stkState.q || "").toLowerCase();
    var list = (stkState.products || []).slice();
    if (q) list = list.filter(function (p) { return (p.name||"").toLowerCase().indexOf(q) >= 0; });

    var tbody = $("ph-stk-tbody");
    if (tbody) {
      if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:30px;color:#64748B">Aucun produit</td></tr>';
      } else {
        tbody.innerHTML = list.map(function (p) {
          var badge = "";
          if (p.stock_quantity == null) badge = '<span class="ph-badge ph-badge-muted">N/R</span>';
          else if (p.stock_quantity <= 0) badge = '<span class="ph-badge ph-badge-danger">Rupture</span>';
          else if (p.stock_quantity <= (p.stock_min_threshold||5)) badge = '<span class="ph-badge ph-badge-warn">Faible</span>';
          else badge = '<span class="ph-badge ph-badge-ok">OK</span>';
          return (
            '<tr>' +
            '<td><div class="ph-cat-name">' + esc(p.name) + '</div><div class="ph-cat-pres">' + esc(p.category||"") + '</div></td>' +
            '<td><strong>' + (p.stock_quantity == null ? "—" : p.stock_quantity) + '</strong></td>' +
            '<td>' + (p.stock_min_threshold||5) + '</td>' +
            '<td>' + badge + '</td>' +
            '<td style="text-align:right"><button class="ph-btn ph-btn-primary ph-btn-sm" data-act="move" data-id="' + p.id + '" data-name="' + esc(p.name) + '">Mouvement</button></td>' +
            '</tr>'
          );
        }).join("");
      }
    }

    var movBox = $("ph-stk-movements");
    if (movBox) {
      var mv = stkState.movements || [];
      if (mv.length === 0) {
        movBox.innerHTML = '<div style="text-align:center;padding:24px;color:#64748B">Aucun mouvement</div>';
      } else {
        movBox.innerHTML = '<table class="ph-cat-table"><thead><tr><th>Date</th><th>Produit</th><th>Type</th><th>Qté</th><th>Motif</th></tr></thead><tbody>' +
          mv.slice(0, 20).map(function (m) {
            var sign = m.quantity > 0 ? "+" : "";
            return '<tr><td style="font-size:12px">' + esc((m.created_at||"").slice(0,16)) + '</td>' +
              '<td>' + esc(m.product_name || "—") + '</td>' +
              '<td><span class="ph-badge ph-badge-info">' + esc(m.type) + '</span></td>' +
              '<td><strong style="color:' + (m.quantity>0?"#0A7A5A":"#B23C3C") + '">' + sign + m.quantity + '</strong></td>' +
              '<td style="font-size:12px">' + esc(m.reason || "—") + '</td></tr>';
          }).join("") + '</tbody></table>';
      }
    }
  }

  // Modale mouvement
  function openMovementModal(productId, productName) {
    var html =
      '<div class="ph-modal-head"><h3>Mouvement de stock</h3>' +
      '<button type="button" class="ph-modal-close" data-close>×</button></div>' +
      '<div class="ph-modal-body">' +
        '<div style="font-size:13.5px;color:#64748B;margin-bottom:12px">Produit : <strong>' + esc(productName) + '</strong></div>' +
        '<div class="ph-form-row"><label>Type *</label><select id="m-type">' +
          '<option value="IN">Entrée (+)</option>' +
          '<option value="OUT">Sortie (-)</option>' +
          '<option value="ADJUST">Ajustement (±)</option>' +
        '</select></div>' +
        '<div class="ph-form-row"><label>Quantité *</label><input id="m-qty" type="number" step="1" value="1"></div>' +
        '<div class="ph-form-row"><label>Motif</label><input id="m-reason" type="text" placeholder="Obligatoire pour ajustement"></div>' +
        '<div class="ph-form-row"><label>Référence</label><input id="m-ref" type="text" placeholder="Optionnel (ex: CMD-xxx, LOT-xxx)"></div>' +
      '</div>' +
      '<div class="ph-modal-foot">' +
        '<button type="button" class="ph-btn ph-btn-ghost" data-close>Annuler</button>' +
        '<button type="button" class="ph-btn ph-btn-primary" id="m-save">Enregistrer</button>' +
      '</div>';
    showModal(html);
    var btn = $("m-save");
    if (btn) btn.addEventListener("click", function () { saveMovement(productId); });
  }

  function saveMovement(productId) {
    var payload = {
      product_id: productId,
      type: $("m-type").value,
      quantity: parseInt($("m-qty").value, 10),
      reason: ($("m-reason").value || "").trim(),
      reference: ($("m-ref").value || "").trim()
    };
    if (!payload.quantity || isNaN(payload.quantity)) { toast("Quantité invalide", "err"); return; }
    var btn = $("m-save");
    if (btn) { btn.disabled = true; btn.textContent = "..."; }
    apiCall("POST", "/api/admin/stock/movements", payload)
      .then(function (r) {
        closeModal();
        toast("Stock mis à jour : " + r.new_quantity, "ok");
        loadStock();
      })
      .catch(function (e) {
        toast(e.message, "err");
        if (btn) { btn.disabled = false; btn.textContent = "Enregistrer"; }
      });
  }

  // ============================================================
  // EVENTS
  // ============================================================
  document.addEventListener("click", function (ev) {
    var t = ev.target;
    // Nouveau produit
    if (t.id === "ph-cat-add") { openProductModal(null); return; }
    // Actions tableau/cartes
    var btn = t.closest ? t.closest("[data-act]") : null;
    if (btn) {
      var act = btn.getAttribute("data-act");
      var id = parseInt(btn.getAttribute("data-id"), 10);
      if (act === "edit") {
        var p = catState.products.find(function (x) { return x.id === id; });
        if (p) openProductModal(p);
      } else if (act === "archive") {
        archiveProduct(id);
      } else if (act === "move") {
        openMovementModal(id, btn.getAttribute("data-name"));
      }
      return;
    }
    // Onglets
    var tab = t.closest ? t.closest("[data-ph-tab]") : null;
    if (tab) {
      var name = tab.getAttribute("data-ph-tab");
      if (name === "catalogue") setTimeout(loadCatalog, 100);
      if (name === "stock") setTimeout(loadStock, 100);
    }
  });

  // Recherche + filtres catalogue
  document.addEventListener("input", function (ev) {
    if (ev.target.id === "ph-cat-search") {
      clearTimeout(ev.target._t);
      ev.target._t = setTimeout(function () {
        catState.q = ev.target.value;
        renderCatalog();
      }, 200);
    }
    if (ev.target.id === "ph-stk-search") {
      clearTimeout(ev.target._t);
      ev.target._t = setTimeout(function () {
        stkState.q = ev.target.value;
        renderStock();
      }, 200);
    }
  });
  document.addEventListener("change", function (ev) {
    if (ev.target.id === "ph-cat-cat")   { catState.cat = ev.target.value; renderCatalog(); }
    if (ev.target.id === "ph-cat-status"){ catState.status = ev.target.value; renderCatalog(); }
  });

  // Init on load if already on page
  document.addEventListener("DOMContentLoaded", function () {
    setTimeout(function () {
      var page = document.body.getAttribute("data-active-page");
      if (page === "catalogue") loadCatalog();
      if (page === "stock") loadStock();
    }, 400);
  });

  window.phLoadCatalog = loadCatalog;
  window.phLoadStock = loadStock;
})();
"""

open(JS, "w", encoding="utf-8").write(JS_CODE)
log("catalogue.js cree", "OK")

# ============================================================
# 3. HTML - injection des onglets + sections
# ============================================================
html = open(HTML, "r", encoding="utf-8").read()

# 3a. Onglets nav
if 'data-ph-tab="catalogue"' in html:
    log("Onglets deja presents", "WARN")
else:
    OLD_NAV = '''  <a href="#" data-ph-tab="stats">
    <span class="ph-nav-ico">&#128200;</span>
    <span class="ph-nav-lbl">Stats</span>
  </a>'''
    NEW_NAV = '''  <a href="#" data-ph-tab="catalogue">
    <span class="ph-nav-ico">&#128230;</span>
    <span class="ph-nav-lbl">Catalogue</span>
  </a>
  <a href="#" data-ph-tab="stock">
    <span class="ph-nav-ico">&#128202;</span>
    <span class="ph-nav-lbl">Stock</span>
  </a>
  <a href="#" data-ph-tab="stats">
    <span class="ph-nav-ico">&#128200;</span>
    <span class="ph-nav-lbl">Stats</span>
  </a>'''
    if OLD_NAV in html:
        html = html.replace(OLD_NAV, NEW_NAV, 1)
        log("Onglets Catalogue + Stock ajoutes", "OK")
    else:
        log("Ancre nav introuvable", "ERR")

# 3b. Sections HTML
if 'data-ph-page="catalogue"' in html:
    log("Sections deja presentes", "WARN")
else:
    SECTIONS = '''
<!-- LOT 7 - CATALOGUE -->
<section data-ph-page="catalogue" class="ph-cat-page">
  <div class="ph-cat-inner">
    <div class="ph-cat-head">
      <div>
        <h1 class="ph-cat-title">Catalogue</h1>
        <p class="ph-cat-sub" id="ph-cat-count">Chargement...</p>
      </div>
      <button type="button" class="ph-btn ph-btn-primary" id="ph-cat-add">+ Ajouter un produit</button>
    </div>
    <div class="ph-cat-toolbar">
      <div class="ph-cat-search">
        <span>&#128269;</span>
        <input type="search" id="ph-cat-search" placeholder="Rechercher un produit..." autocomplete="off">
      </div>
      <select class="ph-cat-select" id="ph-cat-cat"><option value="">Toutes catégories</option></select>
      <select class="ph-cat-select" id="ph-cat-status">
        <option value="">Tous statuts</option>
        <option value="active">Actifs</option>
        <option value="inactive">Archivés</option>
        <option value="rupture">Rupture</option>
        <option value="low">Stock faible</option>
      </select>
    </div>
    <div class="ph-cat-table-wrap">
      <table class="ph-cat-table">
        <thead><tr><th></th><th>Produit</th><th>Catégorie</th><th>Prix</th><th>Stock</th><th></th></tr></thead>
        <tbody id="ph-cat-tbody"><tr><td colspan="6" style="text-align:center;padding:30px">Chargement...</td></tr></tbody>
      </table>
    </div>
    <div class="ph-cat-cards" id="ph-cat-cards"></div>
  </div>
</section>

<!-- LOT 7 - STOCK -->
<section data-ph-page="stock" class="ph-stk-page">
  <div class="ph-stk-inner">
    <div class="ph-stk-head">
      <div>
        <h1 class="ph-stk-title">Gestion du stock</h1>
        <p class="ph-stk-sub">Vue d'ensemble, alertes et mouvements</p>
      </div>
    </div>
    <div class="ph-stk-alerts" id="ph-stk-alerts"></div>
    <div class="ph-stk-toolbar">
      <div class="ph-stk-search">
        <span>&#128269;</span>
        <input type="search" id="ph-stk-search" placeholder="Rechercher un produit..." autocomplete="off">
      </div>
    </div>
    <div class="ph-cat-table-wrap" style="margin-bottom:20px">
      <table class="ph-cat-table">
        <thead><tr><th>Produit</th><th>Stock</th><th>Seuil</th><th>État</th><th></th></tr></thead>
        <tbody id="ph-stk-tbody"><tr><td colspan="5" style="text-align:center;padding:30px">Chargement...</td></tr></tbody>
      </table>
    </div>
    <div class="ph-stk-head" style="margin-top:30px"><h2 class="ph-stk-title" style="font-size:18px">Derniers mouvements</h2></div>
    <div class="ph-cat-table-wrap" id="ph-stk-movements"></div>
  </div>
</section>

<!-- MODALE COMMUNE -->
<div class="ph-modal-backdrop" id="ph-cat-modal">
  <div class="ph-modal"></div>
</div>
'''
    if '<div id="driver-modal"' in html:
        html = html.replace('<div id="driver-modal"', SECTIONS + '\n<div id="driver-modal"', 1)
        log("Sections catalogue + stock ajoutees", "OK")
    else:
        log("Ancre sections introuvable", "ERR")

# 3c. CSS link
if "catalogue.css" not in html:
    if "</head>" in html:
        html = html.replace("</head>",
            '<link rel="stylesheet" href="/static/catalogue.css?v=' + TS + '">\n</head>', 1)
        log("CSS catalogue reference", "OK")

# 3d. JS script
if "catalogue.js" not in html:
    if "</body>" in html:
        html = html.replace("</body>",
            '<script defer src="/static/catalogue.js?v=' + TS + '"></script>\n</body>', 1)
        log("JS catalogue reference", "OK")

# Bump versions existantes
html = re.sub(r'(\?v=)\d+', r'\g<1>' + TS, html)

open(HTML, "w", encoding="utf-8").write(html)
log("pharmacien.html sauvegarde", "OK")

# ============================================================
# Verifications
# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)

final_html = open(HTML, "r", encoding="utf-8").read()
final_css  = open(CSS, "r", encoding="utf-8").read()
final_js   = open(JS, "r", encoding="utf-8").read()

checks = [
    ("CSS cree",                 os.path.isfile(CSS)),
    ("JS cree",                  os.path.isfile(JS)),
    ("Onglet Catalogue",         'data-ph-tab="catalogue"' in final_html),
    ("Onglet Stock",             'data-ph-tab="stock"' in final_html),
    ("Section catalogue",        'data-ph-page="catalogue"' in final_html),
    ("Section stock",            'data-ph-page="stock"' in final_html),
    ("Modale presente",          'ph-cat-modal' in final_html),
    ("CSS reference",            "catalogue.css" in final_html),
    ("JS reference",             "catalogue.js" in final_html),
    ("CSS contient styles cat",  ".ph-cat-page" in final_css),
    ("CSS responsive",           "@media (max-width:800px)" in final_css),
    ("JS loadCatalog",           "function loadCatalog" in final_js),
    ("JS loadStock",             "function loadStock" in final_js),
    ("JS uploadImage",           "function uploadImage" in final_js),
    ("JS modale mouvement",      "openMovementModal" in final_js),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

passed = sum(1 for _, ok in checks if ok)
print(f"\n  RESULTAT : {passed}/{len(checks)}")

print()
print(f"[BACKUP] {BAK}")
print()
print("[CMD] Pas de restart Uvicorn (front uniquement).")
print()
print("[TEST] Edge : F12 > Application > Clear site data + Ctrl+Shift+R")
print("  1) /pharmacien -> sidebar : nouveaux onglets 'Catalogue' et 'Stock'")
print("  2) Catalogue : tableau + bouton 'Ajouter' + filtres")
print("  3) Cliquer 'Ajouter' -> modale -> creer un produit")
print("  4) Stock : alertes + produits + bouton 'Mouvement'")
print()
print("[ROLLBACK] :")
print(f'  copy "{BAK}\\pharmacien.html" "{HTML}"')
print(f'  del "{CSS}"')
print(f'  del "{JS}"')