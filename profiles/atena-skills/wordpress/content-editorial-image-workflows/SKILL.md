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
- **Alt desatualizado após regeneração:** reveja o texto alternativo contra a foto substituta. Se a pessoa, o equipamento ou o enquadramento mudar, corrija o alt antes do upload e confirme a versão final por readback; não descreva Steam, idioma, instituição, evento real ou profissão como se fossem visualmente comprovados por uma cena ilustrativa.
- **Metadados de mídia incompletos:** após o upload, grave título e alt text e leia a mídia por ID; valide também a variante `large` usada no corpo e seu `Content-Type` público.
- **ALT e descrição renderizada do anexo:** um write somente de `alt_text` pode mudar `description.rendered`, pois o WordPress gera ali uma imagem de anexo usando o ALT atual mesmo quando `description.raw` permanece vazio. Compare os campos raw de título/legenda/descrição, IDs/URLs/detalhes da mídia e comprove que o único delta no HTML gerado é o ALT solicitado; não classifique essa derivação como alteração editorial da descrição, não reenvie conteúdo do post nem repita o write para satisfazer um assert defeituoso. Preserve pre-read/intenção e reconcilie o alvo antes da retomada.
- **Lazy-load em aba de browser oculta:** antes de classificar uma imagem ou autoria como ausente, confira `document.visibilityState`, traga a aba à frente e role o elemento real para a viewport; aguarde o carregamento com limite e valide `complete`/`naturalWidth` e o texto de autoria. Uma aba oculta pode suspender o lazy-load apesar de o arquivo responder HTTP 200. Não force `src`, eventos `load` ou conteúdo do DOM para fabricar aprovação; preserve separadas a prova de transporte e a de renderização.
- **Imagem impactante mas suja:** contraste e golden hour não compensam artefatos grandes ou texto estranho.
- **Comparação sem critério:** avaliar impacto visual e segurança de publicação separadamente.

## QA de lotes e regeneração

1. Monte pranchas de contato com miniaturas suficientemente grandes e uma legenda externa por imagem, ligada a artigo, variante e caminho real. Inspecione um conjunto pequeno por vez; se um detalhe de mão, placa ou logotipo ficar inconclusivo, abra a imagem individual em resolução maior. Na pergunta ao revisor visual, diga explicitamente para ignorar as legendas externas, que não serão publicadas, e retornar por asset a cena observada, defeito concreto, decisão e ALT factual. Não peça para autenticar um evento ou documento que a foto é apenas destinada a ilustrar; isso desvia a revisão dos requisitos editoriais.
2. Registre aprovação ou bloqueio por asset, não apenas uma aprovação geral da prancha. Em trabalho delegado, faça a revisão final do responsável antes de montar o manifesto de upload; aprovação do subagente não substitui esse gate. Abra o original quando a prancha suscitar dúvida. Separe os aprovados de uma variante bloqueada, mantenha o manifesto anterior imutável e gere um manifesto complementar apenas para a correção aprovada; confira caminho, SHA-256 e variante exatos para não enviar a versão rejeitada. Regere somente os reprovados.
3. Corrija a composição que favoreceu o defeito, não apenas repita o mesmo prompt: retire pessoas de um still life de equipamentos quando houver membros extras, use fundo liso quando surgir letreiro e enquadre veículos de perfil quando aparecerem emblemas frontais. Em fotografia sintética que deva evitar interfaces fabricadas, reprove também blocos, campos e linhas que simulem uma tela de consulta, mesmo sem palavras legíveis; desfoque não transforma pseudo-interface em evidência legítima. Recompose com a traseira do aparelho ou monitor integralmente voltada à câmera e retire cartões/documentos pautados desnecessários, em vez de apenas apagar letras. Essa regra não proíbe screenshots nativos de origem verificada. Preserve a pertinência ao artigo; uma cena limpa mas intercambiável com qualquer assunto não basta.
4. Inspecione novamente cada substituta antes do upload. Quando o briefing exigir foto sem marcas/textos, reprove também logotipos incidentais reconhecíveis em tampas de notebooks, calculadoras, grades e traseiras de veículos ou fachadas, além de placas e letreiros legíveis; uma cena bonita ou anatomicamente correta não dispensa esse gate. Não trate `sem marcas` no prompt como prova visual nem amplie a proibição a branding oficial expressamente solicitado. Se o reconhecimento ficar inconclusivo na prancha, abra o original antes de decidir.
5. Redija ou ajuste o alt text a partir da imagem final observada, no idioma do artigo, e não do prompt original. Uma regeneração pode retirar a pessoa, o laptop ou outro objeto; manter o alt anterior descreve algo que já não existe. Não afirme jogo, plataforma, instituição, profissão ou evento específico quando a foto mostra apenas uma cena conceitual genérica; não gere interface falsa para suprir essa ausência.

## Pertinência e diversidade entre artigos do lote

Conforme revisão de Raquel `discord:1560295338257023118#1562273124030873610`, compare as imagens finais lado a lado com os temas antes de liberar o lote. Cada imagem deve ajudar a comunicar a intenção específica do artigo. Planeje conceito, composição, enquadramento, elementos, ambiente e ação próprios; não aceite a mesma composição apenas com outra pessoa, carro, ângulo ou cenário. Registre o motivo de preservar ou substituir cada asset. Não troque imagem correta para gerar diferença artificial. Faça QA visual das substitutas e confirme no resultado público a imagem interna e destacada efetivamente renderizadas.

### Gate de especificidade reforçado pela revisão humana

Fonte: Raquel, `discord:1560295338257023118#1562828122762649781`.

- Defina o conceito pela intenção do artigo, não por um inventário recorrente de objetos. Franquia de seguro pede contexto de sinistro/análise de cobertura; combustível pede abastecimento/consumo; manutenção pede situação de oficina. Repetir compactos cinzas/prateados, chaves, papéis, envelopes e mesas com pequenas variações não comprova diversidade.
- Para jogos identificados, exija leitura visual do universo digital pertinente: maquete de prédios, peças de madeira/tabuleiro e cabana realista não substituem imagens adequadas de Roblox, Brawl Stars e Minecraft. Não fabrique screenshot, interface ou identidade do jogo; use fonte legítima e verificável ou cena editorial humanizada que mostre o contexto real sem afirmar que tela genérica comprova o jogo.
- Prefira pessoas em ação e situações naturais quando compatíveis com o tema, sem impor presença humana artificial em todas as imagens. Varie ação, ambiente, perspectiva, enquadramento, elementos e composição; evite metáforas abstratas e cenas intercambiáveis.
- Compare diversidade ENTRE artigos; neste lote SEO preserve a destacada igual à primeira imagem interna do próprio artigo e a posição aprovada. Substitua só assets realmente inadequados e reinspecione cada final antes do upload.
- Não aprove uma foto financeira só porque passou a ter pessoas: casal com notebook, atendimento e papéis podem continuar intercambiáveis. Comunique a intenção por ações, ambiente e enquadramento próprios, não por objetos recorrentes.

### Direção visual vigente: naturalidade e preferência por ausência de texto

Use esta direção em produção e revisão de lotes. Comunique especificidade pela cena, ação e enquadramento, não acrescentando painéis por padrão; infográficos úteis continuam permitidos, sem exigir refação geral.

- Priorize imagens realistas, humanizadas e contextualizadas, com pessoas, ambientes, ações e situações cotidianas quando pertinentes. Prefira não utilizar textos: o assunto deve ser comunicado visualmente, sem criar falsa interface ou evidência documental.
- Compare o conjunto por portal, especialmente financeiro: tabelas, gráficos, números, textos e painéis técnicos não devem predominar. Mescle fotografias, composições criativas e infográficos; use gráficos/tabelas somente se agregarem valor demonstrável, sem impor quota artificial.
- Preserve imagens corretas e diversas; substitua somente as excessivamente técnicas, inadequadas ou repetitivas. Registre decisão e motivo por artigo, comparando cenários, objetos, enquadramentos e conceitos entre todos os assets. Avalie a composição inteira: uma miniatura humana subordinada a um grande painel continua sendo uma peça predominantemente técnica. Não reprove automaticamente screenshots ou interfaces nativas pertinentes de jogos/aplicativos como se fossem painéis editoriais; confirme origem, contexto e ausência de interface fabricada.
- Mantenha a imagem destacada igual à primeira imagem do artigo, com ALT factual no idioma e validação real pública/OG após a troca. Cache social antigo é pendência técnica separada; não equivale a upload falho nem autoriza purge global.
- Quando infográfico for realmente necessário, use somente conceitos e dados sustentados no corpo; calcule valores em código e não apresente hipótese como oferta real. Sua inclusão deve continuar excepcional à preferência por imagem sem textos.

## Sequência para substituir imagens de textos aprovados

1. Congele o manifesto dos posts existentes e leia a mídia atual; compare destacada e primeira imagem por ID, incluindo as variantes realmente enumeradas no attachment.
2. Inspecione o conjunto antes de gerar. Registre por artigo cena observada, preservar/trocar e motivo concreto; planeje cenas novas somente para o subconjunto que precisa de troca. Reutilize uma foto-base sem painel apenas se o arquivo original tiver resolução suficiente e passar no QA; não amplie automaticamente um recorte de miniatura.
3. Gere ou prepare somente as substitutas justificadas. Separe plano de cena, arquivo gerado e aprovação visual; nenhum desses estados comprova upload ou aplicação no WordPress. Redija o ALT da imagem final observada, não do prompt.
4. Antes do write autorizado, faça novo `GET` com `context=edit` e preserve o baseline. Substitua apenas o bloco de imagem identificado e `featured_media`; compare byte a byte todo o raw restante para proteger texto, fontes, links, CTAs e posição aprovados. Pare diante de múltiplos blocos ambíguos ou edição concorrente, em vez de usar regex amplo.
5. Após aplicar, releia mídia e post exatos e confira arquivo original, variante interna, ALT, destacada e corpo público. No navegador, registre `currentSrc`, classe/ID do attachment, `complete` e `naturalWidth > 0`; confira a variante entre as URLs enumeradas pela mídia. Não exija que `naturalWidth` seja igual à largura do original ou do atributo HTML: `srcset` e otimização responsiva podem entregar outra resolução legítima. Preserve IDs/URLs dos artigos; não substitua o artigo inteiro por um fragmento sem os demais blocos.
6. Confira OG e a imagem efetiva do schema separadamente. Uma imagem correta no corpo não comprova prévia atual; registre divergência técnica sem repetir upload, regravar texto ou declarar cache como causa não demonstrada.

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
