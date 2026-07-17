# MGS Digital Corp

> Status: visão geral v0.3
> Fonte-mãe: `context/company-os.md`
> Base operacional: `context/company-current-operating-model.md`

## O que é

MGS Digital Corp é uma empresa de mídia digital focada em publicação, aquisição paga, monetização display e operação de múltiplos sites/verticais.

O modelo é **publisher em escala**: vários sites micro-nichados geram receita por meio de tráfego pago, conteúdo, funis de aquisição e monetização com parceiros de AdOps.

A empresa opera como um sistema dividido por áreas:

```text
Área                         Função
---------------------------- -------------------------------------------------
Executive / Management        Direção, prioridades, governança e decisões.
Office / Follow-up             Cobrança e acompanhamento de tarefas pendentes.
Content Operations            Conteúdo, REC/P1, SEO e WordPress editorial.
Growth / Media Buying         Campanhas, tráfego pago, ROI e gestores.
Creative Operations           Criativos, vídeos, Canva, Drive e assets.
Revenue / AdOps               Monetização, blocos, redes e performance AdX.
Finance / BI                  ROI, gastos, receitas, comissões e fechamento.
Tech / WordPress / Infra      Sites, pixels, integrações, automações e agentes.
Security / Access             Permissões, credenciais, auditoria e acessos.
```

Este arquivo é a visão executiva da empresa. Para decisões detalhadas de rota, permissão e fonte de verdade, usar `context/company-os.md`, `context/routes.md`, `context/sources-of-truth.md` e `context/permissions-matrix.md`.

## Modelo de negócio

### Receita / monetização

A receita vem principalmente de publicidade display via redes AdX/Ad Manager operadas por parceiros do Google.

Smart Bidding e ActiveView são empresas parceiras do Google. Cada uma tem sua própria rede AdX/Ad Manager, onde os sites são adicionados e onde os blocos de anúncio são criados para o site começar a monetizar.

```text
Camada                        Uso
----------------------------- ------------------------------------------------
Smart Bidding                 Parceiro Google/AdX principal da MGS; rede onde
                              a maior parte dos sites deve ser gerenciada.
ActiveView                    Parceiro Google/AdX usado como exceção ativa para
                              openzed, cliquet e respectivos subdomínios.
Google AdX / Ad Manager       Ambiente onde parceiros adicionam sites, URLs e
                              criam blocos de anúncio.
Dashboard Smart Bidding       Dashboard mais completa; preferida para concentrar
                              gerenciamento dos sites.
Dashboard ActiveView          Dashboard alternativa da AV; menos usada pela MGS.
Blocos de anúncio             Criados/configurados dentro das redes dos parceiros.
SMS / Messenger / broadcast   Estratégias de retorno de usuário para os sites.
```

A MGS tem alguns sites dentro da rede da Smart Bidding e alguns sites dentro da rede da ActiveView. Como a dashboard da Smart Bidding é mais completa, a preferência operacional é concentrar o gerenciamento dos sites nela. Os sites `openzed`, `cliquet` e respectivos subdomínios ainda seguem no controle/tecnologia da ActiveView.

### Custo / aquisição

A aquisição vem principalmente de mídia paga e funis próprios.

```text
Canal / estratégia            Uso
----------------------------- ------------------------------------------------
Facebook Ads                  Campanhas para site, Messenger, quiz ou outros fluxos.
Google Ads                    Campanhas diretas para site/quiz quando usado.
TikTok Ads                    Canal potencial/futuro, não foco atual.
Messenger / ChatPion          Estratégia Facebook Ads com bot e páginas conectadas.
Quiz + SMS                    Tráfego direto com captura de telefone e SMS Funnel.
UTM_medium                    Código de atribuição por gestor.
```

Hoje os sources principais são Facebook Ads e Google Ads. TikTok Ads deve ficar documentado como canal potencial/futuro.

## Funis operacionais

### Via Facebook Ads direto para site

```text
Ad Facebook → clique → site MGS → conteúdo/REC/P1 → anúncios display → receita
```

### Via Google Ads direto para site ou quiz

```text
Ad Google → clique → site/quiz → conteúdo ou captura → anúncios display → receita
```

### Via Facebook Ads → Messenger / ChatPion

ChatPion, no contexto MGS, é operado via dashboard DigitalTrChat.

```text
1. Rodolfo/Geizian criam usuários por vertical no DigitalTrChat.
2. Gestor acessa o usuário da vertical.
3. Gestor conecta um segurador/perfil Facebook.
4. Dentro do segurador existem várias páginas Facebook.
5. Gestor configura os flows no Bot Manager.
6. Campanha Facebook Ads roda com objetivo Messenger.
7. Usuário clica no anúncio e abre o Messenger.
8. Bot envia drip nas primeiras 24h.
9. Depois entra broadcast configurado via Smart Bidding.
10. Mensagens levam o usuário para sites MGS monetizados.
```

Limite importante: **Ares não configura ChatPion/DigitalTrChat**. O cadastro de usuários é feito por Rodolfo e Geizian. Os gestores fazem a configuração operacional dos usuários/flows.

### Via quiz + SMS

```text
Ad Facebook/Google → quiz → captura nome/telefone/email → SMS Funnel → link → site MGS → anúncios display → receita
```

Rodolfo monta a estrutura e configuração do quiz/SMS. O SMS Funnel envia mensagens alguns minutos depois do cadastro, com CTA e link para um dos sites.

## Equipe operacional

```text
Pessoa / grupo                Função
----------------------------- ------------------------------------------------
Rodolfo                       CEO, estratégia, Finance/BI, WordPress, pixels,
                              arquitetura, Revenue/AdOps e comando da operação
                              de agentes AI.
Geizian                       Sócio de Rodolfo; acompanha gestores, sobe/testa
                              campanhas, apoia Creative e Revenue/AdOps.
Ially                         Gerente do escritório; cobra/acompanha tarefas
                              pendentes dos gestores e follow-up operacional.
Raquel                        Content Operations; acompanha Atena e conteúdo.
Kelly                         Creative Operations; cria criativos para gestores.
Gestores                      Operam campanhas, páginas, verticais e rotinas
                              definidas por Growth/Revenue/AdOps.
Smart Bidding                 Parceiro de monetização/AdOps e tecnologia.
ActiveView                    Parceiro AdX/Ad Manager em exceção ativa para
                              openzed, cliquet e respectivos subdomínios.
```

Gestores e códigos usados no `UTM_medium`:

```text
Gestor     Código
---------  ------
Icaro      g001
Geizian    g002
Isliago    g003
Joe        g004
Kelly      g005
Nicolas    g006
```

O `UTM_medium` permite atribuir receita/lucro por gestor, site e campanha.

## Agentes AI

Agentes AI são multiplicadores operacionais. Rodolfo comanda a operação dos agentes AI como um todo. Eles não substituem aprovação humana em áreas sensíveis; coordenam, executam dentro de escopo e escalam quando houver risco.

```text
Agente      Área                         Papel
----------  --------------------------- --------------------------------------
Zeus        Executive / Management       GM/orquestrador/auditor. Só Rodolfo
                                         conversa por padrão.
Atena       Content Operations           REC/P1, SEO, conteúdo e WordPress.
Ares        Growth / Media Buying        Campanhas, análise, ROI e operação
                                         de mídia dentro de escopo aprovado.
```

Regras principais:

```text
Zeus     Controle somente Rodolfo. Outras pessoas só entram se Rodolfo pedir.
Atena    Conteúdo/REC/P1/WordPress editorial com supervisão humana.
Ares     Criativos e campanhas. Pode gerenciar Drive de criativos aprovados;
         não configura ChatPion, quiz ou SMS Funnel.
```

Agentes seguem o desenho da empresa, não o contrário: cada agente deve ter área, fonte de verdade, escopo, permissão e escalação definidos antes de assumir operação real.

## Creative Operations e Drive

O fluxo de criativos deve preservar uma fonte oficial de assets aprovados.

```text
1. Kelly/Rodolfo/Geizian/gestor pede criativo ao Ares.
2. Ares cria variações, por exemplo feed e stories para Facebook/Instagram.
3. Kelly ou responsável avalia/aprova.
4. Ares salva o criativo aprovado na pasta correta do Google Drive.
5. Ares usa e gerencia os criativos em testes de campanhas.
```

Ares deve ter leitura/escrita no Drive de criativos aprovados para gerenciar os assets de campanha.

## Finance / BI

Finance e BI ficam sob responsabilidade do Rodolfo.

```text
Fonte / dado                   Uso
----------------------------- ------------------------------------------------
Planilha financeira             Fechamento mensal, ROI, gastos e receitas.
UTM_medium                      Atribuição por gestor.
Reports de parceiros            Receita, performance e validação externa.
Facebook/Google dashboards      Gastos, campanhas e performance.
```

Comissões dos gestores devem ser calculadas na planilha financeira. A regra operacional atual é:

```text
Base salarial                  R$ 3.000
Até R$ 100.000 lucro líquido    7% sobre lucro líquido
A partir de R$ 100.000          10% sobre lucro líquido
Regra                           Não soma salário + comissão; paga o maior valor.
```

## Escala atual

A escala exata deve ser consultada em `context/sites.md` e `data/sites.json`.

Em nível executivo, a MGS opera:

```text
Sites/verticais     Múltiplos sites e verticais por país/nicho/idioma.
Mercados            US, GB, DE, ES, MX, AR, ZA, CA, TR, BR e outros conforme operação.
Nichos              Cartões/crédito, games, jobs, carros e outras verticais ativas.
Modelo              Sites micro-nichados com aquisição paga e monetização display.
```

## Filosofia

### Escala por multiplicação, não por concentração

MGS opera múltiplos sites e verticais em paralelo. Se um site cai, outros seguem operando. Se um nicho satura, outros continuam sendo testados.

### Replicação + localização

Um playbook editorial, técnico e de monetização testado é replicado com adaptação local por mercado, idioma e nicho.

### Stack full-funnel verticalizada

A empresa opera conteúdo, tráfego, criativos, funis, monetização e análise financeira. Isso reduz dependência operacional e acelera testes.

### Leverage humano + agentes

A equipe humana toma decisões, aprova riscos e executa julgamento. Os agentes AI multiplicam capacidade, padronizam execução e reduzem trabalho repetitivo.

### Velocidade de iteração

O modelo permite testar sites, campanhas, criativos e funis rapidamente. O que funciona escala; o que não funciona é ajustado ou descontinuado.
