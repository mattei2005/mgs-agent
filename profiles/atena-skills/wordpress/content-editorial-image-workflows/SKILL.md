---
name: content-editorial-image-workflows
description: "Use when an article needs editorial images. Generate, QA, and integrate media."
version: 1.0.1
author: MGS Digital Corp
license: Proprietary
metadata:
  hermes:
    tags: [wordpress, images, editorial, mgs]
    related_skills: [content-site-vertical-operations, content-publish-wordpress]
---

# content-editorial-image-workflows

## When to Use

Use esta skill quando a tarefa envolver imagem editorial de artigo, especialmente:

- featured image de REC, P1, AD ou artigo SEO;
- imagem contextual de carro/finanças/cartão/produto para WordPress;
- aplicação de logo/site branding em imagem editorial;
- comparação/validação de imagem gerada por IA antes de publicar;
- reparo de composição, artefatos, legibilidade ou identidade visual.

Não use esta skill para criativos de anúncio, variações de campanha, vídeo, Canva/Drive criativo ou handoff de mídia — isso pertence ao Ares/Creative Operations.

## Princípio operacional

Imagem editorial deve vender o clique sem parecer peça de anúncio mal acabada. O produto/tema precisa ser protagonista, mas o branding do site deve funcionar como assinatura visual discreta, não como banner.

Sempre preservar:

1. realismo;
2. clareza do assunto;
3. composição editorial;
4. ausência de artefatos visíveis;
5. identidade correta do site/produto;
6. validação visual antes de declarar pronto.

## Workflow para featured image com logo do site

Quando a imagem precisa conter o logo oficial do site:

1. **Não pedir ao modelo para desenhar o logo final.**
   - Modelos de imagem costumam deformar texto, logotipo e símbolo.
   - Gere a cena sem texto, sem marcas e sem overlay.

2. **Promptar a cena com área limpa para branding posterior.**
   - Exigir 16:9, fotografia ultra-realista/editorial.
   - Definir protagonista e contexto.
   - Pedir fundo com bokeh/profundidade.
   - Bloquear texto, placas legíveis, selos, botões e logos.
   - Pedir canto inferior direito visualmente limpo quando o branding for aplicado ali.

3. **Aplicar o logo oficial depois, deterministicamente.**
   - Usar o ativo oficial do site.
   - Criar painel pequeno no canto, preferencialmente branco/translúcido, com cantos arredondados.
   - Adicionar sombra discreta.
   - Manter o painel pequeno: assinatura premium, não banner.

4. **Validar visualmente antes de publicar ou apresentar como final.**
   - O assunto continua protagonista?
   - O logo está legível e sem deformação?
   - O painel compete com a imagem?
   - Existem artefatos de IA em céu, bandeira, placas, mãos, texto ou fundo?
   - A imagem parece editorial/publicável, não um criativo bruto?

## Pitfalls comuns

- **Logo gerado pela IA:** geralmente sai errado, ilegível ou com identidade alterada. Sobrepor depois é mais seguro.
- **Branding grande demais:** vira banner e reduz qualidade editorial.
- **Bandeiras, placas e textos:** aumentam risco de artefatos. Evitar quando não forem essenciais. Qualquer placa, storefront ou pseudo-texto legível reprova o asset; regenere antes do upload em vez de aceitar o fundo como detalhe.
- **Extensão diferente do conteúdo:** APIs de imagem podem retornar bytes JPEG mesmo quando o arquivo de saída recebeu `.png`. Rode `file`/`identify`, alinhe extensão e MIME antes do upload, porque o uploader define `Content-Type` pelo nome do arquivo.
- **Metadados de mídia incompletos:** após o upload, grave título e alt text e leia a mídia por ID; valide também a variante `large` usada no corpo e seu `Content-Type` público.
- **Imagem impactante mas suja:** contraste e golden hour não compensam artefatos grandes ou texto estranho.
- **Comparação sem critério:** avaliar impacto visual e segurança de publicação separadamente.

## QA de lotes e regeneração

1. Monte pranchas de contato com miniaturas suficientemente grandes e uma legenda externa por imagem, ligada a artigo, variante e caminho real. Inspecione um conjunto pequeno por vez; se um detalhe de mão, placa ou logotipo ficar inconclusivo, abra a imagem individual em resolução maior. Não confunda a legenda da prancha com texto presente na fotografia.
2. Registre aprovação ou bloqueio por asset, não apenas uma aprovação geral da prancha. Regere somente os reprovados e mantenha a ligação entre o artigo e a variante final aprovada para não enviar a original por engano.
3. Corrija a composição que favoreceu o defeito, não apenas repita o mesmo prompt: retire pessoas de um still life de equipamentos quando houver membros extras, use fundo liso quando surgir letreiro e enquadre veículos de perfil quando aparecerem emblemas frontais. Preserve a pertinência ao artigo; uma cena limpa mas intercambiável com qualquer assunto não basta.
4. Inspecione novamente cada substituta antes do upload. Não trate `sem marcas` no prompt como prova de ausência de marca: tampas de notebooks, grades de veículos e fachadas também precisam ser conferidas.
5. Redija ou ajuste o alt text a partir da imagem final observada, no idioma do artigo, e não do prompt original. Uma regeneração pode retirar a pessoa, o laptop ou outro objeto; manter o alt anterior descreve algo que já não existe. Não afirme jogo, plataforma, instituição, profissão ou evento específico quando a foto mostra apenas uma cena conceitual genérica; não gere interface falsa para suprir essa ausência.

## Comparação de alternativas geradas

Ao comparar duas imagens, classifique separadamente:

- impacto/CTR potencial;
- limpeza técnica;
- realismo;
- protagonista e leitura rápida;
- integração do branding;
- riscos de publicação.

Uma imagem pode ganhar em impacto e ainda perder para publicação se tiver artefato grave. Recomende regenerar inspirando-se na composição vencedora quando o conceito é bom, mas o acabamento falha.

## Referências

- `references/car-branded-featured-image-logo-overlay-2026-07-02.md` — lição Eggbev CAR BR: gerar cena limpa e aplicar logo oficial depois, evitando artefatos e logo deformado.
