"""
v6_notifications_accueil.py
Section Notifications integree a l'accueil pro.
- Uniquement les non lues
- Section cachee si vide
- Clic = marque lu + redirige
"""
from pathlib import Path
import datetime
import re
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
PRO_HTML = STATIC / "professional.html"
DASH_JS = STATIC / "professional_dashboard.js"
CSS = STATIC / "professional_accueil.css"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_notif_accueil_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(PRO_HTML, backup / "professional.html")
shutil.copy2(DASH_JS, backup / "professional_dashboard.js")
shutil.copy2(CSS, backup / "professional_accueil.css")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. HTML : ajouter section notifications
# ============================================================
html = PRO_HTML.read_text(encoding="utf-8")

if 'id="notifications-section"' not in html:
    NOTIF_HTML = '''  <!-- Notifications -->
  <section class="acc-section hidden" id="notifications-section">
    <h2 class="acc-section-title">
      Notifications
      <button type="button" class="acc-mark-read" id="mark-all-read">Tout marquer lu</button>
    </h2>
    <div id="notifications"></div>
  </section>

'''
    # Inserer avant le bloc support WhatsApp
    anchor = '  <!-- Support WhatsApp -->'
    if anchor in html:
        html = html.replace(anchor, NOTIF_HTML + anchor, 1)
        PRO_HTML.write_text(html, encoding="utf-8")
        print("[OK] professional.html -> section notifications ajoutee")
    else:
        print("[!] anchor 'Support WhatsApp' introuvable")

# ============================================================
# 2. CSS : styles notifications
# ============================================================
css = CSS.read_text(encoding="utf-8")

if ".acc-notif" not in css:
    NOTIF_CSS = '''

/* -------- Notifications -------- */
.acc-section-title{
  display:flex;align-items:center;justify-content:space-between;
  gap:10px;
}
.acc-mark-read{
  background:none;border:0;padding:4px 8px;
  font-size:11px;font-weight:800;color:var(--blue);
  text-transform:none;letter-spacing:0;
  cursor:pointer;font-family:inherit;
  border-radius:6px;
}
.acc-mark-read:hover{background:var(--blue-soft);color:var(--blue-dark)}

.acc-notif-list{
  background:#fff;border:1px solid var(--line);
  border-radius:var(--radius);overflow:hidden;
}
.acc-notif-item{
  display:flex;align-items:flex-start;gap:12px;
  padding:13px 16px;
  border-bottom:1px solid var(--line-soft);
  cursor:pointer;transition:.12s;
  text-decoration:none;color:inherit;
}
.acc-notif-item:last-child{border-bottom:0}
.acc-notif-item:hover{background:#fafbfc}

.acc-notif-icon{
  width:32px;height:32px;border-radius:9px;
  display:flex;align-items:center;justify-content:center;
  font-size:15px;flex-shrink:0;
}
.acc-notif-icon.payment{background:var(--ok-soft);color:var(--ok)}
.acc-notif-icon.order{background:var(--blue-soft);color:var(--blue)}
.acc-notif-icon.prescription{background:#f3e8ff;color:#6335b8}
.acc-notif-icon.default{background:#f1f5f9;color:var(--muted)}

.acc-notif-body{flex:1;min-width:0}
.acc-notif-title{
  font-size:13px;font-weight:800;color:var(--ink);
  margin:0 0 3px;line-height:1.35;
}
.acc-notif-text{
  font-size:12px;color:var(--muted);margin:0;
  line-height:1.45;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
  overflow:hidden;
}
.acc-notif-date{
  font-size:10px;color:var(--muted-soft);
  font-family:Consolas,monospace;margin-top:4px;
}

.acc-notif-empty{
  padding:20px 16px;text-align:center;
  font-size:13px;color:var(--muted);
}
'''
    css += NOTIF_CSS
    CSS.write_text(css, encoding="utf-8")
    print("[OK] professional_accueil.css -> styles notifications")
else:
    print("[i] styles notifications deja presents")

# ============================================================
# 3. JS : charger et afficher les notifications
# ============================================================
js = DASH_JS.read_text(encoding="utf-8")

# 3.1 : ajouter les fonctions de notifications AVANT la fonction init
NOTIF_FUNCTIONS = '''
  // ============================================================
  // Notifications
  // ============================================================
  function notifIcon(type) {
    if (type === "payment") return { cls: "payment", char: "\\uD83D\\uDCB0" };
    if (type === "order") return { cls: "order", char: "\\uD83D\\uDCE6" };
    if (type === "prescription") return { cls: "prescription", char: "\\u2695\\uFE0F" };
    return { cls: "default", char: "\\uD83D\\uDD14" };
  }

  function notifTypeFromData(n) {
    var title = String((n.title || "")).toLowerCase();
    if (title.indexOf("paiement") >= 0) return "payment";
    if (title.indexOf("commande") >= 0) return "order";
    if (title.indexOf("ordonnance") >= 0) return "prescription";
    return "default";
  }

  function loadNotifications() {
    return api("/notifications?unread_only=1")
      .then(function (list) {
        var arr = Array.isArray(list) ? list : [];
        renderNotifications(arr);
      })
      .catch(function () { renderNotifications([]); });
  }

  function renderNotifications(list) {
    var section = $("notifications-section");
    var box = $("notifications");
    if (!section || !box) return;

    if (!list || list.length === 0) {
      section.classList.add("hidden");
      box.innerHTML = "";
      return;
    }

    section.classList.remove("hidden");
    box.innerHTML = "";

    var wrap = document.createElement("div");
    wrap.className = "acc-notif-list";

    // Afficher les 4 plus recentes
    list.slice(0, 4).forEach(function (n) {
      var iconInfo = notifIcon(notifTypeFromData(n));
      var item = document.createElement("a");
      item.className = "acc-notif-item";
      // Si la notification est liee a une commande, pointer vers le suivi
      var target = "/suivi";
      // Essayer d'extraire une reference dans le corps ou l'order_id
      var refMatch = String(n.body || "").match(/CMD-[0-9]{6}-[A-Z0-9]+/);
      if (refMatch) {
        target = "/suivi?ref=" + encodeURIComponent(refMatch[0]);
      } else if (n.order_id) {
        // Fallback : on n'a pas la ref, mais on peut cliquer pour marquer lu
        target = "#";
      }
      item.href = target;
      item.setAttribute("data-notif-id", String(n.id));

      var dateStr = "";
      try {
        var d = new Date(n.created_at);
        if (!isNaN(d.getTime())) {
          var pad = function (x) { return x < 10 ? "0" + x : "" + x; };
          dateStr = pad(d.getDate()) + "/" + pad(d.getMonth() + 1) + " " +
                    pad(d.getHours()) + ":" + pad(d.getMinutes());
        }
      } catch (e) {}

      item.innerHTML =
        '<div class="acc-notif-icon ' + iconInfo.cls + '">' + iconInfo.char + '</div>' +
        '<div class="acc-notif-body">' +
          '<div class="acc-notif-title">' + escapeHtml(n.title || "Notification") + '</div>' +
          '<div class="acc-notif-text">' + escapeHtml(n.body || "") + '</div>' +
          '<div class="acc-notif-date">' + escapeHtml(dateStr) + '</div>' +
        '</div>';

      // Marquer comme lu au clic
      item.addEventListener("click", function (ev) {
        var id = item.getAttribute("data-notif-id");
        if (!id) return;
        // On ne bloque pas la navigation : on envoie la requete en arriere-plan
        fetch(API + "/notifications/" + id + "/read", {
          method: "PATCH",
          credentials: "same-origin"
        }).catch(function () {});
      });

      wrap.appendChild(item);
    });

    box.appendChild(wrap);

    // Bouton tout marquer lu
    var btn = $("mark-all-read");
    if (btn) {
      // Retirer les anciens listeners
      var newBtn = btn.cloneNode(true);
      btn.parentNode.replaceChild(newBtn, btn);
      newBtn.addEventListener("click", function (ev) {
        ev.preventDefault();
        fetch(API + "/notifications/read-all", {
          method: "PATCH",
          credentials: "same-origin"
        }).then(function () {
          renderNotifications([]);
          renderBell(0);
        }).catch(function () {});
      });
    }
  }

'''

# Inserer les fonctions avant "function init()"
if "function loadNotifications" not in js:
    anchor = "  // ============================================================\n  // Init"
    if anchor in js:
        js = js.replace(anchor, NOTIF_FUNCTIONS + anchor, 1)
        print("[OK] professional_dashboard.js -> fonctions notifications ajoutees")
    else:
        print("[!] anchor Init introuvable")

# 3.2 : appeler loadNotifications() dans load()
old_load_end = '''      renderActivity();
    }).catch(function (e) {
      console.error("load error:", e);
    });'''
new_load_end = '''      renderActivity();
      loadNotifications();
    }).catch(function (e) {
      console.error("load error:", e);
    });'''
if old_load_end in js:
    js = js.replace(old_load_end, new_load_end, 1)
    print("[OK] professional_dashboard.js -> loadNotifications appele")

DASH_JS.write_text(js, encoding="utf-8")

print()
print("=" * 60)
print("NOTIFICATIONS SUR L'ACCUEIL PRO")
print("=" * 60)
print()
print("Fonctionnement :")
print("  - Charge /api/notifications?unread_only=1")
print("  - Section masquee si aucune non lue")
print("  - Affiche les 4 plus recentes")
print("  - Icone selon type (paiement / commande / ordonnance / defaut)")
print("  - Clic = marque lu + redirige vers le suivi (si ref detectee)")
print("  - Bouton 'Tout marquer lu'")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur iPhone")
print("  (pas besoin de redemarrer Uvicorn)")
print()
print("TEST :")
print("  1. En tant que pharmacien, valide un paiement")
print("  2. Retourne sur /professionnel")
print("  3. La section Notifications doit apparaitre avec le message")