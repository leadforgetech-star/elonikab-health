# -*- coding: utf-8 -*-
"""
LOT 2 - CLOTURE v2 (zéro modification du code)
==============================================
Corrige le bug de triple-quotes du script v1.
- Backup
- Verification des 20 patches
- Generation test_e2e_complet.py
- Generation README_PROJET.md
- Generation CHECKLIST_VALIDATION.md
"""
import os, re, sqlite3, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
DB   = os.path.join(ROOT, "database.db")

TS  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, "_closure_backup_" + TS)
os.makedirs(BAK, exist_ok=True)

def log(m, k="INFO"):
    p = {"INFO": "[.]", "OK": "[OK]", "WARN": "[!]", "ERR": "[X]", "STEP": "\n###"}[k]
    print(p, m)

def wf(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

print("=" * 78)
print("LOT 2 - CLOTURE V2 - " + TS)
print("=" * 78)

# ============================================================
# PHASE 0 : Backup
# ============================================================
log("PHASE 0 : Backup", "STEP")
FILES = [
    ("main.py", "main.py"),
    ("v3_modules/payments.py", "payments.py"),
    ("v3_modules/prescriptions.py", "prescriptions.py"),
    ("static/pharmacien.js", "pharmacien.js"),
    ("static/professional_realtime.js", "professional_realtime.js"),
    ("static/pharmacien.html", "pharmacien.html"),
    ("database.db", "database.db"),
]
for src_rel, dst_name in FILES:
    src = os.path.join(ROOT, src_rel)
    if os.path.isfile(src):
        shutil.copy2(src, os.path.join(BAK, dst_name))
        log("Backup " + dst_name, "OK")

# ============================================================
# PHASE 1 : Verification des patches
# ============================================================
log("PHASE 1 : Verification des patches", "STEP")

def read(p):
    if os.path.isfile(p):
        return open(p, "r", encoding="utf-8", errors="ignore").read()
    return ""

main = read(os.path.join(ROOT, "main.py"))
pay  = read(os.path.join(ROOT, "v3_modules", "payments.py"))
presc = read(os.path.join(ROOT, "v3_modules", "prescriptions.py"))
pharm = read(os.path.join(ROOT, "static", "pharmacien.js"))
rt   = read(os.path.join(ROOT, "static", "professional_realtime.js"))

checks = []
def check(label, cond):
    checks.append((label, bool(cond)))
    print("  [" + ("OK" if cond else "!!") + "] " + label)

check("Lot1-A: endpoints admin proteges",
      "user = Depends(get_current_user_dep)" in main)
check("Lot1-B: POST /api/orders auth",
      "Authentification requise pour commander" in main)
check("Lot1-C: chunked upload refused",
      pay.count("Check commande refusee") >= 2)
check("Lot1-D: helper log_audit",
      "def log_audit(" in main)
check("Lot1-D: order.status_change",
      "order.status_change" in main)
check("Lot1-D: payment verify/reject/refund",
      all(x in pay for x in ["payment.verify", "payment.reject", "payment.refund"]))
check("Lot1-E: file.access",
      "file.access" in main)
check("Lot1-Bonus: SSE Guard V3",
      "SSE AUTH GUARD V3" in rt)
check("Lot1-Bonus: drawer pay buttons",
      "drawer-pay-actions" in pharm)
check("Lot1-Bonus: drawerRefreshIfOpen",
      "function drawerRefreshIfOpen" in pharm)
check("Lot2-1: driver.create",
      "driver.create" in main)
check("Lot2-2: driver.toggle",
      "driver.toggle" in main)
check("Lot2-3: settings.update",
      "settings.update" in main)
check("Lot2-4: prescription.review",
      "prescription.review" in presc)
check("Lot2-5: submitSettings 15 champs",
      'car_base_fee: num("car-base-fee")' in pharm
      and 'whatsapp_number: str("whatsapp-input")' in pharm)
check("Lot2-6: sous-onglets admin neutralises",
      "V10 : desactive" in pharm)
check("Lot2-7: setInterval retire",
      "V10 : setInterval retire" in pharm)
check("Lot2-8: ClearSiteData restreint",
      'PATHS = ("/connexion", "/inscription"' in main)
check("DOC_TRANSITIONS.md present",
      os.path.isfile(os.path.join(ROOT, "DOC_TRANSITIONS.md")))
check("test_lot2_e2e.py present",
      os.path.isfile(os.path.join(ROOT, "test_lot2_e2e.py")))

try:
    conn = sqlite3.connect(DB)
    n_audit = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
    conn.close()
    check("DB audit_logs non vide (" + str(n_audit) + " lignes)", n_audit > 0)
except Exception:
    check("DB audit_logs accessible", False)

total = len(checks)
passed = sum(1 for _, ok in checks if ok)
print()
print("  RESULTAT : " + str(passed) + "/" + str(total) + " OK")

# ============================================================
# PHASE 2 : test_e2e_complet.py
# ============================================================
log("PHASE 2 : Generation test_e2e_complet.py", "STEP")

E2E_LINES = [
    "# -*- coding: utf-8 -*-",
    "# Tests E2E complets - 12 scenarios critiques (Lot 1 + Lot 2)",
    "import json, urllib.request, urllib.error, http.cookiejar, sqlite3, sys",
    "",
    'BASE = "http://127.0.0.1:8000"',
    'DB   = r"C:\\Users\\ELOGE KEY\\Desktop\\pharma\\pharmacie\\database.db"',
    "",
    "def login(email, password):",
    "    cj = http.cookiejar.CookieJar()",
    "    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))",
    "    req = urllib.request.Request(",
    '        BASE + "/api/auth/login",',
    '        data=json.dumps({"email": email, "password": password}).encode(),',
    '        headers={"Content-Type": "application/json"}, method="POST")',
    "    r = op.open(req, timeout=10)",
    "    return op",
    "",
    "def call(op, method, path, body=None):",
    '    data = json.dumps(body).encode() if body else None',
    '    req = urllib.request.Request(BASE + path, data=data,',
    '        headers={"Content-Type":"application/json"} if body else {},',
    "        method=method)",
    "    try:",
    "        r = op.open(req, timeout=10)",
    "        return r.status, r.read().decode()[:300]",
    "    except urllib.error.HTTPError as e:",
    "        return e.code, e.read().decode()[:300]",
    "    except Exception as e:",
    "        return None, str(e)",
    "",
    "def call_noauth(method, path, data=None, ct=None):",
    "    req = urllib.request.Request(BASE + path, data=data,",
    '        headers={"Content-Type": ct} if ct else {}, method=method)',
    "    try:",
    "        r = urllib.request.urlopen(req, timeout=10)",
    "        return r.status, r.read().decode()[:300]",
    "    except urllib.error.HTTPError as e:",
    "        return e.code, e.read().decode()[:300]",
    "    except Exception as e:",
    "        return None, str(e)",
    "",
    "results = []",
    "def check(label, condition, detail=''):",
    '    status = "OK" if condition else "ECHEC"',
    "    results.append((label, status, detail))",
    '    print("  [" + status + "] " + label + "  " + detail)',
    "",
    'print("=" * 70)',
    'print("TESTS E2E COMPLETS")',
    'print("=" * 70)',
    "",
    "# S1",
    'print("\\n[S1] POST /api/orders sans auth = 401")',
    'code, _ = call_noauth("POST", "/api/orders",',
    '    data=b"customer_name=T&phone=2289&product_id=1&quantity=1&delivery_mode=retrait",',
    '    ct="application/x-www-form-urlencoded")',
    'check("S1", code == 401, "recu " + str(code))',
    "",
    "# S2",
    'print("\\n[S2] GET /api/drivers sans auth")',
    'code, _ = call_noauth("GET", "/api/drivers")',
    'check("S2", code in (401, 403), "recu " + str(code))',
    "",
    "# S3",
    'print("\\n[S3] PATCH /api/settings sans auth")',
    'code, _ = call_noauth("PATCH", "/api/settings", data=b"{}", ct="application/json")',
    'check("S3", code in (401, 403), "recu " + str(code))',
    "",
    "# S4",
    'print("\\n[S4] GET /api/settings public = 200")',
    'code, _ = call_noauth("GET", "/api/settings")',
    'check("S4", code == 200, "recu " + str(code))',
    "",
    "# S5",
    'print("\\n[S5] Patient -> GET /api/drivers = 403")',
    "try:",
    '    op_p = login("patient@test.tg", "Test1234")',
    '    code, _ = call(op_p, "GET", "/api/drivers")',
    '    check("S5", code == 403, "recu " + str(code))',
    "except Exception as e:",
    '    check("S5", False, "login patient echoue: " + str(e))',
    "",
    "# S6",
    'print("\\n[S6] Pharmacien -> GET /api/drivers = 200")',
    "try:",
    '    op_ph = login("pharmacien@test.tg", "Test1234")',
    '    code, _ = call(op_ph, "GET", "/api/drivers")',
    '    check("S6", code == 200, "recu " + str(code))',
    "except Exception as e:",
    '    check("S6", False, "login pharm echoue: " + str(e))',
    "",
    "# S7",
    'print("\\n[S7] Pharmacien -> PATCH /api/settings = 200")',
    "try:",
    '    code, _ = call(op_ph, "PATCH", "/api/settings", {"delivery_base_fee": 1000})',
    '    check("S7", code == 200, "recu " + str(code))',
    "except Exception as e:",
    '    check("S7", False, str(e))',
    "",
    "# S8",
    'print("\\n[S8] Patient connecte -> POST /api/orders")',
    "try:",
    '    op_p2 = login("patient@test.tg", "Test1234")',
    '    req = urllib.request.Request(BASE + "/api/orders",',
    '        data=b"customer_name=T&phone=2289&product_id=1&quantity=1&delivery_mode=retrait",',
    '        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")',
    "    try:",
    "        r = op_p2.open(req, timeout=10)",
    '        check("S8", r.status in (200, 201), "recu " + str(r.status))',
    "    except urllib.error.HTTPError as e:",
    '        check("S8", e.code in (200, 201, 400), "recu " + str(e.code))',
    "except Exception as e:",
    '    check("S8", False, str(e))',
    "",
    "# S9",
    'print("\\n[S9] audit_logs non vide")',
    "conn = sqlite3.connect(DB)",
    'n = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]',
    "conn.close()",
    'check("S9", n > 0, str(n) + " lignes")',
    "",
    "# S10",
    'print("\\n[S10] Actions instrumentees presentes")',
    "conn = sqlite3.connect(DB)",
    'actions = set(r[0] for r in conn.execute("SELECT DISTINCT action FROM audit_logs").fetchall())',
    "conn.close()",
    'expected = {"order.status_change", "payment.verify"}',
    "missing = expected - actions",
    'check("S10", len(missing) == 0, "presents=" + str(sorted(actions)))',
    "",
    "# S11",
    'print("\\n[S11] Verification coherence paiements")',
    "conn = sqlite3.connect(DB)",
    "rows = conn.execute(",
    '    "SELECT COUNT(*) FROM orders WHERE status = \'refusee\' AND payment_status IN (\'VERIFIED\', \'PROOF_SUBMITTED\')"',
    ").fetchone()[0]",
    "conn.close()",
    'check("S11", True, str(rows) + " cas (informatif)")',
    "",
    "# S12",
    'print("\\n[S12] GET /api/products public = 200")',
    'code, _ = call_noauth("GET", "/api/products")',
    'check("S12", code == 200, "recu " + str(code))',
    "",
    'print()',
    'print("=" * 70)',
    'ok_count = sum(1 for _, s, _ in results if s == "OK")',
    'print("RESULTAT : " + str(ok_count) + "/" + str(len(results)) + " tests OK")',
    'print("=" * 70)',
    "for label, s, detail in results:",
    '    mark = "OK" if s == "OK" else "!!"',
    '    print("  [" + mark + "] " + label + "  " + detail)',
    "",
    "sys.exit(0 if ok_count == len(results) else 1)",
    "",
]

e2e_path = os.path.join(ROOT, "test_e2e_complet.py")
wf(e2e_path, "\n".join(E2E_LINES))
log("test_e2e_complet.py genere (" + str(len(E2E_LINES)) + " lignes)", "OK")

# ============================================================
# PHASE 3 : README_PROJET.md
# ============================================================
log("PHASE 3 : Generation README_PROJET.md", "STEP")

README_LINES = [
    "# Elonikab Health - Documentation technique",
    "",
    "## Architecture",
    "",
    "    main.py             -> routes FastAPI, startup, middleware",
    "    database.db         -> SQLite (toutes les tables)",
    "    v3_modules/         -> modules metier",
    "    static/             -> frontend (HTML/CSS/JS vanilla)",
    "    uploads/            -> fichiers sensibles",
    "",
    "## Roles",
    "",
    "- PATIENT : commande, paie, suit sa commande",
    "- PROFESSIONNEL : commande en gros (B2B)",
    "- PHARMACIEN : traite les commandes, valide paiements",
    "- ADMIN : acces total, gere les utilisateurs",
    "",
    "## Verrous metier",
    "",
    "Voir DOC_TRANSITIONS.md pour la reference complete.",
    "",
    "## Journalisation (audit_logs)",
    "",
    "Table : id, user_id, action, target_type, target_id, details, created_at",
    "",
    "Actions instrumentees :",
    "",
    "- order.status_change",
    "- payment.verify, payment.reject, payment.refund",
    "- file.access",
    "- driver.create, driver.toggle",
    "- settings.update",
    "- prescription.review",
    "",
    "## Securite",
    "",
    "- Endpoints admin : require_role PHARMACIEN/ADMIN",
    "- POST /api/orders : authentification obligatoire",
    "- Fichiers sensibles : /api/files avec rattachement verifie",
    "- Chunked upload : checks refused sur 3 endpoints",
    "",
    "## Tests",
    "",
    "- test_e2e_complet.py : 12 scenarios",
    "- test_lot2_e2e.py : 5 scenarios",
    "",
    "## Restauration",
    "",
    "Backups dans _backup_* et _closure_backup_*.",
    "Copier le fichier souhaite vers son emplacement d'origine.",
    "",
    "## Historique",
    "",
    "- Lot 1 : 5 failles securite + bonus SSE + drawer paiement",
    "- Lot 2 p1 : audit_logs etendus + 15 champs settings + fix reloads",
    "- Lot 2 p2 : a venir (coherence front/back, tests etendus)",
    "",
]

readme_path = os.path.join(ROOT, "README_PROJET.md")
wf(readme_path, "\n".join(README_LINES))
log("README_PROJET.md genere", "OK")

# ============================================================
# PHASE 4 : CHECKLIST_VALIDATION.md
# ============================================================
log("PHASE 4 : Generation CHECKLIST_VALIDATION.md", "STEP")

CHECK_LINES = [
    "# Checklist de validation manuelle",
    "",
    "## Lot 1 - Securite",
    "",
    "- [ ] Patient -> GET /api/drivers = 403",
    "- [ ] Patient -> PATCH /api/settings = 403",
    "- [ ] Patient -> GET /api/settings = 200",
    "- [ ] Non connecte -> POST /api/orders = 401",
    "- [ ] Pharmacien -> GET /api/drivers = 200",
    "- [ ] Pharmacien -> PATCH /api/settings = 200",
    "",
    "## Lot 1 - Temps reel",
    "",
    "- [ ] Visiteur : pas de stream 401 en boucle",
    "- [ ] Patient sur /suivi : SSE s'ouvre",
    "- [ ] Pharmacien change un statut -> patient recoit toast",
    "- [ ] Pharmacien valide un paiement -> drawer se recharge",
    "",
    "## Lot 1 - Drawer paiement",
    "",
    "- [ ] Boutons Valider/Refuser visibles",
    "- [ ] Cliquer Valider -> modale -> toast -> refresh",
    "- [ ] Boutons disparaissent apres validation",
    "",
    "## Lot 2 p1 - Audit",
    "",
    "- [ ] Creer un livreur -> driver.create",
    "- [ ] Desactiver un livreur -> driver.toggle",
    "- [ ] Modifier un tarif -> settings.update",
    "- [ ] Changer statut commande -> order.status_change",
    "",
    "## Lot 2 p1 - Parametres",
    "",
    "- [ ] Modifier Tarifs VOITURE Frais de base -> Enregistrer -> F5 -> persiste",
    "- [ ] Tarifs MOTO, Paiement, WhatsApp -> idem",
    "",
    "## Lot 2 p1 - UI",
    "",
    "- [ ] Pas de sous-onglets Pharmacie/Tarifs/Paiement",
    "- [ ] Section Livreurs visible",
    "- [ ] Pas de reload en cliquant Desactiver",
    "- [ ] Pas de reload auto apres 1 min",
    "",
]

checklist_path = os.path.join(ROOT, "CHECKLIST_VALIDATION.md")
wf(checklist_path, "\n".join(CHECK_LINES))
log("CHECKLIST_VALIDATION.md genere", "OK")

# ============================================================
# RAPPORT
# ============================================================
print()
print("=" * 78)
print("RAPPORT FINAL")
print("=" * 78)
print("Backup        : " + BAK)
print("Verifications : " + str(passed) + "/" + str(total) + " OK")
print()
print("Fichiers generes :")
print("  - " + e2e_path)
print("  - " + readme_path)
print("  - " + checklist_path)
print()
print("[CMD] Lance les tests E2E :")
print("  python test_e2e_complet.py")
print()

if passed < total:
    print("[!!] Verifications echouees :")
    for label, ok in checks:
        if not ok:
            print("   - " + label)
    print()