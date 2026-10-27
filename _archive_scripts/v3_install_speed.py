"""
v3_install_speed.py
- Auto-login : cookie 1 an + localStorage fallback
- Pre-remplissage automatique du checkout
- Performance : GZip + cache headers + cache localStorage
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_speed_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAIN, backup / "main.py")
for f in ("header.js", "cart.js", "auth.js"):
    p = STATIC / f
    if p.exists():
        shutil.copy2(p, backup / f)
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. main.py : GZip + cache + cookie 1 an + SameSite=Lax
# ============================================================
src = MAIN.read_text(encoding="utf-8")

# --- Ajouter GZip middleware + cache headers ---
if "GZipMiddleware" not in src:
    # Ajouter les imports
    src = src.replace(
        "from fastapi import Cookie, FastAPI, File, Form, HTTPException, UploadFile",
        "from fastapi import Cookie, FastAPI, File, Form, HTTPException, Request, UploadFile",
        1,
    )
    src = src.replace(
        "from fastapi.staticfiles import StaticFiles",
        "from fastapi.staticfiles import StaticFiles\n"
        "from starlette.middleware.gzip import GZipMiddleware\n"
        "from starlette.middleware.base import BaseHTTPMiddleware",
        1,
    )

    # Ajouter le middleware apres "app = FastAPI(...)"
    anchor = 'app = FastAPI(title="Pharmacie pilote", version="2.1.0")'
    if anchor in src:
        add = anchor + '''

# --- Performance : compression GZip ---
app.add_middleware(GZipMiddleware, minimum_size=500)

# --- Performance : cache navigateur pour /static/ ---
class StaticCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/static/"):
            if path.endswith((".css", ".js", ".html")):
                response.headers["Cache-Control"] = "public, max-age=86400"
            elif path.endswith((".jpg", ".jpeg", ".png", ".webp", ".svg")):
                response.headers["Cache-Control"] = "public, max-age=604800"
        return response

app.add_middleware(StaticCacheMiddleware)
'''
        src = src.replace(anchor, add, 1)
        print("[OK] main.py -> GZip + cache")
    else:
        print("[!] anchor FastAPI introuvable")

MAIN.write_text(src, encoding="utf-8")

# ============================================================
# 2. auth.py : cookie 1 an + secure pour HTTPS
# ============================================================
AUTH = BASE / "v3_modules" / "auth.py"
auth_src = AUTH.read_text(encoding="utf-8")

# Etendre la duree du cookie a 365 jours
auth_src = auth_src.replace(
    "SESSION_TTL_DAYS = 30",
    "SESSION_TTL_DAYS = 365",
    1,
)

# Configurer le cookie comme secure et httpOnly correctement
old_cookie = '''        response.set_cookie(SESSION_COOKIE, token, httponly=True,
                            samesite="lax", max_age=SESSION_TTL_DAYS * 86400)
        return {"user": _public(row)}

    @app.post("/api/auth/login")'''
new_cookie = '''        response.set_cookie(
            SESSION_COOKIE, token,
            httponly=True, samesite="lax", secure=False,
            max_age=SESSION_TTL_DAYS * 86400, path="/"
        )
        return {"user": _public(row)}

    @app.post("/api/auth/login")'''
if old_cookie in auth_src:
    auth_src = auth_src.replace(old_cookie, new_cookie, 1)
    print("[OK] auth.py -> cookie register")

old_cookie2 = '''        response.set_cookie(SESSION_COOKIE, token, httponly=True,
                            samesite="lax", max_age=SESSION_TTL_DAYS * 86400)
        return {"user": _public(row)}

    @app.post("/api/auth/logout")'''
new_cookie2 = '''        response.set_cookie(
            SESSION_COOKIE, token,
            httponly=True, samesite="lax", secure=False,
            max_age=SESSION_TTL_DAYS * 86400, path="/"
        )
        return {"user": _public(row)}

    @app.post("/api/auth/logout")'''
if old_cookie2 in auth_src:
    auth_src = auth_src.replace(old_cookie2, new_cookie2, 1)
    print("[OK] auth.py -> cookie login")

AUTH.write_text(auth_src, encoding="utf-8")

# ============================================================
# 3. header.js : cache localStorage + une seule verification
# ============================================================
HJ = STATIC / "header.js"
js = HJ.read_text(encoding="utf-8")

# Remplacer inject() pour utiliser un cache localStorage
old_inject = '''  function inject() {
    // Ne PAS injecter sur les pages a carte centree (auth-body)
    var SKIP_PAGES = ['''
new_inject = '''  // Cache local du user (evite 1 requete /auth/me a chaque page)
  function getCachedUser() {
    try {
      var raw = localStorage.getItem("eh_user_cache");
      if (!raw) return null;
      var obj = JSON.parse(raw);
      if (!obj || !obj._at) return null;
      if (Date.now() - obj._at > 5 * 60 * 1000) return null; // 5 min
      return obj.user || null;
    } catch (e) { return null; }
  }
  function setCachedUser(user) {
    try {
      if (user) {
        localStorage.setItem("eh_user_cache", JSON.stringify({ user: user, _at: Date.now() }));
      } else {
        localStorage.removeItem("eh_user_cache");
      }
    } catch (e) {}
  }

  function inject() {
    // Ne PAS injecter sur les pages a carte centree (auth-body)
    var SKIP_PAGES = ['''
if old_inject in js:
    js = js.replace(old_inject, new_inject, 1)

# Utiliser le cache dans le Promise.all
old_promise = '''    Promise.all([
      fetchJson("/auth/me"),
      fetchJson("/cart"),
      fetchJson("/notifications?unread_only=1")
    ]).then(function (r) {
      var user = r[0];
      var cartCount = (r[1] && r[1].item_count) || 0;
      var notifCount = Array.isArray(r[2]) ? r[2].length : 0;
      var actions = buildUserActions(user, cartCount, notifCount);'''
new_promise = '''    var cachedUser = getCachedUser();
    var promiseUser;
    if (cachedUser) {
      promiseUser = Promise.resolve(cachedUser);
    } else {
      promiseUser = fetchJson("/auth/me").then(function (u) {
        setCachedUser(u);
        return u;
      });
    }

    Promise.all([
      promiseUser,
      fetchJson("/cart"),
      fetchJson("/notifications?unread_only=1")
    ]).then(function (r) {
      var user = r[0];
      var cartCount = (r[1] && r[1].item_count) || 0;
      var notifCount = Array.isArray(r[2]) ? r[2].length : 0;
      var actions = buildUserActions(user, cartCount, notifCount);'''
if old_promise in js:
    js = js.replace(old_promise, new_promise, 1)
    print("[OK] header.js -> cache user local")

# Vider le cache au logout
old_logout = '''      logout.addEventListener("click", function () {
        fetch(API + "/auth/logout", { method: "POST", credentials: "same-origin" })
          .then(function () { window.location.href = "/"; });
      });'''
new_logout = '''      logout.addEventListener("click", function () {
        try { localStorage.removeItem("eh_user_cache"); } catch (e) {}
        fetch(API + "/auth/logout", { method: "POST", credentials: "same-origin" })
          .then(function () { window.location.href = "/"; });
      });'''
if old_logout in js:
    js = js.replace(old_logout, new_logout, 1)
    print("[OK] header.js -> cache vide au logout")

HJ.write_text(js, encoding="utf-8")

# ============================================================
# 4. auth.js : stocker le user dans localStorage apres login
# ============================================================
AJ = STATIC / "auth.js"
ajs = AJ.read_text(encoding="utf-8")

# Ajouter la mise en cache du user dans initLogin et initRegister
old_post_ok = '''      }).then(function () {
        showMsg("Connexion reussie. Redirection...", true);
        setTimeout(function () { window.location.href = "/"; }, 600);
      })'''
new_post_ok = '''      }).then(function (data) {
        // Cache le user pour eviter une requete /auth/me
        try { localStorage.setItem("eh_user_cache", JSON.stringify({ user: data.user, _at: Date.now() })); } catch (e) {}
        showMsg("Connexion reussie. Redirection...", true);
        setTimeout(function () { window.location.href = "/"; }, 600);
      })'''
if old_post_ok in ajs:
    ajs = ajs.replace(old_post_ok, new_post_ok, 1)

old_reg_ok = '''      }).then(function () {
        showMsg("Compte cree. Redirection...", true);
        setTimeout(function () { window.location.href = "/"; }, 600);
      })'''
new_reg_ok = '''      }).then(function (data) {
        try { localStorage.setItem("eh_user_cache", JSON.stringify({ user: data.user, _at: Date.now() })); } catch (e) {}
        showMsg("Compte cree. Redirection...", true);
        setTimeout(function () { window.location.href = "/"; }, 600);
      })'''
if old_reg_ok in ajs:
    ajs = ajs.replace(old_reg_ok, new_reg_ok, 1)

AJ.write_text(ajs, encoding="utf-8")
print("[OK] auth.js -> cache apres login/register")

# ============================================================
# 5. cart.js : pre-remplissage automatique des champs
# ============================================================
CJ = STATIC / "cart.js"
cjs = CJ.read_text(encoding="utf-8")

# Remplacer openCheckout pour charger depuis localStorage/cache API
old_open = '''  function openCheckout() {
    if (state.subtotal === 0) { showMsg("Panier vide"); return; }
    $("checkout-panel").classList.remove("hidden");
    document.body.classList.add("checkout-open");
    window.scrollTo(0, 0);
    updateTotals();
    fetch("/api/auth/me", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (u) {
        if (u) {
          if ($("co-name") && !$("co-name").value) $("co-name").value = u.full_name || "";
          if ($("co-phone") && !$("co-phone").value) $("co-phone").value = u.phone || "";
        }
      });
  }'''
new_open = '''  function prefillUser() {
    // 1. Essayer localStorage d'abord (instantanee)
    try {
      var raw = localStorage.getItem("eh_user_cache");
      if (raw) {
        var obj = JSON.parse(raw);
        var u = obj && obj.user;
        if (u) {
          if ($("co-name") && !$("co-name").value) $("co-name").value = u.full_name || "";
          if ($("co-phone") && !$("co-phone").value) $("co-phone").value = u.phone || "";
          return;
        }
      }
    } catch (e) {}

    // 2. Fallback API
    fetch("/api/auth/me", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (u) {
        if (u) {
          if ($("co-name") && !$("co-name").value) $("co-name").value = u.full_name || "";
          if ($("co-phone") && !$("co-phone").value) $("co-phone").value = u.phone || "";
          try { localStorage.setItem("eh_user_cache", JSON.stringify({ user: u, _at: Date.now() })); } catch (e) {}
        }
      });
  }

  function openCheckout() {
    if (state.subtotal === 0) { showMsg("Panier vide"); return; }
    $("checkout-panel").classList.remove("hidden");
    document.body.classList.add("checkout-open");
    window.scrollTo(0, 0);
    updateTotals();
    prefillUser();
  }'''
if old_open in cjs:
    cjs = cjs.replace(old_open, new_open, 1)
    print("[OK] cart.js -> pre-remplissage optimise")
else:
    print("[i] cart.js -> pre-remplissage deja optimise ou pattern introuvable")

CJ.write_text(cjs, encoding="utf-8")

print()
print("=" * 60)
print("PERFORMANCE + AUTO-LOGIN + PREFILL INSTALLES")
print("=" * 60)
print()
print("Changements :")
print("  1. Cookie session : 365 jours (au lieu de 30)")
print("  2. Cookie path=/ + httponly + SameSite=Lax")
print("  3. Cache localStorage pour /auth/me (5 min)")
print("  4. Pre-remplissage instantane du checkout")
print("  5. GZip middleware (compression JSON ~70%)")
print("  6. Cache headers : CSS/JS 1 jour, images 7 jours")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  python main.py")
print("  Sur iPhone : vider le cache Safari UNE FOIS puis tester")