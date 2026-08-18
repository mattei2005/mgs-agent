## Regras de decisão de campanha

Regra inicial discutida para CPA ponderado:

```text
HOA ponderado = Hoje 50% + Ontem 30% + D-2 20%
```

Decisões atuais para OpenzedFinanzas/Europa:

- Intraday R1-R4 e HOA são camadas separadas e devem coexistir inicialmente; R5 foi removida e não pode ser reativada por referência histórica.
- HOA roda nos checkpoints `08:00`, `12:00`, `15:00`, `18:00`, `22:00` no timezone da conta.
- Relatório Discord do HOA deve ser legível para gestor: cabeçalho humano com horário no fuso da conta, `ID REC` com 3 dígitos, campanhas ordenadas por sufixo `001...`, sem Meta ID/Campaign ID no report normal. Ao mesclar campanha viva + histórico de insights, ocultar `HIST` duplicado quando já existir linha viva (`ACTIVE`/`PAUSED`/`IN_PROCESS`/`WITH_ISSUES`) com o mesmo nome/número; manter duplicata técnica só em audit JSON.
- Europa/GDPR usa `MO=complete_registration` e `CPMO=spend/MO`, não CPS/subs.
- No contrato atual de OpenzedFinanzas, “dia ruim” para replacement exige dia completo, `CPMO > USD 1.30`, gasto mínimo `USD 10.00` e `MO >= 5`; replacement requer 2 dias ruins entre 3 dias completos.
- Budget total de referência: `USD 300/dia`; 20% (`USD 60/dia`) reservado para testes de criativos novos.
- CPMO alvo atual do HOA: `USD 1.30`. Em conflito, `meta-ads-intraday-operations/references/current-pilot-contract.md` vence esta referência.
- Campanha nova nunca deve ser criada com budget maior que `USD 25/dia` inicialmente.
- Replacement deve: mapear loser → identificar melhores criativos da conta inteira por menor CPMO nos últimos 3 dias → clonar campanha/adset/criativos do zero → validar clone → deletar a loser se a Meta/API permitir; se não permitir delete, arquivar. O clone deve usar a mesma página, mas pode usar criativo vencedor de outra página.
- Campanhas de replacement devem ser programadas para o dia seguinte, preferencialmente `01:00` no timezone da conta.
- Cada campanha nova deve ter exatamente 3 criativos.
- Se não houver espaço de budget para testes, não executar; avisar só no relatório final das 22h.
- Para controlled-write de duplicação/normalização em massa, primeiro validar o estado vivo e calcular `needed = target_count - current_count`; não criar campanhas extras quando a conta já está no alvo. Usar `references/meta-controlled-write-bulk-duplicates.md` para o padrão de auditoria, cleanup e verificação.
- Para remover bid cap em campanhas novas, usar `bid_strategy=LOWEST_COST_WITHOUT_CAP` no campaign e omitir `bid_amount` no adset; não tentar resolver apenas no adset.

Guardrails:

- Não cortar teste antes de janela mínima definida sem autorização.
- Exigir gasto mínimo/volume antes de avaliar criativo.
- Separar **pausar** de **substituir/replacement**.
- No começo o Ares recomenda; não executa automaticamente.
- Budget/billing nunca automáticos.
## Referências

- `references/cc-us-es-setup.md` — decisões iniciais da operação piloto CC_US_ES: Drive, taxonomia, ângulos, tamanhos e acesso via Service Account.
- `references/drive-review-duplicate-cleanup-and-00-review-closure.md` — fluxo para revisar/ajeitar pasta inteira no Drive, deduplicar, resolver OAuth delete, fechar `00_REVIEW` e preservar RAW.
