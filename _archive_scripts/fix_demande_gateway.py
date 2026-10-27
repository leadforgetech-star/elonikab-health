"""
fix_demande_gateway.py
Reecrit professional_demande.html proprement avec ses styles gateway.
Ajoute les styles .gw-* dans professional_common.css.
"""
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

shutil.copy2(STATIC / "professional_demande.html", STATIC / "professional_demande.html.bak")
shutil.copy2(STATIC / "professional_common.css", STATIC / "professional_common.css.bak")
print("[OK] Backups crees")

# ============================================================
# 1. Ajouter les styles gateway dans professional_common.css
# ============================================================
CSS_PATH = STATIC / "professional_common.css"
css = CSS_PATH.read_text(encoding="utf-8")

GATEWAY_CSS = '''
/* ============================================================
   GATEWAY (page + Demande) - 2 cards
   ============================================================ */
.gw-hero{
  text-align:center;
  margin:0 0 26px;
}
.gw-hero h1{
  font-size:24px;
  font-weight:800;
  letter-spacing:-.02em;
  line-height:1.2;
  margin:0 0 8px;
  color:var(--ink);
}
.gw-hero p{
  font-size:14px;
  color:var(--muted);
  margin:0;
}

.gw-cards{
  display:flex;
  flex-direction:column;
  gap:14px;
  margin:24px 0 0;
}

.gw-card{
  display:block;
  background:#fff;
  border:1px solid var(--line);
  border-radius:var(--radius);
  padding:22px 20px;
  text-decoration:none;
  color:inherit;
  transition:.15s;
  position:relative;
  overflow:hidden;
}
.gw-card:hover{
  border-color:var(--blue);
  transform:translateY(-2px);
  box-shadow:0 10px 28px rgba(26,74,126,.10);
}
.gw-card:active{transform:translateY(0)}

.gw-card-icon{
  width:52px;
  height:52px;
  border-radius:14px;
  display:flex;
  align-items:center;
  justify-content:center;
  font-size:24px;
  margin-bottom:16px;
}
.gw-card.cat .gw-card-icon{
  background:var(--blue-soft);
  color:var(--blue);
}
.gw-card.wa .gw-card-icon{
  background:#E6F9EE;
  color:var(--wa-dark);
}

.gw-card-title{
  font-size:17px;
  font-weight:800;
  letter-spacing:-.01em;
  line-height:1.25;
  margin:0 0 6px;
  color:var(--ink);
}
.gw-card-desc{
  font-size:13.5px;
  color:var(--muted);
  line-height:1.5;
  margin:0 0 18px;
}
.gw-card-foot{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:10px;
  padding-top:14px;
  border-top:1px solid var(--line);
}
.gw-card-cta{
  font-size:13.5px;
  font-weight:800;
}
.gw-card.cat .gw-card-cta{color:var(--blue)}
.gw-card.wa .gw-card-cta{color:var(--wa-dark)}
.gw-card-arrow{
  font-size:18px;
  line-height:1;
  transition:transform .18s;
}
.gw-card:hover .gw-card-arrow{transform:translateX(4px)}

.gw-card-badge{
  position:absolute;
  top:18px;
  right:18px;
  background:var(--blue);
  color:#fff;
  font-size:11px;
  font-weight:800;
  padding:4px 10px;
  border-radius:999px;
}

.gw-or{
  display:flex;
  align-items:center;
  gap:14px;
  margin:4px 0;
  color:var(--muted);
  font-size:12px;
  font-weight:800;
  text-transform:uppercase;
  letter-spacing:.15em;
}
.gw-or::before,
.gw-or::after{
  content:"";
  flex:1;
  height:1px;
  background:var(--line);
}

.gw-hint{
  background:var(--blue-soft);
  border:1px solid var(--blue-line);
  border-radius:14px;
  padding:14px 16px;
  font-size:13px;
  line-height:1.55;
  color:var(--blue-dark);
  margin-top:24px;
}
.gw-hint strong{color:var(--blue-dark);font-weight:800}

@media (max-width:400px){
  .gw-hero h1{font-size:20px}
  .gw-card{padding:18px}
  .gw-card-title{font-size:16px}
}
'''

if ".gw-hero" not in css:
    css += GATEWAY_CSS
    CSS_PATH.write_text(css, encoding="utf-8")
    print("[OK] professional_common.css : styles gateway ajoutes")
else:
    print("[i] Styles gateway deja presents")

# ============================================================
# 2. Reecrire professional_demande.html proprement
# ============================================================
DEM_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Nouvelle demande - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<link rel="stylesheet" href="/static/professional_common.css">
</head>
<body>

<header class="pro-header">
  <div class="pro-header-inner">
    <a class="pro-brand" href="/professionnel">
      <span class="pro-brand-mark">+</span>
      Elokinab
    </a>
    <a class="pro-bell" href="/professionnel/commandes" aria-label="Notifications">
      &#128276;
    </a>
  </div>
</header>

<main class="pro-main">

  <div class="gw-hero">
    <h1>Comment souhaitez-vous<br>passer votre demande ?</h1>
    <p>Choisissez une méthode selon votre besoin.</p>
  </div>

  <div class="gw-cards">

    <!-- Option 1 : Catalogue -->
    <a class="gw-card cat" href="/professionnel/catalogue">
      <span class="gw-card-badge hidden" id="catalogue-badge">0</span>
      <div class="gw-card-icon">&#128269;</div>
      <h2 class="gw-card-title">Commander depuis le catalogue</h2>
      <p class="gw-card-desc">
        Recherchez les produits, choisissez les quantités et constituez votre demande.
      </p>
      <div class="gw-card-foot">
        <span class="gw-card-cta" id="catalogue-cta">Parcourir le catalogue</span>
        <span class="gw-card-arrow">&#8594;</span>
      </div>
    </a>

    <div class="gw-or">ou</div>

    <!-- Option 2 : WhatsApp -->
    <a class="gw-card wa" target="_blank" rel="noopener"
       href="https://wa.me/22871039904?text=Bonjour%20Elokinab%20Health%2C%20je%20souhaite%20passer%20une%20commande.%20Voici%20ma%20liste%20%3A%0A%0A">
      <div class="gw-card-icon">&#128172;</div>
      <h2 class="gw-card-title">Commander via WhatsApp</h2>
      <p class="gw-card-desc">
        Envoyez votre liste, photo, PDF ou message libre directement à la pharmacie.
      </p>
      <div class="gw-card-foot">
        <span class="gw-card-cta">Ouvrir WhatsApp</span>
        <span class="gw-card-arrow">&#8594;</span>
      </div>
    </a>

  </div>

  <div class="gw-hint">
    <strong>&#128161; Conseil :</strong>
    utilisez le catalogue pour les produits que vous connaissez,
    WhatsApp pour les listes libres ou les produits non référencés.
  </div>

</main>

<!-- NAVBAR -->
<nav class="pro-navbar">
  <a href="/professionnel">
    <span class="ico">&#127968;</span>
    Accueil
  </a>
  <a href="/professionnel/catalogue">
    <span class="ico">&#128722;</span>
    Catalogue
  </a>
  <a href="/professionnel/demande" class="central active" id="nav-central" aria-label="Nouvelle demande">
    <span class="ico">+</span>
    <span class="lbl">Demande</span>
    <span class="nav-count hidden" id="nav-count">0</span>
  </a>
  <a href="/professionnel/commandes">
    <span class="ico">&#128230;</span>
    Commandes
  </a>
  <a href="/professionnel/etablissement">
    <span class="ico">&#127970;</span>
    Etabl.
  </a>
</nav>

<script src="/static/safe_locale.js"></script>
<script>
(function () {
  // Badge sur la card catalogue + badge navbar si draft en cours
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
            var cta = document.getElementById("catalogue-cta");
            if (cta) cta.textContent = "Continuer ma demande";
            var navCount = document.getElementById("nav-count");
            if (navCount) {
              navCount.textContent = n > 99 ? "99+" : String(n);
              navCount.classList.remove("hidden");
            }
          }
        });
    })
    .catch(function () {});
})();
</script>
</body>
</html>
'''

(STATIC / "professional_demande.html").write_text(DEM_HTML, encoding="utf-8")
print("[OK] professional_demande.html reecrit")

print()
print("=" * 60)
print("FIX GATEWAY APPLIQUE")
print("=" * 60)
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur /professionnel/demande")
print("  Pas besoin de redemarrer Uvicorn (fichiers statiques)")
print("=" * 60)