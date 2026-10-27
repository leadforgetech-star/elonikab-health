"""
fix_mobile_v2.py
Corrige le debordement horizontal sur iPhone.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_mobile_v2_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(STATIC / "mobile.css", backup / "mobile.css")
print("[OK] Backup ->", backup.name)

# ============================================================
# Reecriture complete de mobile.css : approche stricte
# ============================================================
MOBILE_CSS = '''/* ============================================================
   Elokinab Health - Mobile strict (anti-debordement)
   ============================================================ */

/* --- Reset global : empeche tout debordement horizontal --- */
*, *::before, *::after { box-sizing: border-box; }
html, body {
  max-width: 100vw;
  overflow-x: hidden;
}
img, video, iframe, table { max-width: 100%; }

/* --- Auth card : NE DOIT JAMAIS depasser la largeur ecran --- */
.auth-body {
  padding: 12px !important;
  min-height: 100vh;
  align-items: flex-start !important;
}
.auth-card {
  width: 100% !important;
  max-width: 100% !important;
  padding: 20px 16px !important;
  margin: 0 auto !important;
  border-radius: 16px !important;
}
.auth-logo-mark {
  width: 38px !important; height: 38px !important; font-size: 20px !important;
}
.auth-logo-text strong { font-size: 15px !important; }
.auth-logo-text small { font-size: 10px !important; }
.auth-card h1 { font-size: 20px !important; margin-bottom: 6px !important; }
.auth-card p.sub { font-size: 13px !important; margin-bottom: 16px !important; }
.auth-field { margin-bottom: 12px !important; }
.auth-field label { font-size: 12px !important; }
.auth-field input,
.auth-field select,
.auth-field textarea {
  width: 100% !important;
  padding: 12px 12px !important;
  font-size: 16px !important; /* evite le zoom auto Safari */
  box-sizing: border-box !important;
}
.auth-btn {
  width: 100% !important;
  padding: 13px !important;
  font-size: 15px !important;
}

/* --- Header topbar : responsive --- */
.topbar-inner {
  display: flex !important;
  flex-wrap: wrap !important;
  height: auto !important;
  padding: 10px 14px !important;
  gap: 8px !important;
}
.brand {
  flex: 1 1 auto;
  min-width: 0;
}
.brand-text strong { font-size: 14px !important; }
.brand-text small { display: none; }
.brand-logo {
  width: 36px !important; height: 36px !important; font-size: 20px !important;
}
.topnav {
  flex: 0 0 auto;
  gap: 4px !important;
  flex-wrap: wrap;
}
.topnav a {
  padding: 7px 10px !important;
  font-size: 12px !important;
}

/* --- Container --- */
.container {
  padding: 0 12px !important;
  max-width: 100% !important;
}

/* --- EH header actions --- */
.eh-user-actions {
  width: 100%;
  justify-content: flex-end;
  margin-left: 0 !important;
  padding-top: 6px;
}
.eh-icon-btn {
  width: 34px !important; height: 34px !important; font-size: 15px !important;
}
.eh-user-trigger {
  max-width: 140px !important;
  font-size: 12px !important;
  padding: 7px 10px !important;
}
.eh-link-btn {
  padding: 8px 12px !important;
  font-size: 12px !important;
}
.eh-mini-bar {
  flex-wrap: wrap;
  padding: 10px 12px !important;
}

/* --- Hero --- */
.hero {
  grid-template-columns: 1fr !important;
  padding: 20px !important;
  gap: 16px !important;
}
.hero h1 { font-size: 24px !important; line-height: 1.15 !important; }
.hero p { font-size: 14px !important; }
.hero-card { padding: 16px !important; }
.hero-actions { gap: 8px !important; }
.hero-actions .btn { flex: 1; min-width: 120px; }

/* --- Search --- */
.searchbar {
  flex-direction: column !important;
  gap: 6px !important;
  padding: 6px !important;
}
.searchbar input { padding: 11px !important; font-size: 15px !important; }
.searchbar button { width: 100% !important; padding: 11px !important; }

/* --- Categories --- */
.category-grid {
  grid-template-columns: repeat(2, 1fr) !important;
  gap: 10px !important;
}
.category-card { padding: 12px !important; }
.category-card h3 { font-size: 13px !important; }

/* --- Produits --- */
.product-grid {
  grid-template-columns: repeat(2, 1fr) !important;
  gap: 10px !important;
}
.product-card { font-size: 13px; }
.product-body { padding: 10px !important; gap: 6px !important; }
.product-name { font-size: 13px !important; line-height: 1.2 !important; }
.product-card .muted.small { font-size: 11px !important; }
.price { font-size: 14px !important; }
.product-actions { flex-direction: column !important; gap: 6px !important; }
.product-actions .btn { padding: 9px 8px !important; font-size: 12px !important; }

/* --- Detail produit --- */
.product-detail {
  grid-template-columns: 1fr !important;
  padding: 16px !important;
  gap: 16px !important;
}
.detail-media { min-height: 200px !important; }

/* --- Cards generiques --- */
.card { padding: 16px !important; }
.page-head h1 { font-size: 22px !important; }
.section-title { font-size: 17px !important; }

/* --- Summary --- */
.summary {
  grid-template-columns: 1fr !important;
  gap: 6px 0 !important;
}
.summary dt { font-size: 12px !important; margin-top: 8px !important; }
.summary dd { font-size: 14px !important; }

/* --- Modal --- */
.modal-content {
  max-width: 100% !important;
  border-radius: 14px !important;
  margin: 8px !important;
}
.modal-head { padding: 12px 16px !important; }
.modal-head h2 { font-size: 15px !important; }

/* --- Panier --- */
.cart-item { padding: 10px !important; gap: 8px !important; }
.cart-thumb { width: 44px !important; height: 44px !important; font-size: 16px !important; }
.cart-name { font-size: 13px !important; }
.qty input { width: 36px !important; font-size: 13px !important; }

/* --- Dashboard pharmacien --- */
.stats {
  grid-template-columns: repeat(2, 1fr) !important;
  gap: 8px !important;
}
.stat-card { padding: 14px !important; }
.stat-value { font-size: 22px !important; }
.stat-label { font-size: 10px !important; }
.orders-grid { grid-template-columns: 1fr !important; }
.order-card { padding: 14px !important; }
.order-body { grid-template-columns: 1fr !important; gap: 2px 0 !important; }
.admin-title { font-size: 16px !important; }
.toolbar-row { flex-direction: column !important; align-items: stretch !important; }

/* --- Checkout --- */
.checkout-modes { grid-template-columns: 1fr 1fr !important; gap: 8px !important; }
.mode-btn { padding: 12px 8px !important; font-size: 13px !important; }
.checkout-card { padding: 14px !important; }
.checkout-actions { flex-direction: column !important; }
.checkout-actions .auth-btn { width: 100% !important; }

/* --- Table / listes --- */
.driver-admin-row, .payment-admin-row, .presc-admin-row {
  flex-direction: column !important;
  align-items: stretch !important;
  gap: 8px !important;
}
.driver-admin-row .btn, .payment-admin-row .btn, .presc-admin-row .btn {
  width: 100% !important;
}

/* --- Petits ecrans < 380px --- */
@media (max-width: 380px) {
  .product-grid { grid-template-columns: 1fr !important; }
  .category-grid { grid-template-columns: 1fr !important; }
  .hero h1 { font-size: 20px !important; }
  .auth-card { padding: 16px 12px !important; }
}
'''
(STATIC / "mobile.css").write_text(MOBILE_CSS, encoding="utf-8")
print("[OK] mobile.css reecrit")

# ============================================================
# Forcer la balise viewport sur toutes les pages HTML
# ============================================================
PAGES = ["index.html", "cart.html", "payment.html", "professional.html",
         "driver.html", "suivi.html", "pharmacien.html",
         "login.html", "register.html", "notifications.html"]

GOOD_VIEWPORT = '<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">'

fixed = 0
for page in PAGES:
    p = STATIC / page
    if not p.exists():
        continue
    c = p.read_text(encoding="utf-8")
    changed = False

    # Remplacer n'importe quelle balise viewport par la bonne
    import re
    new_c = re.sub(
        r'<meta\s+name="viewport"[^>]*>',
        GOOD_VIEWPORT,
        c,
        count=1,
    )
    if new_c != c:
        c = new_c
        changed = True

    # S'assurer que mobile.css est en DERNIER (priorite maximale)
    if 'mobile.css' in c:
        # supprimer l'ancien <link> puis le remettre en dernier
        c = re.sub(r'<link[^>]*mobile\.css[^>]*>\s*', '', c)
        if "</head>" in c:
            c = c.replace("</head>", '<link rel="stylesheet" href="/static/mobile.css">\n</head>', 1)
            changed = True
    else:
        if "</head>" in c:
            c = c.replace("</head>", '<link rel="stylesheet" href="/static/mobile.css">\n</head>', 1)
            changed = True

    if changed:
        p.write_text(c, encoding="utf-8")
        fixed += 1
        print("[OK] " + page)
print("[OK] " + str(fixed) + " pages corrigees")

# ============================================================
# Corriger auth.css : padding global
# ============================================================
AUTH = STATIC / "auth.css"
css = AUTH.read_text(encoding="utf-8")
if "/* MOBILE OVERRIDE */" not in css:
    css += '''
/* MOBILE OVERRIDE (priorite max) */
.auth-body{
  padding:12px !important;
  display:flex !important;
  align-items:flex-start !important;
  justify-content:center !important;
}
.auth-card{
  width:100% !important;
  max-width:100% !important;
  padding:22px 18px !important;
}
.auth-field input,
.auth-field select{
  font-size:16px !important;
}
'''
    AUTH.write_text(css, encoding="utf-8")
    print("[OK] auth.css -> override mobile")

print()
print("=" * 60)
print("FIX MOBILE v2 APPLIQUE")
print("=" * 60)
print()
print("Corrections :")
print("  - mobile.css reecrit (force max-width 100vw, padding reduit)")
print("  - viewport force sur toutes les pages HTML")
print("  - mobile.css en DERNIER dans <head> (priorite max)")
print("  - auth.css override mobile ajoute")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur l'iPhone (Safari : tirer vers le bas)")