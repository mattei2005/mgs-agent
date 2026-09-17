# Monetização — MGS

> Status: proposta canônica v0.3
> Fonte-mãe: `context/company-os.md`
> Base operacional: `context/company-current-operating-model.md`

## Princípio

A receita principal da MGS vem de publicidade display nos sites próprios, monetizados por empresas parceiras Google que operam redes AdX/Ad Manager próprias.

Monetização deve sempre conectar quatro camadas:

```text
Site MGS -> rede parceira / blocos -> receita reportada -> Finance / BI
```

---

## Parceiros de monetização

```text
Parceiro        Papel operacional
--------------- ---------------------------------------------------------------
Smart Bidding   Empresa parceira Google com rede AdX/Ad Manager própria.
                É a central principal/preferida de gerenciamento da MGS,
                porque a dashboard é mais completa e concentra melhor os sites,
                blocos, reports, ROI, tecnologia, permissões e visão operacional.
ActiveView      Empresa parceira Google com rede AdX/Ad Manager própria.
                Rede retirada da operação ativa da MGS por decisão de Rodolfo.
                Nenhum site, subdomínio, landing ou rota customizada pode carregar
                loader, bloco ou GAM da ActiveView. A dashboard permanece somente
                como fonte histórica para períodos anteriores ao encerramento.
Google / AdX    Camada de pagamento/monetização por trás das redes parceiras.
                Google paga as parceiras; as parceiras retiram o revenue share
                delas e repassam a MGS conforme reports/fechamento.
```

Regra canônica:

```text
Smart Bidding   Dashboard principal/preferida para gestão operacional.
ActiveView      Retirada de todos os sites; uso apenas histórico/read-only.
```

---

## Fluxo de aprovação e monetização de site

```text
Etapa                           Responsável / fonte
------------------------------- ------------------------------------------------
Site criado/configurado          Rodolfo / Tech / WordPress
Conteúdo inicial publicado        Atena / Raquel / Content
Site enviado para parceiro        Rodolfo / Revenue / AdOps
Site adicionado à rede            Smart Bidding / parceiro atual aprovado
URLs/blocos configurados          Parceiro + interface operacional MGS
Blocos instalados no site         Rodolfo / Tech / WordPress
Receita começa a ser reportada    Dashboard da rede ativa aprovada
ROI consolidado                   Rodolfo / Finance / BI
```

Observação: cada parceira tem sua própria rede AdX/Ad Manager. O site precisa estar adicionado na rede correta e ter blocos de anúncio criados/configurados para monetizar.

---

## Dashboard Smart Bidding

A dashboard da Smart Bidding é a principal para a operação MGS.

Usos:

- visualizar receita/performance por site;
- acompanhar ROI e tecnologia dos sites concentrados/migrados;
- acompanhar blocos e configurações operacionais;
- consultar APIs/permissões quando aplicável;
- centralizar visão dos sites quando possível;
- apoiar análise de ROI com Growth e Finance;
- comunicar ajustes com o time de AdOps da Smart Bidding.

Smart Bidding é a referência operacional vigente para os sites migrados. Qualquer nova rede/parceiro exige decisão explícita de Rodolfo; ActiveView não é fallback.

Acessos operacionais: Rodolfo, Geizian e gestores conforme necessidade/escopo.

---

## Dashboard ActiveView — legado histórico

ActiveView não integra mais a operação ativa da MGS. A partir da decisão global de Rodolfo em 2026-09-17:

- nenhum site, subdomínio, landing, plugin, rota customizada ou cache público deve carregar `scr.actview.net`;
- nenhum runtime deve solicitar os GAMs/blocos legados associados à AV, incluindo `198073784` e `22048006626`;
- blocos Ad Inserter, configurações de plugin, builders, caches e templates residuais são drift técnico a auditar e remover;
- a dashboard AV permanece somente para consulta histórica e conciliação de períodos anteriores.

Histórico superseded: Openzed/subdomínios já foram exceção ativa; Zuout e outros funis já usaram contratos AV; Cliquet teve builders antigos apontando para `198073784`. Essas exceções não permanecem autorizadas.

---

## Blocos de anúncio / AdOps

Blocos de anúncio são parte central da monetização.

```text
Item                         Regra
---------------------------- ------------------------------------------------
Criação de blocos             Feita dentro da rede/parceiro correspondente.
Instalação no site             Rodolfo/Tech/WordPress conforme setup.
Ajustes de bloco/regra         Revenue / AdOps com parceiro e gestores.
Cadastro de URLs/produtos e `jbf_operation` na Smart Bidding  Time de AdOps da Smart Bidding.
Impacto em ROI                 Deve ser acompanhado por Finance / BI.
Mudança crítica                Escala Rodolfo.
```

Ajustes de blocos, precificação, regras, wrappers ou tecnologia de anúncio não devem ser tratados como alteração simples de conteúdo. Eles afetam receita, performance, UX e risco financeiro.

O cadastro de URLs/produtos no catálogo da Smart Bidding e a geração/preenchimento de `jbf_operation` pertencem ao time de AdOps. Zeus e os demais agentes MGS não devem assumir essa função nem oferecer cadastro substitutivo; quando Rodolfo ordenar a criação de pools antes do trabalho de AdOps, podem gravar as URLs públicas validadas com operação vazia, reportar o estado `AdOps pendente` e aguardar a atuação do time. Depois, somente fazem conferência/readback se Rodolfo solicitar.

Canal operacional: a Smart Bidding mantém comunicação de AdOps no Discord. Rodolfo e gestores usam esses canais para acompanhar aprovação de sites, regras, precificação, performance e se o time de AdOps está executando os ajustes combinados.

---

## Receita, reports e Finance / BI

Fontes principais para fechamento financeiro:

```text
Fonte                         Uso
----------------------------- ------------------------------------------------
Smart Bidding reports          Receita/performance dos sites na rede SB.
ActiveView reports             Histórico anterior à retirada global da AV.
Tráfego inválido               Percentual por site/rede para fechamento e risco.
Facebook Business Manager      Custo de mídia.
Google Ads                     Custo de mídia quando usado.
Planilha financeira Rodolfo    Fechamento, ROI, salários, comissões e despesas.
UTM_medium                     Atribuição de receita/lucro por gestor.
```

Finance / BI pertence ao Rodolfo. Reports de monetização alimentam a planilha financeira, junto com custos de mídia, despesas, salários e comissões.

Fechamento: Rodolfo confere reports da rede ativa e, quando o período exigir, o histórico ActiveView; também confere gastos de mídia, tráfego inválido, comissões, salários e despesas. A planilha financeira validada por Rodolfo vence em caso de divergência sobre ROI ou comissão.

---

## Relação com Growth / Media Buying

Growth compra tráfego; Monetização mede e otimiza a receita gerada nos sites.

```text
Growth / Ares / gestores       Campanhas, custo, tráfego, UTMs.
Revenue / AdOps                Blocos, reports, dashboards, parceiros.
Finance / BI                   ROI, lucro líquido, fechamento e comissões.
```

Ares pode analisar ROI e campanhas, mas não altera blocos AdOps nem configura rede/parceiro sem escopo e aprovação. Mudanças com impacto financeiro escalam para Rodolfo/Geizian.

---

## Canais adicionais de monetização / reaproveitamento

Além de display, a MGS pode usar camadas complementares conforme estratégia:

```text
Canal                         Uso
----------------------------- ------------------------------------------------
Push notifications             Retargeting/reaproveitamento quando ativo.
SMS marketing                  Estratégia via captura/quiz/SMS Funnel quando ativo.
Email marketing                Reaproveitamento/opt-in quando ativo.
ChatPion/Messenger             Leva usuário de volta para sites MGS via fluxos.
```

Esses canais podem influenciar receita, mas a fonte primária de monetização estrutural continua sendo display via parceiros Google/AdX/Ad Manager.

---

## Estratégias de receita em sites

```text
Estratégia                    Objetivo
----------------------------- ------------------------------------------------
REC -> P1                     Fluxo editorial/comercial de recomendação.
Paginação/interstitial         Aumentar oportunidade de impressão quando aprovado.
Blocos display                 Monetização principal via parceiros.
Push/SMS/email                 Reaproveitamento e retorno de usuários.
```

Qualquer estratégia deve respeitar experiência do usuário, risco de tráfego inválido, regras dos parceiros e impacto financeiro.

---

## Escalonamento

```text
Situação                                  Escalar para
----------------------------------------- -----------------------------------
Queda forte de receita                     Rodolfo / Revenue / Finance
Tráfego inválido elevado                   Rodolfo / parceiro / gestores
Bloco quebrado ou site sem anúncio          Rodolfo / Tech / AdOps
Alteração de rede/parceiro                  Rodolfo
Vestígio ou request ActiveView encontrado    Rodolfo / Tech / AdOps
Mudança de regra com impacto em ROI         Rodolfo / Geizian
Divergência entre dashboard e planilha       Rodolfo / Finance
```

---

## Fontes de verdade relacionadas

```text
Tipo de dado                   Fonte
------------------------------ ------------------------------------------------
Sites/verticais conceituais     context/sites.md
Config técnica dos sites         data/sites.json
Parceiros/regras AdOps           context/monetization.md + dashboards externos
Receita reportada                Rede ativa; ActiveView somente histórico
Custo de mídia                   FB BM / Google Ads / dashboards de ads
ROI e fechamento                 Planilha financeira do Rodolfo
Atribuição por gestor             UTM_medium
```
