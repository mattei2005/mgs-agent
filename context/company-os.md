# MGS OS — Arquitetura Organizacional e Operacional

> Status: **proposta inicial**  
> Dono: Zeus  
> Aprovador: Rodolfo Mattei  
> Escopo: organizar a MGS como empresa operacional antes de expandir agentes, rotas e automações.

---

## 1. Objetivo

Este documento define a camada canônica de organização da MGS Digital Corp: áreas, responsabilidades, agentes, fontes de verdade, rotas, permissões e governança.

Ele não substitui automaticamente scripts, skills, dados ou prompts existentes. A função inicial é servir como blueprint para migração incremental e segura.

---

## 2. Princípios operacionais

1. **Empresa antes de agente** — agentes executam dentro da arquitetura da empresa, não definem a empresa sozinhos.
2. **Fonte de verdade explícita** — cada assunto deve ter um local oficial de leitura/escrita.
3. **Separação de responsabilidades** — cada agente tem área, limites e autoridade claros.
4. **Governança auditável** — mudanças em produção, permissões, dinheiro, publicação e infra devem deixar rastro.
5. **Migração incremental** — não quebrar operação real para reorganizar estrutura.
6. **Segurança por padrão** — credenciais, tokens, produção e permissões exigem controle explícito.
7. **Rodolfo decide; Zeus orquestra** — decisões estratégicas e autorizações sensíveis passam pelo CEO.

---

## 3. Áreas oficiais da MGS

```text
Área             Função central
--------------- ---------------------------------------------------------------
Executive/Ops    Governança, prioridades, autorizações, auditoria e coordenação
Content          Produção editorial, REC, P1, WordPress e qualidade de conteúdo
Growth/Ads       Aquisição, campanhas, tracking, funis e mídia paga
Tech/Infra       VPS, Hermes, bots, crons, patches, WordPress técnico e serviços
Data/BI          Métricas, relatórios, custos, performance e inteligência operacional
Finance          Receita, custos, ROI, monetização e análise econômica
Security         Acessos, credenciais, hardening, permissões e políticas de risco
```

---

## 4. Mapa inicial de agentes

```text
Agente   Área primária    Papel
-------  --------------- ------------------------------------------------------
Zeus     Executive/Ops    General Manager, governança, roteamento e auditoria
Atena    Content          Produção editorial, REC/P1, publicação e QA WordPress
Ares     Growth/Ads       Campanhas, aquisição, anúncios, tracking e funis
Futuros  A definir        Especialistas subordinados ao mapa MGS OS
```

### 4.1 Regra de autoridade

- **Zeus** coordena e autoriza, mas não deve virar executor operacional de conteúdo/campanha por padrão.
- **Atena** executa conteúdo e WordPress conforme playbooks aprovados.
- **Ares** executa Growth/Ads conforme playbooks aprovados.
- Agente novo só deve ser criado depois de existir área, missão, fontes de verdade e limites.

---

## 5. Fontes de verdade atuais

```text
Assunto                  Fonte atual
------------------------ ------------------------------------------------------
Empresa                  /root/mgs-agent/context/company.md
Sites/verticais          /root/mgs-agent/context/sites.md
Config técnica sites     /root/mgs-agent/data/sites.json
Equipe                   /root/mgs-agent/context/team.md
Permissões               /root/mgs-agent/data/authorized-users.json
Processos                /root/mgs-agent/context/processes.md
Monetização              /root/mgs-agent/context/monetization.md
Aquisição                /root/mgs-agent/context/acquisition.md
Segurança                /root/mgs-agent/context/security-policies.md
Crons                    /root/mgs-agent/docs/CRONS.md
Pendências               /root/mgs-agent/docs/PENDENCIAS.md
Changelog                /root/mgs-agent/docs/CHANGELOG.md + docs/changelog/
Conteúdo REC/P1          /root/mgs-agent/skills/content-generate-rec/
Publicação WordPress     /root/mgs-agent/skills/content-publish-wordpress/
Scripts operacionais     /root/mgs-agent/scripts/
Patches Hermes/MGS       /root/mgs-agent/patches/hermes/
Audit log                /root/mgs-agent/logs/events-audit.jsonl
```

---

## 6. Fontes de verdade alvo

A estrutura alvo deve separar conceito, operação e runtime.

```text
Camada                 Local alvo sugerido
---------------------- --------------------------------------------------------
Arquitetura empresa     /root/mgs-agent/context/company-os.md
Áreas                   /root/mgs-agent/context/areas/
Rotas                   /root/mgs-agent/context/routes.md
Agentes                 /root/mgs-agent/context/agent-map.md
Fontes de verdade       /root/mgs-agent/context/sources-of-truth.md
Permissões              /root/mgs-agent/context/permissions-matrix.md + data/authorized-users.json
Playbooks               /root/mgs-agent/context/playbooks/
Dados operacionais      /root/mgs-agent/data/
Automações              /root/mgs-agent/scripts/
Skills por função       /root/mgs-agent/skills/
Docs históricas         /root/mgs-agent/docs/
Legado/arquivo morto    /root/mgs-agent/archive/ ou data/deprecated/ conforme caso
```

Regra: `context/` explica como a empresa funciona; `data/` guarda estado/dados; `scripts/` executa; `skills/` ensina agente a executar; `docs/` documenta histórico, pendências e mudanças.

---

## 7. Rotas operacionais iniciais

```text
Pedido/evento                         Rota primária      Escala para Zeus?
------------------------------------- ------------------ -----------------------
Pedido de conteúdo REC/P1             Atena              Se envolver prioridade, erro crítico ou permissão
Publicação/edição WordPress           Atena              Se envolver risco, credencial, rollback ou incidente
Campanha/anúncio/tracking             Ares               Se envolver budget, acesso ou decisão estratégica
Usuário externo pedindo acesso        Zeus               Sempre
Erro de agente/bot/Hermes             Tech/Infra + Zeus  Sempre se afetar operação
Mudança em permissões                 Zeus               Sempre; exige confirmação de Rodolfo
Mudança em produção/site              Dono da área        Zeus se alto risco
Relatório executivo                   Zeus               Zeus consolida
Custo/token/API                       Data/BI + Zeus     Se anormal ou crescente
Credencial/token/segredo              Security + Zeus    Sempre
```

---

## 8. Matriz inicial de permissões

```text
Tipo de ação                         Quem pode propor       Quem aprova
------------------------------------ ---------------------- --------------------
Criar conteúdo                       Atena                  Playbook ou Rodolfo
Publicar conteúdo                    Atena                  Conforme regra editorial vigente
Criar campanha                       Ares                   Rodolfo até política formal existir
Alterar budget                       Ares/Zeus              Rodolfo
Autorizar usuário externo            Zeus                   Rodolfo
Alterar authorized-users.json         Zeus                   Rodolfo confirmado
Editar prompts/SOUL/config agente     Zeus/Tech             Rodolfo se crítico
Restart gateway/agente               Zeus/Tech             Rodolfo quando em thread ativa/sensível
Alterar crons/scripts produtivos      Zeus/Tech             Rodolfo se risco operacional
Mexer em credenciais                 Security/Zeus          Rodolfo; nunca expor segredo
Remover arquivo estrutural            Zeus/Tech             Rodolfo após plano de migração
```

---

## 9. Classificação de arquivos

```text
Classe        Definição                                      Exemplo
------------ ---------------------------------------------- --------------------
Canônico      Fonte oficial atual                            context/*.md, data/sites.json
Runtime       Estado gerado/atualizado pela operação          data/*-state.json, logs/*.jsonl
Automação     Código/script usado pela operação               scripts/*.sh, scripts/*.py
Skill         Procedimento reutilizável para agente           skills/*/SKILL.md
Histórico     Registro de mudança, decisão ou fechamento      docs/changelog/*
Backup        Cópia de segurança temporária ou pré-migração   backups/*
Legado        Mantido por referência, não usado ativamente     data/deprecated/*
Experimento   Spike/prova de conceito                         experiments/*
Patch local   Customização MGS em Hermes/runtime              patches/hermes/*
```

---

## 10. Plano de migração seguro

### Fase 1 — Blueprint

- Criar este documento.
- Validar áreas, agentes e rotas com Rodolfo.
- Não alterar runtime.

### Fase 2 — Inventário classificado

- Classificar arquivos atuais em: canônico, runtime, automação, histórico, backup, legado, experimento, patch.
- Produzir tabela de migração por arquivo/pasta.
- Não mover nada ainda.

### Fase 3 — Separação de contexto

- Criar `context/areas/`, `context/routes.md`, `context/sources-of-truth.md`, `context/agent-map.md`, `context/permissions-matrix.md`.
- Migrar conteúdo conceitual duplicado de forma controlada.
- Manter redirects/notas nos arquivos antigos quando necessário.

### Fase 4 — Ajuste dos agentes

- Atualizar Zeus/Atena/Ares para lerem as novas fontes canônicas.
- Validar comportamento em Discord e logs.
- Não remover contexto antigo até estabilidade comprovada.

### Fase 5 — Limpeza

- Arquivar backups antigos e experimentos não ativos.
- Consolidar docs duplicadas.
- Remover apenas com aprovação explícita.

---

## 11. Decisões pendentes para Rodolfo

```text
Decisão                                      Opção recomendada por Zeus
------------------------------------------- -----------------------------------
Áreas iniciais                              Usar as 7 áreas deste documento
Zeus como GM/orquestrador                   Sim
Atena restrita a Content/WordPress           Sim
Ares restrito a Growth/Ads                   Sim
Criar camada context/areas + routes          Sim
Migrar sem quebrar arquivos atuais           Sim
Remover legado automaticamente               Não; só após plano aprovado
```

---

## 12. Próximo passo após aprovação deste blueprint

Gerar o inventário classificado de `/root/mgs-agent` com uma linha por pasta/arquivo estrutural relevante:

```text
Path | Classe | Dono | Área | Status | Ação recomendada
```

Ações possíveis: `manter`, `mover`, `renomear`, `consolidar`, `arquivar`, `remover depois`, `não tocar`.
