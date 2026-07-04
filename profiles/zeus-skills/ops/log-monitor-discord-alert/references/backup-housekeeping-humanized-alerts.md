# Backup housekeeping — alertas humanizados e validação segura

Use quando Rodolfo pedir para melhorar, testar ou explicar alertas de housekeeping de backups (`housekeeping-bak-cleanup.sh`).

## Aprendizado operacional

O alerta antigo mostrava `Backups preservados: 115`, mas esse número vinha apenas de `KEEP_COUNT` dos backups pequenos (`.bak/.backup/.old/.orig/~`). Backups grandes de update Hermes (`hermes-profiles-backup*.tar.gz`) são tratados em fluxo separado. Isso criou ambiguidade: o total físico preservado era `115 pequenos + 2 tarballs Hermes`.

## Layout recomendado do embed

Campos principais:

- `Host`
- `Retenção`
- `Status` — exemplo: `OK — baixo risco (somente backups antigos; canônicos preservados)`
- `Deletados` — exemplo: `9 arquivos / 0.15 MB`
- `Preservados` — exemplo: `115 pequenos + 2 tarballs Hermes`
- `Diretórios vazios`
- `Tipos deletados` — contagem por classe (`config.yaml.bak`, `auth.json.bak`, `SOUL.md.bak`, `hermes update tarball`, `outros backups`)
- `Amostra` — até 5 paths deletados, com `/root/` abreviado para `~/`
- `Log completo` — `/root/mgs-agent/logs/housekeeping.log`

## Regras de implementação

1. Não usar só `HERMES_UPDATE_BACKUP_KEEP_LATEST` no campo de preservados. Calcular o total real preservado:

```bash
HERMES_PRESERVED_COUNT=$(find /root/mgs-agent/reports/hermes-updates -type f -name 'hermes-profiles-backup*.tar.gz' 2>/dev/null | wc -l | tr -d ' ')
```

2. O campo `Preservados` deve explicitar as duas classes:

```bash
PRESERVED_LABEL="${KEEP_COUNT} pequenos + ${HERMES_PRESERVED_COUNT} tarballs Hermes"
```

3. Classificar deletados com `awk` ou arquivo temporário. Evitar este padrão dentro de command substitution:

```bash
awk ... | python3 - <<'PY'
...
PY
```

Esse formato é armadilha: o heredoc ocupa o stdin do Python, então o pipe pode não chegar ao script. Preferir `awk` puro ou passar dados via arquivo/argumento.

4. Para teste real sem mexer em backup operacional, criar arquivos de preview em `/tmp` na mesma família, com um antigo e um novo. O preserve-latest mantém o novo e deleta só o antigo:

```bash
rm -f /tmp/zeus-housekeeping-alert-preview.bak-old /tmp/zeus-housekeeping-alert-preview.bak-new
printf 'old preview housekeeping alert\n' > /tmp/zeus-housekeeping-alert-preview.bak-old
printf 'new preview housekeeping alert\n' > /tmp/zeus-housekeeping-alert-preview.bak-new
touch -d '20 days ago' /tmp/zeus-housekeeping-alert-preview.bak-old
touch -d '1 day ago' /tmp/zeus-housekeeping-alert-preview.bak-new
/root/mgs-agent/scripts/housekeeping-bak-cleanup.sh --dry-run
```

Depois da validação, execução real pode postar o alerta e deletar apenas o arquivo antigo de preview:

```bash
/root/mgs-agent/scripts/housekeeping-bak-cleanup.sh
rm -f /tmp/zeus-housekeeping-alert-preview.bak-new
```

5. Sempre validar antes de declarar concluído:

```bash
bash -n /root/mgs-agent/scripts/housekeeping-bak-cleanup.sh
/root/mgs-agent/scripts/housekeeping-bak-cleanup.sh --dry-run
python3 -m json.tool /root/mgs-agent/data/infra-inventory.json >/dev/null
```

6. Como é mudança em script/data de infra, atualizar `infra-inventory.json`, registrar `events-audit.jsonl` e postar `REPORT-INFRA` no canal correto antes de dizer que terminou.

## Pitfall de comunicação

Se Rodolfo perguntar “tá certo isso?” sobre um número no alerta, responder com a decomposição real e a fonte. Exemplo:

- `115` = backups pequenos preservados
- `2` = tarballs Hermes preservados à parte
- total físico = `117`

Depois propor corrigir a legenda do alerta, não defender que o número “está certo” sem apontar a ambiguidade.
