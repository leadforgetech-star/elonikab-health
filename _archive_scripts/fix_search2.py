from pathlib import Path

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

# ================================================================
# 1) main.py : recherche plus stricte et insensible a la casse
# ================================================================
py = BASE / "main.py"
src = py.read_text(encoding="utf-8")

old_like = 'like = "%%" + q.strip() + "%%"'
new_like = 'like = "%" + q.strip().lower() + "%"'
if old_like in src:
    src = src.replace(old_like, new_like)
    print("[OK] main.py -> like corrige")

old_sql = 'sql += " AND (name LIKE ? OR description LIKE ? OR presentation LIKE ?)"'
new_sql = (
    'sql += " AND (LOWER(name) LIKE ? OR LOWER(description) LIKE ?'
    ' OR LOWER(presentation) LIKE ?)"'
)
if old_sql in src:
    src = src.replace(old_sql, new_sql)
    print("[OK] main.py -> requete SQL normalisee")

# Tri : les produits qui COMMENCENT par la recherche d'abord
old_order = 'sql += " ORDER BY name COLLATE NOCASE"'
new_order = (
    'if q.strip():\n'
    '        sql += " ORDER BY CASE WHEN LOWER(name) LIKE ? THEN 0 ELSE 1 END, name COLLATE NOCASE"\n'
    '        params.append(q.strip().lower() + "%")\n'
    '    else:\n'
    '        sql += " ORDER BY name COLLATE NOCASE"'
)
if old_order in src:
    src = src.replace(old_order, new_order)
    print("[OK] main.py -> tri par pertinence ajoute")

py.write_text(src, encoding="utf-8")

# ================================================================
# 2) app.js : suggestions qui se rafraichissent correctement
# ================================================================
js_path = STATIC / "app.js"
js = js_path.read_text(encoding="utf-8")

# On repart d'un bloc propre pour attachSuggestions
import re

new_func = r'''function attachSuggestions(input, box) {
  var items = [];
  var activeIndex = -1;
  var timer = null;
  var requestId = 0;

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
    list.forEach(function (p) {
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
    if (q.length === 0) { close(); return; }

    if (timer) clearTimeout(timer);
    var myReq = ++requestId;

    timer = setTimeout(function () {
      apiGet("/products?q=" + encodeURIComponent(q)).then(function (list) {
        if (myReq !== requestId) return;
        if (input.value.trim() !== q) return;
        render(list.slice(0, 6));
      }).catch(function () {
        if (myReq !== requestId) return;
        close();
      });
    }, 120);
  });

  input.addEventListener("keydown", function (ev) {
    if (box.classList.contains("hidden") || items.length === 0) return;
    if (ev.key === "ArrowDown") {
      ev.preventDefault();
      activeIndex = (activeIndex + 1) % items.length;
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

  input.addEventListener("blur", function () { setTimeout(close, 150); });

  input.addEventListener("focus", function () {
    if (input.value.trim().length >= 1 && items.length > 0) {
      box.classList.remove("hidden");
    }
  });
}
'''

pattern = re.compile(r'function attachSuggestions\(input, box\) \{.*?\n\}\n', re.DOTALL)
if pattern.search(js):
    js = pattern.sub(new_func + "\n", js, count=1)
    js_path.write_text(js, encoding="utf-8")
    print("[OK] app.js -> attachSuggestions reecrit (annulation des requetes obsoletes)")
else:
    print("[!] attachSuggestions introuvable dans app.js")

print()
print("Termine.")
print("1) Redemarre le serveur : Ctrl+C puis  python main.py")
print("2) Dans le navigateur : Ctrl+Shift+R")