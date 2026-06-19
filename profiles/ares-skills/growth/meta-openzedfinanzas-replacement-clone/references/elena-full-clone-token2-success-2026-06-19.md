# Elena full clone / TOKEN2 success — 2026-06-19

## Contexto

Rodolfo corrigiu o token Meta adicionando escopos de Página/Messenger além dos escopos de ads. Antes disso, `POST /ads` falhava com `code=31/subcode=3858385` (`Autentica tu cuenta`) mesmo com a conta/página aparentemente normais no BM/Ads Manager.

## Permissões do token que destravaram `POST /ads`

Manter no token operacional:

```text
read_insights
pages_show_list
ads_management
ads_read
business_management
instagram_basic
pages_read_engagement
pages_read_user_content
pages_manage_engagement
pages_manage_ads
pages_messaging
pages_manage_metadata
pages_manage_posts
```

As permissões críticas adicionadas foram:

```text
pages_manage_ads
pages_messaging
pages_manage_metadata
pages_manage_posts
```

Aprendizado: campaign/adset podem criar só com `ads_management`/ad account access, mas o nível `ad` com Página + Messenger + creative/template pode exigir escopos de Página/Messenger.

## Teste TOKEN2 — campaign/adset/3 ads

Criado e validado:

```text
Objeto      | ID                  | Status final após teste
------------|---------------------|--------------------------
Campaign    | 120248959079740604  | PAUSED
Adset       | 120248959080020604  | ACTIVE, CAMPAIGN_PAUSED
Ad 1        | 120248959080480604  | ACTIVE, CAMPAIGN_PAUSED
Ad 2        | 120248959081550604  | ACTIVE, CAMPAIGN_PAUSED
Ad 3        | 120248959082080604  | ACTIVE, CAMPAIGN_PAUSED
```

Audits:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-new-token-3ads-probe-20260619T053500Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-activate-all-20260619T055000Z.json
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-pause-campaign-20260619T060000Z.json
```

## Clone full Elena bem-sucedido

Pedido: clonar a campanha `Elena Santana - ES - ESP - (pg_22091) - 4` do jeito que ela é.

Resultado:

```text
Source campaign        | 120248940367540604
Clone campaign         | 120248959247790604
Nome clone             | Elena Santana - ES - ESP - (pg_22091) - 4 - FULLCLONE - 20260620
Status                 | PAUSED
Effective status       | PAUSED
Budget                 | USD 100/dia (copiado da source por pedido de clone fiel)
Adsets                 | 2
Ads                    | 6
```

Mapeamento:

```text
Source adset          | Clone adset
----------------------|---------------------
120248940367380604    | 120248959249340604
120248940367340604    | 120248959251300604
```

```text
Source ad             | Clone ad             | Creative usado
----------------------|----------------------|----------------------
120248940367400604    | 120248959252850604   | 2416649352137237
120248940367500604    | 120248959254280604   | 1710921573663723
120248940367560604    | 120248959255230604   | 27262287090090407
120248940367300604    | 120248959255850604   | 1424497936364679
120248940367420604    | 120248959256470604   | 1165937042364589
120248940367480604    | 120248959256960604   | 1679278363326933
```

Audit:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/elena-full-clone-20260619T061500Z.json
```

## Divergência inevitável validada

Source Elena usa `7-day click + 1-day view`, mas Meta rejeitou essa janela em criação nova com `code=100/subcode=1885501` e só aceitou `1-day click`.

```text
Campo        | Source                    | Clone novo aceito
-------------|---------------------------|------------------
Attribution  | 7-day click + 1-day view  | 1-day click
```

Regra: se Rodolfo pedir clone fiel, tentar primeiro a attribution da source; se Meta retornar `1885501`, repetir com `CLICK_THROUGH 1` e reportar explicitamente essa divergência.

## Modos oficiais após o teste

```text
Modo                         | Uso
-----------------------------|------------------------------------------------
Replacement Ares padrão       | 1 campaign / 1 adset / 3 ads / USD 25 / PAUSED
Clone fiel/source mirror      | copiar estrutura real da source: adsets/ads/budget se pedido "do jeito que é"
```

Não misturar os modos. Se Rodolfo pedir "clone essa campanha do jeito que ela é", usar clone fiel. Se pedir replacement operacional, usar padrão Ares 1x3.

## Guardrails

- Tudo nasce `PAUSED`, salvo ordem explícita para ativar.
- Ativar/pausar via API já foi validado, mas continua exigindo ordem explícita.
- Não arquivar/deletar loser antes de clone validado.
- Não expor token no chat/log.
