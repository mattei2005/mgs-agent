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
Content Operations            content skills, WordPress, sites.json, processes
Growth / Media Buying         dashboards de ads, Smart Bidding, planilhas, Ares
Creative Operations           Canva, ChatGPT, TopView.ai, Grok se aprovado, pastas dos gestores
Revenue / AdOps               Smart Bidding, ActiveView, Discord AdOps, reports
Finance / BI                  planilha financeira, Smart Bidding, FB BM, reports
Tech / WordPress / Infra      scripts, crons, patches, Hermes, WordPress, logs
Security / Access             authorized-users, 1Password, policies, audit log
```

## Fontes externas críticas

```text
Fonte externa                  Uso operacional
------------------------------ ------------------------------------------------
Smart Bidding                   Sites, campanhas, ROI, blocos, tecnologia, reports.
ActiveView                      Exceção ativa: openzed, cliquet e subdomínios.
Facebook Business Manager       Gastos de campanha e contas de anúncio.
Google Ads                      Campanhas/aquisição quando usado.
TikTok Ads                      Canal potencial/futuro para Ares.
Google / AdX                    Camada de pagamento/monetização via parceiros.
Canva                           Organização e entrega de criativos.
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
Smart Bidding vs ActiveView                    Smart Bidding, exceto openzed/cliquet/subdomínios.
Credencial em qualquer fonte vs 1Password       1Password.
Prompt de agente vs company-os/context          company-os/context.
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
