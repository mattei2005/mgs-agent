# Inventário Classificado — MGS OS

> Status: inventário read-only v0.1  
> Data: 2026-06-06  
> Escopo: `/root/mgs-agent`  
> Regra: este documento **não move, remove nem altera runtime**. Ele apenas classifica e recomenda próximos passos.

---

## Resumo executivo

```text
Bloco                         Classe principal        Veredito
----------------------------- ---------------------- ---------------------------------------------
context/                      canônico/conceitual     revisar e alinhar por fases
 data/                         runtime/operacional     não tocar sem plano específico
 docs/                         histórico/planos        manter; revisar documentos de controle
 scripts/                      automação produtiva     não mexer sem validação/rollback
 skills/                       procedimentos           manter; revisar só quando skill for usada
 patches/                      patch local             não tocar sem entender impacto runtime
 backups/                      backup                  manter por enquanto; arquivar depois
 experiments/                  experimento             manter; revisar baixo risco depois
 tools/                        ferramenta auxiliar      revisar quando entrar em fluxo operacional
 api/                          API/runtime             não tocar sem plano técnico
 logs/                         audit/runtime           não tocar; usar só para consulta
```

---

## Inventário principal

```text
Path                                      Classe        Área provável              Status        Ação recomendada
---------------------------------------- ------------- -------------------------- ------------- ---------------------------
context/                                  canônico      Executive / MGS OS          ativo         manter; alinhar por documento
context/company-os.md                     canônico      Executive / MGS OS          revisado      manter como proposta canônica
context/company-current-operating-model.md canônico     Executive / MGS OS          revisado      manter como fonte CEO
context/areas.md                          canônico      Executive / MGS OS          revisado      manter
context/agent-map.md                      canônico      Executive / MGS OS          revisado      manter
context/routes.md                         canônico      Executive / MGS OS          aprovado      manter
context/sources-of-truth.md               canônico      Executive / MGS OS          aprovado      manter
context/permissions-matrix.md             canônico      Security / Access           aprovado      manter
context/company.md                        canônico      Empresa                    legado ativo   revisar depois
context/sites.md                          canônico      Sites / Verticais           legado ativo   revisar depois
context/team.md                           canônico      Equipe / Access             legado ativo   revisar depois
context/processes.md                      canônico      Processos                   legado ativo   revisar depois
context/monetization.md                   canônico      Revenue / AdOps             legado ativo   revisar depois
context/acquisition.md                    canônico      Growth / Media Buying       legado ativo   revisar depois
context/security-policies.md              canônico      Security / Access           legado ativo   revisar depois
```

```text
Path                                      Classe        Área provável              Status        Ação recomendada
---------------------------------------- ------------- -------------------------- ------------- ---------------------------
data/                                     runtime       operação                   ativo         não tocar em massa
data/sites.json                          runtime       Tech / WordPress           ativo         não tocar; fonte técnica
data/authorized-users.json               sensível      Security / Access           ativo         não tocar sem confirmação
data/article-tracker.db                  runtime       Content                    ativo         não tocar
data/card-cache.db                       runtime       Content                    ativo         não tocar
data/rec-fingerprints.db                 runtime       Content                    ativo         não tocar
data/wp-term-cache.json                   runtime/cache Content / WordPress        ativo         não tocar
data/lazyblock-*.json                    runtime/config Content / WordPress        ativo         revisar só com pipeline
data/*-state.json                        runtime       Monitores / crons           ativo         não tocar sem plano
 data/*backup*                            backup        Tech / Infra                histórico     manter; arquivar depois
 data/deprecated/                         legado        variável                   legado        revisar depois
 data/backups/                            backup        Tech / Infra                histórico     manter; arquivar depois
 data/card-images-cache/                  cache         Content                    cache         não tocar agora
 data/chat-logs/                          histórico     Agents / Discord            histórico     manter
```

```text
Path                                      Classe        Área provável              Status        Ação recomendada
---------------------------------------- ------------- -------------------------- ------------- ---------------------------
docs/                                     histórico     Executive / Tech            ativo         manter
docs/mgs-os-restructure-plan.md           plano         Executive / MGS OS          revisado      manter
docs/mgs-structure-inventory.md           inventário    Executive / MGS OS          novo          manter
docs/CRONS.md                             operacional   Tech / Infra                ativo         revisar sem alterar runtime
docs/PENDENCIAS.md                        operacional   Executive / Ops             ativo         manter; revisar depois
docs/PENDENCIAS-HISTORICO.md              histórico     Executive / Ops             histórico     manter
docs/CHANGELOG.md                         histórico     Tech / Infra                histórico     manter
docs/changelog/                           histórico     Tech / Infra                histórico     manter
docs/security/                            segurança     Security / Access           ativo         revisar depois
docs/rec-p1-*                             histórico     Content                    ativo/legado   revisar depois
docs/rule-classification.md               doc           Tech / Ops                  ativo         revisar depois
docs/site-counting.md                     doc           Sites / BI                  ativo         revisar depois
docs/skills-naming-convention.md          doc           Skills / Ops                ativo         revisar depois
```

```text
Path                                      Classe        Área provável              Status        Ação recomendada
---------------------------------------- ------------- -------------------------- ------------- ---------------------------
scripts/                                  automação     Tech / Infra                ativo         não mexer em massa
scripts/monitor-*.sh                      automação     Tech / Monitoring           ativo         revisar só por incidente
scripts/mgs-rec-runner.py                 automação     Content                    ativo         não tocar agora
scripts/mgs-p1-runner.py                  automação     Content                    ativo         não tocar agora
scripts/mgs-rec-p1-orchestrator.py        automação     Content                    ativo         não tocar agora
scripts/cron-control-plane.py             automação     Tech / Infra                ativo         não tocar agora
scripts/mgs-ops-control-plane.py          automação     Executive / Ops             ativo         não tocar agora
scripts/mgs-ops-briefing.py               automação     Executive / Ops             ativo         não tocar agora
scripts/pendencia-*.sh                    automação     Ops                         ativo         manter
scripts/deprecated/                       legado        Tech / Infra                legado        revisar depois
scripts/mu-plugins/                       automação     WordPress                   ativo         não tocar sem plano
scripts/yoast-scorer/                     automação     Content / SEO               ativo         não tocar agora
```

```text
Path                                      Classe        Área provável              Status        Ação recomendada
---------------------------------------- ------------- -------------------------- ------------- ---------------------------
skills/                                   skill         Agents                     ativo         manter
skills/content-generate-rec/              skill         Content / Atena             ativo         não tocar agora
skills/content-publish-wordpress/         skill         Content / WordPress         ativo         não tocar agora
patches/                                  patch local   Tech / Hermes              ativo         não tocar sem plano
patches/hermes/                           patch local   Tech / Hermes              ativo         não tocar sem plano
backups/                                  backup        Tech / Infra                histórico     manter; arquivar depois
experiments/                              experimento   variável                   baixo risco    revisar depois
tools/                                    ferramenta    Tech / Creative             auxiliar      revisar quando necessário
tools/canva-local-automation/             ferramenta    Creative / Hera             auxiliar      revisar antes de usar
api/                                      runtime/API   Tech / Content              ativo         não tocar sem plano
api/generate-rec-api.py                   runtime/API   Content / WordPress         ativo         não tocar agora
api/usage.db                              runtime       API                         ativo         não tocar
logs/                                     logs          Audit / Runtime             ativo         não tocar; consultar só
logs/events-audit.jsonl                   audit log     Security / Ops              ativo         não tocar; fonte audit
```

---

## Arquivos que exigem cuidado especial

```text
Path                                      Motivo
---------------------------------------- -------------------------------------------------------
data/authorized-users.json                Fonte operacional de autorização; exige Rodolfo.
data/sites.json                           Fonte técnica dos sites; alteração pode quebrar pipeline.
.env / tokens / credentials               Segredos; nunca expor em chat.
scripts/monitor-*                         Monitores/crons; risco de spam/loop se mal editado.
scripts/mgs-*-runner.py                   Pipeline de conteúdo; risco operacional.
patches/hermes/                           Patch runtime Hermes/MGS; risco sistêmico.
api/                                      Pode estar ligado a runtime/API.
logs/events-audit.jsonl                   Audit trail; append-only/consulta.
logs/*.log                                Runtime; consultar com filtros, não editar.
```

---

## Próximos blocos recomendados

```text
Ordem   Bloco                         Motivo
------  ----------------------------- --------------------------------------------------
1       context/company.md             Alinhar visão geral antiga com MGS OS novo.
2       context/team.md                Atualizar equipe, gestores/códigos e agentes.
3       context/acquisition.md         Alinhar Ares, Facebook/Google, ChatPion, quiz/SMS.
4       context/monetization.md        Alinhar Smart Bidding, ActiveView, AdOps/AdX.
5       context/processes.md           Consolidar rotas operacionais revisadas.
6       context/sites.md               Revisar sites/verticais depois do modelo de áreas.
7       docs/CRONS.md                  Revisar inventário de crons sem alterar crontab.
```

---

## Regra para a Fase 4

A Fase 4 só deve começar depois de Rodolfo aprovar este inventário. A migração deve ser por bloco pequeno, nesta ordem sugerida:

```text
1. Apenas arquivos context/*.md conceituais.
2. Depois docs operacionais.
3. Depois skills, se necessário.
4. Scripts/runtime/data só com plano específico e validação.
```
