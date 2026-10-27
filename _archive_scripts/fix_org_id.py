"""
fix_org_id.py
Corrige _get_org_id() dans b2b_requests.py :
utilise le professional_profile existant au lieu d'en creer un nouveau.
"""
from pathlib import Path
import datetime
import re
import shutil

BASE = Path(__file__).resolve().parent
B2B = BASE / "v3_modules" / "b2b_requests.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_fix_org_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(B2B, backup / "b2b_requests.py")
print("[OK] Backup ->", backup.name)

src = B2B.read_text(encoding="utf-8")

# Remplacer entierement la fonction _get_org_id
pattern = re.compile(
    r'def _get_org_id\(conn, user_id\):.*?(?=\ndef |\nclass |\n@app|\Z)',
    re.DOTALL
)

new_fn = '''def _get_org_id(conn, user_id):
    """Recupere l'organization_id du user.
    - Si users.organization_id existe -> le retourne
    - Sinon, cherche un professional_profile existant -> l'utilise
    - Sinon, en cree un nouveau
    """
    user = conn.execute(
        "SELECT id, organization_id, role FROM users WHERE id=?", (user_id,)
    ).fetchone()
    if user is None:
        raise HTTPException(401, "Utilisateur inconnu")

    # Cas 1 : deja lie
    if user["organization_id"]:
        return user["organization_id"]

    # Cas 2 : chercher un profil existant pour ce user
    prof = conn.execute(
        "SELECT id FROM professional_profiles WHERE user_id=?", (user_id,)
    ).fetchone()

    if prof:
        # Profil existant : utiliser son id comme org_id et mettre a jour users
        org_id = prof["id"]
        conn.execute(
            "UPDATE users SET organization_id=? WHERE id=?",
            (org_id, user_id)
        )
        conn.commit()
        return org_id

    # Cas 3 : aucun profil -> en creer un
    now = _now()
    cur = conn.execute(
        "INSERT INTO professional_profiles"
        " (user_id, structure_name, structure_type, manager_name, phone, email,"
        "  address, latitude, longitude, status, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'APPROVED', ?)",
        (user_id, "Organisation", "AUTRE", "", "", "", "", None, None, now),
    )
    org_id = cur.lastrowid
    conn.execute(
        "UPDATE users SET organization_id=? WHERE id=?",
        (org_id, user_id)
    )
    conn.commit()
    return org_id

'''

if pattern.search(src):
    src = pattern.sub(new_fn, src, count=1)
    B2B.write_text(src, encoding="utf-8")
    print("[OK] b2b_requests.py -> _get_org_id corrige")
else:
    print("[!] _get_org_id introuvable")
    raise SystemExit(1)

# Verification
check = B2B.read_text(encoding="utf-8")
if "Cas 2 : chercher un profil existant" in check:
    print("[OK] Fix applique avec succes")
else:
    print("[!] Le fix n'a pas ete applique correctement")

print()
print("=" * 60)
print("FIX _get_org_id APPLIQUE")
print("=" * 60)
print()
print("Le bug venait d'une fonction qui essayait de creer un nouveau")
print("professional_profile meme si l'utilisateur en avait deja un.")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print()
print("Puis Ctrl+Shift+R sur le navigateur et re-teste l'ajout.")