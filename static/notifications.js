/* Elonikab Health - Notifications (V6) */
(function () {
  "use strict";

  var API = "/api";

  function $(id) { return document.getElementById(id); }

  function fmtDate(iso) {
    if (!iso) return "";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return iso;
      var diff = Math.floor((Date.now() - d.getTime()) / 1000);
      if (diff < 60) return "A l'instant";
      if (diff < 3600) return "Il y a " + Math.floor(diff / 60) + " min";
      if (diff < 86400) return "Il y a " + Math.floor(diff / 3600) + " h";
      if (diff < 604800) return "Il y a " + Math.floor(diff / 86400) + " j";
      var pad = function (n) { return n < 10 ? "0" + n : "" + n; };
      return pad(d.getDate()) + "/" + pad(d.getMonth()+1) + "/" + d.getFullYear();
    } catch (e) { return ""; }
  }

  function showToast(msg, color) {
    var t = $("toast");
    if (!t) return;
    t.textContent = msg;
    t.style.background = color || "#174A7E";
    t.style.display = "block";
    setTimeout(function () { t.style.display = "none"; }, 2500);
  }

  function call(m, p, d) {
    return fetch(p, {
      method: m,
      credentials: "same-origin",
      headers: d ? { "Content-Type": "application/json" } : {},
      body: d ? JSON.stringify(d) : undefined
    }).then(function (r) {
      if (r.status === 401) {
        window.location.href = "/connexion?next=/notifications.html";
        throw new Error("auth");
      }
      return r.json().then(function (data) {
        if (!r.ok) throw new Error(data.detail || "Erreur");
        return data;
      });
    });
  }

  function render(list) {
    var box = $("list");
    if (!box) return;
    if (!list || list.length === 0) {
      box.innerHTML =
        '<div class="pt-empty">' +
          '<span class="pt-empty-ico">&#128276;</span>' +
          '<h2>Aucune notification</h2>' +
          '<p>Vos mises a jour apparaitront ici.</p>' +
        '</div>';
      return;
    }
    box.innerHTML = "";
    list.forEach(function (n) {
      var item = document.createElement("div");
      item.className = "pt-notif " + (n.is_read ? "read" : "unread");
      var ico = document.createElement("div");
      ico.className = "pt-notif-ico";
      ico.innerHTML = "&#128276;";
      var body = document.createElement("div");
      body.className = "pt-notif-body";
      var title = document.createElement("div");
      title.className = "pt-notif-title";
      title.textContent = n.title || "Notification";
      var text = document.createElement("div");
      text.className = "pt-notif-text";
      text.textContent = n.body || "";
      var date = document.createElement("div");
      date.className = "pt-notif-date";
      date.textContent = fmtDate(n.created_at);
      body.appendChild(title);
      body.appendChild(text);
      body.appendChild(date);
      item.appendChild(ico);
      item.appendChild(body);
      if (!n.is_read) {
        var dot = document.createElement("span");
        dot.className = "pt-notif-dot";
        item.appendChild(dot);
      }
      item.addEventListener("click", function () {
        if (n.order_id) {
          window.location.href = "/suivi?ref=" + encodeURIComponent(n.order_id);
        } else if (!n.is_read) {
          call("PATCH", API + "/notifications/" + n.id + "/read")
            .then(load).catch(function () {});
        }
      });
      box.appendChild(item);
    });
  }

  function load() {
    call("GET", API + "/notifications").then(function (list) {
      render(list);
    }).catch(function (e) {
      if (e.message !== "auth") showToast(e.message, "#B23C3C");
    });
  }

  function clearAll() {
    if (!confirm("Supprimer toutes vos notifications ?")) return;
    var btn = $("btn-clear");
    btn.disabled = true;
    btn.textContent = "Suppression...";
    call("DELETE", API + "/notifications").then(function (res) {
      showToast((res && res.deleted ? res.deleted + " " : "") + "notification(s) supprimee(s)", "#0A7A5A");
      load();
      if (window.PatientNav && window.PatientNav.refreshBellBadge) {
        window.PatientNav.refreshBellBadge();
      }
    }).catch(function (e) {
      showToast(e.message, "#B23C3C");
    }).then(function () {
      btn.disabled = false;
      btn.textContent = "Nettoyer";
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    load();
    var b = $("btn-clear");
    if (b) b.addEventListener("click", clearAll);
  });

  document.addEventListener("eh:refresh", function () {
    try { load(); } catch (e) {}
  });
})();
