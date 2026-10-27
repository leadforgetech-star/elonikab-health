# -*- coding: utf-8 -*-
"""
LOT 7 - ETAPE C : API CRUD produits + upload image + stock
============================================================
Cree un module v3_modules/catalog_stock.py et le branche sur main.py.
Atomic, rollback auto si erreur.
"""
import os, shutil, datetime, sys, re

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
MAIN = os.path.join(ROOT, "main.py")
V3 = os.path.join(ROOT, "v3_modules")
NEW_MODULE = os.path.join(V3, "catalog_stock.py")

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, f"_backup_lot7_stepC_{TS}")
os.makedirs(BAK, exist_ok=True)

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]", "STEP": "\n###"}[k]
    print(p, m)

def syntax_ok(path):
    try:
        with open(path, "rb") as f:
            compile(f.read(), path, "exec")
        return True, None
    except SyntaxError as e:
        return False, f"L{e.lineno}: {e.msg}"

shutil.copy2(MAIN, os.path.join(BAK, "main.py"))

print("=" * 78)
print(f"LOT 7 - ETAPE C (API) - {TS}")
print("=" * 78)
print(f"[BACKUP] {BAK}\n")

# ============================================================
# MODULE catalog_stock.py
# ============================================================
MODULE_CODE = '''# -*- coding: utf-8 -*-
"""Elonikab Health - Module Catalogue & Stock (Lot 7)"""
from datetime import datetime
from pathlib import Path
from typing import Optional
import os, uuid, base64
from fastapi import HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel


ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_IMAGE_MB = 5

# Signature magique (magic bytes) pour valider le contenu reel
MAGIC_BYTES = {
    b"\\xff\\xd8\\xff": "image/jpeg",
    b"\\x89PNG\\r\\n\\x1a\\n": "image/png",
    b"RIFF": "image/webp",  # prefix, verif WEBP a offset 8
}


def _detect_image_type(data: bytes) -> Optional[str]:
    if data.startswith(b"\\xff\\xd8\\xff"):
        return "image/jpeg"
    if data.startswith(b"\\x89PNG\\r\\n\\x1a\\n"):
        return "image/png"
    if data.startswith(b"RIFF") and len(data) > 12 and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _log_audit(conn, user_id, action, target_type, target_id, details=""):
    try:
        conn.execute(
            "INSERT INTO audit_logs (user_id, action, target_type, target_id,"
            " details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, action, target_type, str(target_id) if target_id else None,
             details, datetime.now().isoformat(timespec="seconds"))
        )
    except Exception:
        pass


# === SCHEMAS ===
class ProductCreate(BaseModel):
    name: str
    presentation: str = ""
    description: str = ""
    category: str = "Divers"
    price: float
    requires_prescription: int = 0
    stock_quantity: Optional[int] = None
    stock_min_threshold: Optional[int] = 5
    availability: str = "disponible"


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    presentation: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    requires_prescription: Optional[int] = None
    stock_quantity: Optional[int] = None
    stock_min_threshold: Optional[int] = None
    availability: Optional[str] = None
    is_active: Optional[int] = None


class StockMovementCreate(BaseModel):
    product_id: int
    type: str  # IN, OUT, ADJUST, CANCEL
    quantity: int
    reason: str = ""
    reference: str = ""


class StockLotCreate(BaseModel):
    product_id: int
    lot_number: str
    expiry_date: Optional[str] = None
    quantity: int = 0


def install_catalog_stock(app, get_db, require_role, static_dir):
    """Installe les routes catalogue + stock."""
    IMG_DIR = os.path.join(str(static_dir), "images", "products", "uploads")
    os.makedirs(IMG_DIR, exist_ok=True)

    def _row(r):
        return {k: r[k] for k in r.keys()}

    # ============================================================
    # PRODUITS - CRUD
    # ============================================================
    @app.post("/api/admin/products")
    def create_product(payload: ProductCreate,
                       user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        name = (payload.name or "").strip()
        if not name or len(name) < 2:
            raise HTTPException(400, "Nom obligatoire (min 2 caracteres)")
        if payload.price is None or payload.price < 0:
            raise HTTPException(400, "Prix invalide")
        if payload.stock_quantity is not None and payload.stock_quantity < 0:
            raise HTTPException(400, "Stock negatif interdit")

        now = datetime.now().isoformat(timespec="seconds")
        conn = get_db()
        try:
            cur = conn.execute(
                "INSERT INTO products (name, presentation, description, category,"
                " price, requires_prescription, stock_quantity, stock_min_threshold,"
                " availability, is_active, is_demo, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?)",
                (name, payload.presentation.strip(), payload.description.strip(),
                 payload.category.strip() or "Divers", float(payload.price),
                 1 if payload.requires_prescription else 0,
                 payload.stock_quantity, payload.stock_min_threshold or 5,
                 payload.availability or "disponible", now)
            )
            pid = cur.lastrowid
            _log_audit(conn, user["id"], "product.create", "product", pid,
                       "nom=" + name)
            conn.commit()
            row = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
            return _row(row)
        finally:
            conn.close()

    @app.patch("/api/admin/products/{product_id}")
    def update_product(product_id: int, payload: ProductUpdate,
                       user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        fields = payload.dict(exclude_unset=True, exclude_none=True)
        if not fields:
            raise HTTPException(400, "Aucun champ a modifier")
        if "price" in fields and fields["price"] < 0:
            raise HTTPException(400, "Prix invalide")
        if "stock_quantity" in fields and fields["stock_quantity"] < 0:
            raise HTTPException(400, "Stock negatif interdit")
        if "name" in fields and len((fields["name"] or "").strip()) < 2:
            raise HTTPException(400, "Nom trop court")

        conn = get_db()
        try:
            row = conn.execute("SELECT * FROM products WHERE id = ?",
                              (product_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Produit introuvable")
            set_clause = ", ".join(k + " = ?" for k in fields.keys())
            params = list(fields.values()) + [product_id]
            conn.execute(f"UPDATE products SET {set_clause} WHERE id = ?", params)
            _log_audit(conn, user["id"], "product.update", "product", product_id,
                       "champs=" + ",".join(fields.keys()))
            conn.commit()
            row = conn.execute("SELECT * FROM products WHERE id = ?",
                              (product_id,)).fetchone()
            return _row(row)
        finally:
            conn.close()

    @app.delete("/api/admin/products/{product_id}")
    def archive_product(product_id: int,
                       user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            row = conn.execute("SELECT * FROM products WHERE id = ?",
                              (product_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Produit introuvable")
            # Archivage (jamais de suppression definitive)
            conn.execute("UPDATE products SET is_active = 0 WHERE id = ?",
                        (product_id,))
            _log_audit(conn, user["id"], "product.archive", "product", product_id,
                       "nom=" + (row["name"] or ""))
            conn.commit()
            return {"ok": True, "id": product_id, "archived": True}
        finally:
            conn.close()

    # ============================================================
    # IMAGES
    # ============================================================
    @app.post("/api/admin/products/{product_id}/images")
    async def upload_product_image(product_id: int,
                                   file: UploadFile = File(...),
                                   user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            row = conn.execute("SELECT id FROM products WHERE id = ?",
                              (product_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Produit introuvable")

            data = await file.read()
            if not data:
                raise HTTPException(400, "Fichier vide")
            if len(data) > MAX_IMAGE_MB * 1024 * 1024:
                raise HTTPException(400, f"Fichier trop gros (max {MAX_IMAGE_MB} Mo)")

            # Verifier magic bytes (contenu reel)
            detected = _detect_image_type(data)
            if detected not in ALLOWED_IMAGE_TYPES:
                raise HTTPException(400, "Format non autorise (JPG, PNG, WEBP)")

            ext = ALLOWED_IMAGE_TYPES[detected]
            fname = uuid.uuid4().hex + ext
            target = os.path.join(IMG_DIR, fname)
            with open(target, "wb") as f:
                f.write(data)

            now = datetime.now().isoformat(timespec="seconds")
            url = "/static/images/products/uploads/" + fname

            # Verifier si c'est la premiere image (is_primary)
            has_primary = conn.execute(
                "SELECT id FROM product_images WHERE product_id = ? AND is_primary = 1",
                (product_id,)
            ).fetchone()

            cur = conn.execute(
                "INSERT INTO product_images (product_id, file_path, is_primary,"
                " sort_order, created_at) VALUES (?, ?, ?, ?, ?)",
                (product_id, url, 0 if has_primary else 1, 0, now)
            )
            img_id = cur.lastrowid

            # Si pas d'image principale, on met aussi a jour products.image_url
            if not has_primary:
                conn.execute("UPDATE products SET image_url = ? WHERE id = ?",
                            (url, product_id))

            _log_audit(conn, user["id"], "product.image.upload", "product",
                       product_id, "image_id=" + str(img_id))
            conn.commit()
            return {"ok": True, "id": img_id, "url": url}
        finally:
            conn.close()

    @app.delete("/api/admin/products/{product_id}/images/{image_id}")
    def delete_product_image(product_id: int, image_id: int,
                            user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            img = conn.execute(
                "SELECT * FROM product_images WHERE id = ? AND product_id = ?",
                (image_id, product_id)
            ).fetchone()
            if not img:
                raise HTTPException(404, "Image introuvable")

            was_primary = bool(img["is_primary"])
            conn.execute("DELETE FROM product_images WHERE id = ?", (image_id,))

            # Si c'etait la principale, promouvoir la suivante
            if was_primary:
                nxt = conn.execute(
                    "SELECT id, file_path FROM product_images WHERE product_id = ?"
                    " ORDER BY sort_order ASC, id ASC LIMIT 1",
                    (product_id,)
                ).fetchone()
                if nxt:
                    conn.execute("UPDATE product_images SET is_primary = 1 WHERE id = ?",
                                (nxt["id"],))
                    conn.execute("UPDATE products SET image_url = ? WHERE id = ?",
                                (nxt["file_path"], product_id))
                else:
                    conn.execute("UPDATE products SET image_url = '' WHERE id = ?",
                                (product_id,))

            _log_audit(conn, user["id"], "product.image.delete", "product",
                       product_id, "image_id=" + str(image_id))
            conn.commit()
            return {"ok": True}
        finally:
            conn.close()

    @app.patch("/api/admin/products/{product_id}/images/{image_id}/primary")
    def set_primary_image(product_id: int, image_id: int,
                         user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            img = conn.execute(
                "SELECT * FROM product_images WHERE id = ? AND product_id = ?",
                (image_id, product_id)
            ).fetchone()
            if not img:
                raise HTTPException(404, "Image introuvable")
            conn.execute("UPDATE product_images SET is_primary = 0 WHERE product_id = ?",
                        (product_id,))
            conn.execute("UPDATE product_images SET is_primary = 1 WHERE id = ?",
                        (image_id,))
            conn.execute("UPDATE products SET image_url = ? WHERE id = ?",
                        (img["file_path"], product_id))
            _log_audit(conn, user["id"], "product.image.primary", "product",
                       product_id, "image_id=" + str(image_id))
            conn.commit()
            return {"ok": True}
        finally:
            conn.close()

    @app.get("/api/admin/products/{product_id}/images")
    def list_product_images(product_id: int,
                           user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT * FROM product_images WHERE product_id = ?"
                " ORDER BY is_primary DESC, sort_order ASC, id ASC",
                (product_id,)
            ).fetchall()
            return [_row(r) for r in rows]
        finally:
            conn.close()

    # ============================================================
    # STOCK
    # ============================================================
    @app.get("/api/admin/stock")
    def stock_overview(user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            rows = conn.execute("""
                SELECT id, name, category, price, stock_quantity,
                       stock_min_threshold, is_active, image_url, availability
                FROM products
                WHERE is_active = 1
                ORDER BY name COLLATE NOCASE
            """).fetchall()
            return [_row(r) for r in rows]
        finally:
            conn.close()

    @app.get("/api/admin/stock/alerts")
    def stock_alerts(user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        """Alertes rupture + stock faible + peremption."""
        conn = get_db()
        try:
            rupture = conn.execute("""
                SELECT id, name, stock_quantity, stock_min_threshold
                FROM products
                WHERE is_active = 1
                  AND stock_quantity IS NOT NULL
                  AND stock_quantity <= 0
                ORDER BY name
            """).fetchall()

            low = conn.execute("""
                SELECT id, name, stock_quantity, stock_min_threshold
                FROM products
                WHERE is_active = 1
                  AND stock_quantity IS NOT NULL
                  AND stock_quantity > 0
                  AND stock_quantity <= COALESCE(stock_min_threshold, 5)
                ORDER BY stock_quantity ASC
            """).fetchall()

            today = datetime.now().strftime("%Y-%m-%d")
            soon = datetime.now().timestamp() + 30*24*3600
            soon_date = datetime.fromtimestamp(soon).strftime("%Y-%m-%d")

            expiring = conn.execute("""
                SELECT l.id, l.product_id, l.lot_number, l.expiry_date, l.quantity,
                       p.name AS product_name
                FROM stock_lots l
                JOIN products p ON p.id = l.product_id
                WHERE l.expiry_date IS NOT NULL
                  AND l.expiry_date <= ?
                  AND l.quantity > 0
                ORDER BY l.expiry_date ASC
            """, (soon_date,)).fetchall()

            return {
                "rupture": [_row(r) for r in rupture],
                "low_stock": [_row(r) for r in low],
                "expiring_soon": [_row(r) for r in expiring],
            }
        finally:
            conn.close()

    @app.get("/api/admin/stock/movements")
    def list_movements(product_id: Optional[int] = None, limit: int = 100,
                      user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            if product_id:
                rows = conn.execute("""
                    SELECT m.*, p.name AS product_name
                    FROM stock_movements m
                    LEFT JOIN products p ON p.id = m.product_id
                    WHERE m.product_id = ?
                    ORDER BY m.id DESC LIMIT ?
                """, (product_id, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT m.*, p.name AS product_name
                    FROM stock_movements m
                    LEFT JOIN products p ON p.id = m.product_id
                    ORDER BY m.id DESC LIMIT ?
                """, (limit,)).fetchall()
            return [_row(r) for r in rows]
        finally:
            conn.close()

    @app.post("/api/admin/stock/movements")
    def create_movement(payload: StockMovementCreate,
                       user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        mtype = (payload.type or "").upper().strip()
        if mtype not in ("IN", "OUT", "ADJUST", "CANCEL"):
            raise HTTPException(400, "Type invalide (IN, OUT, ADJUST, CANCEL)")
        if payload.quantity == 0:
            raise HTTPException(400, "Quantite ne peut pas etre 0")
        if mtype == "ADJUST" and not (payload.reason or "").strip():
            raise HTTPException(400, "Motif obligatoire pour un ajustement")

        conn = get_db()
        try:
            prod = conn.execute("SELECT * FROM products WHERE id = ?",
                              (payload.product_id,)).fetchone()
            if not prod:
                raise HTTPException(404, "Produit introuvable")

            current = prod["stock_quantity"]
            if current is None:
                current = 0

            # Calcul du signe
            if mtype == "IN":
                delta = abs(payload.quantity)
            elif mtype == "OUT":
                delta = -abs(payload.quantity)
            elif mtype == "CANCEL":
                # Annulation : inverse du signe
                delta = -payload.quantity
            else:  # ADJUST
                delta = payload.quantity

            new_qty = current + delta
            if new_qty < 0:
                raise HTTPException(400,
                    f"Stock insuffisant. Disponible : {current}, "
                    f"operation demanderait : {new_qty}")

            now = datetime.now().isoformat(timespec="seconds")

            # Transaction
            conn.execute("BEGIN")
            try:
                conn.execute(
                    "INSERT INTO stock_movements (product_id, type, quantity,"
                    " reason, reference, user_id, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (payload.product_id, mtype, delta,
                     (payload.reason or "").strip(),
                     (payload.reference or "").strip(),
                     user["id"], now)
                )
                conn.execute("UPDATE products SET stock_quantity = ? WHERE id = ?",
                            (new_qty, payload.product_id))
                _log_audit(conn, user["id"], "stock.movement", "product",
                          payload.product_id,
                          f"{mtype} {delta:+d} -> {new_qty}")
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise HTTPException(500, "Erreur transaction : " + str(e))

            return {"ok": True, "new_quantity": new_qty, "delta": delta}
        finally:
            conn.close()

    @app.get("/api/admin/stock/lots")
    def list_lots(product_id: Optional[int] = None,
                 user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            if product_id:
                rows = conn.execute("""
                    SELECT l.*, p.name AS product_name
                    FROM stock_lots l
                    LEFT JOIN products p ON p.id = l.product_id
                    WHERE l.product_id = ?
                    ORDER BY l.expiry_date ASC NULLS LAST, l.id DESC
                """, (product_id,)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT l.*, p.name AS product_name
                    FROM stock_lots l
                    LEFT JOIN products p ON p.id = l.product_id
                    ORDER BY l.expiry_date ASC NULLS LAST, l.id DESC
                """).fetchall()
            return [_row(r) for r in rows]
        finally:
            conn.close()

    @app.post("/api/admin/stock/lots")
    def create_lot(payload: StockLotCreate,
                  user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        if not (payload.lot_number or "").strip():
            raise HTTPException(400, "Numero de lot obligatoire")
        conn = get_db()
        try:
            prod = conn.execute("SELECT id FROM products WHERE id = ?",
                              (payload.product_id,)).fetchone()
            if not prod:
                raise HTTPException(404, "Produit introuvable")

            now = datetime.now().isoformat(timespec="seconds")
            cur = conn.execute(
                "INSERT INTO stock_lots (product_id, lot_number, expiry_date,"
                " quantity, created_at) VALUES (?, ?, ?, ?, ?)",
                (payload.product_id, payload.lot_number.strip(),
                 payload.expiry_date, payload.quantity, now)
            )
            lot_id = cur.lastrowid
            _log_audit(conn, user["id"], "stock.lot.create", "product",
                      payload.product_id, f"lot={payload.lot_number}")
            conn.commit()
            return {"ok": True, "id": lot_id}
        finally:
            conn.close()

    print("[catalog_stock] Routes installees")
'''

open(NEW_MODULE, "w", encoding="utf-8").write(MODULE_CODE)

# Verifier syntaxe du module
ok, err = syntax_ok(NEW_MODULE)
if not ok:
    log(f"Module ERREUR : {err}", "ERR")
    shutil.copy2(os.path.join(BAK, "main.py"), MAIN)
    if os.path.isfile(NEW_MODULE):
        os.remove(NEW_MODULE)
    sys.exit(1)
log("Module catalog_stock.py cree (syntaxe OK)", "OK")

# ============================================================
# Branchement sur main.py
# ============================================================
print()
log("Branchement sur main.py", "STEP")

main_src = open(MAIN, "r", encoding="utf-8").read()

if "install_catalog_stock" in main_src:
    log("Deja branche", "WARN")
else:
    # Trouver l'ancre : "from v3_modules.order_timeline import install_order_timeline"
    anchor = "from v3_modules.order_timeline import install_order_timeline"
    if anchor not in main_src:
        log("Ancre d'installation introuvable", "ERR")
        shutil.copy2(os.path.join(BAK, "main.py"), MAIN)
        os.remove(NEW_MODULE)
        sys.exit(1)

    # Ajouter l'installation apres order_timeline
    old_block = anchor + "\ninstall_order_timeline(app, get_db, require_role)"
    new_block = (anchor + "\ninstall_order_timeline(app, get_db, require_role)"
                 + "\nfrom v3_modules.catalog_stock import install_catalog_stock"
                 + "\ninstall_catalog_stock(app, get_db, require_role, STATIC_DIR)")

    if old_block in main_src:
        main_src = main_src.replace(old_block, new_block, 1)
        open(MAIN, "w", encoding="utf-8").write(main_src)
        ok, err = syntax_ok(MAIN)
        if not ok:
            log(f"main.py ERREUR : {err}", "ERR")
            shutil.copy2(os.path.join(BAK, "main.py"), MAIN)
            os.remove(NEW_MODULE)
            sys.exit(1)
        log("main.py : install_catalog_stock branche", "OK")
    else:
        log("Bloc d'installation introuvable", "ERR")
        shutil.copy2(os.path.join(BAK, "main.py"), MAIN)
        os.remove(NEW_MODULE)
        sys.exit(1)

# ============================================================
# Verification
# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)

final_main = open(MAIN, "r", encoding="utf-8").read()
final_mod = open(NEW_MODULE, "r", encoding="utf-8").read()

checks = [
    ("Module cree",                     os.path.isfile(NEW_MODULE)),
    ("Module syntaxe OK",               syntax_ok(NEW_MODULE)[0]),
    ("main.py syntaxe OK",              syntax_ok(MAIN)[0]),
    ("Import branche",                  "from v3_modules.catalog_stock import" in final_main),
    ("Install appele",                  "install_catalog_stock(app" in final_main),
    ("5 routes produits",               final_mod.count("/api/admin/products") >= 5),
    ("5 routes stock",                  final_mod.count("/api/admin/stock") >= 5),
    ("Detection magic bytes",           "_detect_image_type" in final_mod),
    ("Audit log helper",                "_log_audit" in final_mod),
    ("Transaction stock",               "conn.execute(\"BEGIN\")" in final_mod),
]
for label, ok in checks:
    print(f"  [{'OK' if ok else '!!'}] {label}")

passed = sum(1 for _, ok in checks if ok)
print(f"\n  RESULTAT : {passed}/{len(checks)}")

print()
print(f"[BACKUP] {BAK}")
print()
print("[CMD] Restart Uvicorn :")
print("  taskkill /F /IM uvicorn.exe 2>nul")
print("  taskkill /F /IM python.exe 2>nul")
print("  cd \"" + ROOT + "\"")
print("  python -m uvicorn main:app --host 0.0.0.0 --port 8000")
print()
print("[TEST] Apres restart (script a venir) :")
print("  - POST /api/admin/products -> creer")
print("  - POST /api/admin/stock/movements -> IN 10")
print("  - DELETE /api/admin/products/{id} -> archive (pas delete)")
print()
print("[ROLLBACK] :")
print(f"  copy \"{BAK}\\main.py\" \"{MAIN}\"")
print(f"  del \"{NEW_MODULE}\"")