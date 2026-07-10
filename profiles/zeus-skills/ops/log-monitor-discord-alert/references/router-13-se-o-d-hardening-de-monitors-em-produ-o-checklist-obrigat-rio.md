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
- Crons recorrentes devem ser escalonados por minuto de início para evitar colisões óbvias: não usar `*/N` por padrão em jobs novos; preferir offsets/listas explícitas (`3-58/5`, `6,14,22...`) e checar o calendário contra root crontab + Hermes cron antes de aplicar.
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
