# MGS Digital Corp

> Status: visão geral v0.2
> Fonte-mãe: `context/company-os.md`
> Base operacional: `context/company-current-operating-model.md`

## O que é

MGS Digital Corp é uma empresa de mídia digital focada em publicação, aquisição paga, monetização display e operação de múltiplos sites/verticais.

O modelo é **publisher em escala**: vários sites micro-nichados geram receita por meio de tráfego pago, conteúdo, funis de aquisição e monetização com parceiros de AdOps.

A empresa opera como um sistema dividido por áreas:

```text
Área                         Função
---------------------------- -------------------------------------------------
Content Operations            Conteúdo, REC/P1, SEO e WordPress editorial.
Growth / Media Buying         Campanhas, tráfego pago, ROI e gestores.
Creative Operations           Criativos, vídeos, Canva, Drive e assets.
Revenue / AdOps               Monetização, blocos, redes e performance AdX.
Finance / BI                  ROI, gastos, receitas, comissões e fechamento.
Tech / WordPress / Infra      Sites, pixels, integrações, automações e agentes.
Security / Access             Permissões, credenciais, auditoria e acessos.
Executive / Management        Direção, prioridades, governança e decisões.
```

## Modelo de negócio

### Receita / monetização

A receita vem principalmente de publicidade display e monetização via parceiros.

```text
Camada                        Uso
----------------------------- ------------------------------------------------
Smart Bidding                 Central principal de monetização/AdOps.
Google AdX / Ad Manager       Camada de monetização via parceiros.
ActiveView                    Exceção ativa para openzed, cliquet e subdomínios.
Blocos de anúncio             Configurados por parceiros/AdOps nos sites.
SMS / Messenger / broadcast   Estratégias de retorno de usuário para os sites.
```

Smart Bidding é a central principal. ActiveView permanece como exceção operacional para `openzed`, `cliquet` e respectivos subdomínios.

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
                              arquitetura, Revenue/AdOps e configuração de Ares.
Geizian                       Parceiro/gestor operacional; acompanha gestores,
                              sobe/testa campanhas, apoia Creative e Revenue/AdOps.
Raquel                        Content Operations; acompanha Atena e conteúdo.
Kelly                         Creative Operations; cria criativos para gestores.
Gestores                      Operam campanhas, páginas, criativos e verticais.
Smart Bidding                 Parceiro de monetização/AdOps e tecnologia.
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

Agentes AI são multiplicadores operacionais. Eles não substituem aprovação humana em áreas sensíveis; coordenam, executam dentro de escopo e escalam quando houver risco.

```text
Agente      Área                         Papel
----------  --------------------------- --------------------------------------
Zeus        Executive / Management       GM/orquestrador/auditor. Só Rodolfo
                                         conversa por padrão.
Atena       Content Operations           REC/P1, SEO, conteúdo e WordPress.
Ares        Growth / Media Buying        Campanhas, análise, ROI e operação
                                         de mídia dentro de escopo aprovado.
Hera        Creative Operations          Criativos, vídeos, assets e Drive.
```

Regras principais:

```text
Zeus     Controle somente Rodolfo. Outras pessoas só entram se Rodolfo pedir.
Atena    Conteúdo/REC/P1/WordPress editorial com supervisão humana.
Ares     Campanhas. Não configura ChatPion, quiz ou SMS Funnel.
Hera     Criativos. Pode gerenciar Drive de criativos aprovados.
```

## Creative Operations e Drive

O fluxo de criativos deve preservar uma fonte oficial de assets aprovados.

```text
1. Kelly/Rodolfo/Geizian/gestor pede criativo.
2. Hera cria variações, por exemplo feed e stories para Facebook/Instagram.
3. Kelly ou responsável avalia/aprova.
4. Hera salva o criativo aprovado na pasta correta do Google Drive.
5. Ares acessa o Drive para usar e gerenciar criativos em testes de campanhas.
```

Ares e Hera devem ter leitura/escrita no Drive de criativos aprovados para conseguir gerenciar os assets de campanha.

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
