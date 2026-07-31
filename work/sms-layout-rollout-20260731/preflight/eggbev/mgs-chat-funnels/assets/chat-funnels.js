(function () {
  'use strict';

  function sleep(ms) {
    return new Promise(function (resolve) { setTimeout(resolve, ms); });
  }

  function mergeSourceParams(targetUrl) {
    try {
      var url = new URL(targetUrl, window.location.href);
      var sourceParams = new URLSearchParams(window.location.search);
      sourceParams.forEach(function (value, key) {
        url.searchParams.set(key, value);
      });
      return url.toString();
    } catch (e) {
      return targetUrl;
    }
  }

  function pickRandom(items) {
    if (!Array.isArray(items) || !items.length) return null;
    return items[Math.floor(Math.random() * items.length)];
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (typeof text === 'string') node.textContent = text;
    return node;
  }

  function splitMessages(value) {
    if (Array.isArray(value)) return value;
    if (typeof value === 'string') return value.split('|').map(function (v) { return v.trim(); }).filter(Boolean);
    return [];
  }

  function requestRewardAds(config) {
    if (config.ads_enabled === false || adProvider(config) !== 'jbf') return;
    window.jbftag = window.jbftag || { cmd: [] };
    window.jbftag.cmd.push(function () {
      if (window.jbftag && typeof window.jbftag.requestRewardAds === 'function') {
        window.jbftag.requestRewardAds();
      }
    });
  }

  function showRewardedThen(config, callback) {
    if (config.ads_enabled === false) {
      callback();
      return;
    }
    var provider = adProvider(config);
    if (provider === 'm2' || provider === 'actview') {
      setTimeout(callback, 1200);
      return;
    }
    window.jbftag = window.jbftag || { cmd: [] };
    window.jbftag.cmd.push(function () {
      if (window.jbftag && typeof window.jbftag.showRewardedAds === 'function') {
        window.jbftag.showRewardedAds(callback);
      } else {
        callback();
      }
    });
  }

  function adProvider(config) {
    var provider = String(config.ad_provider || 'jbf').toLowerCase();
    if (provider === 'm2' || provider === 'monetizemore' || provider === 'monetize-more') return 'm2';
    if (provider === 'actview' || provider === 'zuout-actview') return 'actview';
    return 'jbf';
  }

  function applyRewardedClass(config, node) {
    if (!node) return;
    var provider = adProvider(config);
    if (provider === 'm2') node.classList.add('pg-rewarded');
    if (provider === 'actview') node.classList.add('av-rewarded');
  }

  function ChatFunnel(container, config) {
    this.container = container;
    this.config = config;
    this.root = container.querySelector('.mgs-chat-funnel-root');
    this.chatBox = null;
    this.questionIndex = -1;
    this.offerIndex = 0;
    this.started = false;
    this.botName = null;
    this.botPhoto = null;
    this.smsLeadCaptured = false;
    this.smsLeadSubmitting = false;
    this.smsFormStartedAt = Date.now();
  }

  ChatFunnel.prototype.init = function () {
    this.choosePersona();
    this.renderShell();
    if (this.config.gate && this.config.gate.enabled !== false) {
      this.renderGate();
      if (adProvider(this.config) === 'jbf') {
        requestRewardAds(this.config);
      }
    } else {
      this.startChat();
    }
  };

  ChatFunnel.prototype.choosePersona = function () {
    var persona = this.config.persona || {};
    this.botName = pickRandom(persona.names) || 'Maria';
    var female = persona.female_names || [];
    var photos = female.indexOf(this.botName) !== -1 ? persona.female_photos : persona.male_photos;
    this.botPhoto = pickRandom(photos) || (Array.isArray(persona.photos) ? pickRandom(persona.photos) : null) || '';
  };

  ChatFunnel.prototype.renderShell = function () {
    var persona = this.config.persona || {};
    this.root.innerHTML = '';

    var chat = el('div', 'mgs-cf-chat');
    var header = el('div', 'mgs-cf-header');
    var avatar = el('img', 'mgs-cf-avatar');
    avatar.alt = this.botName;
    avatar.src = this.botPhoto || 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2240%22 height=%2240%22 viewBox=%220 0 40 40%22%3E%3Crect width=%2240%22 height=%2240%22 rx=%2220%22 fill=%22%23d9fdd3%22/%3E%3Ctext x=%2220%22 y=%2226%22 font-size=%2220%22 text-anchor=%22middle%22%3E%F0%9F%92%AC%3C/text%3E%3C/svg%3E';

    var info = el('div', 'mgs-cf-header-info');
    info.appendChild(el('div', 'mgs-cf-name', this.botName + ' • ' + (persona.role || 'Consultor')));
    info.appendChild(el('div', 'mgs-cf-status', persona.status || '🟢 online agora'));

    var call = el('a', 'mgs-cf-call', '☎');
    call.setAttribute('aria-label', 'Ligar agora');
    call.href = this.randomOfferUrl();

    header.appendChild(avatar);
    header.appendChild(info);
    header.appendChild(call);

    this.chatBox = el('div', 'mgs-cf-box');
    chat.appendChild(header);
    chat.appendChild(this.chatBox);
    this.root.appendChild(chat);
  };

  ChatFunnel.prototype.randomOfferUrl = function () {
    var offers = this.config.offers || [];
    var offer = pickRandom(offers);
    return mergeSourceParams(offer && offer.target ? offer.target : '#');
  };

  ChatFunnel.prototype.renderGate = function () {
    var self = this;
    var gate = this.config.gate || {};
    var questions = gate.questions || [];
    var current = 0;

    var overlay = el('div', 'mgs-cf-gate');
    var card = el('div', 'mgs-cf-gate-card');
    var progressShell = el('div', 'mgs-cf-gate-progress-shell');
    var progress = el('div', 'mgs-cf-gate-progress');
    var body = el('div', 'mgs-cf-gate-body');

    progressShell.appendChild(progress);
    card.appendChild(progressShell);
    card.appendChild(body);
    overlay.appendChild(card);
    this.root.appendChild(overlay);

    function progressWidth() {
      if (!questions.length) return 100;
      return Math.round(((current + 1) / (questions.length + 1)) * 100);
    }

    function drawQuestion() {
      var q = questions[current];
      if (!q) {
        drawLoading();
        return;
      }
      progress.style.width = progressWidth() + '%';
      body.innerHTML = '';
      var slide = el('div', 'mgs-cf-gate-slide');
      slide.appendChild(el('p', 'mgs-cf-gate-question', q.text || 'Vamos começar?'));
      var answers = el('div', 'mgs-cf-gate-answers');
      (q.answers || []).forEach(function (answer) {
        var label = typeof answer === 'string' ? answer : answer.label;
        var btn = el('button', '', label || 'Continuar');
        btn.type = 'button';
        btn.addEventListener('click', function () {
          Array.prototype.forEach.call(answers.querySelectorAll('button'), function (b) { b.disabled = true; });
          current += 1;
          setTimeout(drawQuestion, 350);
        });
        answers.appendChild(btn);
      });
      slide.appendChild(answers);
      body.appendChild(slide);
    }

    function drawLoading() {
      progress.style.width = '80%';
      body.innerHTML = '';
      var loading = el('div', 'mgs-cf-gate-loading');
      var dots = el('div', 'mgs-cf-typing');
      dots.style.display = 'inline-flex';
      dots.appendChild(el('span', 'mgs-cf-dot'));
      dots.appendChild(el('span', 'mgs-cf-dot'));
      dots.appendChild(el('span', 'mgs-cf-dot'));
      loading.appendChild(dots);
      loading.appendChild(el('h2', '', gate.loading_text || '🔍 Buscando a melhor oferta para você...'));
      body.appendChild(loading);
      setTimeout(drawFinal, Number(gate.loading_ms || 1800));
    }

    function drawFinal() {
      progress.style.width = '100%';
      body.innerHTML = '';
      var final = el('div', 'mgs-cf-gate-final');
      final.appendChild(el('div', 'mgs-cf-gate-icon', gate.final_icon || '💬'));
      final.appendChild(el('p', 'mgs-cf-gate-title', gate.final_title || 'Oferta encontrada!'));
      final.appendChild(el('p', 'mgs-cf-gate-subtitle', gate.final_subtitle || 'Um especialista foi identificado para te atender agora.'));
      if (self.config.sms_enabled) {
        var smsForm = el('div', 'mgs-cf-sms-form');
        var nameLabel = el('label', '', self.config.sms_name_label || 'Nome');
        var nameInput = el('input');
        nameInput.type = 'text'; nameInput.autocomplete = 'name'; nameInput.maxLength = 200; nameInput.placeholder = 'Digite seu nome'; nameInput.id = 'mgs-cf-sms-name';
        nameLabel.setAttribute('for', nameInput.id);
        var phoneLabel = el('label', '', self.config.sms_phone_label || 'Telefone');
        var phoneInput = el('input');
        phoneInput.type = 'tel'; phoneInput.inputMode = 'numeric'; phoneInput.autocomplete = 'tel'; phoneInput.maxLength = 20; phoneInput.placeholder = '(11) 99999-9999'; phoneInput.id = 'mgs-cf-sms-phone';
        phoneLabel.setAttribute('for', phoneInput.id);
        phoneInput.addEventListener('input', function () { this.value = self.formatSmsPhone(this.value); });
        var websiteInput = el('input'); websiteInput.type = 'text'; websiteInput.id = 'mgs-cf-sms-website'; websiteInput.tabIndex = -1; websiteInput.setAttribute('aria-hidden', 'true');
        var smsError = el('p', 'mgs-cf-sms-error'); smsError.id = 'mgs-cf-sms-error'; smsError.setAttribute('role', 'alert');
        smsForm.appendChild(nameLabel); smsForm.appendChild(nameInput); smsForm.appendChild(phoneLabel); smsForm.appendChild(phoneInput); smsForm.appendChild(websiteInput); smsForm.appendChild(smsError);
        final.appendChild(smsForm);
      }
      var cta = el('button', 'mgs-cf-gate-cta', gate.cta_label || 'VER OFERTAS →');
      if (!self.config.sms_enabled) applyRewardedClass(self.config, cta);
      cta.type = 'button';
      cta.addEventListener('click', function () {
        if (self.config.sms_enabled && !self.smsLeadCaptured) {
          self.submitSmsLead(cta);
          return;
        }
        applyRewardedClass(self.config, cta);
        cta.disabled = true;
        showRewardedThen(self.config, function () {
          overlay.remove();
          self.startChat();
        });
      });
      final.appendChild(cta);
      if (gate.footer_note) final.appendChild(el('small', 'mgs-cf-gate-note', gate.footer_note));
      body.appendChild(final);
    }

    drawQuestion();
  };

  ChatFunnel.prototype.formatSmsPhone = function (value) {
    var digits = String(value || '').replace(/\D/g, '').slice(0, 11);
    if (digits.length <= 2) return digits;
    if (digits.length <= 6) return '(' + digits.slice(0, 2) + ') ' + digits.slice(2);
    if (digits.length <= 10) return '(' + digits.slice(0, 2) + ') ' + digits.slice(2, 6) + '-' + digits.slice(6);
    return '(' + digits.slice(0, 2) + ') ' + digits.slice(2, 7) + '-' + digits.slice(7);
  };

  ChatFunnel.prototype.smsError = function (message) {
    var node = this.root.querySelector('#mgs-cf-sms-error');
    if (node) node.textContent = message || '';
  };

  ChatFunnel.prototype.submitSmsLead = function (cta) {
    var self = this;
    if (this.smsLeadSubmitting || this.smsLeadCaptured) return;
    var nameInput = this.root.querySelector('#mgs-cf-sms-name');
    var phoneInput = this.root.querySelector('#mgs-cf-sms-phone');
    var websiteInput = this.root.querySelector('#mgs-cf-sms-website');
    var name = nameInput ? nameInput.value.trim() : '';
    var phone = phoneInput ? phoneInput.value.replace(/\D/g, '') : '';
    if (name.length < 2) { this.smsError('Digite seu nome.'); if (nameInput) nameInput.focus(); return; }
    if (phone.length < 10) { this.smsError('Digite um telefone válido com DDD.'); if (phoneInput) phoneInput.focus(); return; }
    this.smsError(''); this.smsLeadSubmitting = true; cta.disabled = true; cta.textContent = 'ENVIANDO...';
    var params = new URLSearchParams(window.location.search); var extra = {};
    params.forEach(function (value, key) { extra[key] = value; });
    var payload = { chat_id: this.config.id, route: this.config.route, name: name, phone: phone, website: websiteInput ? websiteInput.value : '', ts: this.smsFormStartedAt, extra: extra };
    ['utm_source','utm_medium','utm_campaign','utm_term','utm_content','fbclid','gclid'].forEach(function (key) { payload[key] = params.get(key) || ''; });
    fetch(this.config.sms_rest_url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' }, credentials: 'same-origin', body: JSON.stringify(payload) })
      .then(function (response) { return response.json().catch(function () { return {}; }).then(function (data) { return { response: response, data: data }; }); })
      .then(function (result) {
        if (!result.response.ok || !result.data.ok) throw new Error(result.data.error || 'Não foi possível enviar. Tente novamente.');
        self.smsLeadCaptured = true; self.smsLeadSubmitting = false; cta.disabled = false; cta.textContent = (self.config.gate && self.config.gate.cta_label) || self.config.sms_submit_label || 'TRANSFERIR PARA ESPECIALISTA →'; cta.click();
      })
      .catch(function (error) { self.smsLeadSubmitting = false; cta.disabled = false; cta.textContent = (self.config.gate && self.config.gate.cta_label) || self.config.sms_submit_label || 'TRANSFERIR PARA ESPECIALISTA →'; self.smsError(error && error.message ? error.message : 'Não foi possível enviar. Tente novamente.'); });
  };

  ChatFunnel.prototype.showInlineAd = function () {
    if (adProvider(this.config) === 'actview') {
      var actViewBanner = el('div', 'ad-unit ad');
      actViewBanner.dataset.position = 'top';
      actViewBanner.innerHTML = '<div id="zout_top_wrapper" align="center" style="width:100%;margin-top:2rem;margin-bottom:2rem;min-height:400px"><div><p style="font-size:10px;text-transform:uppercase;text-align:center">Anúncios</p><div id="zout_top"></div></div></div>';
      this.chatBox.appendChild(actViewBanner);
      this.scrollBottom();
      if (window.onInfinitePostLoaded) window.onInfinitePostLoaded();
      this.keepPinnedToBottom(4500);
      return;
    }

    if (adProvider(this.config) === 'm2') {
      var pgTopSlot = this.pubGuruTopSlot();
      var pgBanner = el('div', 'pubguru-chat-ad pubguru-chat-ad-top');
      pgBanner.style.minHeight = pgTopSlot === 'wantabrand_mob_top' ? '420px' : '300px';
      pgBanner.style.display = 'flex';
      pgBanner.style.alignItems = 'center';
      pgBanner.style.justifyContent = 'center';
      pgBanner.style.margin = '28px 0 28px';
      pgBanner.style.position = 'relative';
      pgBanner.style.overflow = 'hidden';
      pgBanner.style.isolation = 'isolate';
      pgBanner.style.width = '100%';
      pgBanner.style.flexShrink = '0';
      var pgSlot = document.createElement('pubguru');
      pgSlot.setAttribute('data-pg-ad', pgTopSlot);
      pgSlot.style.display = 'block';
      pgSlot.style.maxWidth = '100%';
      pgBanner.appendChild(pgSlot);
      this.chatBox.appendChild(pgBanner);
      this.scrollBottom();
      // M2/PubGuru: do not fire the legacy infinite-post hook here; it can
      // trigger the interstitial early. Register this top-block tag async so
      // ad rendering cannot block the next chat question.
      setTimeout(this.registerPubGuruTopBlock.bind(this, pgSlot, 0), 0);
      this.keepPinnedToBottom(7000);
      if (window.ResizeObserver) {
        var pgResizeObserver = new ResizeObserver(this.keepPinnedToBottom.bind(this, 1000));
        pgResizeObserver.observe(pgBanner);
        setTimeout(function () { pgResizeObserver.disconnect(); }, 6000);
      }
      if (window.MutationObserver) {
        var pgMutationObserver = new MutationObserver(this.keepPinnedToBottom.bind(this, 1000));
        pgMutationObserver.observe(pgBanner, { attributes: true, childList: true, subtree: true });
        setTimeout(function () { pgMutationObserver.disconnect(); }, 6000);
      }
      return;
    }

    var adBanner = el('div', 'ad-unit ad');
    adBanner.dataset.position = 'top';
    adBanner.appendChild(el('div'));
    this.chatBox.appendChild(adBanner);
    this.scrollBottom();
    if (window.onInfinitePostLoaded) {
      window.onInfinitePostLoaded();
    }
    this.keepPinnedToBottom(4500);
    if (window.ResizeObserver) {
      var resizeObserver = new ResizeObserver(this.keepPinnedToBottom.bind(this, 1000));
      resizeObserver.observe(adBanner);
      setTimeout(function () { resizeObserver.disconnect(); }, 6000);
    }
    if (window.MutationObserver) {
      var mutationObserver = new MutationObserver(this.keepPinnedToBottom.bind(this, 1000));
      mutationObserver.observe(adBanner, { attributes: true, childList: true, subtree: true });
      setTimeout(function () { mutationObserver.disconnect(); }, 6000);
    }
  };

  ChatFunnel.prototype.pubGuruTopSlot = function () {
    if (window.matchMedia && window.matchMedia('(min-width: 768px)').matches) {
      return 'wantabrand_desk_top';
    }
    return 'wantabrand_mob_top';
  };

  ChatFunnel.prototype.registerPubGuruTopBlock = function (slot, attempt) {
    attempt = Number(attempt || 0);
    if (window.pga && window.pga.adunitManager && typeof window.pga.adunitManager.defineObserveredNode === 'function') {
      try {
        window.pga.adunitManager.defineObserveredNode(slot);
        if (slot.classList && slot.classList.contains('pg-disabled') && slot.parentElement) {
          slot.parentElement.style.minHeight = '0';
          slot.parentElement.style.margin = '0';
        }
        this.keepPinnedToBottom(2500);
      } catch (err) {
        console.warn('PubGuru top block registration failed', err);
      }
      return;
    }
    if (attempt < 20) {
      setTimeout(this.registerPubGuruTopBlock.bind(this, slot, attempt + 1), 250);
    }
  };

  ChatFunnel.prototype.startChat = function () {
    if (this.started) return;
    this.started = true;
    this.askQuestion('');
  };

  ChatFunnel.prototype.addMessage = function (text, role) {
    var msg = el('div', 'mgs-cf-message ' + (role === 'user' ? 'mgs-cf-user' : 'mgs-cf-bot'), text);
    this.chatBox.appendChild(msg);
    this.scrollBottom();
  };

  ChatFunnel.prototype.addTyping = function () {
    var typing = el('div', 'mgs-cf-typing');
    typing.appendChild(el('span', 'mgs-cf-dot'));
    typing.appendChild(el('span', 'mgs-cf-dot'));
    typing.appendChild(el('span', 'mgs-cf-dot'));
    this.chatBox.appendChild(typing);
    this.scrollBottom();
    return typing;
  };

  ChatFunnel.prototype.scrollBottom = function () {
    this.chatBox.scrollTop = this.chatBox.scrollHeight;
    var lastChild = this.chatBox.lastElementChild;
    if (lastChild && lastChild.scrollIntoView) {
      var self = this;
      requestAnimationFrame(function () {
        self.chatBox.scrollTop = self.chatBox.scrollHeight;
        lastChild.scrollIntoView({ block: 'end', inline: 'nearest' });
      });
    }
  };


  ChatFunnel.prototype.keepPinnedToBottom = function (durationMs) {
    var self = this;
    var startedAt = Date.now();
    durationMs = Number(durationMs || 3500);
    this.scrollBottom();
    var interval = setInterval(function () {
      self.scrollBottom();
      if (Date.now() - startedAt >= durationMs) {
        clearInterval(interval);
      }
    }, 250);
  };

  ChatFunnel.prototype.askQuestion = function (userAnswer) {
    var self = this;
    if (userAnswer) {
      this.addMessage(userAnswer, 'user');
      var oldButtons = this.chatBox.querySelector('.mgs-cf-buttons');
      if (oldButtons) oldButtons.remove();
    }

    sleep(400).then(function () {
      var typing = self.addTyping();
      return sleep(1200).then(function () {
        typing.remove();
        self.questionIndex += 1;
        if (self.questionIndex === 2) {
          self.showInlineAd();
        }
        self.showStep();
      });
    });
  };

  ChatFunnel.prototype.getSteps = function () {
    var chat = this.config.chat || {};
    var steps = [];
    steps.push({ messages: (chat.intro || []).map(this.replaceVars.bind(this)), answers: chat.start_answers || ['✅ Vamos lá!'] });
    (chat.questions || []).forEach(function (q) {
      steps.push({ messages: splitMessages(q.text || q.question), answers: q.answers || [] });
    });
    (chat.pre_offer_messages || []).forEach(function (m) {
      steps.push({ messages: splitMessages(m), auto: true });
    });
    steps.push({ offers: true });
    return steps;
  };

  ChatFunnel.prototype.replaceVars = function (text) {
    return String(text).replace(/\{botName\}/g, this.botName);
  };

  ChatFunnel.prototype.showStep = function () {
    var self = this;
    var steps = this.getSteps();
    var step = steps[this.questionIndex];
    if (!step) return;

    if (step.offers) {
      this.showOffers();
      return;
    }

    var chain = Promise.resolve();
    (step.messages || []).forEach(function (message, idx) {
      chain = chain.then(function () {
        self.addMessage(self.replaceVars(message), 'bot');
        return sleep(idx < step.messages.length - 1 ? 700 : 0);
      });
    });

    chain.then(function () {
      if (step.auto) {
        setTimeout(function () { self.askQuestion(''); }, 900);
        return;
      }
      self.renderButtons(step.answers || []);
    });
  };

  ChatFunnel.prototype.renderButtons = function (answers) {
    var self = this;
    var wrap = el('div', 'mgs-cf-buttons');
    answers.forEach(function (answer) {
      var label = typeof answer === 'string' ? answer : answer.label;
      var target = typeof answer === 'object' ? answer.target : null;
      var btn = el('button', '', label || 'Continuar');
      btn.type = 'button';
      if (target) {
        var a = el('a');
        a.href = mergeSourceParams(target);
        applyRewardedClass(self.config, a);
        applyRewardedClass(self.config, btn);
        a.appendChild(btn);
        wrap.appendChild(a);
      } else {
        btn.addEventListener('click', function () { self.askQuestion(label); });
        wrap.appendChild(btn);
      }
    });
    this.chatBox.appendChild(wrap);
    setTimeout(function () { wrap.classList.add('is-visible'); self.scrollBottom(); self.keepPinnedToBottom(1500); }, 50);
  };

  ChatFunnel.prototype.showOffers = function () {
    var mode = this.config.mode || (this.config.chat && this.config.chat.offer_mode) || 'cards';
    if (mode === 'sequential') {
      this.showSequentialOffer(0);
    } else {
      this.showCardsOffers();
    }
  };

  ChatFunnel.prototype.showCardsOffers = function () {
    var self = this;
    var chat = this.config.chat || {};
    var headline = chat.offer_headline || '🎉 Encontrei as melhores ofertas para você!';
    splitMessages(headline).forEach(this.addMessage.bind(this));

    var offers = el('div', 'mgs-cf-offers');
    (this.config.offers || []).forEach(function (offer) {
      var a = el('a', 'mgs-cf-offer-card');
      applyRewardedClass(self.config, a);
      a.href = mergeSourceParams(offer.target || '#');
      if (offer.logo) {
        var img = el('img');
        img.src = offer.logo;
        img.alt = offer.name || '';
        a.appendChild(img);
      }
      var info = el('div');
      info.style.flex = '1';
      info.appendChild(el('p', 'mgs-cf-offer-name', offer.name || 'Oferta'));
      info.appendChild(el('p', 'mgs-cf-offer-subtitle', offer.subtitle || 'Ver oferta'));
      a.appendChild(info);
      a.appendChild(el('span', 'mgs-cf-offer-arrow', '→'));
      offers.appendChild(a);
    });
    this.chatBox.appendChild(offers);
    this.scrollBottom();
  };

  ChatFunnel.prototype.showSequentialOffer = function (index) {
    var self = this;
    var offers = this.config.offers || [];
    var offer = offers[index];
    if (!offer) return;
    this.offerIndex = index;

    var chain = Promise.resolve();
    (offer.messages || [offer.name || 'Encontrei uma opção para você.']).forEach(function (message, idx) {
      chain = chain.then(function () {
        self.addMessage(message, 'bot');
        return sleep(idx < offer.messages.length - 1 ? 700 : 0);
      });
    });

    chain.then(function () {
      var answers = [{ label: offer.accept_label || 'Sim, quero conhecer →', target: offer.target }];
      if (offer.reject_label && offers[index + 1]) {
        answers.push({ label: offer.reject_label, reject: true });
      }
      var wrap = el('div', 'mgs-cf-buttons');
      answers.forEach(function (answer) {
        var btn = el('button', '', answer.label);
        btn.type = 'button';
        if (answer.reject) {
          btn.addEventListener('click', function () {
            self.addMessage(answer.label, 'user');
            wrap.remove();
            self.showSequentialOffer(index + 1);
          });
          wrap.appendChild(btn);
        } else {
          var a = el('a');
          a.href = mergeSourceParams(answer.target || '#');
          applyRewardedClass(self.config, a);
          applyRewardedClass(self.config, btn);
          a.appendChild(btn);
          wrap.appendChild(a);
        }
      });
      self.chatBox.appendChild(wrap);
      setTimeout(function () { wrap.classList.add('is-visible'); self.scrollBottom(); self.keepPinnedToBottom(1500); }, 50);
    });
  };

  function initContainer(container) {
    var script = container.querySelector('.mgs-chat-funnel-config');
    if (!script) return;
    try {
      var config = JSON.parse(script.textContent || '{}');
      new ChatFunnel(container, config).init();
    } catch (e) {
      // Keep failures visible only in console; frontend should fail closed.
      console.error('MGS Chat Funnel config error', e);
    }
  }

  function initAll() {
    Array.prototype.forEach.call(document.querySelectorAll('.mgs-chat-funnel'), initContainer);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
})();
