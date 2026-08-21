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
Creative Ops + Growth /      Rodolfo + Geizian +       Criativos, Drive, campanhas, arbitragem,
Media Buying                   Kelly + gestores          custos, aquisição e ROI.
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

Facebook Ads, Google Ads, criativos, Canva/Drive, referências, campanhas, tráfego direto, análise, custos e ROI pertencem ao Ares dentro do escopo aprovado. ChatPion, quiz e SMS Funnel continuam fora da configuração do Ares.

Rodolfo também atua diretamente na configuração e direção estratégica da área, incluindo a preparação do Ares. Geizian acompanha gestores no dia a dia. Rodolfo acompanha visão geral, budget, ROI e impacto financeiro.

## Creative Operations

Criativos estáticos, vídeos, referências, assets, Canva, Google Drive, providers aprovados e inventário são o módulo Creative Ops do Ares.

Kelly é a dona humana da frente criativa. Geizian orienta e apoia. Ares cria/organiza/trata os assets, controla reserva/elegibilidade e conecta o resultado às campanhas sem handoff entre agentes.

## Revenue / AdOps

Smart Bidding, ActiveView, AdManager/AdX, aprovação de sites, blocos de anúncio, precificação, regras e Discord AdOps.

Regra atual: Smart Bidding e ActiveView são parceiros Google/AdX. A dashboard da Smart Bidding é a central principal de gerenciamento por ser mais completa. ActiveView permanece como exceção ativa para `openzed` e seus subdomínios; Cliquet, finanzas.cliquet, Wavesbee e finanzas.wavesbee usam JBF/Smart Bidding. Rodolfo, Geizian e gestores atuam na interface operacional com AdOps, blocos, regras e performance.

## Finance / BI

Planilha financeira, fechamento mensal, gastos, receita, tráfego inválido, comissões, salários, despesas, relatórios e ROI consolidado.

Rodolfo é o dono atual. A camada de BI futura deve conectar gasto de mídia, receita por site/vertical, tráfego inválido e fechamento mensal.

## Tech / WordPress / Infra

WordPress técnico, home, categorias, plugins, pixels, VPS, Hermes, bots, crons, scripts, patches, logs e monitoramento.

Zeus coordena e reporta, mas mudanças críticas em produção continuam dependendo de Rodolfo.

## Security / Access

Credenciais, tokens, permissões, dashboards, APIs, hardening, política de risco e autorizações externas.

`data/authorized-users.json` continua sendo fonte operacional de permissões. Credenciais vivem no 1Password e nunca devem ser expostas em chat.
