## SEÇÃO F — Cron Control Plane e Smoke Tests

Para operações de inventário/reliability dos crons MGS, seguir o padrão em `references/cron-control-plane.md`.

Resumo operacional:
- Fazer backup de `crontab -l` antes de qualquer alteração.
- Usar temp file + `crontab <file>`; nunca heredoc dentro de command substitution para editar crontab.
- Todo cron MGS deve usar `flock -n` para evitar sobreposição.
- Criar/atualizar `docs/CRONS.md` via `cron-control-plane.py --write-doc`.
- Jobs destrutivos devem ter `--dry-run` antes de entrarem no smoke test.
- `cron-smoke-test.sh` deve executar jobs safe, rodar risky em dry-run e marcar skips por design.
- `monitor-cron-stale-logs.sh` deve alertar quando logs deixam de atualizar dentro da tolerância.
- Não deletar threads Discord automaticamente para economizar tokens: thread arquivada/parada custa zero e o histórico é valioso para auditoria.

Quando Rodolfo pedir apenas para **rever/listar `docs/CRONS.md` e dizer o que ainda dá para melhorar**, não aplicar mudanças automaticamente. Ler o documento canônico, listar todos os crons em tabela curta e separar: `urgente/bloqueante`, `melhoria menor/documental`, `aguardar ciclo real`. Melhorias típicas não bloqueantes após hardening: scripts ainda “não classificados” no control-plane, descrições desatualizadas no doc (ex: grace real diferente da descrição), jobs diários com log vazio porque ainda não rodaram no ciclo real, ou `Último log` antigo que será corrigido na próxima regeneração.

---
