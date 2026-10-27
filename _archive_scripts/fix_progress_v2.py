"""
fix_progress_v2.py
- Barre de progression integree directement dans payment.html
- Position fixe en bas (reste visible pendant l'upload)
- JS plus simple
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
HTML = STATIC / "payment.html"
JS = STATIC / "payment.js"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_prog2_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(HTML, backup / "payment.html")
shutil.copy2(JS, backup / "payment.js")
print("[OK] Backup ->", backup.name)

# ============================================================
# 1. HTML : ajouter la barre de progression fixe
# ============================================================
html = HTML.read_text(encoding="utf-8")

if 'id="upload-progress"' not in html:
    PROGRESS_BLOCK = '''
<div id="upload-progress" class="pay-progress hidden">
  <div class="pay-progress-inner">
    <div class="pay-progress-label" id="upload-progress-label">Preparation...</div>
    <div class="pay-progress-track">
      <div class="pay-progress-fill" id="upload-progress-fill" style="width:0%"></div>
    </div>
    <div class="pay-progress-percent" id="upload-progress-percent">0%</div>
  </div>
</div>
'''
    # Inserer avant </body>
    html = html.replace("</body>", PROGRESS_BLOCK + "</body>", 1)
    print("[OK] payment.html -> bloc progress ajoute")

    # Ajouter le CSS
    PROGRESS_CSS = '''
/* -------- Barre de progression upload (fixe bas) -------- */
.pay-progress{
  position:fixed;
  left:0;right:0;bottom:0;
  z-index:500;
  background:rgba(255,255,255,.98);
  border-top:1px solid var(--line);
  padding:14px 16px calc(14px + env(safe-area-inset-bottom));
  box-shadow:0 -4px 20px rgba(15,23,42,.08);
  animation:slideUpProgress .25s ease;
}
@keyframes slideUpProgress{
  from{transform:translateY(100%)}
  to{transform:translateY(0)}
}
.pay-progress.hidden{display:none !important}
.pay-progress-inner{
  max-width:560px;margin:0 auto;
}
.pay-progress-label{
  font-size:13px;font-weight:700;color:var(--ink);
  margin:0 0 10px;display:flex;align-items:center;gap:6px;
}
.pay-progress-track{
  height:8px;background:#eef2f7;border-radius:999px;overflow:hidden;
}
.pay-progress-fill{
  height:100%;background:linear-gradient(90deg,var(--blue),#2a6ba8);
  border-radius:999px;transition:width .3s cubic-bezier(.4,0,.2,1);
  box-shadow:0 0 8px rgba(26,74,127,.3);
}
.pay-progress-percent{
  font-size:13px;font-weight:800;color:var(--blue-dark);
  text-align:right;margin-top:8px;
  font-family:Consolas,monospace;
}
'''
    html = html.replace("</style>", PROGRESS_CSS + "\n</style>", 1)
    print("[OK] payment.html -> styles progress")

HTML.write_text(html, encoding="utf-8")

# ============================================================
# 2. JS : showProgress simplifie
# ============================================================
js = JS.read_text(encoding="utf-8")

# Remplacer la fonction showProgress
import re
old_showpat = re.compile(
    r'  function showProgress\(percent, label\) \{.*?\n  \}\n\n  function hideProgress\(\) \{.*?\n  \}',
    re.DOTALL,
)

new_show = '''  function showProgress(percent, label) {
    var box = document.getElementById("upload-progress");
    if (!box) {
      console.error("[progress] element #upload-progress introuvable");
      return;
    }
    box.classList.remove("hidden");
    var fill = document.getElementById("upload-progress-fill");
    var pct = document.getElementById("upload-progress-percent");
    var lbl = document.getElementById("upload-progress-label");
    if (fill) fill.style.width = Math.max(0, Math.min(100, percent)) + "%";
    if (pct) pct.textContent = Math.round(percent) + "%";
    if (lbl && label) lbl.textContent = label;
    console.log("[progress] " + Math.round(percent) + "% - " + (label || ""));
  }

  function hideProgress() {
    var box = document.getElementById("upload-progress");
    if (box) box.classList.add("hidden");
  }'''

if old_showpat.search(js):
    js = js.replace(old_showpat.search(js).group(0), new_show, 1)
    print("[OK] payment.js -> showProgress simplifie")
else:
    print("[!] showProgress introuvable")

JS.write_text(js, encoding="utf-8")

print()
print("=" * 60)
print("BARRE FIXE EN BAS DE L'ECRAN")
print("=" * 60)
print()
print("La barre apparait :")
print("  - Fixe en bas de l'ecran (au-dessus de tout)")
print("  - Reste visible pendant tout l'upload")
print("  - Affiche le pourcentage qui progresse")
print("  - Disparait quand l'upload termine")
print()
print("PROCHAINE ETAPE :")
print("  1. Ctrl+Shift+R sur Edge/iPhone")
print("  2. Ouvre F12 -> onglet Console")
print("  3. Clique 'Envoyer la preuve'")
print("  4. Colle-moi les logs [progress] et [payment]")