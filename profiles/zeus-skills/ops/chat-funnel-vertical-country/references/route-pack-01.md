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
- Criativos/imagens; isso é agente legado, salvo texto/estrutura do funil.

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

