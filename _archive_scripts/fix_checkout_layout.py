"""
fix_checkout_layout.py
Ameliore la mise en page du formulaire de commande (checkout) sur mobile.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
CART = BASE / "static" / "cart.html"
MOBILE = BASE / "static" / "mobile.css"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_checkout_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(CART, backup / "cart.html")
shutil.copy2(MOBILE, backup / "mobile.css")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. CSS inline dans cart.html (priorite maximale)
# ============================================================
html = CART.read_text(encoding="utf-8")

STYLE_BLOCK = '''<style>
  /* Checkout : styles force */
  .checkout-card{
    background:#fff;border:1px solid #ddece6;border-radius:16px;
    padding:18px 16px !important;margin-top:14px;
  }
  .checkout-card h2{
    font-size:17px !important;margin:0 0 4px !important;
  }
  .checkout-card > p{
    font-size:13px !important;margin:0 0 16px !important;
    color:#6c8a80;
  }
  .checkout-modes{
    display:grid !important;
    grid-template-columns:1fr 1fr !important;
    gap:12px !important;
    margin:6px 0 18px !important;
  }
  .mode-btn{
    padding:16px 8px !important;
    border:2px solid #ddece6 !important;
    border-radius:14px !important;
    background:#fff !important;
    font-family:inherit !important;
    font-size:14px !important;
    font-weight:700 !important;
    color:#0f2620 !important;
    cursor:pointer !important;
    transition:.15s !important;
    text-align:center !important;
    width:100% !important;
  }
  .mode-btn.active{
    border-color:#0f9d76 !important;
    background:#e8f7f1 !important;
    color:#0a7a5a !important;
  }
  .checkout-field{
    display:flex !important;
    flex-direction:column !important;
    gap:6px !important;
    margin:0 0 14px 0 !important;
  }
  .checkout-field label{
    font-size:13px !important;
    font-weight:700 !important;
    color:#0f2620 !important;
    display:block !important;
  }
  .checkout-field input,
  .checkout-field textarea{
    width:100% !important;
    padding:13px 14px !important;
    border:1px solid #ddece6 !important;
    border-radius:11px !important;
    font-size:16px !important; /* evite zoom Safari */
    font-family:inherit !important;
    background:#fff !important;
    color:#0f2620 !important;
    outline:none !important;
    box-sizing:border-box !important;
  }
  .checkout-field input:focus,
  .checkout-field textarea:focus{
    border-color:#0f9d76 !important;
  }
  #co-delivery-fields.hidden{display:none !important}
  .checkout-total{
    display:flex !important;
    justify-content:space-between !important;
    align-items:center !important;
    background:#e8f7f1 !important;
    border:1px solid #c7e9dc !important;
    border-radius:12px !important;
    padding:14px 16px !important;
    margin:16px 0 14px !important;
    font-weight:800 !important;
    color:#0a7a5a !important;
    font-size:16px !important;
  }
  .checkout-total span:last-child{
    font-size:18px !important;
  }
  .checkout-actions{
    display:flex !important;
    flex-direction:column !important;
    gap:10px !important;
    margin-top:14px !important;
  }
  .checkout-actions .auth-btn{
    width:100% !important;
    padding:14px !important;
    font-size:15px !important;
  }
  #co-gps{background:#6c8a80 !important}
  #co-gps-status{
    font-size:12px !important;
    color:#6c8a80 !important;
    margin-top:4px !important;
  }
</style>
'''

if "/* Checkout : styles force */" not in html:
    # Inserer juste avant </head>
    if "</head>" in html:
        html = html.replace("</head>", STYLE_BLOCK + "</head>", 1)
        CART.write_text(html, encoding="utf-8")
        print("[OK] cart.html -> styles force")
    else:
        print("[!] </head> introuvable")
else:
    print("[i] cart.html deja patche")

# ============================================================
# 2. Renforcer aussi dans mobile.css
# ============================================================
css = MOBILE.read_text(encoding="utf-8")
if "/* Checkout STRICT */" not in css:
    css += '''

/* Checkout STRICT (force tout) */
.checkout-card { padding: 18px 16px !important; }
.checkout-modes { gap: 12px !important; margin-bottom: 18px !important; }
.mode-btn { padding: 16px 8px !important; font-size: 14px !important; }
.checkout-field {
  display: flex !important;
  flex-direction: column !important;
  gap: 6px !important;
  margin-bottom: 14px !important;
}
.checkout-field label { display: block !important; font-size: 13px !important; }
.checkout-field input,
.checkout-field textarea {
  width: 100% !important;
  font-size: 16px !important;
  box-sizing: border-box !important;
}
.checkout-total {
  display: flex !important;
  justify-content: space-between !important;
  padding: 14px 16px !important;
  font-size: 16px !important;
}
.checkout-actions {
  flex-direction: column !important;
  gap: 10px !important;
}
.checkout-actions .auth-btn { width: 100% !important; padding: 14px !important; }
'''
    MOBILE.write_text(css, encoding="utf-8")
    print("[OK] mobile.css -> checkout strict")

print()
print("=" * 60)
print("FIX CHECKOUT APPLIQUE")
print("=" * 60)
print()
print("Effet attendu :")
print("  - Retrait / Livraison : 2 gros boutons espaces")
print("  - Nom complet : label au-dessus du champ")
print("  - Telephone : idem")
print("  - Total : montant a droite, espace net")
print("  - Boutons Annuler / Confirmer empiles (plus lisibles)")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur l'iPhone")
print("  ou navigation privee pour eviter le cache")