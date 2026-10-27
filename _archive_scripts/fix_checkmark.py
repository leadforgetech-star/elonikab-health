from pathlib import Path

p = Path("static/payment.js")
c = p.read_text(encoding="utf-8")

# Remplacer les entites HTML par des echappements Unicode
replacements = [
    ("&#10003; Envoyee !", "\\u2713 Envoyee !"),
    ("&#128172; Envoyer la preuve", "\\uD83D\\uDCAC Envoyer la preuve"),
    ("&#128196;", "\\uD83D\\uDCC4"),
]

count = 0
for old, new in replacements:
    if old in c:
        n = c.count(old)
        c = c.replace(old, new)
        count += n
        print(f"[OK] {n} remplacement(s) : {old[:30]}...")

if count == 0:
    print("[i] Aucun remplacement necessaire")

p.write_text(c, encoding="utf-8")
print(f"[OK] {count} remplacement(s) total")

# Verifier le resultat
check = p.read_text(encoding="utf-8")
if "\\u2713 Envoyee" in check:
    print("[OK] Le checkmark est maintenant en Unicode")
else:
    print("[!] Le checkmark n'a pas ete trouve")