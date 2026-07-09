# MGS Chat Funnels — WordPress global sem drift visual

## Contexto operacional

Quando `/chat/...` é aberto para WordPress global (`wp_head`, `wp_body_open`, `wp_footer`), o chat passa a herdar CSS/JS de tema, WPCode, Ad Inserter, Imagify, Elements, plugins de tracking etc. Isso é desejado para GTM/pixels/Yoast, mas **não autoriza alterar o visual do chat**.

Correção explícita do Rodolfo: abrir para WordPress significa liberar integrações globais, não redesenhar fonte/layout. O chat deve permanecer visualmente igual ao standalone anterior.

## Regra de implementação

1. Colocar `wp_head()` antes do CSS próprio do chat.
2. Manter CSS defensivo escopado em `#chat-container` e descendentes.
3. Usar `!important` apenas para proteger valores originais, não para inventar UX nova.
4. Não transformar botões em full-width se o standalone original usa `max-width: 75%`, `float:right`, `align-items:flex-end`.
5. Não aumentar peso visual por “normalização”: se era `font-weight:500`, manter `500`; não trocar para `700` salvo pedido explícito.
6. Preservar `configs/*.json` por site. Deploy de layout/código deve ser code-only.
7. Manter UTM hardening com `data-mgs-target-url` e refresh em `pointerdown`, `touchstart`, `mousedown`, `focus`, `click`.

## Valores visuais de referência preservados

Para o template atual do MGS Chat Funnels:

```css
.button-container {
  margin-right: 18px !important;
  max-width: 75% !important;
  float: right !important;
  align-items: flex-end !important;
}

#chat-container button {
  font-size: 14px !important;
  font-family: "Roboto", sans-serif !important;
  font-weight: 500 !important;
  width: 100% !important;
}
```

Smoke test DOM esperado no OpenZed desktop:

```text
chat width: 780px
button width: ~619px
button container width: ~585px / max-width 75%
font: Roboto
font-size: 14px
font-weight: 500
box-sizing: content-box
alignment: flex-end
float: right
```

## Pitfall: emoji online esticado

Em Topfeed e Wantabrand, o emoji `🟢` em `#header-status` renderizou como oval esticado depois de herdar CSS/font stack global do WordPress. A solução durável é não depender do emoji para esse indicador. Renderizar texto `online agora` e criar a bolinha via pseudo-elemento CSS escopado:

```css
#header-status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

#header-status::before {
  content: "";
  width: 8px !important;
  height: 8px !important;
  min-width: 8px !important;
  max-width: 8px !important;
  min-height: 8px !important;
  max-height: 8px !important;
  display: inline-block !important;
  border-radius: 50% !important;
  background: #25d366 !important;
  flex: 0 0 8px !important;
  aspect-ratio: 1 / 1 !important;
}
```

Validação browser obrigatória:

```js
const e = document.querySelector('#header-status');
const s = getComputedStyle(e, '::before');
({ text: e.textContent.trim(), width: s.width, height: s.height, borderRadius: s.borderRadius, aspect: s.aspectRatio })
```

Esperado:

```text
text: online agora
width: 8px
height: 8px
borderRadius: 50%
aspect: 1 / 1
```

## Checklist final multi-site

Para cada domínio do rollout:

```text
layout_restore: max-width 75% + float right + font-weight 500 presentes
bad_fullwidth: width calc(100% - 36px) ausente
wp_global: GTM/Yoast/wp-includes/wp-json presente
utm_hard: refreshTrackedLinkHref + pointerdown presentes
configs: não sobrescritas
updater temporário: removido
```

Se o usuário mandar screenshot dizendo que “só dois ainda estão errados”, corrigir apenas os domínios citados quando possível; não redeployar todos por padrão.