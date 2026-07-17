## SEÇÃO D — Hardening de Monitors em Produção (checklist obrigatório)

Lições da sessão de auditoria 02/05/2026 — aplicar a todo monitor novo ou existente:

### 0. Cron Control Plane — inventário vivo antes de otimizar

Antes de propor mudanças em crons MGS, gere/consulte o inventário vivo:

```bash
/root/mgs-agent/scripts/cron-control-plane.py --json | jq .
/root/mgs-agent/scripts/cron-control-plane.py --write-doc
```

O documento canônico é `/root/mgs-agent/docs/CRONS.md`. Ele deve listar frequência, script, owner, risco, uso de `flock` e último sinal de log. Ver detalhes em `references/cron-control-plane.md`.

Regras operacionais:
- Fazer backup do crontab antes de qualquer edição.
- Editar crontab via arquivo intermediário validado e aplicar com `crontab <file>`; nunca usar `cmd | python3 <<EOF` nem heredoc dentro de command substitution para gerar/aplicar crontab, porque stdin collisions podem corromper ou apagar entradas.
- Mostrar diff antes/depois quando a mudança for operacionalmente relevante.
- Remover linhas comentadas `DEPRECATED` quando já houver substituto e arquivo em `scripts/deprecated/`.
- Todo cron MGS deve usar `flock -n` para evitar execução paralela.
- Frequência nunca pode ser menor que o runtime p95 do job; se runtime > 60% do intervalo, aumentar intervalo ou otimizar rota antes de reduzir cadência.
- O watchdog de logs deve calcular tolerância pela agenda real, não por um limite diário genérico: jobs diários usam 36h, semanais 8 dias e mensais 32 dias. A janela diária de 36h cobre mudança de horário no mesmo dia sem mascarar a perda de mais de um ciclo.
- Agendas recorrentes escritas como lista explícita de minutos (`4,14,24,34,44,54`) podem cair no fallback diário de um watchdog que só reconhece `*/5`, `*/15` e horário fixo. Após instalar qualquer lista/range, executar o watchdog em `--dry-run` e exigir que a tolerância reflita a cadência real; adicionar override exato ou parser geral antes de considerar o monitor protegido.
- Um state writer atômico dentro de um diretório compartilhado existente, como `data/`, deve aplicar `0600` ao state/temp e preservar o modo do diretório pai. Use `0700` apenas quando o próprio writer criar um pai privado ausente; nunca faça `chmod 0700` indiscriminado no diretório compartilhado para proteger um único state file.
- Crons recorrentes devem ser escalonados por minuto de início para evitar colisões óbvias: não usar `*/N` por padrão em jobs novos; preferir offsets/listas explícitas (`3-58/5`, `6,14,22...`) e checar o calendário contra root crontab + Hermes cron antes de aplicar.
- Quando Rodolfo pedir um horário “se estiver livre”, expandir também agendas recorrentes (`*/5`, `*/15`, listas e ranges), não apenas procurar uma linha diária exatamente naquele horário. Um minuto como `11:45` pode estar ocupado por vários jobs wildcard mesmo sem existir `45 11 * * *`. Se houver colisão, não alterar silenciosamente: informar o job conflitante e oferecer somente horários próximos já verificados como livres.
- Para jobs lentos de fontes externas (DTR/ChatPion/browser/API pesada), usar lock próprio e schedule com folga mínima de 2 minutos acima do runtime medido.
- Após mudar crontab/scripts de cron, rodar `infra-discovery.sh` e registrar em `events-audit.jsonl`.

### 1. flock — Proteger contra execuções paralelas

Sem flock, crons `*/5` ou `*/15` podem sobrepor quando o monitor demora mais que o intervalo (ex: timeout de rede).

```bash
# Cron entry com flock:
*/15 * * * * flock -n /tmp/monitor-NOME.lock /root/mgs-agent/scripts/monitor-NOME.sh >> /root/mgs-agent/logs/monitor-NOME.log 2>&1
```

`-n` = não bloqueia (pula a execução se lock estiver ocupado). Sem `-n`, execuções empilham.

**7 crons MGS com flock (aplicado 02/05/2026):** sync-souls, monitor-auto-push, check-pending-reports, monitor-service-restarts, monitor-tool-loops, track-article-cost, cleanup-zombie-sessions.

### 2. --max-time em todo curl

Sem `--max-time`, um webhook Discord lento ou rede instável trava o script indefinidamente, bloqueando o flock e impedindo execuções subsequentes.

```bash
# OBRIGATORIO em qualquer curl para webhook ou API externa:
curl -s -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "$payload" \
  --max-time 15 >/dev/null
```

**3 monitors corrigidos (02/05/2026):** monitor-tool-loops, monitor-anthropic-cost, monitor-service-restarts.

### 3. Logrotate — Nunca deixar logs crescer sem controle

Sem rotação, logs de crons `*/5` ou `*/15` crescem 100-200 linhas/hora. `monitor-service-restarts.log` atingiu 4.2 MB em semanas.

Config em `/etc/logrotate.d/mgs-agent` (criado 02/05/2026):
```
/root/mgs-agent/logs/*.log {
    daily
    maxsize 10M
    rotate 14
    compress
    delaycompress
    copytruncate
    missingok
    notifempty
}
```

`copytruncate` = trunca o log original sem restart do processo (safe para crons). `delaycompress` = mantém o log do dia anterior descomprimido (útil para debug imediato).

### 4. Heurística de frequência vs erros consecutivos

Detectar só erros consecutivos não é suficiente. Cloudflare e similares retornam HTTP 200 em páginas de challenge — o monitor precisa checar frequência também.

```python
# Adicionado em monitor-tool-loops.py (Patch 7, 01/05/2026):
# browser_navigate > 15 em 30 turns = alerta de loop
# Independente de estar retornando 200
```

---
## SEÇÃO E — Bug History: Regras Universais para Monitors com State File

Lessons learned 2026-04-27 (`check-pending-reports.sh` loop de ~120 msgs) e hardening de 2026-07-14:

1. **Detectar mudança SEM atualizar estado = loop garantido.** Antes do curl, persistir uma intenção/outbox de entrega. Só mover o item para o estado final (`resolved`) após HTTP 2xx; em falha, manter o alerta aberto e registrar a tentativa para retry.
2. **Separador `:` em arrays shell que carregam `agent:skill_name` causa colisão silenciosa** — usar `|`.
3. **`declare -A RESOLVED_DEDUP`** para dedup dentro de uma execução.
4. **Sempre fazer fixture/mock + dry-run manual** após qualquer modificação em monitor com state file. A fixture deve provar transição, retry após falha HTTP e ausência de efeitos no estado produtivo.
5. **Rotular pelo que é realmente verificado.** Um monitor que compara filesystem com `infra-inventory.json` detecta “skill não inventariada”; ele não pode afirmar “sem REPORT-INFRA” sem consultar uma fonte de registro do report.
6. **Ausência transitória não vira alerta imediato.** Exigir pelo menos duas leituras/execuções consecutivas ausentes, ou uma confirmação equivalente em snapshot estável, antes do POST. Se o registro reaparecer, limpar o candidato e registrar supressão.
7. **Evidência Git precisa ser específica do item.** Não usar simplesmente o último commit global que tocou o inventário. Buscar o commit que introduziu/removeu a entrada (`git log -S... -- data/infra-inventory.json`) ou declarar apenas “registro validado” quando não houver commit específico.

---
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
## Exemplo real — monitor-auto-push.sh

Padrão de log real detectado:
```
[2026-04-26T16:27:40-04:00] auto-push START commit=e286604 msg="..."
[2026-04-26T16:27:41-04:00] auto-push OK commit=e286604
```

Adaptação dos padrões no template:
- START pattern: `auto-push START`
- OK pattern: `auto-push OK commit=${commit}`
- id extraído via: `grep -oP 'commit=\K[a-f0-9]+'`
- Arquivo em: `/root/mgs-agent/scripts/monitor-auto-push.sh`
- State em: `/root/mgs-agent/data/auto-push-monitor.json`
- Cron: `*/15 * * * *`
