# WordPress plugin scaffold MVP — MGS Chat Funnels

Sessão de origem: criação do plugin `MGS Chat Funnels` após definir a skill `chat-funnel-vertical-country`.

## Decisão operacional

Para produção MGS, preferir plugin WordPress configurável em vez de HTML solto. HTML estático serve para prova de conceito, mas não escala bem para múltiplas combinações vertical+país.

## Estrutura MVP criada

```text
/root/mgs-agent/plugins/mgs-chat-funnels/
├── mgs-chat-funnels.php
├── README.md
├── assets/
│   ├── chat-funnels.css
│   └── chat-funnels.js
└── configs/
    ├── emp-br-01.json
    └── car-br-01.json
```

## Recursos do MVP

- Shortcode: `[mgs_chat_funnel id="EMP-BR-01"]`.
- Rota configurável por JSON: `/chat/emp/br1`, `/chat/car/br1`.
- Gate inicial com perguntas rápidas.
- Rewarded/interstitial com fallback imediato quando `showRewardedAds` não existe.
- Chat estilo WhatsApp com persona aleatória.
- Modo `cards` para vitrine de ofertas.
- Modo `sequential` para oferta por oferta com “não, mostre outra opção”.
- Preservação de UTMs via `mergeSourceParams`.
- Botão topo apontando para uma oferta aleatória com UTMs preservadas.
- Interface administrativa no WP Admin para autonomia do Rodolfo: menu `MGS Chats`, lista de configs, editor/salvamento de JSON, criação/remoção de chats, rota pública e shortcode visíveis.

## Requisito pós-correção — admin UI

O plugin estar ativo em `Installed Plugins` não é suficiente. Para este tipo de produto, o MVP só está completo quando Rodolfo consegue editar o funil pelo painel WordPress, sem tocar em código ou pedir novo deploy.

Validação mínima da UI:

```text
- Menu MGS Chats presente no admin.
- /wp-admin/admin.php?page=mgs-chat-funnels abre HTTP 200 autenticado.
- Editor carrega EMP-BR-01/CAR-BR-01 ou configs existentes.
- Save no-op retorna notice de sucesso.
- Rotas públicas continuam HTTP 200 depois do save.
```

## Pitfall validado — rewarded fallback

Não basta fazer:

```js
window.jbftag = window.jbftag || { cmd: [] };
window.jbftag.cmd.push(function () { ... });
```

Se o tag real não carregar e só existir o stub `{cmd: []}`, esse callback fica parado na fila e o usuário nunca sai do gate. O fallback correto é executar imediatamente quando `showRewardedAds` não existir:

```js
if (window.jbftag && window.jbftag.cmd && typeof window.jbftag.cmd.push === 'function' && typeof window.jbftag.showRewardedAds === 'function') {
  window.jbftag.cmd.push(runner);
} else {
  runner();
}
```

## Validação mínima antes de instalar em canário

```text
- node --check assets/chat-funnels.js
- python3 -m json.tool configs/*.json
- php -l mgs-chat-funnels.php em ambiente com PHP disponível
- zip -t do pacote final
- browser fixture EMP-BR: gate → chat → cards, UTMs preservadas
- browser fixture CAR-BR: gate → chat → sequential, recusa mostra próxima oferta
```

Se o host local não tiver `php`, validar `php -l` remotamente em um RunCloud com PHP sem expor credenciais.

## REPORT-INFRA

Ao criar/modificar o plugin, enviar `[REPORT-INFRA]` no canal correto de infra/alerts, não como resposta principal na thread de trabalho. Na thread, responder só resumo executivo e validações.
