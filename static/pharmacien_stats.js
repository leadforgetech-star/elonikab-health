/* ============================================================
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
    box.innerHTML =
      '<div class="ph-kpi ph-kpi-ok">' +
        '<span class="ph-kpi-ico">&#128197;</span>' +
        '<strong>' + (data.today_orders || 0) + '</strong>' +
        '<small>Commandes aujourd&#39;hui</small>' +
      '</div>' +
      '<div class="ph-kpi">' +
        '<span class="ph-kpi-ico">&#128230;</span>' +
        '<strong>' + (data.total_orders || 0) + '</strong>' +
        '<small>Total commandes</small>' +
      '</div>' +
      '<div class="ph-kpi ph-kpi-money ph-kpi-ok">' +
        '<span class="ph-kpi-ico">&#128176;</span>' +
        '<strong>' + fmtMoney(data.today_revenue || 0) + '</strong>' +
        '<small>Revenus aujourd&#39;hui</small>' +
      '</div>' +
      '<div class="ph-kpi ph-kpi-warn">' +
        '<span class="ph-kpi-ico">&#9203;</span>' +
        '<strong>' + (data.pending_verify || 0) + '</strong>' +
        '<small>Paiements a valider</small>' +
      '</div>';
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
