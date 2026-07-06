---
name: chat-funnel-vertical-country
description: Use when Rodolfo asks to create, adapt, audit, or plan a MGS chat funnel by vertical and country, e.g. EMP-BR, CC-BR, CAR-BR. Covers WhatsApp-style fake chat flows, rewarded/interstitial ad gate, UTM preservation, offer sequencing/cards, WordPress plugin config, and QA checklist.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mgs, chat-funnel, wordpress, vertical-country, rewarded, rec, p1, funnel]
    related_skills: [wp-plugin-mass-operation]
---

# Chat Funnel por Vertical e País — MGS

## Overview

Use esta skill para criar chats/funnels MGS por combinação de **vertical + país**, como `EMP-BR`, `CC-BR`, `CAR-BR`, `LOAN-US`, `CC-MX`, etc.

O produto é um funil interativo estilo WhatsApp, geralmente composto por:

1. **Gate inicial** com 1–2 perguntas rápidas.
2. **Rewarded/interstitial ad** antes de liberar a experiência principal.
3. **Chat fake estilo WhatsApp** com persona dinâmica.
4. **Perguntas de qualificação** simples.
5. **Ofertas finais** em modo cards ou sequencial.
6. **Links P1/oferta** com UTMs preservadas.

Regra executiva: para teste isolado, HTML pode servir. Para produção MGS escalável, preferir **plugin WordPress configurável** em vez de HTML solto — mas, quando o chat depende do wrapper JBF/Ciro, a rota pública deve renderizar um HTML standalone limpo e respeitar o contrato do wrapper.

## Quando usar

- Rodolfo pedir “cria um chat EMP-BR”, “faz um chat CC-BR”, “monta fluxo de financiamento CAR-BR”.
- Rodolfo enviar HTML/URL de referência de chat e pedir para entender/adaptar.
- Precisar transformar um chat estático em config/plugin WordPress.
- Precisar comparar modelos de fluxo: cards finais vs ofertas sequenciais.
- Precisar definir schema de chat por vertical/país antes de implementar.

Não usar para:

- REC/P1 editorial comum sem chat/funnel.
- Campanhas Meta/Google; isso é Growth/Ares.
- Criativos/imagens; isso é Hera, salvo texto/estrutura do funil.

## Naming canônico

Formato curto:

```text
<VERTICAL>-<PAÍS>
```

Exemplos:

```text
EMP-BR   Empréstimo pessoal Brasil
CC-BR    Cartão de crédito Brasil
CAR-BR   Financiamento de veículo Brasil
LOAN-US  Personal loan Estados Unidos
CC-MX    Tarjeta de crédito México
```

Para variantes:

```text
EMP-BR-01
EMP-BR-02
CAR-BR-BV-FIRST
CC-BR-CARDS
```

Rotas recomendadas:

```text
/chat/emp/br1
/chat/emp/br2
/chat/cc/br1
/chat/car/br1
```

Ou shortcode/plugin:

```text
[mgs_chat_funnel id="EMP-BR-01"]
[mgs_chat_funnel id="CAR-BR-01"]
```

## Arquitetura recomendada

### Para produção

Preferir plugin WordPress, por exemplo `MGS Chat Funnels`, onde cada chat é uma configuração editável por interface administrativa. **Não basta o plugin aparecer em Installed Plugins**: Rodolfo precisa ter autonomia para editar textos, perguntas, ofertas, links, rotas e modo do funil no WP Admin, sem depender de ZIP, arquivo JSON manual ou Zeus.

Requisito mínimo de produção:

```text
- Menu próprio no WP Admin, ex.: MGS Chats
- Lista de chats/configs existentes
- Criar novo chat
- Editar/salvar config com validação
- Remover chat
### Para produção

Preferir plugin WordPress, por exemplo `MGS Chat Funnels`, onde cada chat é uma configuração:

```json
{
  "id": "EMP-BR-01",
  "vertical": "emp",
  "country": "br",
  "language": "pt-BR",
  "route": "/chat/emp/br1",
  "theme": "whatsapp",
  "persona_role": "Consultor de Empréstimo",
  "mode": "cards",
  "rewarded_enabled": true,
  "utm_passthrough": true,
  "gate_questions": [],
  "chat_questions": [],
  "offers": []
}
```

Vantagens do plugin:

- evita drift entre HTMLs soltos;
- centraliza conteúdo, rotas, persona, ofertas e links finais;
- permite editar ofertas/textos por config;
- reduz risco em escala multi-vertical/multi-país;
- facilita QA e rollback.

Limite importante: se houver wrapper JBF/Ciro, **não centralizar nem inventar configuração de ads no plugin**. Auctions, rewarded, interstitial, bids, timeout/fallback e inventário pertencem ao wrapper/adserver. O plugin só entrega o HTML limpo, `window.tags`, `gpt.js`, wrapper e os pontos de chamada que o HTML de referência já usa.

Requisito de UX do admin: a configuração deve ficar por trás de uma interface humana. A tela principal precisa ter campos e ações de gestor de tráfego — criar novo chat, duplicar escolhendo novo ID e pasta/URL, excluir, abrir URL pública, editar gate/chat/persona/ofertas e ver relatórios. Não usar JSON bruto nem strings com separadores como interface principal; JSON só em seção avançada.

### Para teste rápido

HTML estático é aceitável somente quando:

- for prova de conceito única;
- não houver integração de leads;
- não houver necessidade de reaproveitamento;
- Rodolfo pedir explicitamente arquivo isolado.

Mesmo em HTML, manter schema mental de config para facilitar migração ao plugin.

## Estrutura padrão do funil

```text
Entrada na página
  ↓
Gate inicial
  ↓
Loading/oferta encontrada
  ↓
Rewarded/interstitial ou fallback
  ↓
Chat WhatsApp fake
  ↓
Perguntas de qualificação
  ↓
Ofertas finais
  ↓
P1/oferta com UTMs preservadas
```

## Gate inicial

Objetivo: aquecer o usuário e preparar inventário de anúncio antes do chat principal.

Para produção em plugin/admin, o gate precisa ser configurável por campo humano. Padrão validado com Rodolfo: pergunta 1 é obrigatória e não pode ser removida/ocultada; perguntas seguintes podem ter toggle de exibir/ocultar no admin. O template público deve renderizar slides do gate dinamicamente a partir da config ativa e usar contagem dinâmica (`gateQuestionCount`), nunca assumir que sempre existem exatamente 2 perguntas. Ver `references/car-br-gate-admin-and-wrapper-domain.md`.

Boas perguntas por vertical:

```text
EMP-BR
- Qual valor você precisa?
- Você quer quitar dívidas ou realizar um sonho?

CC-BR
- Qual limite você procura?
- Você já possui cartão de crédito?

CAR-BR
- Você já tem um carro?
- Qual tipo de veículo quer financiar?

LOAN-US
- How much do you need?
- What is the loan purpose?
```

Padrão visual:

```text
[pergunta curta]
[2–3 botões]
[loading]
“Oferta encontrada!”
“Um especialista/consultor foi identificado para te atender agora.”
[CTA: VER OFERTAS / TRANSFERIR PARA ESPECIALISTA]
```

## Chat principal

Persona dinâmica recomendada:

```text
Maria, João, Juliana, José, Fernanda, Carlos, Olivia, Lucas, Camilla, Pedro
```

Header:

```text
[Nome] • [Cargo por vertical]
🟢 online agora
```

Cargos por vertical:

```text
EMP-BR  Consultor de Empréstimo
CC-BR   Consultor de Cartões
CAR-BR  Especialista em Financiamentos
```

Mensagem inicial:

```text
Olá! Eu sou [Nome].
Sou [cargo] e estou aqui para te ajudar a encontrar a melhor opção para o seu perfil.
Vamos começar?
```

## Modos de oferta

### Modo `cards`

Mostra 3 ofertas de uma vez.

Usar quando:

- a intenção é dar sensação de escolha rápida;
- as ofertas são equivalentes;
- o usuário deve comparar opções;
- Rodolfo apontar uma referência onde as respostas do chat **não ramificam** e todas convergem para o mesmo bloco final.

Exemplos validados: `fincfrog.com/chat/emp/br2` e referência CAR-BR tipo `fmybc.com/chat/car/br/`.

```text
“Encontrei 3 ofertas exclusivas para você!”
[Card Nubank]
[Card C6 Bank]
[Card Banco BV]
```

Para CAR-BR no padrão de cards de veículo, o card deve ter campos humanos: imagem do carro, nome do carro, texto abaixo do nome, texto verde abaixo e URL final. O bloco pré-card também deve ser editável por campos humanos separados: mensagem de busca (`🔍 Estou pesquisando...`), mensagem de ofertas encontradas e mensagem de instrução. Não usar “Mensagens da oferta” nem fluxo Oferta 1 → recusa → Oferta 2 quando a referência for convergente. Ver `references/car-br-card-offer-convergent-flow.md`.

### Modo `sequential`

Mostra uma oferta por vez, com “sim” ou “mostrar outra opção”.

Usar quando:

- a intenção é simular atendimento humano;
- existe ordem de prioridade por EPC/ROI;
- quer forçar microdecisões.

Exemplo validado: `index_car_br.zip` / `CAR-BR`.

```text
Oferta 1
- Sim, quero simular →
- Não, mostre outra opção
  ↓
Oferta 2
- Sim, quero ver as condições →
- Não, mostre outra opção
  ↓
Oferta 3 fallback
- Sim, quero conhecer →
```

Recomendação padrão: usar `sequential` quando houver ranking claro de ofertas. Usar `cards` quando a página for mais vitrine/comparador.

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

## Rota standalone vs página WordPress

Para rotas públicas `/chat/...` que precisam imitar `index.html`, o plugin pode servir a rota, mas a saída deve ser HTML standalone:

```text
- sem wp_head()
- sem wp_footer()
- sem Yoast
- sem tema
- sem admin bar
- sem Contact Form 7/jQuery/WP scripts
- CSS/JS do chat inline ou controlado pelo próprio renderer
- gpt.js direto no head
- wrapper direto no head
- window.tags antes do wrapper
```

Se a resposta HTML contém “Page not found”, Yoast, `wp-includes/js`, `admin-bar`, tema ou plugins do WP, ainda não está equivalente ao `index.html` do Ciro.


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
- [ ] Testar com UTMs na URL.
- [ ] Testar mobile viewport.
- [ ] Verificar console sem erro crítico.
- [ ] Validar pixel/eventos se aplicável.
- [ ] Para troca de ofertas/textos em sites já instalados: validar em cada domínio HTTP 200 + rota correta + 3 URLs esperadas + 3 textos novos + ausência dos textos antigos; depois fazer pelo menos um smoke test real no navegador até o CTA e confirmar passthrough de UTM.
- [ ] Se usar wrapper JBF/Ciro: confirmar `window.tags`, `gpt.js`, wrapper, `window.jbftag`, slot criado, e distinguir `unfilled` de falha de render.
- [ ] Se for plugin WordPress de produção, validar menu/admin UI: página admin HTTP 200, configs carregadas, save no-op funcionando, rota pública standalone e shortcode exibidos.

## Referências canônicas desta skill

- `references/jbf-ciro-wrapper-contract.md` — contrato de integração ads para chats baseados em `index.html` do Ciro/JBF: plugin só controla contexto do chat; wrapper controla auctions/rewarded/interstitial/fill; inclui checklist de paridade literal quando Rodolfo pedir “100% igual”.
- `references/examples.md` — análise dos exemplos EMP-BR e CAR-BR.
- `references/config-schema.md` — schema sugerido para plugin/config.
- `references/wp-plugin-scaffold-mvp.md` — padrão MVP validado para plugin WordPress `MGS Chat Funnels`, incluindo estrutura, validações e pitfalls de rota standalone + contrato do wrapper JBF/Ciro.
- `references/wp-plugin-human-admin-ui.md` — padrão de admin humano para gestor de tráfego: criar, duplicar, excluir, editar campos e ofertas por blocos/repeaters, sem exigir JSON ou pipes.
- `references/car-br-card-offer-convergent-flow.md` — padrão CAR-BR convergente inspirado em `fmybc`: perguntas sem ramificação real, resposta vira balão do usuário, e bloco final mostra 3 cards de veículos com `image/name/subtitle/bank/url`.
- `references/car-br-gate-admin-and-wrapper-domain.md` — lições do rollout CAR-BR: pergunta 1 obrigatória + pergunta 2 com toggle, renderização dinâmica do gate, prefill/persistência de `ad_domain` por slug do site e QA de clique real.
- `templates/chat-funnel-config.json` — template inicial para novo chat.

## Pitfalls

1. **HTML solto escala mal.** Um ou dois chats tudo bem; dezenas viram drift de texto, tracking e rewarded.
2. **Perguntas não personalizam sozinhas.** Se as respostas não mudam a oferta, tratar como qualificação psicológica, não lógica real.
3. **Rewarded sem fallback derruba conversão.** Se o anúncio não carregar, liberar o chat.
4. **Links sem UTM quebram atribuição.** Sempre usar passthrough.
5. **Cards vs sequential muda a psicologia.** Cards = escolha rápida; sequential = atendimento humano e prioridade de oferta.
6. **Não coletar lead sem política clara.** Nome/telefone/CPF/email exigem armazenamento, consentimento e QA de integração.
7. **Não misturar vertical/país no slug.** `EMP-BR` e `EMP-US` podem ter textos, compliance e ofertas diferentes.
8. **Admin de WordPress não pode parecer ferramenta de dev.** Rodolfo rejeitou editor principal em JSON e textarea de ofertas com `|`. Para produção, criar interface de gestor de tráfego: campos humanos, botões de criar/duplicar/excluir, URL do chat visível, relatório/inventário, e ofertas como blocos/repeaters com campos separados. JSON bruto só em avançado/debug.
9. **Falas pré-card também são produto editável.** Em CAR-BR convergente, Rodolfo espera ver a linha de busca antes das ofertas e poder editar as 3 frases pré-card no admin. Não deixe essas frases hardcoded ou só no JSON bruto; e não crie uma etapa sem botões que impeça o avanço para os cards.
10. **Gate/quiz precisa tolerar clique rápido e wrapper silencioso.** No template Ciro/JBF, não deixe `quizStepLock` descartar o clique do segundo passo depois de desabilitar os botões; se usar lock, aplique antes de desabilitar e libere após a transição. O CTA final não pode depender só do callback do rewarded: sempre incluir fallback determinístico para fechar o modal e liberar o chat.
11. **Gate não deve ficar hardcoded no HTML.** Se Rodolfo quer escolher quais perguntas aparecem, renderize slides do gate a partir da config e use contagem dinâmica. Pergunta 1 é obrigatória; pergunta 2+ pode ser toggled no admin.
12. **Domain do wrapper vazio confunde operação.** Mesmo que o renderer consiga inferir pelo host, o admin deve mostrar e salvar a slug do site (`zuout`, `openzed`, etc.) para Rodolfo ver o wrapper correto sem editar JSON.

## Resposta padrão quando Rodolfo pedir um chat novo

Se Rodolfo disser “cria um chat EMP-BR”, responder com uma proposta curta antes de buildar se faltarem dados críticos:

```text
Vou criar como EMP-BR em modo [cards/sequential].
Preciso só das URLs/ofertas finais ou posso usar as 3 ofertas padrão atuais?
```

Se ele já deu ofertas, agir direto: criar config/HTML/plugin conforme escopo e validar fluxo real.

## Verificação final

- [ ] Skill carregada antes de criar/auditar chat.
- [ ] Vertical-país identificado.
- [ ] Referência usada explicitamente.
- [ ] Fluxo mapeado em gate + chat + ofertas.
- [ ] UTMs preservadas.
- [ ] Rewarded tem fallback.
- [ ] Links finais testados.
- [ ] Se criou/modificou plugin/script/config/data, fazer REPORT-INFRA no canal correto de infra/alerts e manter a thread de trabalho com resumo executivo curto.
