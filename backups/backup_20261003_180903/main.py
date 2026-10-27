import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import Cookie, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_UPLOADS = {"image/jpeg", "image/png", "image/webp", "image/heic", "application/pdf"}

app = FastAPI(title="Elonikab Health", version="2.1.0")




# --- Performance : compression GZip ---
app.add_middleware(GZipMiddleware, minimum_size=500)



def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    return {key: row[key] for key in row.keys()}


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
def list_products(q: str = "", category: str = ""):
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
):
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
def list_orders():
    conn = get_db()
    rows = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 100").fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@app.get("/api/orders/mine")
def list_my_orders(session_token: str = Cookie(None, alias="elokinab_session")):
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
def get_order(reference: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE reference = ?", (reference,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    return row_to_dict(row)


# ============================================================
# V2.1 - Dashboard pharmacien
# ============================================================

VALID_STATUSES = {"en_attente", "confirmee", "en_preparation", "prete", "terminee", "refusee"}

# Transitions autorisees (patch robustesse)
ALLOWED_TRANSITIONS = {
    "en_attente": {"confirmee", "refusee"},
    "confirmee": {"en_preparation", "refusee"},
    "en_preparation": {"prete", "refusee"},
    "prete": {"terminee"},
    "terminee": set(),
    "refusee": set(),
}


class StatusUpdate(BaseModel):
    status: str


@app.get("/pharmacien")
def pharmacien_page():
    return FileResponse(STATIC_DIR / "pharmacien.html")


@app.patch("/api/orders/{reference}/status")
def update_order_status(reference: str, payload: StatusUpdate):
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

    conn.execute("UPDATE orders SET status = ? WHERE reference = ?", (new_status, reference))
    conn.commit()
    updated = conn.execute("SELECT * FROM orders WHERE reference = ?", (reference,)).fetchone()
    conn.close()
    return row_to_dict(updated)


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

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


# ============================================================
# V2.2 - Livreurs
# ============================================================

class DriverCreate(BaseModel):
    name: str
    phone: str


class DriverUpdate(BaseModel):
    is_active: bool


@app.get("/api/drivers")
def list_drivers(include_inactive: int = 0):
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
def create_driver(payload: DriverCreate):
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
    row = conn.execute("SELECT * FROM drivers WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return row_to_dict(row)


@app.patch("/api/drivers/{driver_id}")
def update_driver(driver_id: int, payload: DriverUpdate):
    conn = get_db()
    row = conn.execute("SELECT * FROM drivers WHERE id = ?", (driver_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Livreur introuvable")
    conn.execute(
        "UPDATE drivers SET is_active = ? WHERE id = ?",
        (1 if payload.is_active else 0, driver_id),
    )
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
def update_settings(payload: SettingsUpdate):
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
    conn.execute("INSERT OR IGNORE INTO pharmacy_settings (id) VALUES (1)")
    if fields:
        set_clause = ", ".join(k + " = ?" for k in fields.keys())
        params = list(fields.values())
        conn.execute("UPDATE pharmacy_settings SET " + set_clause + " WHERE id = 1", params)
    conn.commit()
    row = conn.execute("SELECT * FROM pharmacy_settings WHERE id = 1").fetchone()
    conn.close()
    return row_to_dict(row)



@app.get("/suivi")
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

@app.get("/connexion", include_in_schema=False)
def page_connexion():
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/inscription", include_in_schema=False)
def page_inscription():
    return FileResponse(STATIC_DIR / "register.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon_ico():
    return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")



@app.get("/professionnel", include_in_schema=False)
def page_professionnel():
    return FileResponse(STATIC_DIR / "professional.html")



@app.get("/professionnel/catalogue", include_in_schema=False)
def page_pro_catalogue():
    return FileResponse(STATIC_DIR / "professional_catalogue.html")


@app.get("/professionnel/commandes", include_in_schema=False)
def page_pro_commandes():
    return FileResponse(STATIC_DIR / "professional_commandes.html")




@app.get("/professionnel/etablissement", include_in_schema=False)
def page_pro_etablissement():
    return FileResponse(STATIC_DIR / "professional_etablissement.html")



@app.get("/professionnel/demande", include_in_schema=False)
def page_pro_demande():
    return FileResponse(STATIC_DIR / "professional_demande.html")


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
from v3_modules.magic_links import install_magic_links
install_magic_links(app, get_db, require_role)
# ============================================================



if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)