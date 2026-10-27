"""
v3_install_ui_final.py
Finition UI + bouton Assigner livreur + ecran notifications.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_v3_ui_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. HEADER.CSS
# ============================================================
HEADER_CSS = '''
/* ============================================================
   Elokinab Health - Header unifie
   ============================================================ */
.eh-user-actions{
  display:flex;align-items:center;gap:10px;margin-left:auto;
}
.eh-icon-btn{
  position:relative;display:inline-flex;align-items:center;justify-content:center;
  width:38px;height:38px;border-radius:10px;background:var(--bg,#f4faf7);
  border:1px solid var(--line,#ddece6);font-size:17px;text-decoration:none;
  color:#0f2620;transition:.15s;
}
.eh-icon-btn:hover{background:#e8f7f1;border-color:#0f9d76}
.eh-badge{
  position:absolute;top:-4px;right:-4px;
  min-width:18px;height:18px;padding:0 5px;
  background:#0f9d76;color:#fff;border-radius:999px;
  font-size:10px;font-weight:800;line-height:18px;text-align:center;
  box-shadow:0 2px 5px rgba(15,157,118,.4);
}
.eh-badge.hidden{display:none}
.eh-user-menu{position:relative}
.eh-user-trigger{
  padding:8px 14px;border:1px solid var(--line,#ddece6);border-radius:10px;
  background:#fff;font-family:inherit;font-size:13px;font-weight:700;
  color:#0f2620;cursor:pointer;max-width:160px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.eh-user-trigger:hover{border-color:#0f9d76;color:#0a7a5a}
.eh-dropdown{
  position:absolute;top:calc(100% + 6px);right:0;
  background:#fff;border:1px solid var(--line,#ddece6);border-radius:12px;
  box-shadow:0 8px 28px rgba(15,38,32,.12);min-width:200px;
  padding:8px;z-index:100;
}
.eh-dropdown.hidden{display:none}
.eh-drop-user{
  padding:10px 12px;font-size:13px;font-weight:700;
  border-bottom:1px solid var(--line,#ddece6);margin-bottom:6px;
}
.eh-drop-user small{
  font-size:11px;color:#6c8a80;font-weight:600;
  text-transform:uppercase;letter-spacing:.05em;
}
.eh-dropdown a,.eh-dropdown button{
  display:block;width:100%;text-align:left;
  padding:9px 12px;border:0;border-radius:8px;
  background:transparent;color:#0f2620;text-decoration:none;
  font-size:13px;font-weight:600;font-family:inherit;cursor:pointer;
}
.eh-dropdown a:hover,.eh-dropdown button:hover{background:#e8f7f1;color:#0a7a5a}
.eh-link-btn{
  padding:8px 14px;border-radius:10px;font-size:13px;font-weight:700;
  text-decoration:none;color:#0f2620;border:1px solid var(--line,#ddece6);
  background:#fff;
}
.eh-link-btn.primary{background:#0f9d76;color:#fff;border-color:#0f9d76}
.eh-link-btn.primary:hover{background:#0a7a5a}

/* Mini-bar pour pages sans topbar */
.eh-mini-bar{
  display:flex;align-items:center;gap:12px;
  padding:10px 18px;background:#fff;
  border-bottom:1px solid var(--line,#ddece6);
  position:sticky;top:0;z-index:50;
}
.eh-brand-mini{
  display:flex;align-items:center;gap:8px;
  font-weight:800;font-size:14px;color:#0f2620;text-decoration:none;
}
.eh-brand-mark{
  width:28px;height:28px;border-radius:8px;
  background:linear-gradient(135deg,#0f9d76,#37c79c);color:#fff;
  display:flex;align-items:center;justify-content:center;
  font-size:16px;font-weight:800;
}
@media (max-width:500px){
  .eh-user-trigger{max-width:100px;font-size:12px}
  .eh-icon-btn{width:34px;height:34px;font-size:15px}
}
'''
(STATIC / "header.css").write_text(HEADER_CSS, encoding="utf-8")
print("[OK] static/header.css")

# ============================================================
# 2. HEADER.JS
# ============================================================
HEADER_JS = '''/* Elokinab Health - Header unifie (injecteur) */
(function () {
  var API = "/api";

  function el(tag, cls, txt) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (txt !== undefined && txt !== null) n.textContent = txt;
    return n;
  }

  function fetchJson(path) {
    return fetch(API + path, { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
  }

  var ROLE_LABELS = {
    PATIENT: "Particulier",
    PROFESSIONNEL: "Professionnel",
    PHARMACIEN: "Pharmacien",
    ADMIN: "Administrateur",
    LIVREUR_MOTO: "Livreur moto",
    CHAUFFEUR: "Chauffeur"
  };

  function buildUserActions(user, cartCount, notifCount) {
    var wrap = el("div", "eh-user-actions");

    if (user) {
      if (user.role === "PATIENT" || user.role === "PROFESSIONNEL") {
        var cart = el("a", "eh-icon-btn");
        cart.href = "/static/cart.html";
        cart.title = "Panier";
        cart.innerHTML = '&#128722;';
        var cBadge = el("span", "eh-badge eh-cart-count" + (cartCount > 0 ? "" : " hidden"));
        cBadge.textContent = cartCount > 99 ? "99+" : String(cartCount);
        cart.appendChild(cBadge);
        wrap.appendChild(cart);
      }

      var bell = el("a", "eh-icon-btn");
      bell.href = "/static/notifications.html";
      bell.title = "Notifications";
      bell.innerHTML = '&#128276;';
      var nBadge = el("span", "eh-badge eh-notif-count" + (notifCount > 0 ? "" : " hidden"));
      nBadge.textContent = notifCount > 99 ? "99+" : String(notifCount);
      bell.appendChild(nBadge);
      wrap.appendChild(bell);

      var menu = el("div", "eh-user-menu");
      var trigger = el("button", "eh-user-trigger");
      trigger.type = "button";
      trigger.textContent = (user.full_name || user.email || "Compte").slice(0, 18);
      var dd = el("div", "eh-dropdown hidden");
      var head = el("div", "eh-drop-user");
      head.innerHTML = (user.full_name || user.email) +
        '<br><small>' + (ROLE_LABELS[user.role] || user.role) + '</small>';
      dd.appendChild(head);

      if (user.role === "PHARMACIEN" || user.role === "ADMIN") {
        var a = el("a", null, "Tableau de bord");
        a.href = "/pharmacien";
        dd.appendChild(a);
      }
      if (user.role === "LIVREUR_MOTO" || user.role === "CHAUFFEUR") {
        var a = el("a", null, "Mes livraisons");
        a.href = "/static/driver.html";
        dd.appendChild(a);
      }
      if (user.role === "PROFESSIONNEL") {
        var a = el("a", null, "Ma structure");
        a.href = "/static/professional.html";
        dd.appendChild(a);
      }
      var a2 = el("a", null, "Mes notifications");
      a2.href = "/static/notifications.html";
      dd.appendChild(a2);
      var a3 = el("a", null, "Mon panier");
      a3.href = "/static/cart.html";
      if (user.role === "PATIENT" || user.role === "PROFESSIONNEL") dd.appendChild(a3);
      var a4 = el("a", null, "Mes commandes");
      a4.href = "/suivi";
      dd.appendChild(a4);
      var a5 = el("a", null, "Site patient");
      a5.href = "/";
      dd.appendChild(a5);

      var logout = el("button", null, "Deconnexion");
      logout.type = "button";
      logout.addEventListener("click", function () {
        fetch(API + "/auth/logout", { method: "POST", credentials: "same-origin" })
          .then(function () { window.location.href = "/"; });
      });
      dd.appendChild(logout);

      menu.appendChild(trigger);
      menu.appendChild(dd);
      wrap.appendChild(menu);

      trigger.addEventListener("click", function (e) {
        e.stopPropagation();
        dd.classList.toggle("hidden");
      });
      document.addEventListener("click", function (e) {
        if (!menu.contains(e.target)) dd.classList.add("hidden");
      });
    } else {
      var login = el("a", "eh-link-btn", "Connexion");
      login.href = "/static/login.html";
      var reg = el("a", "eh-link-btn primary", "Inscription");
      reg.href = "/static/register.html";
      wrap.appendChild(login);
      wrap.appendChild(reg);
    }

    return wrap;
  }

  function inject() {
    Promise.all([
      fetchJson("/auth/me"),
      fetchJson("/cart"),
      fetchJson("/notifications?unread_only=1")
    ]).then(function (r) {
      var user = r[0];
      var cartCount = (r[1] && r[1].item_count) || 0;
      var notifCount = Array.isArray(r[2]) ? r[2].length : 0;
      var actions = buildUserActions(user, cartCount, notifCount);

      var inner = document.querySelector(".topbar .topbar-inner")
        || document.querySelector(".topbar")
        || document.querySelector(".eh-mini-bar");

      if (inner) {
        var existing = inner.querySelector(".eh-user-actions");
        if (existing) existing.remove();
        inner.appendChild(actions);
      } else {
        var bar = el("div", "eh-mini-bar");
        var brand = el("a", "eh-brand-mini");
        brand.href = "/";
        brand.innerHTML = '<span class="eh-brand-mark">+</span> Elokinab Health';
        bar.appendChild(brand);
        bar.appendChild(actions);
        document.body.insertBefore(bar, document.body.firstChild);
      }
    });
  }

  window.EHHeader = {
    refresh: inject,
    updateCartBadge: function (count) {
      var nodes = document.querySelectorAll(".eh-cart-count");
      Array.prototype.forEach.call(nodes, function (b) {
        if (count > 0) {
          b.textContent = count > 99 ? "99+" : String(count);
          b.classList.remove("hidden");
        } else {
          b.classList.add("hidden");
        }
      });
    },
    updateNotifBadge: function (count) {
      var nodes = document.querySelectorAll(".eh-notif-count");
      Array.prototype.forEach.call(nodes, function (b) {
        if (count > 0) {
          b.textContent = count > 99 ? "99+" : String(count);
          b.classList.remove("hidden");
        } else {
          b.classList.add("hidden");
        }
      });
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", inject);
  } else {
    inject();
  }
})();
'''
(STATIC / "header.js").write_text(HEADER_JS, encoding="utf-8")
print("[OK] static/header.js")

# ============================================================
# 3. NOTIFICATIONS PAGE
# ============================================================
NOTIF_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Notifications - Elokinab Health</title>
<link rel="stylesheet" href="/static/auth.css">
<link rel="stylesheet" href="/static/header.css">
<style>
  .auth-card{max-width:640px}
  .notif-item{
    display:flex;gap:12px;padding:14px;margin-bottom:8px;
    background:#fff;border:1px solid #ddece6;border-radius:12px;
    cursor:pointer;transition:.15s;
  }
  .notif-item:hover{border-color:#0f9d76;background:#fafdfb}
  .notif-item.unread{background:#e8f7f1;border-color:#c7e9dc}
  .notif-dot{
    width:10px;height:10px;border-radius:50%;
    background:#0f9d76;flex-shrink:0;margin-top:7px;
  }
  .notif-item.read .notif-dot{background:#ddece6}
  .notif-body{flex:1;min-width:0}
  .notif-title{font-weight:700;font-size:14px}
  .notif-text{font-size:13px;color:#6c8a80;margin-top:2px}
  .notif-date{font-size:11px;color:#6c8a80;margin-top:4px}
  .notif-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:14px}
  .empty-notif{text-align:center;padding:30px;color:#6c8a80}
</style>
</head>
<body class="auth-body">
<div class="auth-card">
  <h1>Mes notifications</h1>
  <p class="sub">Toutes les mises a jour de vos commandes et activites.</p>
  <div id="msg" class="auth-msg hidden"></div>
  <div id="list"></div>
  <div class="notif-actions">
    <button class="auth-btn" id="mark-all" style="flex:0;padding:10px 16px">Tout marquer comme lu</button>
  </div>
  <div class="auth-alt"><a href="/">Retour a l'accueil</a></div>
</div>
<script src="/static/header.js"></script>
<script src="/static/notifications.js"></script>
</body>
</html>
'''
(STATIC / "notifications.html").write_text(NOTIF_HTML, encoding="utf-8")
print("[OK] static/notifications.html")

NOTIF_JS = '''(function () {
  function $(id) { return document.getElementById(id); }
  function showMsg(t) { var m = $("msg"); m.textContent = t; m.className = "auth-msg"; }
  function hideMsg() { var m = $("msg"); m.className = "auth-msg hidden"; }

  function call(m, p, d) {
    return fetch(p, {
      method: m,
      credentials: "same-origin",
      headers: d ? { "Content-Type": "application/json" } : {},
      body: d ? JSON.stringify(d) : undefined
    }).then(function (r) {
      if (r.status === 401) { window.location.href = "/static/login.html?next=/static/notifications.html"; throw new Error("auth"); }
      return r.json().then(function (data) {
        if (!r.ok) throw new Error(data.detail || "Erreur");
        return data;
      });
    });
  }

  function fmtDate(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    var pad = function (n) { return n < 10 ? "0" + n : "" + n; };
    return pad(d.getDate()) + "/" + pad(d.getMonth()+1) + "/" + d.getFullYear()
      + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
  }

  function render(list) {
    var box = $("list");
    box.innerHTML = "";
    if (!list || list.length === 0) {
      box.innerHTML = '<div class="empty-notif">Aucune notification.</div>';
      return;
    }
    list.forEach(function (n) {
      var item = document.createElement("div");
      item.className = "notif-item " + (n.is_read ? "read" : "unread");
      var dot = document.createElement("div");
      dot.className = "notif-dot";
      var body = document.createElement("div");
      body.className = "notif-body";
      body.innerHTML =
        '<div class="notif-title">' + (n.title || "") + '</div>' +
        '<div class="notif-text">' + (n.body || "") + '</div>' +
        '<div class="notif-date">' + fmtDate(n.created_at) + '</div>';
      item.appendChild(dot);
      item.appendChild(body);
      item.addEventListener("click", function () {
        if (n.is_read) return;
        call("PATCH", "/api/notifications/" + n.id + "/read")
          .then(load).catch(function () {});
      });
      box.appendChild(item);
    });
  }

  function refreshBadge() {
    fetch("/api/notifications?unread_only=1", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (l) {
        var n = Array.isArray(l) ? l.length : 0;
        if (window.EHHeader) window.EHHeader.updateNotifBadge(n);
      }).catch(function () {});
  }

  function load() {
    hideMsg();
    call("GET", "/api/notifications").then(function (list) {
      render(list);
      refreshBadge();
    }).catch(function (e) {
      if (e.message !== "auth") showMsg(e.message);
    });
  }

  function markAll() {
    call("PATCH", "/api/notifications/read-all")
      .then(load).catch(function (e) { showMsg(e.message); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    load();
    $("mark-all").addEventListener("click", markAll);
  });
})();
'''
(STATIC / "notifications.js").write_text(NOTIF_JS, encoding="utf-8")
print("[OK] static/notifications.js")

# ============================================================
# 4. PATCH index.html : retirer anciens liens Panier/Connexion
# ============================================================
IDX = STATIC / "index.html"
html = IDX.read_text(encoding="utf-8")

old_links = '''      <a href="/static/cart.html" class="nav-cart">
        Panier <span id="cart-badge" class="cart-badge hidden">0</span>
      </a>
      <a href="/static/login.html" class="nav-login">Connexion</a>'''

if old_links in html:
    html = html.replace(old_links, "", 1)
    IDX.write_text(html, encoding="utf-8")
    print("[OK] index.html -> anciens liens Panier/Connexion retires")

# ============================================================
# 5. PATCH app.js : mettre a jour le badge du header
# ============================================================
APPJS = STATIC / "app.js"
js = APPJS.read_text(encoding="utf-8")

old_upd = '''function updateCartBadge(count) {
  var b = document.getElementById("cart-badge");
  if (!b) return;
  if (count > 0) {
    b.textContent = count > 99 ? "99+" : String(count);
    b.classList.remove("hidden");
  } else {
    b.classList.add("hidden");
  }
}'''
new_upd = '''function updateCartBadge(count) {
  var b = document.getElementById("cart-badge");
  if (b) {
    if (count > 0) { b.textContent = count > 99 ? "99+" : String(count); b.classList.remove("hidden"); }
    else { b.classList.add("hidden"); }
  }
  if (window.EHHeader && window.EHHeader.updateCartBadge) {
    window.EHHeader.updateCartBadge(count);
  }
}'''
if old_upd in js:
    js = js.replace(old_upd, new_upd, 1)
    APPJS.write_text(js, encoding="utf-8")
    print("[OK] app.js -> updateCartBadge propage au header")

# ============================================================
# 6. PATCH pharmacien.html : modal d'assignation
# ============================================================
PHHTML = STATIC / "pharmacien.html"
html = PHHTML.read_text(encoding="utf-8")

assign_modal = '''<div id="assign-modal" class="modal hidden">
  <div class="modal-backdrop" data-close-assign></div>
  <div class="modal-content">
    <header class="modal-head">
      <h2>&#128100; Assigner un livreur</h2>
      <button type="button" class="modal-close" data-close-assign>&times;</button>
    </header>
    <div id="assign-body" class="assign-body">
      <p class="muted small" id="assign-ref"></p>
      <div id="assign-list" class="assign-list"></div>
    </div>
    <footer class="modal-foot">
      <button type="button" class="btn btn-ghost" data-close-assign>Annuler</button>
    </footer>
  </div>
</div>

'''
anchor = '<script src="/static/pharmacien.js"></script>'
if anchor in html and 'id="assign-modal"' not in html:
    html = html.replace(anchor, assign_modal + anchor, 1)
    PHHTML.write_text(html, encoding="utf-8")
    print("[OK] pharmacien.html -> modal assignation")

# ============================================================
# 7. PATCH pharmacien.js : bouton + logique d'assignation
# ============================================================
PHJS = STATIC / "pharmacien.js"
js = PHJS.read_text(encoding="utf-8")

# 7a. Ajouter un bouton "Assigner" a cote du bouton "Envoyer au livreur"
anchor_btn = '    driverBox.appendChild(driverBtn);'
if anchor_btn in js and "openAssignModal" not in js:
    addition = anchor_btn + '''
    var assignBtn = el("button", "btn btn-ghost", "\\uD83D\\uDC64 Assigner");
    assignBtn.type = "button";
    assignBtn.addEventListener("click", function () { openAssignModal(o); });
    driverBox.appendChild(assignBtn);'''
    js = js.replace(anchor_btn, addition, 1)
    print("[OK] pharmacien.js -> bouton Assigner")
else:
    print("[i] pharmacien.js -> bouton deja ajoute ou anchor introuvable")

# 7b. Fonctions d'assignation
assign_js = '''
// ====== V3 : Assignation livreur ======
function openAssignModal(order) {
  var modal = document.getElementById("assign-modal");
  if (!modal) return;
  modal.classList.remove("hidden");
  modal._order = order;

  var refEl = document.getElementById("assign-ref");
  if (refEl) refEl.textContent = "Commande : " + (order.reference || "");

  var list = document.getElementById("assign-list");
  list.innerHTML = '<div class="muted small" style="padding:14px;text-align:center">Chargement...</div>';

  fetch(API + "/drivers").then(function (r) {
    if (!r.ok) throw new Error();
    return r.json();
  }).then(function (drivers) {
    list.innerHTML = "";
    if (!drivers || drivers.length === 0) {
      list.appendChild(el("div", "muted small", "Aucun livreur actif."));
      return;
    }
    drivers.forEach(function (d) {
      var row = el("div", "assign-row");
      var info = el("div", "assign-info");
      info.appendChild(el("div", "assign-name", d.name));
      info.appendChild(el("div", "assign-phone", String(d.phone || "").replace(/\\D/g, "")));
      var btn = el("button", "btn btn-primary", "Assigner");
      btn.type = "button";
      btn.addEventListener("click", function () {
        btn.disabled = true;
        btn.textContent = "Assignation...";
        fetch(API + "/orders/" + encodeURIComponent(order.reference) + "/assign", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ driver_id: d.id })
        }).then(function (r) {
          return r.json().then(function (b) {
            if (!r.ok) throw new Error(b.detail || "Erreur");
            return b;
          });
        }).then(function () {
          row.innerHTML = '<div class="assign-info"><div class="assign-name">\\u2713 ' +
            d.name + '</div><div class="assign-phone">Livreur assigne</div></div>';
          setTimeout(closeAssignModal, 1000);
        }).catch(function (e) {
          btn.disabled = false;
          btn.textContent = "Assigner";
          alert(e.message);
        });
      });
      row.appendChild(info);
      row.appendChild(btn);
      list.appendChild(row);
    });
  }).catch(function () {
    list.innerHTML = '<div class="muted small" style="padding:14px;text-align:center">Erreur de chargement.</div>';
  });
}

function closeAssignModal() {
  var modal = document.getElementById("assign-modal");
  if (modal) modal.classList.add("hidden");
}

document.addEventListener("DOMContentLoaded", function () {
  var modal = document.getElementById("assign-modal");
  if (!modal) return;
  var closers = modal.querySelectorAll("[data-close-assign]");
  Array.prototype.forEach.call(closers, function (b) {
    b.addEventListener("click", closeAssignModal);
  });
});
'''
if "function openAssignModal" not in js:
    js = js + "\n" + assign_js
    PHJS.write_text(js, encoding="utf-8")
    print("[OK] pharmacien.js -> openAssignModal")
else:
    print("[i] pharmacien.js -> openAssignModal deja present")

# 7c. Styles admin
PHCSS = STATIC / "pharmacien.css"
css = PHCSS.read_text(encoding="utf-8")
if ".assign-row" not in css:
    css += '''
/* --- Modal assignation --- */
.assign-body{padding:14px 20px;overflow-y:auto;max-height:60vh}
.assign-list{display:flex;flex-direction:column;gap:8px;margin-top:10px}
.assign-row{
  display:flex;align-items:center;gap:12px;
  padding:12px 14px;background:#fff;border:1px solid var(--line);
  border-radius:12px;
}
.assign-info{flex:1;min-width:0}
.assign-name{font-weight:700;font-size:14px}
.assign-phone{font-size:12px;color:var(--muted);font-family:Consolas,monospace}
.assign-row .btn{padding:8px 14px;font-size:13px}
'''
    PHCSS.write_text(css, encoding="utf-8")
    print("[OK] pharmacien.css -> styles assignation")

# ============================================================
# 8. INJECTER header.css + header.js SUR TOUTES LES PAGES
# ============================================================
PAGES = [
    "index.html", "cart.html", "payment.html",
    "professional.html", "driver.html", "suivi.html",
    "pharmacien.html", "login.html", "register.html",
]
LINK = '<link rel="stylesheet" href="/static/header.css">'
SCRIPT = '<script src="/static/header.js"></script>'

injected = 0
for page in PAGES:
    p = STATIC / page
    if not p.exists():
        continue
    content = p.read_text(encoding="utf-8")
    changed = False

    if LINK not in content:
        if "</head>" in content:
            content = content.replace("</head>", LINK + "\n</head>", 1)
            changed = True

    if SCRIPT not in content:
        if "</body>" in content:
            content = content.replace("</body>", SCRIPT + "\n</body>", 1)
            changed = True

    if changed:
        p.write_text(content, encoding="utf-8")
        injected += 1
        print("[OK] " + page)

print("[OK] header injecte dans " + str(injected) + " pages")

# ============================================================
# 9. RESUME
# ============================================================
print()
print("=" * 60)
print("FINITION UI + ASSIGNATION + NOTIFICATIONS INSTALLEES")
print("=" * 60)
print()
print("Fichiers crees :")
print("  static/header.css")
print("  static/header.js")
print("  static/notifications.html")
print("  static/notifications.js")
print()
print("Fichiers modifies :")
print("  static/index.html       (retrait anciens liens Panier/Connexion)")
print("  static/app.js           (updateCartBadge propage au header)")
print("  static/pharmacien.html  (modal assignation)")
print("  static/pharmacien.js    (bouton Assigner + openAssignModal)")
print("  static/pharmacien.css   (styles assignation)")
print("  Toutes les pages HTML   (header.css + header.js)")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R dans le navigateur (pas besoin de redemarrer le serveur)")