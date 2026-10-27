from pathlib import Path

BASE = Path(__file__).resolve().parent
py = BASE / "main.py"
src = py.read_text(encoding="utf-8")

new_func = '''@app.get("/api/products")
def list_products(q: str = "", category: str = ""):
    conn = get_db()
    sql = "SELECT * FROM products WHERE 1=1"
    params = []
    q_clean = q.strip().lower()
    if q_clean:
        # Recherche sur le NOM uniquement (pas la description)
        sql += " AND LOWER(name) LIKE ?"
        params.append("%" + q_clean + "%")
    if category.strip():
        sql += " AND category = ?"
        params.append(category.strip())
    if q_clean:
        # Les noms qui COMMENCENT par la recherche arrivent en premier
        sql += " ORDER BY CASE WHEN LOWER(name) LIKE ? THEN 0 ELSE 1 END, name COLLATE NOCASE"
        params.append(q_clean + "%")
    else:
        sql += " ORDER BY name COLLATE NOCASE"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]
'''

start_marker = '@app.get("/api/products")'
end_marker = '@app.get("/api/categories")'

if start_marker in src and end_marker in src:
    i = src.index(start_marker)
    j = src.index(end_marker)
    src = src[:i] + new_func + "\n\n" + src[j:]
    py.write_text(src, encoding="utf-8")
    print("[OK] main.py -> list_products remplace")
    print("[OK] Recherche sur le nom uniquement + tri par pertinence")
else:
    print("[!] markers introuvables dans main.py")
    print("    start_marker present :", start_marker in src)
    print("    end_marker present   :", end_marker in src)

print()
print("Termine.")
print("1) Redemarre le serveur : Ctrl+C puis python main.py")
print("2) Navigateur : Ctrl+Shift+R")