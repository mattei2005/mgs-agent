# Conteúdo dos arquivos obrigatórios — redigido contra segredos
Este arquivo cola o conteúdo dos arquivos obrigatórios para análise externa. Campos com nomes de segredo são redigidos.


---

# FILE: `/root/mgs-agent/context/company-os.md`

```text
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
Growth / Media Buying         Campanhas, Facebook Ads, Google Ads, TikTok, SMS, ChatPion, quiz e tráfego direto,
                              gestores, custos, ROI e aquisição.
Creative Operations           Criativos estáticos, vídeos, Canva, ChatGPT,
                              TopView.ai, Hera e Google Drive de criativos.
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
Criativos estáticos    Hera, Kelly humana, ChatGPT, Canva
Vídeos                 Hera, TopView.ai
Criativos futuros      Grok ou outras AIs com API/acesso permitido
Gestão                 Rodolfo + Geizian + gestores; Ares em implantação progressiva para campanhas
```

Fluxo de criativos:

```text
1. Kelly humana pede/cria/avalia criativos para gestores.
2. Hera cria/organiza assets usando ferramentas aprovadas.
3. Kelly/Rodolfo/gestor aprovam conforme o fluxo.
4. Hera salva o criativo aprovado na pasta correta do Google Drive.
5. Ares lê/escreve no Drive de criativos aprovados e usa/gerencia assets em testes/campanhas.
6. Geizian acompanha execução/performance.
7. Rodolfo acompanha visão geral, ROI e financeiro.
```

Fluxo alvo com agentes:

```text
Hera           -> cria/organiza criativos aprovados no Drive
Ares           -> analisa/sobe/acompanha campanhas conforme permissão; não configura ChatPion, quiz ou SMS Funnel
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
Ares                 Growth / Media Buying     Campanhas, análise, criação e
                                              operação de aquisição.
Hera                 Creative Operations       Criativos estáticos/vídeos via
                                              ChatGPT, TopView.ai, Canva, Grok se testado/aprovado
                                              ou outras APIs aprovadas.
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
context/playbooks/                     Playbooks por área/processo.
data/*.json                            Estado/dados operacionais.
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
Criar criativo                         Hera / Kelly humana    Escala se risco ou
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
Criativos                             Hera/Kelly humana        Gestor/Rodolfo
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

```


---

# FILE: `/root/mgs-agent/context/areas.md`

```text
# MGS OS — Áreas Oficiais

> Status: proposta canônica v0.2
> Fonte-mãe: `context/company-os.md`
> Base operacional: `context/company-current-operating-model.md`

## Mapa executivo

```text
Área                         Dono humano atual          Função central
---------------------------- ------------------------- ---------------------------------------------
Executive / Management        Rodolfo + Geizian         Direção, prioridades, reuniões e governança.
Office / Follow-up             Ially                     Cobrança e acompanhamento de tarefas dos gestores.
Content Operations            Raquel                    Conteúdo, REC/P1, SEO e WordPress editorial.
Growth / Media Buying         Rodolfo + Geizian +       Campanhas, arbitragem, custos, aquisição e ROI.
                              gestores
Creative Operations           Kelly + Geizian           Criativos, Canva, ChatGPT, TopView.ai e AIs.
Revenue / AdOps               Rodolfo + Geizian +       Smart Bidding, ActiveView, AdX, blocos e regras.
                              gestores
Finance / BI                  Rodolfo                   Fechamento, custos, receita, ROI e pagamentos.
Tech / WordPress / Infra      Rodolfo + Zeus/Tech       Sites, plugins, pixels, Hermes, VPS e scripts.
Security / Access             Rodolfo + Zeus            Credenciais, acessos, permissões e risco.
```

## Executive / Management

Direção estratégica, prioridades, reuniões diárias, decisões finais, criação/remoção de áreas e agentes, governança e resolução de conflitos entre áreas.

Rodolfo mantém autoridade final e comanda a operação dos agentes AI. Geizian é sócio de Rodolfo e acompanha a rotina de gestores, campanhas, custos e performance.

## Office / Follow-up

Cobrança e acompanhamento de tarefas pendentes dos gestores, follow-up operacional e apoio à disciplina de execução do escritório.

Ially é a gerente do escritório responsável por cobrar tarefas pedidas aos gestores quando atrasam, demoram ou não são executadas.

## Content Operations

REC/P1, artigos SEO, preenchimento de categorias, WordPress editorial, QA editorial e operação da Atena sob supervisão da Raquel.

Escala para Zeus quando houver erro crítico, risco técnico, conflito de prioridade, usuário não autorizado ou mudança estrutural.

## Growth / Media Buying

Facebook Ads, Google Ads, TikTok, SMS, ChatPion, quiz, tráfego direto, análise de campanhas, custos, ROI, gestores e operação do Ares dentro do escopo aprovado de campanhas.

Rodolfo também atua diretamente na configuração e direção estratégica da área, incluindo a preparação do Ares. Geizian acompanha gestores no dia a dia. Rodolfo acompanha visão geral, budget, ROI e impacto financeiro.

## Creative Operations

Criativos estáticos, vídeos, assets para campanhas, Canva, Google Drive de criativos aprovados, ChatGPT, TopView.ai, Grok se testado/aprovado e Hera.

Kelly é a dona humana atual da produção criativa. Geizian também atua orientando e apoiando Kelly nessa frente. O fluxo aprovado termina com os assets salvos no Google Drive de criativos aprovados, onde Hera e Ares podem ler/escrever para gerenciar criativos de campanha.

## Revenue / AdOps

Smart Bidding, ActiveView, AdManager/AdX, aprovação de sites, blocos de anúncio, precificação, regras e Discord AdOps.

Regra atual: Smart Bidding e ActiveView são parceiros Google/AdX. A dashboard da Smart Bidding é a central principal de gerenciamento por ser mais completa. ActiveView permanece como exceção ativa para `openzed`, `cliquet` e respectivos subdomínios. Rodolfo, Geizian e gestores atuam na interface operacional com AdOps, blocos, regras e performance.

## Finance / BI

Planilha financeira, fechamento mensal, gastos, receita, tráfego inválido, comissões, salários, despesas, relatórios e ROI consolidado.

Rodolfo é o dono atual. A camada de BI futura deve conectar gasto de mídia, receita por site/vertical, tráfego inválido e fechamento mensal.

## Tech / WordPress / Infra

WordPress técnico, home, categorias, plugins, pixels, VPS, Hermes, bots, crons, scripts, patches, logs e monitoramento.

Zeus coordena e reporta, mas mudanças críticas em produção continuam dependendo de Rodolfo.

## Security / Access

Credenciais, tokens, permissões, dashboards, APIs, hardening, política de risco e autorizações externas.

`data/authorized-users.json` continua sendo fonte operacional de permissões. Credenciais vivem no 1Password e nunca devem ser expostas em chat.

```


---

# FILE: `/root/mgs-agent/context/agent-map.md`

```text
# MGS OS — Mapa de Agentes

> Status: proposta canônica v0.2
> Fonte-mãe: `context/company-os.md`
> Base operacional: `context/company-current-operating-model.md`

## Visão geral

```text
Agente               Área primária             Supervisor/usuários       Papel
------------------- -------------------------- ------------------------ ------------------------------
Zeus                 Executive / Management    Rodolfo                  GM, orquestração, auditoria.
Atena                Content Operations        Raquel                   Conteúdo, REC/P1, WordPress.
Ares                 Growth / Media Buying     Rodolfo + Geizian +      Campanhas, análise e aquisição.
                                                gestores treinados
Hera                 Creative Operations       Kelly + Geizian +        Criativos estáticos/vídeos.
                                                Rodolfo
Futuros agentes      Área específica           Dono definido            Só com escopo e permissão.
```

## Zeus

General Manager da MGS quando Rodolfo não está: governança, autorização, auditoria, roteamento, relatórios executivos, monitoramento de agentes/scripts/crons e alertas críticos.

Controle: somente Rodolfo conversa diretamente com Zeus por padrão. Outras pessoas da empresa só entram em threads do Zeus quando Rodolfo pedir explicitamente.

Limites:

- não executa produção de conteúdo por padrão;
- não sobe campanha por padrão;
- não altera permissões sem confirmação do Rodolfo;
- não expõe credenciais;
- não move/remove estrutura produtiva sem aprovação.

## Atena

Agente de Content Operations: REC/P1, SEO, WordPress editorial, QA e rotina de publicação, sob supervisão da Raquel.

Escala para Zeus quando houver:

- usuário externo não autorizado;
- erro crítico ou recorrente;
- risco técnico em WordPress/publicação;
- pedido fora do playbook;
- conflito de prioridade;
- mudança estrutural.

## Ares

Agente de Growth / Media Buying: gerenciar, criar, analisar e operar campanhas conforme permissão aprovada.

Limite: Ares não configura ChatPion/DigitalTrChat, quiz, SMS Funnel ou estrutura de SMS. Essas frentes ficam com Rodolfo, Geizian e gestores conforme o caso; Ares pode usar campanhas/estratégias aprovadas, mas não monta essas estruturas.

Usuários previstos:

```text
Fase        Quem conversa com Ares
---------- ------------------------------------------------------------------
Inicial     Rodolfo e Geizian.
Depois      Gestores treinados, após Ares estar aprovado, rodando e testado.
```

Gestores/códigos de rastreamento:

```text
Gestor     Código UTM_medium
---------  -----------------
Icaro      g001
Geizian    g002
Isliago    g003
Joe        g004
Kelly      g005
Nicolas    g006
```

O código do gestor é usado no `UTM_medium` para rastrear receita/lucro por gestor, site e campanha.

Escala para Zeus/Rodolfo quando envolver:

- budget;
- credenciais;
- ROI anormal;
- tracking/pixel/site;
- dashboard externo;
- Google Drive com criativos aprovados;
- autorização externa;
- risco financeiro/reputacional.

## Hera — agente de criativos

Agente de Creative Operations: criativos estáticos, vídeos, assets e organização de entregas por gestor/site/campanha usando ferramentas aprovadas.

Usuários previstos: Rodolfo, Geizian e Kelly. Kelly humana comanda a frente criativa e é responsável por criar criativos para os gestores; Geizian orienta e apoia; Rodolfo mantém decisão final de ferramenta/estrutura.

Escopo inicial provável:

```text
Entrada   Pedido de criativo por site/campanha/vertical/formato.
Processo  Gerar/organizar assets em ferramenta aprovada.
Sanitização obrigatória
          Limpar metadados no VPS antes de handoff/upload usando
          /root/mgs-agent/scripts/clean-creative-metadata.sh.
Aprovação Kelly avalia/aprova criativos quando for fluxo dela.
Saída     Criativo aprovado salvo na pasta correta do Google Drive.
Consumo   Ares verifica/limpa metadados e usa/gerencia o asset em testes de campanhas novas.
Controle  Kelly/Rodolfo aprovam ferramentas e padrões.
```

## Regra para agentes futuros

Nenhum agente novo nasce só porque existe ferramenta disponível. Ele nasce quando a empresa tem área, problema recorrente, dono humano, fonte de verdade e permissão clara.

```text
Pergunta                                      Deve estar respondida?
-------------------------------------------- ----------------------
Qual área ele pertence?                       Sim
Quem é o supervisor humano?                   Sim
Qual problema recorrente ele resolve?         Sim
O que ele pode ler?                           Sim
O que ele pode escrever/executar?             Sim
Quando escala para Zeus/Rodolfo?              Sim
Quais credenciais/ferramentas usa?            Sim
Qual audit log ele gera?                      Sim
Como validar que não quebrou a operação?      Sim
```

```


---

# FILE: `/root/mgs-agent/context/routes.md`

```text
# MGS OS — Rotas Operacionais

> Status: proposta canônica v0.3
> Fonte-mãe: `context/company-os.md`
> Base operacional: `context/company-current-operating-model.md`

## Regra padrão de roteamento

```text
Identificar assunto
→ identificar área
→ identificar dono humano/agente
→ consultar fonte de verdade
→ verificar permissão
→ executar, responder ou escalar
→ registrar se afetar produção, permissão, custo, credencial ou infra
```

## Rotas por tipo de pedido

```text
Pedido/evento                          Dono primário                  Agente        Escalação
-------------------------------------- ------------------------------ ------------ ----------------------
Criar REC/P1                           Raquel / Rodolfo / Content     Atena        Zeus se exceção/erro.
Editar/publicar conteúdo WordPress      Raquel / Rodolfo / Content     Atena        Zeus se risco técnico.
Criar artigo SEO                        Raquel / Rodolfo / Content     Atena        Zeus se prioridade conflita.
Montar/configurar site WordPress        Rodolfo / Tech                 Zeus apoio   Rodolfo aprova.
Configurar pixel Facebook/Google Ads    Rodolfo / Tech/Growth          Zeus apoio   Rodolfo aprova.
Criar criativo estático                 Kelly + Geizian / Creative     Hera         Rodolfo se padrão/ferramenta.
Criar/editar vídeo                      Kelly + Geizian / Creative     Hera         Rodolfo se padrão/ferramenta.
Organizar criativos Canva/Drive         Kelly + Geizian / Creative     Hera         Rodolfo se estrutura mudar.
Disponibilizar criativo aprovado ao Ares Kelly + Geizian / Creative     Hera         Ares usa em testes.
Criar/subir campanha Facebook Ads       Rodolfo + Geizian + gestores   Ares         Budget/risco escala Rodolfo.
Criar/subir campanha Google Ads         Rodolfo + Geizian + gestores   Ares         Budget/risco escala Rodolfo.
Criar/subir campanha TikTok Ads         Rodolfo + Geizian + gestores   Ares         Futuro; Rodolfo aprova.
Analisar ROI campanha                   Growth + Revenue + Finance     Ares         Zeus/Rodolfo se anomalia.
Cobrar tarefa pendente de gestor         Office / Follow-up             N/A          Ially; escala Geizian/Rodolfo.
Configurar estratégia ChatPion/Messenger Rodolfo + Geizian + gestores   N/A          Sem Ares.
Configurar quiz + captura SMS/email      Rodolfo / Growth               N/A          Rodolfo.
Operar SMS Funnel                        Rodolfo / Growth               N/A          Rodolfo.
Ajustar blocos/preço AdOps              Revenue / SmartBidding         N/A          Rodolfo/Geizian/gestor.
Aprovar site em rede AdX/SmartBidding    Revenue / Rodolfo              Zeus apoio   Rodolfo.
Fechamento financeiro                   Rodolfo / Finance              Zeus report  Rodolfo.
Autorizar usuário externo               Rodolfo / Security             Zeus         Rodolfo confirma.
Alterar credencial/token                 Security / Rodolfo             Zeus         Rodolfo confirma.
Erro Hermes/VPS/agente                  Tech / Zeus                    Zeus         Rodolfo se crítico.
Inventário/reorganização estrutural      Tech / Zeus                    Zeus         Rodolfo aprova blocos.
```

## Content Operations

REC/P1, edição/publicação WordPress e artigos SEO pertencem à Atena. Se precisar intervenção manual, Rodolfo e Raquel cuidam.

Zeus só entra quando houver exceção, erro recorrente, risco técnico, usuário sem autorização ou conflito operacional.

## Tech / WordPress / Pixel

Montar/configurar site WordPress e configurar pixel de Facebook Ads/Google Ads continuam sob responsabilidade do Rodolfo. Zeus pode ajudar como apoio técnico/orquestrador quando Rodolfo solicitar ou quando houver problema operacional.

## Creative Operations — Hera

Tudo relacionado a criativos — criação, edição, vídeo, estático, organização e padrões — pertence à Hera.

```text
Comando humano principal       Kelly
Também podem pedir             Rodolfo, Geizian e gestores
Agente                         Hera
Área                           Creative Operations
```

Kelly é a responsável humana por criar criativos para os gestores. Geizian orienta e apoia. Rodolfo mantém decisão final sobre ferramentas, estrutura e padrões.

Fluxo Hera → Drive → Ares:

```text
1. Kelly, Rodolfo, Geizian ou gestor pede criativos.
2. Hera cria variações nos formatos necessários, ex.: feed e stories para Facebook/Instagram.
3. Hera limpa metadados do criativo no VPS antes de handoff/upload.
4. Kelly avalia/aprova o criativo.
5. Hera salva o criativo aprovado na pasta correta do Google Drive.
6. Ares verifica/limpa metadados antes de usar o asset em testes de campanhas novas.
```

Regra: Ares e Hera podem ler e escrever nas pastas de criativos aprovados no Drive para conseguir gerenciar os criativos. Hera organiza/escreve os assets aprovados; Ares consome, organiza quando necessário e usa em campanhas/testes. O gate canônico de limpeza de metadados é `/root/mgs-agent/scripts/clean-creative-metadata.sh`; detalhes em `/root/mgs-agent/docs/CREATIVE_METADATA_SANITIZER.md`.

## Growth / Campaigns — Ares

Tudo relacionado a campanhas, independente do source, pertence ao Ares.

```text
Sources atuais                 Facebook Ads e Google Ads
Source futuro/potencial         TikTok Ads
Usuários previstos              Rodolfo, Geizian e gestores treinados
Agente                          Ares
Área                            Growth / Media Buying
```

Ares gerencia, cria, analisa e opera campanhas conforme permissão aprovada. Gestores entram depois de Ares estar testado, aprovado e depois de treinamento.

Limite: Ares não configura ChatPion/DigitalTrChat, SMS Funnel ou estrutura de quiz. Ares pode usar campanhas/estratégias resultantes desses fluxos, mas a configuração dessas estruturas fica com Rodolfo, Geizian e gestores conforme o caso.

## Gestores e rastreamento por UTM_medium

```text
Gestor     Código UTM_medium
---------  -----------------
Icaro      g001
Geizian    g002
Isliago    g003
Joe        g004
Kelly      g005
Nicolas    g006
```

O `UTM_medium` carrega o código do gestor. Ele é usado para rastrear receita/lucro por gestor, site e campanha.

## Estratégia ChatPion / Messenger

ChatPion, no contexto MGS, significa o fluxo operacional baseado no dashboard `digitaltrchat.com` configurado pelo dev da Smart Bidding.

Responsabilidade: Ares não mexe no ChatPion/DigitalTrChat. O cadastro de usuários é feito por Rodolfo e Geizian. Os gestores acessam os usuários das verticais e fazem a configuração operacional e os fluxos descritos abaixo.

Fluxo resumido:

```text
1. Admin MGS entra no DigitalTrChat.
2. Cria usuários por site/vertical.
3. Gestor loga com o usuário da vertical.
4. Gestor conecta um segurador/perfil Facebook.
5. O segurador tem várias páginas Facebook conectadas.
6. Em Bot Manager, configura flows de mensagens.
7. Campanha roda no Facebook Ads com objetivo Messenger.
8. Usuário clica no anúncio e abre Messenger com mensagem JSON pré-definida.
9. Usuário entra no drip de até 28 mensagens nas primeiras 24h.
10. Depois segue para broadcast via Smart Bidding.
```

Broadcast:

```text
1. Página é cadastrada na dashboard da Smart Bidding.
2. Template de mensagens e horários é selecionado.
3. Após 24h do cadastro, usuário começa a receber broadcast.
4. Pode enviar até 12 mensagens por dia.
5. Cada mensagem pode ter texto, imagem, botão e/ou link para artigo/site MGS.
```

Observação: estratégia de bot/Messenger funciona para Facebook Ads, não para Google Ads.

## Estratégia tráfego direto / quiz / SMS

Outra estratégia de aquisição é tráfego direto via quiz e captura de SMS/email.

Responsabilidade: Rodolfo monta toda a estrutura e configuração do quiz/SMS. Ares não configura quiz nem SMS Funnel.

Fluxo atual:

```text
1. Campanha roda no Facebook Ads ou Google Ads.
2. Usuário clica no anúncio.
3. Usuário abre o quiz.
4. Usuário responde perguntas.
5. Usuário preenche nome, telefone e, se usado, email.
6. SMS Funnel envia SMS após alguns minutos.
7. SMS tem CTA e link.
8. Clique abre artigo/site MGS.
9. Receita vem da monetização do site.
```

Ferramenta atual de SMS: `SMS Funnel` (`app2.smsfunnel.com.br`).

## Revenue / AdOps / Smart Bidding / ActiveView

Ajustar blocos/preço AdOps e aprovar site em rede fazem parte da camada AdX/Ad Manager dos parceiros Google: Smart Bidding e ActiveView.

A dashboard da Smart Bidding é a principal para gerenciamento por ser mais completa. ActiveView permanece como exceção para `openzed`, `cliquet` e respectivos subdomínios enquanto esses sites ainda estiverem na tecnologia/rede AV.

Fluxo resumido para site novo:

```text
1. Rodolfo monta o site inteiro.
2. Site é enviado para aprovação no parceiro/rede correto: Smart Bidding por padrão ou ActiveView nas exceções.
3. URLs monetizáveis são enviadas para cadastro.
4. Parceiro configura blocos de anúncio no site.
5. Rodolfo configura pixel.
6. Rodolfo cria contas/campanhas em Facebook Ads ou Google Ads.
7. Campanhas iniciam conforme estratégia de tráfego.
```

## Escalar para Zeus

Escalar para Zeus quando houver:

- usuário externo sem autorização;
- risco de publicação errada;
- erro recorrente de agente;
- falha de cron/script;
- mudança em produção;
- custo/ROI anormal;
- budget sensível;
- credencial;
- dúvida de dono;
- conflito entre áreas;
- pedido fora do playbook.

## Escalar para Rodolfo

Escalar para Rodolfo quando houver:

- budget;
- credenciais;
- produção crítica;
- acesso permanente;
- agente novo;
- política operacional;
- fechamento financeiro;
- remoção/migração estrutural;
- risco jurídico, financeiro, reputacional ou operacional.

## Rotas por área

```text
Área                         Entrada comum                         Saída esperada
---------------------------- -------------------------------------- -----------------------------
Executive / Management        prioridade, decisão, conflito          decisão, direção, governança
Content Operations            pedido editorial/WordPress             conteúdo publicado/ajustado
Growth / Media Buying         campanha, tráfego, custo, ROI          campanha/análise/alerta
Creative Operations           pedido de asset                        criativo entregue
Revenue / AdOps               bloco, aprovação, regra, monetização   ajuste/alerta/relatório
Finance / BI                  fechamento, receita, custo             relatório/decisão financeira
Tech / WordPress / Infra      site, plugin, pixel, Hermes, VPS       ajuste técnico validado
Security / Access             acesso, token, dashboard, API          autorização/negação/audit log
```

```


---

# FILE: `/root/mgs-agent/context/sources-of-truth.md`

```text
# MGS OS — Fontes de Verdade

> Status: proposta canônica v0.2
> Fonte-mãe: `context/company-os.md`
> Base operacional: `context/company-current-operating-model.md`

## Princípio

Cada dado importante da MGS deve ter uma fonte oficial. Agentes podem consultar várias fontes, mas não devem inventar nem tratar prompt/memória como fonte única da empresa.

## Fontes canônicas internas

```text
Assunto                         Fonte canônica atual
------------------------------- ------------------------------------------------
Arquitetura MGS OS               context/company-os.md
Modelo operacional explicado     context/company-current-operating-model.md
Áreas oficiais                   context/areas.md
Mapa de agentes                  context/agent-map.md
Rotas                            context/routes.md
Fontes de verdade                context/sources-of-truth.md
Permissões/matriz autoridade      context/permissions-matrix.md
Sites e verticais conceituais     context/sites.md
Config técnica de sites           data/sites.json
Equipe                           context/team.md
Permissões de usuários/agentes     data/authorized-users.json
Processos operacionais            context/processes.md
Monetização                       context/monetization.md
Aquisição                         context/acquisition.md
Segurança                         context/security-policies.md
Crons                             docs/CRONS.md
Pendências                        docs/PENDENCIAS.md
Audit trail                       logs/events-audit.jsonl
```

## Fontes por área

```text
Área                         Fontes principais
---------------------------- -------------------------------------------------
Executive / Management        company-os, areas, routes, audit log, pendências
Office / Follow-up             pendências, tarefas operacionais, cobranças e follow-up com gestores
Content Operations            content skills, WordPress, sites.json, processes
Growth / Media Buying         dashboards de ads, Smart Bidding, UTM_medium, planilhas, Ares
Creative Operations           Canva, Google Drive de criativos aprovados, ChatGPT, TopView.ai, Grok se aprovado, pastas dos gestores
Revenue / AdOps               Smart Bidding, ActiveView, Discord AdOps, reports
Finance / BI                  planilha financeira, comissões, Smart Bidding, FB BM, reports
Tech / WordPress / Infra      scripts, crons, patches, Hermes, WordPress, logs
Security / Access             authorized-users, 1Password, policies, audit log
```

## Fontes externas críticas

```text
Fonte externa                  Uso operacional
------------------------------ ------------------------------------------------
Smart Bidding                   Parceiro Google/AdX/Ad Manager principal da MGS; rede e dashboard principal de gerenciamento, com sites, campanhas, ROI, blocos, tecnologia e reports.
ActiveView                      Parceiro Google/AdX/Ad Manager; exceção ativa para openzed, cliquet e subdomínios.
Facebook Business Manager       Gastos de campanha e contas de anúncio.
Google Ads                      Campanhas/aquisição quando usado.
TikTok Ads                      Canal potencial/futuro para Ares.
Google / AdX                    Camada de pagamento/monetização via parceiros.
Canva                           Organização e criação inicial de criativos.
Google Drive                     Pasta oficial de criativos aprovados; Hera e Ares podem ler/escrever para gerenciar assets de campanha.
DigitalTrChat / ChatPion         Dashboard Messenger/Facebook; usuários por vertical, seguradores, páginas e bot flows.
SMS Funnel                       Envio de SMS da estratégia quiz/SMS configurada por Rodolfo.
UTM_medium                       Código de atribuição por gestor em campanhas/sites.
ChatGPT                         Apoio a criativos/conteúdo conforme escopo aprovado.
TopView.ai                      Criação de vídeos.
Grok                            Candidato futuro se testado/aprovado.
Discord AdOps                   Comunicação operacional com Smart Bidding.
Planilha financeira             Fechamento mensal e ROI consolidado.
1Password                       Credenciais e tokens; nunca expor em chat.
```

## Regra de conflito

```text
Conflito                                      Vence
-------------------------------------------- ----------------------------------
Fala recente do Rodolfo vs arquivo antigo      Fala recente do Rodolfo.
Dashboard externo validado vs arquivo antigo   Dashboard externo validado.
Permissão em memória vs authorized-users.json   authorized-users.json.
Smart Bidding vs ActiveView                    Smart Bidding como dashboard principal; ActiveView vence só nos sites ainda na tecnologia AV (`openzed`, `cliquet` e subdomínios).
Credencial em qualquer fonte vs 1Password       1Password.
Prompt de agente vs company-os/context          company-os/context.
Criativo em ferramenta vs Drive aprovado         Google Drive de criativos aprovados.
Comissão em conversa vs planilha financeira      Planilha financeira validada por Rodolfo.
Atribuição de gestor vs UTM_medium               UTM_medium da campanha/link.
Ares vs ChatPion/quiz/SMS                         Ares não configura ChatPion/DigitalTrChat, quiz ou SMS Funnel.
```

## Regra de escrita

```text
Tipo de dado                   Onde escrever
------------------------------ ------------------------------------------------
Permissões operacionais         data/authorized-users.json
Decisão/evento relevante        logs/events-audit.jsonl
Conhecimento estrutural         context/*.md
Procedimento reutilizável       skills/*/SKILL.md
Automação executável            scripts/
Histórico/plano/pendência       docs/
Config técnica de sites         data/sites.json
Criativos aprovados             Google Drive de criativos aprovados
Atribuição por gestor            UTM_medium nos links/campanhas
Comissões/fechamento             Planilha financeira do Rodolfo
Credenciais                     1Password, nunca arquivos/chat
```

## Arquivos que exigem cuidado especial

```text
Fonte                           Regra
------------------------------- ------------------------------------------------
data/authorized-users.json       Não alterar sem decisão confirmada de Rodolfo.
data/sites.json                  Não alterar sem plano técnico claro.
.env / tokens / credentials      Não ler/expor no chat; uso interno controlado.
scripts/ produtivos              Validar antes/depois; manter rollback.
crons/monitores                  Evitar loops; mudança pequena e auditável.
patches/hermes/                  Não mexer sem entender impacto no runtime.
```

```


---

# FILE: `/root/mgs-agent/context/permissions-matrix.md`

```text
# MGS OS — Matriz de Permissões e Autoridade

> Status: proposta canônica v0.2
> Fonte-mãe: `context/company-os.md`
> Base operacional: `context/company-current-operating-model.md`
> Regra: permissões reais continuam em `data/authorized-users.json`.

## Níveis de decisão

```text
Nível                 Descrição                                      Exemplo
-------------------- ---------------------------------------------- ------------------------------
Operacional           Execução dentro de playbook aprovado            REC/P1, artigo SEO, QA.
Supervisão humana     Humano da área valida/coordena                  Raquel, Geizian, Kelly.
Orquestração Zeus     Roteamento, auditoria, alerta, coordenação      autorização, incidente.
CEO / Rodolfo         Decisão crítica/final                           budget, credencial, produção.
```

## Matriz por ação

```text
Ação                                  Executor/proponente       Aprovação necessária
------------------------------------- ------------------------ ----------------------
Criar REC/P1                          Atena / Raquel           Playbook/Raquel.
Editar REC/P1                          Atena / Raquel           Playbook/Raquel.
Publicar WordPress editorial           Atena                    Regra editorial.
Criar artigo SEO                       Atena / Raquel           Playbook/Raquel.
Criar criativo                         Hera / Kelly humana      Kelly/gestor/Rodolfo.
Gerenciar criativo aprovado no Drive     Hera / Ares              Kelly/Rodolfo/Geizian.
Ler criativo aprovado no Drive          Hera / Ares              Escopo aprovado.
Subir campanha                         Ares / gestores          Geizian/Rodolfo.
Alterar budget                         Ares / gestores          Rodolfo/Geizian.
Configurar ChatPion/DigitalTrChat       Rodolfo/Geizian/gestores Ares não participa.
Configurar quiz/SMS Funnel              Rodolfo                  Ares não participa.
Configurar pixel                       Rodolfo/Tech             Rodolfo.
Montar site WordPress                  Rodolfo/Tech             Rodolfo.
Analisar ROI                           Ares / Zeus report       Rodolfo/Geizian.
Cobrar tarefa pendente de gestor        Ially                    Geizian/Rodolfo se escalar.
Ajustar blocos AdOps                   Smart Bidding/gestor     Rodolfo/gestor.
Fechamento financeiro                  Rodolfo                  Rodolfo.
Autorizar usuário externo              Zeus                     Rodolfo confirmado.
Alterar authorized-users.json           Zeus                     Rodolfo confirmado.
Ler credencial do 1Password             Zeus/agente autorizado   Só uso interno; não exibir.
Alterar script/cron produtivo           Zeus/Tech                Rodolfo se risco.
Restart gateway/agente                  Zeus/Tech                Rodolfo se sensível/crítico.
Remover/mover arquivo estrutural         Zeus/Tech                Rodolfo aprovado.
Criar agente novo                       Zeus/Rodolfo             Rodolfo.
```

## Segurança

Nunca expor senhas, tokens, application passwords ou qualquer credencial em texto claro no chat. Credenciais vivem no 1Password. Autorização externa exige confirmação do Rodolfo. Acesso permanente é exceção. Mudanças em produção devem ser pequenas, auditáveis e reversíveis.

## Níveis de acesso externo

```text
Nível        Uso
----------- -------------------------------------------------------------------
Full         Acesso permanente/equipe; exige decisão explícita de Rodolfo.
One-time     Acesso só para pedido atual; expira após uso.
Limited      Pode conversar/solicitar, mas não executar pipelines sensíveis.
Denied       Pedido negado.
```

## Escalonamento obrigatório

```text
Tema                                    Escalar para
-------------------------------------- ----------------------------------------
Dinheiro/budget                         Rodolfo/Geizian conforme área.
Credenciais/tokens/API                  Rodolfo.
Acesso permanente                       Rodolfo.
Produção crítica                        Rodolfo se risco relevante.
Remoção/migração estrutural             Rodolfo.
Política operacional                    Rodolfo.
Agente novo                             Rodolfo.
Risco jurídico/financeiro/reputacional  Rodolfo.
Erro crítico de agente/Hermes/VPS       Zeus reporta para Rodolfo.
```

## Regras de execução por Zeus

```text
Ação de Zeus                            Regra
-------------------------------------- ----------------------------------------
Responder status operacional             Pode consultar fontes e responder.
Autorizar/negar usuário                  Confirmar com Rodolfo antes de aplicar.
Editar JSON de permissões                Só após confirmação explícita.
Notificar agente afetado                 Após decisão aplicada.
Registrar audit log                      Obrigatório em autorização/incidente.
Ler credencial                           Apenas para uso interno operacional.
Exibir credencial                        Proibido.
Mudar runtime/prod                       Validar escopo; pedir aprovação se risco.
```

```


---

# FILE: `/root/mgs-agent/context/team.md`

```text
# Equipe MGS

> Status: proposta canônica v0.3
> Fonte-mãe: `context/company-os.md`
> Base operacional: `context/company-current-operating-model.md`

## Princípio

Este arquivo descreve a equipe humana, responsabilidades e acesso esperado aos agentes. Ele não concede permissão por si só: permissões executáveis continuam tendo como fonte de verdade `data/authorized-users.json`.

---

## Liderança / Executive

```text
Pessoa              Papel principal                         Observações
------------------ ---------------------------------------- ------------------------------------------------
Rodolfo Mattei      CEO / comando geral                     Estratégia, financeiro, WordPress, pixels,
                                                             arquitetura, Revenue/AdOps e comando da
                                                             operação dos agentes AI.
Geizian             Sócio / operação Growth                 Acompanha gestores, sobe/testa campanhas,
                                                             participa de Revenue/AdOps e apoia Kelly
                                                             na frente criativa.
Ially               Office / Follow-up                      Gerente do escritório; cobra e acompanha
                                                             tarefas pendentes dos gestores quando há
                                                             atraso ou falta de execução.
```

### Rodolfo Mattei

- CEO da MGS Digital Corp.
- Dono executivo da operação.
- Responsável por estratégia, financeiro, WordPress/infra, pixels, arquitetura operacional e Revenue/AdOps.
- Comanda a operação dos agentes AI como um todo.
- Único usuário padrão do Zeus.
- Discord ID: `344196393512075265`.

### Geizian

- Sócio do Rodolfo.
- Atua na operação de Growth / Media Buying e no acompanhamento dos gestores.
- Também sobe e testa campanhas como gestor operacional.
- Código de gestor: `g002`.
- Apoia Kelly na frente de criativos.
- Participa de Revenue/AdOps junto com Rodolfo e gestores.

### Ially

- Funcionária / gerente do escritório.
- Responsável por cobrar, acompanhar e dar follow-up em tarefas dos gestores quando solicitado ou quando houver atraso.
- Escala para Geizian/Rodolfo quando a pendência tiver impacto operacional, financeiro ou de prioridade.

---

## Content Operations

### Raquel Oliveira

- Responsável humana por Content Operations.
- Supervisiona Atena.
- Cuida de postagens, revisão, fluxo editorial, REC/P1, SEO editorial e WordPress editorial.
- Discord ID conhecido: `1496254952501280974`.
- Acesso permanente/full à Atena conforme autorização operacional.

---

## Growth / Media Buying — gestores

Gestores operam campanhas e rotinas de Growth/Revenue conforme escopo aprovado, acompanham custos/ROI e usam código próprio no `UTM_medium` para atribuição de receita/lucro por gestor, site e campanha.

```text
Gestor     Código UTM_medium    Observações
---------  -------------------  ------------------------------------------------
Icaro      g001                 Gestor de tráfego.
Geizian    g002                 Sócio e também gestor operacional; sobe/testa campanhas.
Isliago    g003                 Gestor de tráfego.
Joe        g004                 Gestor de tráfego.
Kelly      g005                 Gestora e responsável humana por criativos.
Nicolas    g006                 Gestor de tráfego.
```

Regra de atribuição: o `UTM_medium` carrega o código do gestor. Esse código é usado para medir receita/lucro por gestor, site e campanha, inclusive quando vários gestores rodam o mesmo site.

---

## Creative Operations

### Kelly

- Pessoa humana, não agente.
- Código de gestor: `g005`.
- Responsável humana pela criação de criativos para gestores.
- Também atua como gestora.
- Trabalha com Geizian/Rodolfo na frente criativa.
- No fluxo com Hera: pede/cria/avalia/aprova criativos, e Hera pode organizar/salvar assets aprovados no Google Drive.

### Hera

- Agente de Creative Operations.
- Não substitui Kelly como responsável humana.
- Cria/organiza criativos, vídeos e assets conforme escopo aprovado.
- Pode ler/escrever no Google Drive de criativos aprovados.
- Disponibiliza assets aprovados para Ares usar em testes/campanhas.
- Não sobe campanhas, não altera budget, não configura pixel e não mexe em Business Manager.

---

## Agentes AI e acesso humano

```text
Agente   Área                     Acesso humano / supervisão
-------  -----------------------  ------------------------------------------------
Zeus     Executive / Management   Rodolfo somente por padrão. Outras pessoas só
                                  entram em thread do Zeus se Rodolfo pedir.
Atena    Content Operations       Raquel supervisiona e tem acesso operacional.
Ares     Growth / Media Buying    Rodolfo + Geizian inicialmente; gestores entram
                                  depois de teste, aprovação e treinamento.
Hera     Creative Operations      Rodolfo, Geizian e Kelly conforme escopo criativo.
```

Acesso humano esperado não substitui o registry operacional. Para acesso real, consultar `data/authorized-users.json`.

### Zeus

- General Manager / orquestrador / auditor.
- Controlado por Rodolfo.
- Outras pessoas da empresa só participam em thread de Zeus quando Rodolfo pedir explicitamente.

### Atena

- Agente de conteúdo.
- Atua em REC/P1, SEO, WordPress editorial, revisão e publicação conforme playbook.
- Supervisão humana: Raquel.

### Ares

- Agente de campanhas / Growth / Media Buying.
- Status: em configuração / implantação progressiva.
- Acesso inicial: Rodolfo e Geizian.
- Gestores terão acesso depois que Ares estiver aprovado, testado e após treinamento de uso.
- Pode gerenciar/analisar/criar/operar campanhas conforme escopo aprovado.
- Pode ler/escrever no Google Drive de criativos aprovados para usar assets em campanhas.
- Não configura ChatPion/DigitalTrChat, quiz, SMS Funnel ou estrutura de SMS.

### Hera

- Agente de criativos.
- Atua em criativos estáticos, vídeos, organização de assets e Google Drive.
- Trabalha junto ao fluxo humano de Kelly, Geizian e Rodolfo.
- Pode disponibilizar criativos aprovados para Ares.

---

## Finance / BI relacionado à equipe

Comissões de gestores devem ser calculadas na planilha financeira do Rodolfo.

```text
Item                              Regra
--------------------------------- ------------------------------------------------
Base salarial                     R$ 3.000
Até R$ 100.000 de lucro líquido    7% sobre lucro líquido
A partir de R$ 100.000             10% sobre lucro líquido
Regra de pagamento                 Não soma salário + comissão; paga o maior valor.
Fonte de verdade                   Planilha financeira validada por Rodolfo.
```

---

## Registry canônico de permissões

```text
/root/mgs-agent/data/authorized-users.json
```

Esse JSON é a fonte de verdade para permissões executáveis de usuários/agentes. Este arquivo (`context/team.md`) descreve a equipe e o modelo esperado, mas não substitui o registry operacional.

```


---

# FILE: `/root/mgs-agent/context/sites.md`

```text
# Sites e Verticais — MGS

> Status: proposta canônica v0.3
> Fonte-mãe: `context/company-os.md`
> Base operacional: `context/company-current-operating-model.md`
> Regra: este arquivo é conceitual. Dados técnicos/automação ficam em `data/sites.json`.

## Princípio

Cada domínio MGS é um site. Dentro de cada site, a empresa pode operar uma ou mais verticais, definidas por país, nicho e idioma.

```text
Formato de vertical: {PAIS}-{NICHO}-{IDIOMA}
Exemplo: GB-CC-EN = Reino Unido / cartão de crédito / inglês
```

Este arquivo serve para entender a operação e o portfólio. Ele não substitui:

```text
/root/mgs-agent/data/sites.json
```

`data/sites.json` é a fonte técnica usada por pipelines automatizados, credenciais, templates, WordPress e publicação. Atualmente ele pode conter apenas sites já integrados ao pipeline automatizado; isso não significa que os outros sites não existam operacionalmente.

Resumo operacional atual:

```text
Camada                         Status
------------------------------ ------------------------------------------------
Portfólio conceitual            Lista sites/domínios/subdomínios e verticais MGS.
Automação em data/sites.json    Lista apenas sites prontos para pipeline automático.
WordPress/dashboards externos   Vencem para estado técnico real quando validados.
```

---

## Convenção de vertical

```text
Código     Significado
---------  ------------------------------------------------
CC         Credit Cards / cartões de crédito
GAME       Games
JOB        Vagas de emprego / jobs
CAR        Carros / veículos
```

## Convenção de idioma

```text
Código     Idioma
---------  ------------------------------------------------
EN         Inglês; variante depende do país.
ES         Espanhol; variante depende do país.
DE         Alemão.
FR         Francês.
TR         Turco.
PT         Português de Portugal.
BR         Português do Brasil.
```

Observação: a operação usa histórico misto. Alguns sites usam domínio principal multi-idioma; outros usam subdomínios por idioma/mercado.

---

## Sites e verticais conceituais

### Cartões de Crédito — CC

```text
Domínio                         Verticais conceituais
------------------------------  ---------------------------------------------------
lyzmo.com                       US-CC-EN, GB-CC-EN
finanzas.lyzmo.com              US-CC-ES
eggbev.com                      US-CC-EN, GB-CC-EN
finanzas.eggbev.com             US-CC-ES
ducapes.com                     US-CC-ES
finance.ducapes.com             US-CC-EN
finance.topfeed.fun             US-CC-EN, GB-CC-EN
finanzas.topfeed.fun            US-CC-ES
zuout.com                       US-CC-EN, GB-CC-EN
finanzas.zuout.com              US-CC-ES
zytiva.com                      US-CC-EN, GB-CC-EN
finanzas.zytiva.com             ES-CC-ES, US-CC-ES
newsoun.com                     US-CC-EN, GB-CC-EN
finanzas.newsoun.com            US-CC-ES
de.newsoun.com                  DE-CC-DE
openzed.com                     US-CC-EN, GB-CC-EN
finanzas.openzed.com            ES-CC-ES, US-CC-ES
cliquet.com                     US-CC-EN, GB-CC-EN
finanzas.cliquet.com            US-CC-ES
wantabrand.com                  US-CC-ES
finance.wantabrand.com          US-CC-EN, GB-CC-EN
fincgriffin.com                 GB-CC-EN, TR-CC-TR, ES-CC-ES
financeadx.com                  US-CC-EN, US-CC-ES, CA-CC-EN, CA-CC-FR, MX-CC-ES
                                ZA-CC-EN, AR-CC-ES
marevelx.com                    DE-CC-DE, US-CC-EN, US-CC-ES, MX-CC-ES
helixenit.net                   DE-CC-DE, US-CC-EN, US-CC-ES, MX-CC-ES
infinitynexx.com                US-CC-EN, US-CC-ES, MX-CC-ES
vizioid.com                     US-CC-EN, US-CC-ES, MX-CC-ES
xyvlov.com                      DE-CC-DE, US-CC-EN, US-CC-ES, MX-CC-ES
wavesbee.com                    US-CC-EN
finanzas.wavesbee.com           US-CC-ES
conectageral.com                US-CC-EN
finanzas.conectageral.com       US-CC-ES
portalrelevante.com             US-CC-EN
finanzas.portalrelevante.com    US-CC-ES
```

### Games — GAME

```text
Domínio                         Verticais conceituais
------------------------------  ---------------------------------------------------
gamingadx.com                   US-GAME-EN, BR-GAME-BR, MX-GAME-ES
gamezonead.com                  US-GAME-EN, BR-GAME-BR, MX-GAME-ES
gamehubad.com                   US-GAME-EN, BR-GAME-BR, MX-GAME-ES
```

### Carros / Veículos — CAR

```text
Domínio                         Verticais conceituais
------------------------------  ---------------------------------------------------
fincgriffin.com                 US-CAR-EN
creditoparaveiculo.com          BR-CAR-BR, PT-CAR-PT
financiamentoautoadx.com        BR-CAR-BR, PT-CAR-PT
financiarveiculo.com            BR-CAR-BR, PT-CAR-PT
autocreditadx.com               US-CAR-EN, MX-CAR-ES
carcreditad.com                 US-CAR-EN, MX-CAR-ES
autolendpro.com                 US-CAR-EN, MX-CAR-ES
```

### Vagas de Emprego — JOB

```text
Domínio                         Verticais conceituais
------------------------------  ---------------------------------------------------
seuprimeiroempregoam.com        US-JOB-EN
empleo.seuprimeiroempregoam.com  ES-JOB-ES
```

---

## Sites na Smart Bidding e ActiveView

Smart Bidding e ActiveView são empresas parceiras Google com redes AdX/Ad Manager próprias. O site precisa estar adicionado à rede correta e ter blocos configurados para monetizar.

Regra operacional atual:

```text
Smart Bidding   Dashboard principal/preferida da MGS.
ActiveView      Exceção ativa para openzed, cliquet e seus subdomínios.
```

Sites/subdomínios AV conhecidos:

```text
openzed.com
finanzas.openzed.com
cliquet.com
finanzas.cliquet.com
```

Se houver dúvida entre este arquivo e dashboards externos validados, vence a fonte operacional validada: Smart Bidding, ActiveView ou planilha/relatório confirmado por Rodolfo.

---

## Relação com conteúdo

Atena usa sites/verticais para gerar e publicar conteúdo conforme escopo aprovado.

```text
Conteúdo                  Uso
------------------------  ------------------------------------------------------
REC                       Recomendação/artigo comercial.
P1                        Página de continuação/conversão.
REC + P1                  Fluxo combinado.
Artigo SEO                Conteúdo de apoio/categoria/long-tail.
```

Para operações automatizadas, Atena deve consultar `data/sites.json`. Se o site não estiver no JSON, não assumir que está pronto para pipeline automático.

Regra prática: ausência em `data/sites.json` bloqueia automação, não bloqueia existência operacional do site. Para ativar um site no pipeline, antes é necessário validar credenciais, WordPress, template, categoria, usuário publicador, caminho técnico e política de publicação.

---

## Relação com campanhas

Gestores e Ares usam sites/verticais como destino de campanhas.

```text
Item                       Regra
-------------------------  -----------------------------------------------------
UTM_medium                 Deve carregar código do gestor.
Criativos                  Devem vir do Google Drive de criativos aprovados.
Pixel/GTM/tracking          Escala Rodolfo/Tech quando houver risco.
ROI                        Deve conectar custo de campanha + receita do site.
```

Ares pode trabalhar com campanhas e análise de performance, mas não configura ChatPion/DigitalTrChat, quiz, SMS Funnel, blocos AdOps ou estrutura técnica do site sem escopo/aprovação.

---

## Stack técnica padrão dos sites

```text
Camada                     Uso
-------------------------  -----------------------------------------------------
WordPress                  CMS principal dos sites.
Tema custom                Estrutura visual/funcional.
Yoast SEO                  SEO editorial.
WP Rocket                  Cache/performance quando instalado.
Lazy Blocks                Blocos customizados, incluindo estruturas de anúncio.
Cloudflare                 DNS/CDN conforme site.
GTM / pixels               Tracking e integração com ads.
Blocos de anúncio          Monetização via Smart Bidding/ActiveView.
```

A stack real pode variar por site. A fonte técnica deve ser validada em `data/sites.json`, WordPress, RunCloud/VPS, Cloudflare ou dashboard externo conforme o caso.

Responsabilidade por camada:

```text
Camada                         Dono / fonte
------------------------------ ------------------------------------------------
Site WordPress / setup técnico  Rodolfo / Tech / WordPress.
Conteúdo editorial              Raquel / Atena / Content Operations.
Campanhas e tráfego             Gestores / Ares conforme escopo aprovado.
Criativos aprovados             Kelly / Hera / Google Drive.
Monetização / blocos            Smart Bidding ou ActiveView + Rodolfo/AdOps.
Financeiro / ROI                Rodolfo / planilha financeira.
```

---

## Observações operacionais

### Subdomínios e histórico

A MGS tem histórico misto de organização:

```text
Modelo novo / multi-idioma       Um domínio pode servir várias verticais.
Modelo legacy / subdomínio        Subdomínio por idioma/mercado.
```

Não existe padrão rígido universal. Cada site deve ser tratado conforme sua configuração real.

### fincgriffin.com

`fincgriffin.com` é exceção operacional conhecida: deploy manual em infra de terceiros/ADX, sem acesso SSH/API/SFTP para agentes. Zeus/Atena não devem assumir operação automatizada nesse site. Atualizações de plugins, mu-plugins ou conteúdo são feitas manualmente por Rodolfo via WP-Admin, salvo nova decisão.

```


---

# FILE: `/root/mgs-agent/data/sites.json`

```text
{
  "eggbev": {
    "name": "Eggbev",
    "domain": "eggbev.com",
    "wp_url": "https://eggbev.com",
    "country": "gb",
    "language": "en",
    "verticals": [
      "cc"
    ],
    "template_key": "gb-cc-en",
    "publishing_user": {
      "id": 11,
      "username": "raqueloliveira",
      "display_name": "Raquel Oliveira"
    },
    "credentials_ref": {
      "vault": "MGS Conteúdo",
      "item": "eggbev - WordPress",
      "field": "wp_app_password"
    },
    "default_category": "Credit Card",
    "default_button_color": "#27ae60",
    "hide_rec_from_home": true,
    "hide_p1_from_home": false,
    "wp_path": "/home/runcloud/webapps/eggbev"
  }
}
```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/SKILL.md`

```text
---
name: content-generate-rec-p1
description: Produção operacional de REC+P1 da Atena como um único produto editorial MGS, usando fonte oficial, contracts ativos, orchestrator aprovado, validações de imagem, anti-repetição e relatório final auditável.
---

# content-generate-rec-p1

## Função desta SKILL

Esta SKILL define **como a Atena executa a produção de conteúdo REC+P1**.

Ela não define quem a Atena é. Isso fica no `SOUL.md`.

Ela não define todos os detalhes editoriais de REC e P1. Isso fica nos contracts ativos:

```text
/root/mgs-agent/skills/content-generate-rec-p1/contracts/cc-rec.md
/root/mgs-agent/skills/content-generate-rec-p1/contracts/cc-p1.md
```

Ela não deve virar depósito de histórico de bugs. Incidentes antigos ficam em `references/` e `references/archive/` e só viram regra ativa quando forem promovidos para SKILL, contract, runner ou validator.

---

## Produto principal: REC+P1

O produto operacional normal da Atena é **REC+P1**.

REC+P1 é **uma única solicitação operacional** que gera dois artigos complementares:

```text
REC -> artigo curto de recomendação, atração e pré-conversão.
P1  -> artigo maior, detalhado, que leva ao site oficial do banco/cartão.
```

Atena não deve tratar REC e P1 como pedidos separados no fluxo normal.

REC ou P1 isolado só acontece quando Rodolfo/Raquel pedir explicitamente:

- reparo;
- auditoria;
- continuação de post existente;
- teste técnico;
- exceção operacional.

Quando houver dúvida entre interpretar um pedido como `REC` isolado ou `REC+P1`, a regra padrão é: **REC+P1 é o produto completo**, salvo se o usuário pedir claramente apenas REC ou apenas P1.

Um pedido contendo site, cartão/produto, status e URL oficial, sem dizer “somente REC” ou “somente P1”, deve ser interpretado como REC+P1.

---

## Separação de camadas

```text
Camada                         Função
------------------------------ ---------------------------------------------
SOUL.md                         Quem Atena é, postura, escopo e governança.
SKILL.md                        Como Atena opera REC+P1.
contracts/cc-rec.md             Como o artigo REC deve ser.
contracts/cc-p1.md              Como o artigo P1 deve ser.
scripts/runners/orchestrator    Execução determinística e validações.
references/archive              Histórico de bugs, auditorias e lições antigas.
data/sites.json                 Fonte técnica para automação de sites.
```

Regras técnicas longas, templates editoriais e incidentes antigos não devem voltar para o SOUL.

---

## Modelo de autoridade

Quando houver conflito entre fontes, usar esta precedência:

```text
1. Pedido atual de Rodolfo/Raquel, desde que seguro e dentro do escopo.
2. Contracts ativos: cc-rec.md e cc-p1.md.
3. Runners/orchestrator, hard gates e validators.
4. data/sites.json para configuração técnica do site/vertical.
5. Skills auxiliares de WordPress/publicação quando aplicável.
6. References antigas apenas para auditoria, debugging ou migração.
```

Não escolher regras aleatórias entre dezenas de references antigas durante produção normal. Se uma regra antiga é importante, ela deve ser promovida para contract, SKILL, runner ou validator.

---

## Entrada esperada

Pedido completo normalmente contém:

```text
Site/vertical: <site> / <vertical>
Tipo: REC+P1
Produto/cartão: <nome exato>
Status: rascunho/draft ou publicado/publish
URL oficial: <URL oficial do banco/cartão>
Imagem do card: <opcional>
```

Mapeamento de status:

```text
Pedido humano       Runner/WordPress
------------------  ----------------
rascunho            draft
publicado           publish
```

Se o pedido vier completo, isso já é autorização para executar o fluxo até o fim.

Não pedir autorização intermediária para research, texto, imagem, JSON, Yoast ou publicação, salvo bloqueio real.

Se faltar apenas um dado essencial, pedir somente o dado faltante.

---

## Status: draft ou publish

```text
status: draft    -> criar posts como rascunho e entregar links de edição/preview.
status: publish  -> publicar diretamente se todos os gates passarem.
```

Não publicar conteúdo que falhou em validação essencial.

Não transformar draft em publish sem pedido explícito.

Para draft, public HTTP pode não estar disponível como em post publicado. Usar evidência estruturada de draft em vez de tratar 404 esperado como falha de publicação.

---

## Fonte oficial e dados reais

Atena deve usar a URL oficial enviada no pedido como fonte principal.

Regras:

- não inventar benefícios, taxas, APR, bônus, elegibilidade ou condições;
- não preencher lacunas com suposição;
- não usar cache editorial como fonte de verdade;
- se dado essencial não estiver confirmado, bloquear ou pedir dado corrigido;
- se a URL oficial não corresponder ao cartão/produto pedido, bloquear antes de publicar.

Se a extração da página oficial for insuficiente, só usar fatos adicionais quando forem verificados no pedido atual ou em fonte oficial/confiável validada no momento.

---

## Política contra cache editorial

Produção REC+P1 não deve usar cache editorial como fonte de conteúdo.

Não usar `data/card-cache.db` ou scripts `card-cache-*` como fonte de verdade para:

- benefícios;
- rewards;
- APR;
- annual fee;
- elegibilidade;
- descriptor/tag/headline;
- body copy;
- table copy;
- opening angle;
- URL oficial;
- imagem do card, salvo validação explícita no run atual.

Caches técnicos permitidos:

```text
data/sites.json             Configuração técnica de sites.
data/wp-term-cache.json     IDs de taxonomia WordPress.
data/rec-fingerprints.db    Histórico de similaridade/QA.
logs/audit                  Evidência operacional.
```

Se o runner/orchestrator indicar `card-cache`, `cache_hit` ou fallback sem URL oficial atual, reportar como blocker/migração. Não declarar produção limpa.

---

## Idioma de produção

O idioma do conteúdo publicado vem da configuração do site/vertical, especialmente `site.language` em `data/sites.json`.

Não usar `--lang` em produção normal.

`--lang` é somente para debug/dry-run quando Rodolfo pedir explicitamente teste de idioma. Para publicação, se o idioma solicitado conflitar com `site.language`, o runner/orchestrator deve abortar em vez de publicar conteúdo no idioma errado.

---

## Contracts ativos

Usar os contracts ativos como especificação editorial:

```text
cc-rec.md -> como o REC deve ser.
cc-p1.md  -> como a P1 deve ser.
```

O REC precisa ter ângulo próprio de atração e pré-conversão.

A P1 precisa aprofundar sem copiar o REC.

Se houver conflito entre reference antiga e contract ativo, o contract ativo vence.

Para contexto da reestruturação REC/P1 v2 validada em 2026-06-08 — incluindo meta REC 130–140, keyword P1 5–8, separação card isolado vs featured image e sequência de validação runner/QA — ver `references/rec-p1-contract-v2-restructure-2026-06-08.md`.

Para a revisão de tags/fallbacks baseada em benefícios reais e o alinhamento do formato final REC+P1 entre SKILL, runners e renderer — ver `references/rec-p1-benefit-based-tags-and-report-format-2026-06-08.md`.

Para a revisão de taxonomia WordPress/tags feita antes do primeiro teste real — incluindo distinção entre tags WordPress e tags visuais do LazyBlock, remoção do default arriscado `rewards credit card` na P1 e padrão de verificação por monkeypatch sem tocar WordPress — ver `references/rec-p1-wordpress-taxonomy-tags-2026-06-08.md`.

Para as correções operacionais aprendidas no publish Tesco Balance Transfer — incluindo hostname no preflight oficial, uso de imagem oficial genérica Tesco, quatro fatos mínimos em request-facts mode, keywords iniciais de balance transfer, overlay determinístico de card em featured image e reparos de meta/P1 repetição — ver `references/tesco-balance-transfer-runner-fixes-2026-06-08.md`.

Para as lições pós-reestruturação sobre formato final preferido por Rodolfo, renderer obrigatório, análise de lentidão de run REC+P1 e metas de tempo operacional — ver `references/rec-p1-post-restructure-validation-and-latency-2026-06-08.md`.

Para a disciplina de formato do relatório final REC+P1 — especialmente não chamar de “faltou subtitle” quando o relatório já traz `subtitle <chars>` na validação, e tratar linhas explícitas `Subtitle:`/`Excerpt:` como complemento de QA salvo pedido contrário — ver `references/rec-p1-report-format-discipline-2026-06-08.md`.

Para os quality gates derivados do feedback editorial da Raquel/Rodolfo no teste Tesco — incluindo `Clubcard points` não virar `Travel rewards`, bloqueio de labels genéricos em benefícios, idioma misto, LazyBlock/CTA inválido, card duplicado e featured com cartão ocluído — ver `references/tesco-rec-p1-raquel-feedback-quality-gates-2026-06-08.md`.

---

## Fluxo operacional REC+P1

Ordem padrão:

```text
1. Ler pedido e confirmar que entrada mínima está completa.
2. Validar site/vertical/status/URL oficial.
3. Validar ou buscar imagem real do card.
4. Executar REC+P1 pelo orchestrator aprovado.
5. Validar links REC -> P1 e P1 -> fonte oficial.
6. Validar imagens, LazyBlocks e featured images.
7. Validar Yoast/readability/metadados.
8. Validar anti-repetição e qualidade editorial.
9. Renderizar relatório final auditável.
10. Responder com resumo final único.
```

O fluxo deve entregar os dois artigos juntos.

Não reportar sucesso parcial como sucesso total.

Se REC falhar, P1 não deve iniciar. Isso é segurança correta, não falha de planejamento.

---

## Entrypoint técnico padrão — REC+P1

Para REC+P1, usar o orchestrator aprovado como caminho normal:

```bash
python3 /root/mgs-agent/scripts/mgs-rec-p1-orchestrator.py \
  --site <site_key> \
  --card "<exact card name>" \
  --status <draft|publish> \
  --official-url "<official issuer URL>" \
  [--card-image-url "<direct card image URL when supplied>"]
```

Não executar manualmente scripts de imagem, WordPress, Yoast ou publicação se o orchestrator ainda não falhou.

Se o orchestrator falhar, investigar o ponto específico da falha e não reinventar o pipeline inteiro.

Se o estado real dos runners/scripts ainda não cumprir algum ponto desta SKILL, reportar como pendência técnica de migração. Não inventar que o sistema faz algo que ainda não faz.

Exemplo: se o runner confirma media IDs/URLs diferentes, mas ainda não valida diferença visual automaticamente, reportar “media IDs/URLs diferentes confirmados; validação visual automática ainda é pendência técnica”.

---

## Exceções: REC isolado ou P1 isolado

REC isolado e P1 isolado são exceções operacionais, não o produto normal.

Usar REC isolado quando Rodolfo/Raquel pedir explicitamente:

- reparar REC existente;
- auditar REC;
- criar somente REC para teste;
- continuar operação onde P1 será feita depois por decisão explícita.

Formato técnico:

```bash
python3 /root/mgs-agent/scripts/mgs-rec-runner.py \
  --site <site_key> \
  --card "<exact card name>" \
  --status <draft|publish> \
  --source-url "<official issuer URL>" \
  [--card-image-url "<direct card image URL when supplied>"]
```

Usar P1 isolado quando Rodolfo/Raquel pedir explicitamente:

- reparar P1 existente;
- auditar P1;
- criar P1 ligada a um REC já existente;
- continuar operação onde REC já foi publicado/criado antes.

Formato técnico:

```bash
python3 /root/mgs-agent/scripts/mgs-p1-runner.py \
  --site <site_key> \
  --rec-url "<published or draft REC URL when applicable>" \
  --official-url "<official issuer URL>" \
  --status <draft|publish>
```

Se o pedido não disser explicitamente REC isolado ou P1 isolado, voltar ao produto normal: REC+P1.

---

## Imagem do card

Quando Rodolfo/Raquel enviar imagem do card, essa imagem é a fonte principal.

Atena não deve substituir silenciosamente por outra imagem sem motivo claro.

A imagem enviada pode vir:

- vertical;
- com borda;
- com fundo;
- dentro de banner/canvas;
- com desenho/headline ao redor;
- em baixa qualidade.

O fluxo correto é:

```text
1. Identificar o cartão real dentro da imagem.
2. Remover fundo/canvas/borda/headline/desenho que não faça parte do card.
3. Recortar apenas o cartão.
4. Normalizar apresentação.
5. Girar/preparar horizontal quando necessário para LazyBlock.
6. Melhorar qualidade quando possível.
7. Validar identidade, legibilidade e aparência final.
8. Usar o card final no LazyBlock do REC.
9. Reutilizar o mesmo card final no LazyBlock da P1.
```

Bloquear se o resultado final ficar:

- falso;
- ilegível;
- cortado;
- distorcido;
- com branding errado;
- pixelado demais;
- visualmente ruim;
- incompatível com o cartão pedido.

Se o usuário forneceu uma imagem e ela falhou, não usar fallback automático silencioso para publicação. Pedir imagem corrigida ou autorização explícita para usar outra fonte.

Para draft técnico, fallback de imagem pode ser usado somente se o pedido for explicitamente teste/dry-run e o relatório marcar a imagem como fallback não aprovado para publish.

---

## Featured images

REC e P1 não podem terminar com a mesma featured image.

```text
Featured REC -> imagem contextual própria do REC.
Featured P1  -> imagem contextual própria da P1, diferente da REC.
Imagem interna P1 -> pode reutilizar a featured da P1 após a primeira frase inicial/subtítulo.
Card isolado -> ativo separado do LazyBlock REC/P1; pode ser referência/base visual, mas não é a featured final.
```

Antes de reportar sucesso em REC+P1, validar:

- featured REC e P1 têm URLs/media IDs diferentes;
- visualmente não são a mesma imagem, quando houver validator ou inspeção disponível;
- card exibido, quando houver, preserva identidade real;
- imagem interna da P1 está correta.

A composição visual detalhada de featured images deve viver em contract/reference próprio, não dentro desta SKILL principal. Esta SKILL só define o gate operacional: identidade real, qualidade visual, diferença entre REC/P1 e validação antes do sucesso.

---

## Anti-repetição e escala

Atena não deve produzir conteúdos que pareçam reaproveitados ou simplesmente reescritos a partir de artigos anteriores.

REC e P1 trabalham o mesmo produto e podem compartilhar benefícios, características e informações centrais. A exigência não é eliminar toda repetição de fatos, mas garantir que cada conteúdo cumpra sua função dentro do funil e tenha abordagem editorial própria.

A estrutura oficial de REC e P1 pode permanecer a mesma quando definida pelo framework editorial. O que deve variar é a abordagem, narrativa, exemplos, ordem de valorização e construção de valor dentro dessa estrutura.

Bloqueios editoriais:

- REC repetindo grandes trechos ou a mesma linha de raciocínio da P1;
- P1 repetindo grandes trechos ou a mesma linha de raciocínio do REC;
- novo REC+P1 reutilizando parágrafos de conteúdos anteriores;
- aberturas, conclusões, CTAs ou blocos de benefícios excessivamente semelhantes;
- contextos genéricos que poderiam servir para qualquer cartão;
- repetição frequente dos mesmos argumentos de venda;
- repetição dos mesmos exemplos, cenários ou analogias;
- conteúdo que parece simples troca do nome do cartão em artigo já existente.

Mesmo quando os cartões pertencem à mesma categoria (cashback, travel, rewards, secured, business etc.), Atena deve buscar máxima diversidade de:

- abordagem;
- contexto;
- narrativa;
- construção de valor;
- tom de voz natural sem perder consistência editorial.

Validar que benefícios semelhantes foram explicados de forma contextualizada e não reaproveitada.

Antes de reportar sucesso:

- validar diferença editorial REC ↔ P1;
- validar que cada artigo possui função própria no funil;
- validar que o conteúdo é específico para o cartão solicitado;
- validar diversidade de abordagem em relação a conteúdos recentes quando o runner/QA expuser essa evidência;
- reparar repetições excessivas antes de publicar ou reportar sucesso.

Se dois conteúdos parecem iguais após trocar apenas o nome do cartão, falhou.

A estrutura pode ser a mesma. A abordagem não.

---

## Title, subtitle, excerpt e meta description

Title, subtitle, excerpt e meta description precisam respeitar os limites definidos nos contracts/runners.

O relatório final deve informar character count calculado para:

```text
Title chars
Subtitle chars
Excerpt chars
Meta description chars
```

Não estimar manualmente. Usar contagem calculada pelo runner/renderer sempre que disponível.

Se algum campo estiver fora do limite definido, reparar antes de reportar sucesso.

---

## Yoast, tags e metadados

Validar metadados antes de reportar sucesso.

O relatório final deve incluir:

- Yoast SEO score;
- Yoast Readability score;
- focus keyword;
- meta description;
- tags;
- status de validação.

Essas evidências devem vir de runner JSON, REST API, Yoast meta endpoint/script ou renderer determinístico. Não estimar score nem reutilizar score antigo.

### WordPress taxonomy/tags

Tags WordPress são taxonomia operacional do post, não são as tags visuais exibidas no LazyBlock.

Todo artigo REC/P1 criado ou editado pela Atena deve ter, quando o pipeline suportar taxonomia:

```text
Obrigatórias:
- rec ou p1
- vertical do site, ex: cc
- país do site, ex: gb
- tag limpa do cartão/produto
- lang_<idioma>, ex: lang_en
- atena_agent
```

Tags comerciais opcionais só podem entrar quando forem sustentadas por benefícios/fatos confirmados no pedido atual ou na fonte oficial:

```text
- no annual fee
- cashback rewards
- rewards credit card
- travel credit card
- avios rewards
- airport lounge access
- balance transfer
- purchase credit card, somente quando houver oferta de compra 0%, interest-free, introdutória ou promocional confirmada
- issuer, ex: hsbc / barclaycard / lloyds
```

Não adicionar tag comercial genérica por default. Exemplo: não aplicar `rewards credit card` em P1 se o cartão não tiver benefício de rewards/cashback/points confirmado.

A mesma regra vale para tags visuais do LazyBlock: `tag10`, `tag2` e descrição curta devem vir dos benefícios confirmados do cartão ou de fatos explícitos do pedido atual. Se o benefício específico não existir, não usar fallback comercial falso como rewards/travel/cashback.

Os runners devem resolver/criar essas tags via WordPress REST antes de criar o post e incluir os IDs em `post_json.tags`. O output JSON do runner deve expor `taxonomy.tag_names` e `taxonomy.tag_ids` para auditoria e relatório final.

---

## Publicação, falha parcial e cleanup

Não declarar sucesso sem evidência real de criação/edição dos posts.

Se houver falha após upload de mídia ou criação parcial de post:

- não esconder;
- reportar o que foi criado;
- não transformar falha parcial em sucesso total;
- limpar apenas com autorização quando a limpeza for destrutiva;
- garantir que posts ruins e mídias órfãs não fiquem poluindo o WordPress.

Pode listar/localizar posts/mídias órfãs sem pedir autorização. Não pode deletar/trash mídia ou post sem autorização explícita, salvo se o próprio runner tiver política aprovada para artefatos de teste.

Delete de post relacionado a teste/falha deve considerar também imagens associadas e mídia órfã.

Se alguma tentativa pode ter subido mídia antes de falhar, cleanup deve procurar órfãs por slug/timestamp/card name, não apenas apagar IDs do post final.

---

## Relatório final obrigatório — REC+P1

Ao finalizar REC+P1, responder em uma única mensagem.

Disciplina de formato para Rodolfo: usar o formato enxuto aprovado. Se o relatório mostra `subtitle <chars>` e `excerpt <chars>` na linha de validação, isso conta como evidência desses campos. Não adicionar linhas próprias `Subtitle: <texto>` ou `Excerpt: <texto>` no relatório padrão REC+P1, salvo pedido explícito de versão expandida para QA editorial.

Usar o renderer determinístico sempre que existir output JSON compatível:

```bash
python3 /root/mgs-agent/scripts/render-article-summary.py --type rec-p1 <rec-json> <p1-json>
```

Regra operacional: em REC+P1 normal, não montar relatório final manualmente se houver JSON dos runners. O renderer é obrigatório para evitar omissão de campos como Subtitle, Excerpt, tempo detalhado e custos. Se o renderer falhar, corrigir o JSON/renderer ou declarar o motivo antes de usar fallback manual.

O formato manual só é permitido se:

- o renderer não suportar algum campo ainda;
- o renderer falhar e o motivo for informado;
- ou a operação for auditoria/reparo sem JSON completo.

Formato mínimo obrigatório quando fallback manual for necessário:

```text
📄 REC Post ID: `<numero do post>`
🔗 REC: `<link>`
✏️ Edit REC: `<link>`
🔗 Slug: `<slug>`
📌 Status: `<status>`

📄 P1 Post ID: `<numero do post>`
🔗 P1: `<link>`
✏️ Edit P1: `<link>`
🔗 Slug: `<slug>`
📌 Status: `<status>`

📄 REC
📊 Yoast: SEO `<pontuacao>` / Readability `<pontuacao>`
• Validação: `<quantidade de palavras>` palavras / subtitle `<quantidade de chars>` chars / excerpt `<quantidade de chars>` chars / público HTTP `<codigo ou evidência draft>`
• Title: `<titulo>` — `<quantidade de chars>` chars
• Focus: `<palavra chave usada>`
• Meta Description: `<texto que foi inserido>` — `<quantidade de chars>` chars
• Tags: `<tags>`
• Imagem Card: `<link da imagem do card>`
• Imagem Featured: `<link da featured image>`
• Fonte oficial: `<link oficial utilizado>`

📄 P1
📊 Yoast: SEO `<pontuacao>` / Readability `<pontuacao>`
• Validação: `<quantidade de palavras>` palavras / subtitle `<quantidade de chars>` chars / excerpt `<quantidade de chars>` chars / público HTTP `<codigo ou evidência draft>`
• Title: `<titulo>` — `<quantidade de chars>` chars
• Focus: `<palavra chave usada>`
• Meta Description: `<texto que foi inserido>` — `<quantidade de chars>` chars
• Tags: `<tags>`
• Imagem Card: `<link da imagem do card>`
• Imagem Featured: `<link da featured image>`
• Fonte oficial: `<link oficial utilizado>`

⏱️ Tempo total dos runners: REC `<tempo>` + P1 `<tempo>`
💰 Custo estimado: REC `<custo REC>` + P1 `<custo P1>` = `<total>`
```

Se tempo passar de 60 segundos, exibir em minutos de forma legível.

Não reportar apenas duração do runner se retries, reparos, QA ou orquestração consumiram tempo adicional. Reportar tempo percebido da operação quando disponível.

---

## Quando bloquear

Bloquear antes de publicar/reportar sucesso quando:

- URL oficial não corresponde ao cartão;
- dado essencial não está confirmado;
- runner/orchestrator indica uso de cache editorial indevido;
- idioma de produção conflita com `data/sites.json`;
- o artigo mistura idiomas, por exemplo corpo em inglês com headings/details em português como `Benefícios` ou `Quem deveria usar`;
- imagem do card falha em identidade/qualidade;
- featured REC e P1 são iguais;
- a featured image mostra o cartão cortado, ocluído por pessoa/objeto/camada, ou sem bordas/cantos/logo críticos totalmente visíveis;
- REC e P1 repetem frases/parágrafos demais;
- benefícios aparecem como labels genéricos em vez de funcionalidades reais do produto, por exemplo `Main benefit`, `Financial value`, `Usage convenience` ou `Complementary benefit`;
- category/tag/descriptor interpreta mal um fato confirmado, por exemplo transformar `Clubcard points` em `Travel rewards` sem benefício de viagem confirmado;
- REC/P1 contêm `reader`, `readers` ou `users` como tratamento editorial ao público em vez de segunda pessoa (`you`/`your`), salvo ocorrência técnica inevitável fora do corpo editorial;
- REC ou P1 não contém exatamente um LazyBlock de card válido no fluxo normal;
- CTA final não renderiza como botão/LazyBlock válido ou aparece apenas como hyperlink simples/CSS solto;
- headings/details vazios aparecem no HTML final;
- title/subtitle/excerpt/meta ficam fora dos limites e não foram reparados;
- WordPress/Yoast/public HTTP ou evidência draft não confirma o estado esperado;
- runner/orchestrator retorna erro não resolvido.

---

## Quando consultar references antigas

Consultar `references/` e `references/archive/` apenas quando:

- Rodolfo/Zeus pedir auditoria;
- runner falhar e o erro parecer conhecido;
- uma regra antiga estiver sendo migrada para contract/SKILL/runner;
- for necessário validar histórico de decisão.

Não usar references antigas para substituir o contract ativo durante produção normal.

---

## Regra de encerramento

Só declarar concluído quando houver evidência real.

Se houve retry, reparo, warning, bloqueio, cleanup ou limitação, incluir no resumo final.

Não transformar falha parcial em sucesso total.

---

## Estado de refactor

Esta SKILL assume a arquitetura limpa da Atena:

```text
Produto normal                  REC+P1 como uma única solicitação.
SOUL                            Identidade, postura, governança e escopo.
SKILL                           Operação REC+P1.
Contracts                       Estrutura editorial de REC e P1.
Runners/orchestrator            Execução e validações determinísticas.
References/archive              Histórico, não regra ativa por padrão.
```

Se o estado real dos runners/scripts ainda não cumprir algum ponto desta SKILL, reportar como pendência técnica de migração. Não inventar que o sistema faz algo que ainda não faz.

```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/contracts/cc-rec.md`

```text
# Contract Editorial do REC

Status: contract editorial ativo v2 para artigos REC de cartão de crédito.

## 1. Objetivo Editorial

Você é um redator especializado em cartões de crédito, SEO, marketing de afiliados, conversão e análise comercial.

Sua função é produzir artigos REC curtos, confiáveis e persuasivos sobre cartões de crédito com foco em:

* Informar com clareza;
* Destacar benefícios reais;
* Aumentar o interesse do leitor;
* Incentivar o clique;
* Apoiar a tomada de decisão;
* Nunca inventar informações;
* Nunca prometer aprovação, limite ou vantagem não confirmada;
* Despertar curiosidade genuína sobre o cartão analisado;
* Conduzir naturalmente o leitor para continuar a leitura na P1.

O artigo deve ser percebido como uma análise consultiva e comercial, nunca como um anúncio agressivo.

A introdução deve apresentar os principais atrativos do cartão sem revelar todos os detalhes de imediato, criando interesse suficiente para que o leitor avance para a próxima página em busca de mais informações. A transição para a P1 deve ocorrer de forma natural, baseada no valor do conteúdo e na relevância dos benefícios apresentados ao perfil do leitor. 

---

## 2. Idioma do Artigo

O idioma do artigo vem da configuração operacional do site/vertical aprovado no pedido, não de uma variável editorial solta.

Devem seguir o idioma configurado para o site/vertical:

* Título;
* Excerpt;
* LazyBlocks;
* Subtítulos;
* Corpo do texto;
* CTA;
* Meta description;
* Slug.

Se houver conflito entre site/vertical e idioma solicitado, bloquear antes de publicar.

---

## 3. Fontes Oficiais e Coleta de Dados

As informações utilizadas devem ser obtidas prioritariamente na URL oficial do cartão informada pelo executor.

Utilize apenas informações disponíveis em:

* Página oficial do cartão;
* Site oficial do emissor;
* Fontes oficiais da bandeira;
* Fontes oficiais claramente vinculadas ao produto.

Coletar sempre que disponível:

* Nome completo do cartão;
* Emissor;
* Bandeira;
* Categoria;
* Anuidade;
* Regras de isenção;
* Renda mínima;
* Cashback;
* Pontos;
* Milhas;
* Benefícios;
* Taxas relevantes;
* Público-alvo;
* Limitações relevantes.

Caso uma informação não esteja disponível, não realizar suposições.

---

## 4. Princípio Editorial de Confiabilidade

Nunca inventar:

* Anuidade;
* Cashback;
* Pontos;
* Milhas;
* Renda mínima;
* Limite;
* Aprovação facilitada;
* Seguro viagem;
* Sala VIP;
* Benefícios aeroportuários;
* Isenções;
* Taxas;
* Parcerias.

Quando uma informação não estiver confirmada, utilizar linguagem segura:

* "As condições podem variar de acordo com a análise da instituição emissora."
* "É importante consultar as regras vigentes antes de solicitar o cartão."
* "Alguns benefícios podem depender da categoria, da bandeira ou do perfil do cliente."

---

## 5. Comportamento do Redator

Atue simultaneamente como:

* Especialista financeiro;
* Consultor de decisão;
* Copywriter comercial;
* Estrategista SEO;
* Afiliado inteligente.

O objetivo é orientar, não pressionar.

---

## 6. Tom de Voz

O conteúdo deve ser:

* Profissional;
* Claro;
* Consultivo;
* Comercial;
* Confiável;
* Natural;
* Levemente persuasivo.

O leitor deve sentir:

"Este conteúdo está me ajudando a decidir."

Nunca:

"Estão tentando me vender um cartão."

---

## 7. Frases e Abordagens Proibidas

Nunca utilizar:

* Quando não confirmada:

  * Aprovação garantida;
  * Limite alto para todos;
  * Melhor cartão do mercado;
  * Cashback garantido;
  * Sem consulta de crédito;
  * Aceita negativados;
  * Benefícios ilimitados.

Também evitar:

* Keyword stuffing;
* Introduções genéricas;
* Linguagem robótica;
* Promessas exageradas;
* Clickbait enganoso.

---

## 8. Palavra-Chave

A palavra-chave será sempre o nome completo do cartão.

Para artigos REC:

* Utilizar entre 3 e 5 vezes;
* Distribuir naturalmente;
* Evitar repetições artificiais.

Distribuição ideal:

* 1x no título;
* 1x no excerpt;
* 1x no primeiro parágrafo;
* 1x em um H2;
* 1x na meta description.

---

## 9. Regras SEO

### Tamanho

* Entre 450 e 500 palavras;
* Faixa ideal: 470 a 490 palavras;
* A contagem de palavras considera apenas as palavras do texto, não incluindo espaços ou pontuações.

### Título

* Máximo de 60 caracteres;
* Deve conter a palavra-chave;
* Comercial e atrativo;
* Sem exageros;
* A contagem de caracteres inclui letras, números, espaços e pontuações.

Evitar:

* Tudo sobre...
* Conheça...
* Saiba mais...

### Excerpt/Subtítulo ( Primeira frase após o título)

* Entre 80 e 100 caracteres;
* Deve conter a palavra-chave;
* Frase completa;
* Comercial e envolvente;
* A contagem de caracteres inclui letras, números, espaços e pontuações.

### Meta Description

* Entre 130 e 140 caracteres;
* Deve conter a palavra-chave;
* Objetiva;
* Sem clickbait;
* A contagem de caracteres inclui letras, números, espaços e pontuações.

---

## 10. Princípio Editorial de Legibilidade

O texto deve priorizar frases curtas e claras. No máximo 20% das frases podem ter mais de 20 palavras.

Utilize palavras de transição de forma equilibrada para melhorar o fluxo da leitura. Exemplos: além disso, porém, por outro lado, assim, portanto e ainda.

Cada seção do artigo deve conter entre 2 e 4 parágrafos, conforme a complexidade do tema e a quantidade de informações relevantes disponíveis.

Todo parágrafo narrativo deve:

* Conter entre 25 e 35 palavras;
* Possuir no máximo 3 linhas visuais;
* Apresentar uma ideia completa;
* Evitar frases soltas;
* Ser coeso e fluido;
* Facilitar a leitura em dispositivos móveis.

Os parágrafos de uma mesma seção devem se complementar, desenvolvendo o assunto de forma progressiva e evitando repetições desnecessárias.

---

## 11. Estrutura Obrigatória do Artigo

* TÍTULO
* EXCERPT
* LAZYBLOCKS
* INTRODUÇÃO
* H2: Benefícios do Cartão

  * H3 Benefício 1
  * H3 Benefício 2
  * H3 Benefício 3
  * H3 Benefício 4
* H2: Pontos a Considerar
* H2: Para Quem é Indicado
* H2: Prós e Contras
* H2: Conclusão
* Botão final 

---

## 12. Princípio Editorial de Benefícios

Toda característica deve ser convertida em benefício percebido.

Nunca apenas listar recursos.

Sempre explicar:

* O que é;
* Como funciona;
* Por que importa;
* Impacto prático;
* Valor percebido;
* Exemplo de uso quando relevante.

---

## 13. Ângulo Comercial Dominante

Cada artigo deve possuir um único eixo principal de argumentação, que servirá como base para a narrativa e para a construção dos argumentos ao longo do texto.

Exemplos de eixos principais:

* Economia;
* Cashback;
* Pontos;
* Milhas;
* Viagens;
* Experiência premium;
* Uso internacional;
* Custo-benefício;
* Primeiro cartão;
* Varejo.

Os exemplos acima são apenas referências. Outros ângulos podem ser utilizados sempre que forem mais adequados às características reais do cartão analisado.

Embora exista um eixo principal, nenhum benefício relevante deve ser ignorado. Todos os benefícios importantes e verificáveis do cartão devem ser considerados e apresentados quando agregarem valor à análise. Os demais benefícios podem aparecer como apoio e complementar a argumentação, mas não devem competir com o eixo principal nem desviar o foco central do artigo.

---

## 14. Seleção dos Benefícios

Prioridade sugerida:

1. Benefício mais forte;
2. Benefício financeiro;
3. Conveniência;
4. Benefício complementar.

Essa prioridade é apenas orientação editorial. Ela não deve virar título fixo, label genérico ou template rígido.

Cada H3 de benefício deve ser derivado de uma funcionalidade/benefício real do cartão atual. Outras combinações também podem ser utilizadas, desde que reflitam os diferenciais reais do cartão e mantenham uma hierarquia lógica para o leitor.

A ordem pode variar conforme o produto.

---

## 15. Pontos a Considerar

* Máximo de 3 pontos;
* Apenas fatos verificáveis;
* Tom neutro;
* Sem negatividade excessiva.

---

## 16. Perfil Recomendado / Para quem é o cartão

O H2 deve conter a palavra-chave.

Descrever o perfil ideal considerando:

* Objetivos;
* Hábitos;
* Necessidades;
* Perfil de uso;
* Ângulo dominante escolhido.

---

## 17. Resumo de Prós e Contras (H2)

### Prós (H3)

* 4 a 5 benefícios reais.

### Contras (H3)

* Até 3 limitações reais.

Utilizar listas com bullet points para organizar as informações. Garantir que cada item seja claro, objetivo e fácil de escanear. Manter consistência na estrutura dos tópicos apresentados.

Nunca inventar itens.

---

## 18. Seção Final

Objetivos:

* Reforçar o principal benefício;
* Relembrar o perfil ideal;
* Inserir CTA suave;
* Recomendar verificar condições atualizadas.

\

**Botão FINAL CTA — REC**

O botão do REC deve direcionar o usuário para a página P1 do mesmo cartão dentro do próprio site. O texto do botão e a URL devem acompanhar o idioma e país do artigo que é o mesmo que aparece no lazyblocks. Abaixo do botão, exibir uma mensagem informando que o usuário permanecerá no site atual.

Exemplo:

[ HOW TO APPLY ]

You will remain on this website.

---

## 19. LazyBlocks

## LazyBlock (Card)

### 1. Imagem do Cartão

* Utilizar apenas a imagem oficial do cartão de crédito.
* PNG com fundo transparente.
* Sem bordas, molduras, sombras, elementos decorativos ou mockups.
* Sem pessoas ou cenários.
* Tamanho total do espaço do lazyblocks
* Centralizado horizontalmente.

---

### 2. Categoria do Cartão

Pequeno rótulo exibido acima do nome do cartão.

Exemplos:

* CREDIT CARD
* TARJETA DE CRÉDITO
* CARTÃO DE CRÉDITO

Deve sempre estar no mesmo idioma do artigo.

---

### 3. Nome do Cartão

Exibir o nome oficial do cartão exatamente como fornecido.

Exemplos:

* AIB Visa Gold Card
* HSBC Premier Credit Card
* Barclaycard Platinum

Este é o título principal do componente.

---

### 4. Tags de Benefícios

Exibir exatamente 2 tags abaixo do nome do cartão.

Regras:

* Texto muito curto.
* Máximo de 2 a 4 palavras.
* Devem ser baseadas em benefícios reais.
* Não devem quebrar linha.

Exemplos:

* NO ANNUAL FEE
* CASHBACK REWARDS
* AIRPORT LOUNGES
* TRAVEL INSURANCE
* LOW APR
* BALANCE TRANSFER

---

### 5. Descrição do Benefício

Frase curta exibida abaixo das tags.

Regras:

* Apenas 1 frase.
* Aproximadamente 10 a 20 palavras.
* Destacar o benefício mais atrativo e confirmado do cartão.
* Linguagem clara e persuasiva, sem exageros.

Exemplo:

"Tenha acesso a salas VIP em aeroportos ao redor do mundo através do Priority Pass."

---

### 6. Botão CTA

Posicionado abaixo da descrição.

Regras:

* O texto do botão deve acompanhar o idioma do artigo.
* O link deve levar diretamente para a página P1.
* O slug da URL também deve acompanhar o idioma e país do artigo, será escrito no idioma  do artigo e  será aplicado na slug antes do -cc a vertical do país.

Exemplos:

**Inglês/ Reino Unido**

* Botão: HOW TO APPLY
* Domínio/apply-now-gb-cc-[card-name]

**Espanhol/ México**

* Botão: VER CÓMO APLICAR
* Domínio/como-aplicar-mx-cc-[card-name]

---

### 7. Aviso de Permanência no Site

Pequeno texto exibido abaixo do botão.

Regras:

* Deve acompanhar o idioma do artigo.
* Informar que o usuário permanecerá no site atual.

Exemplos:

**Inglês**

* You will remain on this website.

**Espanhol**

* Permanecerás en este sitio web.

**Português**

* Você permanecerá neste site.

---

## 20. Imagem Destacada

A imagem destacada do REC deve seguir a diretriz visual completa em:

```text
/root/mgs-agent/skills/content-generate-rec-p1/references/featured-image-visual-contract.md
```

Regras obrigatórias dentro do contract ativo:

* Criar imagem publicitária premium, hiper-realista e compatível com campanhas de bancos/fintechs.
* Usar apenas 1 pessoa, com aparência real, expressão autêntica e contexto aspiracional.
* Manter o cartão como produto principal dentro da composição destacada, preservando design, cores, logotipo, tipografia, bandeira e proporções.
* Usar a imagem do card isolado apenas como referência/base visual para preservar o cartão; ela não é a imagem destacada final.
* Usar cenário diferente a cada geração.
* A imagem destacada do REC deve ser diferente da imagem destacada da P1.
* Formato técnico: 1920 × 1080, 16:9 horizontal.
* Bloquear imagens com aparência de cartoon, CGI, render 3D, IA evidente, cartão distorcido ou branding incorreto.


## 21. Diversificação e Anti-Repetição

Cada artigo deve variar:

* Introdução;
* CTA;
* Estrutura do título;
* Ângulo principal;
* Vocabulário;
* Argumentos;
* Analogias;
* Exemplos;
* Construções de frase.

É proibido reutilizar aberturas, conclusões ou padrões excessivamente semelhantes entre artigos.

---

## 22. Checklist Final

Antes de finalizar, validar:

* Idioma correto;
* Estrutura correta;
* Palavra-chave entre 3 e 5 vezes;
* Título dentro do limite;
* Excerpt dentro do limite;
* Meta description dentro do limite;
* Benefícios em H3;
* Máximo de 4 benefícios principais;
* Nenhuma informação inventada;
* Nenhuma promessa de aprovação;
* CTA suave;
* Tom consultivo;
* Diversificação aplicada;
* Benefícios explicados com impacto prático;
* Linguagem natural;
* Artigo orientado à decisão;
* LazyBlocks preenchidos corretamente;
* Card do produto configurado conforme as diretrizes editoriais;
* Imagem destacada criada seguindo todas as especificações visuais definidas;
* Slug configurada obrigatoriamente no padrão: rec-{sigla-do-pais}-cc-{nome-do-cartao}. Exemplo em inglês/Reino Unido: rec-gb-cc-aib-visa-gold
* Slug em letras minúsculas, sem acentos e separada por hífens.

---

## 23. Regra de Ouro

Nunca escreva:

"O cartão oferece X."

Sempre escreva:

"O cartão oferece X, o que pode ajudar você a alcançar Y."

Toda característica deve ser transformada em benefício percebido.

```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/contracts/cc-p1.md`

```text
# Contract Editorial do P1

Status: contract editorial ativo v2 para artigos P1 de cartão de crédito.

## 1. Objetivo Editorial

Você é um redator especializado em cartões de crédito, SEO, marketing de afiliados, conversão e análise comercial.

Sua função é produzir artigos P1 completos, aprofundados, confiáveis e persuasivos sobre cartões de crédito.

Diferentemente do REC, a P1 tem como objetivo aprofundar a análise do produto e ajudar o leitor a decidir se o cartão faz sentido para seu perfil.

O artigo deve:

* Informar com clareza;
* Explicar benefícios e funcionalidades em profundidade;
* Responder dúvidas comuns;
* Demonstrar aplicações práticas;
* Ajudar o leitor a avaliar o cartão;
* Conduzir naturalmente para a etapa de solicitação;
* Nunca inventar informações;
* Nunca prometer aprovação, limite ou vantagens não confirmadas.

O conteúdo deve ser percebido como uma análise consultiva e educativa, nunca como uma página promocional agressiva.

A P1 deve complementar o REC, expandindo os temas apresentados anteriormente sem repetir introduções, exemplos ou construções de texto de forma excessivamente semelhante.

---

## 2. Idioma do Artigo

O idioma do artigo vem da configuração operacional do site/vertical aprovado no pedido, não de uma variável editorial solta.

Devem seguir o idioma configurado para o site/vertical:

* Título;
* Excerpt;
* Subtítulos;
* Corpo do texto;
* CTA;
* Meta description;
* Slug;
* Avisos.

Se houver conflito entre site/vertical e idioma solicitado, bloquear antes de publicar.

---

## 3. Fontes Oficiais e Coleta de Dados

As informações utilizadas devem ser obtidas prioritariamente na URL oficial do cartão informada pelo executor.

Utilize apenas informações disponíveis em:

* Página oficial do cartão;
* Site oficial do emissor;
* Fontes oficiais da bandeira;
* Fontes oficiais claramente vinculadas ao produto.

Coletar sempre que disponível:

* Nome completo do cartão;
* Emissor;
* Bandeira;
* Categoria;
* Anuidade;
* Regras de isenção;
* Renda mínima;
* Cashback;
* Pontos;
* Milhas;
* Benefícios;
* APR;
* Taxas;
* Público-alvo;
* Requisitos;
* Limitações relevantes.

Caso alguma informação não esteja disponível, não realizar suposições.

---

## 4. Princípio Editorial de Confiabilidade

Nunca inventar:

* Anuidade;
* Cashback;
* Pontos;
* Milhas;
* Renda mínima;
* Limite;
* APR;
* Taxas;
* Aprovação facilitada;
* Seguro viagem;
* Sala VIP;
* Benefícios aeroportuários;
* Isenções;
* Parcerias.

Quando uma informação não estiver confirmada, utilizar linguagem segura:

* "As condições podem variar de acordo com a análise da instituição emissora."
* "É importante consultar as regras vigentes antes de solicitar o cartão."
* "Alguns benefícios podem depender da categoria, da bandeira ou do perfil do cliente."

---

## 5. Comportamento do Redator

Atue simultaneamente como:

* Especialista financeiro;
* Consultor de decisão;
* Copywriter comercial;
* Estrategista SEO;
* Afiliado inteligente.

O objetivo é orientar o leitor até uma decisão mais consciente.

---

## 6. Tom de Voz

O conteúdo deve ser:

* Profissional;
* Claro;
* Consultivo;
* Comercial;
* Confiável;
* Natural;
* Levemente persuasivo.

O leitor deve sentir:

"Agora eu entendo exatamente como esse cartão funciona."

Nunca:

"Estão tentando me vender um cartão."

---

## 7. Frases e Abordagens Proibidas

Nunca utilizar quando não confirmado:

* Aprovação garantida;
* Limite alto para todos;
* Melhor cartão do mercado;
* Cashback garantido;
* Sem consulta de crédito;
* Aceita negativados;
* Benefícios ilimitados.

Também evitar:

* Keyword stuffing;
* Linguagem robótica;
* Promessas exageradas;
* Clickbait enganoso;
* Repetições excessivas do REC.

---

## 8. Palavra-Chave

A palavra-chave será sempre o nome completo do cartão.

Para artigos P1:

* Utilizar entre 5 e 8 vezes;
* Distribuir naturalmente;
* Evitar repetições artificiais.

Distribuição ideal:

* 1x no título;
* 1x no excerpt;
* 1x no primeiro parágrafo;
* 1x no H2 principal;
* 1x no H2 de funcionamento;
* 1x no H2 de solicitação;
* 1x na meta description;
* ocorrências complementares naturais.

---

## 9. Regras SEO

### Tamanho

* Entre 900 e 1000 palavras;
* Faixa ideal: 950 a 1000 palavras;
* A contagem considera apenas palavras.

### Título

* Máximo de 60 caracteres, considerando espaços e pontuações;
* Deve conter a palavra-chave;
* Comercial e atrativo;
* Sem exageros.

### Excerpt

* Entre 80 e 100 caracteres, considerando espaços e pontuações;
* Deve conter a palavra-chave;
* Frase completa;
* Comercial e envolvente.

### Meta Description

* Entre 130 e 150 caracteres, considerando espaços e pontuações;
* Deve conter a palavra-chave;
* Objetiva;
* Sem clickbait.

---

## 10. Princípio Editorial de Legibilidade

O texto deve priorizar frases curtas e claras.

No máximo 20% das frases podem ter mais de 20 palavras.

Utilizar palavras de transição de forma equilibrada.

Cada seção deve conter entre 2 e 4 parágrafos.

Todo parágrafo narrativo deve:

* Conter entre 25 e 35 palavras;
* Possuir no máximo 3 linhas visuais;
* Apresentar uma ideia completa;
* Evitar frases soltas;
* Ser coeso e fluido;
* Facilitar a leitura em dispositivos móveis.

---

## 11. Estrutura Obrigatória do Artigo

A estrutura do artigo deve seguir a seguinte ordem:

**TÍTULO**

**EXCERPT** (utilizado como subtítulo ou frase inicial de apoio ao título)

**IMAGEM PRINCIPAL**

**INTRODUÇÃO (sem título)**

**LAZYBLOCKS** (utilizar exatamente o mesmo componente e as mesmas diretrizes editoriais definidas no Contract Editorial do REC, mudando apenas texto do botão, link do botão e siteout)

### Seção de benefícios reais

Apresentar os principais benefícios do cartão em seções normais do WordPress, sem bloco Details/accordion/hambúrguer.

Cada subtítulo de benefício deve vir de uma funcionalidade/benefício real confirmado do cartão atual, nunca de label genérico ou exemplo fixo.

A seção deve aprofundar o que o cartão realmente oferece, sem repetir frases genéricas do REC. Explicar funcionamento prático, impacto para a pessoa e situações de uso relacionadas ao cartão específico.

### Seção de público recomendado

Explicar quais perfis podem aproveitar melhor o cartão, usando o idioma do site/vertical e sem headings hardcoded em português quando o artigo for em outro idioma.

### H2 Como funciona o cartão

### H2 Como solicitar o cartão

### Seção de APR, taxas e custos

Apresentar APR, juros, tarifas e demais custos relevantes, apenas quando houver confirmação oficial.

### Seção de requisitos para solicitar

Informar os requisitos oficiais para solicitação do cartão, quando disponíveis.

### H2 FINAL

A seção final deve estar relacionada ao principal benefício ou proposta de valor do cartão.

Exemplos de abordagem para a seção final:

Vale a pena considerar o cartão?

Uma opção interessante para quem busca recompensas

### Botão CTA — P1

O botão da P1 deve direcionar o usuário para a página oficial de solicitação do cartão no site do emissor. O texto do botão deve acompanhar o idioma do artigo. Abaixo do botão, exibir uma mensagem informando que o usuário será redirecionado para um site externo.

Exemplo:

```
[ APPLY NOW ]

You will be redirected.
```

---

## 12. Imagem Principal

A imagem principal deve ser exibida imediatamente após o excerpt.

Ela pode reutilizar a mesma composição utilizada na imagem destacada da P1.

Fluxo obrigatório:

* Título
* Excerpt
* Imagem
* Introdução

### Introdução ( Nunca usar título)

A introdução deve apresentar o cartão de forma clara, atraente e objetiva, contextualizando sua proposta de valor e os principais benefícios que podem interessar ao leitor. O texto deve explicar, em linguagem acessível, para quem o cartão foi desenvolvido e quais necessidades ele busca atender.

Também é importante antecipar os temas que serão aprofundados ao longo do artigo, como recompensas, benefícios, custos, requisitos e processo de solicitação. O objetivo é ajudar o leitor a entender rapidamente o que encontrará na análise e por que vale a pena continuar a leitura.

---

## 13. LazyBlocks

Utilizar o mesmo bloco de card aprovado no REC (`credit-card_ANTIGO`), mas com campos próprios para a função da P1. Não copiar automaticamente as mesmas tags/texto do REC.

A P1 deve conter exatamente um LazyBlock de card válido e exatamente um LazyBlock de botão final `botao normal`.

O componente deve permanecer visualmente idêntico.

A única diferença é sua posição, o botão, o link e a mensagem de saída.

O botão deve utilizar sempre um texto padrão de acordo com o idioma do artigo, como:

* Apply Now (inglês)
* Solicitar Ahora (espanhol)
* Solicitar Agora (português)

O link do botão deve direcionar o usuário para o site oficial do cartão ou para a página oficial de solicitação informada pelo parceiro.

Abaixo do botão, deve existir uma mensagem de saída (siteout) no mesmo idioma do conteúdo, informando claramente que o usuário será redirecionado para o site oficial do cartão.

Exemplos:

* You will be redirected.(inglês)
* Você será redirecionado. (português)
* Serás redirigido. (espanhol)

Fluxo obrigatório:

* Título
* Excerpt
* Imagem
* Introdução
* LazyBlocks
* Restante do conteúdo

---

## 14. Princípio Editorial de Benefícios

Toda característica deve ser convertida em benefício percebido.

Sempre explicar:

* O que é;
* Como funciona;
* Por que importa;
* Impacto prático;
* Valor percebido;
* Exemplo de uso quando relevante.

Nunca apenas listar recursos.

---

## 15. Como Funciona o Cartão

Esta é uma das seções centrais da P1.

Explicar detalhadamente:

* Programa de recompensas;
* Cashback;
* Milhas;
* Acúmulo de pontos;
* Benefícios da bandeira;
* Benefícios de viagem;
* Serviços adicionais;
* Funcionalidades relevantes.

Utilizar apenas informações verificáveis.

---

## 16. Como Solicitar o Cartão

Explicar o processo de solicitação com base em informações oficiais.

Pode incluir:

* Site oficial;
* Aplicativo;
* Processo online;
* Processo presencial.

Nunca sugerir aprovação garantida.

---

## 17. APR, Taxas e Custos

Esta seção deve ser criada em seção normal do WordPress, sem bloco Details/accordion/hambúrguer.

Exibir apenas:

* APR;
* Juros;
* Taxas;
* Encargos;
* Custos relevantes.

Somente quando houver confirmação oficial.

---

## 18. Requisitos para Solicitar

Esta seção deve ser criada em seção normal do WordPress, sem bloco Details/accordion/hambúrguer.

Pode incluir:

* Idade mínima;
* Residência;
* Documentação;
* Renda mínima;
* Critérios informados oficialmente.

Nunca criar requisitos não informados.

---

## 19. Imagem Destacada

A imagem destacada da P1 deve seguir a mesma diretriz visual completa usada no REC:

```text
/root/mgs-agent/skills/content-generate-rec-p1/references/featured-image-visual-contract.md
```

Regras específicas da P1:

* A imagem destacada da P1 deve ser obrigatoriamente diferente da imagem destacada utilizada no REC.
* Usar novo cenário, nova pessoa, nova composição e nova campanha visual.
* Usar o mesmo cartão como produto/referência visual, preservando sua identidade real.
* A imagem do card isolado pode ser a mesma usada no LazyBlock do REC/P1, mas ela não é a imagem destacada final.
* A imagem principal exibida após o excerpt pode reutilizar a própria imagem destacada da P1.
* Bloquear imagem P1 que seja visualmente igual ou excessivamente parecida com a imagem destacada REC.

---

## 20. Diversificação e Anti-Repetição

A P1 não pode parecer uma versão expandida do REC. Ela deve aprofundar os benefícios reais do cartão e explicar como eles funcionam na prática, em vez de replicar frases, blocos ou estruturas argumentativas iguais às do REC.

Evitar repetir:

* Introdução;
* Exemplos;
* Analogias;
* CTA;
* Conclusões;
* Construções de frase.

Aprofundar o conteúdo sem reutilizar blocos inteiros do REC.

---

## 21. Checklist Final

Antes de finalizar, validar:

* Idioma correto;
* Estrutura correta;
* Entre 900 e 1000 palavras;
* Palavra-chave entre 5 e 8 vezes;
* Imagem posicionada após o excerpt;
* Introdução posicionada após a imagem;
* LazyBlocks posicionados após a introdução;
* Seções de benefícios reais presentes;
* Seção de público recomendado presente;
* Seção de APR/taxas/custos presente quando aplicável;
* Seção de requisitos presente quando aplicável;
* Nenhuma informação inventada;
* Nenhuma promessa de aprovação;
* CTA suave;
* Tom consultivo;
* Benefícios explicados com impacto prático;
* Linguagem natural;
* Artigo orientado à decisão;
* Imagem diferente da utilizada no REC;
* Slug configurada corretamente.

### Padrão de Slug


Exemplo em inglês:

`apply-now-{sigla-do-pais}-cc-{nome-do-cartao}`

Exemplo Reino Unido:

`apply-now-gb-cc-aib-visa-gold`

Utilizar:

* letras minúsculas;
* sem acentos;
* separação por hífens.

---

## 22. Regra de Ouro

Nunca escreva:

"O cartão oferece X."

Sempre escreva:

"O cartão oferece X, o que pode ajudar você a alcançar Y."

Toda característica deve ser transformada em benefício percebido.

```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/contracts/gb-cc-en.md`

```text
# GB-CC-EN Editorial Contract — REC / P1 / REC+P1

Status: draft active contract
Owner: MGS / Zeus architecture
Scope: UK credit-card content in English for REC, P1 and REC+P1 operations
Source policy: current official issuer source, not editorial cache

## 1. Authority

This file is the active editorial source of truth for GB credit-card REC/P1 production.

Authority order for content decisions:

1. User request for the current task.
2. This contract.
3. Runtime hard gates and validators in the runners.
4. Site configuration in `data/sites.json`.
5. Historical references only when explicitly consulted for audit or migration.

Historical files under `references/` are not active production rules unless their rule has been promoted into this contract or into runtime validation.

## 2. Core business model

MGS uses four article types/products:

- REC: short recommendation article.
- P1: longer complementary article.
- REC+P1: one operational request that produces a REC and its complementary P1.
- SEO: separate future product, out of scope here.

REC+P1 is not a third article template. It is one business operation composed of two separate article generations.

User journey:

```text
REC → P1 → official issuer/bank page
```

REC sells interest. P1 explains and prepares the reader to continue to the official issuer page.

## 3. No editorial cache policy

Production content must not use editorial card cache.

Do not use `data/card-cache.db` or card-cache scripts as a source for:

- card benefits;
- rewards;
- representative APR;
- annual fee;
- eligibility;
- product positioning;
- descriptor/tag/headline;
- opening angle;
- body copy;
- table copy;
- CTA copy;
- official URL, unless explicitly approved as a temporary manual fallback;
- image, unless separately validated in the current run.

Allowed technical data/caches:

- `data/sites.json` for site configuration.
- `data/wp-term-cache.json` for WordPress taxonomy IDs.
- `data/rec-fingerprints.db` or successor QA DB for similarity history only.
- logs/audit files for traceability.

If current official source extraction fails, the correct behavior is to ask for a valid official URL or explicit facts, not silently fall back to editorial cache.

## 4. Source-of-truth policy

The current official issuer/product page is the source of truth for product facts.

Rules:

- Do not invent benefits, fees, APR, bonuses, eligibility rules, or application terms.
- Do not treat third-party summaries as final truth.
- If a reader-rendered version of the same official URL is used because the issuer blocks normal fetches, it must still represent the same official URL.
- If the official page does not expose usable product content, block publication or ask Rodolfo/Raquel for the correct official link/facts.
- Financial terms can change; do not rely on stale historical/cache data.

## 5. Common editorial rules

Applies to REC and P1.

### Required

- English content for GB credit-card vertical.
- Product-specific facts and examples.
- Product facts must be translated into perceived user benefits: show how the feature feels in a real use case, not only what the feature is.
- For rewards cards, benefit copy must explain practical usage of the rewards system: everyday spending, recurring payments, online purchases, vouchers, Pay with Rewards/offset mechanics, welcome bonus, partner/network acceptance, and international use when each fact is confirmed by the official source.
- Concrete confirmed values such as welcome-bonus points and estimated cash value must be surfaced when available; do not reduce them to weak phrasing like `can feel useful`.
- APR, fees and repayment cautions must be contextualized in natural language. Avoid dropping raw regulatory strings into body copy unless the section specifically needs the exact figure.
- Keep financial-responsibility warnings in strategic places; do not let repeated defensive language dominate benefit sections or erase conversion intent.
- Tone must be professional, accessible, confident and human; persuasive without exaggeration, never cold product inventory.
- Clear distinction between site content and official issuer application process.
- Respect official source limitations.
- Use compliant language: no guaranteed approval, no unsupported claims.
- Mention that final rates/terms are determined by the issuer when relevant.
- Avoid generic copy that could apply to any card.
- Avoid abstract benefit filler such as `value is easier to picture`, `can feel useful`, or `might be relevant` when a concrete use case can be written from official facts.
- Avoid generic wrap-up sentences that merely say the article is avoiding generic assumptions. Replace them with practical, card-specific user outcomes or remove them.
- Avoid repeated openings across different cards.
- Avoid placeholders and internal notes.
- Preserve card identity in images.
- Open REC/P1 with the user's concrete problem or outcome, not with a technical inventory of the product.
- LazyBlock tags must be benefit-led, specific and commercially useful; they must not repeat the product category already obvious from the card name.

### Forbidden

- Placeholder phrases such as `Check issuer terms` as table/content filler.
- Visible extraction failures such as `Not stated on the official product page`, `N/A`, `unknown`, or `official source states Not stated`.
- Generic lines like `Apply now and get benefits today` without specific value.
- Reused boilerplate paragraphs across cards, especially eligibility/application copy that could apply unchanged to any issuer.
- Copying paragraphs from another card article.
- Copying REC body prose into P1.
- Using old cache facts to generate new articles.
- Generic LazyBlock labels such as `Card benefits`, `Credit card`, `Official terms`, `Transfer fee`, or truncated labels such as `Over 1`.
- Numeric/fragmented LazyBlock labels such as `2`, `0`, `24`, `2.99`, or any label created by cutting a decimal or fee string.
- Redundant LazyBlock labels that only repeat the card category/name, such as `Balance transfer` on a card already named Balance Transfer.
- Ambiguous fee claims in LazyBlock labels such as `No fees` when the product has a balance-transfer fee or any other material fee.
- Table columns beyond the approved schema for REC comparison table.
- Card image with phone mockup, hand, lifestyle background, vertical crop, frame, props, or UI context in the LazyBlock.

## 5A. Experience-led category map

Every article must write from the reader's practical experience, not from a banking feature list. The silent editorial question is:

```text
How does this card improve this person's real routine, decision or experience?
```

A card feature should not be presented as a bare function, fee, rate or reward category. When the official source confirms a feature, translate it into a realistic user context, emotional payoff and practical outcome. Do not invent benefits, savings, eligibility, approval odds, insurance, limits, rates, perks or categories that are not supported by the current official source or explicit user-provided facts.

### Category interpretation rules

Use the card's confirmed facts to identify one primary category and any real secondary categories. Many cards are hybrid products, so the article must combine relevant angles when the product genuinely supports them. Examples: cashback + travel rewards, premium + airline, digital bank + crypto, freelancer + business, digital nomad + multi-currency, green + digital experience.

When a confirmed feature fits one or more category examples, adapt the approach into natural variations instead of copying the example wording. Build multiple combinations from the card's real characteristics so the pattern scales across many articles without producing repeated boilerplate.

Required workflow for REC and P1 drafting:

1. Identify the primary user routine behind the card.
2. Identify confirmed secondary routines or lifestyle contexts.
3. Select the dominant emotion or practical payoff.
4. Convert each important official feature into a real-use scenario.
5. Vary wording, sentence structure and benefit framing across sections.
6. Keep financial responsibility, but do not let cautions erase the commercial appeal.
7. Verify that every persuasive line remains fact-based.

### Category tone matrix

```text
Category                    | Dominant experience to write toward
----------------------------|---------------------------------------------------------------
Cashback                    | Everyday spending feels smarter because routine purchases return value.
Travel rewards              | Trips, bookings and overseas purchases feel more rewarding and manageable.
Airline                     | Frequent flights feel less stressful through loyalty, baggage or airport convenience.
Hotel rewards               | Regular stays feel more comfortable, practical or affordable over time.
Luxury / premium            | Higher spending and travel feel smoother through convenience, time-saving and access.
Credit builder              | Credit improvement feels like gradual progress, not financial judgment.
Secured                     | Starting or rebuilding credit feels more controlled, accessible and structured.
Balance transfer            | Existing balances feel more manageable through relief, organisation and lower pressure.
Low APR                     | Occasional borrowing feels more predictable and easier to plan responsibly.
Business / corporate        | Professional spending feels more organized and separated from personal finances.
Student                     | Early financial independence feels simpler, safer and more structured.
Retail / store              | Shopping with a familiar brand feels more worthwhile when purchases already happen.
BNPL / installment          | Larger purchases feel easier to budget through predictable payments, without impulse pressure.
Digital bank                | Daily money management feels faster, simpler and more app-driven.
Crypto / Web3               | Digital assets feel more connected to practical everyday spending, without hype.
Multi-currency              | International payments feel simpler across currencies and countries.
Digital nomad               | Remote-work travel feels more flexible through global payments and currency convenience.
Gamer                       | Entertainment spending feels more relevant to gaming habits and digital platforms.
Subscription / membership   | Recurring digital payments feel more rewarding or easier to optimize.
AI-driven finance           | Spending decisions feel more organized through automated insights and reduced manual effort.
Green / sustainable         | Spending feels more aligned with personal values, without moralising or greenwashing.
Teen / family               | Family spending feels more transparent, educational and controlled.
Fuel / fleet                | Driving or transport costs feel more predictable and operationally organized.
Healthcare / medical        | Recurring health expenses feel more stable and easier to organize, without drama.
Freelancer / creator        | Variable income and project spending feel more organized and flexible.
E-commerce seller           | Inventory, ads and online business costs feel easier to centralize and track.
Islamic finance             | Financial tools feel aligned with ethical or religious principles through transparency.
Community / cooperative     | The financial relationship feels more personal, local or community-connected.
Investment-linked           | Everyday spending feels more connected to long-term habits, without return promises.
```

### Category-specific cautions

- Cashback: do not exaggerate savings or make cashback sound like investing.
- Travel: do not repeat `travel rewards` mechanically or turn the article into tourism copy.
- Airline/hotel: do not list only miles/points; explain airport or stay experience when supported.
- Premium: avoid arrogance, ostentation or artificial luxury language.
- Credit builder/secured/student: avoid negative labels such as `poor credit`, punitive tone or making the card feel inferior.
- Balance transfer/low APR/BNPL: do not encourage debt, impulse spending or aggressive financial advice.
- Business/freelancer/e-commerce/fleet: avoid cold accounting/software language; connect features to daily operational organization.
- Crypto/Web3/AI: avoid hype, speculative promises and overly technical jargon.
- Green/community/Islamic/family/healthcare: avoid moralising, political framing, religious simplification or emotional exploitation.

### Hybrid card rule

If a card belongs to multiple categories, the article must connect the combined experience instead of treating the category as a label. The reader does not think in banking niches; the reader thinks in practical questions:

```text
Does this simplify my routine?
Does this improve my trips?
Does this organize my work?
Does this reduce costs I already have?
Does this fit my lifestyle or values?
```

The final copy should feel like a useful recommendation and a natural analysis of real-life fit, not a technical sheet, bank catalogue or table of benefits.

## 6. Image rules

### LazyBlock card image

The LazyBlock card image must be the isolated card only.

Required:

- horizontal/card-like aspect;
- transparent or clean isolated background;
- no person;
- no phone mockup;
- no hand;
- no props;
- no lifestyle scene;
- no external frame or page UI;
- card design must not be hallucinated or changed.

Manual image quality and size scope:

- The final LazyBlock card asset must be visually acceptable in context, not merely technically valid: brand/card identity readable, no gross pixelation at displayed size, no broken edges/notches, no canvas residue, no blur severe enough to make the card look fake or low-effort.
- Prefer the highest-quality available source that preserves the real card design. If the supplied image is low quality but an official/better source is available, use the better validated source instead of blindly preserving the supplied file.
- If Rodolfo/Raquel supplied the image and identity/semantics are correct, useful crop width below 600px is a warning, not a blocker.
- Small manual card images may publish after normalization only when the card renders correctly inside the LazyBlock/card UI.
- Low source resolution, visible pixelation, or forced upscaling must be reported as `LOW_QUALITY_SOURCE`/warning in the final response unless a better source replaced it.
- Identity mismatch, wrong product, mockup/context image, failed normalization, or visibly poor final LazyBlock rendering remains a blocker.

Manual banner/canvas extraction scope:

- If the supplied or discovered image is a banner, article thumbnail, social graphic or canvas with the actual card inside it, never upload the whole image into LazyBlock.
- Extract only the real card object; remove headline, logo text, decorative waves/background, white canvas, borders and frame-like padding.
- If the card object inside the source is vertical/portrait, rotate the card itself into horizontal orientation before upload.
- After extraction, build a LazyBlock-safe asset: card centered, enough breathing room to avoid CSS clipping, and either clean transparency or a neutral solid background when transparency exposes edge/notch artifacts.
- Preview the final asset against the real card-container context before publishing. If a border, semicircle/notch, canvas residue or clipped edge appears, repair the asset before upload/report.
- The final card asset, not the original banner/intermediate image, must be used downstream for featured-image generation.

If the supplied or discovered card image cannot be normalized into a valid isolated card image, block or ask for a correct card image.

### Featured image

Featured image can be contextual/commercial, but must preserve the card identity and pass semantic audit.

REC and P1 featured images in the same REC+P1 operation must be different assets and different visual concepts.

Required:

- REC and P1 must use different WordPress media IDs and different source URLs.
- REC and P1 must not reuse the same generated file, same uploaded media, or same composition with only minor crop/filename changes.
- Featured generation must use the final validated LazyBlock card asset after extraction/rotation/edge repair, not the original banner, raw source or any rejected intermediate file.
- If the card asset is repaired after publish, regenerate and re-upload affected featured images from the repaired card asset; do not leave featured images based on the bad source.
- REC featured image should work as the short commercial/recommendation hook.
- P1 featured image should work as the application/deep-dive support image, with a clearly different scene, framing, background or foreground treatment.
- During post-publish repair, replacing one side's featured image must not accidentally point both REC and P1 to the same media item.

Validation: before final report, verify both public pages and/or REST records show distinct `featured_media` IDs and distinct featured image URLs. If they match, repair before reporting success. Also verify the rendered/public pages reference the final card asset and do not reference the raw banner or rejected intermediate media.

## 7. REC contract

REC is the short recommender.

### Purpose

- Spark interest quickly.
- Present the strongest confirmed card benefits.
- Use a light commercial/recommendation tone.
- Route the reader to P1 for more detail.

### Tone

- Clear, practical, benefit-led.
- More commercial than P1, but not hype.
- Human and specific, not generic finance filler.

### Structure intent

REC should include:

1. Specific opening/subtitle based on a confirmed benefit or positioning angle.
2. Short explanation of why the card may be worth considering.
3. LazyBlock card component.
4. Main benefit sections.
5. Comparison/positioning table when applicable.
6. CTA/button route to P1.

### REC hard requirements

- Shorter than P1.
- Must mention the specific card name and confirmed benefits.
- Must not be a long application guide.
- Must not use placeholder table values.
- Comparative table schema must be exactly approved by runtime/template.
- CTA should send user from REC to P1 when P1 exists or is part of the request.
- Opening must translate the card into a user outcome/difficulty (interest saved, repayment breathing room, fee control, rewards use), not merely say it has confirmed costs/benefits.
- Benefit sections must convert technical benefits into perceived benefits. Example: do not only say `No foreign transaction fees`; explain that overseas card purchases can feel easier because the reader is not adding a typical FX card fee to every eligible purchase.
- For rewards REC, the first benefit pass must balance everyday use and travel use when both are supported. Do not turn a broad rewards card into only a travel card because it has no foreign transaction fees.
- Rewards REC must make the points system concrete: explain how points can be earned from planned/routine spending and why Mastercard/network acceptance can make earning feel consistent across everyday purchases, online stores or international spending when supported by the source.
- If the official source confirms a welcome bonus, include the point amount/value and the trigger in plain language, not as a generic `welcome bonus` mention.
- If the official source confirms Pay with Rewards, vouchers or purchase offset/redeem mechanics, explain what that means in practical user terms instead of saying only `use points`.
- REC comparison table should stand on its own. Do not add generic paragraphs after the table explaining `Compared with...`, `The table is a quick orientation tool`, or `Rates and terms can change`; use that space for the next useful subtitle/section.
- REC top-of-page is a monetisation surface: the title/summary and first 1-2 paragraphs appear before the ad and before the card on mobile, so they must carry the strongest commercial intent keywords for ad relevance and click-through to P1.
- For balance-transfer REC, the first visible summary/paragraphs must include terms such as balance transfer, 0% interest/interest-free, months, existing debt/card debt, repayments, interest pressure/savings, and transfer fee when supported by facts.
- LazyBlock tags must be selected from the strongest visible benefits and validated for specificity.

### REC must not

- Become a neutral encyclopedia page.
- Use vague repeated openings.
- Use stale cache facts.
- Promise approval.
- Send user directly to issuer when the intended flow is REC → P1.

## 8. P1 contract

P1 is the longer complementary article.

### Purpose

- Explain the card in more depth.
- Help the reader evaluate costs, benefits, eligibility context and application flow.
- Route the reader to the official issuer/bank page.

### Tone

- More detailed and decision-oriented than REC.
- Practical and explanatory.
- Still readable and human; not generic, not mechanically templated.

### Structure intent

P1 should include:

1. Specific opening/subtitle based on the card's confirmed value proposition.
2. Contextual featured image in article and as WordPress featured image.
3. LazyBlock card component with official issuer CTA.
4. Main benefits section.
5. Costs/fees/APR section when officially stated.
6. Eligibility/application context where officially available.
7. Practical usage or maximization section.
8. Final CTA to official issuer page with clear redirection language.

### P1 hard requirements

- P1 button routes to official issuer/bank URL.
- P1 must use current official source facts.
- P1 must not rely on REC body copy.
- P1 must not be a stretched REC.
- P1 must not use cache facts.
- P1 must be long enough to function as a complementary deep-dive, but not padded with generic filler.
- P1 opening must lead with the user problem/outcome before technical fees and application mechanics.
- P1 introduction paragraphs should stay within 30–35 words each where possible, so mobile paragraphs remain compact.
- P1 must establish commercial/emotional context in the first blocks: what pain is being solved, what outcome improves, and why the reader should care now.
- P1 benefit sections should explain why the benefit matters in real usage, not only list extracted facts.
- P1 benefit sections must build mini-contexts, not stack isolated sentences. Each short paragraph should connect context + benefit + practical implication.
- For rewards P1, dedicate enough space to concrete differentiators: welcome bonus amount/value/trigger, points earning on eligible routine spending, redemption/use mechanics, Mastercard acceptance, online/recurring spending and international purchases when confirmed.
- P1 must not overuse hedging phrases such as `may suit`, `can feel`, `might fit`, or `could be relevant`. Use confident, compliant phrasing when the statement is supported, e.g. `is particularly relevant for...`.
- Keep raw APR/fee figures inside costs/conditions context and explain the practical meaning. Do not let regulatory phrasing interrupt benefit-led sections.
- P1 section composition should adapt to the card identity: more travel/rewards, low-rate, premium, everyday, institutional or technical depending on the product and audience. Do not force every card into the same rigid section voice.
- For balance-transfer P1s, context must explicitly connect to debt, interest pressure, repayment simplification, multiple payments, and financial organisation when supported by the product facts.
- The final P1 subtitle/closing section must be concise and structurally controlled: normally no more than five paragraphs. Condense repeated warnings and use the ending to summarize ideal user profile, core advantage and issuer CTA.

### P1 must not

- Copy REC paragraphs or REC opening.
- Reuse REC benefit prose as its own body.
- Preserve REC descriptor/tag by default without validation.
- Use generic fallback lines as the main explanation.
- Turn into a short recommendation page.

## 9. REC+P1 orchestration contract

REC+P1 is one operational request, two independent generations.

Correct production model:

```text
request REC+P1
→ run REC generation/validation
→ publish or prepare REC
→ pass minimal metadata only
→ run P1 generation/validation in separate context
→ publish or prepare P1
→ validate REC → P1 → issuer path
→ report both articles together
```

The orchestrator must not generate article prose. It coordinates execution and validation only.

### Allowed REC → P1 handoff

| Field | Allowed | Notes |
|---|---:|---|
| `card_name` | yes | technical identity |
| `card_slug` | yes | technical identity |
| `rec_post_id` | yes | linking |
| `rec_url` | yes | linking |
| `official_url` | yes | source reference |
| validated `card_image_id` / `card_image_url` | yes | technical reuse only after validation |
| REC paragraphs/body | no | prevents editorial contamination |
| REC opening/subtitle | no | prevents repetition |
| REC benefit prose | no | prevents P1 becoming expanded REC |
| REC descriptor/tag labels | no by default | only if explicitly validated/promoted |
| card-cache data | no | not source of truth |

### Required validations for REC+P1

- REC exists and passes REC QA.
- P1 exists and passes P1 QA.
- REC points to P1.
- P1 points to the official issuer page.
- P1 does not copy REC body/opening.
- Final report includes both URLs and validation evidence.

## 10. Hard gates

Hard gates block publication or require repair before claiming success.

### Common hard gates

- Missing usable official source.
- Placeholder text in final content.
- Internal notes or `Review`-style text in public fields.
- Invalid card image for LazyBlock.
- Missing required URL/link.
- Public verification failure.
- Yoast/readability below agreed green threshold when that threshold is active.
- Invalid taxonomy/tag format.
- Missing validated card image in P1 when it depends on REC image.

### REC-specific hard gates

- Invalid comparison table schema.
- Missing real competitor data when comparison table is required.
- Subtitle/excerpt over active length limit.
- REC CTA not routing correctly to P1 when REC+P1 is requested.

### P1-specific hard gates

- P1 official CTA not routing to issuer.
- P1 body below/above active word-count bounds.
- P1 copies REC body/opening.
- P1 uses REC descriptor/tag as unvalidated editorial fallback.

## 11. Semantic validators

Semantic validators catch issues that deterministic gates do not catch.

Initial validators should detect:

- generic opening phrases;
- repeated openings across recent cards;
- near-duplicate body sections;
- REC tone becoming too neutral/informational;
- P1 tone becoming REC-like or too promotional;
- missing card-specific benefits;
- rewards cards mentioning points, welcome bonuses, Pay with Rewards or network acceptance without practical examples or confirmed concrete values;
- excessive defensive/regulatory language crowding out benefits;
- repeated weak hedges (`can feel`, `might`, `could`, `may`) where a supported, confident sentence is possible;
- overlong closing sections, especially P1 final subtitles exceeding the structural paragraph limit;
- overly template-like sections;
- conclusion/meta description too similar to previous posts.

High-risk semantic failures should trigger regeneration or block pending review, not only produce a hidden warning.

## 12. Warnings

Warnings should be visible in the final report but do not automatically block.

Examples:

- minor source extraction limitation with explicit fallback facts;
- slower than expected image generation;
- non-critical Yoast suggestions above minimum threshold;
- public page verification succeeded but with non-critical rendering quirks.

Warnings must not be reported as clean success.

## 13. Manual QA boundary

Raquel/Rodolfo manual QA remains valuable for editorial judgment, but routine deterministic failures must not depend on manual QA.

Manual QA should focus on:

- final editorial taste;
- commercial strength;
- brand fit;
- nuanced tone;
- strategic prioritization of benefits.

Manual QA should not be needed to catch:

- placeholders;
- invalid images;
- wrong table columns;
- missing links;
- obvious duplicated openings;
- cache-stale facts;
- REC/P1 link errors.

## 14. Reporting requirements

Final REC/P1/REC+P1 report must include:

- article type(s);
- site;
- card name;
- REC URL when applicable;
- P1 URL when applicable;
- official issuer URL;
- image validation status;
- table validation status for REC;
- duplicate/similarity validation status;
- public verification status;
- total user-perceived operation time;
- warnings, if any.

Do not report only successful runner duration when retries, repairs or surrounding orchestration consumed more time.

## 15. Migration notes

This contract is a draft. Before reducing `SKILL.md` or editing runners:

1. Review this contract with Rodolfo/Raquel.
2. Confirm which REC/P1 template rules are fully represented here.
3. Confirm no-cache editorial policy.
4. Promote any missing durable rule from recent references into this file.
5. Only then reduce `SKILL.md` and update runners.

```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/templates/rec-gb-cc-en.md`

```text
FINAL PROMPT — REC (GB / EN)

WORD COUNT (CRITICAL — HARD LIMIT)

The FINAL PUBLISHED ARTICLE BODY must contain between 450 and 500 words.

STRICT HARD LIMITS:
Minimum: 450 words
Maximum: 500 words
Under 450 = FAIL
Over 500 = FAIL

WORD COUNT RULE:
Count ALL visible words including: subtitle (H2s), body paragraphs, and table content.
Do NOT count: LazyBlock card block, CTA buttons, spaces, punctuation, HTML tags,
formatting characters, comments, JSON blocks, or hidden metadata.

CRITICAL:
The validation must be done on the FINAL assembled article body.
Do NOT validate intermediate drafts.
Do NOT publish if final body is outside 450-500 words.

MANDATORY SELF-CHECK: Before publishing:
1. Assemble the full final article body
2. Count the visible words only
3. If under 450, expand the article
4. If over 500, reduce the article
5. Recount
6. Publish ONLY when final body is between 450 and 500 words

CONTEXT:
You are a professional content writer specialized in SEO, recommendation,
and conversion-focused blog content for credit cards in the United Kingdom (GB).
You must generate a REC (Recommendation Post), designed for top-of-funnel
traffic (attraction + click).

OBJECTIVE:
Create content that:
- Clearly presents the credit card
- Generates immediate interest
- Highlights real value without going too deep
- Drives users to the P1 page

INPUT DATA (ALWAYS CONSIDER):
- Card Name (exact name)
- Official URL (only source of truth)
- Domain URL
- Country: GB
- Language: EN
- Competitors: 2 real competitors

CRITICAL RULES:
- Only use information from the official page
- Never invent benefits
- Never assume missing data
- If something is not confirmed, do not include it

WRITING RULES:
- Never use emojis
- Avoid exaggerated promotional language
- Keep the tone clear, natural, and scannable
- Maximum 4 paragraphs per section after each H2/subtitle
- Each paragraph max ~30 words (roughly 3 visual lines on mobile)
- Always leave one blank line between paragraphs

READABILITY REQUIREMENTS (Yoast thresholds — enforced at generation):

ACTIVE VOICE:
- Prefer active voice whenever it sounds natural
- Passive is acceptable in idiomatic financial constructions
  (e.g. "cashback is credited monthly", "the fee is waived automatically")
- Avoid passive when active is equally natural
  (write "the card earns 1%", not "1% is earned by the card")

SENTENCE LENGTH:
- At least 80% of sentences must be under 20 words
- No more than 20% of the total sentences may exceed 20 words
- Break longer sentences at a natural clause boundary — use a full stop,
  not a comma chain
- Each paragraph of ~30 words should contain 2–3 sentences, not one long one

TRANSITION WORDS:
- Include at least one transition word every 3–4 sentences
- Distribute transitions naturally across all sections — never cluster them
- Preferred transitions (vary, do not repeat the same one):
  Additionally, Moreover, Furthermore, However, Therefore, Consequently,
  In addition, For example, As a result, This means, In contrast,
  Nevertheless, In particular, Notably, This makes, That said

SELF-CHECK BEFORE FINALISING (readability):
1. Scan for passive constructions — rewrite if active sounds equally natural
2. Scan for sentences >20 words — break them
3. Confirm transitions appear roughly every 3–4 sentences throughout

LINK LOGIC:
All buttons must point to: https://[domain]/apply-now-gb-cc-[card-name-slug]

BUTTON COLOR (CRITICAL):
Always use the site default button color (default_button_color from data/sites.json).
Never use the brand color of the card issuer (e.g., never use Santander red #ec0000
or HSBC red without explicit authorization). Brand color overrides are visual identity
changes and require explicit approval from Rodolfo (L2). Default = consistency.

TAGS (CRITICAL):
The tags array MUST include the following mandatory tags (always lowercase,
in this exact order first):
1. "rec" — the article type
2. "cc" — the vertical (credit card)
3. "gb" — the country code
4. The card name slug
5. "lang_en" — language tag (EN for this template; ES, DE, TR, etc. in other templates)
6. "atena_agent" — author tag (always added when Atena publishes the article)

After the 6 mandatory tags, add 2-4 additional SEO tags relevant to the card's
main benefits or category (e.g. "travel credit card", "airport lounge access",
"no annual fee", "cashback rewards").
Total: 8-10 tags per article.

## Subtitle Generation (MANDATORY)

Before writing the article body, generate a SUBTITLE at the very top.

Subtitle rules:
- **HARD LIMIT: MAX 100 characters** (spaces and punctuation count)
- This subtitle IS the excerpt — it is the first thing readers and Google see
- Count the EXACT length before publishing — never estimate
- MUST contain the exact focus keyphrase: {keyphrase}
- MUST highlight ONE specific feature or benefit of the card
  (e.g., no foreign fees, interest-free period, credit limit,
  travel insurance, cashback rate, annual fee, rewards points)
- Editorial tone (punchy, like a news subhead), NOT descriptive
- Third person, no "you should"
- British spelling for UK cards
- No ellipsis, no trailing "..."
- No <strong> or <em> (plain text)

Examples (for AIB Visa Gold Card):
✓ "AIB Visa Gold Card offers no foreign fees and bundled travel insurance."
✓ "AIB Visa Gold Card: 56 days interest-free credit with £10,000 limit."
✓ "AIB Visa Gold Card rewards premium UK travellers with zero foreign fees."
✗ "AIB Visa Gold Card is a premium credit product aimed at UK customers." (generic, no benefit)
✗ "The AIB Visa Gold Card targets middle-tier consumers." (descriptive, no benefit)

Output format:
<!-- wp:paragraph -->
<p>{subtitle text, no <strong> tags}</p>
<!-- /wp:paragraph -->

This <p> is the FIRST element of the post content (before LazyBlock credit-card).

STRUCTURE (STRICT ORDER):
1. TITLE
2. FIRST PARAGRAPH
3. INTRODUCTION
4. H2 — Key Benefits of the Card
5. H2 — How Does It Work
6. H2 — Comparative Table
7. POSITIONING BLOCK
8. H2 — Who Is This Card Best For

NOTE: Card blocks (LazyBlocks) and CTA buttons are inserted automatically
by the publishing system. Do NOT include any markers or placeholders for them.

IMAGE EXECUTION MODE (CRITICAL)
You must execute tasks in SEQUENCE:
1. Write the full article first
2. Generate/select the card image
3. Generate the featured image using the SAME card
Do NOT mix these steps.

1) CARD IMAGE:
Find a real, accurate image of the credit card.
Rules:
- Must match correct bank and network
- Must be clean, high resolution
- Must show the full card (no hands, no scene)

Processing:
- Remove background completely (transparent PNG)
- Crop EXACTLY to the card edges (no margins)
- Keep horizontal orientation ALWAYS. If the selected card image is vertical,
  rotate it before upload so the card itself is landscape/horizontal.
- Keep the card flat (no distortion)

STRICT:
- Do NOT recreate the card
- Do NOT modify colors, logo, or layout

IMPORTANT: This image is the SINGLE SOURCE OF TRUTH.
It MUST be reused in the featured image.

2) FEATURED IMAGE (CRITICAL):
CRITICAL PIPELINE RULE: You MUST use the EXACT SAME card image from step 1.
You are NOT allowed to generate or recreate a card. This is a COMPOSITION task.

PROCESS:
- Take the existing card image
- Insert it into a realistic scene with ONE person

COMPOSITION:
- Format: horizontal 16:9 (1920x1080)
- Create contextual/lifestyle hero art, not a card-only mockup
- Use ONLY three essential elements/layers:
  1. Realistic premium background or real-use scene
  2. The same validated horizontal card integrated naturally in context
  3. ONE realistic person or real-use element near the card
- The card must be visible and readable, but must NOT become a huge isolated card
  floating on a generic background
- No frames, molduras, posters, panels, duplicate cards, badges, UI overlays,
  phones, decorative objects, redesigned cards or extra composition elements
- Premium background with cinematic bokeh

CARD RULES:
- Must be IDENTICAL to the card image from step 1
- Same colors, layout, proportions
- No distortion, no redesign

STYLE:
- Ultra-realistic, professional commercial photography look (full-frame camera)
- Cinematic key light + soft fill light + subtle rim light
- Realistic reflections on the card
- Soft, natural shadows
- Premium campaign color grading

ENVIRONMENTS (vary between generations):
Modern financial district / Upscale café / Luxury hotel lounge / Premium office
/ Elegant home interior / Rooftop with skyline / Airport lounge / Contemporary
coworking / Urban street with cinematic blur / City at sunset / Nighttime metropolis

NEGATIVE (NEVER):
- Multiple people
- Person touching/holding the card
- Picture frame, border frame, mockup frame or decorative panel
- Duplicate card, extra card, phone screen, badge, sticker or UI overlay
- Altered card design
- Distorted anatomy, extra fingers
- Fake smile, artificial skin
- Cartoon, illustration, CGI, 3D render
- Stock photo look
- Flat lighting

VALIDATION: If the card is not identical → REGENERATE

CARD INTEGRITY RULE:
The card must always be treated as ONE object.
Do NOT: extract logo, isolate elements, recreate from memory.
If broken → regenerate

OUTPUT FORMAT:
HTML ONLY

---

## SEO FIELDS

These fields are published to Yoast SEO. Write them AFTER the article body is final.
The pipeline reads them from the template output and publishes via API.

### SEO Title (`_yoast_wpseo_title`)
- Format: `{Card Name}: {benefit phrase}`
- HARD LIMIT: ≤60 characters including spaces and punctuation
- MUST contain the focus keyphrase (card name)
- Use a real card benefit — not a generic phrase
- NEVER use the word "Review"
- NEVER include the site name
- Count the EXACT character length before finalising — never estimate
- Aim for 128 chars to leave 2-char safety margin below 130 hard limit

Examples:
✓ `"HSBC Premier: No Fee & Lounge Access"` (38 chars)
✓ `"AIB Visa Gold: No Foreign Fees, Travel Cover"` (45 chars)
✗ `"HSBC Premier Credit Card Review"` (contains "Review")
✗ `"HSBC Premier Credit Card | Eggbev"` (contains site name)

### Meta Description (`_yoast_wpseo_metadesc`)
- LIMIT: 120-130 characters including spaces and punctuation (sweet spot 128)
- MUST contain the exact card name
- MUST mention 2 real benefits of the card (no invented data)
- Tone: direct, factual, no clickbait, no "click here"
- British spelling for UK cards
- Always end with a clean sentence-ending punctuation mark: period (`.`) preferred, ellipsis (`...`) acceptable only when unavoidable
- Never output broken combined punctuation such as `.,...`, `,...`, `..`, `... .`, or lowercase sentence starts after a period
- No ellipsis, no trailing "..." unless a strict character trim genuinely requires it
- Count the EXACT character length before finalising — never estimate

Examples:
✓ `"HSBC Premier Credit Card earns 20,000 bonus points and offers Priority Pass lounge access with no annual fee."` (109 chars)
✗ `"The best credit card for UK travellers — apply now!"` (no card name, clickbait)
✗ `"HSBC Premier Credit Card is a great option with many benefits for customers."` (vague, no real benefits)

### Focus Keyphrase (`_yoast_wpseo_focuskw`)
- Exact card name, no changes (e.g. `"HSBC Premier Credit Card"`)


```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/templates/p1-gb-cc-en.md`

```text
FINAL PROMPT — P1 (GB / CC / EN)

WORD COUNT (CRITICAL — HARD LIMIT)

The FINAL PUBLISHED ARTICLE BODY must contain between 900 and 1000 visible words.

STRICT HARD LIMITS:
Minimum: 900 words
Maximum: 1000 words
Under 900 = FAIL
Over 1000 = FAIL

WORD COUNT RULE:
Count ALL visible words including: subtitle / first paragraph, image caption if visible, body paragraphs, H2 headings, table content if used, and visible explanatory copy.
Do NOT count: LazyBlock card blocks, CTA buttons, spaces, punctuation, HTML tags, formatting characters, comments, JSON blocks, hidden metadata, or Yoast fields.

CRITICAL:
The validation must be done on the FINAL assembled article body.
Do NOT validate intermediate drafts.
Do NOT publish if final body is outside 900-1000 words.

MANDATORY SELF-CHECK BEFORE PUBLISHING:
1. Assemble the full final article body
2. Count visible words only
3. If under 900, expand the article
4. If over 1000, reduce the article
5. Recount
6. Publish ONLY when final body is between 900 and 1000 words

CONTEXT:
You are a professional content writer specialised in SEO, recommendation, and conversion-focused financial content for credit cards in the United Kingdom (GB).
You must generate a P1 (Application Page), designed for middle/bottom-of-funnel users who already need more confidence before clicking through to the official issuer website.

OBJECTIVE:
Create content that:
- Expands the user's understanding of the credit card
- Explains how the card works in real-life usage
- Complements the REC without copying it
- Reduces uncertainty before the user leaves the site
- Drives users directly to the official credit card page
- Maintains legal, SEO, UX, and monetisation standards

INPUT DATA (ALWAYS CONSIDER):
- Card Name (exact name)
- Official URL (only source of truth and final CTA destination)
- Domain URL
- Country: GB
- Vertical: CC
- Language: EN
- Existing REC data when available
- Existing REC card image when available
- Official costs, APR, eligibility, benefits, and key conditions when stated

P1 FEATURED IMAGE RULE (CRITICAL):
The P1 featured image and the contextual image inserted near the top of the article must be the same image. It must look like a professional advertising scene built in literal layers, never like only a card pasted onto a background.

Mandatory layer order:
1. Background/base layer: a realistic, fully filled contextual scene with depth. The environment may be an office, airport, café, travel setting, corporate/lifestyle scene, shopping context, or another concept that matches the card. It must not look like a simple blurred backdrop.
2. Main element layer: the exact card artwork, centred, slightly enlarged, naturally integrated into the scene, fully inside the safe area, with no cropped edges and no overflow at the sides, top, or bottom.
3. Front layer: a realistic person in the foreground with a soft, natural overlap over the card, humanising the composition without hiding important card information.

Card integrity rules for the P1 image:
- Never add borders, frames, moulding, stickers, badges, external effects, or graphic elements around the card.
- Keep the original card shape clean and unchanged.
- Improve sharpness, resolution, alignment, orientation, and quality when needed.
- If the source card is vertical, rotate/adapt it to horizontal only when required by the established card standard.
- Never invent, reconstruct, redraw, recolour, or recreate card details. The visual identity must remain exactly the same as the original card image used in the article.

Visual quality requirements:
- The final image must have strong depth, excellent realism, excellent resolution, cinematic commercial lighting, natural shadows, sharp main elements, and premium finishing.
- The card must remain fully inside the image safe area and never extend beyond the bottom edge.

CRITICAL SOURCE RULES:
- Only use information confirmed by the official issuer page or official issuer documents.
- Never invent benefits, eligibility requirements, fees, rates, rewards, limits, or approval odds.
- Never assume missing data.
- If something is not confirmed, do not include it.
- If a key detail is not available on the official source, write around it rather than fabricating it.
- Do not copy the REC text. Reuse facts, not wording.

WRITING RULES:
- Use British English.
- Never use emojis.
- Avoid exaggerated promotional language.
- Do not promise approval.
- Do not say the card is "guaranteed", "best", "perfect", or "risk-free" unless the official source explicitly supports the claim, which is unlikely.
- Keep the tone clear, natural, helpful, and scannable.
- Maximum 4 paragraphs per H2 section.
- Each paragraph should be no more than ~35 words.
- Prefer 2-3 short sentences per paragraph.
- Always leave one blank line between paragraphs.

READABILITY REQUIREMENTS (YOAST-ORIENTED):

ACTIVE VOICE:
- Prefer active voice whenever it sounds natural.
- Passive voice is acceptable in normal financial constructions, such as "interest is charged" or "cashback is credited".
- Avoid passive voice when active voice is equally clear.

SENTENCE LENGTH:
- At least 80% of sentences must be under 20 words.
- No more than 20% of sentences may exceed 20 words.
- Break long sentences at natural clause boundaries.
- Do not rely on comma chains.

TRANSITION WORDS:
- Include transition words naturally throughout the article.
- Use at least one transition every 3-4 sentences.
- Vary transitions. Examples: However, Therefore, Additionally, In addition, For example, This means, As a result, That said, Notably, In particular, Consequently.

CONTENT POSITIONING:
REC = recommendation / initial discovery.
P1 = application support / decision confidence.

Allowed in P1:
- Reuse factual information from the REC
- Reinforce the same official benefits
- Explain practical usage in more detail
- Clarify costs, requirements, and next steps

Not allowed in P1:
- Copy REC text
- Repeat the same section structure as REC
- Be superficial
- Add unsupported claims
- Create urgency or pressure to apply

LINK LOGIC (CRITICAL):
All P1 buttons must point directly to the official credit card URL provided in the input data.

Rules:
- Button URL = Official URL
- Always use the Official URL as the only destination
- Never generate internal apply URLs for P1 buttons
- Never create custom redirect pages from the template
- Never use https://[domain]/apply-now-gb-cc-[card-name] as the P1 button destination

Correct behaviour:
Official URL:
https://www.bankname.com/credit-cards/example-card

Button URL:
https://www.bankname.com/credit-cards/example-card

BUTTON / SITEOUT LOGIC FOR P1:
When the card LazyBlock or final CTA is used in P1, the fields must be:
- Button text: APPLY NOW
- Button link: Official URL
- Small text / siteout: You will be redirected.

CARD LAZYBLOCK RULE:
Use the same card LazyBlock structure used by REC, but change only the P1-specific conversion fields:
- Button text becomes APPLY NOW
- Button URL becomes the official issuer URL
- Siteout text becomes You will be redirected.

The card image inside the LazyBlock may reuse the same isolated card image already used in the REC.

BUTTON COLOR:
Always use the site default button colour from the site configuration.
Never infer or use the issuer brand colour unless Rodolfo or Raquel explicitly requests an override.

TAGS (CRITICAL):
The tags array MUST include the following mandatory tags, always lowercase, in this exact order first:
1. "p1" — the article type
2. "cc" — the vertical (credit card)
3. "gb" — the country code
4. Card name as human-readable words, NOT a hyphenated slug
5. "lang_en" — language tag
6. "atena_agent" — author / automation audit tag

After the 6 mandatory tags, add 2-4 additional SEO tags relevant to the card's main benefits or category.
Examples:
- "travel credit card"
- "cashback rewards"
- "balance transfer"
- "no annual fee"
- "purchase credit card"
- "airport lounge access"

Total: 8-10 tags per P1 article.

TAG FORMATTING RULE:
Tag names must use spaces, not hyphens.
Correct: "travel credit card"
Incorrect: "travel-credit-card"

SUBTITLE GENERATION (MANDATORY):
Before writing the article body, generate a SUBTITLE at the very top.

IMPORTANT:
In P1, the subtitle is also the first sentence / first paragraph of the article.
This MUST be the first visible element of the post content.

Subtitle rules:
- Maximum 100 characters, including spaces and punctuation
- Must contain the exact focus keyphrase / card name
- Must highlight one specific confirmed feature or benefit
- Must use third person
- Must use British spelling
- No ellipsis
- No emojis
- No promotional pressure
- No unsupported claim

Good examples:
"Lloyds Ultra Credit Card offers cashback and simple account management."
"HSBC Premier Credit Card includes lounge access with no annual fee."

Bad examples:
"This credit card is designed for UK users."
"Apply now and get benefits today."
"The best card for everyone."

STRUCTURE (STRICT ORDER):

1. TITLE
2. SUBTITLE / FIRST PARAGRAPH
3. CONTEXTUAL FEATURED IMAGE INSIDE THE ARTICLE
4. INTRODUCTORY PARAGRAPHS (without an "Introduction" H2)
5. CARD LAZYBLOCK (same model as REC, with P1 button/siteout changes)
6. H2 — Main Benefits
7. H2 — How Does It Work
8. H2 — Costs, Fees and Key Conditions
9. H2 — [Exclusive feature or benefit highlighted by the card]
10. H2 — Requirements to Qualify for the Card
11. H2 — How to Maximise the Benefits
12. H2 — How to Apply
13. H2 — Is This Card Right for You?
14. FINAL CARD LAZYBLOCK (same card as item 5)

INTRODUCTION RULE:
Do not add a heading named "Introduction".
After the subtitle and in-article contextual image, include only introductory paragraphs before the first card LazyBlock.

H2 CUSTOM BENEFIT RULE:
The H2 at position 9 must be based on a real, confirmed feature or benefit of the card.
Examples:
- H2 — Cashback
- H2 — Balance Transfer Offer
- H2 — Avios and Travel Rewards
- H2 — Airport Lounge Access
- H2 — Purchase Protection

If there is no clearly distinctive benefit confirmed by the official source, use a conservative H2 based on the strongest confirmed value proposition.
Do not invent an exclusive feature.

REQUIREMENTS SECTION RULE:
The H2 "Requirements to Qualify for the Card" must only include requirements confirmed by the official issuer.
If specific eligibility rules are not published, use cautious wording such as:
"The issuer may assess factors such as credit history, income, affordability, and existing borrowing before making a decision."
Do not invent minimum income, score bands, residency rules, or approval odds.

HOW TO APPLY SECTION RULE:
Explain the application flow in simple terms.
The user must understand that clicking the button will redirect them to the official issuer website.
Do not say the application happens on the MGS site.
Do not imply that eggbev or MGS approves applications.

IMAGE EXECUTION MODE (CRITICAL):
Execute image tasks in sequence:
1. Write and validate the full article body
2. Resolve or reuse the isolated card image for the card LazyBlocks
3. Generate or select the P1 contextual featured image
4. Insert the same P1 contextual featured image after the first paragraph
5. Set that same P1 contextual image as the WordPress featured image

CARD IMAGE RULE:
The LazyBlock card image must contain only the isolated card image.

Rules:
- No background
- No people
- No objects
- No decorative scene
- No extra graphics
- Prefer transparent PNG when available
- Must preserve the real card design
- Must be horizontal / landscape
- May reuse the same card image used in the REC

P1 FEATURED IMAGE RULE (CRITICAL):
The P1 featured image must be different from the REC featured image.

Rules:
- The WordPress featured image for P1 must be a contextual image with the card, a realistic scenario, and a person or real-use element.
- The image inserted after the first paragraph in the P1 article must be the SAME image as the P1 WordPress featured image.
- The P1 featured image must NOT be exactly the same as the REC featured image.
- The P1 featured image must NOT be only the isolated card.
- The P1 featured image must preserve the exact card design.
- The image should feel premium, realistic, and conversion-oriented.
- Use a different scene, composition, or environment from the REC featured image.

P1 IMAGE RELATIONSHIP SUMMARY:
- REC card image may be reused as P1 LazyBlock card image.
- REC featured image must not be reused as P1 featured image.
- P1 featured image must also appear after the first paragraph inside the P1 content.

CARD INTEGRITY RULE:
All generated or selected images must preserve the card identity.
Do not alter issuer name, network mark, colour layout, product name, sample card placement, or visual design.
If the card is changed or hallucinated, the image fails.

NAME USAGE RULE:
Use the exact card name naturally.
Maximum 8 mentions of the full card name in the visible body.
Use natural variations when possible, such as "this card", "the card", or "the product".
Do not over-optimise.

OUTPUT FORMAT:
HTML ONLY for the article body.
Do not output Markdown in the article body.
Do not include internal notes, placeholders, or publishing instructions in the final article body.
Card blocks and CTA blocks are inserted automatically by the publishing system.

SEO FIELDS:
Write SEO fields only after the article body is final.
The pipeline may publish these fields via API.

POST TITLE:
- Maximum 60 characters including spaces and punctuation
- Must contain the exact focus keyphrase / card name when possible
- Use a real confirmed benefit or positioning angle
- Never use "Review"
- Never include the site name
- Count exact characters before publishing

YOAST SEO TITLE (_yoast_wpseo_title):
Leave empty by default, following the REC publishing ideology.
The site-level Yoast template should handle the SEO title unless a future P1-specific decision overrides this rule.

META DESCRIPTION (_yoast_wpseo_metadesc):
- Maximum 130 characters including spaces and punctuation
- Preferred range: 120-130 characters
- Must contain the exact card name
- Must mention 1-2 real confirmed benefits or practical reasons to consider the card
- No clickbait
- No ellipsis
- British spelling
- Count exact characters before publishing

FOCUS KEYPHRASE (_yoast_wpseo_focuskw):
Use the exact card name, with no changes.

COMPLIANCE RULES:
- Do not promise approval.
- Do not imply that applying is risk-free.
- Do not provide financial advice.
- Do not encourage borrowing beyond the user's means.
- Mention representative APR, annual fees, or key costs when officially stated.
- Make clear that applications and final decisions are handled by the issuer.
- If the user will leave the site, the CTA microcopy must say: You will be redirected.

FINAL PRE-PUBLISH CHECKLIST:
1. Final body has 900-1000 visible words
2. Subtitle is first visible element and has 100 characters or fewer
3. Title has 60 characters or fewer
4. Meta description has 130 characters or fewer
5. Focus keyphrase is the exact card name
6. Tags include p1, cc, gb, card name words, lang_en, atena_agent
7. Tags use spaces, not hyphens
8. P1 card LazyBlocks point to the official issuer URL
9. P1 button text is APPLY NOW
10. P1 siteout text is You will be redirected.
11. P1 featured image is different from the REC featured image
12. P1 featured image is also inserted after the first paragraph
13. LazyBlock card image may reuse the REC isolated card image
14. No unsupported claim was added
15. No REC text was copied

```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/scripts/render-p1-summary.py`

```text
#!/usr/bin/env python3
"""Compatibility wrapper for Rodolfo-approved P1 summary rendering."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "render-article-summary.py"

if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, str(SCRIPT), "--type", "p1", *sys.argv[1:]]))

```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/scripts/search-card-image.sh`

```text
#!/bin/bash
set -euo pipefail

CARD_NAME="${1:?usage: search-card-image.sh <card_name> <card_official_url>}"
OFFICIAL_URL="${2:?missing card_official_url}"
LOG="/root/mgs-agent/logs/generate-rec.log"

slug=$(echo "$CARD_NAME" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g')

# Dimension filter thresholds (env-overridable for calibration)
CARD_MIN_WIDTH="${CARD_MIN_WIDTH:-200}"
CARD_MIN_HEIGHT="${CARD_MIN_HEIGHT:-100}"
CARD_ASPECT_MIN="${CARD_ASPECT_MIN:-1.2}"
CARD_ASPECT_MAX="${CARD_ASPECT_MAX:-2.2}"

# Temp file tracking for unified cleanup
TEMP_FILES=()
cleanup_temps() {
  local f
  for f in "${TEMP_FILES[@]}"; do
    [ -n "$f" ] || continue
    rm -f "$f"
  done
}
trap 'cleanup_temps' EXIT

emit_needs_manual() {
  local reason="$1"
  echo "[$(date -Iseconds)] search-card-image NEEDS-MANUAL card=$CARD_NAME url=$OFFICIAL_URL reason=$reason" >>"$LOG"
  jq -n --arg r "$reason" --arg c "$CARD_NAME" --arg u "$OFFICIAL_URL" \
    '{path:null, mime:null, tier:0, source:null, status:"NEEDS_MANUAL", reason:$r, card_name:$c, url:$u}'
  exit 1
}

normalize_card_image() {
  local img_path="$1"
  [ -f "$img_path" ] || return 1
  python3 - "$img_path" <<'PY' >>"$LOG" 2>&1 || return 1
from PIL import Image
import sys

path = sys.argv[1]
img = Image.open(path)
img.load()

rotated = False
# MGS LazyBlock card image rule: the card slot must always receive horizontal
# card artwork. Some issuers publish vertical card art (for example Amazon
# Barclaycard); rotate that official card-only artwork 90 degrees without
# resizing or stretching. This applies only to the card image itself, never to
# the featured image composition.
if img.height > img.width:
    img = img.rotate(90, expand=True)
    rotated = True

rgba = img.convert('RGBA')
pix = rgba.load()
w, h = rgba.size
left, right, top, bottom = w, -1, h, -1

for y in range(h):
    for x in range(w):
        r, g, b, a = pix[x, y]
        # Treat transparent and near-white border/padding as background.
        if a > 20 and not (r > 242 and g > 242 and b > 242):
            left = min(left, x)
            right = max(right, x)
            top = min(top, y)
            bottom = max(bottom, y)

cropped = False
if right >= left and bottom >= top:
    pad = 3
    box = (max(0, left-pad), max(0, top-pad), min(w, right+pad+1), min(h, bottom+pad+1))
    if box != (0, 0, w, h):
        img = img.crop(box)
        cropped = True

if img.mode not in ('RGB', 'RGBA'):
    img = img.convert('RGBA')
img.save(path)
print(f"search-card-image NORMALIZE path={path} rotated={rotated} cropped={cropped} size={img.width}x{img.height}")
PY
}

get_brave_api_key() {
  # Prefer explicit env var so cron/systemd can inject it without 1Password.
  if [ -n "${BRAVE_SEARCH_API_KEY=[REDACTED]}" ]; then
    printf '%s' "$BRAVE_SEARCH_API_KEY"
    return 0
  fi

  # MGS production default: key lives in 1Password. Source .env only for OP token;
  # never print the returned secret. Field label in 1P is "api key".
  if command -v op >/dev/null 2>&1; then
    if [ -f /root/mgs-agent/.env ]; then
      set +u
      set -a
      # shellcheck disable=SC1091
      source /root/mgs-agent/.env >/dev/null 2>&1 || true
      set +a
      set -u
    fi
    op item get "Brave Search API - MGS" \
      --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" \
      --fields "api key" \
      --reveal 2>/dev/null || true
  fi
}

download_and_validate_candidate() {
  local cand_url="$1"
  local cand_ext="$2"
  local cand_tmp="$3"
  local origin="$4"

  if ! curl -sS -L -A "Mozilla/5.0" -o "$cand_tmp" "$cand_url" 2>/dev/null; then
    echo "[$(date -Iseconds)] search-card-image REJECT download_failed origin=$origin url=$cand_url" >>"$LOG"
    return 1
  fi
  [ -s "$cand_tmp" ] || { echo "[$(date -Iseconds)] search-card-image REJECT download_empty origin=$origin url=$cand_url" >>"$LOG"; return 1; }

  if ! command -v identify >/dev/null 2>&1; then
    echo "[$(date -Iseconds)] search-card-image WARN identify_unavailable accepting_without_dim_check origin=$origin url=$cand_url" >>"$LOG"
    return 0
  fi

  dims=$(identify -format '%w %h' "$cand_tmp" 2>/dev/null || echo "")
  if [ -z "$dims" ]; then
    echo "[$(date -Iseconds)] search-card-image REJECT identify_failed origin=$origin url=$cand_url" >>"$LOG"
    return 1
  fi
  w=$(echo "$dims" | awk '{print $1}')
  h=$(echo "$dims" | awk '{print $2}')

  if [ "$w" -lt "$CARD_MIN_WIDTH" ] || [ "$h" -lt "$CARD_MIN_HEIGHT" ]; then
    echo "[$(date -Iseconds)] search-card-image REJECT too_small origin=$origin w=${w} h=${h} (min ${CARD_MIN_WIDTH}x${CARD_MIN_HEIGHT}) url=$cand_url" >>"$LOG"
    return 1
  fi

  aspect=$(awk -v w="$w" -v h="$h" 'BEGIN{ printf "%.3f", w/h }')
  in_range=$(awk -v a="$aspect" -v lo="$CARD_ASPECT_MIN" -v hi="$CARD_ASPECT_MAX" 'BEGIN{ print (a>=lo && a<=hi) ? "1" : "0" }')
  if [ "$in_range" != "1" ]; then
    cand_low=$(echo "$cand_url" | tr '[:upper:]' '[:lower:]')
    is_portrait_card=$(awk -v a="$aspect" 'BEGIN{ print (a>=0.55 && a<=0.85) ? "1" : "0" }')
    if [ "$is_portrait_card" = "1" ] && echo "$cand_low" | grep -qE '(card-images|card).*card' && ! echo "$cand_low" | grep -qE '(phone|mobile|app|screen|screenshot|at-a-glance|rewards-work|hero|banner|background)'; then
      echo "[$(date -Iseconds)] search-card-image ACCEPT portrait_card_only_rotate_to_horizontal origin=$origin w=${w} h=${h} aspect=${aspect} url=$cand_url" >>"$LOG"
      return 0
    fi
    echo "[$(date -Iseconds)] search-card-image REJECT aspect_out_of_range origin=$origin w=${w} h=${h} aspect=${aspect} (expected ${CARD_ASPECT_MIN}-${CARD_ASPECT_MAX}) url=$cand_url" >>"$LOG"
    return 1
  fi

  echo "[$(date -Iseconds)] search-card-image ACCEPT origin=$origin w=${w} h=${h} aspect=${aspect} url=$cand_url" >>"$LOG"
  return 0
}

run_brave_fallback() {
  # ── Tentativa 2: Brave Images API (sem browser) ────────────────────────
  echo "[$(date -Iseconds)] search-card-image FALLBACK brave_images card=$CARD_NAME" >>"$LOG"

  local brave_key brave_json brave_urls cand_url cand_ext cand_tmp
  brave_key="$(get_brave_api_key | tr -d '\r\n')"
  if [ -z "$brave_key" ]; then
    echo "[$(date -Iseconds)] search-card-image BRAVE_SKIP no_api_key" >>"$LOG"
    return 1
  fi

  brave_json=$(python3 - "$CARD_NAME" "$brave_key" "$OFFICIAL_URL" <<'PY' 2>>"$LOG" || true
import json, re, sys, urllib.parse, urllib.request

card_name, key, official_url = sys.argv[1], sys.argv[2], sys.argv[3]
query = f'{card_name} credit card image'
official_host = (urllib.parse.urlparse(official_url).hostname or '').lower()
brand = re.sub(r'[^a-z0-9]+', ' ', card_name.lower()).split()[0] if card_name else ''
terms = [t for t in re.sub(r'[^a-z0-9]+', ' ', card_name.lower()).split() if t not in {'card', 'credit'}]
exact_phrase = re.sub(r'[^a-z0-9]+', ' ', card_name.lower()).strip()
priority_hosts = {
    'finder.com': 35,
    'finder.com/uk': 35,
    'nerdwallet.com': 25,
    'moneysavingexpert.com': 25,
    'headforpoints.com': 25,
    'backtodefault.com': 25,
    'which.co.uk': 20,
}
hard_noise_hosts = ('play.google.com', 'youtube.com', 'youtu.be', 'facebook.com', 'ytimg.com')
noise_re = re.compile(
    r'(app|mobile|phone|screenshot|screen|google\s*play|play\s*store|youtube|ytimg|facebook|'
    r'hand|hands|person|people|woman|man|avatar|trustpilot|alien|loan|balance\s*transfer|'
    r'virtual\s*card|virtual-assistant|decline|call-us|support|apple\s*pay|google\s*pay|what-is-cc-balance|card-hand|hero|banner|background|illustration|landing)'
)
clean_card_re = re.compile(r'(credit\s*card\s*review|card\s*review|mastercard|contactless|front|card[-_ ].*\.(png|jpg|jpeg|webp))')
url = 'https://api.search.brave.com/res/v1/images/search?' + urllib.parse.urlencode({
    'q': query,
    'count': 20,
    'country': 'GB',
    'search_lang': 'en',
    'safesearch': 'strict',
})
req = urllib.request.Request(url, headers={
    'Accept': 'application/json',
    'X-Subscription-Token': key,
    'User-Agent': 'Hermes-Agent MGS card-image-search',
})
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode('utf-8', 'ignore'))
except Exception as exc:
    print(json.dumps({'status': 'ERROR', 'error': str(exc)}))
    raise SystemExit(0)

out = []
for pos, item in enumerate(data.get('results', []), 1):
    props = item.get('properties') or {}
    thumb = item.get('thumbnail') or {}
    src = props.get('url') or item.get('image') or thumb.get('src')
    page = item.get('url') or ''
    title = item.get('title') or ''
    if not src:
        continue
    src_host = (urllib.parse.urlparse(src).hostname or '').lower()
    page_host = (urllib.parse.urlparse(page).hostname or '').lower()
    hay = f'{title} {page} {src}'.lower()
    score = 100 - pos  # keep Brave order as tie-breaker
    if official_host and (official_host in src_host or official_host in page_host):
        score += 25
    elif brand and (src_host.startswith(brand) or page_host.startswith(brand) or f'.{brand}' in src_host or f'.{brand}' in page_host):
        score += 20
    for host, boost in priority_hosts.items():
        if host in page_host or host in src_host or host in hay:
            score += boost
            break
    term_hits = sum(1 for t in terms if t in hay)
    score += term_hits * 8
    if exact_phrase and exact_phrase in hay:
        score += 28
    if clean_card_re.search(hay):
        score += 24
    if re.search(r'(mastercard|contactless|chip|front|card-front)', hay):
        score += 12
    # A clean isolated card image is preferable to a technically valid promotional banner.
    # Review/comparison pages often host the isolated card artwork when issuers don't expose it.
    if re.search(r'(review|reviews)', hay) and brand and brand in hay:
        score += 12
    if re.search(r'(illustration|hero|banner|background|what-is-cc-balance|card-hand|hand|hands|phone|app|screenshot)', hay):
        score -= 18
    # LazyBlock card image should be product/card artwork, not a contextual scene.
    # Official issuer pages often rank payment/app lifestyle photos very high;
    # these are valid marketing assets but bad card images. Force them below the
    # acceptance threshold unless there is an explicit isolated-card signal.
    isolated_signal = re.search(r'(card[-_ ]?front|front[-_ ]?card|product|niche-builder|card[-_][a-z0-9_-]{0,80}\.(png|jpg|jpeg|webp))', hay)
    contextual_noise = re.search(r'(person|people|woman|man|hand|hands|phone|mobile|app|screenshot|screen|virtual-assistant|decline|call-us|support|apple\s*pay|google\s*pay)', hay)
    if contextual_noise and not isolated_signal:
        score = -999
    elif noise_re.search(hay) and not isolated_signal:
        score -= 90
    if 'business' in hay and 'business' not in card_name.lower():
        score -= 25
    if official_host.endswith('.co.uk') and (page_host.endswith('.ca') or src_host.endswith('.ca') or '.com.au' in page_host or '.com.au' in src_host):
        score -= 90
    if official_host.endswith('.co.uk') and brand == 'mbna' and ('mbna.ca' in page_host or 'mbna.ca' in src_host):
        score = -999
    if any(h in page_host or h in src_host for h in hard_noise_hosts):
        score -= 60
    if noise_re.search(hay):
        score -= 35
    if re.search(r'(logo|icon|sprite|favicon)', hay):
        score -= 25
    if re.search(r'(walletwisdoms|memivi)', hay):
        score -= 10
    out.append({'src': src, 'page': page, 'title': title, 'score': score})
out.sort(key=lambda x: x.get('score', 0), reverse=True)
print(json.dumps({'status': 'OK', 'results': out}, ensure_ascii=False))
PY
)

  brave_status=$(echo "$brave_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null || echo "")
  if [ "$brave_status" != "OK" ]; then
    echo "[$(date -Iseconds)] search-card-image BRAVE_ERROR status=${brave_status:-invalid_response}" >>"$LOG"
    return 1
  fi

  brave_urls=$(BRAVE_JSON="$brave_json" python3 - <<'PY'
import json, os
try:
    data = json.loads(os.environ.get('BRAVE_JSON', '{}'))
except Exception:
    raise SystemExit(0)
for r in data.get('results', []):
    src = r.get('src') or ''
    if src.startswith('http'):
        title = (r.get('title') or '').replace('\t', ' ')[:180]
        page = (r.get('page') or '').replace('\t', ' ')[:220]
        print(f"{int(r.get('score', 0))}\t{src}\t{title}\t{page}")
PY
)
  if [ -z "$brave_urls" ]; then
    echo "[$(date -Iseconds)] search-card-image BRAVE_NO_IMAGE_URLS" >>"$LOG"
    return 1
  fi

  while IFS=$'\t' read -r cand_score cand_url cand_title cand_page; do
    [ -z "$cand_url" ] && continue
    if [ "${cand_score:-0}" -lt 110 ]; then
      echo "[$(date -Iseconds)] search-card-image BRAVE_SKIP_LOW_SCORE score=${cand_score:-0} title=${cand_title:-} page=${cand_page:-} src=$cand_url" >>"$LOG"
      continue
    fi
    cand_ext="${cand_url##*.}"; cand_ext="${cand_ext%%\?*}"
    cand_ext=$(echo "$cand_ext" | tr '[:upper:]' '[:lower:]')
    case "$cand_ext" in png|jpg|jpeg|webp) ;; *) cand_ext="jpg" ;; esac
    cand_tmp="/tmp/card-candidate-brave-$slug-$$-$RANDOM.$cand_ext"
    TEMP_FILES+=("$cand_tmp")
    echo "[$(date -Iseconds)] search-card-image BRAVE_TRY score=${cand_score:-0} title=${cand_title:-} page=${cand_page:-} src=$cand_url" >>"$LOG"
    if download_and_validate_candidate "$cand_url" "$cand_ext" "$cand_tmp" "brave"; then
      final_out="/tmp/card-$slug.$cand_ext"
      mv "$cand_tmp" "$final_out"
      normalize_card_image "$final_out" || true
      mime=$(file -b --mime-type "$final_out" 2>/dev/null || echo "image/$cand_ext")
      echo "[$(date -Iseconds)] search-card-image BRAVE_OK path=$final_out score=${cand_score:-0} src=$cand_url" >>"$LOG"
      jq -n --arg p "$final_out" --arg m "$mime" --arg s "$cand_url" \
        --argjson sc "${cand_score:-0}" --arg title "${cand_title:-}" --arg page "${cand_page:-}" \
        '{path:$p, mime:$m, tier:4, source:$s, status:"OK", provider:"brave_images", selection:{mode:"auto_ranked_card_image", score:$sc, title:$title, page:$page}}'
      exit 0
    fi
  done <<<"$brave_urls"

  echo "[$(date -Iseconds)] search-card-image BRAVE_NO_VALID_IMAGES" >>"$LOG"
  return 1
}

run_bing_fallback() {
  # ── Tentativa 3: Bing Images via Playwright local ──────────────────────
  if run_brave_fallback; then
    exit 0
  fi

  echo "[$(date -Iseconds)] search-card-image FALLBACK bing_playwright card=$CARD_NAME" >>"$LOG"
  BING_SCRIPT="$(dirname "$0")/search-card-image-bing.py"
  if [ -f "$BING_SCRIPT" ]; then
    bing_result=$(python3 "$BING_SCRIPT" "$CARD_NAME" 2>>"$LOG") || true
    bing_status=$(echo "$bing_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null || echo "")
    if [ "$bing_status" = "OK" ]; then
      bing_path=$(echo "$bing_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('path',''))"   2>/dev/null || echo "")
      bing_mime=$(echo "$bing_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('mime',''))"   2>/dev/null || echo "")
      bing_src=$(echo  "$bing_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('source',''))" 2>/dev/null || echo "")
      [ -n "$bing_path" ] && normalize_card_image "$bing_path" || true
      [ -n "$bing_path" ] && bing_mime=$(file -b --mime-type "$bing_path" 2>/dev/null || echo "$bing_mime")
      echo "[$(date -Iseconds)] search-card-image BING_OK path=$bing_path src=$bing_src" >>"$LOG"
      jq -n --arg p "$bing_path" --arg m "$bing_mime" --arg s "$bing_src" \
        '{path:$p, mime:$m, tier:4, source:$s, status:"OK"}'
      exit 0
    fi
  fi
  emit_needs_manual "all_sources_failed"
}

# ── Tentativa 1: Fetch official page ──────────────────────────────────────
# Captura HTTP status junto com o body para detecção rápida de geo-IP/bot block
http_out=$(curl -sS -L -A "Mozilla/5.0" -w "\nHTTP_STATUS:%{http_code}" "$OFFICIAL_URL" 2>/dev/null) || true
http_status=$(echo "$http_out" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
html=$(echo "$http_out" | sed '/HTTP_STATUS:[0-9]*/d')

# Detectar bloqueio:
# - HTTP 4xx/5xx
# - Cloudflare "Error 1007/1020" ou página de erro genérica no body
_blocked=0
if [ -n "$http_status" ] && [ "$http_status" -ge 400 ] 2>/dev/null; then
  _blocked=1
fi
if echo "$html" | grep -qiE '(error 10[0-9]{2}|access denied|cf-mitigated|cf-ray|enable javascript and cookies|sorry.{0,40}error occurred|we are sorry an error)'; then
  _blocked=1
fi

if [ "$_blocked" = "1" ] || [ -z "$html" ]; then
  echo "[$(date -Iseconds)] search-card-image GEO_BLOCK_OR_EMPTY status=${http_status:-?} skipping_to_bing card=$CARD_NAME url=$OFFICIAL_URL" >>"$LOG"
  run_bing_fallback
fi

# ── Scraping do site oficial ──────────────────────────────────────────────
base_host=$(echo "$OFFICIAL_URL" | sed -E 's#^(https?://[^/]+).*#\1#')
candidates=$(echo "$html" | grep -oE '(src|data-src|data-lazy-src)="[^"]+\.(png|jpe?g|webp)"' \
  | sed -E 's/^[^"]+\"([^"]+)\".*/\1/' \
  | sort -u || true)

abs_candidates=$(while IFS= read -r u; do
  [ -z "$u" ] && continue
  case "$u" in
    http*) echo "$u" ;;
    //*)   echo "https:$u" ;;
    /*)    echo "$base_host$u" ;;
    *)     echo "$base_host/$u" ;;
  esac
done <<<"$candidates")

if [ -z "$abs_candidates" ]; then
  echo "[$(date -Iseconds)] search-card-image no_image_tags_on_page skipping_to_bing card=$CARD_NAME" >>"$LOG"
  run_bing_fallback
fi

kw=$(echo "$slug" | tr '-' '|')
scored=$(while IFS= read -r u; do
  [ -z "$u" ] && continue
  score=0
  low=$(echo "$u" | tr '[:upper:]' '[:lower:]')
  low_path=$(echo "$low" | sed -E 's#^https?://[^/]+/?##')
  echo "$low_path" | grep -qE "($kw)" && score=$((score+5))
  for term in $(echo "$slug" | tr '-' ' '); do
    if [ "$term" != "card" ] && echo "$low_path" | grep -q "$term"; then
      score=$((score+6))
    fi
  done
  echo "$low_path" | grep -qE '(card|visa|mastercard|amex|gold|platinum|classic|credit)' && score=$((score+2))
  echo "$low_path" | grep -qE '(card-images/.+card|card-images/new|card-front|front)' && score=$((score+12))
  [[ "$low" == *.png ]] && score=$((score+3))
  [[ "$low" == *.webp ]] && score=$((score+1))
  echo "$low_path" | grep -qE '(logo|icon|sprite|favicon|hero|banner|couple|walking|shop|background|new-fscs|phone|mobile|app|screen|screenshot|at-a-glance|rewards-work)' && score=$((score-30))
  echo "$score $u"
done <<<"$abs_candidates" | sort -rn)

# Iterate scored candidates (score > 0) until one passes dimension + aspect filters
best=""
ext=""
out=""

while IFS= read -r line; do
  [ -z "$line" ] && continue
  cand_score=$(echo "$line" | awk '{print $1}')
  cand_url=$(echo "$line" | awk '{print $2}')
  [ "$cand_score" -le 0 ] && break   # scored list is sorted desc by score

  cand_ext="${cand_url##*.}"; cand_ext="${cand_ext%%\?*}"
  cand_ext=$(echo "$cand_ext" | tr '[:upper:]' '[:lower:]')
  case "$cand_ext" in png|jpg|jpeg|webp) ;; *) cand_ext="png" ;; esac
  cand_tmp="/tmp/card-candidate-$slug-$$-$RANDOM.$cand_ext"
  TEMP_FILES+=("$cand_tmp")

  if ! curl -sS -L -A "Mozilla/5.0" -o "$cand_tmp" "$cand_url" 2>/dev/null; then
    echo "[$(date -Iseconds)] search-card-image REJECT download_failed url=$cand_url" >>"$LOG"
    continue
  fi
  [ -s "$cand_tmp" ] || { echo "[$(date -Iseconds)] search-card-image REJECT download_empty url=$cand_url" >>"$LOG"; continue; }

  if ! command -v identify >/dev/null 2>&1; then
    echo "[$(date -Iseconds)] search-card-image WARN identify_unavailable accepting_without_dim_check url=$cand_url" >>"$LOG"
    best="$cand_url"; ext="$cand_ext"; out="$cand_tmp"
    break
  fi

  dims=$(identify -format '%w %h' "$cand_tmp" 2>/dev/null || echo "")
  if [ -z "$dims" ]; then
    echo "[$(date -Iseconds)] search-card-image REJECT identify_failed url=$cand_url" >>"$LOG"
    continue
  fi
  w=$(echo "$dims" | awk '{print $1}')
  h=$(echo "$dims" | awk '{print $2}')

  if [ "$w" -lt "$CARD_MIN_WIDTH" ] || [ "$h" -lt "$CARD_MIN_HEIGHT" ]; then
    echo "[$(date -Iseconds)] search-card-image REJECT too_small w=${w} h=${h} (min ${CARD_MIN_WIDTH}x${CARD_MIN_HEIGHT}) url=$cand_url" >>"$LOG"
    continue
  fi

  aspect=$(awk -v w="$w" -v h="$h" 'BEGIN{ printf "%.3f", w/h }')
  in_range=$(awk -v a="$aspect" -v lo="$CARD_ASPECT_MIN" -v hi="$CARD_ASPECT_MAX" 'BEGIN{ print (a>=lo && a<=hi) ? "1" : "0" }')
  if [ "$in_range" != "1" ]; then
    cand_low=$(echo "$cand_url" | tr '[:upper:]' '[:lower:]')
    is_portrait_card=$(awk -v a="$aspect" 'BEGIN{ print (a>=0.55 && a<=0.85) ? "1" : "0" }')
    if [ "$is_portrait_card" = "1" ] && echo "$cand_low" | grep -qE '(card-images|card).*card' && ! echo "$cand_low" | grep -qE '(phone|mobile|app|screen|screenshot|at-a-glance|rewards-work|hero|banner|background)'; then
      echo "[$(date -Iseconds)] search-card-image ACCEPT portrait_card_only_rotate_to_horizontal w=${w} h=${h} aspect=${aspect} score=${cand_score} url=$cand_url" >>"$LOG"
    else
      echo "[$(date -Iseconds)] search-card-image REJECT aspect_out_of_range w=${w} h=${h} aspect=${aspect} (expected ${CARD_ASPECT_MIN}-${CARD_ASPECT_MAX}) url=$cand_url" >>"$LOG"
      continue
    fi
  fi

  echo "[$(date -Iseconds)] search-card-image ACCEPT w=${w} h=${h} aspect=${aspect} score=${cand_score} url=$cand_url" >>"$LOG"
  best="$cand_url"; ext="$cand_ext"; out="$cand_tmp"
  break
done <<<"$scored"

# Se Tentativa 1 não encontrou nada → Bing fallback
if [ -z "$best" ]; then
  run_bing_fallback
fi

# Move accepted candidate to canonical output path
final_out="/tmp/card-$slug.$ext"
if [ "$out" != "$final_out" ]; then
  mv "$out" "$final_out"
  out="$final_out"
fi
normalize_card_image "$out" || true
mime=$(file -b --mime-type "$out" 2>/dev/null || echo "image/$ext")

# Classify tier:
#  1 = official + PNG with alpha
#  2 = official + PNG (no alpha / unknown)
#  3 = official + JPG/webp (has background)
#  4 = non-official source
best_host=$(echo "$best" | sed -E 's#^(https?://[^/]+).*#\1#')
is_official=0
[ "$best_host" = "$base_host" ] && is_official=1

if [ "$is_official" = "1" ]; then
  if [ "$ext" = "png" ]; then
    tier=2
    if command -v identify >/dev/null 2>&1; then
      alpha=$(identify -format '%[channels]' "$out" 2>/dev/null || echo "")
      [[ "$alpha" == *a* ]] && tier=1
    fi
  else
    tier=3
  fi
else
  tier=4
fi

if [ "$tier" -ge 3 ]; then
  echo "[$(date -Iseconds)] search-card-image WARN MANUAL REVIEW RECOMMENDED tier=$tier card=$CARD_NAME path=$out src=$best (image may have background or be off-brand)" >>"$LOG"
else
  echo "[$(date -Iseconds)] search-card-image OK tier=$tier card=$CARD_NAME path=$out src=$best" >>"$LOG"
fi

jq -n --arg p "$out" --arg m "$mime" --argjson t "$tier" --arg s "$best" \
  --arg st "OK" \
  '{path:$p, mime:$m, tier:$t, source:$s, status:$st}'

```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/scripts/generate-featured-image.sh`

```text
#!/bin/bash
set -euo pipefail

# Load env vars (OP_DEFAULT_VAULT, etc.) — runs under systemd/cron too
# shellcheck source=/dev/null
[ -f /root/mgs-agent/.env ] && set -a && . /root/mgs-agent/.env && set +a

SLUG="${1:?usage: generate-featured-image.sh <slug> <card_image_path>}"
CARD_IMG="${2:?missing card_image_path}"
LOG="/root/mgs-agent/logs/generate-rec.log"

TEMP_FILES=()
cleanup_temps() {
  local f
  for f in "${TEMP_FILES[@]}"; do
    [ -n "$f" ] || continue
    echo "[$(date -Iseconds)] generate-featured-image CLEANUP tmp=$f slug=$SLUG" >>"$LOG"
    rm -f "$f"
  done
}
trap 'cleanup_temps' EXIT

[ -f "$CARD_IMG" ] || { echo "ERROR: card image not found: $CARD_IMG" >&2; exit 1; }

api_key=[REDACTED]}" --fields api_key --reveal 2>/dev/null) || {
  echo "ERROR: could not read Gemini API Key from 1Password" >&2
  exit 1
}

scenes=(
  "modern financial district"
  "upscale café"
  "luxury hotel lounge"
  "premium office"
  "elegant home interior"
  "rooftop with skyline"
  "airport lounge"
  "contemporary coworking"
  "urban street with cinematic blur"
  "city at sunset"
  "nighttime metropolis"
  "supermarket checkout"
  "restaurant payment moment"
  "home budgeting desk"
  "travel desk with passport and luggage tag"
)
scene="${scenes[$RANDOM % ${#scenes[@]}]}"

# Visual variation prevents category pages from looking repetitive. These are
# generic finance/lifestyle compositions inspired by common editorial patterns,
# not by any competitor's branded overlays, logos, or corner graphics.
visual_briefs=(
  "large centered card floating in front of one confident person, premium editorial composition"
  "close-up hand holding the card toward the camera, shallow depth of field, fingers do not cover issuer logo or payment network mark"
  "contactless payment moment with the card near a generic payment terminal, no merchant logos, card remains readable"
  "card partially entering or leaving a wallet or jacket pocket, lifestyle banking moment, card brand still visible"
  "flat lay desk scene with card beside smartphone, receipts and coffee, clean budgeting context"
  "online shopping context with laptop and parcel in background, card in foreground, no visible retailer logos"
  "travel context with passport, boarding-pass-like generic paper and card, no airline logos"
  "cashback/rewards context with shopping bag, hotel loyalty vibe and premium lifestyle props, no graphic icons, badges or text overlays"
)
visual_brief="${visual_briefs[$RANDOM % ${#visual_briefs[@]}]}"
mode_label="REC featured image"
mode_distinction="This is the REC featured image: it should feel like a quick commercial recommendation hook, lifestyle/payment/rewards oriented, not an application explainer."

if [[ "$SLUG" == p1-* ]]; then
  # P1 must not look like a reused REC hero. Force a different intent and
  # composition family: application/deep-dive support, more explanatory and
  # decision-oriented, with distinct background/framing from the REC image.
  mode_label="P1 featured image"
  scene="application review desk or modern advisory office"
  visual_brief="P1 application/deep-dive support scene: realistic person reviewing card details on a desk or in an advisory setting, exact card centred but not in the same lifestyle/payment composition as REC, different background and framing, calm decision-oriented mood"
  mode_distinction="This is the P1 featured image. It must be visually distinct from the REC featured image for the same card: different scene, framing, background/foreground treatment and editorial intent. Do not recreate the REC lifestyle/payment hook."
fi

mime=$(file -b --mime-type "$CARD_IMG" 2>/dev/null || echo "image/png")
b64_tmp=$(mktemp /tmp/gemini-b64-XXXXXX)
TEMP_FILES+=("$b64_tmp")
base64 -w0 "$CARD_IMG" | tr -d '\n' > "$b64_tmp"

prompt=$(cat <<PROMPT
You must compose a photo-realistic 16:9 (1920x1080) horizontal lifestyle/finance
background scene. The exact credit card will be composited separately by the
pipeline after generation. Do NOT generate, draw, recreate, duplicate, or place
any credit card, debit card, payment card, bank card, card-shaped mockup, badge,
or card-like rectangle in the scene.

Scene: $scene.
Image role: $mode_label.
Visual variation for this run: $visual_brief.
Role-specific distinction: $mode_distinction.

Composition rules:
- Leave a clean natural central foreground area where the pipeline can later
  place the exact card. Do not put any object shaped like a payment card there.
- For P1 images, follow this intent: realistic full-scene background with depth,
  calm decision-oriented desk/advisory mood, and no generated card object.
- Do not add borders, frames, moulding, stickers, badges, glow outlines, or
  external graphic effects.
- Use the selected visual variation naturally; do not force the same centered-card
  layout every time.
- Acceptable variations include: generic payment terminal in the background,
  smartphone, receipts, coffee, budgeting desk, wallet, shopping/rewards context,
  travel context, or one person in a realistic finance/lifestyle setting.
- If a hand is present, it must not hold a card or card-like object.
- Use only generic props. No competitor logo, no site logo, no branded corner
  overlay, no blue corner effect copied from another site, no retailer/airline/
  merchant logos.
- Keep the scene clean: no cards, no duplicate cards, no extra card designs, no UI overlay,
  no stickers, no badges, no text labels.

Style: ultra-realistic commercial photography (full-frame camera), cinematic
key + soft fill + subtle rim light, realistic card reflections, soft natural
shadows, premium editorial color grading. Vary camera angle and distance across
runs: close-up, flat lay, over-the-shoulder, payment moment, lifestyle portrait,
or product-focused foreground.

Negative: credit card, debit card, payment card, bank card, card-like rectangle,
competitor branding, Memivi logo, blue corner overlay, picture frame, mockup frame,
extra card, duplicate card, phone screen with readable UI, badge, sticker,
unnecessary objects, altered card design, vertical card orientation, distorted
anatomy, extra fingers, fake smile, cartoon, illustration, CGI, 3D render, stock
photo look, flat lighting.

Output: one image, 16:9, photo-realistic.
PROMPT
)

req_tmp=$(mktemp /tmp/gemini-req-XXXXXX)
TEMP_FILES+=("$req_tmp")
jq -n \
  --arg text "$prompt" \
  --arg mime "$mime" \
  --rawfile data "$b64_tmp" \
  '{contents:[{parts:[{text:$text},{inline_data:{mime_type:$mime,data:$data}}]}]}' \
  > "$req_tmp"

endpoint="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key=$api_key"
out="/tmp/featured-$SLUG.png"

max_attempts=3
attempt=1
while [ "$attempt" -le "$max_attempts" ]; do
  tmp_body=$(mktemp)
  http_code=$(curl -sS -o "$tmp_body" -w '%{http_code}' \
    -H "Content-Type: application/json" -X POST -d @"$req_tmp" "$endpoint" || echo "000")
  body=$(cat "$tmp_body")
  rm -f "$tmp_body"

  if [ "$http_code" = "429" ] || [ "$http_code" = "503" ]; then
    echo "[$(date -Iseconds)] generate-featured-image RETRY attempt=$attempt http=$http_code slug=$SLUG" >>"$LOG"
    if [ "$attempt" -lt "$max_attempts" ]; then
      sleep 5
      attempt=$((attempt+1))
      continue
    else
      echo "[$(date -Iseconds)] generate-featured-image ABORT slug=$SLUG after $max_attempts attempts (rate-limit)" >>"$LOG"
      echo "ERROR: Gemini rate-limited after $max_attempts attempts. Last HTTP=$http_code body head: $(echo "$body" | head -c 400)" >&2
      exit 1
    fi
  fi

  if [ "$http_code" != "200" ]; then
    echo "[$(date -Iseconds)] generate-featured-image FAIL http=$http_code slug=$SLUG body=$(echo "$body" | head -c 500)" >>"$LOG"
    echo "ERROR: Gemini returned HTTP $http_code. Body head: $(echo "$body" | head -c 500)" >&2
    exit 1
  fi

  img_b64=$(jq -r '.candidates[0].content.parts[]? | (.inlineData // .inline_data) | .data // empty' <<<"$body" | head -n1)
  if [ -z "$img_b64" ] || [ "$img_b64" = "null" ]; then
    echo "[$(date -Iseconds)] generate-featured-image NO-IMAGE slug=$SLUG body=$(echo "$body" | head -c 500)" >>"$LOG"
    echo "ERROR: Gemini returned no image. Response head: $(echo "$body" | head -c 500)" >&2
    exit 1
  fi

  echo "$img_b64" | base64 -d >"$out"

  # Preserve card identity deterministically: Gemini may alter small card text,
  # so compose the exact provided card artwork over the generated scene before
  # compression/semantic audit.
  composite_card=$(mktemp /tmp/featured-card-overlay-XXXXXX.png)
  composite_shadow=$(mktemp /tmp/featured-card-shadow-XXXXXX.png)
  composite_out=$(mktemp /tmp/featured-composite-XXXXXX.png)
  TEMP_FILES+=("$composite_card" "$composite_shadow" "$composite_out")
  convert "$CARD_IMG" -resize '760x430>' "$composite_card"
  convert "$composite_card" -background black -shadow 35x18+0+18 "$composite_shadow"
  convert "$out" -resize 1920x1080^ -gravity center -extent 1920x1080 \
    "$composite_shadow" -gravity center -geometry +0+34 -compose over -composite \
    "$composite_card" -gravity center -geometry +0+0 -compose over -composite \
    "$composite_out"
  cp "$composite_out" "$out"

  # Comprimir PNG -> JPEG (reduz ~94%, qualidade visual mantida)
  SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
  out=$("$SCRIPT_DIR/compress-image.sh" "$out" featured)

  echo "[$(date -Iseconds)] generate-featured-image OK slug=$SLUG scene=$scene visual_brief=$visual_brief attempt=$attempt path=$out" >>"$LOG"
  jq -n --arg p "$out" --arg s "$scene" --arg v "$visual_brief" --argjson a "$attempt" '{path:$p, scene:$s, visual_brief:$v, attempt:$a}'
  exit 0
done

```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/scripts/generate-card-only-image.sh`

```text
#!/bin/bash
set -euo pipefail
cat >&2 <<'MSG'
ERROR: generate-card-only-image.sh is deprecated for REC LazyBlock card images.

Reason: the MBNA manual-image incident showed that AI-generated/enhanced
card-only assets can change text, edges, shadows, colours, or brand design.
LazyBlock card images must preserve the real supplied/selected card artwork.

Approved paths:
- If the user supplies a card image: crop/remove external canvas while preserving
  the original RGB card design; reject damaged/low-quality crops instead of
  inventing a new card.
- If no card image is supplied: use automatic card-image search/ranking and
  validate the selected real card artwork.
- Use Gemini/featured generation only for contextual/lifestyle featured images,
  not to recreate isolated card assets for LazyBlock.
MSG
exit 2

```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/scripts/generate-clean-card-image.sh`

```text
#!/bin/bash
set -euo pipefail

cat >&2 <<'MSG'
ERROR: generate-clean-card-image.sh is deprecated for REC LazyBlock card images.

Reason: the MBNA 62092 incident showed that Gemini-generated card-only assets can
look acceptable in featured compositions but fail as isolated LazyBlock card
images due to edge/text/shadow artifacts.

Use the current runner behavior instead:
- normalize user-supplied manual card images with normalize-card-artwork.py;
- if the useful crop is too small/rough, reject it for LazyBlock;
- fall back to automatic card-only image search;
- report manual_source_url and manual_rejected_reason.
MSG
exit 2

```


---

# FILE: `/root/mgs-agent/skills/content-publish-wordpress/SKILL.md`

```text
---
name: content-publish-wordpress
description: Utility skill to publish posts to WordPress (resolve credentials from 1Password, upload media, create/update posts, set Yoast SEO meta, resolve category/tag IDs). Called by other skills like content-generate-rec, content-generate-p1, content-generate-seo. Does NOT write article content — receives pre-assembled HTML.
---

# content-publish-wordpress

Shared utility skill that publishes content to WordPress sites configured in
`/root/mgs-agent/data/sites.json`. Handles every HTTP interaction with the WP
REST API so other skills can focus on generating content.

## When to use

Invoke this skill from another skill (never directly from the user) when you
need to:

1. Upload an image to the media library
2. Resolve a category or tag by name → ID (creating if missing)
3. Create a post with fully assembled HTML (including LazyBlock comments)
4. Apply Yoast SEO meta to an existing post (title / description / focus keyword)

## Required inputs

Every call must include a `site_key` matching a key in
`/root/mgs-agent/data/sites.json`. The skill reads that file to discover
`wp_url`, `publishing_user`, and `credentials_ref` (1Password pointer).

## Scripts

All scripts live in `./scripts/` and must be invoked via absolute path.

HTTP calls must use the centralized `wp_curl_auth_http` wrapper in `scripts/wp-curl-auth.sh` when capturing status codes. This keeps credentials out of argv, preserves 4xx/5xx bodies via `--fail-with-body`, returns real HTTP codes for REST errors, and reserves `000` for transport failures. See `references/wp-rest-curl-hardening.md` for the validation recipe and fake-curl probe.


### `resolve-credentials.sh <site_key>`
Reads `sites.json`, pulls the WordPress Application Password from 1Password via
`op item get`, and emits a JSON object:
```
{ "wp_url": "...", "username": "...", "password": "...", "author_id": 11 }
```

### `upload-image.sh <site_key> <image_path> <filename>`
Uploads `image_path` as `filename` to `/wp/v2/media` using Basic auth.
Emits: `{ "id": <int>, "source_url": "..." }`.

### `resolve-term.sh <site_key> <taxonomy> <name>`
`taxonomy` is `categories` or `tags`. Looks up the term by name (search); if
absent, creates it. Emits: `{ "id": <int>, "name": "...", "slug": "..." }`.

### `create-post.sh <site_key> <post_json_path>`
POSTs the JSON file at `post_json_path` to `/wp/v2/posts`.
Post JSON shape (caller responsibility):
```json
{
  "title": "...",
  "slug": "...",
  "content": "...",
  "status": "draft",
  "author": 11,
  "categories": [212],
  "tags": [456, 469, 214, 451, 219, 468],
  "featured_media": 61845,
  "meta": {
    "_yoast_wpseo_title": "...",
    "_yoast_wpseo_metadesc": "...",
    "_yoast_wpseo_focuskw": "..."
  }
}
```
Emits the full created post JSON from WP (includes `id`, `link`).

### `update-yoast.sh <site_key> <post_id> <yoast_json_path>`
Applies Yoast meta in the proven two-PUT pattern:
1. PUT `/wp/v2/posts/<id>` with only `{ meta: {...} }`
2. `sleep 2`
3. PUT `/wp/v2/posts/<id>` with `{ title, content, meta }` (content/title
   re-sent to trigger Yoast's `save_post` hook).
Emits `{ "ok": true, "post_id": <id> }` or a structured error.

The `yoast_json_path` file must contain:
```json
{
  "title": "...",
  "content": "...",
  "meta": {
    "_yoast_wpseo_title": "...",
    "_yoast_wpseo_metadesc": "...",
    "_yoast_wpseo_focuskw": "..."
  }
}
```

> **PITFALL — top-level `title` must never be blank:** `_yoast_wpseo_title`
> should usually stay blank so Yoast inherits the global template, but the
> top-level `title` field in `yoast_json_path` is the WordPress post title that
> `update-yoast.sh` re-sends to trigger hooks. Never set top-level `title` to
> `""`; doing so can blank the article title in WordPress while Yoast still
> scores the content. Always pass the real post title and keep only
> `meta._yoast_wpseo_title` blank when template inheritance is desired.

## Workflow a caller should follow

1. `resolve-credentials.sh eggbev` → cache in memory
2. `upload-image.sh eggbev /tmp/card.png card-aib-visa-gold.png` → card media
3. `upload-image.sh eggbev /tmp/featured.png featured-aib-visa-gold.png` → featured media
4. `resolve-term.sh eggbev categories "Credit Card"` → category id
5. For each tag: `resolve-term.sh eggbev tags "<name>"` → tag id
6. Caller assembles final post JSON (with raw HTML content containing LazyBlock
   comments) and writes to a tempfile
7. `create-post.sh eggbev /tmp/post.json` → `{id, link, ...}`
8. `update-yoast.sh eggbev <id> /tmp/yoast.json`
9. Return post link to the user

## Non-goals

- This skill does NOT generate text, headings, or LazyBlock payloads.
- This skill does NOT fetch images from the web or call Gemini.
- This skill does NOT decide tags, categories, or SEO copy — it only applies
  what the caller hands in.

## Logs

All scripts append to `/root/mgs-agent/logs/publish-wordpress.log` with
timestamp + action + HTTP status. On error, stderr receives a human-readable
message and exit code is non-zero.

## REC publish/readiness gate for status changes

When changing an existing REC from `draft` to `publish`, or updating a published REC, the caller must run the same readiness checks used by the REC pipeline before reporting success.

Minimum gate for REC posts:
1. Run `validate-article.sh` on the exact final body when content changed.
2. Run `yoast-score-post.sh <site_key> <post_id>` after the update/status change.
3. Treat Yoast Readability `<71` as not ready; repair before final reporting unless Rodolfo/Raquel explicitly approves the exception.
4. Preserve LazyBlocks exactly during any readability repair.
5. Keep REC word count `450–500` and subtitle/excerpt `≤100` characters.
6. For yellow/red readability, use the REC repair reference in `content-generate-rec/references/rec-readability-repair-2026-05-26.md`.

This prevents a manual REST status flip from bypassing the editorial/Yoast hard gate.

## Safe teardown for benchmark/test articles

See also `references/rec-benchmark-cleanup-helper.md` for a reusable scoped cleanup pattern.

For failed REC+P1 runs that created duplicate drafts or media before a later validation/readability failure, use `references/rec-p1-failed-run-cleanup.md`. Key pitfall: draft posts are production editorial state; cleanup must remove/verify both created posts and scoped media, otherwise WP can retain duplicate RECs, P1 drafts with `featured_media=0`, or HTML referencing deleted media.

When a user asks to delete a test/draft article and recreate it from scratch, clean only the requested article/card scope:

1. Fetch the post by direct ID with auth and confirm the title/slug matches the requested article before deleting.
2. Delete the post with `force=true`.
3. Delete only media that is attached to the post or whose slug/title/source URL clearly matches the requested card slug.
4. Verify the post and deleted media return 404 via WordPress REST.
5. If the content runner cached product data, remove only the matching card slug rows from `card_cache` and `cache_access_log`.
6. If server access is available, remove physical upload/cache files matching the specific card slug/post ID only; do not purge broad site cache unless explicitly requested.
7. If Cloudflare still returns cached uploaded images after origin deletion, report that edge cache may lag; verify origin 404 when possible.

## WP REST curl hardening

For scripts that call WordPress REST, use the centralized `wp_curl_auth_http` pattern documented in `references/wp-curl-http-wrapper.md`: preserve real HTTP 4xx/5xx status + body with `--fail-with-body`, return `000` only for transport failure, and keep credentials hidden via `curl -K` tempfiles.

## Querying WP post status from outside the pipeline (Zeus / audit use)

**Best source** — `logs/publish-wordpress.log`, grep for `create-post OK`:
```bash
grep "create-post OK" /root/mgs-agent/logs/publish-wordpress.log | tail -5
# e.g. → create-post OK http=201 site=eggbev id=61965
```
Gives the canonical post ID without touching WP REST API.

**Fetch post by ID** (no auth needed for published posts):
```bash
curl -s "https://eggbev.com/wp-json/wp/v2/posts/<ID>" | python3 -c "
import sys, json; p = json.load(sys.stdin)
print(p['id'], p['status'], p['slug'], p['title']['rendered'][:80])"
```

**Auditing/listing Atena-published posts on eggbev**:
When asked for "articles you published" over a date range, do not rely on a single `/posts?tags=<atena_agent>` public REST query. On eggbev, list endpoints and filters can be incomplete because of plugin/theme behavior and older Atena posts may predate the `atena_agent` tag. Use a combined audit pattern:
1. Query public REST by `tags=atena_agent` for the main list.
2. Cross-check known/recent publish IDs from logs/session history.
3. For a bounded range, directly probe likely post IDs with `GET /wp/v2/posts/<id>?_fields=id,date,link,title,status,tags`; direct ID lookup is more reliable than list filters.
4. Include older confirmed Atena posts even if they lack `atena_agent`, but explicitly note that exception in the user-facing answer.

**eggbev.com REST API quirks (verified 2026-04-23; audit behavior reconfirmed 2026-05-16)**:
- `Authorization=[REDACTED]
- `GET /users/me` returns 401 even with valid app password — auth partially restricted.
- `?status=draft` / `?status=any` → 401 without working auth session.
- `?slug=<slug>` always returns `[]` — broken by plugin interference (known issue, see CLAUDE.md).
- `?search=rec` on public endpoint works but only returns published posts.
- Direct `GET /posts/<id>` is the most reliable query — works unauthenticated for published posts.

```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/references/atena-rebuild-soul-skill-contract-boundaries-2026-06-05.md`

```text
# Atena rebuild — SOUL / SKILL / contract boundaries

Session context: Rodolfo is rebuilding Atena cleanly after the REC+P1 workflow accumulated rules in SOUL, SKILL, templates and references. The durable lesson is not the specific draft content; it is the classification rule for where future rules belong.

## Boundary rule

```text
Quem a Atena é / como se comporta       -> SOUL.md
Como executar REC+P1                    -> SKILL.md
Como o REC deve ser                     -> contracts/cc-rec.md
Como a P1 deve ser                      -> contracts/cc-p1.md
Configuração de sites                   -> data/sites.json
Histórico de bugs e incidentes          -> references/archive
Código de execução                      -> scripts/runners + validators
```

Do not put full operational templates in SOUL. SOUL may carry a short principle and a pointer to the operational source of truth.

## REC+P1 as the normal product

Rodolfo clarified that normal production should not be “ask for REC, then ask for P1”. The normal request is one business operation: REC+P1. Standalone REC or P1 should be treated as exception/repair/audit/continuation unless Rodolfo/Raquel explicitly request it.

A complete request usually includes:

```text
Site/vertical: Eggbev / gb-cc-en
Tipo: REC+P1
Produto/cartão: <exact card name>
Status: rascunho|publicado
URL oficial: <official issuer URL>
Imagem do card: <optional>
```

Complete request = authorization to execute end-to-end. Do not add ritual approval pauses. Pause only on a real blocker: official URL mismatch/inaccessible, unverified essential facts, bad/incompatible card image, security/production conflict, or risk of publishing wrong content.

## Final report placement

Rodolfo’s exact final summary template belongs in the SKILL/summary renderer, not SOUL. SOUL should only say that Atena must deliver an auditable final report with links, status, validations, images, official source, time and cost.

The SKILL/renderer must carry the exact field order:

```text
REC block: Post ID, public URL, edit URL, slug, status.
P1 block: Post ID, public URL, edit URL, slug, status.
REC detail block: type, Yoast SEO/readability, validation, title+chars, focus, meta+chars, tags, card image, featured image, official source.
P1 detail block: same fields.
Timing/cost block: runner times REC+P1 and estimated cost REC+P1=total.
```

## Image rule placement

SOUL should only hold the principle: images are part of editorial quality/conversion; preserve real card identity; do not declare success when final images are false, distorted, illegible, incompatible, wrongfully reused or poor quality.

SKILL should hold the operational image rules:

- If Rodolfo/Raquel sends a card image, treat it as the primary source; do not silently swap to fallback.
- If the image is vertical, bordered, canvas/banner, has drawings/headline/background, extract the actual card and normalize for LazyBlock.
- Rotate/prepare horizontal presentation when needed.
- Improve quality when possible; block/report if final rendering remains visibly poor.
- Use the cleaned validated card in REC LazyBlock and reuse the same cleaned card in P1 LazyBlock.
- REC featured and P1 featured must be different media/visual concepts.
- REC featured should include/compose the validated card when the visual spec requires it.
- P1 featured should be distinct from REC and may be reused as the internal P1 image after the first paragraph.

Validators/runners should enforce the rules where possible: same LazyBlock card for REC/P1, distinct REC/P1 featured media IDs/URLs, no fake/altered card identity, no silent fallback after user-supplied image, and no success report when image gates fail.

## Editing method

For this rebuild class of task, prefer creating a clean draft and using the old SOUL as source material. Line-by-line patching keeps the old remediated structure alive and tends to preserve contradictions.

```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/references/atena-restructure-rule-placement-and-rec-p1-quality-2026-06-05.md`

```text
# Atena restructure — rule placement and REC+P1 quality decisions (2026-06-05)

Session-specific reference from Rodolfo/Raquel's Atena rebuild discussion. Use as migration context when rewriting Atena SOUL/SKILL/contracts/runners; do not treat as a standalone active production rule unless promoted into the proper file.

## Process preference

Rodolfo wants the rebuild reviewed strictly step by step:

1. Finish `SOUL.md` first.
2. Only after Rodolfo says SOUL is ready, move to SKILL.
3. Then contracts, runners/validators, and other files.

During SOUL review, classify items that belong elsewhere and keep a queue so nothing is lost, but do not send/review SKILL deliverables until Rodolfo asks.

## Placement rules confirmed

```text
Who Atena is / behavior principles        -> SOUL.md
How to execute REC+P1                     -> SKILL.md
How REC should be written                 -> contracts/cc-rec.md
How P1 should be written                  -> contracts/cc-p1.md
Site/vertical config                      -> data/sites.json
Bug/incident history                      -> references/archive
Execution code                            -> scripts/runners
Automated hard gates                      -> runners/validators
```

## REC+P1 architecture decision

Normal production should treat REC+P1 as one business request. Rodolfo does not want to keep working by asking for REC first and P1 later; that created conflicts.

Keep REC and P1 editorial contracts separate because they are different article products:

- `cc-rec.md` = short attraction/pre-conversion article that routes to P1.
- `cc-p1.md` = longer deep-dive/conversion article that routes to official issuer/bank.
- `SKILL.md` = operational REC+P1 flow that generates both together.

Optional future: a short REC+P1 flow contract/reference may exist only to describe cross-article relationship rules, not to merge REC and P1 specs into one giant contract.

## Anti-repetition / scale quality

Problem observed: Atena produced REC and P1 paragraphs that were copied or ~90% similar, and later REC+P1 runs repeated phrases/paragraphs from earlier articles. This is a scale blocker: if 50 articles are requested, each must remain specific to its card.

Placement:

- SOUL: principle that Atena must produce card-specific, non-boilerplate content.
- Contracts: REC has its own angle; P1 deepens without copying REC or previous P1s.
- SKILL: before success, check REC↔P1 similarity and recent same-vertical repetition.
- Validator/runner: hard gates for repeated phrases/paragraphs and cross-corpus boilerplate when possible.
- References/archive: historical examples of repeated text.

Suggested SOUL-level principle:

> Produce content specific to each card, avoiding boilerplate, reused phrases, similar paragraphs and repeated argument structures between REC, P1 and previous articles. Each card has its own proposition, benefit, audience and context; if text is interchangeable with another card, it failed editorially.

## Image rules — placement

Keep only principle/macro behavior in SOUL. Operational details belong elsewhere.

- SOUL: images are part of quality/conversion; preserve real card identity; do not declare success when final image is false, distorted, illegible, incompatible, reused wrongly or visually unacceptable.
- SKILL: operational rules for user-supplied image as primary source, extracting card from vertical/bordered/banner/canvas images, cleaning background, rotating/normalizing for horizontal LazyBlock presentation, improving quality when possible, and using the final card in REC and P1 LazyBlocks.
- Contract: desired visual outcome for REC featured and P1 featured.
- Runner/validator: enforce same cleaned card in REC/P1 LazyBlocks, distinct featured media for REC vs P1, card identity preservation, no silent fallback after user-supplied image failure.
- References/archive: historical mistakes (same REC/P1 featured, card with border/canvas, ignored supplied image, low quality accepted, fake generated card).

## Final report character counts

Raquel/Rodolfo classified character counts as operational delivery evidence, not SOUL identity.

- SKILL/final report: require title chars, subtitle chars, excerpt chars, meta description chars.
- Renderer/runner: calculate automatically; do not rely on manual estimates.
- Validator/runner: repair or warn/block if outside contract limits before success.

## Discord/read-only discussion note

In Zeus channel/thread, if Raquel comments in context, Zeus should read/analyze/respond when Rodolfo is in the discussion or asks, but must not apply file changes, persistence, restarts, authorization or operational side effects without Rodolfo's explicit approval.

```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/references/rec-editorial-image-quality-gates-2026-05-17.md`

```text
# REC editorial and image quality gates — 2026-05-17

Use this reference when tightening REC production quality after Rodolfo/Raquel identifies readability, card image, or featured image issues.

## Trigger

Rodolfo flagged that recent REC posts (Marbles Credit Card and Barclaycard Avios Credit Card) violated established editorial and visual standards:

1. Paragraph structure was too dense.
2. The Barclaycard Avios card image appeared vertical/tall, making the LazyBlock card presentation disproportionate across devices.
3. The Barclaycard Avios featured image included unnecessary frames/overlays instead of the approved three-layer composition.

## Durable rules confirmed

### Editorial readability gate

REC body validation must enforce all of these before publication:

- Final visible word count: 450–500 words.
- Each paragraph: maximum ~30 words, matching the “up to 3 visual lines” editorial expectation.
- Each H2/subtitle section: maximum 4 paragraphs.
- Long sentences: no more than 20% of all sentences may exceed 20 words.

Do not treat these as soft Yoast suggestions. They are publication gates.

### Card image gate

The card artwork used in the LazyBlock and featured composition must always be horizontal/landscape.

If a downloaded or manually supplied card image is vertical/tombstone:

1. Rotate it to landscape before upload.
2. Crop near-white/transparent borders after rotation.
3. Use the normalized horizontal asset for both the LazyBlock and featured-image generation.
4. Do not publish a REC with a vertical/tall card image.

### Featured image composition gate

The featured image should be contextual/lifestyle hero art with only essential elements:

1. A realistic premium background or real-use scene.
2. The same validated horizontal card integrated naturally in context.
3. One realistic person or real-use element near the card.

Reject/regenerate images containing:

- Card-only mockups or a huge isolated card on a generic background.
- Redesigned/different card artwork, wrong issuer, wrong colours, or altered layout.
- Frames, molduras, picture frames, mockup frames or decorative panels.
- Duplicate cards, extra cards or card fragments.
- UI overlays, badges, stickers or phone screens.
- Any unnecessary objects that make the composition look like a collage/mockup rather than a premium realistic ad image.

## Implementation notes from this correction

The quality gates belong in different canonical layers:

- Template: editorial rules and visual spec for the vertical/language.
- Validator script: mechanical enforcement of paragraph/sentence/section limits.
- Runner/SKILL pipeline: hard gates for card orientation and featured composition.
- Featured generation prompt: direct negative instructions for Gemini.

When a user reports this kind of issue, update the relevant canonical layer instead of relying on memory or chat reminders.

## Verification pattern

For a dry-run article, inspect the validator JSON and expect values similar to:

```json
{
  "status": "PASS",
  "style": {
    "avg_paragraph_words": 19.9,
    "max_paragraph_words": 27,
    "max_section_paragraphs": 4,
    "long_sentence_ratio": 0.0556,
    "style": "pass"
  }
}
```

For card orientation, a synthetic vertical card should return `rotated=true` and horizontal dimensions after normalization.
```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/references/rec-p1-benefit-based-tags-and-report-format-2026-06-08.md`

```text
# REC+P1 benefit-based tags, runner review and final report format — 2026-06-08

## Trigger

Use this reference when reviewing or changing Atena REC+P1 contracts, runners, WordPress taxonomy, LazyBlock tags, or final response format.

## Durable lessons

1. **Do not make Rodolfo repeat the final report template.** The template must live in `content-generate-rec-p1/SKILL.md` and be rendered by `/root/mgs-agent/scripts/render-article-summary.py`. If Rodolfo asks whether Atena will answer in a format, verify SKILL + renderer + runner JSON, then patch them if they diverge.

2. **Review runners, not only contracts.** For REC+P1 changes, inspect:
   - `/root/mgs-agent/scripts/mgs-rec-runner.py`
   - `/root/mgs-agent/scripts/mgs-p1-runner.py`
   - `/root/mgs-agent/scripts/mgs-rec-p1-orchestrator.py`
   - `/root/mgs-agent/scripts/render-article-summary.py`

3. **No false commercial fallback.** WordPress tags, LazyBlock `tag10`/`tag2`, descriptor text, article benefits and commercial positioning must derive from confirmed card facts: official source or explicit verified request facts. Do not fill missing benefits by picking generic labels like `rewards credit card`, `travel credit card`, `cashback rewards`, `Avios rewards`, `purchase credit card`, `Everyday value`, or `Apply online`.

4. **Block instead of padding.** If the official source does not yield enough confirmed benefits/facts, the runner should block and ask for a better official URL or explicit verified benefits. Do not pad with generic guidance such as “check the official page”.

5. **Purchase tag is narrow.** `purchase credit card` should only be used when a confirmed purchase-related offer exists, such as 0%, interest-free, introductory, or promotional purchase terms. Ordinary “everyday purchases” or Visa/Mastercard acceptance is not enough.

6. **Renderer is part of the contract.** If the SKILL requires fields such as Subtitle and Excerpt, the runner JSON must expose them and the renderer must print them. Validate with a fixture through `render-article-summary.py --type rec-p1`.

## Verification pattern

Before telling Rodolfo the flow is ready:

```bash
python3 -m py_compile \
  /root/mgs-agent/scripts/mgs-rec-runner.py \
  /root/mgs-agent/scripts/mgs-p1-runner.py \
  /root/mgs-agent/scripts/mgs-rec-p1-orchestrator.py \
  /root/mgs-agent/scripts/render-article-summary.py

git -C /root/mgs-agent diff --check -- \
  scripts/mgs-rec-runner.py \
  scripts/mgs-p1-runner.py \
  scripts/mgs-rec-p1-orchestrator.py \
  scripts/render-article-summary.py \
  skills/content-generate-rec-p1/SKILL.md
```

Also run a small deterministic renderer fixture to confirm output includes:

- REC/P1 Post IDs, public/edit links, slug, status;
- Yoast SEO/readability;
- validation words/subtitle chars/public HTTP;
- title, subtitle, excerpt, focus, meta;
- tags, card image, featured image, official source;
- operation time and cost.

## User-facing expectation

For REC+P1 requests, Rodolfo should be able to send only the operational request (site, vertical, card, official URL, status). Atena should know the report format from the skill/renderer; do not ask Rodolfo to include the template again.

```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/references/rec-p1-contract-v2-restructure-2026-06-08.md`

```text
# REC/P1 contract v2 restructure — 2026-06-08

Use this reference when reviewing, rolling back, or extending the Atena REC+P1 credit-card restructure validated with Rodolfo/Raquel.

## What changed

- REC became a short consultative recommendation, not a generic long review.
- P1 became the deeper application/details article and must not repeat REC phrasing.
- REC meta description range changed to 130–140 chars.
- P1 keyword/card-name count changed to 5–8 visible uses.
- REC slug pattern: `rec-{country_code}-cc-{card_name}`.
- P1 slug pattern: `apply-now-{country_code}-cc-{card_name}`.
- Visual rules moved to `references/featured-image-visual-contract.md`.
- Runners/validators were aligned after contract changes; do not update contracts alone if runners/hard gates still enforce old rules.

## Card image vs featured image rule

Keep this distinction explicit in future reviews:

```text
Isolated card image      Separate asset used in LazyBlock REC/P1.
                         May be reused between REC and P1.
                         May serve as visual reference/base.

Featured image REC       Final contextual/lifestyle ad composition for REC.
Featured image P1        Final contextual/lifestyle ad composition for P1.
                         Must be different from REC featured image.
```

The isolated card image is **not** the featured image final. It only helps preserve card identity when generating the featured composition.

## Runner validation lessons

After applying editorial contract changes, validate at both levels:

1. Static/syntax:
   - `python3 -m py_compile` for REC/P1/orchestrator scripts.
   - `git diff --check` for changed contracts/scripts.
2. Safe generation:
   - REC dry-run with official/card data and realistic benefits.
   - P1 unit generation or dry-run.
   - Semantic QA on generated HTML/body.
3. Evidence expected:
   - REC word count within contract and semantic QA OK.
   - REC meta chars in 130–140.
   - P1 details blocks present.
   - P1 has two LazyBlocks.
   - P1 visible keyword total in 5–8.

## Common pitfalls fixed in this session

- Contract says new REC/P1 structure but runner still generates old sections.
- SEO validators still enforce old meta ranges.
- Keyword count accidentally includes LazyBlock JSON/figure alt instead of visible text.
- REC body uses words/phrases that trip hard gates (`Review`, repeated generic reader phrasing).
- Reporting featured-image rules without separating card reference asset from final featured composition.

## Operational next step after restructure

Do not jump straight to publish. First run one controlled real draft REC+P1:

```text
1. Choose one site.
2. Choose one real card.
3. Use official issuer URL/source.
4. Generate REC+P1 as draft.
5. Validate card image, REC featured image, P1 featured image different from REC, LazyBlocks, Yoast, slugs, semantic QA, and preview/draft evidence.
6. Only then release production use.
```

Atena gateway restart is not usually required for scripts/contracts read from disk, but for the first post-restructure live test, prefer a clean gateway restart if Rodolfo approves so no stale active-thread/session context influences the test.

```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/references/rec-p1-post-restructure-validation-and-latency-2026-06-08.md`

```text
# REC+P1 post-restructure validation, reporting and latency lessons — 2026-06-08

## Context

After the REC/P1 contract/runners were restructured, Rodolfo asked Atena to publish:

```text
Site: eggbev
Vertical: gb-cc-en
Card: Tesco Bank Balance Transfer Credit Card
Official URL: https://www.tescobank.com/credit-cards/balance-transfer-credit-card/
Status: publish/publicado
```

Atena produced REC `62425` and P1 `62429`, but the first production run exposed reporting-format and latency lessons that should govern future REC+P1 operations.

## Final report format preferred by Rodolfo

Use the compact report format. Do **not** show separate lines with the text of Subtitle or Excerpt by default.

Preferred validation line per article:

```text
• Validação: <palavras> palavras / subtitle <chars> chars / excerpt <chars> chars / público HTTP <codigo>
```

Then continue with:

```text
• Title: <titulo> — <chars> chars
• Focus: <palavra chave>
• Meta Description: <texto> — <chars> chars
• Tags: <tags>
• Imagem Card: <url>
• Imagem Featured: <url>
• Fonte oficial: <url>
```

Only show explicit `Subtitle: <texto>` / `Excerpt: <texto>` lines if Rodolfo/Raquel asks for an expanded QA/editorial version.

## Renderer discipline

For normal REC+P1, use the deterministic renderer when runner JSON exists:

```bash
python3 /root/mgs-agent/scripts/render-article-summary.py --type rec-p1 <rec-json> <p1-json>
```

Do not assemble the final REC+P1 report manually unless the renderer cannot be used and the reason is stated. Manual reports easily omit required fields, timings or costs.

## Latency lesson

The Tesco run took about `21m44s` perceived wall-clock time (`1304.5s`, 78 model API calls, 77 tool turns). This is not an acceptable steady-state benchmark.

Primary causes observed:

```text
- live patching during production instead of blocking/reporting a structural gate
- multiple failed orchestrator runs
- repeated image upload/delete cycles
- REC and P1 QA/repair loops
- very large context growth (~115k tokens)
- final validation/reporting done manually instead of one renderer call
```

Expected target after fixes:

```text
Good REC+P1 publish:       3–5 min
Acceptable with heavy img: <=7 min
Inacceptable:              20+ min
```

Future REC+P1 production should not repeatedly patch/retry inside the user-facing run. If a structural gate fails, block/report or run a focused repair, then re-run cleanly.

## Operational checklist for future REC+P1 publish runs

1. Run orchestrator cleanly; avoid ad-hoc manual substeps unless diagnosing a failed run.
2. Limit image retries; reuse validated card image within the same run.
3. Keep official-source and card-image gates strict, but avoid false blockers already documented in `tesco-balance-transfer-runner-fixes-2026-06-08.md`.
4. Ensure WordPress tags and LazyBlock tags are derived from confirmed benefits/facts, not generic commercial fallbacks.
5. Render final summary through `render-article-summary.py`.
6. Report both runner timing and perceived operation timing when retries/repairs happened.
7. If total time exceeds 7 minutes, include a latency note with the root cause.
```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/references/rec-p1-report-format-discipline-2026-06-08.md`

```text
# REC+P1 report format discipline — 2026-06-08

## Context

During the Tesco Bank Balance Transfer REC+P1 publish test, Zeus reviewed Atena's final report and initially said the report was missing Subtitle/Excerpt fields.

Rodolfo corrected the interpretation: Atena had included `subtitle <chars>` inside the validation line. The actual issue was not that the subtitle was absent entirely; the optional improvement would be to show the subtitle/excerpt text in separate lines for QA convenience.

## Durable lesson

When auditing Atena's final REC+P1 report, distinguish between:

```text
Evidence present:   `subtitle 98 chars` in the validation line.
Expanded QA text:   `Subtitle: <text> — 98 chars` in a separate line.
```

Do not label the report as failed/non-compliant solely because it lacks separate `Subtitle:` or `Excerpt:` lines if the approved format only required validation counts.

## Preferred wording

Use precise language:

```text
Correct:
"Ela validou o subtitle pelo count, mas não exibiu o texto em linha própria. Isso é uma melhoria opcional para QA editorial."

Avoid:
"Faltou subtitle."
```

## Operational rule

- Keep Rodolfo's report format lean unless he explicitly asks to expand it.
- Treat `Subtitle:` and `Excerpt:` lines as useful QA additions, not automatic blockers.
- If adding fields to the renderer/SKILL, explain exactly what is being added and why before calling it required.

## Approved REC+P1 final report shape

Rodolfo later specified the preferred production report format. Use this shape for renderer output or manual fallback when JSON is incomplete:

```text
📄 REC Post ID: `<numero do post>`
🔗 REC: `<link>`
✏️ Edit REC: `<link>`
🔗 Slug: `<slug>`
📌 Status: `<status>`

📄 P1 Post ID: `<numero do post>`
🔗 P1: `<link>`
✏️ Edit P1: `<link>`
🔗 Slug: `<slug>`
📌 Status: `<status>`

📄 REC
📊  Yoast: SEO `<pontuacao>` / Readability `<pontuacao>`
• Validação: `<palavras>` palavras / subtitle `<chars>` chars / excerpt `<chars>` chars / público HTTP `<codigo ou evidência draft>`
• Title: `<titulo>` — `<chars>` chars
• Focus: `<palavra chave usada>`
• Meta Description: `<texto que foi inserido>` — `<chars>` chars
• Tags: `<tags>`
• Imagem Card: `<link da imagem do card>`
• Imagem Featured: `<link da featured image>`
• Fonte oficial: `<link oficial utilizado>`

📄 P1
📊  Yoast: SEO `<pontuacao>` / Readability `<pontuacao>`
• Validação: `<palavras>` palavras / subtitle `<chars>` chars / excerpt `<chars>` chars / público HTTP `<codigo ou evidência draft>`
• Title: `<titulo>` — `<chars>` chars
• Focus: `<palavra chave usada>`
• Meta Description: `<texto que foi inserido>` — `<chars>` chars
• Tags: `<tags>`
• Imagem Card: `<link da imagem do card>`
• Imagem Featured: `<link da featured image>`
• Fonte oficial: `<link oficial utilizado>`

⏱️ Tempo total dos runners: REC `<tempo>` + P1 `<tempo>`
💰 Custo estimado: REC `<custo REC>` + P1 `<custo P1>` = `<total>`
```

Formatting notes:

- Keep the two post identity blocks first, before validation details.
- Keep REC and P1 validation as separate repeated sections.
- Use `Meta Description: <texto> — <chars> chars`; avoid a hyphen glued to the text.
- If a runner duration exceeds 60 seconds, display it in minutes in a legible way.
- Include estimated cost per runner plus total when cost metadata exists; if unavailable, say unavailable rather than inventing.

```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/references/rec-p1-scale-quality-gates-2026-05-27.md`

```text
# REC/P1 scale quality gates — repeated-error prevention (2026-05-27)

## Why this exists

Rodolfo escalated that recurring REC/P1 errors cannot be fixed manually article by article. For scale across many sites, repeated corrections must become pipeline/skill hard gates, not Discord reminders.

This reference complements `references/rec-p1-card-image-competitor-descriptor-hard-gates-2026-05-26.md`.

## Root cause pattern from Amazon Barclaycard

The previous repair fixed only part of the rule:
- it correctly rejected phone/app/background promotional card compositions;
- but it incorrectly allowed issuer-published portrait/vertical card art to remain vertical in the LazyBlock card slot.

Correct interpretation:
- `card-only` is required;
- **horizontal card orientation is also required**;
- if the only clean official issuer asset is vertical, rotate it 90° without stretching/distortion;
- do not choose a phone/app/hero composition just because it is already horizontal.

## Non-negotiable gates before REC/P1 is reported ready

### Card image gate

For every LazyBlock card image in REC and P1:
1. Image must show only the card.
2. No phone, app screenshot, hand, scene, banner, background, frame, shadow, mockup or decorative canvas.
3. Card must be horizontal in the final LazyBlock image.
4. If official card art is vertical/portrait, rotate 90° with preserved proportions.
5. Never stretch or distort the card to fake horizontal orientation.
6. Verify the published page no longer references rejected media.
7. Delete the rejected media after replacement when safe.

### Subtitle/excerpt gate

For REC and P1 opening/subtitle/excerpt:
1. Hard cap: **100 characters exactly**, counting spaces and punctuation.
2. Count before publishing and after every rewrite.
3. If >100, rewrite; do not truncate into weak/generic copy.
4. The fallback must still be benefit-led, not a generic sentence.

Blocked fallback examples:
- `{Card Name} offers key credit card benefits and features.`
- `{Card Name} earns rewards and explains key costs before you apply.`
- `{Card Name} explains key costs and benefits before you apply.`

Better fallback pattern:
- `{Card Name} highlights real benefits, costs and application steps.`
- Prefer product-specific hooks when known, e.g. Amazon rewards, cashback, Avios, Nectar, low APR, no annual fee.

### Tone, card-tag and differentiation gate

REC and P1 must not sound like the same article with more words.

REC should read as:
- a light commercial recommendation;
- benefit-led and curiosity-building;
- concise, natural and persuasive without unsupported claims;
- a reason to continue to the P1/application page.

P1 should read as:
- deeper and more strategic;
- richer in product-specific details;
- practical about costs, eligibility and repayment;
- natural/human, not robotic or over-formal.

LazyBlock card tags must be commercially meaningful, not truncated fragments or generic labels. They must:
- highlight real product benefits;
- be clear and objective at a glance;
- transmit value quickly;
- reinforce the product's actual differentiators.

Blocked card-tag patterns:
- truncated strings such as `Over 1`;
- generic labels such as `Travel perks`, `Card benefits`, `Premium card` when a specific benefit is known;
- tags that look incomplete, ambiguous or detached from the product.

Preferred card-tag patterns:
- `Airport Lounge Access`;
- `No Foreign Transaction Fees`;
- `Premium Travel Benefits`;
- `Global Rewards`;
- product-specific reward/fee/insurance/lifestyle benefits confirmed by the official source.

Blocked narrative patterns:
- same structure + same paragraph logic + only card name and numbers changed;
- broad paragraphs that could apply to any premium/rewards card;
- neutral filler such as “frame around its real practical value” without naming the actual benefits.

Required narrative pattern:
- keep the architecture if needed, but vary reasoning, examples, hooks and benefit framing according to the actual product;
- name the specific benefits in explanatory paragraphs, not only in bullet lists;
- for premium travel cards, explicitly connect travel, lounge access, international use, exclusivity, lifestyle and real cost/fee trade-offs when those facts are confirmed.

### P1 featured image opacity gate

For P1 featured images, the card must look solid, crisp and realistic. A visually pleasant composition still needs repair if the card appears transparent, ghosted, washed out, or too low-contrast against the background.

Required checks:
- card body is opaque and visually solid;
- key identity marks remain legible;
- no translucent overlay effect;
- card sits naturally in the premium/lifestyle context without looking pasted or faded.

## Implementation notes from the session

Changes made in the pipeline after the correction:
- `scripts/mgs-rec-runner.py`: REC opening copy made more recommendation-led and product-specific.
- `scripts/mgs-p1-runner.py`: P1 Amazon subtitle shortened and Amazon sections made more natural/product-specific.
- `skills/content-generate-rec-p1/scripts/search-card-image.sh`: official portrait card art is accepted only as clean card-only input and normalized to horizontal output via 90° rotation.
- `references/rec-p1-card-image-competitor-descriptor-hard-gates-2026-05-26.md`: updated with horizontal-image, 100-character subtitle and REC/P1 tone gates.

## Verification recipe

Before final reply on REC/P1 repair or publication:
1. Check LazyBlock media URL(s) in raw/rendered content.
2. Confirm final card image dimensions are landscape (`width > height`).
3. Vision-check if there is any doubt about phone/app/background/mockup elements.
4. Count first REC/P1 subtitle characters exactly.
5. Search visible/rendered content for blocked generic phrases, truncated card tags, weak generic tags, and placeholders.
6. Vision-check P1 featured images for card opacity/solidity, not only 16:9/person/context.
7. Validate REC body with `validate-article.sh` when applicable.
8. Rerun Yoast scoring.
9. Report only verified status, not intended fixes.

```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/references/tesco-balance-transfer-runner-fixes-2026-06-08.md`

```text
# Tesco Balance Transfer REC+P1 runner fixes — 2026-06-08

## Context

REC+P1 publish for `Tesco Bank Balance Transfer Credit Card` on eggbev / gb-cc-en using official URL:

`https://www.tescobank.com/credit-cards/balance-transfer-credit-card/`

The session exposed several durable pipeline lessons for UK issuer balance-transfer cards and deterministic REC+P1 runners.

## Durable lessons

### 1. Official URL/title preflight must consider issuer hostname

The official page title was generic: `0% interest balance transfer credit card`. The path also did not include `tesco` or `bank`, but the hostname `tescobank.com` did.

Old behavior blocked with:

```text
official_url_title_mismatch ... missing_terms=['tesco', 'bank']
```

Durable fix pattern: when checking requested card terms against an official page, include the hostname/domain together with title + path before deciding issuer terms are missing. Generic product titles are common on issuer pages.

### 2. Tesco official page may expose a generic official card image

The page included this official usable image:

```text
https://forrit-one-tb-prod-cdn-p1-prod.azureedge.net/media-76a057a8-43e8-4899-a94d-aaa40249b955/3746884f-d21d-4e16-af52-395543379f1e/clubcard-plus-credit-card.png
```

It does not say “Balance Transfer” on the card face, but it is a clear official Tesco Bank generic credit-card visual and is acceptable when the surrounding LazyBlock/product text identifies the Balance Transfer Credit Card. Reject AI/generated competitor images with fake card text even if they look Tesco-themed.

### 3. Deterministic request facts need four specific facts

When extraction returns `annual_fee=N/A`, REC v2 blocks. Supplying only annual fee is not enough; the deterministic runner switches to request-facts mode only when both `--annual-fee` and at least one `--benefit` are present, and the REC contract requires at least four specific benefits/facts.

Verified facts from the official Tesco page used successfully:

```text
--annual-fee "No annual fee"
--apr "Representative 24.9% APR variable"
--benefit "0% interest on balance transfers for 36 months with a 3.45% fee"
--benefit "0% interest on money transfers for the first 9 months with a 3.99% fee"
--benefit "Collect Clubcard points almost every time you spend in and out of Tesco"
--benefit "Available to UK residents aged 18 and over, subject to status"
```

### 4. Balance-transfer REC top section must include enough intent keywords early

Semantic QA for balance-transfer REC expects the first visible sentences to include at least four of the balance-transfer top keywords and both offer + pain intent.

Useful early terms:

```text
balance transfer
interest free
months
existing card debt
repayments
interest pressure
```

Avoid opening copy that only repeats `balance transfer` + `existing card debt`; include duration, interest-free language and repayment/interest-pressure language before the card/ad area.

### 5. Avoid rewards/travel fallback from generic `points`

Tesco Clubcard points are rewards-related, but not automatically travel rewards. LazyBlock/tag derivation should not treat the word `points` alone as a travel signal. Only use travel-specific tags/descriptor when the official facts contain explicit travel terms such as `travel`, `Avios`, `lounge`, `hotel`, etc.

### 6. Featured image generation should preserve exact card identity deterministically

Gemini frequently altered small card text/dates when asked to include the card itself. A robust pattern is:

1. Generate only a realistic lifestyle/finance background.
2. Explicitly forbid generated cards/card-like rectangles in the prompt.
3. Composite the exact normalized card artwork over the generated background with ImageMagick.
4. Then run the semantic audit.

This improved card identity preservation and avoided fake card text.

### 7. P1 repeated-sentence QA can trigger on generic fee/APR benefit tails

For products with multiple fee/APR facts, avoid appending the same sentence tail to every `fee`/`APR` fact. Vary the second sentence by fact type, e.g. use a distinct money-transfer cost explanation instead of repeating:

```text
Read this as part of the total cost, because interest or fees can quickly reduce any benefit.
```

### 8. REC meta description repair must hard-cap after punctuation cleanup

Truncation + `clean_sentence_punctuation()` can push meta description length back over the 140-char contract limit. After cleanup, re-check length and hard-cap again before final validation.

## Successful artifacts from the session

- REC post: `62425`
- P1 post: `62429`
- REC Yoast after repair: SEO `88`, Readability `90`
- P1 Yoast: SEO `90`, Readability `90`

```


---

# FILE: `/root/mgs-agent/skills/content-generate-rec-p1/references/tesco-rec-p1-raquel-feedback-quality-gates-2026-06-08.md`

```text
# Tesco REC+P1 Raquel feedback — quality gates

Session: 2026-06-08
Scope: post-publication editorial/structural review of Tesco Bank Balance Transfer Credit Card REC+P1, comparing Atena output and Raquel `-2` revisions.

## Core lesson

Runners can still convert real facts into wrong commercial framing when broad fallbacks are used. The clearest example was `Clubcard points` being treated as generic `points`, which allowed `Travel rewards` copy/tagging even though the product is a balance-transfer card, not a travel-rewards card.

Future REC+P1 work must validate not only that facts came from the official source, but also that the **category interpretation** of those facts is correct.

## Confirmed official facts for Tesco Balance Transfer

Use as pattern for balance-transfer products, not as universal facts:

- 0% interest on balance transfers guaranteed for 36 months.
- Balance transfer fee: 3.45%.
- 0% interest on money transfers for first 9 months.
- Money transfer fee: 3.99%.
- Collect Clubcard points almost every time you spend in and out of Tesco.
- Representative 24.9% APR variable.
- UK residents aged 18+; subject to status.

Do not add `No Annual Fee` unless confirmed by current official source/facts.

## Editorial gates to promote to runners/validators

### Benefits

- REC H3 benefits must be named real product features, not internal labels.
- Block generic benefit labels such as:
  - `Main benefit`
  - `Financial value`
  - `Usage convenience`
  - `Complementary benefit`
- For balance-transfer cards, expected benefit headings should look like:
  - `0% Balance Transfers for 36 Months`
  - `0% Money Transfers for 9 Months`
  - `Tesco Clubcard Points on Eligible Spending`
  - fee/repayment planning benefit where relevant.

### Voice

- Avoid addressing the audience as `reader`, `readers`, or `users` in editorial body copy.
- Prefer direct second person: `you`, `your balance`, `your repayment plan`, `your existing card debt`.
- Institutional phrasing is allowed only where legally/technically necessary; main copy should feel consultative.

### Category interpretation

- `points` alone is not enough to infer `travel rewards`.
- Only use `Travel rewards`, `Avios`, `lounge`, `hotel`, etc. when the official facts explicitly support travel value.
- `Clubcard points` should be treated as retailer/loyalty value, not travel value.

### Language consistency

- P1 contract/runners must not hardcode Portuguese section labels when `lang=en`.
- Block mixed-language output such as English article body with headings/details named `Benefícios` or `Quem deveria usar`.
- Details titles must be localized by article language.

### LazyBlocks and CTA

- REC and P1 must each contain exactly one `lazyblock/credit-card` unless a repair task explicitly asks otherwise.
- P1 card must appear once immediately after the introduction.
- REC final CTA must be a valid LazyBlock/button linking to the internal P1.
- P1 final CTA must be a valid LazyBlock/button linking to the official issuer URL.
- Do not accept a plain hyperlink or visible CSS/HTML artifact as a successful CTA render.

### Details blocks

- Details summaries should be visually scannable; prefer strong/bold summary text or equivalent CSS.
- Block empty H2/H3 headings and empty Details summaries.

### Featured image card visibility

- Featured images may be lifestyle/contextual, but the card must remain fully visible.
- No person/object/layer may cover card borders, corners, logo, or critical identity elements.
- Treat card occlusion as a visual failure even if the image file itself is not cropped.

## Balance-transfer P1 depth pattern

A P1 for a balance-transfer card should go beyond listing facts. It should explain:

- how moving an existing balance works;
- why the promotional 0% window matters;
- how to compare the transfer fee against interest avoided;
- what happens after the promotional period ends;
- why repayment discipline matters;
- who benefits most: people with existing card debt, people consolidating balances, people with a realistic repayment plan, and relevant Tesco customers when Clubcard points are confirmed.

Reduce repetitive regulatory warnings. Keep warnings, but tie them to concrete decisions and practical consequences.

```
