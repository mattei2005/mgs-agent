# WP Global sem drift visual do chat

## Quando usar

Use esta referência em qualquer alteração do `MGS Chat Funnels` que abra rotas `/chat/...` para o WordPress global (`wp_head`, `wp_body_open`, `wp_footer`) ou que ajuste CSS após herdar tema/plugins do WordPress.

## Regra operacional

Abrir o chat para WordPress global **não autoriza redesenhar o chat**. O objetivo é herdar integrações globais do site — GTM, WPCode, Yoast, pixels, scripts e plugins — mantendo a aparência standalone original.

Correção explícita do Rodolfo nesta classe de tarefa:

> quando pedi para deixar aberto o WordPress, não era para mexer no layout/fonte escrita do chat; o chat era para permanecer o mesmo.

## Padrão correto

1. Colocar `wp_head()` antes do CSS próprio do chat.
2. Manter os valores visuais do template standalone original.
3. Usar CSS defensivo apenas para proteger esses valores contra CSS global do tema/plugins.
4. Escopar tudo no container do chat, preferencialmente `#chat-container ...`.
5. Usar `!important` apenas para preservar os valores originais, não para criar novo layout.
6. Validar por DOM/screenshot que o visual continua igual ao standalone e que WP global/UTM continuam ativos.

## Valores visuais que não devem ser alterados sem pedido explícito

Exemplo do padrão original validado:

```css
.button-container {
  margin-right: 18px;
  max-width: 75%;
  float: right;
  align-items: flex-end;
}

button {
  font-size: 14px;
  font-family: "Roboto", sans-serif;
  font-weight: 500;
  width: 100%;
}
```

Ao proteger contra CSS global, manter a forma original:

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

## Anti-padrões

Não fazer, salvo pedido explícito de redesign:

- transformar botões em full-width (`width: calc(100% - margens)` / `max-width:none`);
- trocar peso 500 por 700;
- alterar `float:right` para `float:none`;
- trocar `align-items:flex-end` por `stretch`;
- mudar box model/tamanhos de forma que o screenshot deixe de bater com o standalone;
- chamar “normalização” uma mudança de UX.

## Validação mínima

Para cada domínio atualizado:

- HTML público contém sinais de WP global (`googletagmanager.com/gtm.js`, Yoast/WP JSON/wp-includes etc.).
- HTML público contém hardening de UTM (`refreshTrackedLinkHref`, eventos de preflight como `pointerdown`).
- HTML público contém o CSS defensivo que preserva o layout original (`max-width: 75%`, `float:right`, `align-items:flex-end`, `font-weight:500`).
- HTML público **não** contém o CSS de redesign full-width indevido (`width: calc(100% - 36px)` quando esse não existia no standalone).
- Smoke test DOM em pelo menos um canário confirma: fonte Roboto, 14px, peso 500, botões alinhados como antes.

## Deploy seguro

Quando a mudança for só PHP/template/CSS/JS:

- fazer deploy **code-only**;
- nunca sobrescrever `configs/*.json` ambientais;
- se usar plugin temporário de updater, ativar o arquivo principal correto do updater e remover depois;
- validar que URLs de oferta continuam do domínio certo e que EMP/redirects compartilhados continuam como esperado.