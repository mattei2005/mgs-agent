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

As decisões e lições de cada incidente (reestruturação v2, tags por benefício, taxonomia WordPress, correções do teste Tesco, latência, formato de relatório e os quality gates do feedback da Raquel) ficam registradas em `references/`. Consulte a pasta quando precisar do detalhe histórico de uma decisão; nenhuma dessas notas é regra ativa por si — a regra ativa vive nos contracts, nos runners e nos validators.

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

### REC runner: `cc-rec.md` como hard requirement

No `scripts/mgs-rec-runner.py`, `load_rec_template_contract` deve usar `skills/content-generate-rec-p1/contracts/cc-rec.md` como contract universal obrigatório (`template_key=cc-universal`). Não reintroduzir fallback para `templates/rec-{template_key}.md`: se `cc-rec.md` faltar, o runner deve falhar com `RunnerError` claro e auditável. Detalhe e checklist de validação: `references/rec-runner-template-fallback-removal-2026-06-13.md`.
