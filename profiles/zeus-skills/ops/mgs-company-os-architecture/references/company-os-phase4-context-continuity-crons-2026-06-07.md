# Company OS Phase 4 — continuidade de contexto, blocos e CRONS

Sessão: 2026-06-07
Contexto: revisão sequencial da Fase 4 da reestruturação MGS OS.

## Lições operacionais

1. Continuidade de thread longa
   - Em thread já aberta de reestruturação, uma mensagem curta como “Ok”, “continue” ou “vamos continuar” deve herdar o contexto do bloco anterior e do reply citado.
   - Não tratar como novo assunto e não renomear a thread. O objetivo da thread persiste até Rodolfo finalizar ou mudar explicitamente o assunto.

2. Sequência de blocos da Fase 4
   - Depois de cada bloco concluído, reportar status executivo com arquivo, validação, secret scan, audit log, auto-push, HEAD=origin e repo limpo.
   - Se Rodolfo aprovar/mandar continuar, executar o próximo bloco recomendado sem replanejar.
   - Após o Bloco 7 (`docs/CRONS.md`), o próximo passo é fechar a Fase 4 atualizando `docs/mgs-os-restructure-plan.md` e definir o gate da Fase 5.

3. CRONS.md é documento gerado
   - `docs/CRONS.md` é regenerado por `scripts/cron-control-plane.py` a partir do root crontab real.
   - Se uma informação do CRONS.md estiver errada/ausente, corrigir primeiro os metadados em `cron-control-plane.py` e regenerar o documento.
   - Não editar crontab/runtime durante revisão documental salvo autorização explícita.

4. Validação mínima usada
   - Confirmar total de crons ativos.
   - Confirmar que todos os crons usam flock.
   - Confirmar ausência de `não classificado` e `Sem descrição cadastrada`.
   - Rodar `git diff --check` e secret scan apenas das linhas adicionadas/diff.
   - Registrar evento em `logs/events-audit.jsonl` e verificar auto-push/HEAD=origin.

## Correções capturadas

- `cleanup-zombie-sessions.sh` não usa mais regra simples de 30 min; descrição correta: última atividade real + grace padrão de 180 minutos.
- `hermes-news-explainer.py` deve ser classificado como baixo/médio: consulta Discord e pode postar explicação automática.
- `monitor-webshare-status.sh` deve ser classificado como baixo: consulta status público e alerta Discord se anomalia.
