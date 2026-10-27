# -*- coding: utf-8 -*-
# prep_safari_test.py
# 1) Verifie que safe_locale.js est charge partout
# 2) Verifie que realtime.js est charge sur pro + suivi
# 3) Ajoute un reconnexion SSE sur visibilitychange (retour d'ecran verrouille)
import os, re, shutil, datetime

ROOT = r"C:\Users\ELOGE KEY\Desktop\pharma\pharmacie"
STATIC = os.path.join(ROOT, "static")

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
bak = os.path.join(ROOT, f"_backup_safari_{ts}")
os.makedirs(bak, exist_ok=True)
print(f"[BACKUP] {bak}\n")

# ============================================================
# 1. ENRICHIR professional_realtime.js : reconnexion sur visibilitychange
# ============================================================
JS = os.path.join(STATIC, "professional_realtime.js")
shutil.copy2(JS, os.path.join(bak, "professional_realtime.js.bak"))
js = open(JS, "r", encoding="utf-8").read()

if "visibilitychange" in js:
    print("[SKIP] visibilitychange deja present")
else:
    MARKER = '''  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();'''
    INSERT = '''  // Safari iOS : reconnexion SSE au retour de veille/arriere-plan
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible") {
      if (_sse && _sse.readyState === EventSource.CLOSED) {
        _sse = null;
        connectSSE();
      } else if (!_sse) {
        connectSSE();
      }
    }
  });
  window.addEventListener("pageshow", function (ev) {
    // Safari iOS : evenement declenche au retour de back-forward cache
    if (!_sse) connectSSE();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();'''

    if MARKER in js:
        js = js.replace(MARKER, INSERT, 1)
        open(JS, "w", encoding="utf-8").write(js)
        print("[OK] professional_realtime.js : reconnexion Safari iOS ajoutee")
    else:
        print("[!!] marker final introuvable")

# ============================================================
# 2. VERIF : safe_locale.js charge partout
# ============================================================
print("\n[VERIF] safe_locale.js dans les HTML")
HTMLS = [f for f in os.listdir(STATIC) if f.endswith(".html")]
missing = []
for name in sorted(HTMLS):
    p = os.path.join(STATIC, name)
    h = open(p, "r", encoding="utf-8").read()
    has = "safe_locale.js" in h
    flag = "OK" if has else "--"
    print(f"  [{flag}] {name}")
    if not has:
        missing.append(name)

# ============================================================
# 3. VERIF : realtime.js sur les pages critiques
# ============================================================
print("\n[VERIF] realtime.js sur pro + suivi")
CRITICAL = [
    "professional.html",
    "professional_catalogue.html",
    "professional_commandes.html",
    "professional_demande.html",
    "professional_etablissement.html",
    "suivi.html",
]
for name in CRITICAL:
    p = os.path.join(STATIC, name)
    if not os.path.exists(p):
        print(f"  [--] {name} absent")
        continue
    h = open(p, "r", encoding="utf-8").read()
    has = "professional_realtime.js" in h
    print(f"  [{'OK' if has else '!!'}] {name}")

# ============================================================
# 4. VERIF cookie config dans auth.py
# ============================================================
AUTH = os.path.join(ROOT, "v3_modules", "auth.py")
auth = open(AUTH, "r", encoding="utf-8").read()
print("\n[VERIF] Cookie config")
print(f"  SameSite=None : {'OK' if 'samesite=\"none\"' in auth else '!!'}")
print(f"  Secure=True   : {'OK' if 'secure=True' in auth else '!!'}")
print(f"  HttpOnly      : {'OK' if 'httponly=True' in auth else '!!'}")

print(f"\n[BACKUP] {bak}")
print("\n[CMD] Pas de restart Uvicorn (static only).")
print("\n[TEST SAFARI iOS]")
print("1. Ouvre Safari sur iPhone")
print("2. Va sur https://robot-everyday-rainbow-nowhere.trycloudflare.com/")
print("3. Login patient@test.tg / Test1234")
print("4. Verifie que la page ne clignote pas (FOUC)")
print("5. Va sur /suivi?ref=CMD-...")