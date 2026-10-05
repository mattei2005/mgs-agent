---
name: landing-page-shein
description: "Use when operating SHEIN landing pages in WordPress."
version: 1.3.4
author: MGS Digital Corp / Zeus
license: Internal MGS
metadata:
  hermes:
    tags: [wordpress, shein, landing-page, direct-traffic, utm]
    related_skills: [wp-plugin-mass-operation]
---

# Landing Page SHEIN

## When to Use

Use quando Rodolfo pedir criação, edição, duplicação, implantação, auditoria ou melhoria da interface das landing pages SHEIN no WordPress. Não usar para funis com lead/SMS nem para o plugin do Creditoparaveiculo.

## Escopo

Skill exclusiva das landing pages de tráfego direto SHEIN. Não misturar com `wp-quiz-lead-funnel` nem com o produto Creditoparaveiculo.

O plugin canônico é `mgs-direct-quiz`. Ele serve landings WordPress por gestor no padrão final SHEIN: V3 de categorias em `/quiz/us/sh3-g002/`, V2 em `/quiz/us/sh2-g002/` e V1 em `/quiz/us/sh1-g002/`. A interface administrativa permite criar, editar, ativar/desativar e duplicar configurações.

## Contrato do produto

- Sem formulário, lead, nome, telefone, SMS, REST de captação, relatórios ou CSV.
- Sem pixel, Facebook event, data layer ou configuração de campanha.
- Cada landing define o idioma público de forma explícita (`en` ou `es`); país não deve ser usado como inferência de idioma. O idioma controla `lang`, rótulos fixos, links jurídicos, disclaimer padrão e copyright, preservando configurações antigas em inglês.
- O evento do Facebook pertence ao artigo/REC de destino.
- A landing apenas renderiza o visual e encaminha os CTAs ao artigo.
- Preservar todos os parâmetros recebidos; parâmetros já fixados no destino vencem e aparecem uma vez.
- `utm_campaign` e `utm_adgroup` são definidos na criação da campanha no Facebook, nunca gerados pelo plugin.
- Rotas inexistentes devem retornar HTTP 404 real.

## Interface WordPress

No painel, usar o menu `Landing SHEIN`:

- `Todas as landings`: lista nome, gestor, modelo, URL, status e ações.
- `Nova landing`: cria uma configuração.
- `Editar`: altera nome, país, idioma público, gestor, slug, V1/V2/V3, logo, título, pergunta, botões, destinos, links jurídicos, status e noindex. No V3 também edita contador, chamada superior, seis categorias com imagem, CTA principal, microtexto e disclaimer.
- `Logo do site`: aceita URL direta e também oferece `Escolher na Biblioteca de Mídia`, com preview e opção de remover.
- `Duplicar`: copia apenas a configuração, abre a cópia inativa e limpa gestor/slug para impedir publicação acidental. Definir o novo gestor e slug correspondente antes de ativar.

## Fluxo de duplicação por gestor

1. Abrir `Landing SHEIN > Todas as landings`.
2. Na landing-base, clicar `Duplicar`.
3. Confirmar que aparece `Cópia criada inativa`.
4. Definir nome interno, gestor `Gxxx` e slug correspondente ao modelo: `sh3-gxxx` para V3, `sh2-gxxx` para V2 ou `sh1-gxxx` para V1.
5. Revisar modelo V1/V2/V3, copy, logo e destinos. No V3, as seis categorias e o CTA principal usam o destino da opção 1.
6. Manter ambos os destinos iguais quando esse for o desenho aprovado.
7. Salvar ainda inativa e validar a configuração por readback.
8. Ativar somente após conferir URL pública, mobile, CTAs e parâmetros.

## Entrega estática gerada pelo painel

Desde a v1.1.1, WordPress é o plano de controle e cada landing ativa é entregue por um `index.html` físico na rota pública. O request da landing não inicializa WordPress/PHP.

- Criar ou ativar publica o `index.html`.
- Editar regenera o arquivo por escrita temporária + rename atômico e valida readback/hash.
- Duplicar mantém a cópia inativa e não cria rota física.
- Desativar move o diretório gerado para arquivo reversível e devolve a rota ao 404 do WordPress; não apagar resíduos sem a confirmação exigida pelo Critical Subset.
- Alteração de país, gestor, modelo ou slug em landing ativa fica bloqueada; desativar primeiro, editar e então reativar. Isso evita duas rotas públicas concorrentes.
- O HTML estático deve carregar CSS/JS por HTTPS mesmo quando `plugin_dir_url()` é calculado dentro de WP-CLI atrás de proxy. Testar explicitamente mixed content; HTML 200 sozinho não prova CSS/JS funcionando.
- UTMs, `fbclid` e parâmetros personalizados continuam no JavaScript do arquivo estático, exatamente uma vez.
- Em deploy de upgrade, chamar `MGS_Direct_Quiz::sync_static_pages()` e validar no HTML público o marker `MGS Direct Quiz static`, versão, dois CTAs, zero formulário/input, zero `wp-includes`/tema e assets HTTPS.
- O browser deve provar largura mobile, execução do JavaScript e clique real; HTML estático sem CSS/JS pode parecer aprovado em checks de texto, mas falha no produto.

## Implantação segura

1. Confirmar domínio, webroot, rota livre e artigo de destino HTTP 200.
2. Criar backup de option/banco e do diretório do plugin.
3. Empacotar a fonte canônica e calcular SHA-256 por shell.
4. Implantar de forma transacional com rollback do diretório anterior.
5. Ativar e validar versão por WP-CLI.
6. Limpar cache do WordPress e CDN quando aplicável.
7. Comparar manifesto SHA-256 da fonte com produção.
8. Não excluir arquivos temporários sem a confirmação adicional do Critical Subset. Preferir caminhos únicos e mover pacote, script e staging para o diretório de backup/auditoria; se um arquivo remoto estiver sob ownership `runcloud`, usar `sudo mv` para o backup em vez de `rm`.

## Validação obrigatória

- Plugin ativo e versão correta por readback.
- Interface administrativa contém criar, editar e duplicar.
- Duplicação cria nova ID, copia configuração, deixa `active=0` e limpa gestor/slug; restaurar estado original após teste controlado.
- Landing HTTP 200 e rota inexistente HTTP 404.
- Zero `<form>` e zero `<input>` na landing pública.
- O atributo `lang`, todos os rótulos fixos e todo o conteúdo visível devem corresponder ao idioma configurado; em espanhol, validar também `Política de Privacidad`, `Términos de Servicio`, `Descargo de responsabilidad` e `Todos los derechos reservados`, com ausência dos equivalentes ingleses.
- V1/V2: dois CTAs presentes e destinos corretos. V3: seis categorias + CTA principal, sete links no total, todos no mesmo REC.
- No V3, contador até meia-noite local, disclaimer recolhível, seis imagens próprias carregadas e zero overflow em 320×700, 360×800 e 390×844.
- Clique real em Chromium chega ao artigo HTTP 200.
- `utm_source`, `utm_medium`, `utm_campaign`, `utm_adgroup`, `fbclid` e parâmetros customizados chegam exatamente uma vez.
- Mobile sem overflow horizontal e card inteiro.
- Código fonte e produção com manifesto idêntico.
- Backups existentes por readback.

## Preflight e validadores sem falso negativo

- Antes de confirmar quantas versões existem para todos os gestores, ler as configurações live com `slug`, modelo e `active`; configuração existente não significa rota publicada. A skill/checkpoint pode preceder expansões posteriores, portanto não afirmar ausência a partir desses registros.
- Para `country=us`, o campo de configuração `language=en` renderiza `<html lang="en-US">` e `es` renderiza `es-US`; fora de US, o template usa os códigos curtos `en/es`. Validar o atributo real e o conteúdo visível, sem exigir que o HTML seja igual ao código curto da option.
- Se o transporte padrão de urllib devolver 403, comparar uma única vez com curl e User-Agent normal ou com Chromium real antes de atribuir WAF/IP/credencial. Um 200 nessa comparação é falha do transporte inicial; não alterar regras Cloudflare ou produção para fazer o validador passar.
- Para a marca, o `custom_logo` pode ser apenas um recorte minúsculo. Ler o attachment, `post_parent` e metadados, e procurar o original em alta resolução na Biblioteca antes de ampliar/recolorir a miniatura. Preservar original e criar derivado separado quando a versão branca não for legível no card.

## Logos com canvas transparente excessivo

Se um logo quadrado aparecer minúsculo apesar do `max-height`, inspecione as dimensões e o bounding box real do alpha. Quando a marca ocupa apenas uma faixa central do canvas, prefira recortar o arquivo sem redesenhá-lo:

1. Calcule o bbox com alpha visível (limiar baixo, por exemplo `>=5`) para ignorar pixels residuais.
2. Preserve a marca integral e adicione margem transparente curta e equilibrada.
3. Redimensione para resolução web/retina proporcional; para logo horizontal, cerca de 600 px de largura é suficiente.
4. Importe o novo PNG na Biblioteca de Mídia, atualize a landing e valide por readback de attachment, dimensões e URL.
5. Faça screenshot Chromium mobile e confirme largura renderizada, centralização, legibilidade e zero overflow.

Não use geração por IA quando um recorte lossless resolve; geração só é necessária se o arquivo original estiver incompleto ou em baixa qualidade.

## QA mobile quando o browser principal falhar

Se o browser harness não iniciar o Chrome, não reduzir a validação a HTML estático. Usar Chromium real em foreground por Playwright ou CDP, sempre sem notificações automáticas no Discord, e validar:

1. viewport mobile 390×844;
2. screenshot de V1 e V2;
3. card inteiro e `scrollWidth <= innerWidth`;
4. clique real em um CTA de cada modelo;
5. destino HTTP 200 e parâmetros exatamente uma vez;
6. inspeção visual do logo sobre o fundo real da landing.

Se o logo oficial tiver texto branco sobre card branco, procurar primeiro uma variante oficial adequada. Se não houver, criar derivação lossless: preservar símbolo e cores da marca, recolorir apenas o texto branco para tom escuro, recortar o alpha visível, adicionar margem curta, salvar em resolução web/retina, importar como novo attachment e validar por screenshot. Não sobrescrever nem excluir o asset original.

## Seletores confiáveis no QA das páginas públicas

- No V3 estático, o contêiner da imagem é `span.mgs-dq-category-image` e o `<img>` fica aninhado; leia `currentSrc`, `complete` e `naturalWidth/naturalHeight` no `<img>`. O texto da categoria está em `.mgs-dq-category-name`. Não procure uma classe de imagem diretamente no `<img>`, porque isso produz falso negativo apesar de a página estar correta.
- Em artigos com CSS inline, nomes como `cnh-rec-quiz-wrap`, `cnh-rec-logo` e `cnh-rec-headline` aparecem primeiro dentro do `<style>`. Ao validar a ordem visual, ancore no `<section class="cnh-rec-quiz-wrap">` renderizado ou consulte o DOM; nunca use a primeira ocorrência textual do nome da classe no HTML inteiro.
- Um falso negativo do validador não autoriza alterar produção novamente. Inspecione o DOM real, corrija o seletor e repita a leitura antes de concluir que existe regressão.

## Preservação de configurações existentes em upgrades

O inventário pode estar defasado em relação às landings criadas depois do último rollout. Antes de atualizar o plugin, ler a option live em cada site, registrar contagem/rotas/status e tratar o runtime como fonte de verdade. Fazer backup da option completa, do plugin e de todo o diretório `quiz`; depois do rollout, comparar cada configuração antiga por ID e exigir igualdade integral, permitindo somente o novo item autorizado. Regenerar e validar todas as rotas ativas, não apenas a nova.

## Edição de copy em rotas estáticas e cache

- Em alteração de copy, valide três camadas separadamente: option do WordPress, `index.html` físico regenerado e URL pública sem cache-buster. A option e o arquivo corretos não provam que a rota pública está atualizada.
- O WP Fastest Cache pode interceptar `/quiz/.../` e servir `wp-content/cache/all/quiz/.../index.html` antigo, enquanto `/quiz/.../index.html` já mostra o arquivo novo. Compare as duas URLs, localize a cópia obsoleta e mova somente o diretório de cache afetado para dentro do backup reversível; não apague para contornar o Critical Subset. Valide novamente a URL pública sem `index.html`.
- Backup JSON criado com `sudo tee` fica root-owned. Antes de usá-lo em rollback via `sudo -u runcloud wp eval`, faça `chown` para o owner, mantenha `chmod 600` e exercite decode/readback; um rollback que suprime erro de permissão pode restaurar os arquivos e deixar a option divergente.
- No V3, `question` pode permanecer armazenada e aparecer no HTML-fonte sem estar visível. Para uma troca somente de título, preserve esse campo e valide a ausência/presença da copy pelo DOM visível; não rejeite a operação pela presença de configuração oculta fora do escopo.

## Imagens de categorias no V3

- Quando a imagem recebida já vier como card vertical com o rótulo embutido, recorte somente a área visual em quadrado antes de importar; o plugin já renderiza o rótulo e manter o rodapé original cria texto duplicado.
- Para cards pequenos, exporte derivados em WebP `400×400`, removendo metadados e usando qualidade visual equivalente a `78–82`. Como alvo operacional, mantenha cada imagem abaixo de 25 KB e as seis abaixo de 100 KiB; compare o peso anterior e posterior por cálculo real e aprove a compressão por inspeção visual.
- Preserve os arquivos originais, os derivados e seus SHA-256 no backup; não sobrescreva nem exclua attachments antigos. Troque apenas as `image_url` das seis categorias e mantenha um rollback da option e do diretório `quiz`.
- `wp media import --title` pode definir o `post_name` a partir do título, e não do nome do arquivo. Capture o ID retornado por `--porcelain` ou resolva o attachment pela URL exata com `attachment_url_to_postid()`; não dependa de `get_page_by_path()` com o filename presumido.
- Plugins de otimização de mídia podem regravar o arquivo durante o import e alterar o SHA-256. Registre separadamente o hash da fonte preservada e o hash do arquivo público; aceite a produção somente após validar MIME, dimensões, limite de bytes, URL pública, carregamento real e QA visual.
- Se o backup/staging for criado com `sudo`, entregue ownership do diretório-pai ao usuário do webapp antes do import. Ownership correto somente no arquivo não basta quando o processo não consegue atravessar o diretório.
- No readback final, valide as seis labels na ordem, seis `currentSrc` exatos, `naturalWidth`/`naturalHeight`, imagens completas, ausência de rótulos antigos, zero overflow mobile e um clique real com tracking preservado.

## Estado validado

- Para o conjunto completo e atual de sites/modelos/gestores, consultar `context/acquisition.md` e depois ler a option live por site; esta seção contém exemplos, não um inventário exclusivo. GrowPowerHub e EscalatePower operam V2/V3 G001–G006 em inglês com `mgs-direct-quiz` v1.2.1 e REC `/rec-us-app-shein-circle-of-style/` do próprio domínio, sem V1. Yolokfx possui V2/V3 G001–G006 ativas; V1 está configurada para seis gestores, mas G004 permanece inativa.
- Plugin canônico mais recente: `mgs-direct-quiz` v1.2.1, com idioma público explícito `en/es`, manifesto de 15 arquivos e frontend entregue por `index.html` físico gerado pelo painel. Mavroa opera v1.2.1; Yolokfx e Vizioid permanecem em v1.2.0 sem alteração neste rollout.
- Interface administrativa em cards, com Biblioteca de Mídia para logo e categorias, idioma público e modelos exibidos como V1/V2/V3.
- Yolokfx G002 V2: `https://yolokfx.com/quiz/us/sh2-g002/`.
- Yolokfx G002 V1: `https://yolokfx.com/quiz/us/sh1-g002/`.
- Vizioid G002 V2: `https://vizioid.com/quiz/us/sh2-g002/`, nome interno `SHEIN US — G002 — V2`.
- Vizioid G002 V1: `https://vizioid.com/quiz/us/sh1-g002/`, nome interno `SHEIN US — G002 — V1`.
- Vizioid e Yolokfx possuem V3 ativa para `G001`–`G006`, nas rotas `/quiz/us/sh3-g001/` até `/quiz/us/sh3-g006/`.
- Mavroa opera em espanhol com V1/V2 G002 (`/quiz/us/sh1-g002/` e `/quiz/us/sh2-g002/`) e V3 G001–G006 (`/quiz/us/sh3-g001/` a `/quiz/us/sh3-g006/`). Todos os CTAs usam `https://mavroa.com/rec-us-app-shein-productos-gratis/`.
- As expansões V3 por site foram validadas como idênticas no contrato do modelo; somente identidade de configuração e conteúdo localizado variam.
- O V3 aceita seis imagens configuradas por landing, contador até meia-noite local, CTA principal e disclaimer recolhível. No Yolokfx e nas réplicas GrowPowerHub/EscalatePower, o conjunto atual é Women/Men/Home/Shoes/Electronics/Others com seis WebP 400×400; SVGs são somente o fallback, não prova do asset live.
- Destinos em Yolokfx/Vizioid: `/rec-us-app-shein-circle-of-style/` no próprio domínio. Destino em Mavroa: `/rec-us-app-shein-productos-gratis/`.
- Logo Vizioid para card branco: attachment `62160`, `600×181`, `https://vizioid.com/wp-content/uploads/2026/08/vizioid-logo-dark-600.png`.
- Logo Mavroa para card branco: attachment `62285`, `600×141`, `https://mavroa.com/wp-content/uploads/2026/09/mavroa-logo-dark-600.png`; derivação lossless preserva o símbolo oficial e usa wordmark escuro.
