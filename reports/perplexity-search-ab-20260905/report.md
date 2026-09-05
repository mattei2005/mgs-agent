# Comparativo A/B — Hermes Web nativo vs Perplexity Search API

**Data:** 2026-09-05  
**Escopo:** políticas de publicidade de produtos financeiros na Meta e no Google para os mercados MGS (US, CA, GB, MX, AR e ZA).  
**Métodos comparados:**

- **Método gratuito atual:** DDGS para descoberta + Keenable para extração.
- **Método Perplexity:** provider nativo `plugins/web/perplexity` do Hermes, usando a Search API; Keenable foi mantido como extrator comum na fase de leitura das fontes para isolar a qualidade da busca.

## Conclusão executiva

A Perplexity foi materialmente melhor para pesquisa profunda multifuente. Ela não substitui o modelo que analisa e redige, mas encontrou mais fontes oficiais únicas, cobriu muito melhor a documentação do Google, respondeu sem falhas iniciais e foi mais rápida no lote observado.

O DDGS continua valioso como fallback gratuito e foi especialmente forte em buscas `site:` muito específicas da Meta. Portanto, a decisão recomendada não é remover o método gratuito: é usar **Perplexity como busca preferencial para pesquisas profundas/atuais** e manter **DDGS + Keenable como fallback e contraprova**.

## Metodologia

Foram executadas oito consultas idênticas em cada backend, com limite de dez resultados por consulta. As consultas cobriram:

1. Meta Business Help e categoria especial de produtos financeiros;
2. Meta for Developers e mudanças 2025–2026;
3. políticas financeiras e verificação no Google Ads;
4. requisitos combinados nos seis países MGS;
5. mudanças recentes 2025–2026;
6. Meta para México e Argentina;
7. Meta para Reino Unido, Canadá e África do Sul;
8. Google para México, Argentina, Canadá, África do Sul e Reino Unido.

URLs foram deduplicadas também por forma canônica para remover variações triviais de idioma, tracking, `.md` e barra final. Dez páginas oficiais foram extraídas integralmente por um único extrator para impedir que diferenças de leitura fossem confundidas com diferenças de busca.

## Resultado quantitativo

### DDGS + Keenable

- Consultas: 8.
- Sucesso inicial: 7/8.
- Uma consulta exata ao domínio de políticas do Google retornou “No results found”; a repetição automática funcionou e recuperou sete resultados.
- Resultados iniciais: 70.
- URLs canônicas únicas: 42.
- Ocorrências de fontes oficiais Meta/Google: 46.
- Fontes oficiais canônicas únicas: 24.
- Ocorrências oficiais Meta: 41.
- Ocorrências oficiais Google: 5.
- Fontes oficiais entre os três primeiros resultados: 17.
- Tempo médio observado: 2,109 s por consulta.

### Perplexity Search API

- Consultas: 8.
- Sucesso inicial: 8/8.
- Resultados: 80.
- URLs canônicas únicas: 51.
- Ocorrências de fontes oficiais Meta/Google: 54.
- Fontes oficiais canônicas únicas: 30.
- Ocorrências oficiais Meta: 32.
- Ocorrências oficiais Google: 22.
- Fontes oficiais entre os três primeiros resultados: 15.
- Tempo médio observado: 1,350 s por consulta.

### Diferença observada

- Perplexity entregou 21,43% mais URLs canônicas únicas.
- Entregou 25% mais fontes oficiais canônicas únicas.
- Entregou 17,39% mais ocorrências de fontes oficiais.
- Encontrou 4,4 vezes mais resultados oficiais do Google.
- Foi 35,99% mais rápida na média observada.
- DDGS teve ligeira vantagem no número bruto de fontes oficiais dentro do top 3 e encontrou mais ocorrências Meta, sobretudo nas buscas `site:facebook.com`.
- Apenas 17 URLs canônicas apareceram nos dois conjuntos: os backends são complementares, não equivalentes.

## Limitações do comparativo

- Amostra pequena e concentrada em um único tema; não é benchmark universal.
- A busca nativa Perplexity no Hermes usa `search_context_size=low`; ela fornece resultados e snippets, não uma resposta Deep Research pronta.
- Perplexity devolveu várias versões localizadas da mesma página Meta. A deduplicação canônica removeu esse ganho artificial.
- Em um smoke isolado, o primeiro resultado da Perplexity foi um terceiro, ConductAtlas, apesar do termo “official”. Portanto, Perplexity melhora descoberta, mas não elimina validação de domínio e fonte primária.
- Latência pode variar com rede, cache e carga dos provedores.
- Custo estimado do canário: dez requisições Search API bem-sucedidas × US$ 0,005 = **US$ 0,05**. O painel de billing permanece a fonte final do valor efetivamente debitado.

# Pesquisa profunda — achados operacionais

## Meta Ads

### Mudança estrutural

A Meta introduziu `FINANCIAL_PRODUCTS_SERVICES` em outubro de 2024 e declarou que esse valor substituiria `CREDIT` em 14 de janeiro de 2025. Desde essa data, a categoria é obrigatória para campanhas de produtos e serviços financeiros quando o anunciante está baseado nos Estados Unidos ou mostra anúncios para pessoas nos Estados Unidos. A Meta informa que anúncios podem ser rejeitados se a categoria apropriada não for escolhida.

Fonte: [Meta for Developers — Special Ad Categories](https://developers.facebook.com/documentation/ads-commerce/marketing-api/audiences/special-ad-category/)

### Campo obrigatório e segmentação

Toda criação de campanha via Marketing API exige `special_ad_categories`; quando nenhuma categoria especial se aplica, deve ser usado `NONE` ou array vazio. Quando uma categoria especial é selecionada, também é necessário definir `special_ad_category_country`.

Anunciantes baseados nos Estados Unidos ou que alcançam Estados Unidos, Canadá ou Europa sofrem limitações de audiência para oportunidades de produtos financeiros. Empresas fora desses mercados e alcançando apenas públicos fora deles ainda precisam enviar o campo, mas podem optar por `NONE` ou aderir voluntariamente à categoria.

Fonte: [Meta for Developers — Special Ad Categories](https://developers.facebook.com/documentation/ads-commerce/marketing-api/audiences/special-ad-category/)

### Regras gerais para crédito, empréstimo e seguro

A Meta permite anúncios de cartão de crédito, empréstimos de longo prazo e seguros desde que:

- segmentem somente maiores de 18 anos;
- apresentem disclosures exigidos por lei;
- não solicitem diretamente informações pessoais ou financeiras sensíveis;
- possuam licenças/autorizações quando exigidas no país de destino.

São proibidos, entre outros:

- payday loans;
- adiantamento de salário;
- bail bonds;
- empréstimos quitados integralmente em 90 dias ou menos;
- opções binárias, CFDs e ICOs;
- práticas enganosas em consolidação, perdão ou refinanciamento estudantil.

Para investimentos direcionados aos Estados Unidos, a Meta também proíbe anúncios que levem a interação com o anunciante por mensagens diretas dentro ou fora da plataforma.

Fontes: [Meta — Financial and Insurance Products and Services](https://transparency.meta.com/policies/ad-standards/restricted-goods-services/financial-services/) e [Meta — Prohibited Financial Products and Services](https://transparency.meta.com/policies/ad-standards/deceptive-content/prohibited-financial-products-and-services/)

## Google Ads

### Disclosures gerais

Landing pages de produtos ou serviços financeiros devem exibir de forma clara e imediatamente visível:

- endereço físico da empresa que oferece o produto ou serviço;
- todas as taxas associadas;
- links de acreditação, endosso ou vínculo governamental quando essa associação for afirmada ou sugerida.

Essas informações não podem ficar escondidas em hover, outra aba ou link secundário.

Fonte: [Google Ads — Financial products and services disclosures](https://support.google.com/adspolicy/answer/15187149?hl=en)

### Empréstimos pessoais

O Google permite somente empréstimos pessoais cuja quitação integral ocorra em 61 dias ou mais. A regra cobre credores, geradores de leads e intermediários. A landing page também deve informar:

- prazo mínimo e máximo de pagamento;
- APR máximo ou taxa equivalente conforme a lei local;
- exemplo representativo do custo total, incluindo taxas.

Nos Estados Unidos, empréstimos pessoais com APR de 36% ou mais são proibidos, inclusive para lead generators e conectores de terceiros.

Fonte: [Google Ads — Financial products and services](https://support.google.com/adspolicy/answer/2464998?hl=en)

### Verificação financeira por país

A lista oficial de verificação contém 41 mercados. Entre os seis mercados MGS avaliados, apenas o **Reino Unido** aparece nessa lista. O Google exige verificação separada por local e pode solicitar licença, registro e outras informações da empresa.

No Reino Unido, anunciantes de serviços financeiros devem ser autorizados pela FCA, ser terceiro aprovado por empresa autorizada ou se enquadrar em uma exceção documentada. A exigência cobre todos os formatos e assets; afiliados e agências de lead generation aparecem explicitamente como possíveis “approved third parties”.

México, Argentina, Canadá, África do Sul e Estados Unidos não apareceram na lista oficial recuperada. Isso não elimina a obrigação de cumprir as regras globais do Google, políticas específicas do produto, verificação geral do anunciante ou legislação local.

Fontes: [Google — Relevant Regulators and Enforcement Dates](https://support.google.com/adspolicy/answer/12390454?hl=en) e [Google — UK Financial Services Verification](https://support.google.com/adspolicy/answer/15332527?hl=en&co=GENIE.CountryCode=GB)

### Mudanças recentes

- Em junho de 2026, o Google anunciou verificação para 24 novos mercados do Espaço Econômico Europeu, com enforcement gradual a partir de 23 de julho de 2026. Essa expansão não inclui os seis países MGS analisados; o Reino Unido já possuía regime próprio.
- Em junho de 2025, serviços de dívida passaram a integrar a verificação financeira na Austrália, Brasil, Alemanha, Irlanda, Coreia do Sul e Espanha. Nenhum dos seis mercados deste teste foi adicionado por esse aviso.

Fontes: [Google — New Verification Requirements, June 2026](https://support.google.com/adspolicy/answer/17127726?hl=en) e [Google — Debt Services Verification Update, June 2025](https://support.google.com/adspolicy/answer/16292878?hl=en)

# Aplicação aos mercados MGS

- **Estados Unidos:** Meta `FINANCIAL_PRODUCTS_SERVICES` obrigatória e targeting limitado; Google proíbe personal loans com APR ≥36%; regra Meta adicional impede investimentos que direcionem para conversa privada.
- **Canadá:** restrições de audiência Meta para oportunidades financeiras; Google aplica disclosures e regras globais, mas Canadá não apareceu na lista recuperada de verificação financeira por localização.
- **Reino Unido:** restrições Meta para Europa; no Google, verificação financeira/FCA é o principal gate e alcança afiliados/lead generators como terceiros aprovados.
- **México, Argentina e África do Sul:** a documentação Meta permite optar por `NONE` fora de US/Canadá/Europa quando a campanha não adere à categoria, mas o campo continua obrigatório na API; as regras gerais Meta de 18+, licença, disclosures e produtos proibidos continuam. No Google, os três não apareceram na lista de verificação financeira por localização, mas disclosures, regras por produto e legislação local continuam obrigatórios.

## Recomendação operacional

1. Promover Perplexity para **pesquisas profundas, regulatórias, concorrenciais e recentes**, não para toda consulta simples.
2. Manter DDGS como fallback gratuito e como segunda opinião em buscas `site:`.
3. Manter Keenable/browser para leitura integral; snippets da Perplexity não substituem a página oficial.
4. Exigir domínio oficial e readback da página antes de transformar achado em regra MGS.
5. Não alterar campanhas existentes somente com este estudo: cada país ainda exige validação jurídica/regulatória e inspeção do account-level enforcement.
