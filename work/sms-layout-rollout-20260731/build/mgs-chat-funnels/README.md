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
/chat-sms/car/br1 -> variante com captura de nome/telefone antes do chat
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
- Variante SMS por chat, com um gestor/lista fixo independentemente das UTMs.
- Captura local de nome, telefone, campanha e status de entrega ao SMS Funnel.
- Menus administrativos de Leads, Relatórios, exportação CSV e URLs SMS por gestor.

## Contrato da variante SMS

1. O chat com `sms_enabled=true` mostra Nome e Telefone na tela final do gate.
2. O botão grava o lead no WordPress e envia apenas `{ name, phone }` ao endpoint `add-lead` do gestor escolhido.
3. O fluxo de anúncio e o chat original só continuam quando o SMS Funnel responde com sucesso.
4. URLs de SMS são salvas em opção privada do WordPress e nunca são expostas no HTML público.
5. A rota comum `/chat/...` continua sem formulário quando `sms_enabled` está desativado.

## Próximas fases

- Admin UI dentro do WordPress.
- Import/export de configs.
- Eventos Pixel/GA configuráveis.
- A/B por peso de ofertas.
- Logs de clique agregados sem PII.
