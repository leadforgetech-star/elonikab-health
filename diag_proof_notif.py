# -*- coding: utf-8 -*-
import os, re
ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
P = os.path.join(ROOT, "v3_modules", "payments.py")
src = open(P, "r", encoding="utf-8").read()

print("=" * 78)
print("Occurrences de push_notification dans payments.py")
print("=" * 78)
for i, line in enumerate(src.split("\n"), 1):
    if "push_notification" in line:
        print(f"  L{i}: {line.strip()}")

print("\n" + "=" * 78)
print("Routes dans payments.py")
print("=" * 78)
for m in re.finditer(r'@app\.(get|post|patch|delete)\("([^"]+)"', src):
    print(f"  {m.group(1).upper():<8} {m.group(2)}")

print("\n" + "=" * 78)
print("Fonction 'proof' ou 'submit' - contexte")
print("=" * 78)
lines = src.split("\n")
for i, line in enumerate(lines, 1):
    if "def " in line and ("proof" in line.lower() or "submit" in line.lower()):
        print(f"\n>>> L{i}: {line.strip()}")
        for j in range(i, min(len(lines), i+40)):
            print(f"  {j+1:4}  {lines[j].rstrip()}")
        print("---")