
      function sleep(ms) {
        return new Promise((resolve) => setTimeout(resolve, ms));
      }

      function scrollChatToBottom() {
        const chatBox = document.getElementById("chat-box");
        if (!chatBox) return;
        chatBox.scrollTop = chatBox.scrollHeight;
        const lastChild = chatBox.lastElementChild;
        if (lastChild && lastChild.scrollIntoView) {
          requestAnimationFrame(() => {
            chatBox.scrollTop = chatBox.scrollHeight;
            lastChild.scrollIntoView({ block: "end", inline: "nearest" });
          });
        }
      }

      function keepChatPinnedToBottom(durationMs = 3500) {
        const startedAt = Date.now();
        scrollChatToBottom();
        const interval = setInterval(() => {
          scrollChatToBottom();
          if (Date.now() - startedAt >= durationMs) {
            clearInterval(interval);
          }
        }, 250);
      }

      // Copia os parâmetros da URL atual para a URL de destino (sobrescreve existentes)
      function mergeSourceParams(targetUrl) {
        try {
          const url = new URL(targetUrl, window.location.href);
          const sourceParams = new URLSearchParams(window.location.search);
          sourceParams.forEach((value, key) => {
            // Sobrescreve parâmetros para garantir que todos da origem sejam levados
            url.searchParams.set(key, value);
          });
          return url.toString();
        } catch (e) {
          return targetUrl;
        }
      }

      let questionIndex = -1;
      const botNames = ["Maria","João","Juliana","José","Fernanda","Carlos","Olivia","Lucas","Camilla","Pedro"];

      const femaleNames = ["Maria","Juliana","Fernanda","Olivia","Camilla"];
      const maleNames = ["João","José","Carlos","Lucas","Pedro"];

      const femalePhotos = ["https://fincfrog.com/wp-content/uploads/2026/03/m1.jpg","https://fincfrog.com/wp-content/uploads/2026/03/m2.jpg","https://fincfrog.com/wp-content/uploads/2026/03/m3.jpg","https://fincfrog.com/wp-content/uploads/2026/03/m4.jpg","https://fincfrog.com/wp-content/uploads/2026/03/m5.jpg"];
      const malePhotos = ["https://fincfrog.com/wp-content/uploads/2026/03/h1.jpg","https://fincfrog.com/wp-content/uploads/2026/03/h2.jpg","https://fincfrog.com/wp-content/uploads/2026/03/h3.jpg","https://fincfrog.com/wp-content/uploads/2026/03/h4.jpg","https://fincfrog.com/wp-content/uploads/2026/03/h5.jpg"];

      let botName = botNames[Math.floor(Math.random() * botNames.length)];

      // Match photo to gender of chosen name
      let botPhoto;
      if (femaleNames.includes(botName)) {
        const idx = femaleNames.indexOf(botName);
        botPhoto = femalePhotos[idx];
      } else {
        const idx = maleNames.indexOf(botName);
        botPhoto = malePhotos[idx];
      }

      // Header will be set inside window.onload

      const questions = [{"question":"Olá! Eu sou {botName}. 🚗 | Sou especialista em financiamento de veículos e estou aqui para te ajudar a realizar o sonho do seu carro com as melhores condições do mercado! | Vamos encontrar a oferta ideal para você?","answers":["✅ Vamos lá!","👀 Quero conhecer as opções"]},{"question":"Quanto você pode pagar por mês?","answers":["Até R$ 500","Entre R$ 500 e R$ 1.000","Acima de R$ 1.000"]},{"question":"Você tem preferência por algum tipo de veículo?","answers":["Sim, já tenho um modelo em mente","Não, estou aberto a sugestões","Ainda estou decidindo"]},{"question":"🔍 Estou pesquisando as melhores condições para você... | 🚗 Encontrei 3 opções que podem combinar com o seu perfil. | Toque na que mais faz sentido para você:","offers":[{"name":"🚗 Financie sem entrada","subtitle":"Valores com parcelas","bank":"R$157,00 a R$299,00","image":"","url":"https://zuout.com/p1-br-car-financiamento-veiculos-sem-entrada-online/"},{"name":"💳 Ver ofertas disponíveis","subtitle":"Bancos com taxas reduzidas","bank":"e facilidade para baixo score.","image":"","url":"https://zuout.com/p1-br-car-simulacao-de-financiamento/"},{"name":"🔥 Juros reduzidos 0.98% e sem entrada","subtitle":"Consulte se essa condição está disponível para você.","bank":"Oferta por tempo LIMITADO !","image":"","url":"https://zuout.com/p1-br-car-financie-seu-carro-em-60-meses/"}]},{"question":""}];
      const rewardedButtonClass = "av-rewarded";
      const smsConfig = {"enabled":false,"endpoint":"","chatId":"CAR-BR-01","route":"/chat/car/br1","submitLabel":"TRANSFERIR PARA ESPECIALISTA →","optional":false,"consentEnabled":false};
      const gateConfig = {"skipLoading":false,"loadingMs":2000,"geoEnabled":false,"geoFallback":"Analisando ofertas disponíveis na sua região","geoPrefix":"Analisando ofertas de veículos em"};
      const smsFormStartedAt = Date.now();
      let smsLeadCaptured = false;
      let smsLeadSubmitting = false;

      function applyRewardedButtonClass(node) {
        if (!node || !rewardedButtonClass) return;
        rewardedButtonClass.split(/\s+/).filter(Boolean).forEach((className) => node.classList.add(className));
      }

      function smsError(message) {
        const error = document.getElementById("mgs-cf-sms-error");
        if (error) error.textContent = message || "";
      }

      function formatSmsPhone(value) {
        const digits = String(value || "").replace(/\D/g, "").slice(0, 11);
        if (digits.length <= 2) return digits;
        if (digits.length <= 6) return "(" + digits.slice(0, 2) + ") " + digits.slice(2);
        if (digits.length <= 10) return "(" + digits.slice(0, 2) + ") " + digits.slice(2, 6) + "-" + digits.slice(6);
        return "(" + digits.slice(0, 2) + ") " + digits.slice(2, 7) + "-" + digits.slice(7);
      }

      function continueSmsWithoutLead() {
        if (!smsConfig.enabled || !smsConfig.optional || smsLeadSubmitting) return;
        smsLeadCaptured = true;
        smsError("");
        const ctaButton = document.getElementById("aq-cta");
        if (!ctaButton) {
          window.mgsCloseQuizAfterReward();
          return;
        }
        applyRewardedButtonClass(ctaButton);
        ctaButton.click();
      }

      function loadGeoIndicator() {
        if (!gateConfig.geoEnabled) return;
        const geoText = document.getElementById("mgs-cf-geo-text");
        if (!geoText) return;
        try {
          fetch("https://ipapi.co/json/", { mode: "cors" })
            .then((response) => response.ok ? response.json() : null)
            .then((data) => {
              if (!data) return;
              const city = String(data.city || "").trim();
              const region = String(data.region_code || data.region || "").trim();
              const location = [city, region].filter(Boolean).join(", ");
              if (location) geoText.textContent = gateConfig.geoPrefix + " " + location;
            })
            .catch(() => {});
        } catch (error) {}
      }

      function submitSmsLead(ctaButton) {
        if (!smsConfig.enabled || smsLeadCaptured || smsLeadSubmitting) return;
        const nameInput = document.getElementById("mgs-cf-sms-name");
        const phoneInput = document.getElementById("mgs-cf-sms-phone");
        const consentInput = document.getElementById("mgs-cf-sms-consent");
        const websiteInput = document.getElementById("mgs-cf-sms-website");
        const name = nameInput ? nameInput.value.trim() : "";
        const phone = phoneInput ? phoneInput.value.replace(/\D/g, "") : "";
        const consent = !smsConfig.consentEnabled || !consentInput || consentInput.checked;
        if (!consent && smsConfig.optional) {
          continueSmsWithoutLead();
          return;
        }
        if (!consent) {
          smsError("Selecione o consentimento para continuar.");
          return;
        }
        if (name.length < 2) {
          smsError("Digite seu nome.");
          if (nameInput) nameInput.focus();
          return;
        }
        if (phone.length < 10) {
          smsError("Digite um telefone válido com DDD.");
          if (phoneInput) phoneInput.focus();
          return;
        }
        smsError("");
        smsLeadSubmitting = true;
        ctaButton.disabled = true;
        ctaButton.textContent = "ENVIANDO...";
        const params = new URLSearchParams(window.location.search);
        const extra = {};
        params.forEach((value, key) => { extra[key] = value; });
        extra.sms_consent = "yes";
        const payload = {
          chat_id: smsConfig.chatId,
          route: smsConfig.route,
          name: name,
          phone: phone,
          website: websiteInput ? websiteInput.value : "",
          ts: smsFormStartedAt,
          utm_source: params.get("utm_source") || "",
          utm_medium: params.get("utm_medium") || "",
          utm_campaign: params.get("utm_campaign") || "",
          utm_term: params.get("utm_term") || "",
          utm_content: params.get("utm_content") || "",
          fbclid: params.get("fbclid") || "",
          gclid: params.get("gclid") || "",
          extra: extra
        };
        fetch(smsConfig.endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Accept": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify(payload)
        }).then((response) => response.json().catch(() => ({})).then((data) => ({ response, data })))
          .then(({ response, data }) => {
            if (!response.ok || !data.ok) throw new Error(data.error || "Não foi possível enviar. Tente novamente.");
            smsLeadCaptured = true;
            smsLeadSubmitting = false;
            ctaButton.disabled = false;
            ctaButton.textContent = smsConfig.submitLabel || "TRANSFERIR PARA ESPECIALISTA →";
            ctaButton.click();
          })
          .catch((error) => {
            smsLeadSubmitting = false;
            ctaButton.disabled = false;
            ctaButton.textContent = smsConfig.submitLabel || "TRANSFERIR PARA ESPECIALISTA →";
            smsError(error && error.message ? error.message : "Não foi possível enviar. Tente novamente.");
          });
      }

      function askQuestion(userAnswer) {
        const chatBox = document.getElementById("chat-box");

        function continueChat() {
          if (userAnswer !== "") {
            const userMessage = document.createElement("div");
            userMessage.classList.add("chat-message", "user-message");
            userMessage.textContent = userAnswer;
            chatBox.appendChild(userMessage);

            const buttonContainer = document.querySelector(".button-container");
            if (buttonContainer) {
              buttonContainer.remove();
            }
          }

          setTimeout(() => {
            const typingIndicator = document.createElement("div");
            typingIndicator.classList.add("typing-indicator");
            typingIndicator.innerHTML =
              '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
            chatBox.appendChild(typingIndicator);
            scrollChatToBottom();

            setTimeout(() => {
              typingIndicator.style.display = "none";
              questionIndex++;

              if (questionIndex === 2) {
                showAd();
              }

              if (questionIndex < questions.length - 1) {
                showNextQuestion();
              } else {
                showNextQuestion();
                showProgressBar();
              }
            }, 2000);
          }, 500);
        }

        continueChat();
      }

      async function showNextQuestion() {
        const chatBox = document.getElementById("chat-box");

        const questionData = questions[questionIndex];

        let messageCounter = 0;
        const messages = questionData.question.split("|");
        for (let message of messages) {
          messageCounter += 1;
          const botMessage = document.createElement("div");
          botMessage.classList.add("chat-message", "bot-message");
          botMessage.textContent = message.replace(/\{botName\}/g, botName);
          chatBox.appendChild(botMessage);
          scrollChatToBottom();

          if (messageCounter < messages.length) {
            await sleep(Math.random() * (2000 - 1000) + 700);
          }
        }

        scrollChatToBottom();

        if (questionData.answers) {
          const buttonContainer = document.createElement("div");
          buttonContainer.classList.add("button-container");

          questionData.answers.forEach((answer) => {
            let answerButton;

            if (answer.includes("→")) {
              const answerLink = document.createElement("a");
              answerLink.dataset.mgsTargetUrl = questionData.target;
              answerLink.href = mergeSourceParams(questionData.target);
              answerLink.style.textDecoration = "none";
              answerButton = document.createElement("button");
              answerButton.textContent = answer;
              applyRewardedButtonClass(answerButton);
              applyRewardedButtonClass(answerLink);
              answerLink.appendChild(answerButton);
              buttonContainer.appendChild(answerLink);
            } else {
              // Create a button otherwise
              answerButton = document.createElement("button");
              answerButton.textContent = answer;
              answerButton.onclick = () => askQuestion(answer);
              buttonContainer.appendChild(answerButton);
            }
          });

          chatBox.appendChild(buttonContainer);

          setTimeout(() => {
            buttonContainer.style.opacity = 1;
            scrollChatToBottom();
            keepChatPinnedToBottom(1500);
          }, 1000);
        }

        if (questionData.offers) {
          const offersContainer = document.createElement("div");
          offersContainer.classList.add("offers-container");

          questionData.offers.forEach((offer) => {
            const card = document.createElement("a");
            card.dataset.mgsTargetUrl = offer.url || offer.target || "#";
            card.href = mergeSourceParams(card.dataset.mgsTargetUrl);
            card.classList.add("offer-card");
            applyRewardedButtonClass(card);

            if (offer.image) {
              const img = document.createElement("img");
              img.src = offer.image;
              img.alt = offer.name || "";
              img.classList.add("offer-card-img");
              card.appendChild(img);
            }

            const info = document.createElement("div");
            info.classList.add("offer-card-info");

            const title = document.createElement("p");
            title.classList.add("offer-card-title");
            title.textContent = offer.name || "Oferta";

            const subtitle = document.createElement("p");
            subtitle.classList.add("offer-card-subtitle");
            subtitle.textContent = offer.subtitle || "Ver oferta";

            const bank = document.createElement("p");
            bank.classList.add("offer-card-bank");
            bank.textContent = offer.bank || "";

            info.appendChild(title);
            info.appendChild(subtitle);
            if (offer.bank) info.appendChild(bank);

            const arrow = document.createElement("span");
            arrow.classList.add("offer-card-arrow");
            arrow.textContent = "→";

            card.appendChild(info);
            card.appendChild(arrow);
            offersContainer.appendChild(card);
          });

          chatBox.appendChild(offersContainer);

          setTimeout(() => {
            offersContainer.style.opacity = 1;
            scrollChatToBottom();
            keepChatPinnedToBottom(1500);
          }, 1000);
        }
      }

      function showAd() {
        const chatBox = document.getElementById("chat-box");
        if (rewardedButtonClass) {
          const pubGuruTopSlot = window.matchMedia && window.matchMedia("(min-width: 768px)").matches
            ? "wantabrand_desk_top"
            : "wantabrand_mob_top";
          const adBanner = document.createElement("div");
          adBanner.classList.add("pubguru-chat-ad", "pubguru-chat-ad-top");
          // Reserve the slot height before PubGuru fills it. On mobile the ad
          // iframe can arrive after the next question and otherwise pushes the
          // question/buttons out of view, making them look like they disappeared.
          // Mobile native/display creatives can be taller than the initial
          // placeholder. Reserve the full creative height so the next question
          // starts below the ad instead of being painted under it.
          adBanner.style.minHeight = pubGuruTopSlot === "wantabrand_mob_top" ? "420px" : "300px";
          adBanner.style.display = "flex";
          adBanner.style.alignItems = "center";
          adBanner.style.justifyContent = "center";
          adBanner.style.margin = "28px 0 28px";
          adBanner.style.position = "relative";
          adBanner.style.overflow = "hidden";
          adBanner.style.isolation = "isolate";
          adBanner.style.width = "100%";
          adBanner.style.flexShrink = "0";
          const adSlot = document.createElement("pubguru");
          adSlot.setAttribute("data-pg-ad", pubGuruTopSlot);
          adSlot.style.display = "block";
          adSlot.style.maxWidth = "100%";
          adBanner.appendChild(adSlot);
          chatBox.appendChild(adBanner);
          scrollChatToBottom();
          // M2/PubGuru: do not fire the legacy infinite-post hook here; it can
          // trigger the interstitial early. Register only this top-block tag.
          function registerPubGuruTopBlock(attempt = 0) {
            try {
              if (window.pga?.adunitManager?.defineObserveredNode) {
                window.pga.adunitManager.defineObserveredNode(adSlot);
                if (adSlot.classList.contains("pg-disabled")) {
                  adBanner.style.minHeight = "0";
                  adBanner.style.margin = "0";
                }
                keepChatPinnedToBottom(2500);
                return;
              }
            } catch (err) {
              console.warn('PubGuru top block registration failed', err);
              return;
            }
            if (attempt < 20) {
              setTimeout(() => registerPubGuruTopBlock(attempt + 1), 250);
            }
          }
          setTimeout(() => registerPubGuruTopBlock(), 0);
          keepChatPinnedToBottom(7000);

          if (window.ResizeObserver) {
            const resizeObserver = new ResizeObserver(() => keepChatPinnedToBottom(1000));
            resizeObserver.observe(adBanner);
            setTimeout(() => resizeObserver.disconnect(), 6000);
          }

          if (window.MutationObserver) {
            const mutationObserver = new MutationObserver(() => keepChatPinnedToBottom(1000));
            mutationObserver.observe(adBanner, { attributes: true, childList: true, subtree: true });
            setTimeout(() => mutationObserver.disconnect(), 6000);
          }
          return;
        }

        const adBanner = document.createElement("div");
        adBanner.innerHTML = `<div id="zout_top_wrapper" align="center" style="width: 100%; margin-top: 2rem; margin-bottom: 2rem; min-height: 400px;"><div><p style="font-size: 10px; text-transform: uppercase; text-align: center;">Anúncios</p><div id="zout_top"></div></div></div>`;
        adBanner.classList.add("ad-unit");
        adBanner.classList.add("ad");
        adBanner.dataset.position = "top";
        chatBox.appendChild(adBanner);
        scrollChatToBottom();
        if (window?.onInfinitePostLoaded) {
          window.onInfinitePostLoaded();
        }

        // O wrapper/GAM pode aumentar/alterar o bloco top depois da próxima pergunta.
        // Mantém o chat no fundo para os botões ficarem visíveis quando o top aparecer.
        keepChatPinnedToBottom(4500);

        if (window.ResizeObserver) {
          const resizeObserver = new ResizeObserver(() => keepChatPinnedToBottom(1000));
          resizeObserver.observe(adBanner);
          setTimeout(() => resizeObserver.disconnect(), 6000);
        }

        if (window.MutationObserver) {
          const mutationObserver = new MutationObserver(() => keepChatPinnedToBottom(1000));
          mutationObserver.observe(adBanner, { attributes: true, childList: true, subtree: true });
          setTimeout(() => mutationObserver.disconnect(), 6000);
        }
      }

      function showProgressBar() {
        const chatBox = document.getElementById("chat-box");

        const progressContainer = document.createElement("div");
        progressContainer.classList.add("progress-container");

        const progressBar = document.createElement("div");
        progressBar.classList.add("progress-bar");
        progressContainer.appendChild(progressBar);

        chatBox.appendChild(progressContainer);
        scrollChatToBottom();

        let width = 0;
        const interval = setInterval(() => {
          width += Math.random() * 30;
          if (width >= 100) {
            width = 100;
            clearInterval(interval);

            // Show completion message
            setTimeout(() => {
              const finalMessage = document.createElement("div");
              finalMessage.classList.add("chat-message", "bot-message");
              finalMessage.textContent =
                "Busca concluída! Clique nas ofertas acima para continuar. 🎉";
              chatBox.appendChild(finalMessage);
              scrollChatToBottom();
            }, 500);
          }
          progressBar.style.width = `${width}%`;
        }, 1000);
      }

      window.onload = function () {
        // Set header
        document.getElementById("bot-avatar").src = botPhoto;
        document.getElementById("header-name").textContent =
          botName + " • " + "Especialista em Financiamentos";

        // Set random offer on call button
        const offers = ["https://zuout.com/p1-br-car-financiamento-veiculos-sem-entrada-online/","https://zuout.com/p1-br-car-simulacao-de-financiamento/","https://zuout.com/p1-br-car-financie-seu-carro-em-60-meses/"];
        const randomOffer = offers[Math.floor(Math.random() * offers.length)];
        const callBtn = document.getElementById("call-btn");
        callBtn.dataset.mgsTargetUrl = randomOffer;
        callBtn.href = mergeSourceParams(randomOffer);

        // Start quiz
        initQuiz();
      };

      function refreshTrackedLinkHref(e) {
        const link = e.target && e.target.closest ? e.target.closest("a[data-mgs-target-url], a.offer-card, #call-btn") : null;
        if (!link) return;
        const targetUrl = link.dataset.mgsTargetUrl || link.getAttribute("href") || "";
        if (!targetUrl || targetUrl === "#") return;
        link.href = mergeSourceParams(targetUrl);
      }

      ["pointerdown", "touchstart", "mousedown", "focus", "click"].forEach((eventName) => {
        document.addEventListener(eventName, refreshTrackedLinkHref, true);
      });

      // ─── QUIZ ────────────────────────────────────────────────────────────
      let quizStep = 0;
      let isQuizClosed = false;
      let quizAlreadyClosed = false;

      function unlockScroll() {
        document.documentElement.classList.remove("modal-locked");
        document.body.classList.remove("modal-locked");
      }

      function lockScroll() {
        document.documentElement.classList.add("modal-locked");
        document.body.classList.add("modal-locked");
      }

      function closeQuiz() {
        const quizContainer = document.getElementById("quiz-container");
        if (quizContainer) quizContainer.style.display = "none";
        isQuizClosed = true;
        unlockScroll();
        askQuestion("");
      }

      window.mgsRewardedClickInProgress = false;
      window.mgsCloseQuizAfterReward = function () {
        window.mgsRewardedClickInProgress = false;
        if (!quizAlreadyClosed) {
          quizAlreadyClosed = true;
          closeQuiz();
        }
      };

      function registerRewardedCloseCallback(attempt = 0) {
        if (!window.googletag || !window.googletag.cmd) {
          if (attempt < 40) setTimeout(() => registerRewardedCloseCallback(attempt + 1), 250);
          return;
        }

        window.googletag.cmd.push(function () {
          try {
            if (!window.googletag.pubads) return;
            window.googletag.pubads().addEventListener("rewardedSlotClosed", function (event) {
              const slotPath = event && event.slot && event.slot.getAdUnitPath ? event.slot.getAdUnitPath() : "";
              if (window.mgsRewardedClickInProgress && slotPath.indexOf("zout_rewarded") !== -1) {
                window.mgsCloseQuizAfterReward();
              }
            });
          } catch (err) {
            console.warn("Rewarded close callback registration failed", err);
          }
        });
      }
      registerRewardedCloseCallback();

      function updateQuizProgress() {
        const fill = document.getElementById("quiz-progress-fill");
        const progress = Math.min(100, Math.max(20, Math.round(((quizStep + 1) / Math.max(1, gateQuestionCount + 1)) * 100)));
        if (fill) fill.style.width = progress + "%";
      }

      let quizStepLock = false;
      const gateQuestionCount = 1;

      function showGateFinal() {
        const loadingSlide = document.querySelector(".aq-loading");
        if (loadingSlide) loadingSlide.style.display = "none";
        const finalSlide = document.querySelector(".aq-final");
        if (finalSlide) finalSlide.style.display = "block";
        const phoneInput = document.getElementById("mgs-cf-sms-phone");
        if (phoneInput && !phoneInput.dataset.mgsMaskBound) {
          phoneInput.dataset.mgsMaskBound = "1";
          phoneInput.addEventListener("input", function () { this.value = formatSmsPhone(this.value); });
        }
        updateQuizProgress();
      }

      function nextQuizStep() {
        const currentSlide = document.querySelector('.aq-slide[data-step="' + quizStep + '"]');
        if (currentSlide) currentSlide.style.display = "none";
        quizStep++;

        if (quizStep < gateQuestionCount) {
          const nextSlide = document.querySelector('.aq-slide[data-step="' + quizStep + '"]');
          if (nextSlide) nextSlide.style.display = "flex";
          updateQuizProgress();
        } else {
          const loadingSlide = document.querySelector(".aq-loading");
          if (gateConfig.skipLoading) {
            showGateFinal();
          } else if (loadingSlide) {
            loadingSlide.style.display = "block";
            setTimeout(showGateFinal, Math.max(0, gateConfig.loadingMs || 0));
          }
        }
      }

      function initQuiz() {
        const quizContainer = document.getElementById("quiz-container");
        if (quizContainer) {
          quizContainer.style.display = "flex";
          lockScroll();
          updateQuizProgress();
        }
        loadGeoIndicator();

        if (!rewardedButtonClass) {
          
        }
      }

      document.addEventListener("click", function (e) {
        if (isQuizClosed) return;

        const skipButton = e.target && e.target.closest ? e.target.closest("#mgs-cf-sms-skip") : null;
        if (skipButton) {
          e.preventDefault();
          continueSmsWithoutLead();
          return;
        }

        const answerButton = e.target && e.target.closest ? e.target.closest(".aq-answer") : null;
        if (answerButton) {
          if (quizStepLock) return;
          quizStepLock = true;
          answerButton.style.background = "#075e54";
          answerButton.style.color = "white";
          const currentSlide = document.querySelector('.aq-slide[data-step="' + quizStep + '"]');
          if (currentSlide) {
            currentSlide.querySelectorAll(".aq-answer").forEach(btn => btn.style.pointerEvents = "none");
          }
          setTimeout(function () {
            nextQuizStep();
            quizStepLock = false;
          }, 500);
        }

        const ctaButton = e.target && e.target.closest ? e.target.closest("#aq-cta") : null;
        if (ctaButton) {
          e.preventDefault();
          if (smsConfig.enabled && !smsLeadCaptured) {
            submitSmsLead(ctaButton);
            return;
          }
          applyRewardedButtonClass(ctaButton);
          window.mgsRewardedClickInProgress = ctaButton.classList.contains("av-rewarded");
          if (quizAlreadyClosed) return;
          const safeCloseQuiz = window.mgsCloseQuizAfterReward;

          if (!ctaButton.classList.contains("av-rewarded")) {
            setTimeout(safeCloseQuiz, 1200);
          }

          if (!rewardedButtonClass) {
            
          }
        }
      });
    