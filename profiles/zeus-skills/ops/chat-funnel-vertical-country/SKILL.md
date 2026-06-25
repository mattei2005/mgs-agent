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

Regra executiva: para teste isolado, HTML pode servir. Para produção MGS escalável, preferir **plugin WordPress configurável** em vez de HTML solto.

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
- centraliza tracking, rewarded, UTM e fallback;
- permite editar ofertas/textos por config;
- reduz risco em escala multi-vertical/multi-país;
- facilita QA e rollback.

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
- o usuário deve comparar opções.

Exemplo validado: `fincfrog.com/chat/emp/br2`.

```text
“Encontrei 3 ofertas exclusivas para você!”
[Card Nubank]
[Card C6 Bank]
[Card Banco BV]
```

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

## Rewarded/interstitial

Padrão:

1. Carregar/requestar rewarded no background durante o gate.
2. No CTA final do gate, tentar `showRewardedAds`.
3. Se a função não existir ou falhar, liberar o chat como fallback.
4. Nunca deixar usuário preso sem saída.

Checklist:

```text
- requestRewardAds chamado no init do gate
- showRewardedAds chamado no CTA
- callback fecha modal e chama o chat
- fallback fecha modal se rewarded não existir
- gate não reabre depois de fechado
```

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
- [ ] Fallback se anúncio não carregar.

Depois de implementar:

- [ ] Testar caminho principal completo.
- [ ] Testar cada CTA final.
- [ ] Testar com UTMs na URL.
- [ ] Testar mobile viewport.
- [ ] Verificar console sem erro crítico.
- [ ] Validar pixel/eventos se aplicável.
- [ ] Validar rewarded/interstitial ou fallback.

## Referências canônicas desta skill

- `references/examples.md` — análise dos exemplos EMP-BR e CAR-BR.
- `references/config-schema.md` — schema sugerido para plugin/config.
- `templates/chat-funnel-config.json` — template inicial para novo chat.

## Pitfalls

1. **HTML solto escala mal.** Um ou dois chats tudo bem; dezenas viram drift de texto, tracking e rewarded.
2. **Perguntas não personalizam sozinhas.** Se as respostas não mudam a oferta, tratar como qualificação psicológica, não lógica real.
3. **Rewarded sem fallback derruba conversão.** Se o anúncio não carregar, liberar o chat.
4. **Links sem UTM quebram atribuição.** Sempre usar passthrough.
5. **Cards vs sequential muda a psicologia.** Cards = escolha rápida; sequential = atendimento humano e prioridade de oferta.
6. **Não coletar lead sem política clara.** Nome/telefone/CPF/email exigem armazenamento, consentimento e QA de integração.
7. **Não misturar vertical/país no slug.** `EMP-BR` e `EMP-US` podem ter textos, compliance e ofertas diferentes.

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
- [ ] Se criou/modificou plugin/script/config/data, fazer REPORT-INFRA e atualizar inventário.
