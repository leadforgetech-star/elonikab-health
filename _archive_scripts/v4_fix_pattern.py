"""
v4_fix_pattern.py
Corrige 'The string did not match the expected pattern' sur iOS Safari.
Cause : toLocaleString('fr-FR') / toLocaleDateString('fr-FR') qui throw.
Solution : try/catch + fallback manuel.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
CATJS = BASE / "static" / "professional_catalogue.js"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_fix_pattern_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(CATJS, backup / "professional_catalogue.js")
print("[OK] Backup ->", backup.name)

js = CATJS.read_text(encoding="utf-8")

# 1. Patch fmtPrice
old_price = '''function fmtPrice(v) {
    var n = Math.round(Number(v) || 0);
    return n.toLocaleString("fr-FR") + " F";
  }'''
new_price = '''function fmtPrice(v) {
    var n = Math.round(Number(v) || 0);
    try {
      return n.toLocaleString("fr-FR") + " F";
    } catch (e) {
      // Fallback manuel : separateur de milliers
      var s = String(n);
      var out = "";
      for (var i = 0; i < s.length; i++) {
        if (i > 0 && (s.length - i) % 3 === 0) out += " ";
        out += s[i];
      }
      return out + " F";
    }
  }'''

if old_price in js:
    js = js.replace(old_price, new_price, 1)
    print("[OK] fmtPrice -> try/catch + fallback")
elif "try {" in js and "fmtPrice" in js:
    print("[i] fmtPrice deja patche")
else:
    print("[!] fmtPrice introuvable, verifie le fichier")

# 2. Patch fmtDate
old_date = '''function fmtDate(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleDateString("fr-FR", {
      day: "2-digit", month: "short", year: "numeric"
    });
  }'''
new_date = '''function fmtDate(iso) {
    if (!iso) return "";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return String(iso);
      var months = ["janv.","fevr.","mars","avr.","mai","juin",
                    "juil.","aout","sept.","oct.","nov.","dec."];
      return d.getDate() + " " + months[d.getMonth()] + " " + d.getFullYear();
    } catch (e) {
      return String(iso);
    }
  }'''

if old_date in js:
    js = js.replace(old_date, new_date, 1)
    print("[OK] fmtDate -> try/catch + fallback manuel")
elif "months = [" in js:
    print("[i] fmtDate deja patche")
else:
    print("[!] fmtDate introuvable ou format different")

# 3. Patch escapeHtml avec try/catch
old_esc = '''function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }'''
new_esc = '''function escapeHtml(s) {
    try {
      return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
        return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
      });
    } catch (e) {
      return "";
    }
  }'''

if old_esc in js and "return String(s == null ? \"\" : s).replace" in js:
    js = js.replace(old_esc, new_esc, 1)
    print("[OK] escapeHtml -> try/catch")

# 4. Patch addToDraft : log complet + URL encode
old_add_start = 'function addToDraft(product, qty, btn) {'
if old_add_start in js:
    # Remplacement complet du contenu
    import re
    pattern = re.compile(
        r'function addToDraft\(product, qty, btn\) \{.*?\n  \}',
        re.DOTALL
    )
    new_add = '''function addToDraft(product, qty, btn) {
    if (btn) { btn.disabled = true; btn.textContent = "Ajout..."; }

    ensureDraft().then(function (draft) {
      if (!draft || !draft.reference) {
        throw new Error("Demande introuvable");
      }
      var desc = (product.name || "") + (product.presentation ? " — " + product.presentation : "");
      var ref = String(draft.reference);
      return api("POST", "/pro/requests/" + encodeURIComponent(ref) + "/items", {
        product_id: product.id,
        description: desc,
        requested_quantity: qty
      });
    }).then(function () {
      state.draftItemsCount += 1;
      updateNavCount();
      if (btn) {
        btn.classList.add("done");
        btn.innerHTML = "&#10003; Ajoute";
        setTimeout(function () {
          btn.classList.remove("done");
          btn.disabled = false;
          btn.innerHTML = "+ Ajouter a ma demande";
        }, 1400);
      }
      toast("Ajoute a votre demande");
    }).catch(function (e) {
      var msg = (e && e.message) ? e.message : "Erreur lors de l'ajout";
      console.error("addToDraft error:", e);
      toast(msg);
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = "+ Ajouter a ma demande";
      }
    });
  }'''
    if pattern.search(js):
        js = pattern.sub(new_add, js, count=1)
        print("[OK] addToDraft -> version defensive")
    else:
        print("[!] addToDraft introuvable")

CATJS.write_text(js, encoding="utf-8")

# Verification
check = CATJS.read_text(encoding="utf-8")
if "try {" in check and "months = [" in check:
    print()
    print("=" * 60)
    print("[OK] Correctifs appliques")
    print("=" * 60)
else:
    print()
    print("[!] Certains correctifs n'ont pas ete appliques")

print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur Edge (ou navigation privee sur iPhone)")
print("  Puis re-teste l'ajout d'un produit au catalogue")