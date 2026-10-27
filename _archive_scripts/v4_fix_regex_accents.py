"""
v4_fix_regex_accents.py
Remplace les regex avec accents par des codes Unicode purs.
Les regex [àâä] etc. cassent sur iOS Safari si l'encodage n'est pas parfait.
"""
from pathlib import Path
import datetime
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
CATJS = STATIC / "professional_catalogue.js"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / ("_backup_fix_regex_" + stamp)
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(CATJS, backup / "professional_catalogue.js")
print("[OK] Backup ->", backup.name)

js = CATJS.read_text(encoding="utf-8")

# 1. Remplacer la fonction normalize par une version Unicode-safe
old_normalize = '''function normalize(s) {
    return String(s || "").toLowerCase()
      .replace(/[àâä]/g, "a").replace(/[éèêë]/g, "e")
      .replace(/[íîï]/g, "i").replace(/[óôö]/g, "o")
      .replace(/[ùûü]/g, "u").replace(/ç/g, "c");
  }'''

new_normalize = '''function normalize(s) {
    // iOS Safari safe : on utilise des codes Unicode, pas des caracteres accentes
    try {
      var str = String(s == null ? "" : s).toLowerCase();
      return str
        .replace(/\\u00e0|\\u00e2|\\u00e4/g, "a")
        .replace(/\\u00e9|\\u00e8|\\u00ea|\\u00eb/g, "e")
        .replace(/\\u00ee|\\u00ef|\\u00ed/g, "i")
        .replace(/\\u00f4|\\u00f6|\\u00f3/g, "o")
        .replace(/\\u00f9|\\u00fb|\\u00fc/g, "u")
        .replace(/\\u00e7/g, "c");
    } catch (e) {
      console.error("normalize error:", e);
      return String(s || "");
    }
  }'''

if old_normalize in js:
    js = js.replace(old_normalize, new_normalize, 1)
    print("[OK] normalize() -> Unicode safe")
elif "\\u00e0|\\u00e2" in js:
    print("[i] normalize deja patche")
else:
    # Chercher le bloc normalize actuel et le remplacer par regex
    import re
    pattern = re.compile(r'function normalize\(s\) \{.*?\n  \}', re.DOTALL)
    if pattern.search(js):
        js = pattern.sub(new_normalize, js, count=1)
        print("[OK] normalize() -> remplace (fallback regex)")
    else:
        print("[!] normalize introuvable")

# 2. Remplacer escapeHtml avec regex accent-safe aussi
old_esc = '''function escapeHtml(s) {
    try {
      return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
        return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
      });
    } catch (e) {
      return "";
    }
  }'''
new_esc = '''function escapeHtml(s) {
    try {
      var str = String(s == null ? "" : s);
      return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    } catch (e) {
      return "";
    }
  }'''

if old_esc in js:
    js = js.replace(old_esc, new_esc, 1)
    print("[OK] escapeHtml -> simplification (pas de regex multi-caracteres)")

# 3. Ajouter une journalisation detaillee sur addToDraft
old_add = '''function addToDraft(product, qty, btn) {
    if (btn) { btn.disabled = true; btn.textContent = "Ajout..."; }

    ensureDraft().then(function (draft) {'''
new_add = '''function addToDraft(product, qty, btn) {
    console.log("[addToDraft] start", product && product.id, qty);
    if (btn) { btn.disabled = true; btn.textContent = "Ajout..."; }

    ensureDraft().then(function (draft) {
      console.log("[addToDraft] draft", draft && draft.reference);'''

if old_add in js:
    js = js.replace(old_add, new_add, 1)
    print("[OK] addToDraft -> logs ajoutes")

# 4. Remplacer le toast par un message avec details si erreur
old_catch = '''}).catch(function (e) {
      var msg = "Erreur";
      try {
        if (e && e.message) msg = e.message;
        else if (e && e.toString) msg = e.toString();
      } catch (x) { msg = "Erreur inconnue"; }
      console.error("addToDraft:", e);
      toast(msg);
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = "+ Ajouter a ma demande";
      }
    });'''
new_catch = '''}).catch(function (e) {
      console.error("[addToDraft] ERROR", e);
      var msg = "Erreur";
      try {
        if (e && e.message) msg = e.message;
        else if (e && e.toString) msg = e.toString();
      } catch (x) { msg = "Erreur inconnue"; }
      // Afficher aussi la stack pour debug
      if (e && e.stack) console.error("[addToDraft] STACK:", e.stack);
      toast(msg);
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = "+ Ajouter a ma demande";
      }
    });'''

if old_catch in js:
    js = js.replace(old_catch, new_catch, 1)
    print("[OK] addToDraft -> catch detaillé")

# 5. Meme traitement pour updateNavCount
old_update = '''function updateNavCount() {
    var c = document.getElementById("nav-count");
    if (!c) return;
    var n = state.draftItemsCount;
    if (n > 0) {
      c.textContent = n > 99 ? "99+" : String(n);
      c.classList.remove("hidden");
    } else {
      c.classList.add("hidden");
    }
  }'''
new_update = '''function updateNavCount() {
    try {
      var c = document.getElementById("nav-count");
      if (!c) return;
      var n = state.draftItemsCount;
      if (n > 0) {
        c.textContent = n > 99 ? "99+" : String(n);
        c.classList.remove("hidden");
      } else {
        c.classList.add("hidden");
      }
    } catch (e) {
      console.error("[updateNavCount]", e);
    }
  }'''

if old_update in js:
    js = js.replace(old_update, new_update, 1)
    print("[OK] updateNavCount -> try/catch")

CATJS.write_text(js, encoding="utf-8")

# ============================================================
# Verifier l'encodage du fichier
# ============================================================
raw = CATJS.read_bytes()
try:
    raw.decode("utf-8")
    print("[OK] Fichier JS en UTF-8 valide")
except UnicodeDecodeError as e:
    print("[!] Probleme d'encodage detecte :", e)

# BOM check
if raw[:3] == b'\xef\xbb\xbf':
    print("[!] BOM UTF-8 detecte, retrait...")
    CATJS.write_bytes(raw[3:])
    print("[OK] BOM retire")

print()
print("=" * 60)
print("FIX REGEX APPLIQUE")
print("=" * 60)
print()
print("Changements :")
print("  - normalize() utilise des codes Unicode purs (\\u00e0...)")
print("  - escapeHtml() simplifie (chaines de .replace)")
print("  - addToDraft logge chaque etape dans la console")
print("  - updateNavCount wrappe dans try/catch")
print()
print("PROCHAINE ETAPE :")
print("  1. Ctrl+Shift+R sur Edge")
print("  2. Sur iPhone : navigation privee")
print("  3. Ouvre F12 (Edge) -> onglet Console")
print("  4. Re-teste l'ajout et COLLE-MOI ce que tu vois dans la console")
print()
print("Les logs [addToDraft] et [EH-ERROR] nous diront exactement la ligne qui plante.")