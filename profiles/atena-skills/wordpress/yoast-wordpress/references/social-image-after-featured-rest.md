# Imagem social antiga após troca editorial de featured_media

## Diagnóstico por objeto

Quando a imagem interna e `featured_media` estão corretos, mas `og:image`/Twitter continuam antigos, separe três provas: attachment/REST editorial, campos sociais do indexable e HTML canônico versus fresco. Não atribua o problema automaticamente a cache.

Em instalações inspecionadas do Yoast 28.3/28.6, o `WP_REST_Posts_Controller::update_item` salva o post antes de `handle_featured_media`. O post watcher pode construir o indexable ainda com a thumbnail anterior. A gravação posterior de `_thumbnail_id` não agenda o watcher de metas que aceita somente o prefixo `_yoast_wpseo_`. Confirme essa ordem e os hooks nas fontes instaladas; não generalize por versão nominal.

## Reparo editorial mínimo, somente quando comprovado

1. Congele IDs autorizados, hashes dos corpos atuais, permalink, attachment aprovado, taxonomia, datas, inputs SEO/sociais, uma linha de indexable, todas as metas do post/mídia, identidade/role, locales e opções.
2. Preserve overrides sociais explícitos. Um fallback `featured-image` antigo com inputs sociais vazios é diferente de uma imagem OG escolhida pelo editor.
3. Inspecione fontes, assinaturas e hooks dos métodos públicos instalados. A rota comprovada em contextos compatíveis foi obter o modelo exato existente pela query do repositório, executar `Indexable_Post_Builder::build($id,$model)` somente em memória e comparar todos os campos. Não use Reflection para invocar métodos protegidos.
4. Exija que a previsão mude somente os campos sociais derivados autorizados; `object_last_modified` só pode corresponder ao `post_modified_gmt` preservado. Se o builder propuser outro delta, pare. Não use SQL UPDATE de colunas nem um full builder que também reconstrói hierarquia/autoria/links.
5. Confira a seleção real de imagem por `Open_Graph\Image_Helper::get_image_by_id` e pelo helper Twitter. O URL pode ser uma variante legítima do mesmo attachment: valide ID, fonte, dimensões e previsão real; nunca normalize sufixos por inferência. Não exija universalmente igualdade com o original.
6. Antes de persistir pela rota pública inspecionada `Indexable_Helper::save_indexable`, revise a árvore de hooks e as opções. Se um hook tentaria normalizar configuração global, bloqueie. Quando flags já vazias tornarem o save um no-op efetivo de opções, exija igualdade completa antes/depois; não altere flags para satisfazer o guard.
7. Faça um canário real por combinação instalação/transporte, registre intenção antes do save e releia em outro processo nativo mais GET autenticado. Exija preservação completa de post, metas, mídia, taxonomia, datas, scores, locais e opções; somente a derivação social prevista e timestamps técnicos permitidos podem mudar. Expanda apenas após esse readback.
8. Uma mudança genuína de score pode disparar o watcher e recalcular imagem, mas notas já iguais podem não emitir `updated_post_meta`. Nunca grave nota intermediária/falsa para provocar hook e nunca confunda save PHP com análise linguística JavaScript.

## Cache e revalidação

- Confirme separadamente o HTML canônico sem query. REST/indexable novo não prova que o cache HTML foi atualizado.
- Prefira API semântica nativa de URL quando fonte e efeitos comprovarem escopo estreito. Algumas instalações têm `WpFastestCache::clear_cache_by_url` que só invalida o HTML desktop/mobile daquela URL; outras não têm. Revalide implementação, raízes, owner, caminhos literais, ausência de symlink, hashes/tamanhos e preserve backups antes da manutenção autorizada.
- Não use `singleDeleteCache`, toolbar ou purge global como fallback por parecerem targeted: podem chamar CDN/Varnish global mesmo com argumentos de pais desligados.
- Sem API semântica segura, mantenha a divergência como pendência e escale a dependência. Não contorne o Critical Subset com primitiva física direta, config temporária, método protegido ou resave artificial de conteúdo.
- Registre cache incidental e derivados UAG/otimização de mídia. Se `_uag_page_assets` ou Imagify mudar entre pre-read e write, reconcilie o delta observado, preserve o manifesto antigo e prepare nova revisão estrita; não relaxe automaticamente o hash completo nem restaure caches derivados.
- Após encerrar a correção social, capture um baseline NOVO para análise/persistência de scores sobre o corpo final; não reutilize snapshots anteriores à derivação de imagem.

## Transporte em lote

No WPClient com `urlencode(...,doseq=True)`, serialize `include` como CSV para posts e mídia. Parâmetros repetidos podem fazer o WordPress retornar só o último ID. Um smoke unitário não detecta esse problema: exercite mais de um ID e exija conjuntos/contagens exatos antes da expansão.
