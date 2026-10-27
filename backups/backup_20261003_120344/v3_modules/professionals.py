"""Gestion des profils professionnels (Phase 3)."""
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel


VALID_STRUCTURE_TYPES = {
    "CLINIQUE", "HOPITAL", "CABINET_MEDICAL",
    "LABORATOIRE", "CENTRE_SANTE", "AUTRE",
}

VALID_STATUSES = {"PENDING", "APPROVED", "REJECTED", "SUSPENDED"}


class ProfessionalProfileCreate(BaseModel):
    structure_name: str
    structure_type: str
    manager_name: str
    phone: str
    email: str = ""
    address: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: str = ""


class ProfessionalReview(BaseModel):
    status: str
    rejection_reason: str = ""


def _row_to_dict(row):
    return {k: row[k] for k in row.keys()} if row else None


def install_professionals(app, get_db, require_role):
    """Enregistre les routes /api/professionals/*."""

    # ---- Cote professionnel ----

    @app.post("/api/professionals/profile")
    def create_or_update_profile(
        payload: ProfessionalProfileCreate,
        user=Depends(require_role("PROFESSIONNEL")),
    ):
        if payload.structure_type not in VALID_STRUCTURE_TYPES:
            raise HTTPException(400, "Type de structure invalide")
        if not payload.structure_name.strip() or not payload.manager_name.strip():
            raise HTTPException(400, "Nom de structure et responsable obligatoires")
        if not payload.phone.strip():
            raise HTTPException(400, "Telephone obligatoire")

        conn = get_db()
        try:
            existing = conn.execute(
                "SELECT id, status FROM professional_profiles WHERE user_id = ?",
                (user["id"],),
            ).fetchone()
            now = datetime.now().isoformat(timespec="seconds")

            if existing is None:
                cur = conn.execute(
                    "INSERT INTO professional_profiles"
                    " (user_id, structure_name, structure_type, manager_name,"
                    " phone, email, address, latitude, longitude, notes,"
                    " status, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'APPROVED', ?)",
                    (user["id"], payload.structure_name.strip(),
                     payload.structure_type, payload.manager_name.strip(),
                     payload.phone.strip(), payload.email.strip(),
                     payload.address.strip(), payload.latitude,
                     payload.longitude, payload.notes.strip(), now),
                )
                pid = cur.lastrowid
            else:
                conn.execute(
                    "UPDATE professional_profiles SET"
                    " structure_name=?, structure_type=?, manager_name=?,"
                    " phone=?, email=?, address=?, latitude=?, longitude=?,"
                    " notes=?, status='APPROVED', rejection_reason=''"
                    " WHERE user_id=?",
                    (payload.structure_name.strip(), payload.structure_type,
                     payload.manager_name.strip(), payload.phone.strip(),
                     payload.email.strip(), payload.address.strip(),
                     payload.latitude, payload.longitude,
                     payload.notes.strip(), user["id"]),
                )
                pid = existing["id"]
            conn.commit()
            row = conn.execute(
                "SELECT * FROM professional_profiles WHERE id = ?", (pid,)
            ).fetchone()
        finally:
            conn.close()
        return _row_to_dict(row)

    @app.get("/api/professionals/me")
    def get_my_profile(user=Depends(require_role("PROFESSIONNEL"))):
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT * FROM professional_profiles WHERE user_id = ?",
                (user["id"],),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            raise HTTPException(404, "Profil non cree")
        return _row_to_dict(row)

    # ---- Cote pharmacien / admin ----

    @app.get("/api/professionals")
    def list_profiles(
        status: str = "",
        user=Depends(require_role("PHARMACIEN", "ADMIN")),
    ):
        conn = get_db()
        try:
            sql = ("SELECT p.*, u.email AS user_email, u.full_name AS user_name"
                   " FROM professional_profiles p"
                   " JOIN users u ON u.id = p.user_id")
            params = []
            if status.strip():
                sql += " WHERE p.status = ?"
                params.append(status.strip().upper())
            sql += " ORDER BY p.created_at DESC"
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
        return [_row_to_dict(r) for r in rows]

    @app.get("/api/professionals/{profile_id}")
    def get_profile(profile_id: int, user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT p.*, u.email AS user_email, u.full_name AS user_name"
                " FROM professional_profiles p"
                " JOIN users u ON u.id = p.user_id WHERE p.id = ?",
                (profile_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            raise HTTPException(404, "Profil introuvable")
        return _row_to_dict(row)

    @app.patch("/api/professionals/{profile_id}/status")
    def review_profile(
        profile_id: int,
        payload: ProfessionalReview,
        user=Depends(require_role("PHARMACIEN", "ADMIN")),
    ):
        new_status = payload.status.strip().upper()
        if new_status not in {"APPROVED", "REJECTED", "SUSPENDED"}:
            raise HTTPException(400, "Statut invalide")
        if new_status == "REJECTED" and not payload.rejection_reason.strip():
            raise HTTPException(400, "Motif de refus obligatoire")

        conn = get_db()
        try:
            row = conn.execute(
                "SELECT id FROM professional_profiles WHERE id = ?",
                (profile_id,),
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Profil introuvable")
            conn.execute(
                "UPDATE professional_profiles SET status=?, rejection_reason=?,"
                " reviewed_at=?, reviewed_by=? WHERE id=?",
                (new_status, payload.rejection_reason.strip(),
                 datetime.now().isoformat(timespec="seconds"),
                 user["id"], profile_id),
            )
            conn.commit()
            updated = conn.execute(
                "SELECT * FROM professional_profiles WHERE id = ?",
                (profile_id,),
            ).fetchone()
        finally:
            conn.close()
        return _row_to_dict(updated)

    @app.get("/api/professionals/stats/summary")
    def stats(user=Depends(require_role("PHARMACIEN", "ADMIN"))):
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS n FROM professional_profiles GROUP BY status"
            ).fetchall()
            counts = {r["status"]: r["n"] for r in rows}
        finally:
            conn.close()
        return {
            "pending": counts.get("PENDING", 0),
            "approved": counts.get("APPROVED", 0),
            "rejected": counts.get("REJECTED", 0),
            "suspended": counts.get("SUSPENDED", 0),
            "total": sum(counts.values()),
        }


