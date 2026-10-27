"""
fix_progress_v3.py
- showProgress avec style inline total (impossible a cacher)
- Logs console pour diagnostiquer
- Test automatique au chargement
"""
from pathlib import Path
import datetime
import re
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
JS = STATIC / "payment.js"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_prog3_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(JS, backup / "payment.js")
print("[OK] Backup ->", backup.name)

js = JS.read_text(encoding="utf-8")

# ============================================================
# 1. Remplacer showProgress + hideProgress par versions inline
# ============================================================
old_pat = re.compile(
    r'  function showProgress\(percent, label\) \{.*?\n  \}\n\n  function hideProgress\(\) \{.*?\n  \}',
    re.DOTALL,
)

new_helpers = '''  function showProgress(percent, label) {
    console.log("[progress] showProgress appele :", percent, label);
    var box = document.getElementById("upload-progress");
    if (!box) {
      console.error("[progress] #upload-progress introuvable");
      return;
    }

    // Force le style inline : aucun CSS externe ne peut cacher cet element
    box.className = "pay-progress"; // supprime 'hidden' et toute autre classe
    box.style.cssText = [
      "position: fixed",
      "left: 0",
      "right: 0",
      "bottom: 0",
      "z-index: 99999",
      "background: #ffffff",
      "border-top: 3px solid #1a4a7f",
      "padding: 16px 18px calc(16px + env(safe-area-inset-bottom)) 18px",
      "box-shadow: 0 -6px 24px rgba(15,23,42,.15)",
      "display: block",
      "font-family: -apple-system,'Segoe UI',system-ui,sans-serif",
      "transition: transform .2s ease"
    ].join(";");

    // Force le parent de la page a ne pas cacher
    if (box.parentNode) {
      box.parentNode.style.overflow = "visible";
    }

    var fill = document.getElementById("upload-progress-fill");
    if (fill) {
      fill.style.cssText = [
        "height: 100%",
        "background: linear-gradient(90deg,#1a4a7f,#2a6ba8)",
        "border-radius: 999px",
        "transition: width .3s cubic-bezier(.4,0,.2,1)",
        "width: " + Math.max(0, Math.min(100, percent)) + "%"
      ].join(";");
    }

    var pct = document.getElementById("upload-progress-percent");
    if (pct) {
      pct.textContent = Math.round(percent) + "%";
      pct.style.cssText = [
        "font-size: 14px",
        "font-weight: 800",
        "color: #123258",
        "text-align: right",
        "margin-top: 8px",
        "font-family: Consolas,monospace"
      ].join(";");
    }

    var lbl = document.getElementById("upload-progress-label");
    if (lbl && label) {
      lbl.textContent = label;
      lbl.style.cssText = [
        "font-size: 13px",
        "font-weight: 700",
        "color: #0f172a",
        "margin: 0 0 10px 0"
      ].join(";");
    }

    // Debug : verifier que l'element est bien visible
    var display = window.getComputedStyle(box).display;
    var height = window.getComputedStyle(box).height;
    console.log("[progress] element visible : display=" + display + " height=" + height);
  }

  function hideProgress() {
    var box = document.getElementById("upload-progress");
    if (box) {
      box.style.cssText = "display: none !important";
      box.classList.add("hidden");
    }
  }'''

if old_pat.search(js):
    js = js.replace(old_pat.search(js).group(0), new_helpers, 1)
    print("[OK] payment.js -> showProgress inline force")
else:
    print("[!] showProgress introuvable")

# ============================================================
# 2. Ajouter un log en entree de send()
# ============================================================
old_send_start = '''  function send() {
    if (!state.file) { toast("Choisissez un fichier."); return; }'''
new_send_start = '''  function send() {
    console.log("[send] ENVOI DECLENCHE");
    console.log("[send] file present :", state.file ? state.file.name : "AUCUN");
    if (!state.file) { toast("Choisissez un fichier."); return; }'''
if old_send_start in js:
    js = js.replace(old_send_start, new_send_start, 1)
    print("[OK] payment.js -> log en entree de send")

# ============================================================
# 3. Ajouter un test automatique au chargement
# ============================================================
TEST_JS = '''

  // Test automatique : verifier que la barre existe au chargement
  setTimeout(function () {
    var box = document.getElementById("upload-progress");
    if (box) {
      console.log("[progress] TEST : barre detectee dans le DOM");
      console.log("[progress] TEST : classes =", box.className);
      console.log("[progress] TEST : display =", window.getComputedStyle(box).display);
    } else {
      console.error("[progress] TEST : barre NON TROUVEE");
    }
  }, 500);
'''

# Inserer avant "if (document.readyState"
anchor = 'if (document.readyState === "loading") {'
if anchor in js and "[progress] TEST" not in js:
    js = js.replace(anchor, TEST_JS + "\n\n" + anchor, 1)
    print("[OK] payment.js -> test auto ajoute")

JS.write_text(js, encoding="utf-8")

print()
print("=" * 60)
print("FIX V3 APPLIQUE")
print("=" * 60)
print()
print("Changements :")
print("  - showProgress force TOUT en style inline (impossible a cacher)")
print("  - Logs dans send() pour confirmer le clic")
print("  - Logs dans showProgress pour voir si appele")
print("  - Test auto au chargement (0.5s apres)")
print()
print("PROCHAINE ETAPE :")
print("  1. Ctrl+Shift+R dans le navigateur")
print("  2. F12 -> Console")
print("  3. Colle-moi TOUT ce qui contient [progress] ou [send]")
print("  4. Clique sur 'Envoyer la preuve'")
print("  5. Colle-moi les nouveaux logs")