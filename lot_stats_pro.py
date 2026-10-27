# -*- coding: utf-8 -*-
"""
Statistiques PRO - onglet dedie + graphiques Chart.js
======================================================
- Enrichit /api/stats/summary (30 jours, top produits, top clients, etc.)
- Nouvel onglet "Stats" dans la sidebar
- Vue dediee avec 6 graphiques pro (line, bar, donut)
- Atomic : rollback auto si erreur
"""
import os, re, shutil, datetime, sys

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
MAIN = os.path.join(ROOT, "main.py")
HTML = os.path.join(ROOT, "static", "pharmacien.html")
JS   = os.path.join(ROOT, "static", "pharmacien.js")
CSS  = os.path.join(ROOT, "static", "pharmacien_v6.css")
NEWJS = os.path.join(ROOT, "static", "pharmacien_stats.js")

TS  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK = os.path.join(ROOT, "_backup_stats_pro_" + TS)
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
print("STATS PRO - " + TS)
print("=" * 78)

# ============================================================
# PHASE 0 : Backup
# ============================================================
log("PHASE 0 : Backup", "STEP")
for f, n in [(MAIN, "main.py"), (HTML, "pharmacien.html"),
             (JS, "pharmacien.js"), (CSS, "pharmacien_v6.css")]:
    if os.path.isfile(f):
        shutil.copy2(f, os.path.join(BAK, n))
        log("Backup " + n, "OK")

# ============================================================
# PHASE 1 : Backend - enrichir /api/stats/summary
# ============================================================
log("PHASE 1 : Backend - endpoint enrichi", "STEP")

main_src = open(MAIN, "r", encoding="utf-8").read()

if "daily_series" in main_src:
    log("Endpoint deja enrichi", "WARN")
else:
    OLD_EP = '''@app.get("/api/stats/summary")
def stats_summary(user = Depends(get_current_user_dep)):
    """Statistiques reelles separees : CA, encaisse, remboursements."""
    if not user or user["role"] not in ("PHARMACIEN", "ADMIN"):
        raise HTTPException(403, "Reserve au personnel pharmacie")
    conn = get_db()
    try:'''

    NEW_EP = '''@app.get("/api/stats/summary")
def stats_summary(user = Depends(get_current_user_dep)):
    """Statistiques completes : series temporelles, top produits, top clients."""
    if not user or user["role"] not in ("PHARMACIEN", "ADMIN"):
        raise HTTPException(403, "Reserve au personnel pharmacie")
    from datetime import timedelta
    conn = get_db()
    try:'''

    if OLD_EP in main_src:
        main_src = main_src.replace(OLD_EP, NEW_EP, 1)
        log("En-tete endpoint remplace", "OK")
    else:
        log("En-tete endpoint introuvable", "WARN")

    # Ajouter les donnees enrichies avant "return {"
    OLD_RET = '''        return {
            "total_orders": total,
            "today_orders": today_orders,
            "by_status": by_status,
            "payments_by_status": pay_by_status,
            "pending_verify": pending_verify,
            "refund_required": refund_required,
        }'''

    NEW_RET = '''        # === Series 30 jours ===
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
        }'''

    if OLD_RET in main_src:
        main_src = main_src.replace(OLD_RET, NEW_RET, 1)
        open(MAIN, "w", encoding="utf-8").write(main_src)
        ok, err = syntax_ok(MAIN)
        if not ok:
            log("main.py ERREUR : " + str(err), "ERR")
            shutil.copy2(os.path.join(BAK, "main.py"), MAIN)
            log("ROLLBACK main.py", "ERR")
            sys.exit(1)
        log("main.py : endpoint enrichi", "OK")
    else:
        log("Bloc return introuvable", "WARN")

# ============================================================
# PHASE 2 : HTML - nouvelle section + onglet
# ============================================================
log("PHASE 2 : HTML - section + onglet", "STEP")

html_src = open(HTML, "r", encoding="utf-8").read()

# 2a. Ajouter le nav item
if 'data-ph-tab="stats"' in html_src:
    log("Onglet stats deja present", "WARN")
else:
    OLD_NAV = '''  <a href="#" data-ph-tab="admin">
    <span class="ph-nav-ico">&#9881;</span>
    <span class="ph-nav-lbl">Admin</span>
  </a>'''
    NEW_NAV = '''  <a href="#" data-ph-tab="stats">
    <span class="ph-nav-ico">&#128200;</span>
    <span class="ph-nav-lbl">Stats</span>
  </a>
  <a href="#" data-ph-tab="admin">
    <span class="ph-nav-ico">&#9881;</span>
    <span class="ph-nav-lbl">Admin</span>
  </a>'''
    if OLD_NAV in html_src:
        html_src = html_src.replace(OLD_NAV, NEW_NAV, 1)
        log("Onglet Stats ajoute", "OK")
    else:
        log("Ancre nav Admin introuvable", "WARN")

# 2b. Ajouter la section
if 'data-ph-page="stats"' in html_src:
    log("Section stats deja presente", "WARN")
else:
    STATS_SECTION = '''
<section data-ph-page="stats" class="ph-stats-page">
  <div class="ph-stats-inner">
    <div class="ph-stats-head">
      <h1 class="ph-stats-title">Statistiques</h1>
      <p class="ph-stats-sub">Vue d'ensemble de l'activite</p>
    </div>

    <!-- KPI cards -->
    <div class="ph-stats-kpis" id="ph-stats-kpis">
      <div class="ph-kpi"><strong>—</strong><span>Aujourd hui</span></div>
      <div class="ph-kpi"><strong>—</strong><span>Total commandes</span></div>
      <div class="ph-kpi"><strong>—</strong><span>Panier moyen</span></div>
      <div class="ph-kpi ph-kpi-warn"><strong>—</strong><span>A valider</span></div>
    </div>

    <!-- Line chart : commandes + revenus 30 jours -->
    <div class="ph-stats-block">
      <div class="ph-stats-block-head">
        <h2>Commandes & revenus (30 derniers jours)</h2>
      </div>
      <div class="ph-chart-wrap" style="height:280px">
        <canvas id="ph-chart-line"></canvas>
      </div>
    </div>

    <!-- 2 colonnes : donut statut + donut categories -->
    <div class="ph-stats-2col">
      <div class="ph-stats-block">
        <div class="ph-stats-block-head"><h2>Statut des commandes</h2></div>
        <div class="ph-chart-wrap" style="height:240px">
          <canvas id="ph-chart-status"></canvas>
        </div>
      </div>
      <div class="ph-stats-block">
        <div class="ph-stats-block-head"><h2>Categories vendues</h2></div>
        <div class="ph-chart-wrap" style="height:240px">
          <canvas id="ph-chart-cats"></canvas>
        </div>
      </div>
    </div>

    <!-- Bar chart : top produits -->
    <div class="ph-stats-block">
      <div class="ph-stats-block-head"><h2>Top 5 produits</h2></div>
      <div class="ph-chart-wrap" style="height:260px">
        <canvas id="ph-chart-products"></canvas>
      </div>
    </div>

    <!-- Bar chart : heures de commande -->
    <div class="ph-stats-block">
      <div class="ph-stats-block-head"><h2>Commandes par heure</h2></div>
      <div class="ph-chart-wrap" style="height:220px">
        <canvas id="ph-chart-hours"></canvas>
      </div>
    </div>

    <!-- Top clients -->
    <div class="ph-stats-block">
      <div class="ph-stats-block-head"><h2>Top clients</h2></div>
      <div id="ph-stats-clients" class="ph-stats-clients">
        <div class="ph-stats-empty">Chargement...</div>
      </div>
    </div>
  </div>
</section>
'''
    # Inserer avant <div id="driver-modal"
    anchor = '<div id="driver-modal"'
    if anchor in html_src:
        html_src = html_src.replace(anchor, STATS_SECTION + "\n" + anchor, 1)
        log("Section Stats ajoutee", "OK")
    else:
        log("Ancre driver-modal introuvable", "WARN")

# 2c. Chart.js CDN
if "chart.umd" not in html_src:
    CDN = '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>\n'
    if "</head>" in html_src:
        html_src = html_src.replace("</head>", CDN + "</head>", 1)
        log("Chart.js CDN ajoute", "OK")

open(HTML, "w", encoding="utf-8").write(html_src)

# ============================================================
# PHASE 3 : CSS - styles stats + display:block
# ============================================================
log("PHASE 3 : CSS", "STEP")

css_src = open(CSS, "r", encoding="utf-8").read()

if "ph-stats-page" in css_src:
    log("CSS stats deja present", "WARN")
else:
    CSS_ADD = '''

/* ============================================================
   STATS PAGE (Lot 5 - vue dediee)
   ============================================================ */
body[data-active-page="stats"] [data-ph-page="stats"]{display:block}

.ph-stats-page{
  min-height:calc(100vh - 66px);
  background:var(--ph-bg);
  padding:22px 18px 60px;
}
.ph-stats-inner{max-width:1100px;margin:0 auto}
.ph-stats-head{margin-bottom:20px}
.ph-stats-title{
  font-size:24px;font-weight:800;letter-spacing:-.02em;
  color:var(--ph-ink);margin:0 0 4px;
}
.ph-stats-sub{font-size:14px;color:var(--ph-muted);margin:0}

.ph-stats-kpis{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
  gap:12px;margin-bottom:18px;
}
.ph-kpi{
  background:#fff;border:1px solid var(--ph-line);
  border-radius:14px;padding:16px 18px;
  display:flex;flex-direction:column;gap:4px;
}
.ph-kpi strong{
  font-size:26px;font-weight:800;color:var(--ph-blue-dark);
  line-height:1.1;
}
.ph-kpi span{
  font-size:11.5px;font-weight:700;color:var(--ph-muted);
  text-transform:uppercase;letter-spacing:.05em;
}
.ph-kpi-warn strong{color:#B26B00}
.ph-kpi-danger strong{color:#B23C3C}
.ph-kpi-ok strong{color:#0A7A5A}

.ph-stats-block{
  background:#fff;border:1px solid var(--ph-line);
  border-radius:14px;padding:16px 18px;margin-bottom:16px;
}
.ph-stats-block-head{
  display:flex;justify-content:space-between;align-items:center;
  margin-bottom:12px;
}
.ph-stats-block-head h2{
  font-size:13px;font-weight:800;color:var(--ph-ink);
  text-transform:uppercase;letter-spacing:.06em;margin:0;
}
.ph-chart-wrap{position:relative}

.ph-stats-2col{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:16px;
}
@media (max-width:800px){
  .ph-stats-2col{grid-template-columns:1fr}
}

.ph-stats-clients{overflow-x:auto}
.ph-stats-table{
  width:100%;border-collapse:collapse;font-size:13.5px;
}
.ph-stats-table th{
  text-align:left;padding:8px 6px;border-bottom:1px solid var(--ph-line);
  font-size:11px;text-transform:uppercase;letter-spacing:.04em;
  color:var(--ph-muted);
}
.ph-stats-table td{
  padding:10px 6px;border-bottom:1px solid #f1f5f9;
}
.ph-stats-table tr:last-child td{border-bottom:0}
.ph-stats-table td.num{text-align:right;font-weight:800;color:var(--ph-ink)}

.ph-stats-empty{
  text-align:center;padding:30px 12px;color:var(--ph-muted);
  font-size:13.5px;
}

@media (max-width:720px){
  .ph-stats-page{padding:16px 12px 40px}
  .ph-stats-title{font-size:20px}
  .ph-kpi strong{font-size:22px}
  .ph-stats-block{padding:14px}
}
'''
    css_src = css_src + CSS_ADD
    open(CSS, "w", encoding="utf-8").write(css_src)
    log("CSS stats ajoute", "OK")

# ============================================================
# PHASE 4 : JS - nouveau module stats
# ============================================================
log("PHASE 4 : JS module stats", "STEP")

JS_MODULE = '''/* ============================================================
   Elonikab Health - Statistiques pro (Lot 5)
   Vue dediee avec Chart.js
   ============================================================ */
(function () {
  "use strict";
  var API = "/api";
  var charts = {};

  function fmtMoney(v) {
    var n = Math.round(Number(v) || 0);
    try { return n.toLocaleString("fr-FR") + " FCFA"; }
    catch (e) { return n + " FCFA"; }
  }

  function $(id) { return document.getElementById(id); }

  function destroyChart(id) {
    if (charts[id]) {
      try { charts[id].destroy(); } catch (e) {}
      charts[id] = null;
    }
  }

  function renderKPIs(data) {
    var box = $("ph-stats-kpis");
    if (!box) return;
    var pays = data.payments_by_status || {};
    var verified = pays["VERIFIED"] || {count: 0, amount: 0};
    box.innerHTML = '';
    box.innerHTML =
      '<div class="ph-kpi ph-kpi-ok"><strong>' + (data.today_orders || 0) + '</strong><span>Aujourd hui</span></div>' +
      '<div class="ph-kpi"><strong>' + (data.total_orders || 0) + '</strong><span>Total commandes</span></div>' +
      '<div class="ph-kpi"><strong>' + fmtMoney(data.avg_basket || 0) + '</strong><span>Panier moyen</span></div>' +
      '<div class="ph-kpi ph-kpi-warn"><strong>' + (data.pending_verify || 0) + '</strong><span>A valider</span></div>';
  }

  function renderLineChart(data) {
    var c = $("ph-chart-line");
    if (!c || typeof Chart === "undefined") return;
    destroyChart("line");
    var labels = (data.daily_series || []).map(function (d) {
      return d.date.slice(5); // MM-DD
    });
    var orders = (data.daily_series || []).map(function (d) { return d.orders; });
    var revenues = (data.daily_series || []).map(function (d) { return d.revenue; });

    charts.line = new Chart(c, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Commandes",
            data: orders,
            borderColor: "#174A7E",
            backgroundColor: "rgba(23,74,126,0.08)",
            tension: 0.35,
            fill: true,
            yAxisID: "y",
            borderWidth: 2,
            pointRadius: 0,
          },
          {
            label: "Revenus (FCFA)",
            data: revenues,
            borderColor: "#0A7A5A",
            backgroundColor: "rgba(10,122,90,0.05)",
            tension: 0.35,
            fill: false,
            yAxisID: "y1",
            borderWidth: 2,
            pointRadius: 0,
            borderDash: [4, 3],
          }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { position: "top", labels: { boxWidth: 12, font: { size: 11 } } }
        },
        scales: {
          y: {
            type: "linear", position: "left",
            beginAtZero: true,
            ticks: { font: { size: 10 } }
          },
          y1: {
            type: "linear", position: "right",
            beginAtZero: true,
            grid: { drawOnChartArea: false },
            ticks: { font: { size: 10 } }
          },
          x: { ticks: { font: { size: 10 } } }
        }
      }
    });
  }

  function renderStatusChart(data) {
    var c = $("ph-chart-status");
    if (!c || typeof Chart === "undefined") return;
    destroyChart("status");
    var by = data.by_status || {};
    var order = [
      ["en_attente", "En attente", "#B26B00"],
      ["confirmee", "Confirmee", "#0A7A5A"],
      ["en_preparation", "En preparation", "#6335B8"],
      ["prete", "Prete", "#0369A1"],
      ["en_livraison", "En livraison", "#2A6BA8"],
      ["terminee", "Terminee", "#475569"],
      ["refusee", "Refusee", "#B23C3C"]
    ];
    var labels = [], values = [], colors = [];
    order.forEach(function (t) {
      var n = by[t[0]] || 0;
      if (n > 0) {
        labels.push(t[1]);
        values.push(n);
        colors.push(t[2]);
      }
    });
    if (labels.length === 0) {
      labels = ["Aucune donnee"]; values = [1]; colors = ["#E2E8F0"];
    }
    charts.status = new Chart(c, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{ data: values, backgroundColor: colors, borderWidth: 0 }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { position: "right", labels: { boxWidth: 10, font: { size: 11 } } }
        },
        cutout: "62%"
      }
    });
  }

  function renderCatsChart(data) {
    var c = $("ph-chart-cats");
    if (!c || typeof Chart === "undefined") return;
    destroyChart("cats");
    var cats = data.categories || {};
    var labels = Object.keys(cats).slice(0, 6);
    var values = labels.map(function (k) { return cats[k]; });
    if (labels.length === 0) {
      labels = ["Aucune donnee"]; values = [1];
    }
    var palette = ["#174A7E", "#2A6BA8", "#0A7A5A", "#B26B00", "#6335B8", "#0369A1"];
    charts.cats = new Chart(c, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: palette.slice(0, labels.length),
          borderWidth: 0
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { position: "right", labels: { boxWidth: 10, font: { size: 11 } } }
        },
        cutout: "62%"
      }
    });
  }

  function renderProductsChart(data) {
    var c = $("ph-chart-products");
    if (!c || typeof Chart === "undefined") return;
    destroyChart("products");
    var top = (data.top_products || []).slice(0, 5);
    var labels = top.map(function (p) {
      var n = p.name || "";
      return n.length > 28 ? n.slice(0, 26) + "…" : n;
    });
    var values = top.map(function (p) { return p.quantity; });
    if (labels.length === 0) { labels = ["Aucune donnee"]; values = [0]; }
    charts.products = new Chart(c, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: "Quantite vendue",
          data: values,
          backgroundColor: "#174A7E",
          borderRadius: 6
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true, ticks: { font: { size: 10 } } },
          y: { ticks: { font: { size: 11 } } }
        }
      }
    });
  }

  function renderHoursChart(data) {
    var c = $("ph-chart-hours");
    if (!c || typeof Chart === "undefined") return;
    destroyChart("hours");
    var hourly = data.hourly || new Array(24).fill(0);
    var labels = [];
    for (var i = 0; i < 24; i++) labels.push((i < 10 ? "0" : "") + i + "h");
    charts.hours = new Chart(c, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: "Commandes",
          data: hourly,
          backgroundColor: "#2A6BA8",
          borderRadius: 4
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { font: { size: 10 }, precision: 0 } },
          x: { ticks: { font: { size: 9 } } }
        }
      }
    });
  }

  function renderTopClients(data) {
    var box = $("ph-stats-clients");
    if (!box) return;
    var clients = data.top_clients || [];
    if (clients.length === 0) {
      box.innerHTML = '<div class="ph-stats-empty">Aucun client pour le moment.</div>';
      return;
    }
    var h = '<table class="ph-stats-table"><thead><tr>';
    h += '<th>#</th><th>Client</th><th>Telephone</th><th>Commandes</th><th style="text-align:right">Total depense</th>';
    h += '</tr></thead><tbody>';
    clients.forEach(function (c, i) {
      h += '<tr>';
      h += '<td>' + (i + 1) + '</td>';
      h += '<td>' + (c.name || "—") + '</td>';
      h += '<td>' + (c.phone || "—") + '</td>';
      h += '<td class="num">' + (c.orders || 0) + '</td>';
      h += '<td class="num">' + fmtMoney(c.spent || 0) + '</td>';
      h += '</tr>';
    });
    h += '</tbody></table>';
    box.innerHTML = h;
  }

  function loadStats() {
    var page = document.querySelector('[data-ph-page="stats"]');
    if (!page) return;
    // Charger les donnees
    fetch(API + "/stats/summary", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        renderKPIs(data);
        renderLineChart(data);
        renderStatusChart(data);
        renderCatsChart(data);
        renderProductsChart(data);
        renderHoursChart(data);
        renderTopClients(data);
      })
      .catch(function (e) {
        console.warn("[stats] erreur :", e);
      });
  }

  // Charger quand on clique sur l'onglet Stats
  document.addEventListener("click", function (ev) {
    var tab = ev.target.closest ? ev.target.closest('[data-ph-tab="stats"]') : null;
    if (tab) setTimeout(loadStats, 200);
  });

  // Charger aussi si on arrive directement sur la page stats
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      if (document.body.getAttribute("data-active-page") === "stats") loadStats();
    });
  }

  window.phLoadStatsPro = loadStats;
})();
'''

wf(NEWJS, JS_MODULE)
log("pharmacien_stats.js (v2) ecrit", "OK")

# ============================================================
# PHASE 5 : Verification finale
# ============================================================
print()
print("=" * 78)
print("VERIFICATION")
print("=" * 78)

final_main = open(MAIN, "r", encoding="utf-8").read()
final_html = open(HTML, "r", encoding="utf-8").read()
final_css = open(CSS, "r", encoding="utf-8").read()
final_js = open(NEWJS, "r", encoding="utf-8").read()

checks = [
    ("Backend : daily_series",       "daily_series" in final_main),
    ("Backend : top_products",       "top_products" in final_main),
    ("Backend : top_clients",        "top_clients" in final_main),
    ("HTML : onglet Stats",          'data-ph-tab="stats"' in final_html),
    ("HTML : section stats",         'data-ph-page="stats"' in final_html),
    ("HTML : Chart.js CDN",          "chart.umd" in final_html),
    ("CSS : styles stats",           "ph-stats-page" in final_css),
    ("CSS : display:block stats",    'body[data-active-page="stats"]' in final_css),
    ("JS : renderLineChart",         "renderLineChart" in final_js),
    ("JS : 5 chart types",           all(x in final_js for x in ["renderLineChart", "renderStatusChart", "renderCatsChart", "renderProductsChart", "renderHoursChart"])),
    ("JS : top clients table",       "renderTopClients" in final_js),
]
for label, ok in checks:
    print("  [" + ("OK" if ok else "!!") + "] " + label)

ok_count = sum(1 for _, ok in checks if ok)
print()
print("  RESULTAT : " + str(ok_count) + "/" + str(len(checks)))
print()
print("Backup : " + BAK)
print()
print("[CMD] Restart Uvicorn :")
print("  taskkill /F /IM uvicorn.exe 2>nul")
print("  taskkill /F /IM python.exe 2>nul")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print()
print("[TEST] Edge : F12 > Application > Clear site data + Disable cache + Ctrl+Shift+R")
print("  1) /pharmacien -> voir un nouvel onglet 'Stats' dans la sidebar")
print("  2) Cliquer dessus -> 4 KPIs + 5 graphiques + top clients")
print()
print("[ROLLBACK] :")
print('  copy "' + BAK + '\\main.py" "' + MAIN + '"')
print('  copy "' + BAK + '\\pharmacien.html" "' + HTML + '"')
print('  copy "' + BAK + '\\pharmacien_v6.css" "' + CSS + '"')
print('  del "' + NEWJS + '"')