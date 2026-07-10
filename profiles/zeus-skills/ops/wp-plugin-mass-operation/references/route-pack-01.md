## Quando usar
- Preciso instalar, ativar, desativar ou deletar um plugin em todos os 31 sites
- Preciso portar/migrar um fluxo de SaaS/builder/static app para plugin WordPress próprio em um site MGS (ex: quiz/lead capture com REST, rewrite, CSV, SMS Funnel)
- Preciso rodar um comando WP-CLI de plugin (ex: imagify bulk-optimize, yoast reindex) em massa
- Preciso verificar se um plugin está instalado/ativo em todos os sites
- Preciso revisar, preparar ou fazer cutover de plugin WordPress customizado que substitui stack externa (Lovable/Supabase/iframe/static app) em produção — ver `references/wordpress-quiz-plugin-migration.md` para o padrão validado de quiz/funil com SMS Funnel, leads e relatório
- Rodolfo pergunta se Zeus/Atena instalou um plugin ou se ele já estava presente — fazer auditoria de proveniência, não responder por memória
- Recebeu REPORT-INFRA de um agente e precisa atualizar o inventário de infra
- Auditoria da operação MGS (o que existe, onde, quem criou)
- Onboarding de novo agente — verificar o que já existe
- Migrar/cortar apps externos ou estáticos para plugin WordPress próprio com rotas públicas, captura de leads, integrações externas e dashboard/reporting — ver `references/custom-wp-plugin-cutover.md`

### Referência rápida — custom plugin cutover

Quando substituir Lovable/Supabase/static folders/iframes por plugin WP first-party, seguir `references/custom-wp-plugin-cutover.md`: validar REST admin, lint remoto, backup, desativar pastas físicas que sombreiam rewrites, salvar lead no WP + encaminhar server-side, importar histórico sem reenviar para vendor, e validar cada rota/lista com status armazenado.

Para UI operacional de quiz e diagnóstico SMS Funnel, ver `references/quiz-redirect-sms-diagnostics.md`: redirect split deve ser editável por linhas com `+ Adicionar URL`, URL + peso + remover; `redirect_variants` não deve ficar como JSON para operador; quando SMS Funnel dashboard mostrar zero mas WP recebeu `success:true` com `list_id` correto, tratar como provável delay/cache/indexação/deduplicação da plataforma SMS Funnel após validar com leads frescas por gestor.

### Referência rápida — revisão de plugin customizado de quiz

Quando revisar plugin customizado de quiz/lead capture gerado por Lovable/dev externo, usar o checklist em `references/wp-quiz-plugin-migration-review.md`: shortcode completo, segredo de SMS Funnel fora do público, sem redirect antes de `ok:true`, Pixel Lead só pós-sucesso, `require_sms_success` para cutover, anti-spam com timestamp obrigatório e canário antes de tráfego cheio.

### Referência rápida — proveniência WP File Manager

Quando a pergunta for "foi você que instalou o File Manager?", não pivotar para o último REC/P1 nem explicar publicação. Auditar evidências e responder a pergunta de accountability diretamente. Ver `references/wp-file-manager-provenance-audit.md`.

### Referência rápida — auditoria WP File Manager + mu-plugins

Quando Rodolfo trouxer preocupação de segurança sobre `mu-plugins`, WP File Manager, elFinder ou WPCode: não remover primeiro. Rodar auditoria read-only, separar achado acionável de diferença de arquitetura, e só depois pedir confirmação para desativar/deletar resíduos. Ver `references/wp-file-manager-mu-plugin-security-audit.md`.

---

## SEÇÃO PRÉ-FLIGHT — Inventário de Infraestrutura MGS

### Arquivo canônico e regeneração

```
/root/mgs-agent/data/infra-inventory.json
```

Gerado por: `/root/mgs-agent/scripts/infra-discovery.sh`

```bash
/root/mgs-agent/scripts/infra-discovery.sh
# Saída esperada (atualizado 2026-04-27):
# Serviços: 3 | Crons: 8 | Scripts: 16
# skills_mgs: 2 | skills_hermes: "atena=78, zeus=87"
```

O auto-commit watcher detecta a mudança e faz push automaticamente.

### Schema do JSON (chaves principais)

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

**⚠️ Pitfall:** chave canônica é `"crons"` (não `"cron_jobs"`). Validar:
```bash
jq '.crons | length' /root/mgs-agent/data/infra-inventory.json
# Deve retornar >= 1, não 0
```

### Separação skills_mgs vs skills_hermes

| Chave | Path | Propósito | Dispara REPORT-INFRA? |
|---|---|---|---|
| `skills_mgs` | `/root/mgs-agent/skills/` | Skills do **projeto MGS** | ✅ Sim |
| `skills_hermes` | `/root/.hermes/profiles/{agent}/skills/` | Capabilities internas do **framework Hermes** | ❌ Não |

**Números de referência (2026-04-27):** `skills_mgs`: 2 · `skills_hermes.atena`: 78 · `skills_hermes.zeus`: 87

### Processo após receber REPORT-INFRA

1. Validar mentalmente se o artefato reportado faz sentido
2. Se OK → rodar `infra-discovery.sh` para capturar o estado atual
3. Se identificar problema → escalar para Rodolfo
4. Silêncio ou ack curto no canal

### Validação real do inventário antes de mass operation (L2)

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

**Nota:** Para contagem de sites/webapps MGS, ver `docs/site-counting.md`. **32 sites MGS oficiais** (fonte: `context/sites.md`), 27 em RunCloud, 5 em SFTP. Os 107 webapps RunCloud incluem não-MGS — não são fonte de verdade pra contagem MGS.

### Atualizar inventário manualmente (sem rodar script)

```bash
jq '.mu_plugin_canonical.deploy_status.eggbev_com = "deployed_v2"' \
  /root/mgs-agent/data/infra-inventory.json > /tmp/inv.json \
  && mv /tmp/inv.json /root/mgs-agent/data/infra-inventory.json
```

O auto-commit watcher vai detectar e fazer push.

---

## Infraestrutura dos 31 sites MGS

### RunCloud (27 sites) — WP-CLI via SSH
| Servidor | IP | User sudo | Sites |
|---|---|---|---|
| MatteiInc01 | 162.55.28.178 | zeus | 17 sites |
| MatteiInc02 | 162.55.28.179 | zeus | 2 sites |
| MatteiInc03JBF | 46.4.95.117 | zeus | 8 sites |

Credenciais: `op item get "Runcloud Server 0X - IP- zeus Acesso" --vault "MGS Conteúdo" --fields label=password --reveal`

**CRÍTICO:** Buscar senha via `terminal()` do hermes_tools, NÃO via subprocess Python — o subprocess não tem acesso ao token de serviço do 1Password.

### AWS/Bitnami (4 sites) — Browser automation
- finanzas.openzed.com, openzed.com, finanzas.cliquet.com, cliquet.com
- Login em `SITE/rodloguda` com credenciais do 1Password
- WP-CLI não disponível (não há SSH com usuário runcloud)

### Sem acesso programático
- fincgriffin.com — fazer manualmente

---

