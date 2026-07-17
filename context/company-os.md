# MGS OS — Arquitetura Organizacional e Operacional

> Status: **proposta canônica v0.2**  
> Base: modelo operacional real explicado por Rodolfo Mattei.  
> Dono executivo: Rodolfo Mattei.  
> Orquestração: Zeus.  
> Regra: este documento orienta a reorganização; não altera automaticamente agentes, scripts, permissões ou produção.

---

## 1. Por que este documento existe

A MGS cresceu como operação real: sites, WordPress, conteúdo, campanhas, gestores, monetização, financeiro, Smart Bidding, ActiveView, criações, agentes e automações.

A próxima fase exige organizar a empresa como um **sistema operacional empresarial** antes de expandir agentes.

Objetivo do MGS OS:

1. separar áreas da empresa;
2. definir quem cuida do quê;
3. mapear fontes de verdade;
4. padronizar rotas de pedidos;
5. controlar permissões e riscos;
6. encaixar Zeus, Atena, Ares e agentes futuros dentro da estrutura real;
7. permitir crescimento sem bagunça operacional.

---

## 2. Princípios do MGS OS

```text
Princípio                     Regra prática
----------------------------- ------------------------------------------------
Empresa antes de agente        Primeiro definimos áreas, rotas e autoridade.
Fonte de verdade explícita     Cada dado importante tem um local oficial.
Humano dono, agente executor    Agentes não substituem autoridade humana sem regra.
Migração incremental           Nada de mover/remover arquivos produtivos em massa.
Segurança por padrão           Credenciais, permissões e produção exigem controle.
Auditoria sempre               Decisões, acessos e mudanças relevantes deixam rastro.
ROI e operação conectados      Conteúdo, campanha e monetização precisam conversar.
```

---

## 3. Sócios e liderança

```text
Pessoa        Papel atual
------------ ---------------------------------------------------------------
Rodolfo       CEO; gestão geral, financeiro, estrutura WordPress, pixels,
              relacionamento com redes, estratégia, arquitetura operacional
              e comando da operação dos agentes AI.
Geizian       Sócio; acompanha gestores, rotina diária de campanhas, custos,
              performance e execução junto ao time.
```

---

## 4. Áreas oficiais da MGS

```text
Área                         Função central
---------------------------- -------------------------------------------------
Executive / Management        Direção, estratégia, prioridades, reuniões,
                              decisões, coordenação geral e governança.
Office / Follow-up             Cobrança, acompanhamento de tarefas pendentes
                              dos gestores e disciplina operacional.
Content Operations            Produção de conteúdo, REC/P1, SEO, categorias,
                              WordPress editorial e rotina de publicação.
Creative Ops + Growth        Criativos, Drive, Facebook/Google Ads, tráfego direto,
                              gestores, custos, ROI e aquisição via Ares.
Acquisition systems           ChatPion, quiz e SMS continuam com Rodolfo/Geizian/gestores, fora do setup do Ares.
Revenue / AdOps               Smart Bidding, ActiveView, AdManager, AdX,
                              blocos de anúncio, precificação e monetização.
Finance / BI                  Relatórios recebidos, planilhas alimentadas por Rodolfo,
                              custos, receita, comissões, salários, despesas e ROI.
Tech / WordPress / Infra      WordPress técnico, sites, plugins, pixels,
                              VPS, Hermes, bots, crons, scripts e patches.
Security / Access             Credenciais, acessos, permissões, dashboards,
                              APIs, hardening e política de risco.
```

---

## 5. Pessoas e responsabilidades atuais

```text
Pessoa/grupo       Área principal             Responsabilidade
------------------ -------------------------- ---------------------------------
Rodolfo            Executive / Finance / Tech Gestão geral, financeiro,
                                              arquitetura, WordPress, pixels,
                                              redes, agentes, decisões e prioridades.
Geizian            Executive / Growth         Sócio; gestão dos gestores, rotina
                                              de campanhas, custos e performance.
Ially              Office / Follow-up         Gerente do escritório; cobrança e
                                              acompanhamento de tarefas dos gestores.
Raquel             Content Operations         Produção de conteúdo; supervisão
                                              operacional da Atena.
Gestores           Growth / Content           Operam sites/campanhas, acompanham
                                              custos, ROI e contato com AdOps.
Kelly              Creative Operations        Pessoa responsável por criativos com AI/Canva
                                              para gestores usarem em campanhas.
Smart Bidding      Revenue / AdOps            Parceiro Google/AdX; rede e dash
                                              principal para gerenciamento.
ActiveView         Revenue / AdOps            Parceiro Google/AdX; exceção ativa
                                              para openzed/cliquet/subdomínios.
```

---

## 6. Modelo operacional de sites

A MGS opera mais de 30 sites em múltiplos países, nichos e idiomas. Cada combinação operacional pode ser tratada como uma vertical.

Exemplo:

```text
Site      País             Nicho              Idioma
-------- ----------------- ------------------ -------
EggBev    GB/Reino Unido   Credit Cards/CC    EN
```

Fluxo estrutural de um site:

```text
Etapa       Responsável provável       Descrição
---------- --------------------------- ----------------------------------------
Setup       Tech / WordPress / Rodolfo Instalar/configurar WordPress, plugins,
                                       home, categorias e pixels.
Conteúdo    Content / Raquel / Atena   Publicar REC/P1 e preencher categorias.
SEO         Content                    Artigos de ~1.200 palavras quando há
                                       categorias adicionais a preencher.
Aprovação   Revenue / Rodolfo          Enviar site para aprovação nas redes.
Blocos      Revenue / AdOps            Criar/ajustar blocos de anúncio e regras.
Campanhas   Growth / gestores / Ares   Rodar/analisar campanhas de mídia paga e tráfego direto conforme escopo aprovado.
ROI         Growth + Revenue + Finance Acompanhar custo, receita e performance.
```

---

## 7. Monetização e AdOps

```text
Sistema/rede       Papel no MGS OS
----------------- -------------------------------------------------------------
Smart Bidding      Fonte operacional principal para gerenciamento de sites,
                   campanhas, ROI, blocos, tecnologia e relatórios.
ActiveView         Exceção ativa para openzed, cliquet e seus subdomínios,
                   quando ainda estiverem na tecnologia/rede AV.
AdManager/AdX      Camada de monetização Google dentro das redes parceiras
                   Smart Bidding e ActiveView.
Discord AdOps      Canal operacional com Smart Bidding para regras, aprovação,
                   precificação e acompanhamento dos blocos.
```

Regra canônica inicial:

- Smart Bidding é a dashboard/rede principal de gerenciamento operacional.
- ActiveView deve ser tratada como exceção ativa apenas para sites que ainda estejam na tecnologia AV: openzed, cliquet e subdomínios.
- Alterações de blocos, regras e precificação pertencem a Revenue / AdOps.
- Impactos financeiros pertencem a Finance / BI.

---

## 8. Aquisição, campanhas e criativos

```text
Camada                 Ferramentas / canais
---------------------- --------------------------------------------------------
Media buying           Facebook Ads, Google Ads, TikTok e tráfego direto
ChatPion/Messenger     DigitalTrChat/ChatPion; cadastro por Rodolfo/Geizian e configuração operacional por gestores
Quiz/SMS               Estrutura montada/configurada por Rodolfo usando SMS Funnel quando aplicável
Criativos estáticos    Ares, Kelly humana e providers aprovados
Vídeos                 Ares e providers aprovados
Criativos futuros      Ferramentas/APIs testadas e aprovadas
Gestão                 Rodolfo + Geizian + gestores; Ares em implantação progressiva para campanhas
```

Fluxo de criativos:

```text
1. Kelly/Rodolfo/Geizian/gestor pede ou envia criativo ao Ares.
2. Ares cria/trata/sanitiza/nomeia e registra a linhagem.
3. Kelly/Rodolfo/gestor aprovam quando o fluxo exigir.
4. Ares salva no Drive, controla reserva/elegibilidade e conecta o asset às campanhas.
5. Ares lê/escreve no Drive de criativos aprovados e usa/gerencia assets em testes/campanhas.
6. Geizian acompanha execução/performance.
7. Rodolfo acompanha visão geral, ROI e financeiro.
```

Fluxo alvo com agentes:

```text
Ares           -> cria/organiza criativos e analisa/sobe/acompanha campanhas conforme permissão; não configura ChatPion, quiz ou SMS Funnel
Zeus           -> monitora, audita, escala exceções e reporta para Rodolfo
```

---

## 9. Financeiro e BI

Rodolfo é o dono atual do financeiro.

```text
Item                     Regra atual
------------------------ ------------------------------------------------------
Período analisado         Dia 1 ao dia 30
Pagamento Google          Entre dia 21 e dia 23
Controle principal        Planilha financeira do Rodolfo
Conferência de mídia      Facebook Business Manager e contas de anúncio
Conferência de receita    Smart Bidding / ActiveView / relatórios
Conferência de risco      Tráfego inválido por site
Saídas financeiras        Comissões, salários e despesas da empresa
```

No MGS OS, Finance / BI deve conectar:

- gasto por campanha;
- receita por site/vertical;
- tráfego inválido;
- ROI;
- comissões;
- salários;
- despesas;
- fechamento mensal.

---

## 10. Agentes no MGS OS

```text
Agente               Área primária             Papel
------------------- -------------------------- --------------------------------
Zeus                 Executive / Management    General Manager, orquestrador,
                                              governança, autorizações,
                                              auditoria, roteamento e reports.
Atena                Content Operations        Gestora/agente de conteúdo;
                                              REC/P1, SEO, WordPress editorial,
                                              sob supervisão da Raquel.
Ares                 Creative Ops + Growth    Criativos, Drive, campanhas, análise e
                                              operação de aquisição.
Futuros agentes      Área específica           Só devem nascer com área, dono,
                                              fontes, permissões e rotas claras.
```

---

## 11. Fontes de verdade atuais

```text
Assunto                  Fonte atual
------------------------ ------------------------------------------------------
Empresa                  /root/mgs-agent/context/company.md
Modelo real atual         /root/mgs-agent/context/company-current-operating-model.md
Arquitetura MGS OS        /root/mgs-agent/context/company-os.md
Sites/verticais           /root/mgs-agent/context/sites.md
Config técnica sites      /root/mgs-agent/data/sites.json
Equipe                    /root/mgs-agent/context/team.md
Permissões                /root/mgs-agent/data/authorized-users.json
Processos                 /root/mgs-agent/context/processes.md
Monetização               /root/mgs-agent/context/monetization.md
Aquisição                 /root/mgs-agent/context/acquisition.md
Segurança                 /root/mgs-agent/context/security-policies.md
Crons                     /root/mgs-agent/docs/CRONS.md
Pendências                /root/mgs-agent/docs/PENDENCIAS.md
Conteúdo REC/P1           /root/mgs-agent/skills/content-generate-rec-p1/
Publicação WordPress      /root/mgs-agent/skills/content-publish-wordpress/
Scripts operacionais      /root/mgs-agent/scripts/
Patches Hermes/MGS        /root/mgs-agent/patches/hermes/
Audit log                 /root/mgs-agent/logs/events-audit.jsonl
```

---

## 12. Fontes de verdade alvo

```text
Documento alvo                        Função
------------------------------------- -----------------------------------------
context/company-os.md                  Arquitetura geral da empresa.
context/areas.md                       Áreas, donos e responsabilidades.
context/agent-map.md                   Agentes, escopos, limites e supervisores.
context/routes.md                      Roteamento de pedidos/eventos.
context/sources-of-truth.md            Onde cada dado deve ser lido/escrito.
context/permissions-matrix.md          Matriz de autoridade e permissões.
context/knowledge-governance.md        Classificação, promoção e continuidade.
context/playbooks/                     Playbooks por área/processo.
data/*.json                            Estado/dados operacionais.
data/knowledge-registry.json           Índice institucional e supersessão.
data/agent-checkpoints.json            Continuidade de iniciativas.
scripts/                               Automações executáveis.
skills/                                Procedimentos reutilizáveis de agentes.
docs/                                  Histórico, changelog, pendências e crons.
```

---

## 13. Rotas operacionais iniciais

```text
Pedido/evento                          Rota primária          Escala para Zeus?
-------------------------------------- ---------------------- -----------------
Criar/editar REC/P1                    Atena / Content        Se prioridade,
                                                              erro ou exceção.
Publicar/ajustar WordPress editorial   Atena / Content        Se risco técnico.
Montar site/plugin/pixel               Tech / Rodolfo         Sim se produção.
Criar/tratar criativo                 Ares / Kelly humana    Escala se risco ou
                                                              ferramenta nova.
Subir/analisar campanha                Gestor / Ares          Se budget, risco
                                                              ou decisão.
Ajustar blocos/preço AdOps             Revenue / SmartBidding Sim se impacto ROI.
Conferir ROI                           Growth + Revenue + BI  Sim em anomalias.
Fechamento financeiro                  Rodolfo / Finance      Zeus reporta se
                                                              houver automação.
Autorizar usuário externo              Zeus                   Sempre Rodolfo.
Mexer em credencial/API/dashboard      Security / Zeus        Sempre Rodolfo.
Erro de agente/Hermes/VPS              Tech / Zeus            Sempre se crítico.
```

---

## 14. Matriz inicial de autoridade

```text
Ação                                  Pode executar/propor      Aprovação
------------------------------------- ------------------------ -----------------
Conteúdo REC/P1                       Atena/Raquel             Playbook/Raquel
Artigo SEO                            Atena/Raquel             Playbook/Raquel
Publicação WordPress editorial        Atena                    Regra editorial
Setup técnico WordPress/site          Rodolfo/Tech             Rodolfo
Campanhas Facebook/Google/TikTok      Gestores/Ares            Geizian/Rodolfo
Criativos                             Ares/Kelly humana        Gestor/Rodolfo
Budget de mídia                       Gestores/Ares            Rodolfo/Geizian
Blocos e regras AdOps                 Smart Bidding/Revenue    Rodolfo/gestor
Fechamento financeiro                 Rodolfo                  Rodolfo
Permissão de usuário externo          Zeus                     Rodolfo confirmado
Credenciais/tokens                    Security/Zeus            Rodolfo confirmado
Alterar agente/config/runtime         Zeus/Tech                Rodolfo se crítico
Remover/mover arquivo estrutural       Zeus/Tech                Rodolfo aprovado
```

---

## 15. Classificação de arquivos da reestruturação

```text
Classe        Definição                                      Exemplo
------------ ---------------------------------------------- -------------------
Canônico      Fonte oficial atual                            context/*.md
Runtime       Estado gerado pela operação                     data/*-state.json
Automação     Script/código ativo                             scripts/*.sh/.py
Skill         Procedimento de agente                          skills/*/SKILL.md
Histórico     Changelog/fechamento/registro                   docs/changelog/*
Backup        Cópia pré-migração                              backups/*
Legado        Mantido por referência, não ativo                data/deprecated/*
Experimento   Spike/prova de conceito                         experiments/*
Patch local   Customização Hermes/MGS                         patches/hermes/*
Sensível      Segredo/config com credencial                    .env, tokens
```

---

## 16. Plano de execução

```text
Fase   Entregável                                  Regra
------ ------------------------------------------- -----------------------------
0      Captura do modelo real                      Concluído em company-current-operating-model.md
1      Company OS real                             Este documento
2      Arquivos separados por área/rota/fonte       Criar sem quebrar antigos
3      Inventário classificado                     Uma linha por arquivo/pasta
4      Plano de migração                           Manter/mover/arquivar/etc.
5      Ajuste de agentes                           Um agente por vez
6      Validação operacional                       Discord, logs, scripts
7      Limpeza                                     Só com aprovação explícita
```

---

## 17. Próxima ação concreta

Criar os documentos separados derivados deste MGS OS:

```text
context/areas.md
context/agent-map.md
context/routes.md
context/sources-of-truth.md
context/permissions-matrix.md
```

Esses documentos serão a base que Zeus, Atena, Ares e agentes futuros deverão consultar depois da aprovação.
