/* Register Elonikab Health - version robuste */
(function () {
  "use strict";

  function $(id) { return document.getElementById(id); }
  function $$(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

  console.log("[register] script charge");

  var state = { accountType: null, step: 0 };

  function showMsg(t, ok) {
    var m = $("msg");
    if (!m) return;
    m.textContent = t;
    m.className = "msg" + (ok ? " ok" : "");
  }
  function hideMsg() {
    var m = $("msg");
    if (m) m.className = "msg hidden";
  }

  function stepsFor(type) {
    if (type === "pro") return [1, 2, 3];
    if (type === "patient") return [2, 3];
    return [];
  }
  function totalSteps() {
    return stepsFor(state.accountType).length;
  }
  function stepIndex() {
    return stepsFor(state.accountType).indexOf(state.step) + 1;
  }

  function setStep(n) {
    state.step = n;
    console.log("[register] setStep", n, "accountType=", state.accountType);

    // Afficher/masquer les etapes
    $$(".step").forEach(function (s) {
      var sNum = parseInt(s.getAttribute("data-step"), 10);
      s.classList.toggle("active", sNum === n);
    });

    var isFirst = (n === 0);
    var progressWrap = $("progress-wrap");
    var actionsWrap = $("actions-wrap");
    var mainTitle = $("main-title");
    var mainSub = $("main-sub");

    if (progressWrap) progressWrap.classList.toggle("hidden", isFirst);
    if (actionsWrap) actionsWrap.classList.toggle("hidden", isFirst);
    if (mainTitle) mainTitle.textContent = isFirst ? "Creer mon compte" : "Finalisons votre inscription";
    if (mainSub) mainSub.textContent = isFirst
      ? "Choisissez votre type de compte pour commencer."
      : "Quelques informations supplementaires.";

    if (isFirst) return;

    var total = totalSteps();
    var idx = stepIndex();
    var labels = { 1: "Etablissement", 2: "Informations", 3: "Securite" };

    var pl = $("progress-label");
    var pt = $("progress-title");
    var pf = $("progress-fill");
    if (pl) pl.textContent = "Etape " + idx + "/" + total;
    if (pt) pt.textContent = labels[n] || "";
    if (pf) pf.style.width = Math.round((idx / total) * 100) + "%";

    var isLast = (idx === total);
    var btnPrev = $("btn-prev");
    var btnNext = $("btn-next");
    var btnSubmit = $("btn-submit");

    if (btnPrev) btnPrev.classList.remove("hidden");
    if (btnNext) btnNext.classList.toggle("hidden", isLast);
    if (btnSubmit) btnSubmit.classList.toggle("hidden", !isLast);

    if (n === 2) {
      var labelName = $("label-name");
      if (labelName) {
        labelName.textContent = state.accountType === "pro"
          ? "Nom du responsable *"
          : "Nom complet *";
      }
    }
  }

  function nextStep() {
    var order = stepsFor(state.accountType);
    var i = order.indexOf(state.step);
    if (i < order.length - 1) setStep(order[i + 1]);
  }
  function prevStep() {
    var order = stepsFor(state.accountType);
    var i = order.indexOf(state.step);
    if (i > 0) {
      setStep(order[i - 1]);
    } else {
      state.accountType = null;
      $$(".acc-btn").forEach(function (b) { b.classList.remove("active"); });
      setStep(0);
    }
  }

  function validate(n) {
    hideMsg();
    if (n === 0) {
      if (!state.accountType) { showMsg("Choisissez un type de compte."); return false; }
    }
    if (n === 1) {
      if (!$("establishment_type") || !$("establishment_type").value) {
        showMsg("Selectionnez le type d'etablissement."); return false;
      }
      if (!$("establishment_name") || !$("establishment_name").value.trim()) {
        showMsg("Le nom de l'etablissement est obligatoire."); return false;
      }
      if (!$("establishment_city") || !$("establishment_city").value.trim()) {
        showMsg("La ville est obligatoire."); return false;
      }
    }
    if (n === 2) {
      if (!$("full_name") || !$("full_name").value.trim()) {
        showMsg("Le nom est obligatoire."); return false;
      }
      if (!$("phone") || !$("phone").value.trim()) {
        showMsg("Le telephone est obligatoire."); return false;
      }
      var email = $("email") ? $("email").value.trim() : "";
      if (!email || email.indexOf("@") === -1) {
        showMsg("E-mail invalide."); return false;
      }
    }
    if (n === 3) {
      var pwd = $("password") ? $("password").value : "";
      if (!pwd || pwd.length < 6) {
        showMsg("Mot de passe trop court (6 caracteres minimum)."); return false;
      }
      if (!$("terms") || !$("terms").checked) {
        showMsg("Vous devez accepter les conditions d'utilisation."); return false;
      }
      if (!$("accurate") || !$("accurate").checked) {
        showMsg("Vous devez certifier l'exactitude des informations."); return false;
      }
    }
    return true;
  }

  function setupAccountChoice() {
    $$(".acc-btn").forEach(function (b) {
      b.addEventListener("click", function () {
        var t = b.getAttribute("data-account");
        state.accountType = (t === "pro") ? "pro" : "patient";
        console.log("[register] accountType =", state.accountType);
        $$(".acc-btn").forEach(function (x) { x.classList.remove("active"); });
        b.classList.add("active");
        var order = stepsFor(state.accountType);
        if (order.length > 0) setStep(order[0]);
      });
    });
  }

  function setupTypes() {
    var box = $("types");
    if (!box) return;
    $$(".type-btn").forEach(function (b) {
      b.addEventListener("click", function () {
        $$(".type-btn").forEach(function (x) { x.classList.remove("active"); });
        b.classList.add("active");
        var hidden = $("establishment_type");
        if (hidden) hidden.value = b.getAttribute("data-value");

        // Scroll automatique vers le formulaire d'etablissement
        try {
          var nameInput = $("establishment_name");
          if (nameInput) {
            var rect = nameInput.getBoundingClientRect();
            var y = rect.top + window.pageYOffset - 100; // offset header
            window.scrollTo({ top: y, behavior: "smooth" });
            setTimeout(function () {
              try { nameInput.focus({ preventScroll: true }); } catch (e) {}
            }, 400);
          }
        } catch (e) {}
      });
    });
  }

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

  function submitForm() {
    console.log("[register] submitForm() appele");
    if (!validate(3)) {
      console.log("[register] validation echouee");
      return;
    }
    var btn = $("btn-submit");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Creation...";
    }

    var isPro = (state.accountType === "pro");
    var payload = {
      email: $("email") ? $("email").value.trim() : "",
      phone: $("phone") ? $("phone").value.trim() : "",
      password: $("password") ? $("password").value : "",
      full_name: $("full_name") ? $("full_name").value.trim() : "",
      role: isPro ? "PROFESSIONNEL" : "PATIENT"
    };

    if (isPro) {
      payload.establishment_type = $("establishment_type") ? $("establishment_type").value : "";
      payload.establishment_name = $("establishment_name") ? $("establishment_name").value.trim() : "";
      payload.establishment_city = $("establishment_city") ? $("establishment_city").value.trim() : "";
      payload.establishment_responsible = payload.full_name;
    }

    console.log("[register] payload =", payload);

    fetch("/api/auth/register", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(function (r) {
        console.log("[register] reponse status", r.status);
        return r.json().then(function (d) {
          if (!r.ok) throw new Error(d.detail || "Erreur d'inscription");
          return d;
        });
      })
      .then(function (d) {
        console.log("[register] OK", d);
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
        console.error("[register] erreur", e);
        showMsg(e.message || "Erreur d'inscription");
        if (btn) {
          btn.disabled = false;
          btn.textContent = "Creer mon compte";
        }
      });
  }

  function init() {
    // Auto-bascule PRO si ?type= dans l'URL (venant de la landing)
    var __preType = "";
    try {
      var __params = new URLSearchParams(window.location.search);
      __preType = (__params.get("type") || "").toUpperCase();
    } catch (e) {}

    if (__preType) {
      // Pre-remplir le type d'etablissement
      var __hiddenType = document.getElementById("establishment_type");
      if (__hiddenType) __hiddenType.value = __preType;

      // Activer le bouton PRO
      var __proBtn = document.querySelector('.acc-btn[data-account="pro"]');
      if (__proBtn) {
        setTimeout(function () {
          __proBtn.click();
          // Preselectionner le type dans la grille
          setTimeout(function () {
            var __typeBtn = document.querySelector('.type-btn[data-value="' + __preType + '"]');
            if (__typeBtn) __typeBtn.click();
            // Scroll smooth vers le formulaire
            try {
              var __card = document.getElementById("register-form") || document.querySelector(".card");
              if (__card) {
                var y = __card.getBoundingClientRect().top + window.pageYOffset - 20;
                window.scrollTo({ top: y, behavior: "smooth" });
              }
            } catch (e) {}
            // Focus sur le nom d'etablissement
            setTimeout(function () {
              var __nameInput = document.getElementById("establishment_name");
              if (__nameInput) {
                try { __nameInput.focus({ preventScroll: true }); } catch (e) {}
              }
            }, 500);
          }, 100);
        }, 50);
      }
    }

    console.log("[register] init()");
    setupAccountChoice();
    setupTypes();
    setupStrength();

    // Bouton "Continuer"
    var btnNext = $("btn-next");
    if (btnNext) {
      btnNext.addEventListener("click", function () {
        console.log("[register] clic Continuer step=", state.step);
        if (validate(state.step)) nextStep();
      });
    }

    // Bouton "Retour"
    var btnPrev = $("btn-prev");
    if (btnPrev) {
      btnPrev.addEventListener("click", function () {
        hideMsg();
        prevStep();
      });
    }

    // Bouton "Creer mon compte"
    var btnSubmit = $("btn-submit");
    if (btnSubmit) {
      btnSubmit.addEventListener("click", function (ev) {
        ev.preventDefault();
        console.log("[register] clic Creer mon compte");
        submitForm();
      });
    }

    // Form submit natif (si Enter depuis un champ)
    var form = $("register-form");
    if (form) {
      form.addEventListener("submit", function (ev) {
        ev.preventDefault();
        console.log("[register] form submit");
        if (state.step === 3) {
          submitForm();
        } else if (validate(state.step)) {
          nextStep();
        }
      });
    }

    setStep(0);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
