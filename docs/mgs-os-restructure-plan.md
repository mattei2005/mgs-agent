# Plano de Reestruturação — MGS OS

> Status: plano de execução v0.4, Fase 4 contextual concluída; estado de agentes reconciliado em 2026-07-15.
> Base: `context/company-current-operating-model.md` e `context/company-os.md`.
> Regra: nenhuma automação/agente/arquivo produtivo será removido ou movido sem inventário, aprovação e validação.

---

## Objetivo

Reestruturar a MGS como um sistema operacional empresarial antes de expandir agentes: áreas, rotas, fontes de verdade, permissões, dados, playbooks e agentes.

A reorganização deve preservar a operação atual. Primeiro criamos a camada canônica da empresa; depois inventariamos; só então migramos ou ajustamos agentes.

---

## Estado atual

```text
Item                                      Status
---------------------------------------- ---------------------------------------
Modelo operacional real                   Concluído em context/company-current-operating-model.md
Arquitetura MGS OS                         Concluída como proposta operacional atual
Documentos derivados                       Concluídos como proposta operacional atual
Inventário classificado                    Concluído em docs/mgs-structure-inventory.md
Fase 4 — revisão contextual                Concluída nos blocos 1–7
Migração física de arquivos produtivos      Não iniciada; exige plano específico
Ajuste de agentes                          Próximo gate: Fase 5
Limpeza/consolidação                        Não iniciada; só com aprovação explícita
```

---

## Áreas oficiais propostas

```text
Área                         Função central
---------------------------- -------------------------------------------------
Executive / Management        Direção, estratégia, prioridades, governança.
Content Operations            REC/P1, SEO, categorias e WordPress editorial.
Growth / Media Buying         Facebook Ads, Google Ads, TikTok, SMS, ChatPion,
                              quiz, tráfego direto, gestores, custos e ROI.
Creative Operations           Kelly, Canva, ChatGPT, TopView.ai, Grok ou outras
                              AIs aprovadas para criativos estáticos/vídeos.
Revenue / AdOps               Smart Bidding, ActiveView, AdManager/AdX, blocos,
                              precificação, aprovação e monetização.
Finance / BI                  Planilha financeira, relatórios, receita, custos,
                              comissões, salários, despesas e ROI.
Tech / WordPress / Infra      WordPress, sites, plugins, pixels, VPS, Hermes,
                              bots, crons, scripts e patches.
Security / Access             1Password, permissões, credenciais, dashboards,
                              APIs, hardening e política de risco.
```

---

## Fase 0 — Captura do modelo real

```text
Status: concluída
Saída:  context/company-current-operating-model.md
```

A fala do Rodolfo virou a fonte primária do modelo atual da MGS.

---

## Fase 1 — Arquitetura MGS OS

```text
Status: concluída como proposta operacional atual
Saída:  context/company-os.md
```

O `company-os.md` consolida a estrutura real da empresa em áreas, agentes, fontes, rotas e permissões iniciais.

Status operacional: base suficiente para avançar para inventário, mantendo ajustes futuros por correção/cascata quando Rodolfo apontar mudanças.

---

## Fase 2 — Documentos derivados canônicos

```text
Status: concluída como proposta operacional atual
Saídas: context/areas.md
        context/agent-map.md
        context/routes.md
        context/sources-of-truth.md
        context/permissions-matrix.md
```

Criar/revisar os arquivos separados que os agentes deverão consultar depois da aprovação:

```text
context/areas.md
context/agent-map.md
context/routes.md
context/sources-of-truth.md
context/permissions-matrix.md
context/playbooks/
```

Regra: esta fase é aditiva. Não move, remove ou substitui arquivo produtivo.

---

## Fase 3 — Inventário classificado

```text
Status: concluída
Saída:  docs/mgs-structure-inventory.md
```

O inventário classificado foi criado como mapa de risco da estrutura `/root/mgs-agent`.

Regra: o inventário é read-only. Ele classifica e recomenda, mas não move, remove nem altera runtime.

Classes usadas:

```text
canônico | runtime | automação | skill | histórico | backup | legado | experimento | patch | sensível/não-versionar
```

Ações permitidas:

```text
manter | não tocar | mover | renomear | consolidar | arquivar | remover depois | revisar com Rodolfo
```

Arquivos sensíveis ou runtime ativo seguem como `não tocar` até existir plano específico aprovado.

---

## Fase 4 — Revisão contextual por bloco

```text
Status: concluída
Escopo: arquivos conceituais/controle; sem migração física de runtime.
```

Blocos executados:

```text
Bloco   Arquivo / área                         Resultado
------  -------------------------------------- ---------------------------------
1       context/company.md                      Visão geral alinhada ao MGS OS.
2       context/team.md + agent-map             Equipe, gestores, agentes e acesso.
3       context/acquisition.md                  Ares, Ads, ChatPion, quiz/SMS.
4       context/monetization.md                 Smart Bidding, ActiveView, AdOps.
5       context/processes.md                    Fluxos operacionais consolidados.
6       context/sites.md                        Sites/verticais e limite data/sites.
7       docs/CRONS.md + cron-control-plane      Inventário de crons sem alterar runtime.
```

Regras mantidas:

- nada de movimento em massa;
- nenhuma alteração de crontab/runtime na revisão de `docs/CRONS.md`;
- validação depois de cada bloco;
- audit log em `logs/events-audit.jsonl`;
- auto-push verificado com `HEAD == origin/main`.

Observação: Fase 4 concluiu a revisão contextual inicial. Migração física, limpeza, arquivamento ou alteração de agentes ficam para fases/gates próprios.

---

## Fase 5 — Ajustar agentes

```text
Status: em execução controlada; Zeus concluído no primeiro gate.
Regra: alterar um agente por vez.
```

Depois da aprovação da camada canônica:

```text
Agente   Status                         Ajuste esperado
-------  -----------------------------  ---------------------------------------
Zeus     Concluído                       Lê MGS OS como fonte gerencial principal;
                                         reporta por área/rota e respeita fontes.
Atena    Próximo gate recomendado        Ler Content Operations, WordPress editorial,
                                         REC/P1 e fontes de conteúdo.
Ares     Ativo e consolidado             Creative Ops + Growth/Campaign Ops conforme
                                         mapa atual e permissões aprovadas.
Futuros  Pendente                        Só nascer com área, dono, fontes, permissões
                                         e escalonamento definidos.
```

Gate antes de executar Fase 5:

```text
Decisão                         Recomendação Zeus
------------------------------- ------------------------------------------------
Primeiro agente                 Zeus.
Tipo de ajuste                  Referenciar MGS OS/context sem apagar contexto antigo.
Validação                       Resposta curta no Discord + logs sem erro novo.
Rollback                        Backup/diff do profile antes de alterar.
Escopo proibido nesta etapa      Não mexer em crontab, tokens, runtime ou permissões.
```

Regras:

- alterar um agente por vez;
- validar resposta no Discord;
- validar logs;
- manter rollback;
- não apagar contexto antigo até estabilidade.

---

## Fase 6 — Validação operacional

Validar que a nova camada não quebrou a operação:

```text
Área validada                 Como validar
----------------------------- ------------------------------------------------
Discord                       Zeus/Atena respondem no canal/thread correto.
Autorizações                  authorized-users.json segue como fonte de verdade.
Conteúdo                      Atena mantém REC/P1/WordPress sem regressão.
Crons/monitores               Sem loops, spam ou alertas falsos.
Logs                          events-audit e logs dos agentes continuam úteis.
Hermes/VPS                    Serviços ativos e sem erro crítico novo.
```

---

## Fase 7 — Limpeza e consolidação

Só depois de tudo validado e com aprovação explícita:

- arquivar backups antigos;
- consolidar docs duplicadas;
- remover scripts deprecated realmente mortos;
- padronizar nomes;
- documentar changelog final.

---

## Próximo passo imediato

A Fase 4 contextual está concluída e Zeus já passou pelo primeiro gate da Fase 5. Ajustes futuros devem seguir o mapa atual: Atena e Ares são agentes ativos e agentes legados não devem ser recriados como operação nova.

A nova frente de preservação de contexto está documentada em `docs/mgs-knowledge-continuity-plan.md`. Qualquer mudança de comportamento nos agents continua sendo executada um agente por vez, com gate, rollback e validação próprios.
