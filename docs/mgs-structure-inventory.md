# Inventário Classificado — MGS OS

> Status: inventário v0.4 — Ares unificado  
> Data original: 2026-06-07 01:28 EDT; atualização: 2026-07-12  
> Escopo: `/root/mgs-agent`  
> Regra: este documento classifica a estrutura e registra a migração autorizada; runtime real e manifests vencem para estado técnico.

---

## Atualização operacional — SHEIN horário vencido e recovery delegado (2026-10-09)

- Autoridade: Rodolfo, mensagem `1558142161659105342` nesta thread `1557274000680288307`; delegação Ares→Zeus aprovada em `1558142033774776411`, thread `1558141425541980203`, já registrada por Zeus em `context/routes.md` / `zeus.ares.manager-authorized-technical-recovery`.
- Horário explícito vencido do próprio dia no timezone verificado da conta resolve NOW após QA, com audit do horário original, sem nova autorização apenas pelo atraso; futuro, PAUSED expresso e próxima meia-noite omitida são preservados. Data anterior ao dia da conta não muda automaticamente.
- Runtime desta correção: novo `scripts/ares_campaign_v3/shein_schedule.py`, hook somente de intake/preflight em `shein_single_clone.py`, testes `test_shein_elapsed_schedule.py`; contrato `SHEIN-US-DIRECT.json#/request_defaults/expired_explicit_start_policy` e skill própria SHEIN (main/general route/standard requests). Snapshots PREPARED vencidos são rematerializados somente antes de write, preservando clock; estados de recovery e manifests/IDs já criados não são reescritos por esta tarefa.
- Comunicação: Geizian avisado na origem e Zeus coordenado com mention/readback, sem writer concorrente; recuperação parcial de C106/CBO segue com Zeus técnico e Ares funcional. A normalização de tempo não corrige a rejeição Meta de CBO e não comprova conclusão da campanha.
- Evidência: `data/ares/meta-ads/audit/shein/schedule-and-recovery-permission-20261009/verification-final.json`; red→green e regressão offline registrados. Zero writes Meta/replay/cópias/restart nesta tarefa. Permissão de recovery não altera billing, credenciais ou Critical Subset.

## Atualização operacional — thread de relatórios YOLO G002 retirada (2026-10-09)

- Pedido explícito de Rodolfo na thread `1557274000680288307`: deletar somente `1558138059344576593` (`Yolokfx Conta 01 Intraday`, pai G002 `1548149300826079333`). DELETE 200 e GET posterior 404 confirmados.
- Rota retirada em `context/ares-operational-map.md`; registro de escopo anterior supersedido por `ARES-THREAD-1558138059344576593-DELETED-BY-RODOLFO`. Histórico canônico preservado; não recriar/publicar na thread. Rodolfo criará o canal substituto; ID ainda não informado.
- Evidência: `data/ares/discord/thread-deletions/1558138059344576593.json`. Sem novo canal, alterações Meta, gateway, cron ou permissões Discord; nenhum job do profile Ares aponta para o ID retirado.

## Atualização operacional — SHEIN lance e autorização por canal (2026-10-09)

- Autoridade: Rodolfo, confirmação explícita na thread `1557274000680288307`; nenhum pedido de campanha ou replay autorizado nesta mudança.
- Regras: `SHEIN-US-DIRECT.json#/bid_strategy_change_policy` e `#/channel_authorization_policy`; matriz, mapa operacional e parity reconciliados. Qualquer participante humano com permissão efetiva de comunicação no canal/thread pode solicitar sobre contas/perfis do canal; gestor titular deixa de ser filtro exclusivo.
- Runtime: `shein_general.py`, `shein_single_clone.py`, novo `shein_channel_authority.py`, `schema.py`, leitura consolidada `engine.py`, proteção `activation.py` e `shell_recovery.py`. Troca de lance é delta somente no alvo, com cap exato/reset, naming coerente e QA antes de ativação; nenhuma mudança em targeting/credenciais/billing. Permissões Discord consultadas read-only por Ares e relidas antes dos writes.
- Procedimento: skills próprias `direct-traffic-shein-operations` (main, general fast route e standard requests) e regra 21 de `meta-campaign-engine-v3`. Dois asserts legados de formulários 1.0 foram reconciliados com o modelo 3.0 já aprovado e o estado técnico real, sem restaurar o formulário antigo.
- Evidência: `data/ares/meta-ads/audit/shein/rules-bid-channel-20261009/` contém backups/inventário, red→green, regressão offline e proof Discord de Geizian nos seis canais e thread `1558126286826774711` (pai G005). Testes offline não provam aceitação Meta/serving; readback live permanece obrigatório no próximo pedido real.
- Sem writes Meta, sem alterações de permissões Discord/cadastro global de usuários, sem cron/gateway/restart. Histórico dos registros anteriores preservado por supersessão; fontes canônicas e checkpoint registrados pelo controle institucional.

## Atualização operacional — CPV13 relatórios isolados (2026-10-08)

- Autoridade: Rodolfo, thread `1557763617578033172`; chave `growth.creditoparaveiculo.account13.reporting.read-only-isolation` no contrato CPV.
- Runtime: wrappers Diário/Intraday da conta 13 e `creditoparaveiculo-fixed-reports.py` no profile Ares. Relatórios usam somente leitura, sem gate persistente de recovery de campanha; checkpoints de ações preservam gates próprios. Lock físico tem espera limitada e aviso idempotente; readback de entrega diferido não é sucesso.
- Auditoria: `data/ares/meta-ads/audit/reporting/Creditoparaveiculo-BR-CAR-BR/intraday-recovery-20261008/verification-final.json`; inventário global dos 49 jobs Hermes, root crontab, systemd timers e gates internos coletado antes/depois. Nenhum schedule/enabled/paused/root crontab alterado.
- Verificação: 111 testes passaram; Intraday live publicado em três partes com GET/conteúdo confirmado, seguido de execução do wrapper automático com duplicação suprimida; zero ações Meta e lease da duplicação pendente preservada.
- Procedimento: `meta-ads-intraday-operations/references/current-operational-pitfalls.md`, conferido após atualização. Pausas históricas CPV/Eggbev autorizadas não foram reativadas.

## Atualização operacional — SMS CHAT (2026-10-05)

- Fonte/auditoria: `data/ares/sms-funnel/audit/creditoparaveiculo/chat-url-1556643119515172927.json`.
- Registro: `growth.creditoparaveiculo.sms-funnel.chat-destination-attribution`, autorizado por Rodolfo na thread `1556643119515172927`.
- Escopo: seis sequências CHAT G001–G006, incluindo TOPFEED G004; destino `https://creditoparaveiculo.com/rec-br-sem-entrada-mesmo-com-nome-restrito` e `utm_campaign=s01c01g00x-chat`, com os demais parâmetros preservados.
- Evidência: seis URLs e destinos dos encurtadores validados; 36 sequências fora do escopo e 42 configurações de campanha inalteradas; seis probes HTTP 200 sem telefone.
- Procedimento atualizado: referência `sms-funnel-wordpress-routing/references/sms-funnel-api-readback.md` registra validação do `external_id` do provedor e comparação consistente entre respostas de sequência e inventário.

## Resumo executivo

Atualização estrutural de 2026-07-12:

```text
Componente                              Estado atual
--------------------------------------  ---------------------------------------------------------
Ares                                    agente ativo unificado Creative Ops + Growth/Media Buying
data/ares/creative-ops/                  dados e inventário unificado de Creative Operations
profiles/ares-skills/growth/             Creative Ops, taxonomia, Meta Library e Campaign Ops
scripts/ares-meta-library-*              runtime criativo migrado para Ares
browser-profiles Ares                    Meta Library/YouTube copiados com origem preservada
authorized-users.json                    7 usuários permanentes no Ares
```

O snapshot de contagens abaixo é histórico de 2026-06-07 e não deve ser usado como contagem atual.

```text
Bloco                         Classe principal        Veredito
----------------------------- ---------------------- ---------------------------------------------
context/                      canônico/conceitual     manter; base Company OS atual
profiles/                     config/skills agentes   manter; versiona SOUL/config/skills próprios
data/                         runtime/operacional     não tocar sem plano específico
scripts/                      automação produtiva     não mexer em massa; validar por script
skills/                       procedimentos globais    manter; revisar só quando skill for usada
docs/                         histórico/planos        manter; atualizar docs de controle
patches/                      patch local Hermes      não tocar sem entender impacto runtime
api/                          API/runtime             não tocar sem plano técnico
tools/                        ferramenta auxiliar      revisar quando entrar em fluxo operacional
backups/                      backup                  preservar último por família; arquivar depois
experiments/                  experimento             baixo risco, mas não limpar ainda
logs/                         audit/runtime           não editar; consultar com filtros
.env / auth / credenciais     sensível/não-versionar   nunca expor; não versionar
```

---

## Contagem estrutural atual

```text
Path                         Arquivos detectados     Observação
---------------------------- ---------------------- ---------------------------------------------
context/                     15                     camada canônica/conceitual MGS OS
data/                        102                    runtime, states, caches e bancos locais
docs/                        28                     planos, changelog, CRONS, inventários
scripts/                     2689                   inclui yoast-scorer/ com muitos arquivos
skills/                      118                    skills globais Content/WordPress
profiles/                    142                    SOUL/config/skills versionadas dos agentes
patches/                     32                     patches Hermes/MGS
backups/                     34                     backups manuais e safety snapshots
experiments/                 584                    spike Honcho/experimentos
tools/                       13                     automações auxiliares
api/                         5                      API local + usage.db
logs/                        543                    logs rotacionados/audit/runtime
```

---

## Inventário principal — context/

```text
Path                                      Classe        Área provável              Status        Ação recomendada
---------------------------------------- ------------- -------------------------- ------------- ---------------------------
context/                                  canônico      Executive / MGS OS          ativo         manter
context/company-current-operating-model.md canônico     Executive / MGS OS          revisado      manter como fonte CEO
context/company-os.md                     canônico      Executive / MGS OS          proposta atual manter
context/areas.md                          canônico      Executive / MGS OS          auditado      manter
context/agent-map.md                      canônico      Executive / MGS OS          auditado      manter
context/routes.md                         canônico      Executive / MGS OS          auditado      manter
context/sources-of-truth.md               canônico      Executive / MGS OS          auditado      manter
context/permissions-matrix.md             canônico      Security / Access           auditado      manter
context/ares-operational-map.md           canônico      Creative + Growth / Ares     ativo         fonte operacional HOT
context/company.md                        canônico      Empresa                    legado ativo   revisar em bloco conceitual
context/sites.md                          canônico      Sites / Verticais           legado ativo   revisar em bloco conceitual
context/team.md                           canônico      Equipe / Access             legado ativo   revisar em bloco conceitual
context/processes.md                      canônico      Processos                   legado ativo   revisar em bloco conceitual
context/monetization.md                   canônico      Revenue / AdOps             legado ativo   revisar em bloco conceitual
context/acquisition.md                    canônico      Growth / Media Buying       legado ativo   revisar em bloco conceitual
context/security-policies.md              canônico      Security / Access           ativo         revisar depois
```

---

## Inventário principal — profiles/

```text
Path                                      Classe        Área provável              Status        Ação recomendada
---------------------------------------- ------------- -------------------------- ------------- ---------------------------
profiles/                                 versão agente Agents / Hermes            ativo         manter; não editar em massa
profiles/zeus-soul.md                     config        Executive / Zeus            ativo         manter; ajustar só por governança
profiles/zeus-config.yaml                 config        Executive / Zeus            ativo         não tocar sem plano Hermes
profiles/zeus-skills/                     skill         Zeus / Ops                  ativo         manter; commitar mudanças úteis
profiles/atena-soul.md                    config        Content / Atena             ativo         manter; ajustar depois de Company OS
profiles/atena-config.yaml                config        Content / Atena             ativo         não tocar sem plano Hermes
profiles/atena-skills/                    skill         Content / Atena             ativo         manter
profiles/ares-soul.md                     config        Growth / Ares               ativo         revisar quando Ares avançar
profiles/ares-config.yaml                 config        Growth / Ares               ativo         não tocar sem plano Hermes
profiles/ares-skills/                     skill         Growth / Ares               ativo         manter
profiles/ares-skills/growth/direct-traffic-vehicle-finance-operations/ skill Growth / Ares ativo contrato CPV/Diário; manter em paridade com runtime
profiles/ares-skills/growth/direct-traffic-vehicle-finance-operations/references/creative-cut-24h-strategy.md procedure Growth / Ares ativo estratégia CREATIVE_CUT_24H documentada para conta 05; ativação depende de onboarding/readback
profiles/*bak*                            backup        Agents / Hermes             histórico     manter por enquanto
```

---

## Inventário principal — data/

```text
Path                                      Classe        Área provável              Status        Ação recomendada
---------------------------------------- ------------- -------------------------- ------------- ---------------------------
data/                                     runtime       Operação                   ativo         não tocar em massa
data/sites.json                          runtime       Tech / WordPress           ativo         fonte técnica; não tocar sem plano
data/authorized-users.json               sensível      Security / Access           ativo         fonte autorização; exige confirmação
data/article-tracker.db                  runtime       Content                    ativo         não tocar
data/card-cache.db                       runtime/cache Content                    ativo         não tocar
data/rec-fingerprints.db                 runtime       Content                    ativo         não tocar
data/wp-term-cache.json                   runtime/cache Content / WordPress        ativo         não tocar
data/lazyblock-*.json                    runtime/config Content / WordPress        ativo         revisar só com pipeline
data/*-state.json                        runtime       Monitores / crons           ativo         não tocar sem plano
data/infra-inventory.json                inventário    Tech / Infra                ativo         manter; atualizar via script
data/knowledge-registry.json             registro      MGS OS / conhecimento       ativo         ponteiro canônico; validar via mgs-knowledge-control
data/ares/meta-ads/operations/Creditoparaveiculo-BR-CAR-BR.json runtime/config Growth / Ares ativo fonte canônica da operação CPV G006
data/ares/meta-ads/operations/Creditoparaveiculo-BR-CAR-BR-05-CREATIVE-CUT-24H.json runtime/config Growth / Ares documentado não ativo contrato da estratégia 24h na conta 05; sem writes/crons até gates
data/pendencias.db.json                  runtime       Executive / Ops             ativo         não tocar sem plano
data/discord-thread-imports/             histórico     Agents / Discord            histórico     manter
data/chat-logs/                          histórico     Agents / Discord            histórico     manter
data/card-images-cache/                  cache         Content                    cache         não tocar agora
data/backups/                            backup        Tech / Infra                histórico     manter; arquivar depois
data/deprecated/                         legado        variável                   legado        revisar depois
```

---

## Inventário principal — scripts/

```text
Path                                      Classe        Área provável              Status        Ação recomendada
---------------------------------------- ------------- -------------------------- ------------- ---------------------------
scripts/                                  automação     Tech / Infra                ativo         não mexer em massa
scripts/cron-control-plane.py             automação     Tech / Infra                ativo         manter; controlar via dry-run/teste
scripts/cron-smoke-test.sh                automação     Tech / Infra                ativo         manter
scripts/housekeeping-bak-cleanup.sh       automação     Tech / Infra                ativo         manter; já preserva último backup
scripts/mgs-safety-backup.sh              automação     Tech / Infra                ativo         manter; backup periódico seguro
scripts/monitor-*.sh                      automação     Tech / Monitoring           ativo         revisar só por incidente
scripts/mgs-rec-runner.py                 automação     Content                    ativo         não tocar agora
scripts/mgs-p1-runner.py                  automação     Content                    ativo         não tocar agora
scripts/mgs-rec-p1-orchestrator.py        automação     Content                    ativo         não tocar agora
scripts/mgs-ops-control-plane.py          automação     Executive / Ops             ativo         não tocar agora
scripts/mgs-ops-briefing.py               automação     Executive / Ops             ativo         não tocar agora
scripts/sync-souls.sh                     automação     Agents / Hermes             ativo         alterar só com validação completa
/root/.hermes/profiles/ares/scripts/creditoparaveiculo-fixed-reports.py automação Growth / Ares ativo renderer Diário/Intraday CPV, incluindo Lucro Líquido USD; teste e dry-run obrigatórios
scripts/pendencia-*.sh                    automação     Ops                         ativo         manter
scripts/mu-plugins/                       automação     WordPress                   ativo         não tocar sem plano
scripts/yoast-scorer/                     automação     Content / SEO               ativo         não tocar agora
scripts/deprecated/                       legado        Tech / Infra                legado        revisar depois
```

---

## Inventário principal — docs/

```text
Path                                      Classe        Área provável              Status        Ação recomendada
---------------------------------------- ------------- -------------------------- ------------- ---------------------------
docs/                                     histórico     Executive / Tech            ativo         manter
docs/mgs-os-restructure-plan.md           plano         Executive / MGS OS          atualizado    manter
docs/mgs-structure-inventory.md           inventário    Executive / MGS OS          v0.2          manter; base Fase 3
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
docs/CHECKPOINT-FASE-3.md                 histórico     Content / antigo            legado        revisar/arquivar depois
```

---

## Inventário principal — skills, patches, api, tools

```text
Path                                      Classe        Área provável              Status        Ação recomendada
---------------------------------------- ------------- -------------------------- ------------- ---------------------------
skills/                                   skill         Agents                     ativo         manter
skills/content-generate-rec-p1/              skill         Content / Atena             ativo         não tocar agora
skills/content-publish-wordpress/         skill         Content / WordPress         ativo         não tocar agora
patches/                                  patch local   Tech / Hermes              ativo         não tocar sem plano
patches/hermes/                           patch local   Tech / Hermes              ativo         não tocar sem plano
api/                                      runtime/API   Tech / Content              ativo         não tocar sem plano
api/generate-rec-api.py                   runtime/API   Content / WordPress         ativo         não tocar agora
api/usage.db                              runtime       API                         ativo         não tocar
tools/                                    ferramenta    Tech / Creative             auxiliar      revisar quando necessário
tools/canva-local-automation/             ferramenta    Creative / Ares             auxiliar      revisar antes de usar
```

---

## Inventário principal — backups, experiments, logs e raiz

```text
Path                                      Classe        Área provável              Status        Ação recomendada
---------------------------------------- ------------- -------------------------- ------------- ---------------------------
backups/                                  backup        Tech / Infra                histórico     manter; arquivar depois
backups/safety/                           backup        Tech / Infra                ativo         manter último snapshot válido
experiments/                              experimento   variável                   baixo risco    manter; revisar depois
experiments/honcho-spike/                 experimento   AI / memória               legado/aux     revisar depois
logs/                                     logs          Audit / Runtime             ativo         não editar; consultar só
logs/events-audit.jsonl                   audit log     Security / Ops              ativo         append-only/consulta
logs/*.log                                runtime       Tech / Infra                ativo         consultar com filtros
.env                                      sensível      Security / Access           ativo         não versionar; nunca expor
AGENT.md / CLAUDE.md                      prompt/doc    Agents / Legacy             ativo         revisar só com plano
*.bak / *~ raiz                           backup        Tech / Infra                histórico     housekeeping controla
inventario-webapps.json                   inventário    WordPress / Infra           histórico     revisar depois
```

---

## Arquivos que exigem cuidado especial

```text
Path                                      Motivo
---------------------------------------- -------------------------------------------------------
.env / auth.json / tokens / credentials   Segredos; nunca expor em chat nem versionar.
data/authorized-users.json                Fonte operacional de autorização; exige Rodolfo.
data/sites.json                           Fonte técnica dos sites; alteração pode quebrar pipeline.
profiles/*-config.yaml                    Config Hermes/gateway; risco de agente offline.
profiles/*-soul.md                        Comportamento de agente; alterar um agente por vez.
scripts/monitor-*                         Monitores/crons; risco de spam/loop se mal editado.
scripts/mgs-*-runner.py                   Pipeline de conteúdo; risco operacional.
scripts/sync-souls.sh                     Sincroniza SOUL/config/skills versionadas; risco de sujeira.
patches/hermes/                           Patch runtime Hermes/MGS; risco sistêmico.
api/                                      Pode estar ligado a runtime/API.
logs/events-audit.jsonl                   Audit trail; append-only/consulta.
logs/*.log                                Runtime; consultar com filtros, não editar.
```

---

## Ações recomendadas por classe

```text
Classe                  Regra
----------------------- -------------------------------------------------------
canônico/context        revisar por bloco pequeno e cascata semântica
runtime/data            não tocar sem plano específico, backup e validação
config/profile          alterar um agente por vez, validar gateway/logs
script/automação        dry-run/bash -n/teste real controlado antes de commitar
skill                   editar quando usada ou quando bug operacional aparecer
patch local             só mexer com plano técnico e rollback
backup                  não apagar agora; arquivar depois preservando último
experimento             baixo risco, mas classificar antes de remover
logs                    consulta/read-only; nunca limpar sem política aprovada
sensível                não versionar, não expor, não colar em chat
```

---

## Próximos blocos recomendados para Fase 4

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
9       profiles/ares-*                Revisar quando Ares avançar operacionalmente.
10      backups/                       Arquivar/limpar só após política aprovada.
```

---

## Gate para Fase 4

A Fase 4 só deve começar depois de Rodolfo aprovar este inventário como base de trabalho.

```text
Regra de migração
-----------------
1. Começar por arquivos context/*.md conceituais.
2. Depois docs operacionais.
3. Depois skills, se necessário.
4. Profiles de agentes só um por vez.
5. Scripts/runtime/data só com plano específico, backup, dry-run e validação.
6. Remoção/limpeza só depois de classificar e preservar rollback.
```
