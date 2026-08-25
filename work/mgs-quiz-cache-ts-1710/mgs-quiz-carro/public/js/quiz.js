/*
 * MGS Quiz — frontend público em vanilla JS.
 * Espera window.MGS_QUIZ_REST e window.MGS_QUIZ_CFG no escopo global.
 *
 * Garantias:
 *   - máscara de telefone configurável
 *   - honeypot + timestamp anti-spam
 *   - só redireciona se o POST /lead retornar ok:true
 *   - em erro, reabilita o botão e mostra mensagem amigável
 *   - track Lead via fbq/dataLayer
 *   - escolha ponderada de redirect_variants
 *   - preserva TODOS os query params (UTMs, fbclid, gclid, ...) no redirect
 */
(function () {
  var cfg  = window.MGS_QUIZ_CFG  || {};
  var REST = window.MGS_QUIZ_REST || '';
  if (!cfg || !REST) return;

  var root = document.querySelector('.mgs-quiz');
  if (!root) return;

  var online = root.querySelector('#mgsq-online-count');
  if (online) {
    var updateOnline = function () { online.textContent = String(Math.floor(80 + Math.random() * 61)); };
    updateOnline();
    setInterval(updateOnline, 8000);
  }

  var step1     = root.querySelector('.mgs-quiz-step-1');
  var step2     = root.querySelector('.mgs-quiz-step-2');
  var success   = root.querySelector('.mgs-quiz-success');
  var stepTitle = root.querySelector('.mgs-quiz-step-title');
  var progress  = root.querySelector('.mgs-quiz-progress-bar');
  var errorMsg  = root.querySelector('.mgs-quiz-error-msg');

  var state = { parcela: '' };

  function track(ev, data) {
    try { if (window.fbq) window.fbq('trackCustom', ev, data || {}); } catch (e) {}
    try { (window.dataLayer = window.dataLayer || []).push(Object.assign({ event: ev }, data || {})); } catch (e) {}
  }
  function getUrlParams() {
    var out = {};
    try { new URLSearchParams(location.search).forEach(function (v, k) { out[k] = v; }); } catch (e) {}
    return out;
  }
  function applyMask(value, mask) {
    var digits = (value || '').replace(/\D/g, '');
    var out = ''; var i = 0;
    for (var c = 0; c < mask.length; c++) {
      if (i >= digits.length) break;
      var ch = mask.charAt(c);
      if (ch === '9') { out += digits.charAt(i); i++; } else { out += ch; }
    }
    return out;
  }
  function maskPhone(v) {
    var mask = cfg.form_phone_mask;
    if (mask && mask.indexOf('9') !== -1) return applyMask(v, mask);
    var x = (v || '').replace(/\D/g, '');
    x = x.replace(/^(\d{2})(\d)/g, '($1) $2');
    x = x.replace(/(\d{5})(\d)/, '$1-$2');
    return x.substring(0, 15);
  }
  function pickWeighted(pool, fallback) {
    var valid = (pool || []).filter(function (v) { return v && v.url && Number(v.weight) > 0; });
    if (!valid.length) return fallback;
    var total = valid.reduce(function (s, v) { return s + Number(v.weight); }, 0);
    var r = Math.random() * total;
    for (var i = 0; i < valid.length; i++) { r -= Number(valid[i].weight); if (r <= 0) return String(valid[i].url).trim(); }
    return String(valid[valid.length - 1].url).trim();
  }
  function buildRedirect(base, extra) {
    if (!base) return '';
    try {
      var url = new URL(base);
      Object.keys(extra).forEach(function (k) {
        if (extra[k] == null || extra[k] === '') return;
        if (url.searchParams.has(k)) return;
        url.searchParams.append(k, extra[k]);
      });
      return url.toString();
    } catch (e) { return base; }
  }
  function showError(msg) {
    if (!errorMsg) return;
    errorMsg.textContent = msg || 'Não foi possível enviar agora. Tente novamente em instantes.';
    errorMsg.style.display = 'block';
  }
  function clearError() { if (errorMsg) { errorMsg.textContent = ''; errorMsg.style.display = 'none'; } }

  // Step 1: pick option
  Array.prototype.forEach.call(root.querySelectorAll('.mgs-quiz-option'), function (btn) {
    btn.addEventListener('click', function () {
      state.parcela = btn.getAttribute('data-value') || '';
      track('QuizStep1', { parcela: state.parcela });
      root.classList.add('mgs-quiz-is-step2');
      if (step1) step1.style.display = 'none';
      if (step2) step2.style.display = root.classList.contains('mgsq-sb') ? 'flex' : 'block';
      if (stepTitle) stepTitle.textContent = stepTitle.getAttribute('data-step2') || '';
      if (progress) progress.style.width = '90%';
    });
  });

  if (!step2) return;

  // Step 2: mask + submit
  var phoneInput = step2.querySelector('input[name="phone"]');
  var tsInput    = step2.querySelector('input[name="ts"]');
  function resetFormTimestamp() {
    if (tsInput) tsInput.value = String(Date.now());
  }
  // O HTML público pode vir de page cache. Nunca use como início do formulário
  // o timestamp renderizado pelo servidor dentro de uma página cacheada.
  resetFormTimestamp();
  window.addEventListener('pageshow', function (ev) {
    if (ev.persisted) resetFormTimestamp();
  });
  if (phoneInput) {
    phoneInput.addEventListener('input', function () { phoneInput.value = maskPhone(phoneInput.value); });
  }

  step2.addEventListener('submit', function (ev) {
    ev.preventDefault();
    clearError();
    var nameInput = step2.querySelector('input[name="name"]');
    var hpInput   = step2.querySelector('input[name="website"]');
    var submitBtn = step2.querySelector('.mgs-quiz-submit');

    var name  = ((nameInput && nameInput.value) || '').trim();
    var phone = ((phoneInput && phoneInput.value) || '').replace(/\D/g, '');
    var hp    = (hpInput && hpInput.value) || '';
    var ts    = Number((tsInput && tsInput.value) || 0);
    var bad = false;
    if (name.length < 2) { if (nameInput) nameInput.classList.add('is-error'); bad = true; } else if (nameInput) nameInput.classList.remove('is-error');
    if (phone.length < 10) { if (phoneInput) phoneInput.classList.add('is-error'); bad = true; } else if (phoneInput) phoneInput.classList.remove('is-error');
    if (bad) { showError('Preencha nome e telefone com DDD.'); return; }

    var all = getUrlParams();
    var payload = {
      slug: cfg.slug, name: name, phone: phone, parcela: state.parcela,
      utm_source: all.utm_source, utm_medium: all.utm_medium, utm_campaign: all.utm_campaign,
      utm_term: all.utm_term, utm_content: all.utm_content,
      fbclid: all.fbclid, gclid: all.gclid,
      extra: all,
      website: hp,   // honeypot
      ts: ts         // timestamp do carregamento do form
    };

    if (submitBtn) { submitBtn.disabled = true; submitBtn.style.opacity = 0.6; }
    fetch(REST + '/lead', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (r) {
      return r.json().then(function (j) { return { status: r.status, body: j }; })
                     .catch(function () { return { status: r.status, body: { ok: false, error: 'invalid_json' } }; });
    }).then(function (out) {
      if (!out.body || out.body.ok !== true) {
        if (submitBtn) { submitBtn.disabled = false; submitBtn.style.opacity = 1; }
        var msg = (out.body && out.body.error) ? String(out.body.error) : 'Falha ao enviar. Tente novamente.';
        showError(msg);
        return;
      }
      // sucesso confirmado pelo servidor → dispara conversão e redireciona
      track('Lead', { value: 1, currency: 'BRL', parcela: state.parcela });
      root.classList.add('mgs-quiz-is-success');
      if (step2) step2.style.display = 'none';
      if (success) success.style.display = 'block';
      if (progress) progress.style.width = '100%';

      var pool = [].concat(
        cfg.redirect_url ? [{ url: cfg.redirect_url, weight: Number(cfg.redirect_url_weight) || 0 }] : [],
        Array.isArray(cfg.redirect_variants) ? cfg.redirect_variants : []
      );
      var base = pickWeighted(pool, cfg.redirect_url || '');
      var dest = buildRedirect(base, all);
      var delay = Number(cfg.redirect_delay_ms) || 1800;
      if (dest) setTimeout(function () { window.location.href = dest; }, delay);
    }).catch(function () {
      if (submitBtn) { submitBtn.disabled = false; submitBtn.style.opacity = 1; }
      showError('Erro de conexão. Tente novamente.');
    });
  });
})();
