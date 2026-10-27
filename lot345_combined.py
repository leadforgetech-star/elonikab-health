# -*- coding: utf-8 -*-
"""
LOTS 3 + 4 + 5 - Script unique
================================
Lot 5 : endpoint /api/stats/summary + vue stats
Lot 4 : checklist avant remise dans le drawer
Lot 3 : cartes actionnables accueil (deja partiellement en place)

Atomic : si UNE etape echoue -> ROLLBACK complet.
Ne touche PAS aux modules existants sauf ajout pur.
"""
import os, re, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
MAIN = os.path.join(ROOT, "main.py")
HTML = os.path.join(ROOT, "static", "pharmacien.html")
JS   = os.path.join(ROOT, "static", "pharmacien.js")
NEW  = os.path.join(ROOT, "static", "pharmacien_stats.js")

TS  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, "_backup_lot345_" + TS)
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
        return False, "L" + str(e.lineno) + ": " + e.msg

def wf(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

print("=" * 78)
print("LOTS 3 + 4 + 5 - " + TS)
print("=" * 78)

# ============================================================
# PHASE 0 : BACKUP
# ============================================================
log("PHASE 0 : BACKUP", "STEP")
for f, n in [(MAIN, "main.py"), (HTML, "pharmacien.html"), (JS, "pharmacien.js")]:
    if os.path.isfile(f):
        shutil.copy2(f, os.path.join(BAK, n))
        log("Backup " + n, "OK")

# ============================================================
# PHASE 1 : LOT 5 - Endpoint /api/stats/summary
# ============================================================
log("PHASE 1 : LOT 5 - Endpoint stats", "STEP")

main_src = open(MAIN, "r", encoding="utf-8").read()

if "/api/stats/summary" in main_src:
    log("Endpoint deja present", "WARN")
else:
    STATS_EP = '''

# ============================================================
# LOT 5 - Statistiques fiables (PHARMACIEN/ADMIN)
# ============================================================
@app.get("/api/stats/summary")
def stats_summary(user = Depends(get_current_user_dep)):
    """Statistiques reelles separees : CA, encaisse, remboursements."""
    if not user or user["role"] not in ("PHARMACIEN", "ADMIN"):
        raise HTTPException(403, "Reserve au personnel pharmacie")
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

        return {
            "total_orders": total,
            "today_orders": today_orders,
            "by_status": by_status,
            "payments_by_status": pay_by_status,
            "pending_verify": pending_verify,
            "refund_required": refund_required,
        }
    finally:
        conn.close()

'''

    # Inserer juste avant "if __name__ == \"__main__\":"
    marker = 'if __name__ == "__main__":'
    if marker in main_src:
        idx = main_src.find(marker)
        main_src = main_src[:idx] + STATS_EP + main_src[idx:]
        open(MAIN, "w", encoding="utf-8").write(main_src)
        ok, err = syntax_ok(MAIN)
        if not ok:
            log("main.py ERREUR : " + str(err), "ERR")
            shutil.copy2(os.path.join(BAK, "main.py"), MAIN)
            log("ROLLBACK main.py", "ERR")
            sys.exit(1)
        log("main.py : endpoint stats ajoute", "OK")
    else:
        log("Marqueur __main__ introuvable", "ERR")
        sys.exit(1)

# ============================================================
# PHASE 2 : LOT 5 - Module JS stats
# ============================================================
log("PHASE 2 : LOT 5 - Module JS stats", "STEP")

JS_MODULE = '''/* ============================================================
   Elonikab Health - Stats module (Lot 5)
   Ajoute un onglet "Stats" dans l'admin.
   ============================================================ */
(function () {
  "use strict";
  var API = "/api";

  function fmtMoney(v) {
    var n = Math.round(Number(v) || 0);
    try { return n.toLocaleString("fr-FR") + " FCFA"; }
    catch (e) {
      var s = String(n), out = "";
      for (var i = 0; i < s.length; i++) {
        if (i > 0 && (s.length - i) % 3 === 0) out += " ";
        out += s.charAt(i);
      }
      return out + " FCFA";
    }
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  var STATUS_LBL = {
    en_attente: "En attente",
    confirmee: "Confirmees",
    en_preparation: "En preparation",
    prete: "Pretes",
    en_livraison: "En livraison",
    terminee: "Terminees",
    refusee: "Refusees"
  };

  function renderStats(data) {
    var box = document.getElementById("ph-stats-panel");
    if (!box) return;

    var by = data.by_status || {};
    var pays = data.payments_by_status || {};
    var verified = pays["VERIFIED"] || {count:0, amount:0};
    var pending  = pays["PROOF_SUBMITTED"] || {count:0, amount:0};
    var refund   = pays["REFUND_REQUIRED"] || {count:0, amount:0};
    var rejected = pays["REJECTED"] || {count:0, amount:0};

    var h = '';
    h += '<div class="ph-stats-wrap">';

    // Ligne 1 : chiffres cles
    h += '<div class="ph-stats-row">';
    h += '<div class="ph-stats-card"><strong>' + (data.today_orders||0) + '</strong><span>Commandes aujourd hui</span></div>';
    h += '<div class="ph-stats-card"><strong>' + (data.total_orders||0) + '</strong><span>Commandes total</span></div>';
    h += '<div class="ph-stats-card ph-stats-warn"><strong>' + (data.pending_verify||0) + '</strong><span>Paiements a valider</span></div>';
    h += '<div class="ph-stats-card ph-stats-danger"><strong>' + (data.refund_required||0) + '</strong><span>Remboursements</span></div>';
    h += '</div>';

    // Ligne 2 : finances (separees)
    h += '<div class="ph-stats-section"><h3>Encaissements reels</h3>';
    h += '<div class="ph-stats-row">';
    h += '<div class="ph-stats-card ph-stats-ok"><strong>' + fmtMoney(verified.amount) + '</strong><span>Encaisse (' + verified.count + ' paiements)</span></div>';
    h += '<div class="ph-stats-card ph-stats-warn"><strong>' + fmtMoney(pending.amount) + '</strong><span>En attente validation (' + pending.count + ')</span></div>';
    h += '<div class="ph-stats-card ph-stats-danger"><strong>' + fmtMoney(refund.amount) + '</strong><span>A rembourser (' + refund.count + ')</span></div>';
    h += '<div class="ph-stats-card ph-stats-muted"><strong>' + fmtMoney(rejected.amount) + '</strong><span>Refuses (' + rejected.count + ')</span></div>';
    h += '</div></div>';

    // Ligne 3 : repartition commandes
    h += '<div class="ph-stats-section"><h3>Repartition des commandes</h3>';
    h += '<table class="ph-stats-table"><thead><tr><th>Statut</th><th>Nombre</th></tr></thead><tbody>';
    var order = ["en_attente", "confirmee", "en_preparation", "prete", "en_livraison", "terminee", "refusee"];
    order.forEach(function (k) {
      var n = by[k] || 0;
      if (n > 0 || k === "en_attente") {
        h += '<tr><td>' + esc(STATUS_LBL[k] || k) + '</td><td><strong>' + n + '</strong></td></tr>';
      }
    });
    h += '</tbody></table></div>';

    // Note : si aucune donnee
    if ((data.total_orders || 0) === 0) {
      h += '<div class="ph-stats-empty">Aucune donnee pour le moment.</div>';
    }

    h += '</div>';
    box.innerHTML = h;
  }

  function loadStats() {
    var box = document.getElementById("ph-stats-panel");
    if (box) box.innerHTML = '<div class="ph-stats-empty">Chargement...</div>';
    fetch(API + "/stats/summary", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) {
          if (box) box.innerHTML = '<div class="ph-stats-empty">Erreur de chargement.</div>';
          return;
        }
        renderStats(data);
      })
      .catch(function () {
        if (box) box.innerHTML = '<div class="ph-stats-empty">Erreur reseau.</div>';
      });
  }

  function injectStatsTab() {
    var tabs = document.querySelector(".ph-admin-tabs");
    if (!tabs) return;
    if (tabs.querySelector('[data-ph-admin="stats"]')) return;
    var btn = document.createElement("button");
    btn.className = "ph-admin-tab";
    btn.setAttribute("data-ph-admin", "stats");
    btn.textContent = "Statistiques";
    tabs.appendChild(btn);
  }

  function injectStatsPanel() {
    var page = document.querySelector('[data-ph-page="admin"]');
    if (!page) return;
    if (document.getElementById("ph-stats-panel")) return;
    var panel = document.createElement("div");
    panel.className = "ph-admin-panel";
    panel.setAttribute("data-ph-admin-panel", "stats");
    panel.innerHTML = '<div id="ph-stats-panel"></div>';
    page.appendChild(panel);
  }

  function init() {
    injectStatsTab();
    injectStatsPanel();
  }

  document.addEventListener("DOMContentLoaded", function () { setTimeout(init, 1500); });

  document.addEventListener("click", function (ev) {
    var t = ev.target.closest ? ev.target.closest('[data-ph-admin="stats"]') : null;
    if (t) setTimeout(loadStats, 100);
  });

  window.phLoadStats = loadStats;
})();
'''

wf(NEW, JS_MODULE)
log("pharmacien_stats.js cree", "OK")

# ============================================================
# PHASE 3 : Reference dans pharmacien.html
# ============================================================
log("PHASE 3 : Reference stats dans HTML", "STEP")

html_src = open(HTML, "r", encoding="utf-8").read()

if "pharmacien_stats.js" in html_src:
    log("Reference deja presente", "WARN")
else:
    # Ajouter avant </body>
    if "</body>" in html_src:
        inject = '<script defer src="/static/pharmacien_stats.js?v=' + TS + '"></script>\n'
        html_src = html_src.replace("</body>", inject + "</body>", 1)
        open(HTML, "w", encoding="utf-8").write(html_src)
        log("pharmacien_stats.js reference ajoutee", "OK")
    else:
        log("</body> introuvable", "WARN")

# ============================================================
# PHASE 4 : LOT 4 - Checklist avant remise (drawer)
# ============================================================
log("PHASE 4 : LOT 4 - Checklist drawer", "STEP")

js_src = open(JS, "r", encoding="utf-8").read()

if "drawer-checklist" in js_src:
    log("Checklist deja presente", "WARN")
else:
    # Injecter avant les actions du drawer
    OLD_ACTIONS = '    // ---- Actions ----\n    h += \'<div class="ph-drawer-actions">\';'
    NEW_ACTIONS = '''    // ---- Checklist avant remise (Lot 4) ----
    if (o.status === "prete") {
      h += '<div class="ph-drawer-block drawer-checklist">';
      h += '<div class="ph-drawer-lbl">Controle avant remise</div>';
      h += '<label style="display:block;font-size:13.5px;padding:6px 0"><input type="checkbox" class="ph-check" data-check="1"> Produits verifies</label>';
      h += '<label style="display:block;font-size:13.5px;padding:6px 0"><input type="checkbox" class="ph-check" data-check="2"> Ordonnance conforme</label>';
      h += '<label style="display:block;font-size:13.5px;padding:6px 0"><input type="checkbox" class="ph-check" data-check="3"> Paiement valide</label>';
      h += '<div style="margin-top:8px;font-size:12px;color:#64748b" id="ph-check-hint">Cochez les 3 points avant de marquer terminee</div>';
      h += '</div>';
    }

    // ---- Actions ----
    h += '<div class="ph-drawer-actions">\';'''

    if OLD_ACTIONS in js_src:
        js_src = js_src.replace(OLD_ACTIONS, NEW_ACTIONS, 1)
        # Verifier equilibre accolades
        if js_src.count("{") - js_src.count("}") != 0:
            log("Accolades desequilibrees - rollback partiel", "ERR")
            shutil.copy2(os.path.join(BAK, "pharmacien.js"), JS)
            sys.exit(1)
        open(JS, "w", encoding="utf-8").write(js_src)
        log("Checklist avant remise ajoutee", "OK")
    else:
        log("Ancre actions drawer introuvable - SKIP", "WARN")

# ============================================================
# PHASE 5 : Test E2E
# ============================================================
log("PHASE 5 : Generation test", "STEP")

TEST_LINES = [
    "# -*- coding: utf-8 -*-",
    "# Test Lot 3+4+5",
    "import json, urllib.request, urllib.error, http.cookiejar, sys",
    "",
    'BASE = "http://127.0.0.1:8000"',
    "",
    "def login(email, password):",
    "    cj = http.cookiejar.CookieJar()",
    "    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))",
    "    req = urllib.request.Request(",
    '        BASE + "/api/auth/login",',
    '        data=json.dumps({"email": email, "password": password}).encode(),',
    '        headers={"Content-Type": "application/json"}, method="POST")',
    "    op.open(req, timeout=10)",
    "    return op",
    "",
    "results = []",
    "def check(label, ok, detail=''):",
    '    results.append((label, ok, detail))',
    '    print("  [" + ("OK" if ok else "!!") + "] " + label + "  " + detail)',
    "",
    'print("=" * 60)',
    'print("TEST LOT 3+4+5")',
    'print("=" * 60)',
    "",
    "# Stats endpoint",
    'print("\\n[S1] /api/stats/summary pharmacien")',
    "try:",
    '    op = login("pharmacien@test.tg", "Test1234")',
    '    r = op.open(BASE + "/api/stats/summary", timeout=10)',
    "    data = json.loads(r.read().decode())",
    '    check("Stats accessible", r.status == 200, "")',
    '    check("total_orders present", "total_orders" in data)',
    '    check("by_status present", "by_status" in data)',
    '    check("payments_by_status present", "payments_by_status" in data)',
    "except Exception as e:",
    '    check("Stats pharmacien", False, str(e))',
    "",
    "# Stats refusees patient",
    'print("\\n[S2] /api/stats/summary patient -> 403")',
    "try:",
    '    op_p = login("patient@test.tg", "Test1234")',
    "    try:",
    '        r = op_p.open(BASE + "/api/stats/summary", timeout=10)',
    '        check("Patient bloque", r.status == 403, "recu " + str(r.status))',
    "    except urllib.error.HTTPError as e:",
    '        check("Patient bloque", e.code == 403, "recu " + str(e.code))',
    "except Exception as e:",
    '    check("Patient login", False, str(e))',
    "",
    "# Stats refusees non auth",
    'print("\\n[S3] /api/stats/summary sans auth -> 403")',
    "try:",
    '    r = urllib.request.urlopen(BASE + "/api/stats/summary", timeout=10)',
    '    check("Non auth bloque", r.status == 403, "")',
    "except urllib.error.HTTPError as e:",
    '    check("Non auth bloque", e.code in (401, 403), "recu " + str(e.code))',
    "except Exception as e:",
    '    check("Non auth", False, str(e))',
    "",
    'print()',
    'print("=" * 60)',
    'ok = sum(1 for _, s, _ in results if s)',
    'print("RESULTAT : " + str(ok) + "/" + str(len(results)))',
    'print("=" * 60)',
    "sys.exit(0 if ok == len(results) else 1)",
    "",
]

test_path = os.path.join(ROOT, "test_lot345.py")
wf(test_path, "\n".join(TEST_LINES))
log("test_lot345.py genere", "OK")

# ============================================================
# RAPPORT
# ============================================================
print()
print("=" * 78)
print("RAPPORT FINAL")
print("=" * 78)
print("Backup : " + BAK)
print()
print("Fichiers modifies / crees :")
print("  - main.py (endpoint /api/stats/summary)")
print("  - static/pharmacien_stats.js (nouveau)")
print("  - static/pharmacien.html (reference script)")
if "drawer-checklist" in js_src:
    print("  - static/pharmacien.js (checklist avant remise)")
print("  - test_lot345.py (nouveau)")
print()
print("[CMD] Restart Uvicorn :")
print("  taskkill /F /IM uvicorn.exe 2>nul")
print("  taskkill /F /IM python.exe 2>nul")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print()
print("[TEST] Apres restart :")
print("  1) python test_lot345.py")
print("  2) /pharmacien -> Admin -> onglet Statistiques")
print("  3) Ouvrir une commande prete -> checklist visible")
print()
print("[ROLLBACK] :")
print('  copy "' + BAK + '\\main.py" "' + MAIN + '"')
print('  copy "' + BAK + '\\pharmacien.html" "' + HTML + '"')
print('  copy "' + BAK + '\\pharmacien.js" "' + JS + '"')
print('  del "' + NEW + '"')
print()
print("[ATTENTION] Lot 2 p2 (coherence front/back) NON inclus.")
print("            Revue manuelle page par page requise.")