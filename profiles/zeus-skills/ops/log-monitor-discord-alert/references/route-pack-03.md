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

No fluxo fixed-30 ativo desde 2026-08-03, o canal operacional canônico é `#broadcast-templates` (ID `1522487422510694450`). O alerta diário legado de listas grandes (`sb-utility-gray-alerts`) deve permanecer pausado enquanto o executor `sb-broadcast-template-repair` estiver habilitado; não manter dois publishers concorrentes. O executor considera somente produção ativa (`PAGES > 0`), exatamente 30 mensagens, excluindo `Teste-*` e `NAO/NÃO USAR`.

Formato de alertas desse fluxo:
- transporte direto pelo bot Zeus, `content` vazio, sem mentions e sem criar thread;
- um embed de início por template realmente tocado;
- um embed de resultado positivo, concluído, sem progresso ou bloqueado após o ETA;
- um único digest diário compacto;
- mostrar template, páginas/vertical, contagens antes/depois por cor, ação, horário do Approval, ETA e próximo passo;
- não despejar IDs de todas as mensagens, copies completas, motivos repetidos nem paginação em várias mensagens;
- fingerprint por template ID + ciclo + evento + contagens para suprimir repetição;
- checker silencioso enquanto o ETA não venceu.

Pitfall validado no host MGS: `CRON_TZ=America/Sao_Paulo` aparece no root crontab, mas o pacote Ubuntu `cron 3.0pl1` observado continuou disparando pelo timezone do host (`America/New_York`). Isso fez `10 23 * * *` executar às `00:10 SP` durante EDT e o digest selecionar o dia recém-iniciado, retornando zero. Para rotinas que precisam fechar exatamente um dia de São Paulo, não depender de `CRON_TZ`: agendar no minuto desejado de todas as horas (`10 * * * *`) e usar um gate `--scheduled` dentro do script baseado em `ZoneInfo('America/Sao_Paulo')`, que só publica na hora SP pretendida. Manter backfill manual por data explícita e incluir as contagens/resumo no fingerprint diário, para que um digest vazio prematuro não suprima o resultado real posterior. Validar com fixture de virada de dia/DST, execução scheduled fora da hora (deve fazer skip) e readback do embed corrigido.

As cores são operacionais: template 30/30 verde é intocável; vermelho entra em troca em lote no nível do template; roxo sem vermelho entra em reset sem alteração visível + novo Approval; cinza aguarda ETA. Essa regra substitui o texto antigo que dizia que roxo era somente diagnóstico e que vermelho não tinha executor ativo. A distinção de atribuição permanece: roxo agregado não identifica a Page causal.

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
