# -*- coding: utf-8 -*-
# inspect_routes_and_sse.py
# Dump le code exact des routes + le module notifications_stream
import os, re

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
MAIN = os.path.join(ROOT, "main.py")
STREAM = os.path.join(ROOT, "v3_modules", "notifications_stream.py")
NOTIF = os.path.join(ROOT, "v3_modules", "notifications.py")
CART = os.path.join(ROOT, "v3_modules", "cart.py")

def dump_route(src, marker_re):
    lines = src.split("\n")
    s = None
    for i, l in enumerate(lines):
        if re.search(marker_re, l):
            s = i; break
    if s is None:
        print(f"  [!!] route introuvable : {marker_re}")
        return
    # Fin : prochaine ligne @app. ou fin
    e = len(lines)
    for j in range(s+1, len(lines)):
        if re.match(r'^@(app|router)\.', lines[j]) or lines[j].startswith("if __name__"):
            e = j; break
    print(f"\n{'=' * 70}")
    print(f"ROUTE  ({e-s} lignes)")
    print(f"{'=' * 70}")
    for k in range(s, min(e, s+120)):
        print(f"  {k+1:4}  {lines[k].rstrip()}")

print("=" * 70)
print("INSPECTION DES ROUTES main.py")
print("=" * 70)

main = open(MAIN, "r", encoding="utf-8").read()
dump_route(main, r'@app\.patch\("/api/orders/\{reference\}/status"')
dump_route(main, r'@app\.post\("/api/orders"\)')

# ============================================================
print("\n\n" + "=" * 70)
print("MODULE notifications_stream.py")
print("=" * 70)
if os.path.exists(STREAM):
    src = open(STREAM, "r", encoding="utf-8").read()
    for i, l in enumerate(src.split("\n"), 1):
        print(f"  {i:4}  {l.rstrip()}")
else:
    print("  [!!] ABSENT")

# ============================================================
print("\n\n" + "=" * 70)
print("MODULE notifications.py (partie push_notification + broadcast)")
print("=" * 70)
if os.path.exists(NOTIF):
    src = open(NOTIF, "r", encoding="utf-8").read()
    for i, l in enumerate(src.split("\n"), 1):
        print(f"  {i:4}  {l.rstrip()}")
else:
    print("  [!!] ABSENT")

# ============================================================
print("\n\n" + "=" * 70)
print("cart.py (autour de push_notification injecte)")
print("=" * 70)
if os.path.exists(CART):
    src = open(CART, "r", encoding="utf-8").read()
    lines = src.split("\n")
    for i, l in enumerate(lines, 1):
        if "push_notification" in l:
            s = max(0, i - 15)
            e = min(len(lines), i + 15)
            for k in range(s, e):
                print(f"  {k+1:4}  {lines[k].rstrip()}")
            print("  ---")