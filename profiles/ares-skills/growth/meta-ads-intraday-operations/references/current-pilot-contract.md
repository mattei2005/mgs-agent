# Contrato atual do piloto Meta Ads intraday

Este arquivo preserva literalmente os blocos operacionais extraídos do `SKILL.md` em 2026-07-13. Ele é canônico para o estado atual; identificadores legados citados como compatibilidade não reativam fluxos removidos.

## Escopo atual do piloto

```text
Campo                         | Valor
------------------------------|------------------------------------------------------------
Operação                      | OpenzedFinanzas-CC-ES
Conta piloto                  | 1356770869843984
Canal                         | Messenger
Nível de ação                 | Campaign somente
Cortes intraday               | R1-R4 a cada 30 minutos, com 2 checkpoints consecutivos, via cron determinístico
Reativação 00:30              | Somente `paused_by_ares_rule`; pausas humanas/históricas/saturadas/hold/unknown são bloqueadas
Budget referência             | USD 300/dia; 20% (USD 60/dia) reservado para teste de criativos
Carência TEST                 | Nome contém TEST => não pausar/excluir por 3 dias
Log intraday                  | Só quando houver ação/erro; resumido no canal dedicado
Write                         | Desabilitado até aprovação explícita de Rodolfo
```

## Estrutura canônica

```text
/root/mgs-agent/data/ares/meta-ads/accounts/      # configs por conta
/root/mgs-agent/data/ares/meta-ads/operations/    # configs por operação país+vertical
/root/mgs-agent/data/ares/meta-ads/rules/         # rulesets versionados R1-R4 + política de reativação 00:30
/root/mgs-agent/data/ares/meta-ads/state/         # carência TEST, exclusões, estado local
/root/mgs-agent/data/ares/meta-ads/cache/         # cache para reduzir chamadas Meta API
/root/mgs-agent/data/ares/meta-ads/audit/         # logs auditáveis
/root/mgs-agent/data/ares/meta-ads/reports/       # relatórios
/root/mgs-agent/data/ares/meta-ads/permissions/   # permissionamento/guardrails
```

Scripts iniciais / cron:

```text
/root/mgs-agent/scripts/ares-meta-common.py
/root/mgs-agent/scripts/ares-meta-auth-check.py
/root/mgs-agent/scripts/ares-meta-intraday-runner.py
/root/mgs-agent/scripts/ares-meta-cron-runner.py                 # intraday v2 + reativação segura 00:30 dry-run/no-write
/root/mgs-agent/scripts/ares-meta-token-expiry-alert.py          # watchdog de expiração do Token Meta API
/root/.hermes/profiles/ares/scripts/ares-meta-intraday-cron.sh   # wrapper Hermes script-only
/root/.hermes/profiles/ares/scripts/ares-meta-reactivate-all-cron.sh
/root/.hermes/profiles/ares/scripts/ares-meta-token-expiry-alert.sh
```


## Defaults v2 aprovados — OpenzedFinanzas-CC-ES / Europa / USD

```text
Regra | Condição                                                                 | Persistência | Ação
------|--------------------------------------------------------------------------|-------------|-------------------
R1    | MO = 0 e spend >= USD 4.00                                                | 2 checkpoints| pausar campanha
R2    | MO = 1 e spend >= USD 4.50                                                | 2 checkpoints| pausar campanha
R3    | MO >= 2 + spend >= USD 6.00 + CPMO > USD 2.00                            | 2 checkpoints| pausar campanha
R4    | LOWEST_COST/LOWEST_COST_WITHOUT_CAP + MO >= 5 + spend >= 10 + CPMO > 1.75| 2 checkpoints| pausar campanha
R5    | removida: não existe reativação intraday por métrica congelada            | n/a          | nenhuma
```

Exceções: `COST_CAP` fica fora de todas as pausas por custo; TEST e learning com menos de 3 dias não acumulam persistência nem recebem ação. Às 00:30, reativar somente campanhas com proveniência persistida `paused_by_ares_rule`, respeitando quantidade ativa e projeção de gasto <= USD 300. HOA usa target CPMO USD 1.30 e replacement exige 2 dias ruins entre 3 dias completos; dia ruim requer CPMO > 1.30, spend >= USD 10 e MO >= 5. ROI Drip/Total é informativo e não aciona write.

## Métricas Meta atuais

```text
Métrica | Definição
--------|------------------------------------------------------------
MO      | actions.complete_registration
CPMO    | spend / MO
```

Em operações Europa/GDPR, `MO/CPMO` são a métrica primária do intraday porque a informação de subscribe pode não aparecer de forma confiável na Meta. Se `MO = 0`, `CPMO` fica nulo/não comparável.

Para operações fora da Europa onde subscribe é confiável, usar mapping separado de `subs/CPS` conforme operação específica, sem misturar com o ruleset Europa.


## Checklist para avanço de fase

```text
Fase | Critério
-----|-----------------------------------------------------------------
0    | Estrutura local criada e validada
1    | Token lido do 1Password sem exposição e conta lida read-only
2    | Métrica CPS mapeada nos insights Meta
3    | R1-R4 v2 aprovadas por Rodolfo e rodando dry-run com persistência
4    | Canal Discord de log configurado
5    | Controlled-write aprovado explicitamente
```

