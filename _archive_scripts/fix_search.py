from pathlib import Path

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

# ================================================================
# 1) index.html : ajouter les conteneurs de suggestions
# ================================================================
html_path = STATIC / "index.html"
html = html_path.read_text(encoding="utf-8")

old_home = '<input type="search" id="home-search-input" placeholder="Rechercher un produit (ex : doliprane, vitamine...)" autocomplete="off">'
new_home = (
    '<div class="search-field">'
    '<input type="search" id="home-search-input" placeholder="Rechercher un produit (ex : doliprane, vitamine...)" autocomplete="off">'
    '<div class="suggestions hidden" id="home-suggestions"></div>'
    '</div>'
)
if old_home in html:
    html = html.replace(old_home, new_home)
    print("[OK] index.html -> home-suggestions ajoute")
else:
    print("[!] home-search-input introuvable")

old_cat = '<input type="search" id="catalog-search" placeholder="Rechercher un produit..." autocomplete="off">'
new_cat = (
    '<div class="search-field">'
    '<input type="search" id="catalog-search" placeholder="Rechercher un produit..." autocomplete="off">'
    '<div class="suggestions hidden" id="catalog-suggestions"></div>'
    '</div>'
)
if old_cat in html:
    html = html.replace(old_cat, new_cat)
    print("[OK] index.html -> catalog-suggestions ajoute")
else:
    print("[!] catalog-search introuvable")

html_path.write_text(html, encoding="utf-8")

# ================================================================
# 2) style.css : style du dropdown de suggestions
# ================================================================
css_path = STATIC / "style.css"
css = css_path.read_text(encoding="utf-8")

css_add = """
/* --- Suggestions de recherche --- */
.search-field{position:relative;width:100%}
.suggestions{
  position:absolute;top:calc(100% + 6px);left:0;right:0;
  background:#fff;border:1px solid var(--line);border-radius:12px;
  box-shadow:var(--shadow);z-index:60;
  max-height:340px;overflow-y:auto;
}
.suggestions .sugg-item{
  display:flex;align-items:center;gap:12px;
  padding:10px 14px;cursor:pointer;
  border-bottom:1px solid var(--line);
}
.suggestions .sugg-item:last-child{border-bottom:0}
.suggestions .sugg-item:hover,
.suggestions .sugg-item.active{background:var(--green-soft)}
.suggestions .sugg-thumb{
  width:38px;height:38px;border-radius:9px;flex-shrink:0;
  background:linear-gradient(135deg,#eaf7f2,#d6efe6);
  display:flex;align-items:center;justify-content:center;
  font-weight:800;color:var(--green);font-size:13px;overflow:hidden;
}
.suggestions .sugg-thumb img{width:100%;height:100%;object-fit:cover}
.suggestions .sugg-info{flex:1;min-width:0}
.suggestions .sugg-name{
  font-weight:700;font-size:14px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.suggestions .sugg-meta{
  font-size:12px;color:var(--muted);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.suggestions .sugg-price{
  font-weight:800;color:var(--green-dark);font-size:13px;white-space:nowrap;
}
.suggestions .sugg-empty{
  padding:14px;color:var(--muted);font-size:14px;text-align:center;
}
"""

if "Suggestions de recherche" not in css:
    css = css + "\n" + css_add
    css_path.write_text(css, encoding="utf-8")
    print("[OK] style.css -> styles suggestions ajoutes")
else:
    print("[i] style.css deja patche")

# ================================================================
# 3) app.js : logique des suggestions
# ================================================================
js_path = STATIC / "app.js"
js = js_path.read_text(encoding="utf-8")

func = '''function attachSuggestions(input, box) {
  var items = [];
  var activeIndex = -1;
  var lastQuery = "__init__";
  var timer = null;

  function close() {
    box.classList.add("hidden");
    box.innerHTML = "";
    activeIndex = -1;
    items = [];
  }

  function highlight(idx) {
    var nodes = box.querySelectorAll(".sugg-item");
    Array.prototype.forEach.call(nodes, function (n, i) {
      if (i === idx) n.classList.add("active");
      else n.classList.remove("active");
    });
  }

  function choose(p) {
    close();
    input.value = p.name;
    lastQuery = p.name;
    openProduct(p.id);
  }

  function render(list) {
    box.innerHTML = "";
    items = list;
    activeIndex = -1;
    if (list.length === 0) {
      box.appendChild(el("div", "sugg-empty", "Aucun produit trouve"));
      box.classList.remove("hidden");
      return;
    }
    list.forEach(function (p, i) {
      var item = el("div", "sugg-item");
      var thumb = el("div", "sugg-thumb");
      if (p.image_url) {
        var img = document.createElement("img");
        img.src = p.image_url;
        img.alt = p.name;
        thumb.appendChild(img);
      } else {
        thumb.textContent = initials(p.name);
      }
      var info = el("div", "sugg-info");
      info.appendChild(el("div", "sugg-name", p.name));
      info.appendChild(el("div", "sugg-meta", p.category + " - " + p.presentation));
      var price = el("div", "sugg-price", money(p.price));
      item.appendChild(thumb);
      item.appendChild(info);
      item.appendChild(price);
      item.addEventListener("mousedown", function (ev) {
        ev.preventDefault();
        choose(p);
      });
      box.appendChild(item);
    });
    box.classList.remove("hidden");
  }

  input.addEventListener("input", function () {
    var q = input.value.trim();
    if (q === lastQuery) return;
    lastQuery = q;
    if (q.length < 1) { close(); return; }
    if (timer) clearTimeout(timer);
    timer = setTimeout(function () {
      apiGet("/products?q=" + encodeURIComponent(q)).then(function (list) {
        if (input.value.trim() !== q) return;
        render(list.slice(0, 6));
      }).catch(function () { close(); });
    }, 120);
  });

  input.addEventListener("keydown", function (ev) {
    if (box.classList.contains("hidden") || items.length === 0) return;
    if (ev.key === "ArrowDown") {
      ev.preventDefault();
      activeIndex = (activeIndex + 1) %% items.length;
      highlight(activeIndex);
    } else if (ev.key === "ArrowUp") {
      ev.preventDefault();
      activeIndex = activeIndex <= 0 ? items.length - 1 : activeIndex - 1;
      highlight(activeIndex);
    } else if (ev.key === "Enter") {
      if (activeIndex >= 0 && items[activeIndex]) {
        ev.preventDefault();
        choose(items[activeIndex]);
      }
    } else if (ev.key === "Escape") {
      close();
    }
  });

  input.addEventListener("blur", function () {
    setTimeout(close, 150);
  });

  input.addEventListener("focus", function () {
    if (input.value.trim().length >= 1 && items.length > 0) {
      box.classList.remove("hidden");
    }
  });
}

'''

marker = "function init() {"
if marker in js and "function attachSuggestions" not in js:
    js = js.replace(marker, func + marker, 1)
    print("[OK] app.js -> fonction attachSuggestions ajoutee")
else:
    print("[i] app.js -> fonction deja presente ou marker introuvable")

anchor = '  $("#order-form").addEventListener("submit", submitOrder);'
insert = (
    '  $("#order-form").addEventListener("submit", submitOrder);\n'
    '  attachSuggestions($("#home-search-input"), $("#home-suggestions"));\n'
    '  attachSuggestions($("#catalog-search"), $("#catalog-suggestions"));'
)
if anchor in js and "attachSuggestions($(" not in js:
    js = js.replace(anchor, insert, 1)
    print("[OK] app.js -> init() branche les suggestions")
else:
    print("[i] app.js -> init() deja branche ou anchor introuvable")

js_path.write_text(js, encoding="utf-8")

print()
print("Termine. Redemarre le serveur puis Ctrl+Shift+R dans le navigateur.")