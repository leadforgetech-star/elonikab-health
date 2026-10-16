"""Migrations sures et idempotentes pour Elonikab Health V3."""
import sqlite3


SCHEMA_V3 = [
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        phone TEXT DEFAULT '',
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'PATIENT',
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT NOT NULL UNIQUE,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS addresses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        label TEXT DEFAULT '',
        full_address TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        is_default INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS professional_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        structure_name TEXT NOT NULL,
        structure_type TEXT NOT NULL,
        manager_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT DEFAULT '',
        address TEXT DEFAULT '',
        latitude REAL,
        longitude REAL,
        notes TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'PENDING',
        reviewed_at TEXT,
        reviewed_by INTEGER,
        rejection_reason TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER,
        product_name TEXT NOT NULL,
        unit_price REAL NOT NULL,
        quantity INTEGER NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS prescriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING',
        reviewed_at TEXT,
        reviewed_by INTEGER,
        comment TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        payment_method TEXT NOT NULL DEFAULT 'MANUAL',
        payment_number TEXT DEFAULT '',
        payment_name TEXT DEFAULT '',
        proof_file TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'PENDING',
        submitted_at TEXT,
        verified_at TEXT,
        verified_by INTEGER,
        rejection_reason TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS deliveries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL UNIQUE,
        vehicle_type TEXT NOT NULL,
        driver_id INTEGER,
        status TEXT NOT NULL DEFAULT 'ASSIGNED',
        assigned_at TEXT,
        accepted_at TEXT,
        picked_up_at TEXT,
        delivered_at TEXT,
        failed_at TEXT,
        notes TEXT DEFAULT '',
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        order_id INTEGER,
        channel TEXT NOT NULL DEFAULT 'IN_APP',
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        is_read INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        target_type TEXT DEFAULT '',
        target_id INTEGER,
        details TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )""",
    """CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)""",
    """CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)""",
    """CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)""",
    """CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)""",
    """CREATE TABLE IF NOT EXISTS carts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS cart_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cart_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id),
        UNIQUE (cart_id, product_id)
    )""",
    """CREATE INDEX IF NOT EXISTS idx_cart_items_cart ON cart_items(cart_id)""",
    """CREATE INDEX IF NOT EXISTS idx_cart_items_cart ON cart_items(cart_id)""",
    """CREATE TABLE IF NOT EXISTS driver_pins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        driver_id INTEGER NOT NULL UNIQUE,
        pin TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL UNIQUE,
        receipt_number TEXT NOT NULL UNIQUE,
        issued_at TEXT NOT NULL,
        html_path TEXT DEFAULT '',
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
    )""",
    """CREATE INDEX IF NOT EXISTS idx_receipts_order ON receipts(order_id)""",
]


ORDERS_NEW_COLS = [
    ("user_id", "INTEGER"),
    ("customer_type", "TEXT DEFAULT 'PARTICULIER'"),
    ("delivery_vehicle_type", "TEXT DEFAULT 'MOTO'"),
    ("payment_status", "TEXT DEFAULT 'PENDING'"),
    ("delivery_status", "TEXT DEFAULT 'NONE'"),
    ("prescription_status", "TEXT DEFAULT 'NONE'"),
    ("professional_id", "INTEGER"),
]

PRODUCTS_NEW_COLS = [
    ("stock_quantity", "INTEGER DEFAULT 0"),
    ("stock_min_threshold", "INTEGER DEFAULT 5"),
    ("is_active", "INTEGER DEFAULT 1"),
]

SETTINGS_NEW_COLS = [
    ("motorbike_base_fee", "REAL DEFAULT 300"),
    ("motorbike_price_per_km", "REAL DEFAULT 100"),
    ("motorbike_minimum_fee", "REAL DEFAULT 300"),
    ("motorbike_max_distance", "REAL DEFAULT 0"),
    ("car_base_fee", "REAL DEFAULT 1000"),
    ("car_price_per_km", "REAL DEFAULT 250"),
    ("car_minimum_fee", "REAL DEFAULT 1000"),
    ("car_max_distance", "REAL DEFAULT 0"),
    ("payment_number", "TEXT DEFAULT ''"),
    ("payment_name", "TEXT DEFAULT ''"),
    ("pharmacy_name", "TEXT DEFAULT 'Elonikab Health'"),
    ("pharmacy_phone", "TEXT DEFAULT ''"),
    ("pharmacy_address", "TEXT DEFAULT ''"),
]


def _cols(cur, table):
    return {row[1] for row in cur.execute("PRAGMA table_info(" + table + ")").fetchall()}


def _tables(cur):
    return {row[0] for row in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}


def _add_columns(cur, table, cols):
    existing = _cols(cur, table)
    for name, ddl in cols:
        if name not in existing:
            cur.execute("ALTER TABLE " + table + " ADD COLUMN " + name + " " + ddl)


def run_migrations(db_path):
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    for stmt in SCHEMA_V3:
        cur.execute(stmt)
    tables = _tables(cur)
    if "orders" in tables:
        _add_columns(cur, "orders", ORDERS_NEW_COLS)
    if "products" in tables:
        _add_columns(cur, "products", PRODUCTS_NEW_COLS)
    if "pharmacy_settings" in tables:
        _add_columns(cur, "pharmacy_settings", SETTINGS_NEW_COLS)
    conn.commit()
    conn.close()
    return True
