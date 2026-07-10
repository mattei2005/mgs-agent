# Segurador/Page Health — Discord Format + SB API Session Notes (2026-06-30)

Session-specific notes from Rodolfo's review of the first `#seguradores-pagina` alert mockups.

## Final approved Discord report format

Rodolfo approved a compact plain-text header plus one monospaced code block.

Use this shape for manual status reports and anomaly alerts:

````text
<@344196393512075265> ALERTA REAL — Relatório Segurador/Página

Domain: zytiva
User: disparoszytiva@gmail.com
Segurador: Dân Kbang
Período: 2026-06-29
Recorte: 20 páginas

```
Página                   PG ID            Ativa  Leads  Enviando
------------------------ ---------------- -----  ------ --------
Patricia Smith           796622570197092  sim       495 não
```
````

Do not include:

```text
- Company line;
- legend line;
- footer/timestamp line;
- page hyperlinks;
- Facebook URLs;
- Discord embeds;
- Markdown tables with pipes outside a code block.
```

Why:

```text
- Discord embeds made the table too narrow/cramped.
- Markdown tables looked visually poor.
- Facebook links generated unwanted preview cards.
- Code blocks keep columns aligned and readable.
```

When posting through Discord API, include `flags: 4` (`SUPPRESS_EMBEDS`) as a safety guard even when no URL is expected.

## Healthy-page guardrail

For production monitoring, do not send rows just because they are healthy.

```text
Ativa  Enviando  Leads vs baseline   Discord action
-----  --------  ------------------  ------------------------------
sim    sim       normal              silent; update state/log only
sim    sim       collapsed/stalled    alert RISCO
sim    não       below expected/zero  alert RISCO/CRÍTICO
não    qualquer  qualquer            alert CRÍTICO
sumiu  sumiu     known page missing   alert CRÍTICO
```

Manual reports requested by Rodolfo can include all pages, but autonomous recurring alerts should report exceptions only.

## SB Messenger report API lessons

The SmartBidding Messenger report can return `0` rows if queried for the new UTC/current day before data exists. Before posting an operational report, validate row count. If today returns 0 unexpectedly, query the last known complete day or the period requested by Rodolfo.

For authenticated in-browser fetches from Playwright, the SB dashboard keeps the API bearer token in `sessionStorage.ac`. Do not print it. Use it only inside browser context:

```javascript
const token = sessionStorage.getItem('ac');
await fetch('https://api.jbfdigital.com.br/report/messenger', {
  method: 'POST',
  headers: {
    'content-type': 'application/json',
    'authorization': 'Bearer ' + token
  },
  body: JSON.stringify(payload)
});
```

Direct `page.evaluate(fetch(...))` without the Authorization header can return `401 Unauthorized`, even while the UI itself is logged in.

## Validation before sending

Before posting to Discord, verify:

```text
- Meta /me/accounts returned pages for the segurador.
- SB report returned non-zero rows for the intended period, unless a zero-row period is explicitly the point of the alert.
- Number of Meta pages and matched SB pages are recorded.
- Domain/User came from SB rows, not from examples or placeholders.
- The message uses the approved code-block format.
```

If a bad/placeholder report was posted, send a corrected final message and clearly identify the final valid Message ID in the response to Rodolfo.
