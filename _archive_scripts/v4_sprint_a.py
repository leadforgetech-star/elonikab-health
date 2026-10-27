"""
v4_sprint_a.py - Sprint A : Fondations
- Routes /connexion et /inscription
- Header sticky renforce
- Footer complet sur index.html
- Favicon SVG integre
"""
from pathlib import Path
import datetime
import shutil
import re

BASE = Path(__file__).resolve().parent
MAIN = BASE / "main.py"
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_sprint_a_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAIN, backup / "main.py")
shutil.copy2(STATIC / "index.html", backup / "index.html")
shutil.copy2(STATIC / "mobile.css", backup / "mobile.css")
shutil.copy2(STATIC / "header.css", backup / "header.css")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. main.py : routes /connexion et /inscription
# ============================================================
src = MAIN.read_text(encoding="utf-8")

if '"/connexion"' not in src:
    routes = '''

# ============================================================
# V4 - Routes propres (Sprint A)
# ============================================================

@app.get("/connexion", include_in_schema=False)
def page_connexion():
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/inscription", include_in_schema=False)
def page_inscription():
    return FileResponse(STATIC_DIR / "register.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon_ico():
    return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")

'''
    anchor = "\ninit_db()\n"
    if anchor in src:
        src = src.replace(anchor, routes + anchor, 1)
        MAIN.write_text(src, encoding="utf-8")
        print("[OK] main.py -> routes /connexion, /inscription, /favicon.ico")
    else:
        print("[!] anchor init_db() introuvable")
else:
    print("[i] routes V4 deja presentes")

# ============================================================
# 2. Favicon SVG
# ============================================================
FAVICON = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0f9d76"/>
      <stop offset="1" stop-color="#37c79c"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="14" fill="url(#g)"/>
  <path d="M32 14 V50 M14 32 H50" stroke="#ffffff" stroke-width="6"
        stroke-linecap="round"/>
</svg>
'''
(STATIC / "favicon.svg").write_text(FAVICON, encoding="utf-8")
print("[OK] static/favicon.svg")

# ============================================================
# 3. Header sticky V4 - renforcement total
# ============================================================
HC = STATIC / "header.css"
hcss = HC.read_text(encoding="utf-8")

STICKY_V4 = '''

/* ============================================================
   HEADER STICKY V4 - Regle definitive
   ============================================================ */
html, body{
  overflow-x: clip !important;
  overflow-y: visible !important;
  position: static !important;
}
body > .topbar,
body > .eh-mini-bar,
body > header.topbar{
  position: -webkit-sticky !important;
  position: sticky !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  z-index: 99999 !important;
  background: #ffffff !important;
  box-shadow: 0 2px 12px rgba(15,38,32,.08) !important;
  isolation: isolate;
  will-change: transform;
  transform: translateZ(0);
}
/* Si le header est dans un conteneur, forcer son sticky aussi */
.topbar-parent-safe{
  overflow: visible !important;
  transform: none !important;
  contain: none !important;
}
'''

if "HEADER STICKY V4" not in hcss:
    hcss += STICKY_V4
    HC.write_text(hcss, encoding="utf-8")
    print("[OK] header.css -> sticky V4")
else:
    print("[i] header.css -> sticky V4 deja present")

# ============================================================
# 4. index.html : footer complet + favicon + corrections
# ============================================================
html = (STATIC / "index.html").read_text(encoding="utf-8")

# 4a. Favicon dans <head>
if 'rel="icon"' not in html:
    html = html.replace(
        "</head>",
        '<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">\n'
        '<link rel="apple-touch-icon" href="/static/favicon.svg">\n'
        "</head>",
        1,
    )
    print("[OK] index.html -> favicon")

# 4b. Footer complet (remplacer l'ancien si existe)
FOOTER = '''<footer class="eh-footer">
  <div class="container eh-footer-inner">
    <div class="eh-footer-col">
      <div class="eh-footer-brand">
        <span class="eh-footer-logo">+</span>
        <strong>Elokinab Health</strong>
      </div>
      <p class="muted small">
        Vos produits de sante, simplement.
        Plateforme digitale de commande et de livraison de produits pharmaceutiques au Togo.
      </p>
    </div>

    <div class="eh-footer-col">
      <h4>A propos</h4>
      <ul>
        <li><a href="/#comment-ca-marche">Comment ca marche</a></li>
        <li><a href="/#ordonnance">Envoyer une ordonnance</a></li>
        <li><a href="/#professionnels">Espace professionnel</a></li>
        <li><a href="/suivi">Suivre ma commande</a></li>
      </ul>
    </div>

    <div class="eh-footer-col">
      <h4>Aide</h4>
      <ul>
        <li><a href="/#faq">FAQ</a></li>
        <li><a href="/#contact">Contact</a></li>
        <li><a href="/#conditions">Conditions d'utilisation</a></li>
        <li><a href="/#confidentialite">Confidentialite</a></li>
      </ul>
    </div>

    <div class="eh-footer-col">
      <h4>Contact</h4>
      <ul>
        <li id="footer-phone">+228 90 00 00 00</li>
        <li id="footer-whatsapp">
          <a href="#" target="_blank" rel="noopener">WhatsApp</a>
        </li>
        <li id="footer-address">Lome, Togo</li>
      </ul>
    </div>
  </div>

  <div class="eh-footer-bottom">
    <div class="container">
      <span>&copy; 2026 Elokinab Health. Tous droits reserves.</span>
      <span class="muted small">Prototype en cours de deploiement.</span>
    </div>
  </div>
</footer>

<style>
  .eh-footer{
    background: #0f2620;
    color: #c9d9d3;
    margin-top: 60px;
    padding: 40px 0 0 0;
    font-size: 14px;
  }
  .eh-footer-inner{
    display: grid;
    grid-template-columns: 2fr 1fr 1fr 1fr;
    gap: 32px;
    padding-bottom: 32px;
  }
  .eh-footer-brand{
    display:flex;align-items:center;gap:10px;margin-bottom:12px;
  }
  .eh-footer-logo{
    width:36px;height:36px;border-radius:10px;
    background:linear-gradient(135deg,#0f9d76,#37c79c);color:#fff;
    display:flex;align-items:center;justify-content:center;
    font-size:20px;font-weight:800;
  }
  .eh-footer-brand strong{color:#fff;font-size:15px}
  .eh-footer-col h4{
    color:#fff;font-size:13px;font-weight:800;
    text-transform:uppercase;letter-spacing:.06em;
    margin:0 0 14px 0;
  }
  .eh-footer-col ul{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:8px}
  .eh-footer-col a{color:#c9d9d3;text-decoration:none;transition:.15s}
  .eh-footer-col a:hover{color:#37c79c}
  .eh-footer .muted.small{font-size:12px;color:#8fa89f;line-height:1.6}
  .eh-footer-bottom{
    border-top: 1px solid #1f3a33;
    padding: 16px 0;
    font-size: 12px;
    color: #8fa89f;
  }
  .eh-footer-bottom .container{
    display: flex;justify-content:space-between;align-items:center;
    gap:12px;flex-wrap:wrap;
  }
  @media (max-width: 720px){
    .eh-footer-inner{grid-template-columns:1fr 1fr;gap:24px}
    .eh-footer-inner > div:first-child{grid-column:1 / -1}
  }
  @media (max-width: 400px){
    .eh-footer-inner{grid-template-columns:1fr}
  }
</style>
'''

# Remplacer l'ancien footer s'il existe
if '<footer class="footer">' in html:
    # Ancien footer
    start = html.find('<footer class="footer">')
    end = html.find('</footer>', start) + len('</footer>')
    html = html[:start] + FOOTER + html[end:]
    print("[OK] index.html -> footer remplace")
elif 'class="eh-footer"' not in html:
    html = html.replace("</body>", FOOTER + "\n</body>", 1)
    print("[OK] index.html -> footer ajoute")
else:
    print("[i] index.html -> footer deja present")

# 4c. Remplacer les liens /static/login.html par /connexion dans le header
html = html.replace('href="/static/login.html"', 'href="/connexion"')
html = html.replace('href="/static/register.html"', 'href="/inscription"')
print("[OK] index.html -> liens /connexion et /inscription")

(STATIC / "index.html").write_text(html, encoding="utf-8")

# ============================================================
# 5. header.js : remplacer les liens par /connexion et /inscription
# ============================================================
HJ = STATIC / "header.js"
hjs = HJ.read_text(encoding="utf-8")

hjs = hjs.replace('login.href = "/static/login.html";', 'login.href = "/connexion";')
hjs = hjs.replace('reg.href = "/static/register.html";', 'reg.href = "/inscription";')
hjs = hjs.replace('window.location.href = "/static/login.html?next="', 'window.location.href = "/connexion?next="')

HJ.write_text(hjs, encoding="utf-8")
print("[OK] header.js -> liens /connexion et /inscription")

# ============================================================
# 6. auth.js : redirections vers les nouvelles routes
# ============================================================
AJ = STATIC / "auth.js"
ajs = AJ.read_text(encoding="utf-8")
ajs = ajs.replace('href="/static/login.html"', 'href="/connexion"')
ajs = ajs.replace('href="/static/register.html"', 'href="/inscription"')
AJ.write_text(ajs, encoding="utf-8")
print("[OK] auth.js -> liens mis a jour")

# ============================================================
# 7. Footer dynamique : charger le numero WhatsApp configure
# ============================================================
APPJS = STATIC / "app.js"
apjs = APPJS.read_text(encoding="utf-8")

FOOTER_JS = '''

// ===== Footer dynamique (telephone + WhatsApp) =====
(function () {
  function hydrateFooter() {
    fetch("/api/settings", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (s) {
        if (!s) return;
        var phone = s.pharmacy_phone || s.whatsapp_number || "";
        var wa = s.whatsapp_number || s.pharmacy_phone || "";
        var addr = s.pharmacy_address || "";
        var phoneEl = document.getElementById("footer-phone");
        if (phoneEl && phone) phoneEl.textContent = phone;
        var waEl = document.getElementById("footer-whatsapp");
        if (waEl && wa) {
          var num = String(wa).replace(/\\D/g, "");
          waEl.innerHTML = '<a href="https://wa.me/' + num + '" target="_blank" rel="noopener">WhatsApp : ' + wa + '</a>';
        }
        var addrEl = document.getElementById("footer-address");
        if (addrEl && addr) addrEl.textContent = addr;
      })
      .catch(function () {});
  }
  document.addEventListener("DOMContentLoaded", hydrateFooter);
})();
'''

if "hydrateFooter" not in apjs:
    apjs += FOOTER_JS
    APPJS.write_text(apjs, encoding="utf-8")
    print("[OK] app.js -> footer dynamique")

print()
print("=" * 60)
print("SPRINT A - FONDATIONS LIVRE")
print("=" * 60)
print()
print("Ce qui a change :")
print("  1. /connexion       -> page login propre")
print("  2. /inscription     -> page register propre")
print("  3. /favicon.ico     -> favicon SVG (plus de 404)")
print("  4. Header sticky V4 -> regle definitive")
print("  5. Footer complet   -> sur index.html")
print("  6. Liens mis a jour dans header.js et auth.js")
print("  7. Footer dynamique -> telephone + WhatsApp auto")
print()
print("PROCHAINE ETAPE :")
print("  taskkill /F /IM python.exe")
print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
print("  Puis Ctrl+Shift+R sur Edge/iPhone")
print()
print("TEST : ouvrir /connexion et /inscription")