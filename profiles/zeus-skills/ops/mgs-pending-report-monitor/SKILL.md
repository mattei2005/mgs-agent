---
name: mgs-pending-report-monitor
description: "Monitor automático que detecta skills MGS criadas sem REPORT-INFRA no inventário. Alerta via Discord webhook, anti-spam 24h, resolução automática. Parte do sistema defense-in-depth para rastreabilidade de infra."
tags: [monitoring, discord, cron, infra, inventory, skills, report-infra]
related_skills: [mgs-infra-inventory, log-monitor-discord-alert, shell-cron-env-export]
---

# Monitor de Skills Sem REPORT-INFRA (check-pending-reports.sh)

## Quando usar

- Configurar pela primeira vez o monitor de pendências de REPORT-INFRA
- Adicionar novos diretórios de skills a monitorar (ex: novo agente)
- Debugar por que alerta foi ou não enviado
- Entender a lógica de resolução automática

## Contexto

Este monitor é a **Opção C** do sistema defense-in-depth MGS (implementado 2026-04-27).
A **Opção A** é o checklist de encerramento nos SOUL.md dos agentes.
Juntos, garantem que nenhuma skill MGS seja criada sem registro no inventário.

---

## Diretórios monitorados

| Agente | Diretório | Razão |
|--------|-----------|-------|
| Zeus | `/root/.hermes/profiles/zeus/skills/ops/` | Skills operacionais MGS |
| Atena | `/root/.hermes/profiles/atena/skills/wordpress/` | Skills WP MGS |
| Atena | `/root/.hermes/profiles/atena/skills/devops/` | Skills devops MGS |

**NÃO monitorados** (propositalmente): skills genéricas Hermes (apple/, creative/, mlops/ etc.) — essas são capabilities do framework, não artefatos MGS.

---

## Arquivos do sistema

```
/root/mgs-agent/scripts/check-pending-reports.sh   — script principal
/root/mgs-agent/data/pending-reports-state.json    — state anti-spam
/root/mgs-agent/logs/check-pending-reports.log     — output do cron
crontab: */15 * * * *                               — frequência de verificação
```

---

## State file schema

```json
{
  "alerted": {
    "zeus:skill-name": {
      "alerted_at": 1745726823,   // epoch seconds
      "skill_name": "skill-name",
      "agent": "zeus",
      "path": "/root/.hermes/profiles/zeus/skills/ops/skill-name"
    }
  },
  "resolved": {}
}
```

- **alerted**: skills que já receberam alerta; chave = `"agent:skill_name"`
- **anti-spam**: se `now - alerted_at < 86400s (24h)`, não reaterta
- **resolução**: quando skill entra no inventário, remove de `alerted` e posta mensagem de resolved no Discord

---

## Adicionar novo agente/diretório

No script `check-pending-reports.sh`, adicionar nas duas declarações `declare -A`:

```bash
# Em SKILL_DIRS:
SKILL_DIRS["novo_agente"]="/root/.hermes/profiles/novo_agente/skills/ops"

# Em DIR_AGENT:
DIR_AGENT["novo_agente"]="novo_agente"
```

E adicionar extração do inventário:

```bash
# Adicionar após ATENA_INVENTORY_SKILLS=...
NOVO_INVENTORY_SKILLS=$(get_inventory_skills "novo_agente")
```

E no bloco de seleção de inventário por agente:

```bash
elif [[ "$agent" == "novo_agente" ]]; then
    inventory_skills="$NOVO_INVENTORY_SKILLS"
fi
```

---

## Validação após instalação

```bash
# 1. Script executável
ls -la /root/mgs-agent/scripts/check-pending-reports.sh
# Esperado: -rwxr-xr-x

# 2. Dry-run manual
bash /root/mgs-agent/scripts/check-pending-reports.sh
# Esperado: "[timestamp] OK — nenhuma skill pendente de REPORT-INFRA"
# Se houver pendentes: alerta vai para Discord + state atualiza

# 3. Cron ativo
crontab -l | grep check-pending-reports
# Esperado: */15 * * * * /root/mgs-agent/scripts/check-pending-reports.sh ...

# 4. State file
cat /root/mgs-agent/data/pending-reports-state.json
# Esperado: JSON válido com "alerted" e "resolved"
```

---

## Pitfalls

1. **Campo webhook no 1Password é `label=webhook_url`** — o item "Discord Webhook - Zeus Channel" (ID: `3jffmnrxkxbzmb3g745t777po4`) tem campo com label `webhook_url`, não `url`. Usar `--fields label=webhook_url`.

2. **`set -a / set +a` ao redor do `source .env`** — obrigatório para que `op` CLI veja `OP_SERVICE_ACCOUNT_TOKEN`. Sem isso, script falha silenciosamente em ambiente cron. Ver skill `shell-cron-env-export`.

3. **Source correto: `/root/mgs-agent/.env`** — o `OP_SERVICE_ACCOUNT_TOKEN` está em `/root/mgs-agent/.env`, não em `/root/.hermes/profiles/zeus/.env`. O profile zeus `.env` não tem o token. Usar `source "/root/mgs-agent/.env"` no script.

4. **Dry-run detecta uma skill real pendente** — é esperado se houver skill no filesystem que de fato não está no inventário. O sistema está funcionando corretamente. Adicionar ao inventário e rodar novamente.

5. **Anti-spam de 24h**: se alerta foi enviado e você quer forçar novo alerta, deletar a entrada do `alerted` no state file:
   ```bash
   # Resetar state completamente
   echo '{"alerted": {}, "resolved": {}}' > /root/mgs-agent/data/pending-reports-state.json
   ```

6. **Inventário usa `python3` inline** — o script depende de `python3` disponível no PATH. Validado no VPS (Debian). Se mudar ambiente, verificar dependência.

7. **⚠️ BUG HISTÓRICO CORRIGIDO (2026-04-27) — separador IFS em `RESOLVED_SKILLS[]`:** O formato original usava `:` como separador no array (`skill_key:skill_path`), mas `skill_key` tem formato `agent:skill_name` — o `:` colidia. O `IFS=':' read -r agent_skill skill_path` quebrava errado, o `pop()` usava chave `"zeus"` em vez de `"zeus:skill-name"`, falhava silenciosamente, state nunca atualizava → loop infinito de resoluções. **Fix:** separador trocado para `|`. Se fizer refactor, nunca usar `:` como separador em arrays shell que carreguem `agent:skill_name`.

8. **⚠️ BUG HISTÓRICO CORRIGIDO (2026-04-27) — persistir state ANTES de enviar mensagem:** Versão original persistia o state *após* o `curl`. Se o curl falhasse, estado não era salvo e a skill reentraria no loop no próximo ciclo. **Fix canônico:** `echo "$STATE" > "$STATE_FILE"` deve ocorrer *antes* do `curl`. Idempotência garante que segunda execução seja no-op mesmo sem resposta do Discord.

9. **Loop infinito de resolução:** Combinação dos bugs 7+8 causou ~120 mensagens duplicadas em 8h (2026-04-27, 02:00–10:00). Sempre validar empiricamente com dry-run após qualquer modificação no script, especialmente na lógica de state transitions.

---

## Comportamento esperado — fluxo completo

```
[t=0]   Skill nova criada no filesystem mas não no inventário
[t=15m] Cron roda → detecta skill → alerta Discord → atualiza state (alerted_at=now)
[t=30m] Cron roda → skill ainda pendente → anti-spam (< 24h) → silêncio
[t=Xh]  Zeus/Atena atualiza infra-inventory.json
[t=X+15m] Cron roda → skill está no inventário → posta "✅ RESOLVIDO" → remove de alerted
```

---

## Formato das mensagens Discord

**Alerta de pendência:**
```
🚨 [PENDING-REPORT] Skills detectadas SEM REPORT-INFRA:
• `zeus` criou skill `nome-skill`
  Path: `/root/.hermes/profiles/zeus/skills/ops/nome-skill`

Aguardo REPORT-INFRA + atualização de `infra-inventory.json`.
<@1496296175014252634>
```

**Resolução:**
```
✅ [PENDING-REPORT] Skill `nome-skill` (agente: `zeus`) agora está no inventário (commit XXXX). Pendência fechada.
```
