## Anti-repetição, anti-plágio e escala

Atena deve reescrever a partir do par REC+P1 de referência sem copiar a superfície textual.

Reescrever não significa trocar palavras por sinônimos. O fluxo correto é reconstrução editorial:

- preservar fatos, benefícios e lógica útil do par REC+P1 de referência;
- mudar abertura, ordem de argumentos quando fizer sentido, exemplos, transições e fraseado;
- adaptar para os contracts MGS de REC e P1;
- manter REC como chamada/resumo e P1 como aprofundamento/conversão;
- evitar mesma sequência de parágrafos;
- bloquear longos trechos contíguos copiados das referências;
- validar similaridade antes de publicar/reportar sucesso.

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

Tags comerciais opcionais só podem entrar quando forem sustentadas por benefícios/fatos confirmados no pedido atual, no REC/P1 de referência ou em fonte confiável validada:

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

