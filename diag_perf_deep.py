# -*- coding: utf-8 -*-
"""Diagnostic profond : d'ou vient la lenteur ?"""
import urllib.request, time, os, sqlite3, subprocess, json

LOCAL = "http://127.0.0.1:8000"
DB = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie\database.db"

def timeit(url, timeout=60):
    t0 = time.time()
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        data = r.read()
        return (time.time() - t0) * 1000, r.status, len(data)
    except Exception as e:
        return (time.time() - t0) * 1000, str(e), 0

print("=" * 70)
print("DIAGNOSTIC PROFOND PERFORMANCE")
print("=" * 70)

# --- 1. Test direct DB SQLite ---
print("\n[1] Test DIRECT SQLite (sans passer par HTTP)")
print("-" * 70)
t0 = time.time()
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT COUNT(*) AS n FROM products").fetchone()
count = row["n"]
rows = conn.execute("SELECT * FROM products").fetchall()
conn.close()
sqlite_ms = (time.time() - t0) * 1000
print(f"  SELECT products ({count} lignes) : {sqlite_ms:.0f}ms")
if sqlite_ms < 100:
    print("  [OK] SQLite rapide -> le probleme vient d'AILLEURS (pas DB)")
else:
    print("  [!!] SQLite LENT -> probleme DB")

# --- 2. Test HTTP simple ---
print("\n[2] Test HTTP /api/products (3 fois)")
print("-" * 70)
times = []
for i in range(3):
    ms, st, sz = timeit(LOCAL + "/api/products")
    times.append(ms)
    print(f"  Test {i+1} : {ms:.0f}ms (status={st}, size={sz} bytes)")

avg = sum(times) / len(times)
print(f"\n  Moyenne : {avg:.0f}ms")

# --- 3. Test HTTP tres simple (favicon) ---
print("\n[3] Test HTTP /favicon.ico (endpoint le plus simple)")
print("-" * 70)
ms, st, sz = timeit(LOCAL + "/favicon.ico")
print(f"  {ms:.0f}ms (status={st}, size={sz} bytes)")

# --- 4. Test HTTP / (page racine) ---
print("\n[4] Test HTTP / (page accueil)")
ms, st, sz = timeit(LOCAL + "/")
print(f"  {ms:.0f}ms (status={st}, size={sz} bytes)")

# --- 5. Processus python en cours ---
print("\n[5] Processus python.exe en cours")
print("-" * 70)
try:
    out = subprocess.check_output(
        ["tasklist", "/FI", "IMAGENAME eq python.exe"],
        stderr=subprocess.DEVNULL
    ).decode("cp850", errors="ignore")
    for line in out.split("\n"):
        if "python" in line.lower():
            print("  " + line.strip())
except Exception as e:
    print("  [!!] " + str(e))

# --- 6. Taille DB ---
print("\n[6] Informations DB")
print("-" * 70)
db_size = os.path.getsize(DB)
print(f"  database.db : {db_size / 1024 / 1024:.2f} MB")

# --- 7. Nombre de middlewares dans main.py ---
print("\n[7] Middlewares declares dans main.py")
print("-" * 70)
main_path = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie\main.py"
if os.path.isfile(main_path):
    src = open(main_path, "r", encoding="utf-8").read()
    import re
    for m in re.finditer(r'app\.add_middleware\((\w+)', src):
        print(f"  - {m.group(1)}")
    for m in re.finditer(r'class (\w+Middleware)', src):
        print(f"  class {m.group(1)}")
else:
    print("  [!!] main.py introuvable")

print("\n" + "=" * 70)
print("INTERPRETATION")
print("=" * 70)
print("""
  Si SQLite < 100ms MAIS HTTP > 5000ms -> middleware ou Uvicorn bloque
  Si HTTP /favicon.ico > 5000ms        -> Uvicorn est en PLS (trop de middlewares ?)
  Si plusieurs python.exe             -> Uvicorn tourne en multiple process
""")