"""
fix_register_neutre.py
Inscription commune : choix Particulier / Professionnel au depart.
"""
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"
REG = STATIC / "register.html"
REGJS = STATIC / "register.js"

shutil.copy2(REG, REG.with_suffix(".html.bak"))
shutil.copy2(REGJS, REGJS.with_suffix(".js.bak"))
print("[OK] Backups crees")

# ============================================================
# 1. Nouveau register.html
# ============================================================
REG_HTML = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Inscription - Elokinab Health</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
:root{
  --blue:#174A7E;--blue-dark:#0F3457;--blue-soft:#E8F0F8;
  --ink:#0F172A;--muted:#64748B;--line:#E2E8F0;--bg:#F5F8FC;
  --danger:#B23C3C;--ok:#0A7A5A;
}
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  font-family:-apple-system,"Segoe UI",system-ui,sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.5;font-size:15px;
  min-height:100vh;padding:20px;-webkit-font-smoothing:antialiased;
}
.card{
  width:100%;max-width:480px;margin:20px auto;background:#fff;
  border-radius:20px;padding:30px 26px;
  box-shadow:0 12px 40px rgba(15,23,42,.08);
}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:22px}
.brand-logo{
  width:42px;height:42px;border-radius:11px;
  background:linear-gradient(135deg,#174A7E,#2A6BA8);color:#fff;
  display:flex;align-items:center;justify-content:center;
  font-size:22px;font-weight:800;
}
.brand-name{font-size:16px;font-weight:800;line-height:1.1}
.brand-tag{font-size:10px;color:var(--muted);text-transform:uppercase;
  letter-spacing:.1em;margin-top:2px}
h1{font-size:21px;font-weight:800;letter-spacing:-.02em;margin:0 0 4px}
.sub{font-size:13px;color:var(--muted);margin:0 0 18px;line-height:1.5}

/* Progress bar */
.progress{margin:0 0 22px}
.progress-text{
  display:flex;justify-content:space-between;
  font-size:11px;font-weight:800;
  text-transform:uppercase;letter-spacing:.08em;
  color:var(--muted);margin-bottom:8px;
}
.progress-track{
  height:6px;background:#EEF2F7;border-radius:999px;overflow:hidden;
}
.progress-fill{
  height:100%;background:linear-gradient(90deg,#174A7E,#2A6BA8);
  border-radius:999px;transition:width .3s cubic-bezier(.4,0,.2,1);
}

.step{display:none}
.step.active{display:block}

.field{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.field label{font-size:12.5px;font-weight:700;color:var(--ink)}
.field input, .field select{
  padding:13px 14px;border:1.5px solid var(--line);border-radius:11px;
  font-family:inherit;font-size:15px;outline:none;background:#fff;color:var(--ink);
  width:100%;transition:.15s;
}
.field input:focus, .field select:focus{
  border-color:var(--blue);box-shadow:0 0 0 3px var(--blue-soft);
}

/* Grande carte de choix de type de compte */
.account-choice{
  display:flex;flex-direction:column;gap:12px;margin-bottom:20px;
}
.acc-btn{
  display:flex;align-items:center;gap:16px;
  padding:18px;border:2px solid var(--line);border-radius:14px;
  background:#fff;cursor:pointer;font-family:inherit;
  text-align:left;transition:.15s;
}
.acc-btn:hover{border-color:var(--blue);transform:translateY(-1px);
  box-shadow:0 4px 14px rgba(23,74,126,.1)}
.acc-btn.active{border-color:var(--blue);background:var(--blue-soft)}
.acc-btn .acc-ico{
  width:52px;height:52px;border-radius:14px;
  background:var(--blue-soft);color:var(--blue);
  display:flex;align-items:center;justify-content:center;
  font-size:24px;flex-shrink:0;
}
.acc-btn.active .acc-ico{background:#fff;color:var(--blue)}
.acc-btn .acc-body{flex:1;min-width:0}
.acc-btn .acc-title{font-size:15px;font-weight:800;color:var(--ink);margin:0 0 3px}
.acc-btn .acc-desc{font-size:12.5px;color:var(--muted);margin:0;line-height:1.4}
.acc-btn .acc-arrow{color:var(--muted);font-size:20px;flex-shrink:0}

.types{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:14px}
.type-btn{
  padding:14px 12px;border:1.5px solid var(--line);border-radius:11px;
  background:#fff;cursor:pointer;font-family:inherit;
  display:flex;flex-direction:column;align-items:center;gap:6px;
  font-size:12.5px;font-weight:700;color:var(--ink);
  transition:.15s;
}
.type-btn:hover{border-color:var(--blue)}
.type-btn.active{
  border-color:var(--blue);background:var(--blue-soft);color:var(--blue-dark);
}
.type-btn .ico{font-size:20px}

.row-2{display:grid;grid-template-columns:1fr 1fr;gap:12px}

.msg{
  padding:11px 14px;border-radius:11px;font-size:13px;
  margin-bottom:14px;background:#FDE8E8;color:var(--danger);
  border:1px solid #F6D2D2;
}
.msg.ok{background:#E6F7F1;color:var(--ok);border-color:#C7E9DC}
.msg.hidden{display:none}

.actions{
  display:flex;gap:10px;margin-top:20px;padding-top:18px;
  border-top:1px solid var(--line);
}
.btn{
  flex:1;padding:15px;border:0;border-radius:12px;
  font-weight:800;font-size:14.5px;
  cursor:pointer;transition:.15s;
}
.btn-primary{background:var(--blue);color:#fff}
.btn-primary:hover:not(:disabled){background:var(--blue-dark)}
.btn-primary:disabled{background:#C7D5E3;cursor:not-allowed}
.btn-ghost{
  background:#fff;border:1.5px solid var(--line);
  color:var(--ink);
}
.btn-ghost:hover{border-color:var(--blue);color:var(--blue)}

.checks{display:flex;flex-direction:column;gap:10px;margin-top:12px}
.check{display:flex;align-items:flex-start;gap:10px;font-size:12.5px;color:var(--ink);cursor:pointer;line-height:1.5}
.check input{accent-color:var(--blue);width:16px;height:16px;margin-top:2px;flex-shrink:0}
.check a{color:var(--blue);font-weight:700;text-decoration:none}

.alt{
  text-align:center;font-size:13px;color:var(--muted);
  margin-top:18px;padding-top:16px;border-top:1px solid var(--line);
}
.alt a{color:var(--blue);font-weight:800;text-decoration:none}

.strength{
  height:4px;background:#EEF2F7;border-radius:999px;overflow:hidden;margin-top:6px;
}
.strength-fill{height:100%;width:0%;transition:.3s;background:#DC2626}
.strength-fill.weak{background:#DC2626;width:33%}
.strength-fill.medium{background:#F59E0B;width:66%}
.strength-fill.strong{background:#0A7A5A;width:100%}

@media (max-width:400px){
  .card{padding:22px 18px}
  .row-2{grid-template-columns:1fr}
  .types{grid-template-columns:1fr}
  .acc-btn{padding:14px}
  .acc-btn .acc-ico{width:44px;height:44px;font-size:20px}
}
</style>
</head>
<body>

<form class="card" id="register-form" autocomplete="on">
  <div class="brand">
    <div class="brand-logo">+</div>
    <div>
      <div class="brand-name">Elokinab Health</div>
      <div class="brand-tag">Healthcare Procurement</div>
    </div>
  </div>

  <h1 id="main-title">Creer mon compte</h1>
  <p class="sub" id="main-sub">Choisissez votre type de compte pour commencer.</p>

  <div class="progress hidden" id="progress-wrap">
    <div class="progress-text">
      <span id="progress-label">Etape 1/3</span>
      <span id="progress-title">Etablissement</span>
    </div>
    <div class="progress-track"><div class="progress-fill" id="progress-fill" style="width:33%"></div></div>
  </div>

  <div id="msg" class="msg hidden"></div>

  <!-- ETAPE 0 : TYPE DE COMPTE -->
  <div class="step active" data-step="0">
    <div class="account-choice">
      <button type="button" class="acc-btn" data-account="patient">
        <span class="acc-ico">&#128100;</span>
        <span class="acc-body">
          <span class="acc-title">Particulier</span>
          <span class="acc-desc">Pour mes besoins personnels ou ceux de ma famille.</span>
        </span>
        <span class="acc-arrow">&#8250;</span>
      </button>

      <button type="button" class="acc-btn" data-account="pro">
        <span class="acc-ico">&#127973;</span>
        <span class="acc-body">
          <span class="acc-title">Structure professionnelle</span>
          <span class="acc-desc">Clinique, cabinet, laboratoire, hopital.</span>
        </span>
        <span class="acc-arrow">&#8250;</span>
      </button>
    </div>
  </div>

  <!-- ETAPES PRO -->
  <div class="step" data-step="1" data-account="pro">
    <div class="field">
      <label>Type d'etablissement *</label>
      <div class="types" id="types">
        <button type="button" class="type-btn" data-value="CLINIQUE">
          <span class="ico">&#127973;</span>Clinique
        </button>
        <button type="button" class="type-btn" data-value="CABINET_MEDICAL">
          <span class="ico">&#129658;</span>Cabinet medical
        </button>
        <button type="button" class="type-btn" data-value="LABORATOIRE">
          <span class="ico">&#128300;</span>Laboratoire
        </button>
        <button type="button" class="type-btn" data-value="HOPITAL">
          <span class="ico">&#127974;</span>Hopital
        </button>
        <button type="button" class="type-btn" data-value="CENTRE_SANTE">
          <span class="ico">&#127976;</span>Centre de sante
        </button>
        <button type="button" class="type-btn" data-value="AUTRE">
          <span class="ico">&#10133;</span>Autre
        </button>
      </div>
      <input type="hidden" id="establishment_type" value="">
    </div>

    <div class="field">
      <label for="establishment_name">Nom de l'etablissement *</label>
      <input type="text" id="establishment_name" placeholder="Ex : Clinique Les Merveilles">
    </div>

    <div class="field">
      <label for="establishment_city">Ville *</label>
      <input type="text" id="establishment_city" placeholder="Ex : Lome">
    </div>
  </div>

  <!-- ETAPE INFOS (particulier + pro) -->
  <div class="step" data-step="2">
    <div class="field">
      <label for="full_name" id="label-name">Nom complet *</label>
      <input type="text" id="full_name" required placeholder="Ex : Adjalo Georges" autocomplete="name">
    </div>

    <div class="field">
      <label for="phone">Telephone *</label>
      <input type="tel" id="phone" required placeholder="Ex : 90 00 00 00" autocomplete="tel">
    </div>

    <div class="field">
      <label for="email">E-mail *</label>
      <input type="email" id="email" required placeholder="vous@exemple.tg" autocomplete="email">
    </div>
  </div>

  <!-- ETAPE SECURITE -->
  <div class="step" data-step="3">
    <div class="field">
      <label for="password">Mot de passe * (6 caracteres minimum)</label>
      <input type="password" id="password" required minlength="6" autocomplete="new-password">
      <div class="strength"><div class="strength-fill" id="strength-fill"></div></div>
    </div>

    <div class="checks">
      <label class="check">
        <input type="checkbox" id="terms" required>
        <span>J'accepte les <a href="#" onclick="return false">conditions d'utilisation</a> et la <a href="#" onclick="return false">politique de confidentialite</a>.</span>
      </label>
      <label class="check">
        <input type="checkbox" id="accurate" required>
        <span>Je certifie que les informations fournies sont exactes.</span>
      </label>
    </div>
  </div>

  <!-- ACTIONS -->
  <div class="actions hidden" id="actions-wrap">
    <button type="button" class="btn btn-ghost hidden" id="btn-prev">Retour</button>
    <button type="button" class="btn btn-primary" id="btn-next">Continuer</button>
    <button type="submit" class="btn btn-primary hidden" id="btn-submit">Creer mon compte</button>
  </div>

  <div class="alt">
    Deja un compte ? <a href="/connexion">Se connecter</a>
  </div>
</form>

<script src="/static/safe_locale.js"></script>
<script src="/static/register.js"></script>
</body>
</html>
'''
REG.write_text(REG_HTML, encoding="utf-8")
print("[OK] register.html reecrit")

# ============================================================
# 2. Nouveau register.js
# ============================================================
REG_JS = '''/* Register Elokinab Health - Particulier + Pro */
(function () {
  var $ = function (id) { return document.getElementById(id); };

  // State
  var state = {
    accountType: null,  // 'patient' ou 'pro'
    step: 0             // etape courante
  };

  function showMsg(t, ok) {
    var m = $("msg");
    m.textContent = t;
    m.className = "msg" + (ok ? " ok" : "");
    m.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  function hideMsg() { $("msg").className = "msg hidden"; }

  // Ordre des etapes selon le type de compte
  function stepsFor(type) {
    if (type === "pro") return [1, 2, 3];
    return [2, 3];  // particulier : on saute l'etape "etablissement"
  }

  function totalSteps() {
    return stepsFor(state.accountType).length;
  }

  function stepIndex() {
    return stepsFor(state.accountType).indexOf(state.step) + 1;
  }

  function setStep(n) {
    state.step = n;

    var steps = document.querySelectorAll(".step");
    Array.prototype.forEach.call(steps, function (s) {
      s.classList.toggle("active",
        parseInt(s.getAttribute("data-step"), 10) === n);
    });

    // Afficher/masquer progress + actions
    var isFirst = (n === 0);
    $("progress-wrap").classList.toggle("hidden", isFirst);
    $("actions-wrap").classList.toggle("hidden", isFirst);
    $("main-title").textContent = isFirst ? "Creer mon compte" : "Finalisons votre inscription";
    $("main-sub").textContent = isFirst
      ? "Choisissez votre type de compte pour commencer."
      : "Quelques informations supplementaires.";

    if (isFirst) return;

    // Progress
    var total = totalSteps();
    var idx = stepIndex();
    var labels = { 1: "Etablissement", 2: "Informations", 3: "Securite" };
    $("progress-label").textContent = "Etape " + idx + "/" + total;
    $("progress-title").textContent = labels[n] || "";
    $("progress-fill").style.width = Math.round((idx / total) * 100) + "%";

    // Boutons
    var isLast = (idx === total);
    $("btn-prev").classList.remove("hidden");
    $("btn-next").classList.toggle("hidden", isLast);
    $("btn-submit").classList.toggle("hidden", !isLast);

    // Titre du nom
    if (n === 2) {
      $("label-name").textContent =
        state.accountType === "pro" ? "Nom du responsable *" : "Nom complet *";
    }
  }

  function nextStep() {
    var order = stepsFor(state.accountType);
    var i = order.indexOf(state.step);
    if (i < order.length - 1) {
      setStep(order[i + 1]);
    }
  }
  function prevStep() {
    var order = stepsFor(state.accountType);
    var i = order.indexOf(state.step);
    if (i > 0) {
      setStep(order[i - 1]);
    } else {
      // Retour au choix initial
      state.accountType = null;
      state.step = 0;
      Array.prototype.forEach.call(
        document.querySelectorAll(".acc-btn"),
        function (b) { b.classList.remove("active"); }
      );
      setStep(0);
    }
  }

  // ============================================================
  // Validation par etape
  // ============================================================
  function validate(n) {
    hideMsg();
    if (n === 0) {
      if (!state.accountType) {
        showMsg("Choisissez un type de compte."); return false;
      }
    }
    if (n === 1) {
      if (!$("establishment_type").value) {
        showMsg("Selectionnez le type d'etablissement."); return false;
      }
      if (!$("establishment_name").value.trim()) {
        showMsg("Le nom de l'etablissement est obligatoire."); return false;
      }
      if (!$("establishment_city").value.trim()) {
        showMsg("La ville est obligatoire."); return false;
      }
    }
    if (n === 2) {
      if (!$("full_name").value.trim()) {
        showMsg("Le nom est obligatoire."); return false;
      }
      if (!$("phone").value.trim()) {
        showMsg("Le telephone est obligatoire."); return false;
      }
      var email = $("email").value.trim();
      if (!email || email.indexOf("@") === -1) {
        showMsg("E-mail invalide."); return false;
      }
    }
    if (n === 3) {
      var pwd = $("password").value;
      if (!pwd || pwd.length < 6) {
        showMsg("Mot de passe trop court (6 caracteres minimum)."); return false;
      }
      if (!$("terms").checked) {
        showMsg("Vous devez accepter les conditions d'utilisation."); return false;
      }
      if (!$("accurate").checked) {
        showMsg("Vous devez certifier l'exactitude des informations."); return false;
      }
    }
    return true;
  }

  // ============================================================
  // Choix du type de compte
  // ============================================================
  function setupAccountChoice() {
    Array.prototype.forEach.call(
      document.querySelectorAll(".acc-btn"),
      function (b) {
        b.addEventListener("click", function () {
          var t = b.getAttribute("data-account");
          state.accountType = (t === "pro") ? "pro" : "patient";
          Array.prototype.forEach.call(
            document.querySelectorAll(".acc-btn"),
            function (x) { x.classList.remove("active"); }
          );
          b.classList.add("active");

          // Aller a la 1ere etape de ce parcours
          var order = stepsFor(state.accountType);
          setStep(order[0]);
        });
      }
    );
  }

  // ============================================================
  // Boutons types d'etablissement
  // ============================================================
  function setupTypes() {
    var box = $("types");
    if (!box) return;
    Array.prototype.forEach.call(box.querySelectorAll(".type-btn"), function (b) {
      b.addEventListener("click", function () {
        Array.prototype.forEach.call(
          box.querySelectorAll(".type-btn"),
          function (x) { x.classList.remove("active"); }
        );
        b.classList.add("active");
        $("establishment_type").value = b.getAttribute("data-value");
      });
    });
  }

  // ============================================================
  // Force du mot de passe
  // ============================================================
  function setupStrength() {
    var pwd = $("password");
    var fill = $("strength-fill");
    if (!pwd || !fill) return;
    pwd.addEventListener("input", function () {
      var v = pwd.value || "";
      var score = 0;
      if (v.length >= 6) score++;
      if (v.length >= 10) score++;
      if (/[A-Z]/.test(v) && /[a-z]/.test(v)) score++;
      if (/[0-9]/.test(v)) score++;
      if (/[^A-Za-z0-9]/.test(v)) score++;
      fill.className = "strength-fill";
      if (v.length === 0) { fill.style.width = "0%"; return; }
      if (score <= 2) fill.classList.add("weak");
      else if (score <= 3) fill.classList.add("medium");
      else fill.classList.add("strong");
    });
  }

  // ============================================================
  // Soumission
  // ============================================================
  function submit() {
    if (!validate(3)) return;
    var btn = $("btn-submit");
    btn.disabled = true;
    btn.textContent = "Creation...";

    var isPro = (state.accountType === "pro");
    var payload = {
      email: $("email").value.trim(),
      phone: $("phone").value.trim(),
      password: $("password").value,
      full_name: $("full_name").value.trim(),
      role: isPro ? "PROFESSIONNEL" : "PATIENT"
    };
    if (isPro) {
      payload.establishment_type = $("establishment_type").value;
      payload.establishment_name = $("establishment_name").value.trim();
      payload.establishment_city = $("establishment_city").value.trim();
      payload.establishment_responsible = $("full_name").value.trim();
    }

    fetch("/api/auth/register", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
    .then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.detail || "Erreur d'inscription");
        return d;
      });
    })
    .then(function (d) {
      try {
        localStorage.setItem("eh_user_cache",
          JSON.stringify({ user: d.user, _at: Date.now() }));
      } catch (e) {}
      showMsg("Compte cree. Redirection...", true);
      setTimeout(function () {
        window.location.href = isPro ? "/professionnel" : "/";
      }, 700);
    })
    .catch(function (e) {
      showMsg(e.message);
      btn.disabled = false;
      btn.textContent = "Creer mon compte";
    });
  }

  // ============================================================
  // Init
  // ============================================================
  document.addEventListener("DOMContentLoaded", function () {
    setupAccountChoice();
    setupTypes();
    setupStrength();

    $("btn-next").addEventListener("click", function () {
      if (validate(state.step)) nextStep();
    });
    $("btn-prev").addEventListener("click", function () {
      hideMsg();
      prevStep();
    });
    $("register-form").addEventListener("submit", function (ev) {
      ev.preventDefault();
      if (state.step === 3) submit();
      else if (validate(state.step)) nextStep();
    });

    setStep(0);
  });
})();
'''
REGJS.write_text(REG_JS, encoding="utf-8")
print("[OK] register.js reecrit")

print()
print("=" * 60)
print("INSCRIPTION COMMUNE LIVREE")
print("=" * 60)
print()
print("Parcours :")
print("  1. Choix : Particulier OU Structure professionnelle")
print("  2. Si Particulier -> 2 etapes (infos + securite)")
print("     Si Pro        -> 3 etapes (etablissement + infos + securite)")
print()
print("Backend :")
print("  - RegisterRequest accepte establishment_* (optionnels)")
print("  - Si role=PATIENT -> compte simple")
print("  - Si role=PROFESSIONNEL -> cree le professional_profile")
print()
print("PROCHAINE ETAPE :")
print("  Ctrl+Shift+R sur le navigateur")
print("  (pas besoin de redemarrer Uvicorn)")