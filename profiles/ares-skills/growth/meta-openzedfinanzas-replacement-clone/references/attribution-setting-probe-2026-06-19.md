# Attribution setting probe — Elena clone perfeito 7/1 — 2026-06-19

## Contexto

Após alinhamento com Zeus/Rodolfo, Ares testou a hipótese de que o rebuild manual estava usando `attribution_spec` legado e que a Meta poderia exigir `attribution_setting=7d_click_1d_view` e/ou `use_unified_attribution_setting=true` para criar adsets novos com a mesma atribuição da source Elena.

## GET source vs clone

Objetos:

```text
Source adset Elena | 120248940367380604
Clone adset 1-day  | 120248959249340604
```

Campos testados via GET explícito:

```text
Campo                              | Source GET                         | Clone GET
-----------------------------------|------------------------------------|-----------------------------
attribution_spec                    | 7-day click + 1-day view           | 1-day click
attribution_setting                 | erro: Tried accessing nonexisting field | erro: nonexisting field
use_unified_attribution_setting     | erro: Tried accessing nonexisting field | erro: nonexisting field
```

Conclusão: em Graph API v25.0 para este objeto/conta, `attribution_setting` e `use_unified_attribution_setting` não aparecem como campos de GET.

## Rebuild isolado de 1 adset PAUSED

Criada campaign temporária PAUSED e testadas variantes de `POST /adsets` usando a source Elena como base. A campaign temporária foi deletada/verificada depois.

Variantes testadas:

```text
Variante                          | Resultado
----------------------------------|------------------------------------------------
attribution_setting only           | falhou
attribution_setting + unified true | falhou
use_unified + attribution_spec 7/1 | falhou com 1885501
attribution_setting + spec 7/1     | falhou
```

Erro principal quando 7/1 entrou no payload:

```text
code/subcode | 100 / 1885501
Título       | El intervalo de atribución de visualización no es válido
Mensagem     | ... valores admitidos ... son (1, 0)
```

Audit:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-attribution-setting-isolated-probe-20260619T071500Z.json
```

## Conclusão operacional

A hipótese de campo alternativo (`attribution_setting=7d_click_1d_view` / `use_unified_attribution_setting`) foi testada e não resolveu no create manual via API v25.0. Não tratar `1-day click` como clone perfeito.

Próximo caminho para clone perfeito 7/1:

1. Continuar investigação de native/async copy/cópia interna Meta que preserve lineage.
2. Se native/async copy não for viável pela API pública/app tier, usar Ads Manager UI duplicate/automação browser como caminho de clone perfeito.
3. Só declarar clone perfeito quando GET dos adsets clonados retornar `attribution_spec=[7-day click, 1-day view]`.
