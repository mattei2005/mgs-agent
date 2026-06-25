# Schema de configuração — Chat Funnel MGS

Este schema é a base recomendada para plugin WordPress ou gerador de HTML estático.

## Campos principais

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
  "mode": "cards",
  "rewarded_enabled": true,
  "utm_passthrough": true,
  "tags": ["br", "emp", "rec"],
  "persona": {},
  "gate": {},
  "chat": {},
  "offers": []
}
```

## `mode`

```text
cards       Mostra todas as ofertas finais em cards.
sequential  Mostra oferta por oferta, com opção de recusar e ver próxima.
```

## `persona`

```json
{
  "names": ["Maria", "João", "Juliana", "José", "Fernanda", "Carlos", "Olivia", "Lucas", "Camilla", "Pedro"],
  "female_names": ["Maria", "Juliana", "Fernanda", "Olivia", "Camilla"],
  "male_names": ["João", "José", "Carlos", "Lucas", "Pedro"],
  "female_photos": [],
  "male_photos": [],
  "role": "Consultor de Empréstimo",
  "status": "🟢 online agora"
}
```

## `gate`

```json
{
  "enabled": true,
  "progress_steps": [20, 60, 100],
  "questions": [
    {
      "text": "💰 Qual valor você precisa?",
      "answers": [
        {"label": "R$ 500 a R$ 3.000", "value": "500-3000"},
        {"label": "R$ 3.000 a R$ 10.000", "value": "3000-10000"},
        {"label": "Acima de R$ 10.000", "value": "10000-plus"}
      ]
    }
  ],
  "loading_text": "🔍 Buscando a melhor oferta para você...",
  "final_icon": "💰",
  "final_title": "Oferta encontrada!",
  "final_subtitle": "Um consultor foi identificado para te atender agora.",
  "cta_label": "VER OFERTAS →",
  "footer_note": "✅ Análise gratuita e sem compromisso"
}
```

## `chat`

```json
{
  "intro": [
    "Olá! Eu sou {botName}. 💰",
    "Sou consultor de empréstimo pessoal e estou aqui para te ajudar a encontrar a melhor opção para o seu perfil.",
    "Vamos encontrar a oferta ideal para você?"
  ],
  "start_answers": ["✅ Vamos lá!", "👀 Quero conhecer as opções"],
  "questions": [
    {
      "text": "Para qual finalidade você precisa do empréstimo?",
      "answers": ["Quitar dívidas", "Realizar um sonho", "Emergência"]
    },
    {
      "text": "Você tem nome restrito no SPC/Serasa?",
      "answers": ["Sim, mas quero tentar mesmo assim", "Não, meu nome está limpo", "Não sei informar"]
    }
  ],
  "pre_offer_messages": [
    "🔍 Estou pesquisando as melhores opções para você..."
  ]
}
```

## `offers` para modo `cards`

```json
[
  {
    "name": "Nubank",
    "logo": "https://example.com/nubank.png",
    "subtitle": "Ver oferta",
    "target": "https://fincfrog.com/br-chat-emp-nubank/"
  },
  {
    "name": "C6 Bank",
    "logo": "https://example.com/c6.png",
    "subtitle": "Ver oferta",
    "target": "https://fincfrog.com/br-chat-emp-c6-bank/"
  }
]
```

## `offers` para modo `sequential`

```json
[
  {
    "name": "Banco BV",
    "messages": [
      "Aqui está uma ótima opção para você!",
      "O Banco BV é especialista em financiamento de veículos, com taxas a partir de 1,32% ao mês, prazo de até 60 meses e processo 100% digital."
    ],
    "accept_label": "Sim, quero simular →",
    "reject_label": "Não, mostre outra opção",
    "target": "https://fincpro.com/br-chat-car-banco-bv/"
  },
  {
    "name": "Santander Financiamentos",
    "messages": [
      "Encontrei outra opção incrível para você:",
      "O Santander Financiamentos tem décadas de experiência no mercado, taxas a partir de 1,39% ao mês e aprovação rápida."
    ],
    "accept_label": "Sim, quero ver as condições →",
    "reject_label": "Não, mostre outra opção",
    "target": "https://fincpro.com/br-chat-car-santander-financiamento/"
  },
  {
    "name": "Bradesco",
    "messages": [
      "Talvez esta seja a opção ideal para você:",
      "O Bradesco financia carros com até 12 anos de fabricação e permite financiar até 100% do valor do veículo."
    ],
    "accept_label": "Sim, quero conhecer →",
    "target": "https://fincpro.com/br-chat-car-bradesco-financiamento/"
  }
]
```

## Tracking obrigatório

- `utm_passthrough=true` por padrão.
- Preservar todos os parâmetros da URL de origem.
- Adicionar eventos Pixel/GA somente se Rodolfo pedir ou se o plugin já tiver padrão existente.
- Não expor IDs/secrets no frontend.

## Validações mínimas

```text
- JSON/config parseia sem erro.
- Todas as URLs finais respondem 200/3xx esperado.
- Todos os botões têm ação.
- O último caminho sequencial sempre tem CTA final.
- Rewarded tem fallback.
- Mobile viewport não corta CTA.
```
