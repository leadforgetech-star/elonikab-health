"""
v3_install_ui_live.py
- Header sticky + lien Suivi
- Notifications temps reel (SSE)
- Checkout plein ecran mobile
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
MODULES = BASE / "v3_modules"
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_ui_live_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAIN, backup / "main.py")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. MODULE SSE : notifications en temps reel
# ============================================================
SSE = '''"""Notifications temps reel via Server-Sent Events (SSE)."""
import asyncio
import json
from datetime import datetime

from fastapi import Cookie, Depends, Request
from fastapi.responses import StreamingResponse


SESSION_COOKIE = "elokinab_session"


def install_notifications_stream(app, get_db):
    """Enregistre GET /api/notifications/stream (SSE)."""

    @app.get("/api/notifications/stream")
    async def stream(request: Request, session_token: str = Cookie(None, alias=SESSION_COOKIE)):
        # Auth manuelle (EventSource n'accepte pas les Depends facilement)
        if not session_token:
            return StreamingResponse(
                iter(["event: error\\ndata: unauthorized\\n\\n"]),
                media_type="text/event-stream",
                status_code=401,
            )

        conn = get_db()
        try:
            user = conn.execute(
                "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id"
                " WHERE s.token = ? AND s.expires_at > ?",
                (session_token, datetime.now().isoformat(timespec="seconds")),
            ).fetchone()
        finally:
            conn.close()

        if user is None:
            return StreamingResponse(
                iter(["event: error\\ndata: unauthorized\\n\\n"]),
                media_type="text/event-stream",
                status_code=401,
            )

        user_id = user["id"]

        async def event_generator():
            last_id = 0
            # Envoyer un ping initial pour eviter les buffers proxy
            yield ": ping\\n\\n"
            idle = 0
            while True:
                if await request.is_disconnected():
                    break
                try:
                    conn = get_db()
                    rows = conn.execute(
                        "SELECT id, title, body, order_id, is_read, created_at"
                        " FROM notifications WHERE user_id = ? AND id > ?"
                        " ORDER BY id LIMIT 20",
                        (user_id, last_id),
                    ).fetchall()
                    conn.close()
                    for r in rows:
                        last_id = r["id"]
                        payload = {
                            "id": r["id"],
                            "title": r["title"],
                            "body": r["body"],
                            "order_id": r["order_id"],
                            "created_at": r["created_at"],
                        }
                        yield "data: " + json.dumps(payload) + "\\n\\n"
                        idle = 0
                    else:
                        idle += 1
                        # Ping toutes les 5 iterations inactives (~15s)
                        if idle % 5 == 0:
                            yield ": keep-alive\\n\\n"
                except Exception:
                    yield ": error\\n\\n"

                await asyncio.sleep(3)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )


'''
(MODULES / "notifications_stream.py").write_text(SSE, encoding="utf-8")
print("[OK] v3_modules/notifications_stream.py")

# ============================================================
# 2. PATCH main.py : brancher SSE + push_notification dans les transitions
# ============================================================
src = MAIN.read_text(encoding="utf-8")
if "install_notifications_stream" not in src:
    old = "install_notifications(app, get_db, require_role)"
    new = (old + "\n"
           "from v3_modules.notifications_stream import install_notifications_stream\n"
           "install_notifications_stream(app, get_db)")
    if old in src:
        src = src.replace(old, new, 1)
        print("[OK] main.py -> SSE branche")
    else:
        print("[!] anchor install_notifications introuvable")
    MAIN.write_text(src, encoding="utf-8")
else:
    print("[i] main.py deja patche")

# ============================================================
# 3. Injecter push_notification dans les transitions de statut
# ============================================================
# On ajoute des appels dans les modules existants
# Status order
CART_MOD = MODULES / "cart.py"  # pas concerne ici
# Paiements
PAY = MODULES / "payments.py"
paysrc = PAY.read_text(encoding="utf-8")
if "push_notification" not in paysrc:
    paysrc = paysrc.replace(
        "from pydantic import BaseModel",
        "from pydantic import BaseModel\n\n# push_notification importe dynamiquement (evite import circulaire)",
        1,
    )
    # Dans verify_payment
    old = '''            conn.execute(
                "UPDATE payments SET status='VERIFIED', verified_at=?, verified_by=?"
                " WHERE id=?",
                (now, user["id"], payment_id),
            )
            conn.execute(
                "UPDATE orders SET payment_status='VERIFIED' WHERE id=?",
                (pay["order_id"],),
            )
            conn.commit()'''
    new = '''            conn.execute(
                "UPDATE payments SET status='VERIFIED', verified_at=?, verified_by=?"
                " WHERE id=?",
                (now, user["id"], payment_id),
            )
            conn.execute(
                "UPDATE orders SET payment_status='VERIFIED' WHERE id=?",
                (pay["order_id"],),
            )
            try:
                from v3_modules.notifications import push_notification
                o = conn.execute("SELECT user_id, reference FROM orders WHERE id=?",
                                 (pay["order_id"],)).fetchone()
                if o and o["user_id"]:
                    push_notification(
                        conn, o["user_id"],
                        "Paiement verifie",
                        "Votre paiement pour la commande " + (o["reference"] or "") + " a ete confirme.",
                        order_id=pay["order_id"],
                    )
            except Exception:
                pass
            conn.commit()'''
    if old in paysrc:
        paysrc = paysrc.replace(old, new, 1)
        print("[OK] payments.py -> push_notification sur verify")
    PAY.write_text(paysrc, encoding="utf-8")

# Prescriptions
PRESC = MODULES / "prescriptions.py"
psrc = PRESC.read_text(encoding="utf-8")
if "push_notification" not in psrc:
    old = '''            conn.execute(
                "UPDATE orders SET prescription_status=? WHERE id=?",
                (st, p["order_id"]),
            )
            conn.commit()'''
    new = '''            conn.execute(
                "UPDATE orders SET prescription_status=? WHERE id=?",
                (st, p["order_id"]),
            )
            try:
                from v3_modules.notifications import push_notification
                o = conn.execute("SELECT user_id, reference FROM orders WHERE id=?",
                                 (p["order_id"],)).fetchone()
                if o and o["user_id"]:
                    labels = {
                        "APPROVED": "Ordonnance approuvee",
                        "REJECTED": "Ordonnance refusee",
                        "NEEDS_REVIEW": "Ordonnance a renvoyer",
                    }
                    push_notification(
                        conn, o["user_id"],
                        labels.get(st, "Ordonnance mise a jour"),
                        "Commande " + (o["reference"] or "") + " : " + st,
                        order_id=p["order_id"],
                    )
            except Exception:
                pass
            conn.commit()'''
    if old in psrc:
        psrc = psrc.replace(old, new, 1)
        print("[OK] prescriptions.py -> push_notification sur review")
    PRESC.write_text(psrc, encoding="utf-8")

# Deliveries
DELIV = MODULES / "deliveries.py"
dsrc = DELIV.read_text(encoding="utf-8")
if "push_notification" not in dsrc:
    old = '''            conn.execute("UPDATE orders SET delivery_status=? WHERE id=?", (st, d["order_id"]))
            conn.commit()'''
    new = '''            conn.execute("UPDATE orders SET delivery_status=? WHERE id=?", (st, d["order_id"]))
            try:
                from v3_modules.notifications import push_notification
                o = conn.execute("SELECT user_id, reference FROM orders WHERE id=?",
                                 (d["order_id"],)).fetchone()
                if o and o["user_id"]:
                    labels = {
                        "ACCEPTED": "Livreur en route",
                        "PICKED_UP": "Commande recuperee",
                        "IN_DELIVERY": "En cours de livraison",
                        "DELIVERED": "Commande livree",
                        "FAILED": "Livraison echouee",
                    }
                    push_notification(
                        conn, o["user_id"],
                        labels.get(st, "Livraison mise a jour"),
                        "Commande " + (o["reference"] or "") + " : " + st,
                        order_id=d["order_id"],
                    )
            except Exception:
                pass
            conn.commit()'''
    if old in dsrc:
        dsrc = dsrc.replace(old, new, 1)
        print("[OK] deliveries.py -> push_notification sur status")
    DELIV.write_text(dsrc, encoding="utf-8")

# Order status (main.py : update_order_status)
if "push_notification" not in src and "def update_order_status" in src:
    old = '''    conn.execute("UPDATE orders SET status = ? WHERE reference = ?", (new_status, reference))
    conn.commit()'''
    new = '''    conn.execute("UPDATE orders SET status = ? WHERE reference = ?", (new_status, reference))
    try:
        from v3_modules.notifications import push_notification
        if row["user_id"]:
            push_notification(
                conn, row["user_id"],
                "Commande mise a jour",
                "Votre commande " + reference + " : " + new_status,
                order_id=row["id"],
            )
    except Exception:
        pass
    conn.commit()'''
    if old in src:
        src = src.replace(old, new, 1)
        print("[OK] main.py -> push_notification sur update_order_status")
    MAIN.write_text(src, encoding="utf-8")

# ============================================================
# 4. HEADER : sticky + lien Suivi + SSE
# ============================================================
# Forcer topbar sticky
MOBILE = STATIC / "mobile.css"
css = MOBILE.read_text(encoding="utf-8")
if "STICKY HEADER FORCE" not in css:
    css = css.replace(
        "/* ============================================================\n   Elokinab Health - Mobile strict (anti-debordement)",
        """/* STICKY HEADER FORCE */
.topbar, .eh-mini-bar{
  position: sticky !important;
  top: 0 !important;
  z-index: 100 !important;
  background: #fff !important;
  box-shadow: 0 2px 8px rgba(15,38,32,.06) !important;
}

/* ============================================================
   Elokinab Health - Mobile strict (anti-debordement)""",
        1,
    )
    MOBILE.write_text(css, encoding="utf-8")
    print("[OK] mobile.css -> sticky header force")

# ============================================================
# 5. HEADER.js : ajouter lien Suivi + connexion SSE
# ============================================================
HJ = STATIC / "header.js"
js = HJ.read_text(encoding="utf-8")

# Ajouter un lien "Suivre" visible en permanence dans la barre
old_build = '''  function buildUserActions(user, cartCount, notifCount) {
    var wrap = el("div", "eh-user-actions");

    if (user) {'''
new_build = '''  function buildUserActions(user, cartCount, notifCount) {
    var wrap = el("div", "eh-user-actions");

    // Lien Suivi toujours visible
    var track = el("a", "eh-icon-btn");
    track.href = "/suivi";
    track.title = "Suivre ma commande";
    track.innerHTML = "\\uD83D\\uDCE6";
    wrap.appendChild(track);

    if (user) {'''
if old_build in js and "track.href = \"/suivi\"" not in js:
    js = js.replace(old_build, new_build, 1)
    HJ.write_text(js, encoding="utf-8")
    print("[OK] header.js -> lien Suivi dans le header")

# Ajouter la connexion SSE
SSE_CLIENT = '''
  // ===== Notifications temps reel (SSE) =====
  var _sse = null;
  function connectSSE() {
    if (_sse) return;
    if (typeof EventSource === "undefined") return;
    try {
      _sse = new EventSource("/api/notifications/stream", { withCredentials: true });
    } catch (e) { _sse = null; return; }

    _sse.addEventListener("message", function (ev) {
      try {
        var data = JSON.parse(ev.data);
        // Mise a jour badge
        if (window.EHHeader && window.EHHeader.bumpNotifBadge) {
          window.EHHeader.bumpNotifBadge(1);
        }
        // Toast visuel
        showToast(data.title, data.body, data.order_id);
      } catch (e) {}
    });

    _sse.onerror = function () {
      if (_sse) { try { _sse.close(); } catch (e) {} _sse = null; }
      setTimeout(connectSSE, 5000); // reconnexion auto apres 5s
    };
  }

  function showToast(title, body, orderId) {
    var t = document.createElement("div");
    t.className = "eh-toast";
    t.innerHTML =
      '<div class="eh-toast-title">' + (title || "Notification") + '</div>' +
      '<div class="eh-toast-body">' + (body || "") + '</div>';
    if (orderId) {
      t.style.cursor = "pointer";
      t.addEventListener("click", function () {
        window.location.href = "/suivi?ref=" + encodeURIComponent(orderId);
      });
    }
    document.body.appendChild(t);
    // Auto-dismiss
    setTimeout(function () {
      t.classList.add("eh-toast-out");
      setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 400);
    }, 7000);
  }
'''

# Injecter juste avant "  if (document.readyState === \"loading\") {"
anchor = '  if (document.readyState === "loading") {'
if anchor in js and "connectSSE" not in js:
    js = js.replace(anchor, SSE_CLIENT + "\n" + anchor, 1)

    # Brancher au chargement
    inject_anchor = "  if (document.readyState === \"loading\") {\n    document.addEventListener(\"DOMContentLoaded\", inject);\n  } else {\n    inject();\n  }"
    inject_new = """  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      inject();
      setTimeout(connectSSE, 800);
    });
  } else {
    inject();
    setTimeout(connectSSE, 800);
  }"""
    if inject_anchor in js:
        js = js.replace(inject_anchor, inject_new, 1)
        print("[OK] header.js -> SSE connect")
    else:
        print("[!] anchor DOMContentLoaded introuvable, SSE connect manuel")

    HJ.write_text(js, encoding="utf-8")

# Ajouter bumpNotifBadge dans l'API publique EHHeader
if "bumpNotifBadge" not in HJ.read_text(encoding="utf-8"):
    js = HJ.read_text(encoding="utf-8")
    old_api = '''    updateNotifBadge: function (count) {
      var nodes = document.querySelectorAll(".eh-notif-count");
      Array.prototype.forEach.call(nodes, function (b) {
        if (count > 0) {
          b.textContent = count > 99 ? "99+" : String(count);
          b.classList.remove("hidden");
        } else {
          b.classList.add("hidden");
        }
      });
    }'''
    new_api = old_api + ''',
    bumpNotifBadge: function (delta) {
      var nodes = document.querySelectorAll(".eh-notif-count");
      Array.prototype.forEach.call(nodes, function (b) {
        var cur = parseInt(b.textContent) || 0;
        if (b.classList.contains("hidden")) cur = 0;
        var n = Math.max(0, cur + (delta || 1));
        if (n > 0) {
          b.textContent = n > 99 ? "99+" : String(n);
          b.classList.remove("hidden");
        } else {
          b.classList.add("hidden");
        }
      });
    }'''
    if old_api in js:
        js = js.replace(old_api, new_api, 1)
        HJ.write_text(js, encoding="utf-8")
        print("[OK] header.js -> bumpNotifBadge")

# ============================================================
# 6. CSS toast notifications
# ============================================================
HC = STATIC / "header.css"
hcss = HC.read_text(encoding="utf-8")
if ".eh-toast" not in hcss:
    hcss += '''
/* --- Toast notifications temps reel --- */
.eh-toast{
  position: fixed;
  top: 70px;
  left: 12px;
  right: 12px;
  background: #fff;
  border: 1px solid #0f9d76;
  border-left: 4px solid #0f9d76;
  border-radius: 12px;
  padding: 12px 14px;
  box-shadow: 0 12px 30px rgba(15,38,32,.18);
  z-index: 9999;
  animation: eh-toast-in .25s ease-out;
  max-width: 420px;
  margin: 0 auto;
}
.eh-toast-title{
  font-weight: 800;
  font-size: 14px;
  color: #0f2620;
  margin-bottom: 3px;
}
.eh-toast-body{
  font-size: 13px;
  color: #6c8a80;
  line-height: 1.4;
}
.eh-toast-out{
  animation: eh-toast-out .3s ease-in forwards;
}
@keyframes eh-toast-in {
  from { opacity:0; transform: translateY(-10px); }
  to { opacity:1; transform: translateY(0); }
}
@keyframes eh-toast-out {
  from { opacity:1; transform: translateY(0); }
  to { opacity:0; transform: translateY(-10px); }
}
'''
    HC.write_text(hcss, encoding="utf-8")
    print("[OK] header.css -> styles toast")

# ============================================================
# 7. CHECKOUT plein ecran sur mobile
# ============================================================
css = MOBILE.read_text(encoding="utf-8")
if "CHECKOUT FULLSCREEN MOBILE" not in css:
    css += '''

/* CHECKOUT FULLSCREEN MOBILE */
@media (max-width: 720px){
  body.checkout-open{overflow:hidden;position:fixed;width:100%}
  #checkout-panel{
    position: fixed !important;
    inset: 0 !important;
    z-index: 300 !important;
    margin: 0 !important;
    border-radius: 0 !important;
    overflow-y: auto !important;
    max-height: 100vh !important;
    padding: 60px 16px 100px 16px !important;
    box-shadow: none !important;
    background: #fff !important;
  }
  #checkout-panel .co-fixed-head{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background: #fff;
    border-bottom: 1px solid #ddece6;
    padding: 12px 16px;
    z-index: 301;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  #checkout-panel .co-fixed-head h2{
    flex: 1;
    margin: 0;
    font-size: 16px;
  }
  #checkout-panel .co-fixed-head button{
    background: none;
    border: 0;
    font-size: 24px;
    line-height: 1;
    color: #6c8a80;
    cursor: pointer;
    padding: 4px 8px;
  }
  #checkout-panel .co-fixed-foot{
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: #fff;
    border-top: 1px solid #ddece6;
    padding: 12px 16px;
    z-index: 301;
    display: flex;
    gap: 10px;
  }
  #checkout-panel .co-fixed-foot .auth-btn{flex: 1;padding: 14px;}
}
'''
    MOBILE.write_text(css, encoding="utf-8")
    print("[OK] mobile.css -> checkout fullscreen")

# ============================================================
# 8. cart.html : ajouter les blocs co-fixed-head/foot
# ============================================================
CART_HTML = STATIC / "cart.html"
html = CART_HTML.read_text(encoding="utf-8")
if "co-fixed-head" not in html:
    # Remplacer le <h2> actuel par un header sticky
    old_h2 = '''    <h2 style="margin:0 0 6px;font-size:17px">Finaliser la commande</h2>
    <p class="muted small" style="margin:0 0 10px">Verifiez les produits puis choisissez le mode.</p>'''
    new_h2 = '''    <div class="co-fixed-head">
      <h2>Finaliser la commande</h2>
      <button type="button" id="co-close" aria-label="Fermer">&#10005;</button>
    </div>
    <p class="muted small" style="margin:0 0 10px">Verifiez les produits puis choisissez le mode.</p>'''
    if old_h2 in html:
        html = html.replace(old_h2, new_h2, 1)
    else:
        # Insere en debut de checkout-panel
        html = html.replace('<div id="checkout-panel" class="checkout-card hidden">',
                            '<div id="checkout-panel" class="checkout-card hidden">\n    <div class="co-fixed-head"><h2>Finaliser la commande</h2><button type="button" id="co-close" aria-label="Fermer">&#10005;</button></div>', 1)
        print("[i] cart.html -> co-fixed-head insere en tete")

    # Envelopper les actions dans un fixed-foot
    old_actions = '''    <div id="co-error" class="auth-msg hidden"></div>
    <div class="checkout-actions">
      <button type="button" class="auth-btn" id="co-cancel" style="background:#6c8a80">Annuler</button>
      <button type="button" class="auth-btn" id="co-confirm">Confirmer la commande</button>
    </div>'''
    new_actions = '''    <div id="co-error" class="auth-msg hidden"></div>
    <div class="checkout-actions co-fixed-foot">
      <button type="button" class="auth-btn" id="co-cancel" style="background:#6c8a80">Annuler</button>
      <button type="button" class="auth-btn" id="co-confirm">Confirmer la commande</button>
    </div>'''
    if old_actions in html:
        html = html.replace(old_actions, new_actions, 1)
        print("[OK] cart.html -> co-fixed-foot")

    CART_HTML.write_text(html, encoding="utf-8")

# ============================================================
# 9. cart.js : gerer l'ouverture/fermeture plein ecran + blocage scroll
# ============================================================
CART_JS = STATIC / "cart.js"
js = CART_JS.read_text(encoding="utf-8")

# openCheckout : ajouter class au body
old_open = '''  function openCheckout() {
    if (state.subtotal === 0) { showMsg("Panier vide"); return; }
    $("checkout-panel").classList.remove("hidden");
    $("checkout-panel").scrollIntoView({ behavior: "smooth" });'''
new_open = '''  function openCheckout() {
    if (state.subtotal === 0) { showMsg("Panier vide"); return; }
    $("checkout-panel").classList.remove("hidden");
    document.body.classList.add("checkout-open");
    window.scrollTo(0, 0);'''
if old_open in js:
    js = js.replace(old_open, new_open, 1)

# closeCheckout helper
if "function closeCheckout" not in js:
    close_fn = '''
  function closeCheckout() {
    var p = $("checkout-panel");
    if (p) p.classList.add("hidden");
    document.body.classList.remove("checkout-open");
  }
'''
    js = js.replace("  function selectMode(mode) {",
                    close_fn + "\n  function selectMode(mode) {", 1)

# Remplacer les endroits qui ajoutent "hidden" par closeCheckout
js = js.replace(
    '''    if ($("co-cancel")) $("co-cancel").addEventListener("click", function () {
      $("checkout-panel").classList.add("hidden");
    });''',
    '''    if ($("co-cancel")) $("co-cancel").addEventListener("click", closeCheckout);
    if ($("co-close")) $("co-close").addEventListener("click", closeCheckout);''',
    1,
)

# Fermer le checkout apres redirect paiement (deja fait par location.href, mais au cas ou)
# Fermer au submit reussi (deja fait)

CART_JS.write_text(js, encoding="utf-8")
print("[OK] cart.js -> plein ecran + fermeture")

print()
print("=" * 60)
print("HEADER STICKY + SUIVI + NOTIFS TEMPS REEL + CHECKOUT PLEIN ECRAN")
print("=" * 60)
print()
print("Nouveautes :")
print("  1. Header sticky partout (reste visible en scrollant)")
print("  2. Icone Suivi dans le header (toujours visible)")
print("  3. Notifications temps reel via SSE")
print("     - Un toast apparait a l'ecran")
print("     - Le badge 🔔 s'incremente automatiquement")
print("     - Rafraichissement auto toutes les 3s cote serveur")
print("  4. Checkout mobile en plein ecran (plus de scroll infini)")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  python main.py")
print("  Ctrl+Shift+R sur l'iPhone (ou navigation privee)")