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
