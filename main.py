import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import Cookie, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware


class SelectiveGZipMiddleware:
    """GZip tout SAUF les flux SSE (qui doivent rester non bufferises)."""
    def __init__(self, app, minimum_size=500, exclude_paths=None):
        self.app = app
        self.exclude_paths = list(exclude_paths or ["/api/notifications/stream"])
        self._gzip = GZipMiddleware(app, minimum_size=minimum_size)

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self._gzip(scope, receive, send)
            return
        path = scope.get("path", "")
        for excl in self.exclude_paths:
            if path.startswith(excl):
                # Bypass GZip pour ne pas bufferiser le SSE
                await self.app(scope, receive, send)
                return
        await self._gzip(scope, receive, send)
from starlette.middleware.base import BaseHTTPMiddleware

# ============================================================
# Patient Cache : cache HTTP sur categories + products (5 min)
# ============================================================


# ============================================================
# Blocage : rediriger les PRO des pages patient vers /professionnel
# ============================================================
class BlockProOnPatientMiddleware(BaseHTTPMiddleware):
    PATIENT_PATHS = (
        "/static/cart.html",
        "/checkout",
        "/payment.html",
        "/compte",
        "/notifications.html",
    )
    async def dispatch(self, request, call_next):
        path = request.url.path
        # Seulement GET (pas les POST API)
        if request.method != "GET":
            return await call_next(request)
        # Uniquement les pages patient listees
        is_patient_path = any(path == p or path.startswith(p) for p in self.PATIENT_PATHS)
        if not is_patient_path:
            return await call_next(request)

        # Verifier la session
        token = request.cookies.get("elonikab_session")
        if token:
            try:
                from v3_modules.auth import load_user_from_cookie
                conn = get_db()
                try:
                    row = load_user_from_cookie(get_db, token)
                finally:
                    conn.close()
                if row and row["role"] == "PROFESSIONNEL":
                    from fastapi.responses import RedirectResponse
                    return RedirectResponse(url="/professionnel", status_code=302)
            except Exception:
                pass
        return await call_next(request)



class PatientCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        if request.method == "GET":
            # Routes cacheables 5 min
            if path in ("/api/categories", "/api/products", "/api/settings"):
                response.headers["Cache-Control"] = "public, max-age=300, must-revalidate"
                response.headers["Vary"] = "Accept-Encoding, Cookie"
            else:
                # No-cache par defaut pour le reste
                if "cache-control" not in (k.lower() for k in response.headers.keys()):
                    response.headers["Cache-Control"] = "no-store"
        return response


from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_UPLOADS = {"image/jpeg", "image/png", "image/webp", "image/heic", "application/pdf"}

app = FastAPI(title="Elonikab Health", version="2.1.0")

# Brotli si dispo (meilleure compression)
try:
    from starlette.middleware.brotli import BrotliMiddleware
    app.add_middleware(BrotliMiddleware, quality=5)
    print("[BOOT] BrotliMiddleware actif")
except Exception:
    pass  # fallback GZip deja en place




# --- Performance : compression GZip ---
app.add_middleware(SelectiveGZipMiddleware, minimum_size=500,
                  exclude_paths=["/api/notifications/stream"])



def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    return {key: row[key] for key in row.keys()}

# ============================================================
# LOT 1 - Helper audit_logs (Faille D)
# ============================================================
def log_audit(conn, user_id, action, target_type="", target_id=None, details=""):
    """Enregistre une action sensible dans audit_logs.
    Ne leve jamais d'exception : le logging ne doit pas casser le flow metier.
    """
    try:
        conn.execute(
            "INSERT INTO audit_logs (user_id, action, target_type, target_id,"
            " details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, action, target_type,
             str(target_id) if target_id is not None else None,
             details, datetime.now().isoformat(timespec="seconds")),
        )
    except Exception:
        pass



# --- PHASE 3a : deps auth pour routes non protegees ---
from v3_modules.auth import make_current_user_dep, can_access_order as _can_access_order
get_current_user_dep = make_current_user_dep(get_db)


def can_access_order(user, order_row):
    """Wrapper : accepte sqlite3.Row ou dict, verifie ownership."""
    if isinstance(order_row, dict):
        order = order_row
    else:
        order = row_to_dict(order_row)
    return _can_access_order(user, order)



def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS products ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " name TEXT NOT NULL,"
        " presentation TEXT DEFAULT '',"
        " price REAL NOT NULL DEFAULT 0,"
        " availability TEXT NOT NULL DEFAULT 'disponible',"
        " description TEXT DEFAULT '',"
        " category TEXT DEFAULT 'Divers',"
        " requires_prescription INTEGER NOT NULL DEFAULT 0,"
        " image_url TEXT DEFAULT '',"
        " is_demo INTEGER NOT NULL DEFAULT 1,"
        " created_at TEXT NOT NULL"
        ")"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS orders ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " reference TEXT NOT NULL UNIQUE,"
        " customer_name TEXT NOT NULL,"
        " phone TEXT NOT NULL,"
        " product_id INTEGER,"
        " product_name TEXT DEFAULT '',"
        " quantity INTEGER NOT NULL DEFAULT 1,"
        " delivery_mode TEXT NOT NULL,"
        " address TEXT DEFAULT '',"
        " prescription_file TEXT DEFAULT '',"
        " status TEXT NOT NULL DEFAULT 'en_attente',"
        " created_at TEXT NOT NULL"
        ")"
    )

    # --- GPS MIGRATION ---
    existing_cols = {row[1] for row in cur.execute("PRAGMA table_info(orders)").fetchall()}
    for col_name, col_type in (("latitude", "REAL"), ("longitude", "REAL"), ("location_accuracy", "REAL")):
        if col_name not in existing_cols:
            cur.execute("ALTER TABLE orders ADD COLUMN " + col_name + " " + col_type)
    # --- end GPS MIGRATION ---

    cur.execute(
        "CREATE TABLE IF NOT EXISTS drivers ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " name TEXT NOT NULL,"
        " phone TEXT NOT NULL,"
        " is_active INTEGER NOT NULL DEFAULT 1,"
        " created_at TEXT NOT NULL"
        ")"
    )
    cur.execute("SELECT COUNT(*) AS total FROM drivers")
    if cur.fetchone()["total"] == 0:
        now_drivers = datetime.now().isoformat(timespec="seconds")
        demo_drivers = [
            ("Kossi (DEMO)", "22890000001"),
            ("Mensah (DEMO)", "22890000002"),
            ("Komlan (DEMO)", "22890000003"),
        ]
        cur.executemany(
            "INSERT INTO drivers (name, phone, is_active, created_at) VALUES (?, ?, 1, ?)",
            [(n, p, now_drivers) for n, p in demo_drivers],
        )

    cur.execute(
        "CREATE TABLE IF NOT EXISTS pharmacy_settings ("
        " id INTEGER PRIMARY KEY,"
        " delivery_fee_default REAL NOT NULL DEFAULT 0"
        ")"
    )
    cur.execute(
        "INSERT OR IGNORE INTO pharmacy_settings (id, delivery_fee_default) VALUES (1, 500)"
    )
    ps_cols = {row[1] for row in cur.execute("PRAGMA table_info(pharmacy_settings)").fetchall()}
    ps_new_cols = [
        ("pharmacy_latitude", "REAL"),
        ("pharmacy_longitude", "REAL"),
        ("delivery_base_fee", "REAL NOT NULL DEFAULT 300"),
        ("delivery_price_per_km", "REAL NOT NULL DEFAULT 100"),
        ("delivery_max_km", "REAL NOT NULL DEFAULT 0"),
    ]
    for col_name, col_type in ps_new_cols:
        if col_name not in ps_cols:
            cur.execute("ALTER TABLE pharmacy_settings ADD COLUMN " + col_name + " " + col_type)
    ord_cols2 = {row[1] for row in cur.execute("PRAGMA table_info(orders)").fetchall()}
    if "delivery_distance_km" not in ord_cols2:
        cur.execute("ALTER TABLE orders ADD COLUMN delivery_distance_km REAL")
    if "price" not in ord_cols2:
        cur.execute("ALTER TABLE orders ADD COLUMN price REAL NOT NULL DEFAULT 0")
    if "subtotal" not in ord_cols2:
        cur.execute("ALTER TABLE orders ADD COLUMN subtotal REAL NOT NULL DEFAULT 0")
    orders_cols = {row[1] for row in cur.execute("PRAGMA table_info(orders)").fetchall()}
    if "delivery_fee" not in orders_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN delivery_fee REAL NOT NULL DEFAULT 0")

    cur.execute("SELECT COUNT(*) AS total FROM products")
    if cur.fetchone()["total"] == 0:
        now = datetime.now().isoformat(timespec="seconds")
        demo = [
            ("Doliprane 1000 mg", "Boite de 8 comprimes", 1000, "disponible",
             "Antalgique et antipyretique contre les douleurs legeres et la fievre.",
             "Douleurs et fievre", 0),
            ("Amoxicilline 500 mg", "Boite de 12 gelules", 2500, "disponible",
             "Antibiotique de la famille des penicillines. Delivrance sur ordonnance.",
             "Antibiotiques", 1),
            ("Vitamine C 1000 mg", "Tube de 20 comprimes effervescents", 2000, "disponible",
             "Contribution au fonctionnement normal du systeme immunitaire.",
             "Vitamines", 0),
            ("Serum physiologique", "20 dosettes de 5 ml", 1500, "disponible",
             "Solution saline sterile pour le nettoyage du nez et des yeux.",
             "Hygiene", 0),
            ("Ibuprofene 400 mg", "Boite de 20 comprimes", 1500, "disponible",
             "Anti-inflammatoire non steroidien contre les douleurs et la fievre.",
             "Douleurs et fievre", 0),
            ("Pansements assortis", "Boite de 40 pansements", 2000, "disponible",
             "Pansements steriles de tailles variees pour les petites blessures.",
             "Premiers soins", 0),
            ("Thermometre digital", "Thermometre electronique", 4500, "disponible",
             "Mesure rapide de la temperature corporelle en 60 secondes.",
             "Materiel", 0),
            ("Gel hydroalcoolique", "Flacon pompe de 250 ml", 2500, "rupture",
             "Solution hydroalcoolique pour l'hygiene des mains.",
             "Hygiene", 0),
        ]
        cur.executemany(
            "INSERT INTO products (name, presentation, price, availability, description,"
            " category, requires_prescription, is_demo, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)",
            [(p[0], p[1], p[2], p[3], p[4], p[5], p[6], now) for p in demo],
        )

    # --- IMAGES PRODUITS (patch) ---
    image_map = {
        "Doliprane 1000 mg": "doliprane_1000mg.jpg",
        "Amoxicilline 500 mg": "amoxicilline_500mg.jpg",
        "Vitamine C 1000 mg": "vitamine_c_1000mg.jpg",
        "Serum physiologique": "serum_physiologique.jpg",
        "Ibuprofene 400 mg": "ibuprofene_400mg.jpg",
        "Pansements assortis": "pansements_40.jpg",
        "Thermometre digital": "thermometre_digital.jpg",
        "Gel hydroalcoolique": "gel_hydroalcoolique_250ml.jpg",
    }
    for _name, _fname in image_map.items():
        cur.execute(
            "UPDATE products SET image_url = ?"
            " WHERE name = ? AND (image_url IS NULL OR image_url = '')",
            ("/static/images/products/" + _fname, _name),
        )
    # --- fin patch ---

    conn.commit()
    conn.close()


@app.get("/api/products")
def list_products(q: str = "", category: str = "", limit: int = 0, offset: int = 0):
    conn = get_db()
    sql = "SELECT * FROM products WHERE 1=1"
    params = []
    q_clean = q.strip().lower()
    if q_clean:
        sql += " AND LOWER(name) LIKE ?"
        params.append("%" + q_clean + "%")
    if category.strip():
        sql += " AND category = ?"
        params.append(category.strip())
    if q_clean:
        sql += " ORDER BY CASE WHEN LOWER(name) LIKE ? THEN 0 ELSE 1 END, name COLLATE NOCASE"
        params.append(q_clean + "%")
    else:
        sql += " ORDER BY name COLLATE NOCASE"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@app.get("/api/categories")
def list_categories():
    conn = get_db()
    rows = conn.execute(
        "SELECT category, COUNT(*) AS total FROM products"
        " GROUP BY category ORDER BY category COLLATE NOCASE"
    ).fetchall()
    conn.close()
    return [{"name": r["category"], "total": r["total"]} for r in rows]


@app.get("/api/products/{product_id}")
def get_product(product_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return row_to_dict(row)




# ============================================================
# V2.4 - Calcul des frais de livraison selon la distance
# ============================================================

def haversine_km(lat1, lon1, lat2, lon2):
    """Distance a vol d'oiseau en km entre deux points GPS."""
    from math import radians, sin, cos, asin, sqrt
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))


def compute_delivery_fee(client_lat, client_lon):
    """Retourne (fee, distance_km) selon la position du client.
    Si GPS client ou position pharmacie manquants : fallback delivery_fee_default,
    distance = None."""
    conn = get_db()
    s = conn.execute("SELECT * FROM pharmacy_settings WHERE id = 1").fetchone()
    conn.close()
    if s is None:
        return 0.0, None

    def col(name, default=0.0):
        try:
            v = s[name]
        except Exception:
            return default
        return default if v is None else v

    fallback = float(col("delivery_fee_default", 0.0))
    ph_lat = s["pharmacy_latitude"] if "pharmacy_latitude" in s.keys() else None
    ph_lon = s["pharmacy_longitude"] if "pharmacy_longitude" in s.keys() else None

    if client_lat is None or client_lon is None or ph_lat is None or ph_lon is None:
        return fallback, None

    dist = haversine_km(float(ph_lat), float(ph_lon), float(client_lat), float(client_lon))
    base = float(col("delivery_base_fee", 300.0))
    per_km = float(col("delivery_price_per_km", 100.0))
    fee = base + dist * per_km
    fee = round(fee / 50.0) * 50  # arrondi aux 50 FCFA
    return float(fee), round(dist, 2)


@app.post("/api/orders")
async def create_order(
    request: Request,
    customer_name: str = Form(...),
    phone: str = Form(...),
    product_id: int = Form(...),
    quantity: int = Form(1),
    delivery_mode: str = Form(...),
    address: str = Form(""),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    location_accuracy: Optional[float] = Form(None),
    prescription: Optional[UploadFile] = File(None),
    user = Depends(get_current_user_dep),
):
    if not user:
        raise HTTPException(401, "Authentification requise pour commander")
    name = customer_name.strip()
    phone_clean = phone.strip()
    if not name or not phone_clean:
        raise HTTPException(status_code=400, detail="Nom et telephone obligatoires")
    if delivery_mode not in ("retrait", "livraison"):
        raise HTTPException(status_code=400, detail="Mode de livraison invalide")
    if delivery_mode == "livraison" and not address.strip():
            has_gps = latitude is not None and longitude is not None
    if delivery_mode == "livraison" and not address.strip() and not has_gps:
        raise HTTPException(
            status_code=400,
            detail="Adresse ou localisation GPS obligatoire pour la livraison",
        )
    if latitude is not None and (latitude < -90 or latitude > 90):
        raise HTTPException(status_code=400, detail="Latitude invalide (doit etre entre -90 et 90)")
    if longitude is not None and (longitude < -180 or longitude > 180):
        raise HTTPException(status_code=400, detail="Longitude invalide (doit etre entre -180 et 180)")
    if location_accuracy is not None and location_accuracy < 0:
        raise HTTPException(status_code=400, detail="Accuracy invalide (doit etre superieure ou egale a 0)")
    quantity = max(1, quantity)

    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Produit introuvable")

    saved_file = ""
    if prescription is not None and prescription.filename:
        content_type = prescription.content_type or ""
        if content_type not in ALLOWED_UPLOADS:
            conn.close()
            raise HTTPException(status_code=400, detail="Format d'ordonnance non accepte")
        ext = Path(prescription.filename).suffix.lower() or ".jpg"
        saved_file = uuid.uuid4().hex + ext
        target = UPLOADS_DIR / saved_file
        with target.open("wb") as f:
            while True:
                chunk = await prescription.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)

    reference = "CMD-" + datetime.now().strftime("%y%m%d") + "-" + uuid.uuid4().hex[:6].upper()
    created_at = datetime.now().isoformat(timespec="seconds")

    if delivery_mode == "livraison":
        delivery_fee, delivery_distance = compute_delivery_fee(latitude, longitude)
    else:
        delivery_fee = 0.0
        delivery_distance = None
    subtotal = round(product["price"] * quantity, 2)

    cur = conn.execute(
        "INSERT INTO orders (reference, customer_name, phone, product_id, product_name,"
        " quantity, delivery_mode, address, prescription_file, status, created_at,"
        " latitude, longitude, location_accuracy, delivery_fee, delivery_distance_km,"
        " price, subtotal)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'en_attente', ?, ?, ?, ?, ?, ?, ?, ?)",
        (reference, name, phone_clean, product["id"], product["name"], quantity,
         delivery_mode, address.strip(), saved_file, created_at,
         latitude, longitude, location_accuracy, delivery_fee, delivery_distance,
         product["price"], subtotal),
    )
    conn.commit()
    order_id = cur.lastrowid
    conn.close()

    return {
        "id": order_id,
        "reference": reference,
        "status": "en_attente",
        "created_at": created_at,
        "customer_name": name,
        "phone": phone_clean,
        "product_id": product["id"],
        "product_name": product["name"],
        "quantity": quantity,
        "delivery_mode": delivery_mode,
        "address": address.strip(),
        "prescription_file": saved_file,
        "price": product["price"],
        "subtotal": round(product["price"] * quantity, 2),
        "delivery_fee": delivery_fee,
        "delivery_distance_km": delivery_distance,
        "total": round(product["price"] * quantity + delivery_fee, 2),
        "latitude": latitude,
        "longitude": longitude,
        "location_accuracy": location_accuracy,
    }


@app.get("/api/orders")
def list_orders(user = Depends(get_current_user_dep)):
    if not user:
        raise HTTPException(401, "Non authentifie")
    role = user["role"]
    conn = get_db()
    if role in ("PHARMACIEN", "ADMIN"):
        rows = conn.execute(
            "SELECT * FROM orders ORDER BY id DESC LIMIT 100"
        ).fetchall()
    elif role == "PROFESSIONNEL":
        org = user.get("organization_id")
        if org:
            rows = conn.execute(
                "SELECT * FROM orders WHERE user_id = ?"
                " OR organization_id = ? OR professional_id = ?"
                " ORDER BY id DESC LIMIT 100",
                (user["id"], org, org)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM orders WHERE user_id = ?"
                " ORDER BY id DESC LIMIT 100",
                (user["id"],)
            ).fetchall()
    else:  # PATIENT
        rows = conn.execute(
            "SELECT * FROM orders WHERE user_id = ?"
            " ORDER BY id DESC LIMIT 100",
            (user["id"],)
        ).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@app.get("/api/orders/mine")
def list_my_orders(session_token: str = Cookie(None, alias="elonikab_session")):
    """Liste des commandes de l'utilisateur connecte."""
    if not session_token:
        raise HTTPException(401, "Non authentifie")
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT u.id FROM sessions s JOIN users u ON u.id = s.user_id"
            " WHERE s.token = ? AND s.expires_at > ?",
            (session_token, datetime.now().isoformat(timespec="seconds")),
        ).fetchone()
        if user is None:
            raise HTTPException(401, "Session expiree")
        rows = conn.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 50",
            (user["id"],),
        ).fetchall()
    finally:
        conn.close()
    return [row_to_dict(r) for r in rows]


@app.get("/api/orders/{reference}")
def get_order(reference: str, user = Depends(get_current_user_dep)):
    if not user:
        raise HTTPException(401, "Non authentifie")
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE reference = ?", (reference,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if not can_access_order(user, row):
        raise HTTPException(403, "Acces refuse a cette commande")
    return row_to_dict(row)


# ============================================================
# V2.1 - Dashboard pharmacien
# ============================================================

VALID_STATUSES = {"en_attente", "confirmee", "en_preparation", "prete", "terminee", "refusee", "en_livraison"}

# Transitions autorisees (patch robustesse)
ALLOWED_TRANSITIONS = {
    "en_attente": {"confirmee", "refusee"},
    "confirmee": {"en_preparation", "refusee"},
    "en_preparation": {"prete", "refusee"},
    "prete": {"terminee", "en_livraison"},

    "en_livraison": {"terminee"},
    "terminee": set(),
    "refusee": set(),
}


class StatusUpdate(BaseModel):
    status: str
    note: str = ""


@app.api_route("/pharmacien", methods=["GET", "HEAD"])
def page_pharmacien(request: Request):
    from v3_modules.auth import SESSION_COOKIE, load_user_from_cookie
    token = request.cookies.get(SESSION_COOKIE)
    row = load_user_from_cookie(get_db, token)
    if row is None:
        return RedirectResponse(url="/connexion?next=/pharmacien", status_code=302)
    if row["role"] not in ("PHARMACIEN", "ADMIN"):
        return RedirectResponse(url="/acces-refuse", status_code=302)
    return FileResponse(STATIC_DIR / "pharmacien.html")


@app.patch("/api/orders/{reference}/status")
def update_order_status(
    reference: str,
    payload: StatusUpdate,
    user = Depends(get_current_user_dep),
):
    if not user or user["role"] not in ("PHARMACIEN", "ADMIN"):
        raise HTTPException(403, "Seul le pharmacien peut changer le statut")
    new_status = payload.status.strip().lower()
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Statut invalide")

    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE reference = ?", (reference,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Demande introuvable")

    current_status = row["status"]
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        conn.close()
        raise HTTPException(status_code=400, detail="Transition de statut non autorisee")

    # Check metier : pas de livraison si mode retrait
    if new_status == "en_livraison" and row["delivery_mode"] != "livraison":
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Commande en retrait : pas de livraison possible"
        )

    conn.execute("UPDATE orders SET status = ? WHERE reference = ?", (new_status, reference))
    log_audit(conn, user["id"] if user else None,
              "order.status_change", "order", row["id"],
              "de " + current_status + " vers " + new_status)
    # V6 : enregistrer dans l'historique
    try:
        conn.execute(
            "INSERT INTO order_status_history (order_id, from_status, to_status,"
            " changed_at, changed_by, note)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (row["id"], row["status"], new_status,
             datetime.now().isoformat(timespec="seconds"), user["id"] if user else None,
            (getattr(payload, "note", "") or "").strip())
        )
    except Exception:
        pass
    conn.commit()
    # SSE : notifier le client (si proprietaire user_id)
    try:
        from v3_modules.notifications import push_notification
        _dest = row["user_id"]
        if _dest:
            _labels = {
                "confirmee": "Commande confirmee",
                "en_preparation": "Commande en preparation",
                "prete": "Commande prete",
                "en_livraison": "Commande en livraison",
                "terminee": "Commande terminee",
                "refusee": "Commande refusee",
            }
            push_notification(
                conn, _dest,
                _labels.get(new_status, "Commande mise a jour"),
                "Commande " + (reference or "") + " : " + new_status,
                order_id=row["id"],
            )
            conn.commit()
    except Exception:
        pass

    # === ETAPE 3.6 : gestion du refus ===
    if new_status == "refusee":
        # 1. Marquer les paiements actifs comme REFUND_REQUIRED
        try:
            pmt = conn.execute(
                "SELECT id, status FROM payments WHERE order_id = ? ORDER BY id DESC LIMIT 1",
                (row["id"],)
            ).fetchone()
            if pmt and pmt["status"] in ("PENDING", "PROOF_SUBMITTED", "VERIFIED"):
                conn.execute(
                    "UPDATE payments SET status='REFUND_REQUIRED', rejection_reason=? WHERE id=?",
                    ("Commande refusee - action requise", pmt["id"])
                )
                conn.execute(
                    "UPDATE orders SET payment_status='REFUND_REQUIRED' WHERE id=?",
                    (row["id"],)
                )
        except Exception as _e:
            pass

        # 2. Notifier les autres users de l'organisation (si PRO)
        try:
            _org = row["organization_id"] if "organization_id" in row.keys() else None
            _owner = row["user_id"] if "user_id" in row.keys() else None
            if _org:
                _users = conn.execute(
                    "SELECT id FROM users WHERE organization_id = ? AND is_active = 1",
                    (_org, _owner or 0)
                ).fetchall()
                from v3_modules.notifications import push_notification
                for _u in _users:
                    push_notification(
                        conn, _u["id"],
                        "Demande refusee",
                        "Votre demande " + (reference or "") + " a ete refusee.",
                        order_id=row["id"],
                    )
        except Exception as _e:
            pass
        conn.commit()
    updated = conn.execute("SELECT * FROM orders WHERE reference = ?", (reference,)).fetchone()
    conn.close()
    return row_to_dict(updated)


# BlockProOnPatientMiddleware (apres app cree)
try:
    app.add_middleware(BlockProOnPatientMiddleware)
except Exception as e:
    print(f"[BOOT] BlockProOnPatient err: {e}")



# ============================================================
# Endpoint specifique pharmacien : detail paiement d'une commande
# ============================================================
@app.get("/api/pharmacien/orders/{reference}/payment")
def pharm_get_order_payment(reference: str, user = Depends(get_current_user_dep)):
    """Retourne le paiement d'une commande (PHARMACIEN/ADMIN only)."""
    if user is None:
        raise HTTPException(401, "Non authentifie")
    if user["role"] not in ("PHARMACIEN", "ADMIN"):
        raise HTTPException(403, "Reserve au personnel pharmacie")
    conn = get_db()
    try:
        order = conn.execute(
            "SELECT * FROM orders WHERE reference = ?", (reference,)
        ).fetchone()
        if not order:
            raise HTTPException(404, "Commande introuvable")
        payment = conn.execute(
            "SELECT * FROM payments WHERE order_id = ? ORDER BY id DESC LIMIT 1",
            (order["id"],),
        ).fetchone()
        if not payment:
            return {"payment": None}
        return {"payment": row_to_dict(payment)}
    finally:
        conn.close()


# ============================================================
# Endpoint specifique pharmacien : ordonnance d'une commande
# ============================================================
@app.get("/api/pharmacien/orders/{reference}/prescription")
def pharm_get_order_prescription(reference: str, user = Depends(get_current_user_dep)):
    """Retourne l'ordonnance d'une commande (PHARMACIEN/ADMIN only)."""
    if user is None:
        raise HTTPException(401, "Non authentifie")
    if user["role"] not in ("PHARMACIEN", "ADMIN"):
        raise HTTPException(403, "Reserve au personnel pharmacie")
    conn = get_db()
    try:
        order = conn.execute(
            "SELECT * FROM orders WHERE reference = ?", (reference,)
        ).fetchone()
        if not order:
            raise HTTPException(404, "Commande introuvable")
        presc = conn.execute(
            "SELECT * FROM prescriptions WHERE order_id = ? ORDER BY id DESC LIMIT 1",
            (order["id"],),
        ).fetchone()
        if not presc:
            return {"prescription": None}
        return {"prescription": row_to_dict(presc)}
    finally:
        conn.close()





# ============================================================
# ETAPE 7 : Export CSV
# ============================================================
import csv
import io as _io

@app.get("/api/export/orders.csv")
def export_orders_csv(user = Depends(get_current_user_dep)):
    """Export CSV des commandes (PHARMACIEN/ADMIN)."""
    if user is None:
        raise HTTPException(401)
    if user["role"] not in ("PHARMACIEN", "ADMIN"):
        raise HTTPException(403)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT reference, status, payment_status, customer_name, phone,"
            " delivery_mode, subtotal, delivery_fee, created_at"
            " FROM orders ORDER BY id DESC"
        ).fetchall()
    finally:
        conn.close()
    buf = _io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Reference", "Statut", "Paiement", "Client", "Telephone",
                "Mode", "Sous-total", "Livraison", "Creee le"])
    for r in rows:
        w.writerow([r["reference"], r["status"], r["payment_status"],
                    r["customer_name"], r["phone"], r["delivery_mode"],
                    r["subtotal"], r["delivery_fee"], r["created_at"]])
    from fastapi.responses import Response as _R
    return _R(content=buf.getvalue(), media_type="text/csv",
              headers={"Content-Disposition": 'attachment; filename="commandes.csv"'})


@app.get("/api/export/payments.csv")
def export_payments_csv(user = Depends(get_current_user_dep)):
    """Export CSV des paiements (PHARMACIEN/ADMIN)."""
    if user is None:
        raise HTTPException(401)
    if user["role"] not in ("PHARMACIEN", "ADMIN"):
        raise HTTPException(403)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT p.id, p.status, p.amount, p.payment_method,"
            " p.submitted_at, p.verified_at, p.rejection_reason,"
            " o.reference AS order_ref, o.customer_name"
            " FROM payments p JOIN orders o ON o.id = p.order_id"
            " ORDER BY p.id DESC"
        ).fetchall()
    finally:
        conn.close()
    buf = _io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["ID", "Statut", "Montant", "Methode", "Soumis le",
                "Verifie le", "Motif", "Commande", "Client"])
    for r in rows:
        w.writerow([r["id"], r["status"], r["amount"], r["payment_method"],
                    r["submitted_at"], r["verified_at"], r["rejection_reason"],
                    r["order_ref"], r["customer_name"]])
    from fastapi.responses import Response as _R
    return _R(content=buf.getvalue(), media_type="text/csv",
              headers={"Content-Disposition": 'attachment; filename="paiements.csv"'})


app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# --- Cache bust V4 : no-store sur tout /static ---
class NoCacheAllStatic(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheAllStatic)


# ============================================================
# V8 - Clear-Site-Data pour Safari iOS
# Force Safari a vider son cache HTTP pour ce domaine a chaque HTML servi.
# ============================================================
class ClearSiteDataMiddleware(BaseHTTPMiddleware):
    """Clear-Site-Data uniquement sur les pages de login/register pour
    eviter les reloads brutaux sur chaque navigation."""
    PATHS = ("/connexion", "/inscription", "/login.html", "/register.html")
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        if any(path.startswith(p) for p in self.PATHS):
            ctype = response.headers.get("content-type", "").lower()
            if "text/html" in ctype:
                response.headers["Clear-Site-Data"] = '"cache"'
                response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
        return response

# Enregistrement direct (pas dans un try) — on est sur que BaseHTTPMiddleware est importe
app.add_middleware(ClearSiteDataMiddleware)

# ============================================================
# V7 - No-cache sur les routes HTML propres
# (les /static/ ont deja leur no-cache via NoCacheAllStatic)
# ============================================================
from starlette.middleware.base import BaseHTTPMiddleware
class NoCacheHTMLMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        ctype = response.headers.get("content-type", "").lower()
        # No-cache uniquement pour les pages HTML (routes + /static/*.html)
        if "text/html" in ctype:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response
try:
    app.add_middleware(NoCacheHTMLMiddleware)
except Exception:
    pass


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def root(request: Request):
    from v3_modules.auth import SESSION_COOKIE, load_user_from_cookie
    token = request.cookies.get(SESSION_COOKIE)
    row = load_user_from_cookie(get_db, token)
    if row is not None:
        role = row["role"]
        if role == "PROFESSIONNEL":
            return RedirectResponse(url="/professionnel", status_code=302)
        if role in ("PHARMACIEN", "ADMIN"):
            return RedirectResponse(url="/pharmacien", status_code=302)
    return FileResponse(STATIC_DIR / "index.html")


class DriverCreate(BaseModel):
    name: str
    phone: str


class DriverUpdate(BaseModel):
    is_active: bool


@app.get("/api/drivers")
def list_drivers(include_inactive: int = 0,
                 user = Depends(get_current_user_dep)):
    if not user or user["role"] not in ("PHARMACIEN", "ADMIN"):
        raise HTTPException(403, "Reserve au personnel pharmacie")
    conn = get_db()
    if include_inactive:
        rows = conn.execute(
            "SELECT * FROM drivers ORDER BY is_active DESC, name COLLATE NOCASE"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM drivers WHERE is_active = 1 ORDER BY name COLLATE NOCASE"
        ).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@app.post("/api/drivers")
def create_driver(payload: DriverCreate,
                  user = Depends(get_current_user_dep)):
    if not user or user["role"] not in ("PHARMACIEN", "ADMIN"):
        raise HTTPException(403, "Reserve au personnel pharmacie")
    name = payload.name.strip()
    phone = payload.phone.strip()
    if not name or not phone:
        raise HTTPException(status_code=400, detail="Nom et telephone obligatoires")
    created_at = datetime.now().isoformat(timespec="seconds")
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO drivers (name, phone, is_active, created_at) VALUES (?, ?, 1, ?)",
        (name, phone, created_at),
    )
    conn.commit()
    log_audit(conn, user["id"] if user else None,
              "driver.create", "driver", cur.lastrowid,
              "nom=" + name + " tel=" + phone)
    conn.commit()
    row = conn.execute("SELECT * FROM drivers WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return row_to_dict(row)


@app.patch("/api/drivers/{driver_id}")
def update_driver(driver_id: int, payload: DriverUpdate,
                  user = Depends(get_current_user_dep)):
    if not user or user["role"] not in ("PHARMACIEN", "ADMIN"):
        raise HTTPException(403, "Reserve au personnel pharmacie")
    conn = get_db()
    row = conn.execute("SELECT * FROM drivers WHERE id = ?", (driver_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Livreur introuvable")
    conn.execute(
        "UPDATE drivers SET is_active = ? WHERE id = ?",
        (1 if payload.is_active else 0, driver_id),
    )
    log_audit(conn, user["id"] if user else None,
              "driver.toggle", "driver", driver_id,
              "actif=" + ("1" if payload.is_active else "0"))
    conn.commit()
    row = conn.execute("SELECT * FROM drivers WHERE id = ?", (driver_id,)).fetchone()
    conn.close()
    return row_to_dict(row)


# ============================================================
# V2.3 - Parametres pharmacie
# ============================================================

class SettingsUpdate(BaseModel):
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


@app.get("/api/settings")
def get_settings():
    conn = get_db()
    row = conn.execute("SELECT * FROM pharmacy_settings WHERE id = 1").fetchone()
    conn.close()
    if row is None:
        return {"delivery_fee_default": 0}
    return row_to_dict(row)


@app.patch("/api/settings")
def update_settings(payload: SettingsUpdate,
                    user = Depends(get_current_user_dep)):
    if not user or user["role"] not in ("PHARMACIEN", "ADMIN"):
        raise HTTPException(403, "Reserve au personnel pharmacie")
    fields = payload.dict(exclude_unset=True, exclude_none=True)

    validators = {
        "delivery_fee_default": (0, 1000000, "Frais par defaut"),
        "delivery_base_fee": (0, 1000000, "Frais de base"),
        "delivery_price_per_km": (0, 1000000, "Prix par km"),
        "delivery_max_km": (0, 1000, "Distance maximale"),
    }
    for name, (vmin, vmax, label) in validators.items():
        if name in fields:
            try:
                v = float(fields[name])
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail=label + " : valeur invalide")
            if v < vmin or v > vmax:
                raise HTTPException(status_code=400, detail=label + " : valeur hors limites")
            fields[name] = v

    if "pharmacy_latitude" in fields:
        try:
            lat = float(fields["pharmacy_latitude"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Latitude invalide")
        if lat < -90 or lat > 90:
            raise HTTPException(status_code=400, detail="Latitude invalide")
        fields["pharmacy_latitude"] = lat

    if "pharmacy_longitude" in fields:
        try:
            lon = float(fields["pharmacy_longitude"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Longitude invalide")
        if lon < -180 or lon > 180:
            raise HTTPException(status_code=400, detail="Longitude invalide")
        fields["pharmacy_longitude"] = lon

    conn = get_db()
    # Valider les champs numériques
    numeric_validators = {
        "delivery_fee_default": (0, 1000000),
        "delivery_base_fee": (0, 1000000),
        "delivery_price_per_km": (0, 1000000),
        "motorbike_base_fee": (0, 1000000),
        "motorbike_price_per_km": (0, 1000000),
        "motorbike_minimum_fee": (0, 1000000),
        "car_base_fee": (0, 1000000),
        "car_price_per_km": (0, 1000000),
        "car_minimum_fee": (0, 1000000),
        "delivery_max_km": (0, 1000),
    }
    for name, (vmin, vmax) in numeric_validators.items():
        if name in fields:
            try:
                v = float(fields[name])
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail=name + " : valeur invalide")
            if v < vmin or v > vmax:
                raise HTTPException(status_code=400, detail=name + " : valeur hors limites")
            fields[name] = v

    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO pharmacy_settings (id) VALUES (1)")
    if fields:
        set_clause = ", ".join(k + " = ?" for k in fields.keys())
        params = list(fields.values())
        conn.execute("UPDATE pharmacy_settings SET " + set_clause + " WHERE id = 1", params)
    conn.commit()
    try:
        log_audit(conn, user["id"] if user else None,
                  "settings.update", "settings", 1,
                  "champs=" + ",".join(fields.keys()))
        conn.commit()
    except Exception:
        pass
    row = conn.execute("SELECT * FROM pharmacy_settings WHERE id = 1").fetchone()
    conn.close()
    return row_to_dict(row)



@app.api_route("/compte", methods=["GET", "HEAD"], include_in_schema=False)
def page_compte():
    return FileResponse(STATIC_DIR / "patient_compte.html")


@app.api_route("/checkout", methods=["GET", "HEAD"], include_in_schema=False)
def page_checkout():
    return FileResponse(STATIC_DIR / "checkout.html")


@app.api_route("/notifications.html", methods=["GET", "HEAD"], include_in_schema=False)
def page_notifications():
    return FileResponse(STATIC_DIR / "notifications.html")


@app.api_route("/payment.html", methods=["GET", "HEAD"], include_in_schema=False)
def page_payment():
    return FileResponse(STATIC_DIR / "payment.html")


@app.api_route("/suivi", methods=["GET", "HEAD"])
def suivi_page():
    return FileResponse(STATIC_DIR / "suivi.html")


# ============================================================
# V3 - Migrations + Auth
# ============================================================
from v3_modules.migrations import run_migrations
from v3_modules.auth import install_auth


# ============================================================
# V4 - Routes propres (Sprint A)
# ============================================================

@app.api_route("/connexion", methods=["GET", "HEAD"], include_in_schema=False)
def page_connexion(request: Request):
    from v3_modules.auth import SESSION_COOKIE, load_user_from_cookie
    token = request.cookies.get(SESSION_COOKIE)
    row = load_user_from_cookie(get_db, token)
    if row is not None:
        role = row["role"]
        if role == "PROFESSIONNEL":
            return RedirectResponse(url="/professionnel", status_code=302)
        if role in ("PHARMACIEN", "ADMIN"):
            return RedirectResponse(url="/pharmacien", status_code=302)
        return RedirectResponse(url="/", status_code=302)
    return FileResponse(STATIC_DIR / "login.html")


@app.api_route("/inscription", methods=["GET", "HEAD"], include_in_schema=False)
def page_inscription(request: Request):
    from v3_modules.auth import SESSION_COOKIE, load_user_from_cookie
    token = request.cookies.get(SESSION_COOKIE)
    row = load_user_from_cookie(get_db, token)
    if row is not None:
        role = row["role"]
        if role == "PROFESSIONNEL":
            return RedirectResponse(url="/professionnel", status_code=302)
        if role in ("PHARMACIEN", "ADMIN"):
            return RedirectResponse(url="/pharmacien", status_code=302)
        return RedirectResponse(url="/", status_code=302)
    return FileResponse(STATIC_DIR / "register.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon_ico():
    return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")



@app.api_route("/acces-refuse", methods=["GET", "HEAD"], include_in_schema=False)
def page_acces_refuse():
    return FileResponse(STATIC_DIR / "acces_refuse.html", status_code=403)


@app.api_route("/professionnel", methods=["GET", "HEAD"], include_in_schema=False)
def page_professionnel(request: Request):
    # Phase 3b : acces protege + redirection si profil incomplet
    from v3_modules.auth import SESSION_COOKIE, load_user_from_cookie
    token = request.cookies.get(SESSION_COOKIE)
    row = load_user_from_cookie(get_db, token)
    if row is None:
        return RedirectResponse(url="/connexion?next=/professionnel", status_code=302)
    role = row["role"]
    if role != "PROFESSIONNEL":
        return RedirectResponse(url="/acces-refuse", status_code=302)
    if not row["organization_id"]:
        return RedirectResponse(url="/professionnel/etablissement", status_code=302)
    return FileResponse(STATIC_DIR / "professional.html")



@app.api_route("/professionnel/catalogue", methods=["GET", "HEAD"], include_in_schema=False)
def page_pro_catalogue():
    return FileResponse(STATIC_DIR / "professional_catalogue.html")


@app.api_route("/professionnel/commandes", methods=["GET", "HEAD"], include_in_schema=False)
def page_pro_commandes():
    return FileResponse(STATIC_DIR / "professional_commandes.html")




@app.api_route("/professionnel/etablissement", methods=["GET", "HEAD"], include_in_schema=False)
def page_pro_etablissement():
    return FileResponse(STATIC_DIR / "professional_etablissement.html")



@app.api_route("/professionnel/demande", methods=["GET", "HEAD"], include_in_schema=False)
def page_pro_demande():
    return FileResponse(STATIC_DIR / "professional_demande.html")



@app.get("/professionnel/demande/confirmer", include_in_schema=False)
def page_pro_demande_confirmer():
    return FileResponse(STATIC_DIR / "professional_demande_confirmer.html")



@app.get("/professionnel/commande/{reference}/reprendre", include_in_schema=False)
def page_pro_reprendre(reference: str):
    return FileResponse(STATIC_DIR / "professional_reprendre.html")


init_db()
run_migrations(DB_PATH)
require_role = install_auth(app, get_db, row_to_dict)
from v3_modules.professionals import install_professionals
install_professionals(app, get_db, require_role)
from v3_modules.cart import install_cart
install_cart(app, get_db, require_role, compute_delivery_fee)
from v3_modules.payments import install_payments
install_payments(app, get_db, require_role, UPLOADS_DIR)
from v3_modules.prescriptions import install_prescriptions
install_prescriptions(app, get_db, require_role, UPLOADS_DIR)
from v3_modules.deliveries import install_deliveries
from v3_modules.notifications import install_notifications, push_notification
from v3_modules.admin import install_admin
install_deliveries(app, get_db, require_role)
install_notifications(app, get_db, require_role)
from v3_modules.notifications_stream import install_notifications_stream
install_notifications_stream(app, get_db)
install_admin(app, get_db, require_role)
from v3_modules.pro_features import install_pro_features
install_pro_features(app, get_db, require_role)
from v3_modules.b2b_requests import install_b2b
install_b2b(app, get_db, require_role, UPLOADS_DIR)
from v3_modules.order_timeline import install_order_timeline
install_order_timeline(app, get_db, require_role)

# ============================================================





# ============================================================
# LOT 5 - Statistiques fiables (PHARMACIEN/ADMIN)
# ============================================================
@app.get("/api/stats/summary")
def stats_summary(user = Depends(get_current_user_dep)):
    """Statistiques completes : series temporelles, top produits, top clients."""
    if not user or user["role"] not in ("PHARMACIEN", "ADMIN"):
        raise HTTPException(403, "Reserve au personnel pharmacie")
    from datetime import timedelta
    conn = get_db()
    try:
        # Commandes par statut
        by_status = {}
        for r in conn.execute(
            "SELECT status, COUNT(*) AS n FROM orders GROUP BY status"
        ).fetchall():
            by_status[r["status"]] = r["n"]

        # Total commandes
        total = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]

        # Aujourd'hui
        today = datetime.now().strftime("%Y-%m-%d")
        today_orders = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE created_at LIKE ?",
            (today + "%",)
        ).fetchone()[0]

        # Revenus du jour (hors refusees)
        today_revenue = 0.0
        try:
            row = conn.execute(
                "SELECT COALESCE(SUM(subtotal + delivery_fee), 0) AS rev"
                " FROM orders WHERE created_at LIKE ? AND status != 'refusee'",
                (today + "%",)
            ).fetchone()
            today_revenue = float(row["rev"] or 0) if row else 0.0
        except Exception:
            pass

        # Paiements par statut (montants)
        pay_by_status = {}
        for r in conn.execute(
            "SELECT status, COUNT(*) AS n, COALESCE(SUM(amount),0) AS total"
            " FROM payments GROUP BY status"
        ).fetchall():
            pay_by_status[r["status"]] = {
                "count": r["n"],
                "amount": float(r["total"]),
            }

        # Paiements en attente de verification
        pending_verify = conn.execute(
            "SELECT COUNT(*) FROM payments WHERE status='PROOF_SUBMITTED'"
        ).fetchone()[0]

        # Remboursements requis
        refund_required = conn.execute(
            "SELECT COUNT(*) FROM payments WHERE status='REFUND_REQUIRED'"
        ).fetchone()[0]

        # === Series 30 jours ===
        daily_series = []
        today_d = datetime.now().date()
        for i in range(29, -1, -1):
            day = today_d - timedelta(days=i)
            day_str = day.isoformat()
            row = conn.execute(
                "SELECT COUNT(*) AS n, COALESCE(SUM(subtotal + delivery_fee),0) AS rev"
                " FROM orders WHERE created_at LIKE ?",
                (day_str + "%",)
            ).fetchone()
            daily_series.append({
                "date": day_str,
                "orders": row["n"],
                "revenue": float(row["rev"] or 0),
            })

        # === Top produits ===
        top_products = []
        try:
            for r in conn.execute("""
                SELECT product_name, SUM(quantity) AS qty,
                       COUNT(DISTINCT order_id) AS nb
                FROM order_items
                GROUP BY product_name
                ORDER BY qty DESC
                LIMIT 10
            """).fetchall():
                top_products.append({
                    "name": r["product_name"] or "(sans nom)",
                    "quantity": int(r["qty"] or 0),
                    "orders": int(r["nb"] or 0),
                })
        except Exception:
            pass

        # === Top clients ===
        top_clients = []
        try:
            for r in conn.execute("""
                SELECT customer_name, phone, COUNT(*) AS nb,
                       COALESCE(SUM(subtotal + delivery_fee),0) AS spent
                FROM orders
                WHERE status != 'refusee'
                GROUP BY phone
                ORDER BY spent DESC
                LIMIT 10
            """).fetchall():
                top_clients.append({
                    "name": r["customer_name"] or "(anonyme)",
                    "phone": r["phone"] or "",
                    "orders": int(r["nb"] or 0),
                    "spent": float(r["spent"] or 0),
                })
        except Exception:
            pass

        # === Categories ===
        categories = {}
        try:
            for r in conn.execute("""
                SELECT p.category AS cat, SUM(oi.quantity) AS qty
                FROM order_items oi
                LEFT JOIN products p ON p.id = oi.product_id
                GROUP BY p.category
                ORDER BY qty DESC
                LIMIT 8
            """).fetchall():
                categories[r["cat"] or "Divers"] = int(r["qty"] or 0)
        except Exception:
            pass

        # === Methodes de paiement ===
        payment_methods = {}
        try:
            for r in conn.execute(
                "SELECT COALESCE(payment_method,'INCONNU') AS m, COUNT(*) AS n"
                " FROM payments GROUP BY payment_method"
            ).fetchall():
                payment_methods[r["m"]] = int(r["n"] or 0)
        except Exception:
            pass

        # === Panier moyen ===
        avg_basket = 0.0
        try:
            row = conn.execute(
                "SELECT AVG(subtotal + delivery_fee) AS m FROM orders"
                " WHERE status != 'refusee'"
            ).fetchone()
            avg_basket = float(row["m"] or 0) if row else 0.0
        except Exception:
            pass

        # === Repartition horaire (heure de commande) ===
        hourly = [0] * 24
        try:
            for r in conn.execute(
                "SELECT created_at FROM orders"
            ).fetchall():
                ca = r["created_at"] or ""
                if len(ca) >= 13:
                    try:
                        h = int(ca[11:13])
                        if 0 <= h < 24:
                            hourly[h] += 1
                    except Exception:
                        pass
        except Exception:
            pass

        return {
            "total_orders": total,
            "today_orders": today_orders,
            "today_revenue": today_revenue,
            "by_status": by_status,
            "payments_by_status": pay_by_status,
            "pending_verify": pending_verify,
            "refund_required": refund_required,
            "daily_series": daily_series,
            "top_products": top_products,
            "top_clients": top_clients,
            "categories": categories,
            "payment_methods": payment_methods,
            "avg_basket": avg_basket,
            "hourly": hourly,
        }
    finally:
        conn.close()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

# ============================================================
# PHASE 3 - Route protegee pour fichiers sensibles
# ============================================================
import re as _re

_FILE_CATEGORIES = {"proofs", "prescriptions", "requests"}

@app.get("/api/files/{category}/{filename}")
def serve_protected_file(
    category: str,
    filename: str,
    user = Depends(get_current_user_dep),
):
    """Sert un fichier sensible (preuve, ordonnance, piece jointe) avec auth."""
    if user is None:
        raise HTTPException(401, "Non authentifie")

    # 1. Whitelist categorie
    if category not in _FILE_CATEGORIES:
        raise HTTPException(404, "Ressource introuvable")

    # 2. Anti path traversal : nom strict
    if (".." in filename or "/" in filename or "\\" in filename
        or not _re.match(r'^[A-Za-z0-9_.-]+$', filename)):
        raise HTTPException(400, "Nom invalide")

    # 3. Chemin resolu dans UPLOADS_DIR / category
    base = (UPLOADS_DIR / category).resolve()
    target = (base / filename).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise HTTPException(400, "Chemin invalide")
    if not target.exists() or not target.is_file():
        raise HTTPException(404, "Fichier introuvable")

    # 4. Verifier rattachement a une commande accessible
    role = user["role"]
    rel_path = "/uploads/" + category + "/" + filename

    conn = get_db()
    try:
        # Log consultation (Faille E)
        log_audit(conn, user["id"], "file.access", category, filename, rel_path)

        # PHARMACIEN / ADMIN : acces total
        if role in ("PHARMACIEN", "ADMIN"):
            return FileResponse(str(target))

        # PATIENT / PROFESSIONNEL : verifier rattachement
        if role in ("PATIENT", "PROFESSIONNEL"):
            # Preuve de paiement ?
            if category == "proofs":
                p = conn.execute(
                    "SELECT o.user_id, o.organization_id FROM payments pmt"
                    " JOIN orders o ON o.id = pmt.order_id"
                    " WHERE pmt.proof_file = ? LIMIT 1",
                    (rel_path,),
                ).fetchone()
                if p and (p["user_id"] == user["id"] or
                          (p["organization_id"] and p["organization_id"] == user.get("organization_id"))):
                    return FileResponse(str(target))
            # Ordonnance ?
            if category == "prescriptions":
                p = conn.execute(
                    "SELECT o.user_id FROM prescriptions p"
                    " JOIN orders o ON o.id = p.order_id"
                    " WHERE p.file_path = ? LIMIT 1",
                    (rel_path,),
                ).fetchone()
                if p and p["user_id"] == user["id"]:
                    return FileResponse(str(target))
            # Piece jointe B2B
            if category == "requests":
                p = conn.execute(
                    "SELECT organization_id FROM request_attachments"
                    " WHERE storage_path = ? LIMIT 1",
                    (rel_path,),
                ).fetchone()
                if p and p["organization_id"] == user.get("organization_id"):
                    return FileResponse(str(target))

        raise HTTPException(403, "Acces refuse")
    finally:
        conn.close()


# ============================================================
# PHASE 3 - Routes notes internes
# ============================================================
class OrderNoteCreate(BaseModel):
    body: str


@app.get("/api/orders/{reference}/notes")
def list_order_notes(reference: str, user = Depends(get_current_user_dep)):
    """Liste les notes internes d'une commande (PHARMACIEN/ADMIN uniquement)."""
    if user is None:
        raise HTTPException(401)
    if user["role"] not in ("PHARMACIEN", "ADMIN"):
        raise HTTPException(403, "Reserve au personnel pharmacie")
    conn = get_db()
    try:
        order = conn.execute(
            "SELECT id FROM orders WHERE reference = ?", (reference,)
        ).fetchone()
        if not order:
            raise HTTPException(404, "Commande introuvable")
        rows = conn.execute(
            "SELECT n.id, n.body, n.created_at, u.full_name AS author"
            " FROM order_notes n LEFT JOIN users u ON u.id = n.author_id"
            " WHERE n.order_id = ? ORDER BY n.created_at DESC",
            (order["id"],),
        ).fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()


@app.post("/api/orders/{reference}/notes")
def add_order_note(
    reference: str,
    payload: OrderNoteCreate,
    user = Depends(get_current_user_dep),
):
    """Ajoute une note interne a une commande (PHARMACIEN/ADMIN uniquement)."""
    if user is None:
        raise HTTPException(401)
    if user["role"] not in ("PHARMACIEN", "ADMIN"):
        raise HTTPException(403, "Reserve au personnel pharmacie")
    body = (payload.body or "").strip()
    if not body:
        raise HTTPException(400, "Note vide")
    if len(body) > 2000:
        raise HTTPException(400, "Note trop longue (max 2000)")
    conn = get_db()
    try:
        order = conn.execute(
            "SELECT id FROM orders WHERE reference = ?", (reference,)
        ).fetchone()
        if not order:
            raise HTTPException(404, "Commande introuvable")
        now = datetime.now().isoformat(timespec="seconds")
        cur = conn.execute(
            "INSERT INTO order_notes (order_id, author_id, body, created_at)"
            " VALUES (?, ?, ?, ?)",
            (order["id"], user["id"], body, now),
        )
        conn.commit()
        return {"ok": True, "id": cur.lastrowid}
    finally:
        conn.close()


# ============================================================
# PHASE 3 - Bon de commande imprimable
# ============================================================
@app.get("/api/orders/{reference}/print", response_class=HTMLResponse)
def print_order(reference: str, user = Depends(get_current_user_dep)):
    """Bon de commande imprimable (PHARMACIEN/ADMIN uniquement)."""
    from fastapi.responses import HTMLResponse as _HR
    if user is None:
        raise HTTPException(401)
    if user["role"] not in ("PHARMACIEN", "ADMIN"):
        raise HTTPException(403, "Reserve au personnel pharmacie")
    conn = get_db()
    try:
        o = conn.execute(
            "SELECT * FROM orders WHERE reference = ?", (reference,)
        ).fetchone()
        if not o:
            raise HTTPException(404, "Commande introuvable")
        items = conn.execute(
            "SELECT * FROM order_items WHERE order_id = ? ORDER BY id",
            (o["id"],),
        ).fetchall()
        settings = conn.execute(
            "SELECT * FROM pharmacy_settings WHERE id=1"
        ).fetchone()
    finally:
        conn.close()

    sub = float(o["subtotal"] or 0)
    fee = float(o["delivery_fee"] or 0)
    tot = round(sub + fee, 2)

    def money(v):
        try:
            return "{:,.0f}".format(v).replace(",", " ") + " FCFA"
        except Exception:
            return str(v) + " FCFA"

    rows_html = ""
    if items:
        for it in items:
            rows_html += (
                "<tr><td>" + (it["product_name"] or "") + "</td>"
                "<td style='text-align:right'>" + str(it["quantity"]) + "</td>"
                "<td style='text-align:right'>" + money(it["unit_price"]) + "</td>"
                "<td style='text-align:right'>" + money(it["subtotal"]) + "</td></tr>"
            )
    else:
        rows_html = (
            "<tr><td>" + (o["product_name"] or "") + "</td>"
            "<td style='text-align:right'>" + str(o["quantity"]) + "</td>"
            "<td style='text-align:right'>" + money(o["price"]) + "</td>"
            "<td style='text-align:right'>" + money(sub) + "</td></tr>"
        )

    ph_name = settings["pharmacy_name"] if settings and "pharmacy_name" in settings.keys() else "Elonikab Health"
    ph_phone = settings["pharmacy_phone"] if settings and "pharmacy_phone" in settings.keys() else ""
    ph_addr = settings["pharmacy_address"] if settings and "pharmacy_address" in settings.keys() else ""

    html = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Bon de commande """ + reference + """</title>
<style>
  body{font-family:Segoe UI,system-ui,sans-serif;color:#0f172a;background:#fff;padding:20px}
  .card{max-width:680px;margin:0 auto;padding:32px;border:1px solid #e2e8f0;border-radius:12px}
  h1{margin:0 0 4px;color:#174A7E;font-size:22px}
  .ref{font-family:Consolas,monospace;color:#64748b;font-size:13px;margin-bottom:16px}
  .head{display:flex;justify-content:space-between;gap:20px;margin-bottom:20px}
  .head > div{flex:1}
  .lbl{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#64748b;font-weight:800}
  table{width:100%;border-collapse:collapse;margin:18px 0;font-size:14px}
  th,td{padding:8px 4px;border-bottom:1px solid #e2e8f0;text-align:left}
  th{background:#E8F0F8;color:#0F3457;font-size:11px;text-transform:uppercase}
  .total{font-size:20px;font-weight:800;color:#174A7E;text-align:right;margin-top:12px}
  .foot{margin-top:32px;font-size:11px;color:#64748b;text-align:center;border-top:1px solid #e2e8f0;padding-top:12px}
  @media print{body{padding:0}.card{border:0;box-shadow:none}}
</style></head><body>
<div class="card">
  <h1>""" + ph_name + """</h1>
  <div style="font-size:12px;color:#64748b;margin-bottom:14px">""" + ph_addr + " - " + ph_phone + """</div>
  <div class="ref">BON DE COMMANDE - """ + reference + """ - """ + (o["created_at"] or "")[:16] + """</div>
  <div class="head">
    <div>
      <div class="lbl">Client</div>
      <div><strong>""" + (o["customer_name"] or "") + """</strong></div>
      <div style="font-size:13px;color:#64748b">""" + (o["phone"] or "") + """</div>
    </div>
    <div>
      <div class="lbl">Mode</div>
      <div><strong>""" + ("Livraison" if o["delivery_mode"]=="livraison" else "Retrait") + """</strong></div>
      """ + (('<div style="font-size:13px;color:#64748b">' + (o["address"] or "") + '</div>') if o["delivery_mode"]=="livraison" else "") + """
    </div>
    <div>
      <div class="lbl">Statut</div>
      <div><strong>""" + (o["status"] or "") + """</strong></div>
    </div>
  </div>
  <table>
    <thead><tr><th>Produit</th><th style="text-align:right">Qte</th><th style="text-align:right">P.U.</th><th style="text-align:right">Total</th></tr></thead>
    <tbody>""" + rows_html + """</tbody>
  </table>
  <div style="text-align:right;font-size:13px">
    Sous-total : <strong>""" + money(sub) + """</strong><br>
    Livraison : <strong>""" + money(fee) + """</strong>
  </div>
  <div class="total">Total : """ + money(tot) + """</div>
  <div class="foot">
    Bon de commande interne - """ + ph_name + """<br>
    Document genere le """ + datetime.now().strftime("%d/%m/%Y %H:%M") + """
  </div>
</div>
<script>window.print&&setTimeout(window.print,300)</script>
</body></html>"""
    return _HR(html)


