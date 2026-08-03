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
    if (config.ads_enabled === false) return;
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
    window.jbftag = window.jbftag || { cmd: [] };
    window.jbftag.cmd.push(function () {
      if (window.jbftag && typeof window.jbftag.showRewardedAds === 'function') {
        window.jbftag.showRewardedAds(callback);
      } else {
        callback();
      }
    });
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
  }

  ChatFunnel.prototype.init = function () {
    this.choosePersona();
    this.renderShell();
    if (this.config.gate && this.config.gate.enabled !== false) {
      this.renderGate();
      requestRewardAds(this.config);
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
      var cta = el('button', 'mgs-cf-gate-cta', gate.cta_label || 'VER OFERTAS →');
      cta.type = 'button';
      cta.addEventListener('click', function () {
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

  ChatFunnel.prototype.showInlineAd = function () {
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
    var chat = this.config.chat || {};
    var headline = chat.offer_headline || '🎉 Encontrei as melhores ofertas para você!';
    splitMessages(headline).forEach(this.addMessage.bind(this));

    var offers = el('div', 'mgs-cf-offers');
    (this.config.offers || []).forEach(function (offer) {
      var a = el('a', 'mgs-cf-offer-card');
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
