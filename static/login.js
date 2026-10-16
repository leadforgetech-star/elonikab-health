/* Login Elonikab Health */
(function () {
  var $ = function (id) { return document.getElementById(id); };
  function showMsg(t, ok) {
    var m = $("msg"); m.textContent = t;
    m.className = "msg" + (ok ? " ok" : "");
  }
  function hideMsg() { $("msg").className = "msg hidden"; }

  document.addEventListener("DOMContentLoaded", function () {
    // Toggle mot de passe
    var eye = $("toggle-eye");
    var pwd = $("password");
    if (eye && pwd) {
      eye.addEventListener("click", function () {
        if (pwd.type === "password") {
          pwd.type = "text";
          eye.innerHTML = "&#128584;";
          eye.setAttribute("aria-label", "Masquer le mot de passe");
        } else {
          pwd.type = "password";
          eye.innerHTML = "&#128065;";
          eye.setAttribute("aria-label", "Afficher le mot de passe");
        }
      });
    }

    // Submit
    $("login-form").addEventListener("submit", function (ev) {
      ev.preventDefault();
      hideMsg();
      var btn = $("btn");
      btn.disabled = true; btn.textContent = "Connexion...";

      var __next = "";
      try {
        var __params = new URLSearchParams(window.location.search);
        var __n = __params.get("next") || "";
        if (__n && __n.charAt(0) === "/" &&
            __n.indexOf("://") === -1 &&
            __n.indexOf("//") !== 0 &&
            __n.indexOf("/api/") !== 0) {
          __next = __n;
        }
      } catch(e){}

      fetch("/api/auth/login", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: $("email").value.trim(),
          password: $("password").value,
          next: __next
        })
      })
      .then(function (r) {
        return r.json().then(function (d) {
          if (!r.ok) throw new Error(d.detail || "Identifiants incorrects");
          return d;
        });
      })
      .then(function (d) {
        try { localStorage.setItem("eh_user_cache",
          JSON.stringify({ user: d.user, _at: Date.now() })); } catch (e) {}
        showMsg("Connexion reussie. Redirection...", true);
        var target = (d && d.redirect_to) ? d.redirect_to : "/";
        setTimeout(function () { window.location.href = target; }, 500);
      })
      .catch(function (e) {
        showMsg(e.message || "Erreur de connexion");
        btn.disabled = false; btn.textContent = "Se connecter";
      });
    });
  });
})();
