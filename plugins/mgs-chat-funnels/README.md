# MGS Chat Funnels

Plugin WordPress configurável para chats/funnels por vertical + país.

## Objetivo

Renderizar funis estilo WhatsApp para combinações como:

- `EMP-BR`
- `CC-BR`
- `CAR-BR`
- `LOAN-US`

Cada funil é definido por JSON em `configs/*.json`.

## Uso por rota

O plugin intercepta rotas configuradas no JSON:

```text
/chat/emp/br1  -> EMP-BR-01
/chat/car/br1  -> CAR-BR-01
```

## Uso por shortcode

```text
[mgs_chat_funnel id="EMP-BR-01"]
[mgs_chat_funnel id="CAR-BR-01"]
```

## Estrutura

```text
mgs-chat-funnels.php          Main plugin
assets/chat-funnels.css       Layout WhatsApp + gate
assets/chat-funnels.js        Renderer/config runtime
configs/emp-br-01.json        Exemplo empréstimo BR em modo cards
configs/car-br-01.json        Exemplo financiamento BR em modo sequential
```

## Recursos MVP

- Gate inicial com 1–2 perguntas.
- Rewarded/interstitial com fallback.
- Persona aleatória.
- Chat estilo WhatsApp.
- Modo `cards`.
- Modo `sequential`.
- Preservação de UTMs nos links finais.
- Botão topo com oferta aleatória.

## Próximas fases

- Admin UI dentro do WordPress.
- Import/export de configs.
- Eventos Pixel/GA configuráveis.
- A/B por peso de ofertas.
- Logs de clique agregados sem PII.
