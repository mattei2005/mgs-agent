---
name: google-ads-amphtml-creative
description: "Use quando Ares criar ou converter criativos HTML5/AMPHTML para upload no Google Ads. Reconstrói o visual em HTML/CSS/SVG inline, valida AMP4ADS e entrega ZIP somente com index.html."
version: 1.0.0
author: MGS Digital Corp
license: Proprietary
metadata:
  hermes:
    tags: [mgs, ares, google-ads, amphtml, amp4ads, html5, creative, svg]
    related_skills: [creative-operations-mgs, paid-acquisition-operations]
---

# Google Ads AMPHTML Creative — Ares

## Overview

Esta skill governa a criação e conversão de criativos visuais para o fluxo de **Uploaded ads** do Google Ads usando AMPHTML (`AMP4ADS`). O produto final é um anúncio desenhado integralmente em `index.html`, com HTML, CSS e SVG inline — não um wrapper que aponta para uma imagem raster.

O fluxo termina somente quando o arquivo exato entregue:

1. reproduz visualmente o criativo na dimensão solicitada;
2. não contém imagem referenciada nem clique customizado;
3. passa no validador AMP4ADS;
4. é renderizado e inspecionado visualmente;
5. é empacotado em ZIP contendo apenas `index.html`;
6. passa por readback do ZIP.

## When to Use

Use quando Rodolfo ou outro usuário autorizado pedir:

- converter imagem PNG/JPG em HTML5 para Google Ads;
- criar banner AMPHTML/AMP4ADS;
- corrigir erro de upload como `Custom exit is not allowed`;
- transformar um layout em HTML/CSS/SVG inline;
- validar código no AMP Validator e gerar ZIP para Google Ads;
- revisar código de outro criativo AMPHTML usado como referência.

Não use esta skill para:

- criar ou alterar campanha, budget, billing ou credencial;
- configurar pixel, conversão ou conta Google Ads;
- empacotar HTML5 comum quando o pedido exige outro formato diferente de AMP4ADS;
- publicar um criativo sem validação visual e técnica.

Campaign write continua governado por `paid-acquisition-operations` e pela autoridade vigente.

## Regra central: reconstrução, não encapsulamento

Quando o fluxo exigir criativo autocontido, a imagem fornecida serve como **referência visual**. Reconstrua seus elementos com:

- HTML para textos e estrutura;
- CSS para dimensões, cores, gradientes, bordas e posicionamento;
- SVG inline para ícones, logos vetoriais e formas simples.

É proibido entregar como conversão:

- `<img>` ou `<amp-img>` apontando para PNG/JPG/WebP/GIF;
- `<image>` dentro de SVG apontando para raster;
- `background-image: url(...)` ou qualquer `url(...)` em CSS;
- data URI/base64 de imagem;
- arquivo de imagem ao lado do HTML no ZIP;
- CSS ou fonte externa usada para completar o visual.

A única dependência externa obrigatória é o runtime oficial:

```html
<script async src="https://cdn.ampproject.org/amp4ads-v0.js"></script>
```

Se o material tiver fotografia, textura complexa ou arte impossível de reconstruir fielmente com HTML/CSS/SVG, não finja equivalência pixel-perfect. Informe a limitação e proponha uma adaptação vetorial verificável ou solicite assets editáveis.

## Shell mínimo AMP4ADS

O documento deve começar com o caractere real `⚡`, nunca com a textualização `:zap:` gerada por Discord:

```html
<!doctype html>
<html ⚡4ads lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,minimum-scale=1">
  <meta name="ad.size" content="width=336,height=280">
  <script async src="https://cdn.ampproject.org/amp4ads-v0.js"></script>
  <style amp4ads-boilerplate>body{visibility:hidden}</style>
  <style amp-custom>
    *{box-sizing:border-box}
    html,body{margin:0;width:336px;height:280px;overflow:hidden;background:#fff}
  </style>
</head>
<body>
  <div id="banner">
    <!-- Todo o visual deve existir aqui em HTML/CSS/SVG inline. -->
  </div>
</body>
</html>
```

A dimensão em `meta name="ad.size"`, no CSS de `html,body` e no container principal deve coincidir com o pedido.

## Clique e URL final no Google Ads

Para este fluxo de AMPHTML Uploaded ads:

- não adicionar `amp-ad-exit`;
- não adicionar `ExitApi`;
- não usar `tap:exit-api.exit(...)`;
- não inserir `finalUrl` no JSON do criativo;
- não criar área de clique customizada.

A ausência de saída customizada permite que o Google Ads torne o corpo inteiro clicável. A URL de destino é preenchida no campo **URL final** da campanha/anúncio no Google Ads.

Erro típico que esta regra evita:

```text
Custom exit is not allowed. The full ad body should be clickable.
```

## CSS e animação

Prefira layout fixo correspondente ao tamanho do anúncio. Para preservar validade AMP4ADS:

- use `position`, flex/grid, cores, bordas, gradientes e SVG inline;
- mantenha todo elemento dentro do canvas;
- se usar `@keyframes`, anime somente `opacity` e `transform`;
- não anime `box-shadow`, `background`, `border` ou outras propriedades que o AMP4ADS rejeita;
- não use JavaScript próprio.

A animação é opcional. Um criativo estático fiel é melhor que uma animação que introduza erro, corte ou divergência visual.

## Workflow obrigatório

### 1. Inspecionar os inputs

- confirmar dimensão real da imagem com ferramenta de arquivo, não por suposição;
- inspecionar visualmente textos, cores, proporções, ícones e alinhamento;
- identificar se a fonte visual pode ser aproximada com fontes locais seguras;
- registrar qualquer parte impossível de reconstruir fielmente sem raster.

**Critério:** existe um mapa visual suficiente para reproduzir o anúncio sem referenciar a imagem original.

### 2. Criar em diretório temporário

Produzir primeiro em diretório temporário, com o nome final `index.html`. Não montar o ZIP definitivo antes das validações.

**Critério:** o HTML abre, tem o canvas exato e todo o conteúdo visual está inline.

### 3. Executar as guardas estáticas

Antes do validador, confirmar ausência de:

```text
<img
<amp-img
<image ... href/src
url(
data:
<link rel="stylesheet"
amp-ad-exit
ExitApi
exit-api
finalUrl
tap:...exit
```

Use o helper desta skill:

```bash
python3 scripts/verify_amphtml_bundle.py \
  --html /caminho/index.html \
  --width 336 \
  --height 280
```

**Critério:** helper retorna `PASS` e não gera ZIP quando qualquer guarda falha.

### 4. Validar AMP4ADS

O helper executa:

```bash
npx --yes amphtml-validator \
  --html_format AMP4ADS \
  --format text \
  /caminho/index.html
```

Quando Rodolfo estiver conferindo manualmente, o mesmo código pode ser colado em:

```text
https://validator.ampproject.org/#htmlFormat=AMP4ADS
```

Nunca declarar `PASS` com base no boilerplate vazio do site. O código exato do artefato deve estar no editor quando o status for lido.

**Critério:** saída real termina em `index.html: PASS` ou a interface mostra `Validation Status: PASS` para o código exato.

### 5. Renderizar e comparar

Renderizar o HTML final em navegador e comparar com a referência:

- título e textos completos;
- elementos dentro do canvas;
- alinhamento, espaçamento e hierarquia;
- cores e gradientes;
- ausência de cortes, sobreposições ou tela branca.

Se um preview injetado por `document.write` mantiver `body{visibility:hidden}` porque o runtime não reexecutou, altere a visibilidade apenas no DOM temporário de preview. Nunca grave essa exceção no `index.html` final.

**Critério:** inspeção visual do artefato final aprovada pelo executor; divergências materiais são corrigidas e renderizadas novamente.

### 6. Gerar ZIP somente após PASS

```bash
python3 scripts/verify_amphtml_bundle.py \
  --html /caminho/index.html \
  --width 336 \
  --height 280 \
  --zip /caminho/criativo-336x280-amphtml.zip
```

O helper deve criar atomicamente um ZIP com um único membro:

```text
index.html
```

**Critério:** `zip_member_count=1`, `zip_members=["index.html"]`, conteúdo de readback idêntico ao HTML validado e teste do arquivo ZIP sem erro.

### 7. Entregar e reportar

Informar de forma curta:

- dimensão;
- AMP4ADS `PASS`;
- ZIP somente com `index.html`;
- ausência de imagem referenciada e custom exit;
- qualquer aproximação visual relevante;
- que a URL final é configurada no Google Ads.

O `PASS` técnico não garante aprovação de política, elegibilidade da conta ou veiculação.

## Uso de código de referência

Código enviado por Rodolfo ou por terceiros é referência, não verdade canônica. Verifique especialmente:

- `:zap:4ads` deve virar `⚡4ads`;
- fontes externas devem ser removidas se o requisito for autocontido;
- presença de imagem, `url(...)`, custom exit ou JavaScript;
- dimensão declarada versus dimensão real;
- validade no AMP4ADS atual.

Preserve somente padrões que passem nas guardas e no validador real.

## Common Pitfalls

1. **Wrapper de imagem em AMPHTML** — passa no AMP Validator, mas o ZIP ainda depende de PNG. Corrigir reconstruindo o visual em HTML/CSS/SVG inline.
2. **Confundir PASS com upload aceito** — o validador AMP não aplica todas as regras do uploader do Google Ads. Executar também as guardas específicas desta skill.
3. **Adicionar `amp-ad-exit` para a URL** — o uploader rejeita custom exit. Remover e usar o campo URL final do Google Ads.
4. **Validar o boilerplate do site** — o site abre em PASS antes do código ser inserido. Confirmar que o editor contém o artefato exato.
5. **Atributo textualizado** — `<html :zap:4ads>` é inválido. Usar `<html ⚡4ads>`.
6. **Fonte remota escondida** — Google Fonts ainda é dependência externa. Preferir fontes locais ou incorporar somente quando a política e o requisito permitirem explicitamente.
7. **ZIP com sobras** — imagem original, preview, pasta ou arquivo oculto invalida o contrato. ZIP deve conter apenas `index.html`.
8. **Preview branco interpretado como falha visual** — confirmar se o boilerplate permaneceu oculto por injeção de preview antes de alterar o artefato.
9. **Fotografia reconstruída como se fosse idêntica** — declarar a limitação em vez de inventar fidelidade.
10. **Encerrar após escrever código** — só concluir após validator, render, ZIP e readback reais.

## Verification Checklist

- [ ] Dimensão real confirmada
- [ ] Visual reconstruído em HTML/CSS/SVG inline
- [ ] Nenhuma referência de imagem ou data URI
- [ ] Nenhuma stylesheet/fonte externa
- [ ] Nenhum custom exit, `finalUrl` ou JavaScript próprio
- [ ] `meta ad.size` e canvas coincidem
- [ ] AMP4ADS validator `PASS`
- [ ] Preview renderizado e comparado
- [ ] ZIP contém somente `index.html`
- [ ] ZIP íntegro e readback idêntico
- [ ] URL final deixada para o campo do Google Ads
- [ ] Limitações de política/fidelidade declaradas
