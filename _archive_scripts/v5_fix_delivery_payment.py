"""
v5_fix_delivery_payment.py
1. Ajoute endpoint estimate-delivery (distance + frais VOITURE)
2. Modifie submit : cree directement un order + renvoie la ref
3. Frontend : affiche distance + frais + total, redirige vers paiement
"""
from pathlib import Path
import datetime
import re
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
MAIN = BASE / "main.py"
B2B = BASE / "v3_modules" / "b2b_requests.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_v5_fix_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAIN, backup / "main.py")
shutil.copy2(B2B, backup / "b2b_requests.py")
shutil.copy2(STATIC / "professional_demande_confirmer.js", backup / "professional_demande_confirmer.js")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. BACKEND : refonte complete de b2b_requests.py
# ============================================================
src = B2B.read_text(encoding="utf-8")

# 1.1 Ajouter helpers Haversine + compute delivery fee pro
helpers = '''

# ============================================================
# Helpers livraison (Haversine + tarifs VOITURE pour pros)
# ============================================================

def _haversine_km(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, asin, sqrt
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))


def _compute_delivery_fee_pro(conn, client_lat, client_lon):
    """Calcule le frais de livraison VOITURE pour un pro.
    Retourne (fee, distance_km, source) :
    - source = "gps" si calcul reussi
    - source = "fallback" si pas de GPS ou config manquante
    """
    s = conn.execute("SELECT * FROM pharmacy_settings WHERE id=1").fetchone()
    if s is None:
        return 0.0, None, "no_config"

    # Lire les valeurs avec fallback
    def get(key, default=0.0):
        try:
            v = s[key] if key in s.keys() else None
            return default if v is None else float(v)
        except Exception:
            return default

    ph_lat = None
    ph_lon = None
    try:
        if "pharmacy_latitude" in s.keys():
            ph_lat = s["pharmacy_latitude"]
        if "pharmacy_longitude" in s.keys():
            ph_lon = s["pharmacy_longitude"]
    except Exception:
        pass

    # Tarifs VOITURE (professionnels)
    base = get("car_base_fee", 1000.0)
    per_km = get("car_price_per_km", 250.0)
    min_fee = get("car_minimum_fee", 1000.0)

    if client_lat is None or client_lon is None:
        # Pas de GPS : fallback sur delivery_fee_default
        return get("delivery_fee_default", 1000.0), None, "no_gps"

    if ph_lat is None or ph_lon is None:
        # Position pharmacie pas configuree
        return get("delivery_fee_default", 1000.0), None, "no_pharmacy"

    dist = _haversine_km(float(ph_lat), float(ph_lon), float(client_lat), float(client_lon))
    fee = base + dist * per_km
    if fee < min_fee:
        fee = min_fee
    # Arrondi aux 50 F
    fee = round(fee / 50.0) * 50
    return float(fee), round(dist, 2), "gps"

'''

if "_compute_delivery_fee_pro" not in src:
    src = src.replace(
        "def _row(r):",
        helpers + "\ndef _row(r):",
        1,
    )
    print("[OK] b2b_requests.py -> helpers livraison ajoutes")

# 1.2 Ajouter l'endpoint estimate-delivery AVANT le endpoint submit
estimate_ep = '''
    @app.post("/api/pro/requests/{reference}/estimate-delivery")
    def estimate_delivery(reference: str, payload: SubmitRequestPayload,
                          user=Depends(require_role("PROFESSIONNEL"))):
        """Estime la distance et les frais de livraison selon la position GPS fournie."""
        if (payload.delivery_mode or "").lower() != "livraison":
            return {"distance_km": None, "delivery_fee": 0, "source": "retrait"}

        conn = get_db()
        try:
            oid = _get_org_id(conn, user["id"])
            req = conn.execute(
                "SELECT id FROM requests WHERE reference=? AND organization_id=?",
                (reference, oid),
            ).fetchone()
            if req is None:
                raise HTTPException(404, "Demande introuvable")

            fee, dist, source = _compute_delivery_fee_pro(
                conn, payload.latitude, payload.longitude
            )

            # Calcul du sous-total pour info
            raw = conn.execute(
                "SELECT ri.requested_quantity, p.price"
                " FROM request_items ri"
                " LEFT JOIN products p ON p.id = ri.product_id"
                " WHERE ri.request_id=?",
                (req["id"],),
            ).fetchall()
            subtotal = 0.0
            for r in raw:
                if r["price"]:
                    subtotal += float(r["price"]) * float(r["requested_quantity"] or 0)
            subtotal = round(subtotal, 2)
        finally:
            conn.close()

        return {
            "distance_km": dist,
            "delivery_fee": fee,
            "source": source,
            "subtotal": subtotal,
            "total": round(subtotal + fee, 2) if source == "gps" else None,
        }


'''
if "/estimate-delivery" not in src:
    anchor = '    @app.post("/api/pro/requests/{reference}/submit")'
    if anchor in src:
        src = src.replace(anchor, estimate_ep + anchor, 1)
        print("[OK] b2b_requests.py -> endpoint /estimate-delivery ajoute")

# 1.3 Remplacer submit par une version qui cree un order
old_submit_pat = re.compile(
    r'    @app\.post\("/api/pro/requests/\{reference\}/submit"\).*?(?=\n    #|\n\nclass |\ndef |\Z)',
    re.DOTALL
)

new_submit = '''    @app.post("/api/pro/requests/{reference}/submit")
    def submit_request(reference: str, payload: SubmitRequestPayload = None,
                       user=Depends(require_role("PROFESSIONNEL"))):
        if payload is None:
            payload = SubmitRequestPayload()

        import uuid
        import json as _json

        conn = get_db()
        try:
            oid = _get_org_id(conn, user["id"])
            req = conn.execute(
                "SELECT * FROM requests WHERE reference=? AND organization_id=?",
                (reference, oid),
            ).fetchone()
            if req is None:
                raise HTTPException(404, "Demande introuvable")
            if req["status"] != "DRAFT":
                raise HTTPException(400, "Demande deja soumise")

            items = conn.execute(
                "SELECT * FROM request_items WHERE request_id=? ORDER BY id",
                (req["id"],),
            ).fetchall()
            atts = conn.execute(
                "SELECT * FROM request_attachments WHERE request_id=? ORDER BY id",
                (req["id"],),
            ).fetchall()
            if len(items) == 0 and len(atts) == 0:
                raise HTTPException(400, "Ajoutez au moins un produit ou une piece jointe")

            mode = (payload.delivery_mode or "retrait").strip().lower()
            if mode not in ("retrait", "livraison"):
                raise HTTPException(400, "Mode de livraison invalide")
            if mode == "livraison" and not payload.address.strip() and payload.latitude is None:
                raise HTTPException(400, "Adresse ou GPS obligatoire pour la livraison")

            # Calcul frais livraison
            if mode == "livraison":
                delivery_fee, delivery_distance, _src = _compute_delivery_fee_pro(
                    conn, payload.latitude, payload.longitude
                )
            else:
                delivery_fee, delivery_distance = 0.0, None

            # Sous-total (prix actuels du catalogue)
            subtotal = 0.0
            order_items = []
            first_product_id = None
            first_product_name = ""
            first_qty = 0
            first_price = 0.0
            for it in items:
                price = 0.0
                pname = it["description"]
                if it["product_id"]:
                    p = conn.execute(
                        "SELECT price, name FROM products WHERE id=?",
                        (it["product_id"],),
                    ).fetchone()
                    if p:
                        price = float(p["price"] or 0)
                        pname = it["description"] or p["name"]
                qty = float(it["requested_quantity"] or 0)
                line_total = round(price * qty, 2)
                subtotal += line_total
                order_items.append({
                    "product_id": it["product_id"],
                    "product_name": pname,
                    "unit_price": price,
                    "quantity": qty,
                    "subtotal": line_total,
                })
                if first_product_id is None:
                    first_product_id = it["product_id"]
                    first_product_name = pname
                    first_qty = qty
                    first_price = price

            subtotal = round(subtotal, 2)
            total = round(subtotal + delivery_fee, 2)

            # Recuperer les infos du client
            user_row = conn.execute(
                "SELECT full_name, phone FROM users WHERE id=?", (user["id"],)
            ).fetchone()
            prof = conn.execute(
                "SELECT structure_name, phone FROM professional_profiles WHERE id=?",
                (oid,),
            ).fetchone()

            customer_name = (prof["structure_name"] if prof else "") or (user_row["full_name"] if user_row else "")
            phone = (prof["phone"] if prof else "") or (user_row["phone"] if user_row else "")

            # Creer une commande (orders) a partir de la demande
            order_ref = "CMD-" + datetime.now().strftime("%y%m%d") + "-" + uuid.uuid4().hex[:6].upper()
            now = _now()

            cur = conn.execute(
                "INSERT INTO orders (reference, customer_name, phone, product_id,"
                " product_name, quantity, delivery_mode, address, prescription_file,"
                " status, created_at, latitude, longitude, location_accuracy,"
                " delivery_fee, delivery_distance_km, price, subtotal,"
                " user_id, customer_type, delivery_vehicle_type,"
                " payment_status, delivery_status, prescription_status,"
                " professional_id, request_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'en_attente', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,"
                " 'PENDING', 'NONE', 'NONE', ?, ?)",
                (
                    order_ref, customer_name, phone,
                    first_product_id, first_product_name or "Produit",
                    int(first_qty) or 1,
                    mode, payload.address.strip(), "",
                    now,
                    payload.latitude, payload.longitude, payload.location_accuracy,
                    delivery_fee, delivery_distance,
                    first_price, subtotal,
                    user["id"], "PROFESSIONNEL", "VOITURE",
                    oid, req["id"],
                ),
            )
            order_id = cur.lastrowid

            # Inserer les order_items
            for oi in order_items:
                conn.execute(
                    "INSERT INTO order_items (order_id, product_id, product_name,"
                    " unit_price, quantity, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
                    (order_id, oi["product_id"], oi["product_name"],
                     oi["unit_price"], oi["quantity"], oi["subtotal"]),
                )

            # Marquer la demande comme SUBMITTED
            summary = {
                "delivery_mode": mode,
                "address": payload.address.strip(),
                "latitude": payload.latitude,
                "longitude": payload.longitude,
                "order_ref": order_ref,
            }
            conn.execute(
                "UPDATE requests SET status='SUBMITTED', notes=?, source_summary=?, updated_at=?"
                " WHERE id=?",
                (payload.notes.strip(), _json.dumps(summary), now, req["id"]),
            )

            conn.commit()

            # Notifier la pharmacie
            try:
                from v3_modules.notifications import push_notification
                admins = conn.execute(
                    "SELECT id FROM users WHERE role IN ('PHARMACIEN', 'ADMIN')"
                ).fetchall()
                for a in admins:
                    push_notification(
                        conn, a["id"],
                        "Nouvelle commande pro",
                        order_ref + " — " + customer_name,
                    )
                conn.commit()
            except Exception:
                pass
        finally:
            conn.close()

        return {
            "request_reference": reference,
            "order_reference": order_ref,
            "delivery_mode": mode,
            "delivery_fee": delivery_fee,
            "delivery_distance_km": delivery_distance,
            "subtotal": subtotal,
            "total": total,
        }

'''
if old_submit_pat.search(src):
    src = old_submit_pat.sub(new_submit, src, count=1)
    print("[OK] b2b_requests.py -> submit cree un order")

B2B.write_text(src, encoding="utf-8")

# ============================================================
# 2. FRONTEND JS : affiche distance + frais + redirection paiement
# ============================================================
CONF_JS = r'''/* Elokinab Health - Page confirmation demande (v5) */
(function () {
  var API = "/api";
  var $ = function (id) { return document.getElementById(id); };

  var state = {
    draft: null,
    summary: null,
    mode: "retrait",
    lat: null, lon: null, acc: null,
    estimate: null,
    estimateLoading: false,
    submitted: false,
    orderRef: null
  };

  function escapeHtml(s) {
    try {
      return String(s == null ? "" : s)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;")
        .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    } catch (e) { return ""; }
  }

  function money(v) {
    var n = Math.round(Number(v) || 0);
    try { return n.toLocaleString("fr-FR") + " F"; }
    catch (e) {
      var s = String(n), out = "";
      for (var i = 0; i < s.length; i++) {
        if (i > 0 && (s.length - i) % 3 === 0) out += " ";
        out += s.charAt(i);
      }
      return out + " F";
    }
  }

  function qtyLabel(q) {
    var n = Number(q) || 0;
    if (n === Math.floor(n)) return String(n);
    return n.toFixed(2);
  }

  function api(method, path, body) {
    var opts = {
      method: method, credentials: "same-origin",
      headers: { "Accept": "application/json" }
    };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(API + path, opts).then(function (r) {
      if (r.status === 401) {
        window.location.href = "/connexion?next=/professionnel/demande";
        throw new Error("Non authentifie");
      }
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur");
        return d;
      });
    });
  }

  function toast(msg) {
    var t = document.createElement("div");
    t.className = "pg-toast";
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 2400);
  }

  // ============================================================
  // Chargement
  // ============================================================
  function load() {
    return api("GET", "/pro/requests/draft").then(function (d) {
      state.draft = d;
      return api("GET", "/pro/requests/" + encodeURIComponent(d.reference) + "/summary");
    }).then(function (sum) {
      state.summary = sum;
      if (sum.items_count === 0 && sum.attachments_count === 0) {
        window.location.href = "/professionnel/demande";
        return;
      }
      render();
    }).catch(function (e) {
      $("main").innerHTML = '<div style="text-align:center;padding:40px;color:#dc2626">Erreur : ' +
        escapeHtml(e.message) + '</div>';
    });
  }

  // ============================================================
  // Rendu
  // ============================================================
  function render() {
    if (state.submitted) { renderSuccess(); return; }

    $("page-ref").textContent = state.summary.reference;

    var subtotal = state.summary.subtotal;
    var fee = state.estimate && state.estimate.delivery_fee ? state.estimate.delivery_fee : 0;
    var total = state.mode === "livraison" && state.estimate
      ? (state.estimate.total || subtotal + fee)
      : subtotal;

    var deliveryLine = '';
    if (state.mode === "livraison") {
      if (state.estimate && state.estimate.source === "gps") {
        deliveryLine =
          '<div class="totals-line">' +
            '<span class="lbl">Distance</span>' +
            '<span class="val">' + state.estimate.distance_km + ' km</span>' +
          '</div>' +
          '<div class="totals-line">' +
            '<span class="lbl">Frais livraison</span>' +
            '<span class="val">' + money(state.estimate.delivery_fee) + '</span>' +
          '</div>';
      } else if (state.estimate && state.estimate.source === "no_gps") {
        deliveryLine =
          '<div class="totals-line">' +
            '<span class="lbl">Frais livraison</span>' +
            '<span class="val confirm">Activez le GPS</span>' +
          '</div>';
      } else if (state.estimate && state.estimate.source === "no_pharmacy") {
        deliveryLine =
          '<div class="totals-line">' +
            '<span class="lbl">Frais livraison</span>' +
            '<span class="val confirm">A confirmer</span>' +
          '</div>';
      } else {
        deliveryLine =
          '<div class="totals-line">' +
            '<span class="lbl">Frais livraison</span>' +
            '<span class="val confirm">En attente</span>' +
          '</div>';
      }
    } else {
      deliveryLine =
        '<div class="totals-line">' +
          '<span class="lbl">Frais livraison</span>' +
          '<span class="val">Retrait en pharmacie — 0 F</span>' +
        '</div>';
    }

    var deliveryFields = state.mode === "livraison" ? '' :
      ' class="hidden"';

    var html = '' +
      '<h2 class="pg-section-title">Recapitulatif</h2>' +
      itemsRender() +
      '<div class="totals-card">' +
        '<div class="totals-line">' +
          '<span class="lbl">Sous-total</span>' +
          '<span class="val">' + money(subtotal) + '</span>' +
        '</div>' +
        deliveryLine +
        '<div class="totals-line total">' +
          '<span>Total' + (state.mode === "livraison" && !state.estimate ? ' estime' : '') + '</span>' +
          '<span class="val">' + money(total) + '</span>' +
        '</div>' +
      '</div>' +

      '<h2 class="pg-section-title">Mode de recuperation</h2>' +
      '<div class="mode-grid">' +
        '<button class="mode-btn ' + (state.mode === "retrait" ? "active" : "") + '" data-mode="retrait" type="button">' +
          '<span class="ico">&#127968;</span>Retrait' +
        '</button>' +
        '<button class="mode-btn ' + (state.mode === "livraison" ? "active" : "") + '" data-mode="livraison" type="button">' +
          '<span class="ico">&#128666;</span>Livraison' +
        '</button>' +
      '</div>' +

      '<div id="delivery-fields"' + deliveryFields + '>' +
        '<div class="field">' +
          '<label for="address">Adresse de livraison</label>' +
          '<textarea id="address" rows="2" placeholder="Quartier, rue, repere..."></textarea>' +
        '</div>' +
        '<button type="button" class="gps-btn" id="gps-btn">' +
          (state.lat !== null ? '&#128205; Actualiser ma position' : '&#128205; Utiliser ma position GPS') +
        '</button>' +
        '<div class="gps-status" id="gps-status">' +
          (state.lat !== null ? '&#10003; Position : ' + state.lat.toFixed(4) + ', ' + state.lon.toFixed(4) +
            ' (&plusmn; ' + Math.round(state.acc || 0) + ' m)' : '') +
        '</div>' +
      '</div>' +

      '<div class="notes-block">' +
        '<label for="notes">Notes (facultatif)</label>' +
        '<textarea class="notes" id="notes" placeholder="Instructions particulieres, delai souhaite..."></textarea>' +
      '</div>' +

      '<div class="pg-actions">' +
        '<button class="btn btn-primary" id="submit-btn" type="button">Continuer vers le paiement</button>' +
        '<a class="btn btn-ghost" href="/professionnel/demande">Retour</a>' +
      '</div>' +

      '<div class="pg-info">' +
        '<strong>Prochaine etape :</strong> vous serez redirige vers la page de paiement. ' +
        'La pharmacie confirmera ensuite la disponibilite et preparera votre commande.' +
      '</div>';

    $("main").innerHTML = html;
    bindEvents();

    // Si mode livraison + GPS present -> recalcul auto
    if (state.mode === "livraison" && state.lat !== null && !state.estimateLoading) {
      computeEstimate();
    }
  }

  function itemsRender() {
    if (!state.summary.items || state.summary.items.length === 0) {
      return '<div class="pg-info">Aucun produit.</div>';
    }
    return state.summary.items.map(function (it) {
      var priceHtml = it.unit_price > 0
        ? money(it.line_total) + '<small>' + money(it.unit_price) + ' / unite</small>'
        : '<small>Prix a confirmer</small>';
      return '<div class="it-row">' +
        '<div class="it-body">' +
          '<div class="it-name">' + escapeHtml(it.description) + '</div>' +
          '<div class="it-qty">x ' + qtyLabel(it.requested_quantity) + '</div>' +
        '</div>' +
        '<div class="it-price">' + priceHtml + '</div>' +
      '</div>';
    }).join("");
  }

  // ============================================================
  // Evenements
  // ============================================================
  function bindEvents() {
    Array.prototype.forEach.call(document.querySelectorAll(".mode-btn"), function (b) {
      b.addEventListener("click", function () {
        var newMode = b.getAttribute("data-mode");
        if (newMode !== state.mode) {
          state.mode = newMode;
          if (newMode === "retrait") {
            state.lat = null; state.lon = null; state.acc = null;
            state.estimate = null;
          }
          render();
        }
      });
    });

    var gpsBtn = $("gps-btn");
    if (gpsBtn) gpsBtn.addEventListener("click", askGPS);

    var sub = $("submit-btn");
    if (sub) sub.addEventListener("click", submit);
  }

  function askGPS() {
    if (!navigator.geolocation) {
      $("gps-status").textContent = "GPS indisponible.";
      return;
    }
    var b = $("gps-btn");
    b.disabled = true;
    b.textContent = "Localisation...";
    navigator.geolocation.getCurrentPosition(function (pos) {
      state.lat = pos.coords.latitude;
      state.lon = pos.coords.longitude;
      state.acc = pos.coords.accuracy;
      b.disabled = false;
      b.innerHTML = "&#128205; Actualiser ma position";
      $("gps-status").innerHTML = "&#10003; Position obtenue, calcul du frais...";
      computeEstimate();
    }, function () {
      b.disabled = false;
      b.innerHTML = "&#128205; Utiliser ma position GPS";
      $("gps-status").textContent = "Position introuvable. Saisissez l'adresse.";
    }, { enableHighAccuracy: true, timeout: 15000 });
  }

  function computeEstimate() {
    if (state.mode !== "livraison") return;
    if (state.estimateLoading) return;
    state.estimateLoading = true;

    api("POST", "/pro/requests/" + state.draft.reference + "/estimate-delivery", {
      delivery_mode: "livraison",
      latitude: state.lat,
      longitude: state.lon,
      location_accuracy: state.acc,
      address: "",
      notes: ""
    }).then(function (r) {
      state.estimate = r;
      state.estimateLoading = false;
      render();
    }).catch(function (e) {
      state.estimateLoading = false;
      toast("Impossible de calculer le frais : " + e.message);
    });
  }

  function submit() {
    var notes = $("notes") ? $("notes").value.trim() : "";
    var address = $("address") ? $("address").value.trim() : "";

    if (state.mode === "livraison" && !address && state.lat === null) {
      toast("Adresse ou GPS obligatoire pour la livraison");
      return;
    }

    var payload = {
      delivery_mode: state.mode,
      address: address,
      notes: notes
    };
    if (state.lat !== null && state.lon !== null) {
      payload.latitude = state.lat;
      payload.longitude = state.lon;
      payload.location_accuracy = state.acc;
    }

    var btn = $("submit-btn");
    btn.disabled = true;
    btn.textContent = "Envoi...";

    api("POST", "/pro/requests/" + state.draft.reference + "/submit", payload)
      .then(function (r) {
        state.submitted = true;
        state.orderRef = r.order_reference;
        // Redirection DIRECTE vers le paiement
        window.location.href = "/static/payment.html?ref=" + encodeURIComponent(r.order_reference);
      })
      .catch(function (e) {
        toast(e.message);
        btn.disabled = false;
        btn.textContent = "Continuer vers le paiement";
      });
  }

  function renderSuccess() {
    // Non utilise car on redirige directement vers le paiement
    $("main").innerHTML = '<div style="text-align:center;padding:40px;color:#64748b">Redirection vers le paiement...</div>';
  }

  document.addEventListener("DOMContentLoaded", load);
})();
'''
(STATIC / "professional_demande_confirmer.js").write_text(CONF_JS, encoding="utf-8")
print("[OK] professional_demande_confirmer.js")

print()
print("=" * 60)
print("FIX LIVRAISON + PAIEMENT DIRECT LIVRE")
print("=" * 60)
print()
print("Backend :")
print("  POST /api/pro/requests/{ref}/estimate-delivery")
print("    -> distance + frais (tarifs VOITURE)")
print("  POST /api/pro/requests/{ref}/submit")
print("    -> cree un order + order_items")
print("    -> retourne order_reference")
print()
print("Frontend :")
print("  - Affiche Distance + Frais de livraison")
print("  - Recalcul auto au GPS")
print("  - Total = sous-total + frais")
print("  - Bouton 'Continuer vers le paiement'")
print("  - Redirection DIRECTE vers /static/payment.html")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")