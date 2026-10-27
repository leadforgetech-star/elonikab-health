from pathlib import Path
import sqlite3

BASE = Path(__file__).resolve().parent

# ---------------------------------------------------------------
# 1) app.js : affichage en FCFA (entiers, separateur de milliers)
# ---------------------------------------------------------------
js_path = BASE / "static" / "app.js"
js = js_path.read_text(encoding="utf-8")

old_money = '''function money(v) {
  var n = Number(v) || 0;
  return n.toFixed(2) + CURRENCY;
}'''
new_money = '''function money(v) {
  var n = Math.round(Number(v) || 0);
  return n.toLocaleString("fr-FR") + " FCFA";
}'''

if old_money in js:
    js = js.replace(old_money, new_money)
elif 'function money(v)' in js:
    # filet de securite : remplacement souple
    import re
    js = re.sub(r'function money\(v\)\s*\{[^}]*\}', new_money, js, count=1)

# On peut retirer la variable CURRENCY devenue inutile
js = js.replace('var CURRENCY = " EUR";\n', '')
js = js.replace('var CURRENCY = "EUR";\n', '')

js_path.write_text(js, encoding="utf-8")
print("[OK] app.js -> affichage FCFA")

# ---------------------------------------------------------------
# 2) main.py : prix de demonstration en FCFA (entiers)
# ---------------------------------------------------------------
py_path = BASE / "main.py"
src = py_path.read_text(encoding="utf-8")

# Nouveaux prix FCFA par nom de produit
prices = {
    "Doliprane 1000 mg": 1000,
    "Amoxicilline 500 mg": 2500,
    "Vitamine C 1000 mg": 2000,
    "Serum physiologique": 1500,
    "Ibuprofene 400 mg": 1500,
    "Pansements assortis": 2000,
    "Thermometre digital": 4500,
    "Gel hydroalcoolique": 2500,
}

# Remplace les tuples de demo dans init_db() en cherchant les anciens prix
old_new_pairs = [
    ('("Doliprane 1000 mg", "Boite de 8 comprimes", 2.50,',
     '("Doliprane 1000 mg", "Boite de 8 comprimes", 1000,'),
    ('("Amoxicilline 500 mg", "Boite de 12 gelules", 4.90,',
     '("Amoxicilline 500 mg", "Boite de 12 gelules", 2500,'),
    ('("Vitamine C 1000 mg", "Tube de 20 comprimes effervescents", 6.20,',
     '("Vitamine C 1000 mg", "Tube de 20 comprimes effervescents", 2000,'),
    ('("Serum physiologique", "20 dosettes de 5 ml", 3.10,',
     '("Serum physiologique", "20 dosettes de 5 ml", 1500,'),
    ('("Ibuprofene 400 mg", "Boite de 20 comprimes", 3.80,',
     '("Ibuprofene 400 mg", "Boite de 20 comprimes", 1500,'),
    ('("Pansements assortis", "Boite de 40 pansements", 4.50,',
     '("Pansements assortis", "Boite de 40 pansements", 2000,'),
    ('("Thermometre digital", "Thermometre electronique", 9.90,',
     '("Thermometre digital", "Thermometre electronique", 4500,'),
    ('("Gel hydroalcoolique", "Flacon pompe de 250 ml", 3.50,',
     '("Gel hydroalcoolique", "Flacon pompe de 250 ml", 2500,'),
]
changed = 0
for old, new in old_new_pairs:
    if old in src:
        src = src.replace(old, new)
        changed += 1

py_path.write_text(src, encoding="utf-8")
print("[OK] main.py -> %d/%d prix mis a jour" % (changed, len(old_new_pairs)))

# ---------------------------------------------------------------
# 3) database.db : mettre a jour les prix deja en base
# ---------------------------------------------------------------
db_path = BASE / "database.db"
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    for name, price in prices.items():
        cur.execute("UPDATE products SET price = ? WHERE name = ?", (price, name))
    conn.commit()
    rows = cur.execute("SELECT name, price FROM products ORDER BY name").fetchall()
    conn.close()
    print("[OK] database.db -> prix mis a jour :")
    for name, price in rows:
        print("      %-28s %8d FCFA" % (name, price))
else:
    print("[!] database.db absent (sera cree au prochain demarrage)")

print()
print("Termine. Redemarre le serveur puis fais Ctrl+Shift+R dans le navigateur.")