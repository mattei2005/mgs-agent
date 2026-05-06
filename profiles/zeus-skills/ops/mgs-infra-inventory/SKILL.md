---
name: mgs-infra-inventory
description: "Mantém e regenera o inventário de infraestrutura MGS (data/infra-inventory.json) via script infra-discovery.sh. Cobre schema, separação skills_mgs vs skills_hermes, e processo de atualização após REPORT-INFRA."
tags: [infra, inventory, audit, mgs, runcloud, skills]
related_skills: [wp-plugin-mass-operation]
---

# Inventário de Infraestrutura MGS

## Quando usar
- Recebeu REPORT-INFRA de um agente e precisa atualizar o inventário
- Auditoria da operação MGS (o que existe, onde, quem criou)
- Onboarding de novo agente — verificar o que já existe
- Investigação de discrepância entre briefing e realidade antes de mass operation

## Arquivo canônico

`/root/mgs-agent/data/infra-inventory.json`

Gerado por: `/root/mgs-agent/scripts/infra-discovery.sh`

## Regenerar inventário

```bash
/root/mgs-agent/scripts/infra-discovery.sh
# Saída esperada (atualizado 2026-04-27):
# Serviços: 3 | Crons: 8 | Scripts: 16
# skills_mgs: 2 | skills_hermes: "atena=78, zeus=87"
```

O auto-commit watcher detecta a mudança e faz push para GitHub automaticamente.

## Schema do JSON (chaves principais)

```json
{
  "_meta": { "updated_at": "...", "generated_by": "infra-discovery.sh" },
  "systemd_services": [ {"name": "...", "status": "active/running"} ],
  "crons": [ {"entry": "*/5 * * * * /root/mgs-agent/scripts/sync-souls.sh ..."} ],
  "scripts": [ {"path": "...", "size_bytes": N, "modified_at": "..."} ],
  "skills_mgs": [
    {"name": "content-generate-rec", "path": "/root/mgs-agent/skills/.../", "skill_md": "..."}
  ],
  "skills_hermes": {
    "atena": [ {"name": "apple-notes", "category": "apple", "skill_md": "..."} ],
    "zeus":  [ {"name": "runcloud-api-management", "category": "ops", "skill_md": "..."} ]
  },
  "data_files": [ {"path": "...", "size_bytes": N, "md5": "...", "modified_at": "..."} ],
  "mu_plugin_canonical": {"path": "...", "md5": "...", "lines": N}
}
```

## ⚠️ Pitfall de schema — chave correta é `crons` (não `cron_jobs`)

Versão inicial usou `"cron_jobs"` como chave. A chave canônica é **`"crons"`**.

Validar:
```bash
jq '.crons | length' /root/mgs-agent/data/infra-inventory.json
# Deve retornar >= 1, não 0
```

## Separação skills_mgs vs skills_hermes

**Por que separar:**  
`infra-discovery.sh` coleta skills de dois lugares com propósitos distintos:

| Chave | Path | Propósito | Dispara REPORT-INFRA? |
|---|---|---|---|
| `skills_mgs` | `/root/mgs-agent/skills/` | Skills do **projeto MGS** | ✅ Sim |
| `skills_hermes` | `/root/.hermes/profiles/{agent}/skills/` | Capabilities internas do **framework Hermes** | ❌ Não |

**Números de referência (2026-04-27):**
- `skills_mgs`: 2 (content-generate-rec, content-publish-wordpress)
- `skills_hermes.atena`: 78
- `skills_hermes.zeus`: 87

**Para contagem de sites/webapps MGS (não coberto por esta SKILL):**
Ver `docs/site-counting.md`. Resumo: **32 sites MGS oficiais** (fonte: `context/sites.md`), 27 rodam em RunCloud, 5 em SFTP. Os 107 webapps RunCloud incluem não-MGS (sites pessoais, parceiros, staging) — não são fonte de verdade pra contagem MGS.

## Processo após receber REPORT-INFRA

1. Validar mentalmente se o artefato reportado faz sentido
2. Se OK → rodar `infra-discovery.sh` para capturar o estado atual
3. Se identificar problema → escalar para Rodolfo
4. Silêncio ou ack curto no canal

## Validação de inventário antes de mass operation (L2)

**Sempre validar o inventário real antes de executar em massa.**

Exemplo do acerto do Zeus em 2026-04-24:
- Briefing dizia "34 sites RunCloud"
- Cruzamento inventário (`inventario-webapps.json`) × `sites.md` = 26 sites reais
- Diferença: eggbev (canário já feito), fincgriffin (manual), 4 SFTP fora do RunCloud
- Zeus parou, reportou discrepância, aguardou confirmação → 0 sites tocados incorretamente

**Comando de cruzamento:**
```python
import json

with open('/root/mgs-agent/inventario-webapps.json') as f:
    inventory = json.load(f)

mgs_sites = { ... }  # domínios de sites.md
excluded = {'eggbev.com', 'fincgriffin.com'}
sftp_sites = {'openzed.com', 'finanzas.openzed.com', 'cliquet.com', 'finanzas.cliquet.com'}

target = [s for s in inventory
          if s.get('primary_domain') in mgs_sites
          and s.get('primary_domain') not in excluded
          and s.get('primary_domain') not in sftp_sites]

print(f"Total real para deploy: {len(target)}")
```

## Atualizar inventário manualmente (sem rodar script)

Para entradas com estado operacional que o script não captura automaticamente (ex: deploy_status do mu-plugin):

```bash
# Editar diretamente via jq
jq '.mu_plugin_canonical.deploy_status.eggbev_com = "deployed_v2"' \
  /root/mgs-agent/data/infra-inventory.json > /tmp/inv.json \
  && mv /tmp/inv.json /root/mgs-agent/data/infra-inventory.json
```

O auto-commit watcher vai detectar e fazer push.
