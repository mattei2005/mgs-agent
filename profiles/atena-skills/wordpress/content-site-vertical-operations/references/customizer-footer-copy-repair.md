# Aviso de rodapé armazenado no Customizer

## Escolher o objeto correto

- Compare o texto público de `footer .footer-disclaimer` com `content.raw` antes de editar um artigo. Se o aviso não está no corpo, não regrave o post para corrigir o rodapé.
- Leia o renderer instalado para distinguir string hardcoded, widget, template e cópia armazenada por idioma. Em temas que usam `get_theme_mod`, confirme a chave literal e os fallbacks reais; um disclaimer PT pode coexistir com chaves EN/ES independentes.
- Prefira corrigir a cópia na origem existente a instalar PHP/filtros ou editar templates. Limite a alteração ao componente e idioma cobertos pelo pedido; registre que um rodapé é compartilhado, sem supor autorização para outros idiomas ou todo o portal. Preserve locale, enable flag, identidade legal, divulgacões de publicidade, URLs e markup.

## Execução nativa restrita

1. Resolva domínio/site_key/owner/webroot/identidade e o transporte canônico já permitido. Uma recusa REST de `settings` com Editor não autoriza elevação, nova credencial nem transporte improvisado; uma manutenção nativa só é admissível com acesso existente certificado e autoridade cobrindo a operação concreta.
2. Capture a linha da opção com ID, bytes serializados e autoload, o valor da chave, as demais theme mods, os arquivos renderizadores e os campos de posts protegidos. Prepare diff de substituições exatas; exija inverso byte-exato e markup idêntico.
3. Inspecione `pre_set_theme_mod_<chave>`, `pre_update_option*`, `update_option*`, `updated_option`, sanitização e seus efeitos reais. Confira também a lista de opções que acionam limpeza de sitemaps/cache; nomes de APIs nativas não garantem isolamento. Não execute save se houver purge amplo ou efeito protegido não contido pelo escopo.
4. Para a rota nativa já autorizada, use `set_theme_mod` da instalação, com CAS da linha completa e snapshot protegido. Preserve autoload. Quando a implementação permitir, limite o query guard a um único UPDATE exato emitido pelo WordPress e use transação/row-lock somente após certificar InnoDB; reverta em falha. Isso não é uma autorização genérica de SQL ou de mudança de configuração.
5. Registre intenção antes da transmissão e não repita após timeout/recibo incompleto. Faça readback independente em outro processo; comprove a alteração de uma única chave, demais idiomas e opções idênticos, templates/posts/metas/taxonomias/indexables preservados.

## Público e cache

- Um `set_theme_mod` correto não invalida necessariamente WP Fastest Cache. Confronte a URL normal com a cópia literal de `cache/all/<path>/index.html` e qualquer variante mobile realmente existente. `cf-cache-status:DYNAMIC` não exclui cache de origem.
- Antes de invalidar, comprove a representação antiga e a natureza regenerável, fingerprint do método instalado, owner/no-symlink e backup. Exija intenção por URL; nunca amplie para site/host ou outras páginas só porque o rodapé é compartilhado.
- Valide a mesma URL normal em desktop e mobile, sem login/query especial. Cache local do navegador pode ser desativado apenas no contexto de QA e restaurado depois, sem confundir isso com purge de produção. Confira texto/contraste/quebra lateral, canonical/idioma e preservação do artigo.
- Diferencie cópia corrigida na origem, URL específica comprovada e propagação para outros caches não consultados. Não declare todo o portal renovado a partir de uma URL.
