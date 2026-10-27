"""
v3_install_pro_features.py
- WhatsApp number configurable + bouton liste WhatsApp
- Reorder (recharger dernier panier depuis une commande existante)
"""
from pathlib import Path
import datetime
import shutil
import sqlite3

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
MODULES = BASE / "v3_modules"
STATIC = BASE / "static"
DB = BASE / "database.db"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_pro_features_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(DB, backup / "database.db")
shutil.copy2(MAIN, backup / "main.py")
for f in ("professional.html", "professional.js", "cart.js", "pharmacien.html", "pharmacien.js", "suivi.js", "suivi.html"):
    p = STATIC / f
    if p.exists():
        shutil.copy2(p, backup / f)
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. Ajouter colonne whatsapp_number dans pharmacy_settings
# ============================================================
conn = sqlite3.connect(DB)
cur = conn.cursor()
cols = {r[1] for r in cur.execute("PRAGMA table_info(pharmacy_settings)").fetchall()}
if "whatsapp_number" not in cols:
    cur.execute("ALTER TABLE pharmacy_settings ADD COLUMN whatsapp_number TEXT DEFAULT ''")
    conn.commit()
    print("[OK] pharmacy_settings -> whatsapp_number ajoute")
else:
    print("[i] whatsapp_number deja present")
conn.close()

# ============================================================
# 2. Module reorder + whatsapp helper
# ============================================================
PRO_FEATURES = '''"""Fonctionnalites pro : WhatsApp + Reorder (V3 extension)."""
from datetime import datetime

from fastapi import Depends, HTTPException


def _row(r):
    return {k: r[k] for k in r.keys()} if r else None


def _get_or_create_cart(conn, user_id):
    row = conn.execute("SELECT * FROM carts WHERE user_id = ?", (user_id,)).fetchone()
    if row:
        return row
    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        "INSERT INTO carts (user_id, created_at, updated_at) VALUES (?, ?, ?)",
        (user_id, now, now),
    )
    conn.commit()
    return conn.execute("SELECT * FROM carts WHERE id = ?", (cur.lastrowid,)).fetchone()


def install_pro_features(app, get_db, require_role):
    """Enregistre les routes /api/pro/whatsapp-info et /api/orders/{ref}/reorder."""

    @app.get("/api/pro/whatsapp-info")
    def whatsapp_info(user=Depends(require_role("PROFESSIONNEL", "PATIENT", "ADMIN", "PHARMACIEN"))):
        """Retourne le numero WhatsApp config + le nom de la structure du user."""
        conn = get_db()
        try:
            settings = conn.execute(
                "SELECT pharmacy_name, whatsapp_number, phone FROM pharmacy_settings WHERE id = 1"
            ).fetchone()
            whatsapp = ""
            pharmacy_name = "Elokinab Health"
            if settings:
                whatsapp = (settings["whatsapp_number"] or "").strip()
                if not whatsapp:
                    whatsapp = (settings["phone"] or "").strip()
                if settings["pharmacy_name"]:
                    pharmacy_name = settings["pharmacy_name"]

            structure_name = ""
            if user["role"] == "PROFESSIONNEL":
                prof = conn.execute(
                    "SELECT structure_name FROM professional_profiles WHERE user_id = ?",
                    (user["id"],),
                ).fetchone()
                if prof:
                    structure_name = prof["structure_name"] or ""
            if not structure_name:
                structure_name = user.get("full_name") or ""
        finally:
            conn.close()
        return {
            "whatsapp_number": whatsapp,
            "pharmacy_name": pharmacy_name,
            "structure_name": structure_name,
        }

    @app.post("/api/orders/{reference}/reorder")
    def reorder(reference: str, user=Depends(require_role("PATIENT", "PROFESSIONNEL"))):
        """Recharge le panier avec les produits d'une commande passee."""
        conn = get_db()
        try:
            order = conn.execute(
                "SELECT * FROM orders WHERE reference = ? AND user_id = ?",
                (reference, user["id"]),
            ).fetchone()
            if order is None:
                raise HTTPException(404, "Commande introuvable")

            # Recuperer les lignes
            items = conn.execute(
                "SELECT product_id, quantity FROM order_items WHERE order_id = ?",
                (order["id"],),
            ).fetchall()

            # Si pas d'order_items (commande V1), utiliser product_id direct
            if not items:
                if order["product_id"]:
                    items = [{"product_id": order["product_id"], "quantity": order["quantity"] or 1}]

            if not items:
                raise HTTPException(400, "Aucun produit dans cette commande")

            cart = _get_or_create_cart(conn, user["id"])
            now = datetime.now().isoformat(timespec="seconds")
            added = 0
            skipped = 0

            for it in items:
                pid = it["product_id"]
                qty = it["quantity"] or 1
                # Verifier produit actif et existant
                prod = conn.execute(
                    "SELECT id, is_active FROM products WHERE id = ?", (pid,)
                ).fetchone()
                if prod is None or prod["is_active"] == 0:
                    skipped += 1
                    continue

                existing = conn.execute(
                    "SELECT id, quantity FROM cart_items WHERE cart_id = ? AND product_id = ?",
                    (cart["id"], pid),
                ).fetchone()
                if existing:
                    conn.execute(
                        "UPDATE cart_items SET quantity = quantity + ?, updated_at = ?"
                        " WHERE id = ?",
                        (qty, now, existing["id"]),
                    )
                else:
                    conn.execute(
                        "INSERT INTO cart_items (cart_id, product_id, quantity,"
                        " created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                        (cart["id"], pid, qty, now, now),
                    )
                added += 1

            conn.execute("UPDATE carts SET updated_at = ? WHERE id = ?", (now, cart["id"]))
            conn.commit()

            # Retourner le panier a jour
            cart_data = conn.execute(
                "SELECT ci.id, ci.product_id, ci.quantity, p.name AS product_name,"
                " p.presentation, p.price, (ci.quantity * p.price) AS line_total"
                " FROM cart_items ci JOIN products p ON p.id = ci.product_id"
                " WHERE ci.cart_id = ? ORDER BY ci.id",
                (cart["id"],),
            ).fetchall()
            items_list = [_row(i) for i in cart_data]
            subtotal = sum((i["line_total"] or 0) for i in items_list)
        finally:
            conn.close()

        return {
            "added": added,
            "skipped": skipped,
            "cart": {
                "items": items_list,
                "item_count": sum(i["quantity"] for i in items_list),
                "subtotal": round(subtotal, 2),
            },
        }


'''
(MODULES / "pro_features.py").write_text(PRO_FEATURES, encoding="utf-8")
print("[OK] v3_modules/pro_features.py")

# ============================================================
# 3. Patch main.py : brancher pro_features
# ============================================================
src = MAIN.read_text(encoding="utf-8")
if "install_pro_features" not in src:
    old = "install_admin(app, get_db, require_role)"
    new = (old + "\n"
           "from v3_modules.pro_features import install_pro_features\n"
           "install_pro_features(app, get_db, require_role)")
    if old in src:
        src = src.replace(old, new, 1)
        MAIN.write_text(src, encoding="utf-8")
        print("[OK] main.py -> install_pro_features branche")
    else:
        print("[!] anchor install_admin introuvable")
else:
    print("[i] main.py deja patche")

# ============================================================
# 4. API settings : accepter whatsapp_number
# ============================================================
src = MAIN.read_text(encoding="utf-8")
old_model = '''class SettingsUpdate(BaseModel):
    delivery_fee_default: Optional[float] = None
    pharmacy_latitude: Optional[float] = None
    pharmacy_longitude: Optional[float] = None
    delivery_base_fee: Optional[float] = None
    delivery_price_per_km: Optional[float] = None
    delivery_max_km: Optional[float] = None
'''
new_model = '''class SettingsUpdate(BaseModel):
    delivery_fee_default: Optional[float] = None
    pharmacy_latitude: Optional[float] = None
    pharmacy_longitude: Optional[float] = None
    delivery_base_fee: Optional[float] = None
    delivery_price_per_km: Optional[float] = None
    delivery_max_km: Optional[float] = None
    motorbike_base_fee: Optional[float] = None
    motorbike_price_per_km: Optional[float] = None
    motorbike_minimum_fee: Optional[float] = None
    car_base_fee: Optional[float] = None
    car_price_per_km: Optional[float] = None
    car_minimum_fee: Optional[float] = None
    payment_number: Optional[str] = None
    payment_name: Optional[str] = None
    pharmacy_name: Optional[str] = None
    pharmacy_phone: Optional[str] = None
    pharmacy_address: Optional[str] = None
    whatsapp_number: Optional[str] = None
'''
if old_model in src and "whatsapp_number" not in src:
    src = src.replace(old_model, new_model, 1)
    MAIN.write_text(src, encoding="utf-8")
    print("[OK] main.py -> SettingsUpdate etendu (whatsapp_number)")
else:
    print("[i] SettingsUpdate deja etendu ou introuvable")

# ============================================================
# 5. professional.html : ajouter les 2 boutons
# ============================================================
PRO_HTML = STATIC / "professional.html"
html = PRO_HTML.read_text(encoding="utf-8")

block = '''  <div class="pro-actions">
    <button type="button" class="pro-action-btn wa" id="wa-btn">
      <span class="pro-action-icon">&#128242;</span>
      <span class="pro-action-text">
        <strong>Envoyer ma liste WhatsApp</strong>
        <small>Commander rapidement via WhatsApp</small>
      </span>
    </button>
    <button type="button" class="pro-action-btn reorder" id="reorder-btn">
      <span class="pro-action-icon">&#128257;</span>
      <span class="pro-action-text">
        <strong>Recommander ma derniere commande</strong>
        <small>Recharger le panier en 1 clic</small>
      </span>
    </button>
  </div>

  <div id="wa-modal" class="pro-modal hidden">
    <div class="pro-modal-backdrop" data-close-wa></div>
    <div class="pro-modal-content">
      <header class="pro-modal-head">
        <h3>&#128242; Liste WhatsApp</h3>
        <button type="button" class="pro-modal-close" data-close-wa>&times;</button>
      </header>
      <div class="pro-modal-body">
        <p class="muted small">Modifiez la liste ci-dessous, puis cliquez sur "Ouvrir WhatsApp".</p>
        <textarea id="wa-text" rows="12" placeholder="Votre liste de produits..."></textarea>
        <div id="wa-info" class="muted small"></div>
      </div>
      <footer class="pro-modal-foot">
        <button type="button" class="btn btn-ghost" data-close-wa>Annuler</button>
        <button type="button" class="btn btn-primary" id="wa-send">Ouvrir WhatsApp</button>
      </footer>
    </div>
  </div>

'''

anchor = '<button class="auth-btn" id="btn" type="submit">Enregistrer mon profil</button>'
if anchor in html and "pro-actions" not in html:
    html = html.replace(anchor, anchor + "\n\n" + block, 1)
    PRO_HTML.write_text(html, encoding="utf-8")
    print("[OK] professional.html -> boutons + modal WA")
elif "pro-actions" in html:
    print("[i] professional.html deja patche")
else:
    print("[!] anchor bouton Enregistrer introuvable")

# Ajouter styles
STYLE = '''<style>
  .pro-actions{
    display:flex;flex-direction:column;gap:10px;margin:20px 0;
  }
  .pro-action-btn{
    display:flex;align-items:center;gap:14px;
    padding:14px 16px;border-radius:14px;border:1px solid #ddece6;
    background:#fff;cursor:pointer;font-family:inherit;text-align:left;
    transition:.15s;width:100%;
  }
  .pro-action-btn:hover{border-color:#0f9d76;box-shadow:0 4px 14px rgba(15,157,118,.1)}
  .pro-action-btn.wa{background:linear-gradient(135deg,#e8f7f1,#d6efe6);border-color:#c7e9dc}
  .pro-action-btn.reorder{background:linear-gradient(135deg,#f4f0ff,#e9e0ff);border-color:#d6c8ff}
  .pro-action-icon{
    font-size:26px;line-height:1;
    width:46px;height:46px;border-radius:12px;
    display:flex;align-items:center;justify-content:center;
    background:#fff;flex-shrink:0;
  }
  .pro-action-text{display:flex;flex-direction:column;gap:2px;flex:1;min-width:0}
  .pro-action-text strong{font-size:14px;color:#0f2620}
  .pro-action-text small{font-size:12px;color:#6c8a80}

  .pro-modal{
    position:fixed;inset:0;z-index:200;
    display:flex;align-items:center;justify-content:center;
    padding:14px;
  }
  .pro-modal.hidden{display:none}
  .pro-modal-backdrop{position:absolute;inset:0;background:rgba(15,38,32,.45)}
  .pro-modal-content{
    position:relative;background:#fff;border-radius:16px;
    width:100%;max-width:520px;max-height:90vh;display:flex;flex-direction:column;
    box-shadow:0 20px 60px rgba(15,38,32,.25);overflow:hidden;
  }
  .pro-modal-head{
    display:flex;align-items:center;justify-content:space-between;
    padding:14px 18px;border-bottom:1px solid #ddece6;
  }
  .pro-modal-head h3{margin:0;font-size:16px}
  .pro-modal-close{background:none;border:0;font-size:24px;line-height:1;color:#6c8a80;cursor:pointer;padding:0 4px}
  .pro-modal-body{padding:14px 18px;overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:10px}
  .pro-modal-body textarea{
    width:100%;padding:12px 14px;border:1px solid #ddece6;border-radius:11px;
    font-family:inherit;font-size:14px;resize:vertical;outline:none;box-sizing:border-box;
  }
  .pro-modal-body textarea:focus{border-color:#0f9d76}
  .pro-modal-foot{
    display:flex;gap:10px;padding:14px 18px;border-top:1px solid #ddece6;
    background:#f4faf7;
  }
  .pro-modal-foot .btn{flex:1;padding:12px;font-size:14px}
</style>
'''
if "pro-actions" in html and ".pro-actions{" not in html:
    html = html.replace("</head>", STYLE + "</head>", 1)
    PRO_HTML.write_text(html, encoding="utf-8")
    print("[OK] professional.html -> styles ajoutes")

# ============================================================
# 6. professional.js : logique WhatsApp + reorder
# ============================================================
PRO_JS = STATIC / "professional.js"
pjs = PRO_JS.read_text(encoding="utf-8")

wa_js = '''

// ===== WhatsApp list =====
(function () {
  function $(id) { return document.getElementById(id); }

  var state = { whatsapp: "", structure: "", pharmacy: "Elokinab Health" };

  function openModal() {
    var m = $("wa-modal");
    if (!m) return;
    m.classList.remove("hidden");
    document.body.style.overflow = "hidden";
  }
  function closeModal() {
    var m = $("wa-modal");
    if (!m) return;
    m.classList.add("hidden");
    document.body.style.overflow = "";
  }

  function buildDefaultList() {
    return [
      "Bonjour " + state.pharmacy + " \\uD83D\\uDC4B",
      "",
      "Nous souhaitons passer une commande pour notre structure.",
      "",
      "\\uD83C\\uDFE5 Structure : " + (state.structure || "................"),
      "",
      "\\uD83D\\uDCCB Liste :",
      "- ................... (quantite)",
      "- ................... (quantite)",
      "- ................... (quantite)",
      "",
      "Merci de nous confirmer la disponibilite, les prix et le delai de livraison."
    ].join("\\n");
  }

  function loadInfo() {
    fetch("/api/pro/whatsapp-info", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) return;
        state.whatsapp = d.whatsapp_number || "";
        state.structure = d.structure_name || "";
        state.pharmacy = d.pharmacy_name || "Elokinab Health";
        var info = $("wa-info");
        if (info) {
          if (state.whatsapp) {
            info.textContent = "Destinataire WhatsApp : " + state.whatsapp;
          } else {
            info.textContent = "Numero WhatsApp non configure par la pharmacie. Contactez la pharmacie.";
          }
        }
      });
  }

  function send() {
    if (!state.whatsapp) {
      alert("La pharmacie n'a pas encore configure son numero WhatsApp.");
      return;
    }
    var phone = String(state.whatsapp).replace(/\\D/g, "");
    if (!phone) { alert("Numero WhatsApp invalide"); return; }
    var msg = $("wa-text").value || "";
    var url = "https://wa.me/" + phone + "?text=" + encodeURIComponent(msg);
    window.open(url, "_blank");
    closeModal();
  }

  document.addEventListener("DOMContentLoaded", function () {
    var openBtn = $("wa-btn");
    if (openBtn) {
      openBtn.addEventListener("click", function () {
        var ta = $("wa-text");
        if (ta && !ta.value) ta.value = buildDefaultList();
        loadInfo();
        openModal();
      });
    }
    var closeEls = document.querySelectorAll("[data-close-wa]");
    Array.prototype.forEach.call(closeEls, function (b) {
      b.addEventListener("click", closeModal);
    });
    var sendBtn = $("wa-send");
    if (sendBtn) sendBtn.addEventListener("click", send);

    // ===== Reorder =====
    var reorderBtn = $("reorder-btn");
    if (reorderBtn) {
      reorderBtn.addEventListener("click", function () {
        reorderBtn.disabled = true;
        var orig = reorderBtn.querySelector(".pro-action-text strong");
        var oldTxt = orig ? orig.textContent : "";
        if (orig) orig.textContent = "Recherche...";

        fetch("/api/orders/mine", { credentials: "same-origin" })
          .then(function (r) { return r.ok ? r.json() : []; })
          .then(function (list) {
            if (!list || list.length === 0) {
              alert("Aucune commande precedente.");
              reorderBtn.disabled = false;
              if (orig) orig.textContent = oldTxt;
              return;
            }
            var ref = list[0].reference;
            return fetch("/api/orders/" + encodeURIComponent(ref) + "/reorder", {
              method: "POST", credentials: "same-origin"
            }).then(function (r) {
              return r.json().then(function (d) {
                if (!r.ok) throw new Error(d.detail || "Erreur");
                return d;
              });
            }).then(function (d) {
              alert(d.added + " produit(s) ajoute(s) au panier." +
                    (d.skipped > 0 ? " " + d.skipped + " indisponible(s)." : ""));
              window.location.href = "/static/cart.html";
            });
          })
          .catch(function (e) {
            alert(e.message || "Erreur");
            reorderBtn.disabled = false;
            if (orig) orig.textContent = oldTxt;
          });
      });
    }
  });
})();
'''

if "wa-btn" not in pjs and "WhatsApp list" not in pjs:
    pjs = pjs + wa_js
    PRO_JS.write_text(pjs, encoding="utf-8")
    print("[OK] professional.js -> WhatsApp + reorder")
else:
    print("[i] professional.js deja patche")

# ============================================================
# 7. pharmacien : parametre WhatsApp dans la section settings
# ============================================================
PH_HTML = STATIC / "pharmacien.html"
phtml = PH_HTML.read_text(encoding="utf-8")

wa_field = '''      <h3 class="settings-sub">Contact WhatsApp (pour commandes pro)</h3>
      <div class="settings-row">
        <input type="tel" id="whatsapp-input" placeholder="+228 90 00 00 00" class="settings-input-wide">
        <span class="muted small">Numero WhatsApp au format international</span>
      </div>

'''
anchor_wa = '<h3 class="settings-sub">Tarification</h3>'
if anchor_wa in phtml and "whatsapp-input" not in phtml:
    phtml = phtml.replace(anchor_wa, wa_field + anchor_wa, 1)
    PH_HTML.write_text(phtml, encoding="utf-8")
    print("[OK] pharmacien.html -> champ WhatsApp")

# pharmacien.js : charger et sauvegarder whatsapp_number
PH_JS = STATIC / "pharmacien.js"
phjs = PH_JS.read_text(encoding="utf-8")

# Patch loadSettingsDashboard
old_load = '''    setVal("ph-lat-input", s.pharmacy_latitude, 5);
    setVal("ph-lon-input", s.pharmacy_longitude, 5);'''
new_load = '''    setVal("ph-lat-input", s.pharmacy_latitude, 5);
    setVal("ph-lon-input", s.pharmacy_longitude, 5);
    var waEl = document.getElementById("whatsapp-input");
    if (waEl) waEl.value = s.whatsapp_number || "";'''
if old_load in phjs and "whatsapp-input" not in phjs:
    phjs = phjs.replace(old_load, new_load, 1)

# Patch submitSettings
old_payload = '''  var payload = {
    delivery_fee_default: num("fallback-fee-input"),
    delivery_base_fee: num("base-fee-input"),
    delivery_price_per_km: num("per-km-input"),
    delivery_max_km: num("max-km-input"),
    pharmacy_latitude: num("ph-lat-input"),
    pharmacy_longitude: num("ph-lon-input")
  };'''
new_payload = '''  var payload = {
    delivery_fee_default: num("fallback-fee-input"),
    delivery_base_fee: num("base-fee-input"),
    delivery_price_per_km: num("per-km-input"),
    delivery_max_km: num("max-km-input"),
    pharmacy_latitude: num("ph-lat-input"),
    pharmacy_longitude: num("ph-lon-input")
  };
  var waEl = document.getElementById("whatsapp-input");
  if (waEl) payload.whatsapp_number = String(waEl.value || "").trim();'''
if old_payload in phjs and "whatsapp_number" not in phjs:
    phjs = phjs.replace(old_payload, new_payload, 1)
    PH_JS.write_text(phjs, encoding="utf-8")
    print("[OK] pharmacien.js -> whatsapp charge/sauvegarde")
else:
    PH_JS.write_text(phjs, encoding="utf-8")

# ============================================================
# 8. suivi : ajouter bouton recommander
# ============================================================
SUIVI_JS = STATIC / "suivi.js"
sjs = SUIVI_JS.read_text(encoding="utf-8")

reorder_js = '''

// ===== Reorder depuis le suivi =====
(function () {
  function $(id) { return document.getElementById(id); }

  document.addEventListener("DOMContentLoaded", function () {
    var btn = $("track-reorder");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var ref = btn.getAttribute("data-ref");
      if (!ref) return;
      btn.disabled = true;
      var old = btn.textContent;
      btn.textContent = "Rechargement...";
      fetch("/api/orders/" + encodeURIComponent(ref) + "/reorder", {
        method: "POST", credentials: "same-origin"
      })
        .then(function (r) { return r.json().then(function (d) {
          if (!r.ok) throw new Error(d.detail || "Erreur");
          return d;
        }); })
        .then(function (d) {
          alert(d.added + " produit(s) ajoute(s) au panier.");
          window.location.href = "/static/cart.html";
        })
        .catch(function (e) {
          alert(e.message);
          btn.disabled = false;
          btn.textContent = old;
        });
    });
  });
})();
'''
if "track-reorder" not in sjs:
    sjs = sjs + reorder_js
    # Brancher : injecter le bouton dans le rendu detail
    old_track = '''  var payBtn = $("#track-pay");'''
    new_track = '''  // Bouton Reorder
  var existing = $("#track-reorder");
  if (!existing) {
    var ro = document.createElement("button");
    ro.type = "button";
    ro.id = "track-reorder";
    ro.className = "btn btn-ghost";
    ro.textContent = "\\uD83D\\uDD01 Recommander";
    ro.style.marginLeft = "8px";
    var actions = document.querySelector(".track-actions");
    if (actions) actions.appendChild(ro);
  }
  var roBtn = $("#track-reorder");
  if (roBtn) roBtn.setAttribute("data-ref", o.reference);

  var payBtn = $("#track-pay");'''
    if old_track in sjs:
        sjs = sjs.replace(old_track, new_track, 1)
    SUIVI_JS.write_text(sjs, encoding="utf-8")
    print("[OK] suivi.js -> bouton Recommander")
else:
    print("[i] suivi.js deja patche")

print()
print("=" * 60)
print("FONCTIONNALITES PRO INSTALLEES")
print("=" * 60)
print()
print("Nouveautes :")
print("  1. Parametre whatsapp_number dans pharmacy_settings")
print("  2. Champ WhatsApp dans /pharmacien > Parametres")
print("  3. Bouton 'Envoyer ma liste WhatsApp' sur /static/professional.html")
print("  4. Bouton 'Recommander ma derniere commande' sur /static/professional.html")
print("  5. Bouton 'Recommander' sur /suivi")
print("  6. API POST /api/orders/{ref}/reorder")
print("  7. API GET /api/pro/whatsapp-info")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print("  Ctrl+Shift+R sur iPhone")