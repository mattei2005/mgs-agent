## Regras de clone

1. Clone deve ser criado PAUSED inicialmente, salvo autorização explícita para ACTIVE.
2. Start time deve ser o dia seguinte às `01:00` no timezone da conta; ao enviar em criação, converter com timezone real `Europe/Madrid` para ISO UTC `Z` (DST-aware), não usar offset fixo nem string local `+0200`.
3. Campaign daily budget nunca pode passar de `USD 25` inicialmente (`daily_budget=2500` cents).
4. Para clone-source/replacement, não começar com payload mínimo nem declarar campo “não encontrado”: primeiro fazer GET explícito completo da source e diff source-vs-payload nos níveis campaign/adset/ad.
5. Em conta Europa/UE de financeiro, adset pode exigir campos DSA/compliance diferentes de North America. Sempre puxar e copiar exatamente da source: `dsa_beneficiary`, `dsa_payor`, e qualquer campo com `dsa`, `beneficiary`, `payor`, `regulated`.
6. Selecionar exatamente 3 criativos vencedores da conta inteira, não só da campanha/página.
7. Ranking inicial de criativo vencedor: menor CPMO nos últimos 3 dias, com `spend >= USD 5` e `MO >= 2`.
8. Clone usa a mesma página/promoted object da loser, mas os criativos podem vir de outra campanha/página se forem vencedores da conta.
9. Depois do clone validado, loser deve ser deletada se a API permitir; se não permitir delete, arquivar/pausar.
10. Antes de reportar sucesso, validar com GET: campanha criada, status, budget, adsets e exatamente 3 ads.
11. Salvar audit em `/root/mgs-agent/data/ares/meta-ads/audit/clone/`.

### Checklist obrigatório antes de `POST /adsets` em EU/financeiro

```text
Campo / validação                         | Regra
------------------------------------------|------------------------------------------------------------
Source fields explícitos                   | Não confiar em default GET; ele esconde DSA/compliance
DSA                                         | GET `dsa_beneficiary` e `dsa_payor`; copiar string exata da API
Campaign category                          | Confirmar `FINANCIAL_PRODUCTS_SERVICES` e `special_ad_category_country`
Adset parity                               | Diff `optimization_goal`, `billing_event`, `destination_type`, `promoted_object`, `targeting`, `attribution_spec`
Campos graváveis ausentes                  | Listar `SÓ NA SOURCE` e `VALOR DIFERENTE` antes de escrever
Campos derivados                           | Não enviar `configured_status`, `effective_status`, `source_adset_id`
Execução                                   | Criar um objeto por vez, PAUSED, validar GET e parar no checkpoint
Falha `100/1487202`                        | Tratar como campo/regra compliance ausente; não isolar cegamente campos um por um
```

Detalhe de sessão DSA/1487202: `references/eu-dsa-adset-diagnostic-2026-06-19.md`.
Detalhe source mirror EU/financeiro, page permission e attribution blockers: `references/eu-finserv-source-mirror-and-adset-errors-2026-06-19.md`.
## Source mirror obrigatório antes de writes EU/financeiro

Antes de qualquer `POST /campaigns`, `/adsets`, `/adcreatives` ou `/ads` em campanhas EU/financeiro, rodar o mirror read-only:

```bash
/root/mgs-agent/scripts/ares-meta-source-mirror.py \
  --source-campaign-id <campaign_id> \
  --source-adset-id <adset_1> \
  --source-adset-id <adset_2> \
  --source-ad-id <winner_1> \
  --source-ad-id <winner_2> \
  --source-ad-id <winner_3> \
  --ads-count 3 \
  --daily-budget-usd 25
```

Regra aprendida com correção do Rodolfo: não testar payload mínimo nem reportar “não achei” campos sem antes fazer GET explícito e diff source-vs-payload. Default GET da Meta esconde campos de compliance.

Campos de compliance que devem ser confirmados por API e copiados exatamente no adset quando existirem:

```text
dsa_beneficiary
dsa_payor
regional_regulated_categories
special_ad_categories / special_ad_category_country
```

Para OpenzedFinanzas EU/Spain, valores observados nos adsets Patricia/Elena:

```json
{
  "dsa_beneficiary": "Openzed",
  "dsa_payor": "Openzed",
  "regional_regulated_categories": ["SPAIN_FINSERV", "VOLUNTARY_VERIFICATION"]
}
```

Pitfalls validados:
- `code=100/subcode=1487202` pode esconder erro de permissão de Página. Capturar raw HTTP body/headers; o corpo completo pode conter `error_user_title: El permiso de la página es insuficiente...`. Nesse caso, parar: precisa acesso de criação de anúncios na Página, não mais tentativa de campo.
- `code=100/subcode=1885501` em Elena indicou janela de atribuição inválida **no contexto novo incompleto**. Não trocar automaticamente para `(1,0)` quando a source UI/API mostra `7-day click + 1-day view`; isso é sinal de que a campanha/adset novo ainda não espelha o contexto da source. Primeiro corrigir paridade de campaign/adset (COST_CAP, bid_amount, `smart_promotion_type`, pacing, DSA/regional, promoted_object, targeting) e só mudar attribution se Rodolfo aprovar conscientemente um replacement não-fiel.
- Sempre deletar/verificar campaign parcial quando o adset falha e a campaign não será reutilizada no próximo checkpoint.
## Script canônico

```bash
/root/mgs-agent/scripts/ares-meta-replacement-clone.py \
  --account-id 1356770869843984 \
  --operation-id OpenzedFinanzas-CC-ES \
  --loser-campaign-id 120248290564280604 \
  --daily-budget-usd 25
```

Dry-run:

```bash
/root/mgs-agent/scripts/ares-meta-replacement-clone.py --dry-run
```
## Criativos vencedores do dry-run inicial

Dry-run real salvo em `/root/mgs-agent/data/ares/meta-ads/audit/clone/clone-dry-run-20260618T035853Z.json`:

```text
Source campaign                                 | Source ad ID        | Creative ID       | Spend | MO | CPMO
------------------------------------------------|---------------------|-------------------|-------|----|------
Patricia Flores - US - ESP - (pg_22069) - 4     | 120248290564590604  | 1878134753167706  | 9.36  | 7  | 1.34
Patricia Flores - US - ESP - (pg_22069) - 1     | 120248290297210604  | 1018755007258886  |107.96 |70  | 1.54
Patricia Flores - US - ESP - (pg_22069) - 3     | 120248290564610604  | 1829542905087157  |101.34 |58  | 1.75
```
