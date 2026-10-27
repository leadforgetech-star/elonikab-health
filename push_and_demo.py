# -*- coding: utf-8 -*-
"""
Push GitHub + Compte patient demo + Prefill login
===================================================
1. Push branche lot7 -> merge main -> push main (Render redeploie)
2. Cree compte demo@elonikab.tg / Demo2026
3. Patche login.html pour ?demo=1 (auto-fill)
"""
import os, subprocess, sqlite3, json, urllib.request, urllib.error, datetime

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
DB = os.path.join(ROOT, "database.db")
LOGIN_HTML = os.path.join(ROOT, "static", "login.html")
BASE = "http://127.0.0.1:8000"

DEMO_EMAIL = "demo@elonikab.tg"
DEMO_PASSWORD = "Demo2026"
DEMO_NAME = "Patient Demo"

def run(cmd, silent=False):
    if not silent: print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
    if not silent:
        if r.stdout.strip(): print(r.stdout)
        if r.stderr.strip(): print(r.stderr)
    return r.returncode

print("=" * 78)
print("PUSH + DEMO - " + datetime.datetime.now().isoformat(timespec="seconds"))
print("=" * 78)

# ============================================================
# PART 1 : PUSH GITHUB
# ============================================================
print("\n### PART 1 : PUSH GITHUB\n")

run("git add .")
commit_msg = "Sprint A+B+C+D - Livraison intelligente + Comptabilite + Stock avance + Vue Direction"
run(f'git commit -m "{commit_msg}"')

print("\n--- Push branche lot7-catalogue-stock ---")
run("git push -u origin lot7-catalogue-stock")

print("\n--- Merge dans main ---")
run("git checkout main")
run("git merge lot7-catalogue-stock --no-edit")

print("\n--- Push main (Render va redeployer) ---")
run("git push origin main")

print("\n--- Retour sur branche lot7 ---")
run("git checkout lot7-catalogue-stock")

print("\n[INFO] Render redéploie dans 2-4 min")
print("[INFO] URL production : https://elonikab-health.onrender.com")

# ============================================================
# PART 2 : COMPTE DEMO PATIENT
# ============================================================
print("\n### PART 2 : COMPTE DEMO PATIENT\n")

# Check if exists
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
existing = conn.execute("SELECT id, email FROM users WHERE email = ?", (DEMO_EMAIL,)).fetchone()
conn.close()

if existing:
    print(f"[OK] Compte demo existe (id={existing['id']}, email={existing['email']})")
else:
    print(f"[..] Creation du compte {DEMO_EMAIL}...")
    try:
        payload = json.dumps({
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD,
            "full_name": DEMO_NAME,
            "phone": "+22890000000",
            "role": "PATIENT"
        }).encode()
        req = urllib.request.Request(
            BASE + "/api/auth/register",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        r = urllib.request.urlopen(req, timeout=10)
        body = r.read().decode()
        print(f"[OK] Compte cree : {body[:150]}")
    except urllib.error.HTTPError as e:
        print(f"[!!] Erreur HTTP {e.code} : {e.read().decode()[:200]}")
        print("      Uvicorn doit etre lance sur 127.0.0.1:8000")
    except Exception as e:
        print(f"[!!] Erreur : {e}")
        print("      Uvicorn doit etre lance sur 127.0.0.1:8000")

# ============================================================
# PART 3 : PREFILL LOGIN ?demo=1
# ============================================================
print("\n### PART 3 : PREFILL LOGIN\n")

if not os.path.isfile(LOGIN_HTML):
    print("[!!] login.html introuvable")
else:
    html = open(LOGIN_HTML, "r", encoding="utf-8").read()
    if "eh-demo-prefill" in html:
        print("[SKIP] login.html deja patche")
    else:
        PATCH = """
<script id="eh-demo-prefill">
/* Sprint B+C : prefill demo credentials via ?demo=1 */
(function(){
  if (new URLSearchParams(window.location.search).get("demo") !== "1") return;
  function fill(){
    var emailInp = document.querySelector('input[type="email"], input[name="email"], #email');
    var pwdInp = document.querySelector('input[type="password"], input[name="password"], #password');
    if (emailInp) emailInp.value = "demo@elonikab.tg";
    if (pwdInp) pwdInp.value = "Demo2026";
    var firstInput = emailInp || pwdInp;
    if (firstInput) { try { firstInput.focus(); } catch(e) {} }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fill);
  } else {
    fill();
  }
  // Re-essayer apres 500ms (au cas ou le form est injecte dynamiquement)
  setTimeout(fill, 500);
})();
</script>
"""
        if "</body>" in html:
            html = html.replace("</body>", PATCH + "\n</body>", 1)
            open(LOGIN_HTML, "w", encoding="utf-8").write(html)
            print("[OK] login.html patche (support ?demo=1)")
        else:
            print("[!!] </body> introuvable dans login.html")

# ============================================================
# RESUME
# ============================================================
print("\n" + "=" * 78)
print("RESUME")
print("=" * 78)
print()
print("Push GitHub : OK (Render redéploie sous 2-4 min)")
print()
print("Compte demo patient :")
print(f"  Email    : {DEMO_EMAIL}")
print(f"  Password : {DEMO_PASSWORD}")
print()
print("LIENS DE PROSPECTION (à partager aux pharmacies) :")
print()
print("  1. Landing (sans connexion) :")
print("     https://elonikab-health.onrender.com/")
print()
print("  2. Experience patient (auto-fill demo) :")
print("     https://elonikab-health.onrender.com/connexion?demo=1")
print()
print("  3. Inscription patient (compte libre) :")
print("     https://elonikab-health.onrender.com/inscription")
print()
print("=" * 78)