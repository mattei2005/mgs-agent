## Schema operacional mínimo

```json
{
  "id": "EMP-BR-01",
  "vertical": "emp",
  "country": "br",
  "language": "pt-BR",
  "route": "/chat/emp/br1",
  "title": "Chatbot Empréstimo Pessoal",
  "brand": "FincFrog",
  "theme": "whatsapp",
  "persona": {
    "names": ["Maria", "João", "Juliana", "José", "Fernanda", "Carlos", "Olivia", "Lucas", "Camilla", "Pedro"],
    "role": "Consultor de Empréstimo",
    "status": "🟢 online agora"
  },
  "tracking": {
    "utm_passthrough": true,
    "rewarded_enabled": true,
    "tags": ["br", "emp", "rec"]
  },
  "gate": {
    "questions": [],
    "loading_text": "Buscando a melhor oferta para você...",
    "final_title": "Oferta encontrada!",
    "final_subtitle": "Um consultor foi identificado para te atender agora.",
    "cta": "VER OFERTAS →"
  },
  "chat": {
    "intro_messages": [],
    "questions": [],
    "offer_mode": "cards",
    "offers": []
  }
}
```

## UTM e parâmetros

Sempre preservar os parâmetros da URL de origem nos links finais.

Padrão JS validado:

```js
function mergeSourceParams(targetUrl) {
  try {
    const url = new URL(targetUrl);
    const sourceParams = new URLSearchParams(window.location.search);
    sourceParams.forEach((value, key) => url.searchParams.set(key, value));
    return url.toString();
  } catch (e) {
    return targetUrl;
  }
}
```

Não remover nem sobrescrever UTMs sem motivo explícito.

## Contrato de ads com wrapper JBF/Ciro

Quando Rodolfo trouxer um `index.html` do Ciro/JBF como referência, trate o wrapper como dono da implementação de anúncios. Não crie camada própria no plugin para ads.

No admin, o campo `Domain do wrapper` deve vir pré-preenchido com a slug do site atual quando estiver vazio (ex.: `zuout.com` → `zuout`) e deve ser persistido no save humano. Em rollout multi-site, grave `ad_domain` explicitamente por domínio para evitar preview/confusão no painel. Ver `references/car-br-gate-admin-and-wrapper-domain.md`.

Contrato mínimo do HTML público:

```html
<script>window.tags = ["br", "car", "rec"];</script>
<script async src="https://securepubads.g.doubleclick.net/tag/js/gpt.js"></script>
<script defer src="https://assets.jbfdigital.com.br/assets/{company}/{domain}/{company}_{domain}.builder.js"></script>
```

No JS do chat, preserve apenas os pontos de chamada já existentes no HTML de referência:

```js
window.jbftag = window.jbftag || { cmd: [] };
window.jbftag.cmd.push(() => {
  if (window.jbftag.requestRewardAds) window.jbftag.requestRewardAds();
});

// No CTA final do gate:
window.jbftag.cmd.push(() => {
  if (window.jbftag.showRewardedAds) {
    window.jbftag.showRewardedAds(closeQuiz);
  } else {
    closeQuiz();
  }
});

// No ponto do banner inline:
const adBanner = document.createElement("div");
adBanner.innerHTML = `<div></div>`;
adBanner.classList.add("ad-unit", "ad");
adBanner.dataset.position = "top";
chatBox.appendChild(adBanner);
if (window.onInfinitePostLoaded) window.onInfinitePostLoaded();
```

Não adicionar no plugin/painel/config:

```text
- Quantidade de auctions
- rewarded_auctions
- rewarded_timeout_ms
- bids
- timeout/fallback próprio de ads
- checkbox “exigir anúncio” controlando lógica do wrapper
```

Se Rodolfo perguntar por que o anúncio não aparece, validar em browser/runtime e diferenciar:

```text
wrapper não carregou          problema de HTML/script/cache
window.jbftag sem funções     problema de wrapper
slot não criado               problema de ponto de chamada HTML/JS
slot criado com .unfilled     problema de fill/adserver/inventário, não de render do plugin
```

Para diagnóstico, inspecionar `.ad-unit.ad`, `data-requested`, `data-displayed`, classe `unfilled`, iframes e `googletag.pubads().getSlots()`.

## Rota WordPress aberta vs HTML isolado

Padrão MGS atual para `/chat/...`: a rota pública deve se comportar como URL normal do WordPress, herdando integrações globais do site. Mesmo quando o visual precisa parecer um HTML limpo de chat, o renderer deve permitir hooks globais como `wp_head()`, `wp_body_open()` e `wp_footer()` para WPCode/GTM/Yoast/pixels/scripts/plugins do site.

Use HTML totalmente isolado apenas quando Rodolfo pedir explicitamente paridade com arquivo estático isolado ou quando a integração de ads exigir isolamento técnico documentado. Nesse caso, declarar a troca: isolamento preserva paridade com `index.html`, mas não herda alterações globais do WordPress.

Para implementação e validação do padrão aberto, ver também `wp-plugin-mass-operation/references/wp-custom-plugin-public-routes-global-hooks.md`.

Se a resposta HTML contém “Page not found”, rota de tema/404 ou placeholders `{{...}}`, ainda não está correta.

## Checklist de criação

Antes de implementar:

- [ ] Identificar vertical e país: `EMP-BR`, `CC-BR`, `CAR-BR`.
- [ ] Definir objetivo do funil: REC interativo, P1, captação, oferta direta.
- [ ] Definir modo: `cards` ou `sequential`.
- [ ] Listar 2–3 perguntas de gate.
- [ ] Listar 2–3 perguntas de chat.
- [ ] Listar ofertas finais em ordem de prioridade.
- [ ] Confirmar URLs finais/P1.
- [ ] Confirmar brand/site/domínio.
- [ ] Confirmar se há rewarded/interstitial.

Durante implementação:

- [ ] Preservar UTMs.
- [ ] Mobile-first.
- [ ] Persona randômica funcional.
- [ ] Botões removem opções antigas após clique.
- [ ] Loading/typing indicator não trava.
- [ ] CTA externo abre URL certa.
- [ ] Se usar wrapper JBF/Ciro, não criar configuração própria de ads; copiar o contrato do `index.html` de referência.

Depois de implementar:

- [ ] Testar caminho principal completo com clique real: gate passo 1 → gate passo 2 quando habilitado → CTA final → chat principal → cards/oferta. HTTP 200 e presença de HTML não bastam.
- [ ] Se o gate tiver pergunta opcional, testar também o caminho com ela desabilitada: pergunta 1 → loading/final CTA → chat.
- [ ] Testar cada CTA final.
- [ ] Testar com UTMs na URL e validar o `href` final real de cada card/oferta no DOM e a URL após clique/navegação, não apenas a função de merge. Em rotas que herdam WordPress global, scripts externos podem alterar ou ler anchors antes do click; o renderer deve guardar `data-mgs-target-url` com URL base e reaplicar `mergeSourceParams` em eventos de preflight (`pointerdown`, `touchstart`, `mousedown`, `focus`) e `click` antes da navegação.
- [ ] Testar mobile viewport.
- [ ] Verificar console sem erro crítico.
- [ ] Validar pixel/eventos se aplicável.
- [ ] Para troca de ofertas/textos em sites já instalados: validar em cada domínio HTTP 200 + rota correta + 3 URLs esperadas + 3 textos novos + ausência dos textos antigos; depois fazer pelo menos um smoke test real no navegador até o CTA e confirmar passthrough de UTM.
- [ ] Se usar wrapper JBF/Ciro: confirmar `window.tags`, `gpt.js`, wrapper, `window.jbftag`, slot criado, e distinguir `unfilled` de falha de render.
- [ ] Se for plugin WordPress de produção, validar menu/admin UI: página admin HTTP 200, configs carregadas, save no-op funcionando, rota pública standalone e shortcode exibidos.

