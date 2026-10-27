"""
fix_redirect_after_proof.py
Apres upload de la preuve de paiement, redirige vers /suivi?ref=...
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
PAYJS = BASE / "static" / "payment.js"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_redirect_proof_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(PAYJS, backup / "payment.js")
print("[OK] Backup ->", backup.name)

js = PAYJS.read_text(encoding="utf-8")

# Remplacer le bloc de succes dans upload()
old = '''    }).then(function () {
      showMsg("Preuve envoyee. La pharmacie va verifier.", true);
      load();
      btn.disabled = false;
      btn.textContent = "Envoyer la preuve";
    }).catch(function (e) {'''

new = '''    }).then(function () {
      showMsg("Preuve envoyee. Redirection vers le suivi...", true);
      btn.textContent = "Redirection...";
      // Redirection auto apres 1,2 s vers la page de suivi
      setTimeout(function () {
        window.location.href = "/suivi?ref=" + encodeURIComponent(ref);
      }, 1200);
    }).catch(function (e) {'''

if old in js:
    js = js.replace(old, new, 1)
    PAYJS.write_text(js, encoding="utf-8")
    print("[OK] payment.js -> redirection apres preuve")
elif 'window.location.href = "/suivi?ref="' in js:
    print("[i] payment.js deja patche")
else:
    print("[!] pattern du bloc succes introuvable")
    # Afficher un extrait pour debug
    idx = js.find("Preuve envoyee")
    if idx > 0:
        print("Contexte trouve :")
        print(js[max(0,idx-400):idx+300])

print()
print("=" * 60)
print("REDIRECTION APRES PREUVE INSTALLEE")
print("=" * 60)
print()
print("Effet :")
print("  - Client envoie sa preuve de paiement")
print("  - Message 'Preuve envoyee. Redirection...' affiche")
print("  - Apres 1,2 seconde : redirection auto vers /suivi?ref=CMD-XXX")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur l'iPhone (ou navigation privee)")