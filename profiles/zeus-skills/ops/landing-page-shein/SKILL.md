---
name: landing-page-shein
description: "Use when operating SHEIN landing pages in WordPress."
version: 1.0.1
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

O plugin canônico é `mgs-direct-quiz`. Ele serve landings WordPress por gestor no padrão final SHEIN: V2 em `/quiz/us/sh2-g002/` e V1 em `/quiz/us/sh1-g002/`. A interface administrativa permite criar, editar, ativar/desativar e duplicar configurações.

## Contrato do produto

- Sem formulário, lead, nome, telefone, SMS, REST de captação, relatórios ou CSV.
- Sem pixel, Facebook event, data layer ou configuração de campanha.
- O evento do Facebook pertence ao artigo/REC de destino.
- A landing apenas renderiza o visual e encaminha os CTAs ao artigo.
- Preservar todos os parâmetros recebidos; parâmetros já fixados no destino vencem e aparecem uma vez.
- `utm_campaign` e `utm_adgroup` são definidos na criação da campanha no Facebook, nunca gerados pelo plugin.
- Rotas inexistentes devem retornar HTTP 404 real.

## Interface WordPress

No painel, usar o menu `Landing SHEIN`:

- `Todas as landings`: lista nome, gestor, modelo, URL, status e ações.
- `Nova landing`: cria uma configuração.
- `Editar`: altera nome, país, gestor, slug, V1/V2, logo, título, pergunta, botões, destinos, links jurídicos, status e noindex.
- `Logo do site`: aceita URL direta e também oferece `Escolher na Biblioteca de Mídia`, com preview e opção de remover.
- `Duplicar`: copia apenas a configuração, abre a cópia inativa e limpa gestor/slug para impedir publicação acidental. Definir o novo gestor e slug correspondente antes de ativar.

## Fluxo de duplicação por gestor

1. Abrir `Landing SHEIN > Todas as landings`.
2. Na landing-base, clicar `Duplicar`.
3. Confirmar que aparece `Cópia criada inativa`.
4. Definir nome interno, gestor `Gxxx` e slug correspondente ao modelo: `sh2-gxxx` para V2 ou `sh1-gxxx` para V1.
5. Revisar modelo V1/V2, copy, logo e URLs dos dois CTAs.
6. Manter ambos os destinos iguais quando esse for o desenho aprovado.
7. Salvar ainda inativa e validar a configuração por readback.
8. Ativar somente após conferir URL pública, mobile, CTAs e parâmetros.

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
- Dois CTAs presentes e destinos corretos.
- Clique real em Chromium chega ao artigo HTTP 200.
- `utm_source`, `utm_medium`, `utm_campaign`, `utm_adgroup`, `fbclid` e parâmetros customizados chegam exatamente uma vez.
- Mobile sem overflow horizontal e card inteiro.
- Código fonte e produção com manifesto idêntico.
- Backups existentes por readback.

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

## Estado validado

- Sites ativos: `yolokfx.com` e `vizioid.com`.
- Plugin canônico: `mgs-direct-quiz` v1.0.7, com código fonte e produção validados por manifesto.
- Interface administrativa em cards, com Biblioteca de Mídia para o logo e modelos exibidos como V1/V2.
- Yolokfx G002 V2: `https://yolokfx.com/quiz/us/sh2-g002/`.
- Yolokfx G002 V1: `https://yolokfx.com/quiz/us/sh1-g002/`.
- Vizioid G002 V2: `https://vizioid.com/quiz/us/sh2-g002/`, nome interno `SHEIN US — G002 — V2`.
- Vizioid G002 V1: `https://vizioid.com/quiz/us/sh1-g002/`, nome interno `SHEIN US — G002 — V1`.
- Destinos por site: `/rec-us-app-shein-circle-of-style/` no próprio domínio.
- Logo Vizioid para card branco: attachment `62160`, `600×181`, `https://vizioid.com/wp-content/uploads/2026/08/vizioid-logo-dark-600.png`.
