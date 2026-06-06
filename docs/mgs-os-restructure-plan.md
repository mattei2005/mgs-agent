# Plano de Reestruturação — MGS OS

> Status: plano de execução v0.2, alinhado ao modelo operacional real.  
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
Arquitetura MGS OS                         Criada como proposta canônica v0.2 em context/company-os.md
Documentos derivados                       Em criação/revisão
Inventário classificado                    Pendente
Migração de arquivos produtivos            Não iniciada
Ajuste de agentes                          Não iniciado
Limpeza/consolidação                        Não iniciada
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
Status: concluída/parcial
Saída:  context/company-os.md
```

O `company-os.md` consolida a estrutura real da empresa em áreas, agentes, fontes, rotas e permissões iniciais.

Pendente nesta fase: Rodolfo aprovar ou ajustar o documento como base canônica.

---

## Fase 2 — Documentos derivados canônicos

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

Gerar inventário dos arquivos estruturais atuais:

```text
Path | Classe | Área | Dono | Status | Ação recomendada
```

Classes permitidas:

```text
canônico | runtime | automação | skill | histórico | backup | legado | experimento | patch | sensível/não-versionar
```

Ações permitidas:

```text
manter | não tocar | mover | renomear | consolidar | arquivar | remover depois | revisar com Rodolfo
```

Regra: arquivos sensíveis ou runtime ativo entram como `não tocar` até existir plano específico aprovado.

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
