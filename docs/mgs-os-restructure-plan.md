# Plano de Reestruturação — MGS OS

> Status: plano de execução v0.3, Fase 4 contextual concluída.
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

## Fase 4 — Plano de migração por bloco

Para cada arquivo/pasta relevante, decidir destino e risco.

Regras:

- nada de movimento em massa;
- migrar por blocos pequenos;
- manter rollback;
- validar depois de cada bloco;
- registrar decisões relevantes.

---

## Fase 5 — Ajustar agentes

Depois da aprovação da camada canônica:

```text
Agente   Ajuste esperado
-------  ----------------------------------------------------------------------
Zeus     Ler MGS OS como fonte gerencial principal; reportar por área/rota.
Atena    Ler Content Operations, WordPress editorial, REC/P1 e fontes de conteúdo.
Ares     Ler Growth, campanhas, criativos, ROI e permissões conforme escopo aprovado.
Futuros  Só nascer com área, dono, fontes, permissões e escalonamento definidos.
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

Revisar/aprovar os documentos derivados da camada canônica:

```text
context/areas.md
context/agent-map.md
context/routes.md
context/sources-of-truth.md
context/permissions-matrix.md
```

Depois disso, gerar o inventário classificado antes de qualquer migração de arquivos ou ajuste de agentes.
