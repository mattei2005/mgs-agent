---
name: lazyblocks-native-cross-site-migration
description: Use when migrating WordPress pages and Lazy Blocks.
version: 1.0.0
author: MGS Digital Corp / Zeus
license: Internal MGS
metadata:
  hermes:
    tags: [wordpress, lazy-blocks, migration, pages]
    related_skills: [wp-plugin-mass-operation]
---

# Migração nativa de páginas e Lazy Blocks entre sites

## When to Use

Use quando Rodolfo pedir que páginas e cards definidos no plugin Lazy Blocks de um WordPress sejam reproduzidos em outros sites.

## Princípios

- Trate as páginas editoriais e as definições de bloco como camadas separadas.
- A lista nativa que o Lazy Blocks registra vence a contagem bruta de posts `post_type=lazyblocks`. Definições antigas podem permanecer publicadas com o mesmo runtime slug; o exportador nativo resolve o bloco funcional vencedor.
- Não copie metadados Lazy Blocks por `get_post_meta()` → `add_post_meta()` entre versões. Sanitizadores e serialização podem normalizar `lazyblocks_controls`, `lazyblocks_styles` e `lazyblocks_supports_align`, produzindo hashes diferentes mesmo quando os valores parecem equivalentes.
- Não use SQL cru quando o export/import oficial da versão alinhada está disponível.

## Preflight

1. Confirmar `home`, WordPress, PHP, tema, versão/status do Lazy Blocks e atualizações pendentes em origem e destinos.
2. Inventariar páginas, posts `lazyblocks`, runtime slugs e uso real de `<!-- wp:lazyblock/... -->` em conteúdo publicado.
3. Detectar runtime slugs duplicados. Preservar o histórico no backup, mas migrar a saída do exportador nativo — não duas definições concorrentes com o mesmo slug.
4. Exigir alvo vazio ou resolver conflitos de slug antes da escrita; nunca sobrescrever páginas/cards existentes por conveniência.
5. Criar backup full da origem antes de alinhar versões quando Rodolfo pedir atualização: dump SQL, arquivo integral do webroot, inventário de plugins/temas/ativos e snapshot dos Lazy Blocks. Validar `gzip -t`, presença de `wp-config.php`/plugins, rodapé `Dump completed on`, hashes e modes.

## Alinhamento de versão

- Leia o changelog oficial e o código de migrações da versão-alvo. Um changelog sem breaking change não elimina a necessidade de canário.
- Para Lazy Blocks 4.4.1, o salto desde 4.3.1 adiciona compatibilidade WordPress 7.1 e correções de controles; não há migração 4.4 que regrave as definições. A migration apenas avança `lzb_db_version` quando aplicável.
- Após atualizar a origem, exija: mesma lista/status de plugins, zero updates remanescentes, banco OK, hash canônico das definições inalterado, todos os runtime slugs registrados, rotas públicas 200 e browser sem imagens quebradas/overflow. Restaurar somente se um gate real falhar.

## Exportação e importação canônicas

Na origem já alinhada:

```php
$tools = lazyblocks()->tools();
$all   = lazyblocks()->blocks()->get_blocks( true );
$out   = array();
foreach ( $all as $block ) {
    $id = (int) ( $block['id'] ?? 0 );
    if ( $id > 0 && 'publish' === get_post_status( $id ) ) {
        $out[] = $tools->clean_block_to_export( $block );
    }
}
```

No destino:

```php
$id = lazyblocks()->tools()->import_block( $exported_block );
```

- Rode o import sob administrador autorizado e dentro de transação InnoDB junto da criação das páginas.
- Congele os IDs criados para rollback exato.
- Em falha antes do commit, `ROLLBACK`; em falha de validação pós-commit, remova somente os IDs congelados e exija o estado prévio por readback.
- Preserve payload, scripts, resultado, validação e manifesto SHA-256 em backup fora do webroot. Não apagar tentativas ou backups sem a confirmação destrutiva aplicável.

## Páginas

- Preserve slugs e função das páginas, mas adapte marca, domínio, links internos, copy e metadescription para cada destino.
- Remova referências ao domínio/brand de origem e parâmetros editoriais residuais como `utm_source=chatgpt.com`.
- Não clone locks, IDs de autor, scores Yoast ou metadados calculados. Metas Yoast vazias podem ser descartadas por hooks; não as use como gate de igualdade.
- Para evitar conteúdo duplicado, medir similaridade entre origem e cada destino e entre destinos, além de fazer leitura humana das partes alteradas. Linguagem legal inevitavelmente mantém termos oficiais, mas introduções, explicações e identidade editorial devem ser próprias.

## Validação

- Origem pós-update: backup válido, plugins/status preservados, definições Lazy Blocks hash-idênticas, todos os runtime slugs registrados, DB e rotas públicas saudáveis.
- Cada destino: contagem exata de páginas e blocos do exportador nativo.
- Reexportar cada bloco no destino com `clean_block_to_export()`, remover somente campos locais `id` e `edit_url`, e exigir hash igual ao export da origem.
- Exigir todos os `lazyblock/<slug>` registrados no `WP_Block_Type_Registry`.
- Páginas: conteúdo e meta esperados por readback, zero referência à origem, HTTP 200, canonical próprio, `index,follow`, presença no page sitemap e formulário/links funcionais.
- Navegador real em páginas representativas: H1, texto renderizado, imagens completas e `scrollWidth <= clientWidth`.

## Caso validado

Em Yolokfx 4.4.1, nove posts `lazyblocks` publicados correspondiam a oito blocos funcionais porque duas definições compartilhavam `cartao-de-credito`. O exportador nativo retornou oito blocos e escolheu `CARD ADX` para esse runtime slug. Escalate Power e Grow Power Hub receberam os oito exports canônicos com igualdade de reexport/hash, evitando importar a definição antiga concorrente.
