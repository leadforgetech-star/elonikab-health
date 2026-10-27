"""Dashboard admin consolide (Phase 9)."""
from datetime import datetime

from fastapi import Depends


def install_admin(app, get_db, require_role):
    @app.get("/api/admin/dashboard")
    def dashboard(user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            def scalar(sql, params=()):
                r = conn.execute(sql, params).fetchone()
                return r[0] if r else 0

            today = datetime.now().strftime("%Y-%m-%d")

            stats = {
                "orders_total": scalar("SELECT COUNT(*) FROM orders"),
                "orders_today": scalar(
                    "SELECT COUNT(*) FROM orders WHERE created_at LIKE ?",
                    (today + "%",),
                ),
                "orders_pending": scalar(
                    "SELECT COUNT(*) FROM orders WHERE status = 'en_attente'"
                ),
                "orders_preparing": scalar(
                    "SELECT COUNT(*) FROM orders WHERE status = 'en_preparation'"
                ),
                "orders_ready": scalar(
                    "SELECT COUNT(*) FROM orders WHERE status = 'prete'"
                ),
                "payments_pending": scalar(
                    "SELECT COUNT(*) FROM payments WHERE status = 'PROOF_SUBMITTED'"
                ),
                "payments_verified_today": scalar(
                    "SELECT COUNT(*) FROM payments WHERE status = 'VERIFIED'"
                    " AND verified_at LIKE ?",
                    (today + "%",),
                ),
                "prescriptions_pending": scalar(
                    "SELECT COUNT(*) FROM prescriptions WHERE status = 'PENDING'"
                ),
                "professionals_pending": scalar(
                    "SELECT COUNT(*) FROM professional_profiles WHERE status = 'PENDING'"
                ),
                "deliveries_active": scalar(
                    "SELECT COUNT(*) FROM deliveries"
                    " WHERE status NOT IN ('DELIVERED','FAILED')"
                ),
                "deliveries_moto": scalar(
                    "SELECT COUNT(*) FROM deliveries WHERE vehicle_type = 'MOTO'"
                ),
                "deliveries_car": scalar(
                    "SELECT COUNT(*) FROM deliveries WHERE vehicle_type = 'VOITURE'"
                ),
                "users_total": scalar("SELECT COUNT(*) FROM users"),
                "users_patients": scalar("SELECT COUNT(*) FROM users WHERE role = 'PATIENT'"),
                "users_pro": scalar("SELECT COUNT(*) FROM users WHERE role = 'PROFESSIONNEL'"),
                "revenue_verified": scalar(
                    "SELECT COALESCE(SUM(amount),0) FROM payments WHERE status = 'VERIFIED'"
                ),
            }
            return stats
        finally:
            conn.close()

    @app.get("/api/admin/users")
    def list_users(role: str = "",
                   user=Depends(require_role("ADMIN"))):
        conn = get_db()
        try:
            sql = ("SELECT id, email, phone, full_name, role, is_active, created_at"
                   " FROM users")
            params = []
            if role.strip():
                sql += " WHERE role = ?"
                params.append(role.strip().upper())
            sql += " ORDER BY id DESC LIMIT 500"
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
        return [{k: r[k] for k in r.keys()} for r in rows]


