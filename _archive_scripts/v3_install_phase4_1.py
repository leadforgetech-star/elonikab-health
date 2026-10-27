"""
v3_install_phase4_1.py
Ajoute le bouton "Ajouter au panier" sur les cartes produit
+ lien vers la connexion et le panier dans le header.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
APPJS = BASE / "static" / "app.js"
INDEX = BASE / "static" / "index.html"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_v3_p41_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(APPJS, backup / "app.js")
shutil.copy2(INDEX, backup / "index.html")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. app.js - bouton "Ajouter au panier" dans productCard
# ============================================================
js = APPJS.read_text(encoding="utf-8")

old = """  var btn = el("button", "btn btn-primary btn-block", "Voir le produit");
  btn.addEventListener("click", function () { openProduct(p.id); });
  body.appendChild(btn);
  card.appendChild(body);
  return card;
}"""

new = """  var actions = el("div", "product-actions");

  var btn = el("button", "btn btn-ghost", "Voir le produit");
  btn.addEventListener("click", function () { openProduct(p.id); });
  actions.appendChild(btn);

  if (p.availability === "disponible") {
    var addBtn = el("button", "btn btn-primary", "Ajouter au panier");
    addBtn.addEventListener("click", function () {
      addToCart(p.id, addBtn);
    });
    actions.appendChild(addBtn);
  }

  body.appendChild(actions);
  card.appendChild(body);
  return card;
}

function addToCart(productId, btn) {
  if (btn) { btn.disabled = true; btn.textContent = "Ajout..."; }
  fetch(API + "/cart/items", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_id: productId, quantity: 1 })
  }).then(function (r) {
    return r.json().then(function (d) {
      if (r.status === 401) {
        // Non connecte : rediriger vers login
        window.location.href = "/static/login.html?next=/static/cart.html";
        return;
      }
      if (!r.ok) throw new Error(d.detail || "Erreur");
      if (btn) { btn.textContent = "\\u2713 Ajoute"; }
      updateCartBadge(d.item_count);
      setTimeout(function () {
        if (btn) { btn.disabled = false; btn.textContent = "Ajouter au panier"; }
      }, 1200);
    });
  }).catch(function (e) {
    alert(e.message);
    if (btn) { btn.disabled = false; btn.textContent = "Ajouter au panier"; }
  });
}

function updateCartBadge(count) {
  var b = document.getElementById("cart-badge");
  if (!b) return;
  if (count > 0) {
    b.textContent = count > 99 ? "99+" : String(count);
    b.classList.remove("hidden");
  } else {
    b.classList.add("hidden");
  }
}

function loadCartBadge() {
  fetch(API + "/cart").then(function (r) {
    if (r.status === 401) return null;
    if (!r.ok) return null;
    return r.json();
  }).then(function (d) {
    if (d) updateCartBadge(d.item_count || 0);
  }).catch(function () {});
}"""

if old in js and "addToCart" not in js:
    js = js.replace(old, new, 1)
    print("[OK] app.js -> productCard + addToCart + badge")
elif "addToCart" in js:
    print("[i] app.js deja patche")
else:
    print("[!] anchor productCard introuvable")

# Ajouter appel loadCartBadge() dans init()
anchor_init = 'loadCategories().then(function () { showView("home"); });'
if anchor_init in js and "loadCartBadge" not in js.split(anchor_init)[0][-500:]:
    js = js.replace(anchor_init,
        'loadCartBadge();\n  ' + anchor_init, 1)
    print("[OK] app.js -> loadCartBadge() branche dans init")

APPJS.write_text(js, encoding="utf-8")

# ============================================================
# 2. index.html - lien panier + login dans le header
# ============================================================
html = INDEX.read_text(encoding="utf-8")

old_nav = '''      <a href="#demande" data-nav="order">Ma demande</a>
      <a href="/suivi">Suivre ma commande</a>'''

new_nav = '''      <a href="#demande" data-nav="order">Ma demande</a>
      <a href="/suivi">Suivre ma commande</a>
      <a href="/static/cart.html" class="nav-cart">
        Panier <span id="cart-badge" class="cart-badge hidden">0</span>
      </a>
      <a href="/static/login.html" class="nav-login">Connexion</a>'''

if old_nav in html and "cart-badge" not in html:
    html = html.replace(old_nav, new_nav, 1)
    print("[OK] index.html -> liens Panier + Connexion")
elif "cart-badge" in html:
    print("[i] index.html deja patche")
else:
    print("[!] anchor nav introuvable")

# CSS inline pour le badge et boutons produit
extra_css = '''
<style>
  .product-actions{display:flex;gap:8px;margin-top:auto}
  .product-actions .btn{flex:1;padding:10px 8px;font-size:13px}
  .nav-cart{position:relative}
  .cart-badge{
    display:inline-block;background:#0f9d76;color:#fff;
    font-size:10px;font-weight:800;padding:2px 6px;border-radius:999px;
    margin-left:4px;vertical-align:middle;
  }
  .nav-login{color:#0f9d76!important;font-weight:700!important}
</style>
'''

if "product-actions" not in html:
    html = html.replace("</head>", extra_css + "</head>", 1)
    print("[OK] index.html -> styles inline ajoutes")

INDEX.write_text(html, encoding="utf-8")

print()
print("=" * 60)
print("PHASE 4.1 installee.")
print("=" * 60)
print()
print("Modifications :")
print("  - Bouton 'Ajouter au panier' sur chaque carte produit disponible")
print("  - Lien 'Panier' + badge compteur dans le header")
print("  - Lien 'Connexion' dans le header")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R dans le navigateur (pas besoin de redemarrer le serveur)")