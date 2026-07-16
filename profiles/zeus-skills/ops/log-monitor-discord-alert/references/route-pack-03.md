## Cron entry

```bash
# Adicionar ao crontab root (sem modificar entradas existentes)
(crontab -l 2>/dev/null; echo "*/15 * * * * /root/mgs-agent/scripts/monitor-NOME.sh >> /root/mgs-agent/logs/monitor-NOME.log 2>&1") | crontab -
```

---
## Validação pós-criação

```bash
# 1. Permissões
chmod +x /root/mgs-agent/scripts/monitor-NOME.sh
ls -la /root/mgs-agent/scripts/monitor-NOME.sh
# Esperado: -rwxr-xr-x

# 2. Dry-run manual
bash /root/mgs-agent/scripts/monitor-NOME.sh
# Esperado: "OK: zero falhas" + sem Discord enviado

# 3. State file populado
jq . /root/mgs-agent/data/NOME-monitor.json
# Esperado: last_check com timestamp, consecutive_failures=0

# 4. Cron ativo
crontab -l | grep monitor-NOME
```
## Triage operacional de alertas já disparados

Quando Rodolfo pedir para "resolver um por um" alertas de Discord/cron/infra, não assumir que todos ainda estão ativos. Fazer triagem read-only primeiro e classificar cada alerta como **ativo**, **resolvido**, **histórico**, **state-corruption** ou **teste/layout** antes de mexer em scripts. Após incidente de disco cheio/ENOSPC, seguir `references/cron-enospc-recovery.md`: validar JSONs de state, reconstruir `service-restart-state.json` se zerado, rodar scripts em modo dry-run/manual seguro e limpar o estado do stale monitor com uma execução real quando `resolved=N`.

Checklist validado:

```bash
# Estado atual do monitor e últimos eventos
tail -80 /root/mgs-agent/logs/monitor-NOME.log
jq . /root/mgs-agent/data/NOME-state.json 2>/dev/null || true

# Se for script shell, validar sintaxe de todos os monitors tocados
bash -n /root/mgs-agent/scripts/monitor-NOME.sh

# Executar manualmente só quando for seguro/idempotente; usar --dry-run quando existir
/root/mgs-agent/scripts/monitor-NOME.sh --dry-run
/root/mgs-agent/scripts/monitor-NOME.sh >> /root/mgs-agent/logs/monitor-NOME.log 2>&1

# Confirmar resolução pelo log/state após a execução
tail -20 /root/mgs-agent/logs/monitor-NOME.log
```

Padrão de resposta para o CEO: tabela curta com `Item | Status agora | Decisão`. Separar claramente pendências deliberadas (ex: update Hermes em outro tópico) de problemas resolvidos. Se um erro apareceu em log mas `bash -n` e execução real passam depois, reportar como "não reproduzido no estado atual" e citar a validação feita, sem inventar causa.

Para alertas Discord com muitos itens comparáveis, o próprio script deve renderizar blocos monoespaçados alinhados. Em volume alto, agregar por entidade sem esconder o estado operacional: uma linha por template, contagens separadas por cor/status e todos os IDs afetados com idade individual (`ID(dias)`). Não despejar uma linha completa por mensagem quando isso gerar dezenas de milhares de caracteres; preservar o detalhe bruto no state/live source e identificar claramente que a tabela é agregada. Dividir em blocos independentes abaixo do limite do Discord, repetindo cabeçalho e delimitadores. Validar o renderer contra o state real: totais por cor, quantidade de registros agregados, presença das três classes, tamanho dos blocos e fechamento dos delimitadores.

No alerta diário de templates SB, o canal operacional canônico é `#broadcast-templates` (ID `1522487422510694450`). Não chamar o canal de “SB Utility”; esse termo pode descrever o processo, mas não é o nome do canal. `#cron-temp-templates` é separado e serve a crons temporários/infra. Considerar somente produção ativa (`PAGES > 0`), excluindo `Teste-*` e `NAO/NÃO USAR`. Reportar imediatamente **roxo** (`INVALID_FORMAT`/`ERROR`) e **vermelho** (`REJECTED`), além do **cinza** persistente por pelo menos 2 dias. Roxo é diagnóstico e nunca troca global automática. Vermelho só pode ser descrito como troca automática ativa após confirmar scheduler `enabled/scheduled` e execução real recente; existência de código red-only ou job pausado não equivale a automação ativa. Enquanto o executor estiver pausado, manter vermelho no relatório como pendência acionável.

---
## Atualizar infra-inventory.json

Após criar os artefatos, atualizar manualmente 3 seções do inventário:

```json
// crons: adicionar
{
  "entry": "*/15 * * * * /root/mgs-agent/scripts/monitor-NOME.sh >> /root/mgs-agent/logs/monitor-NOME.log 2>&1",
  "description": "Monitor de ..."
}

// scripts: adicionar
{
  "path": "/root/mgs-agent/scripts/monitor-NOME.sh",
  "size_bytes": N,
  "modified_at": "TIMESTAMP",
  "description": "..."
}

// data_files: adicionar
{
  "path": "/root/mgs-agent/data/NOME-monitor.json",
  "description": "Estado do monitor. Campos: last_check, consecutive_failures, last_alert_sent, last_failure_details.",
  "modified_at": "TIMESTAMP"
}
```

---
