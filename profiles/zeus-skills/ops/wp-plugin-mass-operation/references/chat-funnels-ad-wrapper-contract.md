# MGS Chat Funnels — contrato de anúncios do wrapper JBF/Ciro

Use esta referência quando criar, migrar, instalar ou debugar chats/funnels que dependem do wrapper `assets.jbfdigital.com.br` para rewarded/interstitial/display ads.

## Lição principal

Não transformar a implementação interna de ads do HTML estático em configuração de produto no plugin. O plugin deve renderizar o chat e expor os pontos mínimos que o wrapper espera; a lógica de auctions, rewarded, interstitial, bidding e fallback pertence ao wrapper.

Erro observado: ao ler um `index.html` estático com `for (let i = 0; i < 5; i++) requestRewardAds()`, o agente interpretou o `5` como parâmetro configurável e criou campo `Quantidade de auctions`. Isso chamou a tag 5x e invadiu a responsabilidade do wrapper. Correção: remover loop/campo/config e chamar `requestRewardAds()` uma vez.

## Contrato mínimo do HTML original

O plugin deve preservar estes pontos:

1. Carregar GPT:
   ```html
   <script async src="https://securepubads.g.doubleclick.net/tag/js/gpt.js"></script>
   ```

2. Carregar o wrapper JBF:
   ```html
   <script defer src="https://assets.jbfdigital.com.br/assets/{company}/{domain}/{company}_{domain}.builder.js"></script>
   ```
   Exemplo: `https://assets.jbfdigital.com.br/assets/digital-trust/openzed/digital-trust_openzed.builder.js`

3. Definir tags globais antes/ao redor do wrapper:
   ```js
   window.tags = ["br", "car", "rec"];
   ```
   Não basta guardar `tags` dentro de JSON de configuração do plugin se o wrapper espera `window.tags`.

4. Preload rewarded: chamar uma vez, sem loop:
   ```js
   window.jbftag = window.jbftag || { cmd: [] };
   window.jbftag.cmd.push(function () {
     if (window.jbftag.requestRewardAds) {
       window.jbftag.requestRewardAds();
     }
   });
   ```

5. CTA final: deixar o wrapper controlar rewarded/interstitial:
   ```js
   window.jbftag.cmd.push(function () {
     if (window.jbftag.showRewardedAds) {
       window.jbftag.showRewardedAds(callback);
     } else {
       callback();
     }
   });
   ```

6. Display/refresh no meio do chat: quando o HTML original cria slot inline, replicar exatamente o contrato:
   ```js
   const adBanner = document.createElement("div");
   adBanner.innerHTML = `<div></div>`;
   adBanner.classList.add("ad-unit");
   adBanner.classList.add("ad");
   adBanner.dataset.position = "top";
   chatBox.appendChild(adBanner);
   if (window.onInfinitePostLoaded) window.onInfinitePostLoaded();
   ```

## O que NÃO colocar no plugin

- Campo `Quantidade de auctions`.
- Campo `Timeout do anúncio` como controle de rewarded/interstitial.
- Loop chamando `requestRewardAds()` várias vezes.
- Config própria de bidding, auctions, fallback ou interstitial.
- Reinterpretação da implementação do wrapper como lógica configurável do plugin.

O plugin pode ter `company` e `domain` apenas para montar a URL do wrapper, ou um campo explícito `wrapper_url`. Todo o resto de ads fica com o wrapper.

## Método de comparação obrigatório

Quando o usuário fornecer um `index.html` de referência do Ciro/time técnico:

1. Extrair scripts do `<head>`: `gpt.js`, wrapper, `window.tags`.
2. Extrair funções globais/contratos usados por ads: `window.jbftag`, `requestRewardAds`, `showRewardedAds`, `onInfinitePostLoaded`, `.ad-unit.ad`, `data-position`.
3. Comparar contra o plugin antes de alterar.
4. Só transformar em configuração os dados de negócio do chat: perguntas, respostas, persona, URLs finais, tags, company/domain/wrapper URL.
5. Não transformar detalhes técnicos do wrapper em campos do admin.

## Verificação ad-hoc recomendada

Após deploy, validar no HTML remoto:

- contém `gpt.js`;
- contém wrapper correto `{company}_{domain}.builder.js`;
- contém `window.tags`;
- não contém `rewarded_auctions`, `rewarded_timeout_ms`, `Quantidade de auctions` ou `Timeout do anúncio`;
- no browser, `window.jbftag` existe e o fluxo cria safeframes/slots quando acionado.

Diferenciar: “wrapper carregou” não prova contrato completo. A prova mínima precisa incluir `window.tags`, chamada única de rewarded e slot inline/`onInfinitePostLoaded` quando o HTML original usa isso.

## Comunicação com Rodolfo

Em resumo executivo para Rodolfo, não colar bloco `[REPORT-INFRA]` no final. Se houver registro infra obrigatório, processar pelo canal/procedimento certo e manter a resposta normal limpa.