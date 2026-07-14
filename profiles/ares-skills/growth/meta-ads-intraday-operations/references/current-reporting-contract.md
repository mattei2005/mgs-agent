# Contrato atual de relatórios Meta Ads intraday

Este arquivo preserva literalmente o contrato de logs extraído do `SKILL.md` em 2026-07-13.

## Formato de log dos crons

Quando configurar ou ajustar crons Meta Ads do Ares (`intraday v2` e `reativação segura 00:30`), o log operacional deve ir para o canal `logs-aquisicao` quando configurado para a operação. O formato preferido por Rodolfo é uma tabela curta, com título contendo conta, dia e horário da conta.

Durante `read_only/dry_run`, relatórios de gestão devem ser tratados como recomendações auditáveis: cada checkpoint/recomendação relevante deve ter thread própria no `logs-aquisicao` para Rodolfo responder a ação manual tomada. Depois que write/autonomia for explicitamente liberado, não abrir thread para cada ação por padrão; executar, validar e postar log consolidado.

```text
<Nome da conta> — <YYYY-MM-DD> — <HH:MM TZ> — <Tipo do cron>

ID REC                 | Nome da campanha              | PG ID    | Início     | Spend | MO | CPMO | Ação que eu tomaria | Motivo
-----------------------|-------------------------------|----------|------------|-------|----|------|---------------------|-------
REC-20260621-0124-001  | Elena Santana - ES - ESP - 009| pg_22091 | 20/06/2026 | 6.21  | 0  |      | OBSERVAR            | Learning < 3d; R1 acionou
```

Regras de formatação:
- Extrair `PG ID` do nome da campanha quando houver padrão `(pg_12345)`.
- `País/Vertical`: país do nome da campanha quando disponível + vertical da operação.
- `Regra usada`: `R1`–`R4` no intraday v2; `reativar-00:30-paused_by_ares_rule` no cron diário; `HOA`/razão no gestor HOA.
- `Status atual`: `effective_status` atual da campanha.
- `Ação que eu tomaria`: no dry-run, usar verbos simulados (`pausaria`, `reativaria`, `manteria`, `clonaria/substituiria`, `ignoraria`). Nunca executar write nessa fase.
- Se não houver ação candidata nem erro, o cron fica silencioso e salva apenas audit JSON local, salvo HOA configurado para `always_output_each_checkpoint`.
- Sempre declarar `dry_run_no_write` no audit enquanto controlled-write não estiver aprovado; não precisa poluir a tabela principal com essa coluna.
- Respostas curtas de Rodolfo na thread devem mapear para state/audit: `feito`, `ignorar`, `segurar 1 checkpoint`, `pausei`, `reativei`, `não mexer nessa campanha`.

