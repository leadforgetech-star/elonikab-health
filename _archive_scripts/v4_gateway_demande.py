"""
v4_gateway_demande.py
Page Demande devient un simple gateway avec 2 cards premium.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_gateway_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(STATIC / "professional_demande.html", backup / "professional_demande.html")
shutil.copy2(STATIC / "professional_demande.js", backup / "professional_demande.js")
print("[OK] Backup ->", backup.name)

# ============================================================
# HTML : gateway 2 cards
# ============================================================
DEM_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Nouvelle demande - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
:root{
  --blue:#1a4a7f;--blue-dark:#123258;--blue-soft:#eaf1f9;
  --wa:#25d366;--wa-dark:#1da851;
  --ink:#0f172a;--muted:#64748b;--line:#e6ebf1;--bg:#f7fafc;
}
*,*::before,*::after{box-sizing:border-box}
html,body{overflow-x:clip;margin:0;padding:0}
body{
  font-family:-apple-system,"Segoe UI",system-ui,sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.5;font-size:15px;
  -webkit-font-smoothing:antialiased;padding-bottom:100px;
}
a{color:inherit;text-decoration:none}
button{font-family:inherit;cursor:pointer}
.hidden{display:none !important}

/* ---- Header ---- */
.gw-header{
  background:#fff;border-bottom:1px solid var(--line);
  position:sticky;top:0;z-index:50;
}
.gw-header-inner{
  max-width:640px;margin:0 auto;padding:12px 16px;
  display:flex;align-items:center;gap:12px;
}
.gw-back{
  width:36px;height:36px;border-radius:10px;border:1px solid var(--line);
  background:#fff;color:var(--ink);font-size:18px;
  display:flex;align-items:center;justify-content:center;text-decoration:none;
}
.gw-title{font-size:15px;font-weight:800;flex:1}
.gw-bell{
  width:36px;height:36px;border-radius:10px;border:1px solid var(--line);
  background:#fff;color:var(--ink);font-size:16px;
  display:flex;align-items:center;justify-content:center;position:relative;
}
.gw-bell-badge{
  position:absolute;top:-3px;right:-3px;background:#dc2626;
  color:#fff;font-size:9px;font-weight:800;min-width:16px;
  height:16px;padding:0 4px;border-radius:999px;
  display:flex;align-items:center;justify-content:center;
}

/* ---- Main ---- */
.gw-main{max-width:640px;margin:0 auto;padding:28px 20px 40px}

.gw-hero{margin:0 0 24px;text-align:center}
.gw-hero h1{
  font-size:24px;font-weight:800;line-height:1.2;
  letter-spacing:-.02em;margin:0 0 8px;color:var(--ink);
}
.gw-hero p{
  font-size:14px;color:var(--muted);margin:0;
}

/* ---- Cards ---- */
.gw-cards{display:flex;flex-direction:column;gap:16px;margin:24px 0}

.gw-card{
  display:block;background:#fff;
  border:1px solid var(--line);border-radius:18px;
  padding:22px 20px;cursor:pointer;
  transition:all .18s cubic-bezier(.4,0,.2,1);
  position:relative;overflow:hidden;
  text-decoration:none;color:inherit;
}
.gw-card:hover{
  border-color:var(--blue);
  transform:translateY(-2px);
  box-shadow:0 10px 28px rgba(26,74,127,.10);
}
.gw-card:active{transform:translateY(0)}

.gw-card-icon{
  width:52px;height:52px;border-radius:14px;
  display:flex;align-items:center;justify-content:center;
  font-size:24px;margin-bottom:16px;
}
.gw-card.cat .gw-card-icon{
  background:var(--blue-soft);color:var(--blue);
}
.gw-card.wa .gw-card-icon{
  background:#e6f9ee;color:var(--wa);
}

.gw-card-title{
  font-size:17px;font-weight:800;letter-spacing:-.01em;
  color:var(--ink);margin:0 0 6px;line-height:1.25;
}
.gw-card-desc{
  font-size:13.5px;color:var(--muted);
  line-height:1.5;margin:0 0 18px;
}

.gw-card-foot{
  display:flex;align-items:center;justify-content:space-between;
  padding-top:14px;border-top:1px solid var(--line);
}
.gw-card-cta{
  font-size:13.5px;font-weight:800;
  display:flex;align-items:center;gap:6px;
}
.gw-card.cat .gw-card-cta{color:var(--blue)}
.gw-card.wa .gw-card-cta{color:var(--wa-dark)}
.gw-card-arrow{
  font-size:18px;line-height:1;transition:transform .18s;
}
.gw-card:hover .gw-card-arrow{transform:translateX(4px)}

/* Badge elements en cours */
.gw-card-badge{
  position:absolute;top:18px;right:18px;
  background:var(--blue);color:#fff;
  font-size:11px;font-weight:800;
  padding:4px 10px;border-radius:999px;
}

/* ---- Separateur OU ---- */
.gw-or{
  display:flex;align-items:center;gap:14px;
  margin:4px 0;color:var(--muted);
  font-size:12px;font-weight:800;
  text-transform:uppercase;letter-spacing:.15em;
}
.gw-or::before,
.gw-or::after{
  content:"";flex:1;height:1px;background:var(--line);
}

/* ---- Hint ---- */
.gw-hint{
  background:var(--blue-soft);
  border:1px solid #cddff0;
  border-radius:14px;padding:14px 16px;
  font-size:13px;line-height:1.55;
  color:var(--blue-dark);
  margin-top:24px;
}
.gw-hint strong{color:var(--blue-dark);font-weight:800}
.gw-hint .emoji{font-size:15px;margin-right:4px}

/* ---- Navbar ---- */
.pro-navbar{
  position:fixed;bottom:0;left:0;right:0;z-index:200;
  background:#fff;border-top:1px solid var(--line);
  display:grid;grid-template-columns:1fr 1fr 76px 1fr 1fr;
  padding:6px 6px calc(6px + env(safe-area-inset-bottom)) 6px;
  box-shadow:0 -2px 12px rgba(15,38,32,.06);
}
.pro-navbar a{
  padding:8px 4px;text-align:center;font-size:10px;font-weight:700;
  color:var(--muted);display:flex;flex-direction:column;align-items:center;gap:3px;
  text-decoration:none;
}
.pro-navbar a .ico{font-size:18px;line-height:1}
.pro-navbar a.active{color:var(--blue-dark)}
.pro-navbar .central{
  margin-top:-22px;background:var(--blue);color:#fff;border-radius:50%;
  width:64px;height:64px;justify-self:center;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  font-size:22px;font-weight:800;
  box-shadow:0 6px 20px rgba(26,74,127,.35);
  border:4px solid var(--bg);position:relative;
}
.pro-navbar .central .lbl{font-size:9px;font-weight:700;margin-top:-2px}
.pro-navbar .central .nav-count{
  position:absolute;top:-4px;right:-4px;
  min-width:22px;height:22px;padding:0 6px;
  background:#fff;color:var(--blue-dark);
  border:2px solid var(--blue);
  border-radius:999px;font-size:11px;font-weight:900;
  display:flex;align-items:center;justify-content:center;
}
.pro-navbar .central .nav-count.hidden{display:none}
.pro-navbar .central.active{background:var(--blue-dark)}

@media(max-width:400px){
  .gw-hero h1{font-size:20px}
  .gw-card{padding:18px}
  .gw-card-title{font-size:16px}
}
</style>
</head>
<body>

<header class="gw-header">
  <div class="gw-header-inner">
    <a class="gw-back" href="/professionnel" aria-label="Retour">&#8592;</a>
    <span class="gw-title">Nouvelle demande</span>
    <a class="gw-bell" href="/professionnel/commandes" aria-label="Commandes">
      &#128276;
      <span class="gw-bell-badge hidden" id="bell-badge">0</span>
    </a>
  </div>
</header>

<main class="gw-main">

  <div class="gw-hero">
    <h1>Comment souhaitez-vous<br>passer votre demande ?</h1>
    <p>Choisissez une méthode selon votre besoin.</p>
  </div>

  <div class="gw-cards">

    <!-- Option 1 : Catalogue -->
    <a class="gw-card cat" href="/professionnel/catalogue" id="card-catalogue">
      <span class="gw-card-badge hidden" id="catalogue-badge">0</span>
      <div class="gw-card-icon">&#128269;</div>
      <h2 class="gw-card-title">Commander depuis le catalogue</h2>
      <p class="gw-card-desc">
        Recherchez les produits, choisissez les quantités et constituez votre demande.
      </p>
      <div class="gw-card-foot">
        <span class="gw-card-cta">Parcourir le catalogue</span>
        <span class="gw-card-arrow">&#8594;</span>
      </div>
    </a>

    <!-- Séparateur -->
    <div class="gw-or">ou</div>

    <!-- Option 2 : WhatsApp -->
    <a class="gw-card wa" id="card-wa" target="_blank" rel="noopener"
       href="https://wa.me/22871039904?text=Bonjour%20Elokinab%20Health%2C%20je%20souhaite%20passer%20une%20commande.%20Voici%20ma%20liste%20%3A%0A%0A">
      <div class="gw-card-icon">&#128172;</div>
      <h2 class="gw-card-title">Commander via WhatsApp</h2>
      <p class="gw-card-desc">
        Envoyez votre liste, photo, PDF, vocal ou message libre directement à la pharmacie.
      </p>
      <div class="gw-card-foot">
        <span class="gw-card-cta">Ouvrir WhatsApp</span>
        <span class="gw-card-arrow">&#8594;</span>
      </div>
    </a>

  </div>

  <!-- Hint -->
  <div class="gw-hint">
    <span class="emoji">&#128161;</span>
    <strong>Vous ne savez pas quelle option choisir ?</strong><br>
    WhatsApp est recommandé pour les <strong>listes volumineuses</strong> ou les
    <strong>produits qui ne figurent pas</strong> dans notre catalogue.
  </div>

</main>

<nav class="pro-navbar">
  <a href="/professionnel"><span class="ico">&#127968;</span> Accueil</a>
  <a href="/professionnel/catalogue"><span class="ico">&#128722;</span> Catalogue</a>
  <a href="/professionnel/demande" class="central active" id="nav-central">
    <span>+</span><span class="lbl">Demande</span>
    <span class="nav-count hidden" id="nav-count">0</span>
  </a>
  <a href="/professionnel/commandes"><span class="ico">&#128230;</span> Commandes</a>
  <a href="/professionnel/etablissement"><span class="ico">&#127970;</span> Etabl.</a>
</nav>

<script>
(function () {
  // Affiche un badge sur la card Catalogue si une demande est en cours
  fetch("/api/pro/requests/draft", { credentials: "same-origin" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) {
      if (!d) return;
      return fetch("/api/pro/requests/" + d.reference, { credentials: "same-origin" })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (full) {
          if (!full) return;
          var n = (full.items || []).length + (full.attachments || []).length;
          if (n > 0) {
            var badge = document.getElementById("catalogue-badge");
            if (badge) { badge.textContent = n; badge.classList.remove("hidden"); }
            var navCount = document.getElementById("nav-count");
            if (navCount) {
              navCount.textContent = n > 99 ? "99+" : String(n);
              navCount.classList.remove("hidden");
            }
            var cta = document.querySelector("#card-catalogue .gw-card-cta");
            if (cta) cta.textContent = "Continuer ma demande";
          }
        });
    }).catch(function () {});

  // Badge notifications
  fetch("/api/notifications?unread_only=1", { credentials: "same-origin" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (list) {
      var n = Array.isArray(list) ? list.length : 0;
      var b = document.getElementById("bell-badge");
      if (b && n > 0) {
        b.textContent = n > 99 ? "99+" : String(n);
        b.classList.remove("hidden");
      }
    }).catch(function () {});
})();
</script>
</body>
</html>
'''
(STATIC / "professional_demande.html").write_text(DEM_HTML, encoding="utf-8")
print("[OK] professional_demande.html -> gateway 2 cards")

# Simplifier le JS : la page n'a plus besoin de logique complexe
DEM_JS = '''/* Elokinab Health - Gateway page demande */
/* Toute la logique est inline dans le HTML. Ce fichier est conserve
   pour compatibilite mais ne fait rien. */
'''
(STATIC / "professional_demande.js").write_text(DEM_JS, encoding="utf-8")
print("[OK] professional_demande.js -> nettoye")

print()
print("=" * 60)
print("GATEWAY DEMANDE LIVRE")
print("=" * 60)
print()
print("La page /professionnel/demande devient un simple gateway :")
print("  - Hero : 'Comment souhaitez-vous passer votre demande ?'")
print("  - Card 1 : 'Commander depuis le catalogue' (bleu)")
print("  - Separateur 'OU'")
print("  - Card 2 : 'Commander via WhatsApp' (vert)")
print("  - Hint : recommande WhatsApp pour listes volumineuses")
print()
print("Intelligent :")
print("  - Si demande en cours -> badge sur la card Catalogue")
print("  - CTA devient 'Continuer ma demande'")
print("  - Compteur sur la navbar synchronise")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R dans le navigateur")