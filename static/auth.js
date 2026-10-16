var EH = (function () {
  function $(id) { return document.getElementById(id); }
  function showMsg(text, ok) {
    var m = $("msg");
    if (!m) return;
    m.textContent = text;
    m.className = "auth-msg" + (ok ? " ok" : "");
  }
  function hideMsg() { var m = $("msg"); if (m) m.className = "auth-msg hidden"; }

  function post(path, body) {
    return fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (r) {
      return r.json().then(function (data) {
        if (!r.ok) throw new Error(data.detail || "Erreur serveur");
        return data;
      });
    });
  }

  function initLogin() {
    var form = $("login-form");
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      hideMsg();
      var btn = $("btn");
      btn.disabled = true; btn.textContent = "Connexion...";
      post("/api/auth/login", {
        email: $("email").value.trim(),
        password: $("password").value
      }).then(function (data) {
        // Cache le user pour eviter une requete /auth/me
        try { localStorage.setItem("eh_user_cache", JSON.stringify({ user: data.user, _at: Date.now() })); } catch (e) {}
        showMsg("Connexion reussie. Redirection...", true);
        setTimeout(function () { window.location.href = "/"; }, 600);
      }).catch(function (e) {
        showMsg(e.message);
        btn.disabled = false; btn.textContent = "Se connecter";
      });
    });
  }

  function initRegister() {
    var form = $("register-form");
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      hideMsg();
      var btn = $("btn");
      btn.disabled = true; btn.textContent = "Creation...";
      post("/api/auth/register", {
        role: $("role").value,
        full_name: $("full_name").value.trim(),
        email: $("email").value.trim(),
        phone: $("phone").value.trim(),
        password: $("password").value
      }).then(function (data) {
        try { localStorage.setItem("eh_user_cache", JSON.stringify({ user: data.user, _at: Date.now() })); } catch (e) {}
        showMsg("Compte cree. Redirection...", true);
        setTimeout(function () { window.location.href = "/"; }, 600);
      }).catch(function (e) {
        showMsg(e.message);
        btn.disabled = false; btn.textContent = "Creer mon compte";
      });
    });
  }

  return { initLogin: initLogin, initRegister: initRegister };
})();
