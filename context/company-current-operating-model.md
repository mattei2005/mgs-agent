# MGS — Operating Model Atual

> Status: fonte primária do CEO, capturada a partir da explicação do Rodolfo.  
> Dono da informação: Rodolfo Mattei.  
> Uso: base para redesenhar a arquitetura MGS OS antes de reorganizar agentes, arquivos e rotas.

---

## 1. Sócios e liderança

```text
Pessoa        Papel atual
------------ ---------------------------------------------------------------
Rodolfo       CEO; gestão geral, financeiro, estrutura, WordPress, pixels,
              aprovação/relacionamento com redes, estratégia, arquitetura e
              comando da operação dos agentes AI.
Geizian       Sócio; acompanha e gerencia os gestores, rotina diária de
              campanhas, custos e performance.
```

---

## 2. Estrutura humana atual

```text
Grupo                         Responsabilidade
----------------------------- ------------------------------------------------
Raquel                        Produção/conteúdo; cuida da Atena no futuro.
Gestores                      Gestão de conteúdo/campanhas/sites; acompanham
                              campanhas, custos, ROI e contato operacional.
Kelly                         Criativos; produz assets em ferramentas AI/Canva
                              para gestores usarem nas campanhas.
Ially                         Gerente do escritório; cobra e acompanha tarefas
                              pendentes dos gestores e follow-up operacional.
Rodolfo + Geizian + gestores  Acessam dashboards de monetização/ROI/campanhas.
```

Gestores e códigos usados em `UTM_medium` para rastrear receita/lucro por gestor:

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

---

## 3. Sites, verticais e conteúdo

A MGS opera mais de 30 sites em vários países, nichos e idiomas. Cada site pode ter uma ou mais verticais.

Exemplo de vertical:

```text
Site      País             Nicho              Idioma
-------- ----------------- ------------------ -------
EggBev    GB/Reino Unido   Credit Cards/CC    EN
```

Fluxo estrutural de site:

```text
Etapa                         Descrição
----------------------------- ------------------------------------------------
1. WordPress                  Configurar instalação, tema/home, plugins e base.
2. Categorias                 Criar categorias conforme vertical/nicho.
3. Conteúdo REC/P1            Raquel publica conteúdo comercial principal.
4. Artigos SEO                Quando há mais categorias, publicar artigos SEO
                              de aproximadamente 1.200 palavras para preencher.
5. Conteúdo diário            Raquel mantém produção e preenchimento diário.
6. Aprovação em rede          Sites são enviados para aprovação nas redes de
                              AdManager/AdX via parceiros.
```

---

## 4. Monetização e redes

A MGS trabalha com redes/parceiros de AdManager/AdX, principalmente Smart Bidding e ActiveView. As duas são empresas parceiras do Google com suas próprias redes AdX/Ad Manager, onde sites são adicionados e blocos de anúncio são criados.

```text
Rede/empresa       Papel atual
----------------- -------------------------------------------------------------
Smart Bidding      Parceiro Google/AdX principal. Dashboard com sites,
                   campanhas, ROI, tecnologia, relatórios, blocos de anúncio,
                   APIs, permissões e gerenciamento preferencial dos sites MGS.
                   Também tem time de AdOps no Discord.
ActiveView         Rede/tecnologia ainda relevante em alguns sites. A maior
                   parte foi migrada/concentrada na Smart Bidding.
Google/AdX         Origem dos pagamentos via ecossistema de monetização.
```

### 4.1 Dashboard Smart Bidding

A dash da Smart Bidding é fonte operacional principal de monetização/ROI.

Observação: a lista abaixo é exemplificativa, não exaustiva. A tecnologia deles tem mais features além das listadas aqui.

Exemplos de uso:

- lista de sites;
- campanhas;
- ROI;
- features de análise;
- criação/gestão de blocos de anúncio;
- API/permissões;
- tecnologia concentrada dos sites migrados;
- relatórios e dados operacionais enviados para fechamento financeiro.

Acessos: Rodolfo, Geizian e gestores.

### 4.2 ActiveView — exceção atual

Os únicos sites que ainda não tiveram a tecnologia migrada para Smart Bidding são:

```text
- openzed
- cliquet
- respectivos subdomínios
```

Todo o restante está concentrado/operado via Smart Bidding, ainda que tenha origem histórica em ActiveView.

---

## 5. AdOps e precificação

A Smart Bidding mantém canais no Discord com time de AdOps. Rodolfo e gestores usam esses canais para acompanhar:

- aprovação dos sites;
- funcionamento das regras;
- alteração de precificação dos blocos de anúncio;
- performance da monetização;
- se o time de AdOps está trabalhando corretamente;
- ajustes de preço e regras dos blocos.

Essa área pertence à camada de **Monetização / AdOps / Revenue Operations**.

---

## 6. Aquisição, arbitragem e campanhas

Google Ads e Facebook Ads são canais onde a MGS compra tráfego para enviar para os sites. A estratégia central é arbitragem: comprar tráfego, monetizar nos sites e medir ROI.

Canais/estratégias atuais:

```text
Canal/estratégia       Uso
--------------------- ----------------------------------------------------------
Facebook Ads           Compra de tráfego para arbitragem e envio aos sites.
Google Ads             Compra de tráfego para arbitragem e envio aos sites.
ChatPion modificado    Estratégia Facebook/Messenger. O developer da Smart
                       Bidding modificou o ChatPion inteiro para a operação.
Quiz                   Estratégia usada em Facebook/Google; pode capturar e-mail,
                       SMS ou enviar direto sem captura.
Tráfego direto         Estratégia usada em Google e Facebook.
E-mail                 Estratégia/camada de monetização e reaproveitamento.
SMS                    Estratégia/camada de monetização e reaproveitamento;
                       também usado em nichos como financiamento de carro.
TikTok                 Canal potencial/futuro para Ares se operar campanhas.
```

Fluxo operacional:

1. Kelly cria criativos com ferramentas AI e Canva.
2. Kelly sobe os criativos na pasta Canva do gestor.
3. Gestor acessa a pasta, pega os criativos e sobe campanhas.
4. Geizian acompanha gestores diariamente.
5. Rodolfo acompanha visão geral, custos, ROI e financeiro.

---

## 7. Criativos e ferramentas AI

Ferramentas citadas:

```text
Ferramenta       Uso atual
--------------- ---------------------------------------------------------------
ChatGPT          Criativos estáticos e apoio criativo.
TopView.ai       Criação de vídeos.
Canva            Organização/entrega de criativos para gestores.
Grok             Ainda não testado; candidato futuro por possível integração
                 com Hermes/API.
Outras AIs       Ferramentas futuras possíveis para criação de criativos.
```

Necessidade futura: agente especializado em criação de criativos, com acesso controlado a APIs/ferramentas compatíveis.

---

## 8. Financeiro e fechamento

Rodolfo é responsável pelo financeiro.

Ciclo mensal:

```text
Período analisado           Dia 1 ao dia 30
Pagamento Google            Entre dia 21 e dia 23
Fonte de controle           Planilha financeira do Rodolfo
```

Conferências feitas por Rodolfo:

- gastos no Facebook Business Manager;
- gastos por conta de anúncio;
- tráfego inválido por site;
- relatórios Smart Bidding;
- relatórios ActiveView;
- percentual de tráfego inválido enviado pela Smart Bidding/ActiveView, pois
  a monetização usa o AdManager/AdX deles;
- comissões;
- salários;
- despesas da empresa;
- fechamento e pagamentos.

Google paga Smart Bidding e ActiveView. Smart Bidding/ActiveView retiram o revenue share deles e pagam a MGS.

Rodolfo recebe os relatórios, alimenta a planilha com gastos, receitas, despesas, salários e comissões. A planilha calcula ROI e o fechamento detalhado. No fim do mês, a empresa sabe quanto cada gestor recebe, quanto deve ser pago em despesas e quanto os sócios recebem.

Regra atual de remuneração dos gestores:

```text
Base salarial                 R$ 3.000
Até R$ 100.000 lucro líquido   7% sobre lucro líquido
A partir de R$ 100.000         10% sobre lucro líquido
Regra contra duplicidade       Não paga salário + comissão; paga o maior valor.
Exemplo R$ 45.000 lucro líquido 45.000 * 7% = R$ 3.150; recebe R$ 3.150.
Ponto de virada aproximado     ~R$ 42.857 de lucro líquido para superar R$ 3.000.
```

Essa regra pertence à camada **Finance / BI / Executive Reporting**.

---

## 9. Rotina de gestão

A empresa tem reuniões diárias internas. Nessas reuniões são acompanhados:

- campanhas;
- custos;
- performance;
- ROI;
- gestores;
- problemas operacionais;
- demandas de sites/conteúdo/campanhas.

---

## 10. Agentes atuais e planejados

```text
Agente               Papel pretendido
------------------- -----------------------------------------------------------
Zeus                 Manager geral de tudo; olha todos os agentes, faz updates,
                     instalações, verifica problemas, dá indicações de melhoria,
                     governa, audita, roteia e reporta.
Atena                Gestora/agente de conteúdo; produz conteúdos. Raquel deve
                     cuidar/supervisionar.
Ares                 Agente unificado de Creative Operations + mídia paga/aquisição:
                     criação/tratamento/inventário de criativos, Drive, Facebook Ads,
                     Google Ads e demais canais aprovados. Não configura ChatPion,
                     DigitalTrChat, quiz ou SMS Funnel.
```

---

## 11. Implicação para a nova arquitetura

A arquitetura da MGS deve ser desenhada por áreas reais da empresa, não apenas por agentes.

Áreas candidatas derivadas da operação real:

```text
Área alvo                     Origem operacional
----------------------------- ------------------------------------------------
Executive / Management        Rodolfo, Geizian, reuniões, decisões, estratégia
Content Operations            Raquel, gestores, REC/P1, SEO, WordPress conteúdo
Creative Ops + Growth        Kelly, gestores, Ares, Drive, providers criativos, Facebook/Google Ads
Acquisition systems           ChatPion, quiz e SMS sob Rodolfo/Geizian/gestores
Revenue / AdOps               Smart Bidding, ActiveView, AdManager, AdX, blocos
Finance / BI                  Rodolfo recebe relatórios, alimenta planilhas,
                              acompanha ROI, gastos, receitas, custos
Tech / WordPress / Infra      Rodolfo gerencia sites, WordPress, servidor,
                              instalações, plugins, pixels, Hermes e scripts
Security / Access             1Password, permissões, credenciais, acesso a
                              dashboards/APIs
```

---

## 12. Regra de migração

Este documento é uma captura da operação real. Ele deve orientar a reorganização, mas não substitui automaticamente os arquivos existentes.

Próxima etapa: criar o diagrama-alvo do MGS OS e depois o inventário de migração arquivo por arquivo.
