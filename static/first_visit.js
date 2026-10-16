/* Elonikab Health - Auto-redirect premier visiteur */
(function () {
  var KEY = "eh_visited";
  var SKIP_PAGES = ["/static/register.html", "/static/login.html",
                    "/static/payment.html", "/static/driver.html",
                    "/pharmacien", "/suivi"];
  var path = window.location.pathname;
  for (var i = 0; i < SKIP_PAGES.length; i++) {
    if (path.indexOf(SKIP_PAGES[i]) === 0) return;
  }

  var seen = null;
  try { seen = localStorage.getItem(KEY); } catch (e) {}

  if (seen) return;

  // Verifier si un compte est deja connecte
  fetch("/api/auth/me", { credentials: "same-origin" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (user) {
      try { localStorage.setItem(KEY, "1"); } catch (e) {}
      if (!user && path === "/") {
        window.location.href = "/inscription";
      }
    })
    .catch(function () {
      try { localStorage.setItem(KEY, "1"); } catch (e) {}
    });
})();
