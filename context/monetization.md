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
                Tem dashboard própria, mas é menos usada pela MGS atualmente.
                Permanece como exceção ativa para openzed e seus subdomínios.
                Wavesbee e finanzas.wavesbee usam JBF/Smart Bidding. Cliquet e
                finanzas.cliquet carregam wrapper JBF, mas o runtime de produção
                ainda aponta para builders country-specific antigos que usam o
                GAM ActiveView `198073784`; o cutover para o GAM SB está incompleto.
Google / AdX    Camada de pagamento/monetização por trás das redes parceiras.
                Google paga as parceiras; as parceiras retiram o revenue share
                delas e repassam a MGS conforme reports/fechamento.
```

Regra canônica:

```text
Smart Bidding   Dashboard principal/preferida para gestão operacional.
ActiveView      Exceção ativa para sites ainda na tecnologia/controle AV.
```

---

## Fluxo de aprovação e monetização de site

```text
Etapa                           Responsável / fonte
------------------------------- ------------------------------------------------
Site criado/configurado          Rodolfo / Tech / WordPress
Conteúdo inicial publicado        Atena / Raquel / Content
Site enviado para parceiro        Rodolfo / Revenue / AdOps
Site adicionado à rede            Smart Bidding ou ActiveView
URLs/blocos configurados          Parceiro + interface operacional MGS
Blocos instalados no site         Rodolfo / Tech / WordPress
Receita começa a ser reportada    Dashboard Smart Bidding ou ActiveView
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

Mesmo quando há mais de uma rede parceira, a preferência operacional é usar Smart Bidding como dashboard central quando o site/tecnologia permitir.

Acessos operacionais: Rodolfo, Geizian e gestores conforme necessidade/escopo.

---

## Dashboard ActiveView

ActiveView também tem dashboard própria, mas é menos usada pela MGS atualmente.

Uso principal atual:

```text
openzed
subdomínios de openzed
```

Openzed e seus subdomínios continuam como exceção ativa enquanto usam tecnologia/controle da ActiveView. Wavesbee e finanzas.wavesbee usam JBF/Smart Bidding. Em 2026-08-21, Rodolfo instalou nos dois Cliquet os snippets manuais mínimos com os builders genéricos e desativou o Wrapper integrado antigo do tema. Após purge Cloudflare, o runtime público de `cliquet.com` e `finanzas.cliquet.com` ficou com exatamente um GPT e um builder genérico por site, zero builder legacy e `window.wrapper.config.general.networkCode=21922122164` em desktop/mobile; não houve mais slot ou request para a ActiveView `198073784`. A seleção do GAM SB e a remoção do stack AV estão confirmadas. A impressão/fill real continua bloqueada pelo detector IVT da JBF: além do VPS (`Crawler`, risk 9/10), o navegador residencial do Rodolfo retornou `network=21922122164`, `operation=facebook_us_cc_all-d`, `flow=facebook_us_cc`, `page_type=rec`, tags corretas, porém `bot_code=100`, `traffic=Crawler`, `risk=0` e nenhum slot. Isso caracteriza falso positivo/decisão do detector JBF, não erro de builder, GAM, operação ou tags; escalar à Smart Bidding/JBF antes de marcar throughput como provado.

---

## Blocos de anúncio / AdOps

Blocos de anúncio são parte central da monetização.

```text
Item                         Regra
---------------------------- ------------------------------------------------
Criação de blocos             Feita dentro da rede/parceiro correspondente.
Instalação no site             Rodolfo/Tech/WordPress conforme setup.
Ajustes de bloco/regra         Revenue / AdOps com parceiro e gestores.
Impacto em ROI                 Deve ser acompanhado por Finance / BI.
Mudança crítica                Escala Rodolfo.
```

Ajustes de blocos, precificação, regras, wrappers ou tecnologia de anúncio não devem ser tratados como alteração simples de conteúdo. Eles afetam receita, performance, UX e risco financeiro.

Canal operacional: a Smart Bidding mantém comunicação de AdOps no Discord. Rodolfo e gestores usam esses canais para acompanhar aprovação de sites, regras, precificação, performance e se o time de AdOps está executando os ajustes combinados.

---

## Receita, reports e Finance / BI

Fontes principais para fechamento financeiro:

```text
Fonte                         Uso
----------------------------- ------------------------------------------------
Smart Bidding reports          Receita/performance dos sites na rede SB.
ActiveView reports             Receita/performance dos sites ainda na AV.
Tráfego inválido               Percentual por site/rede para fechamento e risco.
Facebook Business Manager      Custo de mídia.
Google Ads                     Custo de mídia quando usado.
Planilha financeira Rodolfo    Fechamento, ROI, salários, comissões e despesas.
UTM_medium                     Atribuição de receita/lucro por gestor.
```

Finance / BI pertence ao Rodolfo. Reports de monetização alimentam a planilha financeira, junto com custos de mídia, despesas, salários e comissões.

Fechamento: Rodolfo confere reports Smart Bidding/ActiveView, gastos de mídia, tráfego inválido, comissões, salários e despesas. A planilha financeira validada por Rodolfo vence em caso de divergência sobre ROI ou comissão.

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
Mudança em openzed/subdomínios              Rodolfo / ActiveView
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
Receita reportada                Smart Bidding / ActiveView
Custo de mídia                   FB BM / Google Ads / dashboards de ads
ROI e fechamento                 Planilha financeira do Rodolfo
Atribuição por gestor             UTM_medium
```
