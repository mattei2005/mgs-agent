# 📋 Pendências MGS Digital Corp

> ⚠️ **NÃO EDITAR ESTE ARQUIVO MANUALMENTE.**  
> Gerado automaticamente a partir de `data/pendencias.db.json`.  
> Para adicionar/resolver: use scripts em `scripts/pendencia-*.sh`

**Última atualização:** 2026-05-14T11:54:07-04:00  
**Total abertas:** 63  
**Total resolvidas:** 10

---

## 📊 Resumo

| Prioridade | Quantidade |
|---|---|
| 🔴 alta | 7 |
| 🟡 media | 25 |
| 🟢 baixa | 31 |

**Por categoria:**

- `infra`: 10
- `agente`: 10
- `conteudo`: 7
- `monitor`: 7
- `skills`: 6
- `lovable`: 5
- `documentacao`: 5
- `pessoal`: 5
- `externo`: 4
- `seguranca`: 3
- `app`: 1

---

## 🔴 ALTA (7 itens)

| ID | Título | Categoria | Tempo | Bloqueio |
|---|---|---|---|---|
| `PEND-001` | Publicar MGS Dashboard Android no Play Store | `app` | 10min | — |
| `PEND-002` | Desativar e deletar WP File Manager em openzed.com | `seguranca` | 5min | — |
| `PEND-003` | Trocar app.mgsdigitalcorp.com de Public para Private/Unlisted | `seguranca` | 1min | — |
| `PEND-004` | REC 62026 Yoast SEO Title duplicado - decisão produto | `conteudo` | 15min | — |
| `PEND-005` | Migrar runcloud-inventory.sh para set -a/+a | `infra` | 10min | — |
| `PEND-007` | Verificar se Hermes v0.12 native modify_thread substitui patch custom | `infra` | 15min | — |
| `PEND-008` | Verificar resposta form Tier 4 Anthropic | `externo` | 5min | — |

## 🟡 MÉDIA (25 itens)

| ID | Título | Categoria | Tempo | Bloqueio |
|---|---|---|---|---|
| `PEND-009` | Replicar adendo readability em template mx-cc-es | `conteudo` | 30min | Aguarda 5 RECs verdes consecutivos no eggbev (a... |
| `PEND-010` | Replicar adendo readability em template de-cc-de | `conteudo` | 30min | Após PEND-009 validado |
| `PEND-011` | Replicar adendo readability em template tr-cc-tr | `conteudo` | 30min | Após PEND-010 validado |
| `PEND-012` | Replicar adendo readability em template ar-cc-es | `conteudo` | 30min | Após PEND-011 validado |
| `PEND-013` | Templates novos por vertical (60 sem template) | `conteudo` | 60h+ | Colaborativo Raquel - 1h cada template aproxima... |
| `PEND-014` | Skill nova Atena: P1 (Page 1) | `skills` | 4h | — |
| `PEND-015` | Skill nova Atena: REC+P1 combo | `skills` | 2h | Após PEND-014 |
| `PEND-016` | Skill nova Atena: SEO articles (1200+ words) | `skills` | 4h | — |
| `PEND-017` | Skill nova Atena: Análise de sites | `skills` | 8h | — |
| `PEND-018` | Mudança lógica monitor readability: canário 5/5 → saúde geral site | `conteudo` | 2h | Decidida com Atena, implementação não rolou |
| `PEND-019` | REGRA 7 (Atena custo Discord) - testar em REC novo após fortalecimento | `agente` | 5min após próximo REC | — |
| `PEND-020` | REGRA 8 (rename + mention) - Atena ignora apesar de EXECUCAO OBRIGATORIA | `agente` | 1-2h investigação | Comportamental, não técnico |
| `PEND-021` | Migração Lovable Cloud → Supabase próprio (MGS Dashboard) | `lovable` | 8-16h | — |
| `PEND-022` | Trocar @lovable.dev/cloud-auth-js → auth nativo Supabase | `lovable` | 4h | Bloqueado por PEND-021 |
| `PEND-023` | Trocar @lovable.dev/email-js → Resend/SES/Postmark | `lovable` | 1h | — |
| `PEND-024` | Fix segurança wp_app_password (criptografar pgsodium) | `seguranca` | 1-2h | — |
| `PEND-026` | Preservar última migration kill-switch force_logout_version | `lovable` | 10min | Crítico se PEND-021 |
| `PEND-027` | Agente Ares (FB Ads + Google Ads + ChatPion) | `agente` | 40h+ | Após Atena 100% estável em produção |
| `PEND-028` | Adicionar gestores em authorized-users.json | `agente` | 30min | Quando Ares existir |
| `PEND-035` | Migração total operação MGS para produção (90+ RECs/mês) | `agente` | ongoing | — |
| `PEND-045` | Compartilhar briefings com Raquel | `documentacao` | 30min | — |
| `PEND-046` | Reunião com Raquel (pipeline + próxima vertical) | `documentacao` | 1h | — |
| `PEND-047` | Adicionar Raquel como GitHub collaborator (mattei2005/mgs-agent) | `documentacao` | 5min | — |
| `PEND-054` | 1Password Teams plan vaults estruturados | `pessoal` | 4h | — |
| `PEND-067` | Auto-discover Discord channel_prompts - validar fix em REC real | `agente` | 5min após próximo REC | — |

## 🟢 BAIXA (31 itens)

| ID | Título | Categoria | Tempo | Bloqueio |
|---|---|---|---|---|
| `PEND-025` | Cleanup repos zumbis GitHub (mgsdashboard + -bbdeba00) | `lovable` | 5min | Aguarda Lovable autorizar |
| `PEND-029` | Migração ChatPion → bot próprio | `agente` | 80h+ | Longo prazo, projeto paralelo |
| `PEND-030` | Otimização SOUL/tools overhead (~80k chars/sessão) | `agente` | 8-16h | Refactoring grande |
| `PEND-031` | Pricing hardcoded em 3 lugares - consolidar | `infra` | 30min | — |
| `PEND-032` | Avaliação Kimi K2.6 vs Sonnet 4.6 (potencial 88% economia) | `agente` | 4h pesquisa | — |
| `PEND-033` | Image generation nativo Hermes (PR #4317 upstream) | `infra` | depende de merge | Aguarda merge upstream |
| `PEND-034` | Bug Discord adapter drop 3+ msgs rápidas | `infra` | investigar | Workaround OK (aguardar resposta entre msgs) |
| `PEND-036` | Tradução Hermes PT-BR | `infra` | 4h | — |
| `PEND-037` | Refactor SKILL content-generate-rec (1016L) | `skills` | 2-4h | PULADO 02/05 - low ROI ($5/ano economia) |
| `PEND-038` | Monitor SSL expiry (<14 dias alerta) | `monitor` | 1h | — |
| `PEND-039` | Monitor disk space (>80% alerta) | `monitor` | 30min | — |
| `PEND-040` | Monitor site UP/DOWN dos 32 sites | `monitor` | 2h | — |
| `PEND-041` | Monitor SystemD services (zeus-gw, atena-gw, mgs-autocommit) | `monitor` | 30min | — |
| `PEND-042` | Monitor MD5 mu-plugin v4 drift detection (32 sites) | `monitor` | 2h | — |
| `PEND-043` | Monitor backup integrity | `monitor` | 1h | — |
| `PEND-044` | Dashboard custo cumulativo web | `monitor` | 8h | — |
| `PEND-048` | Adicionar 4 sites SFTP em sites.json | `infra` | 30min | Quando templates SFTP existirem |
| `PEND-049` | PITFALLs centralizados (mencionar wp_curl_auth em mais skills) | `skills` | 10min cada | — |
| `PEND-050` | iOS Apple Unlisted Distribution review | `externo` | aguardar Apple | Apple review |
| `PEND-051` | openzed.com cleanup completo pós-recovery | `externo` | 30min | Confirmar 100% pós-recovery |
| `PEND-052` | Hetzner snapshots cleanup (4 snapshots ativos) | `externo` | 5min | — |
| `PEND-053` | SSH login notification cleanup MatteiInc01 | `pessoal` | 1h | — |
| `PEND-055` | SSH no Mac do Rodolfo | `pessoal` | 30min | — |
| `PEND-056` | Backup ZIP automatizado da operação | `infra` | 2h | — |
| `PEND-057` | Hurácan diminished value claim vs Allstate | `pessoal` | ongoing | Pessoal/jurídico |
| `PEND-068` | Push notifications Discord mobile não chegam ao celular Rodolfo | `pessoal` | investigação | — |
| `PEND-069` | AGENT.md authorization layer - verificar se finalização foi commitada | `documentacao` | 30min validação | — |
| `PEND-070` | Criar docs/onboarding-new-site.md (mapa completo adicionar site MGS) | `documentacao` | 30min skeleton + preenchimento gradual | — |
| `PEND-071` | Hermes session zombies em pts/ - investigar fix estrutural | `infra` | investigacao 1h | — |
| `PEND-072` | Cost tracking nativo Hermes - revisitar quando upstream adicionar pricing dos modelos atuais | `infra` | 10min validacao | — |
| `PEND-073` | Confirmar visualmente se duplicacao Atena canal pai vs thread eh preview nativo Discord ou bug real | `agente` | 5min observacao | — |

---

## 📚 Como usar

```bash
# Adicionar nova pendência
./scripts/pendencia-add.sh "Título da tarefa" --categoria infra --prioridade alta --tempo "30min"

# Marcar como resolvida
./scripts/pendencia-done.sh PEND-001 --como "Como foi resolvido"

# Listar com filtros
./scripts/pendencia-list.sh --prioridade alta
./scripts/pendencia-list.sh --categoria seguranca
./scripts/pendencia-list.sh --stats
./scripts/pendencia-list.sh PEND-001  # ver uma específica
```

## 🏷️ Categorias

- **`app`** — MGS Dashboard, USX Track, MGS Tasks (iOS/Android)
- **`seguranca`** — Vulnerabilidades, credenciais, acesso
- **`infra`** — Hetzner VPS, scripts, crons, monitores
- **`conteudo`** — REC, P1, SEO, templates, RECs específicos
- **`skills`** — Skills Atena/Zeus, refactoring, novas skills
- **`agente`** — Atena, Zeus, futuros agentes (Ares)
- **`lovable`** — MGS Dashboard Lovable, Supabase migration
- **`monitor`** — Monitores futuros zero-token
- **`documentacao`** — Docs internas, briefings, colaboração
- **`externo`** — Apple, Google, Lovable, Anthropic, dev externo
- **`pessoal`** — Itens não-MGS do Rodolfo
