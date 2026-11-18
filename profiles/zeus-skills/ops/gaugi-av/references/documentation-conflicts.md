# Divergências e gates antes de escrita

## 1. Contrato de path
- TXT fornecido e /llm.txt live: `path` obrigatório no PUT da tradução; exemplo blog/my-article.
- Screenshots do PUT: não incluem path no request; response tem 101/my-post.
- Canário posterior autorizado Monteralis: PUT com `path` explícito relativo igual ao slug foi aceito e devolvido sem alteração em dois readbacks (v1/v2); ver `draft-write-validation.md`. Isso reconcilia o formato usado, não obrigatoriedade nem omissão. Para novos rascunhos equivalentes, usar path explícito validado. Não mudar URLs existentes como experimento.

## 2. Tipos de bloco e schemas
- Screenshots usam `prose` com data.html. Catálogo live inicial possui 19 tipos e **não** inclui prose. TXT usa paragraph.
- Schema live paragraph exige content **e align**, content até 3000; exemplo visual só exige content. Schema live heading level 2–4; não inferir H1.
- `custom-html` existe e aceita html até 65536 caracteres, mas não é substituição automática de prose nem garantia de scripts executáveis.
- Usar catálogo vigente de cada chamada, não converter silenciosamente. `default_data` pode conter strings vazias que violam minLength; completar antes de validar.

## 3. Recursos das imagens ausentes no TXT/live llm
- sitemap_exclude, list_exclude, hide_header.
- Tradução review, meta_title/meta_description, nulabilidade de excerpt.
- exclude_translation_locales/overwrite_manual_locales e fan-out.
- Filtros de listagem de artigos mais detalhados.
- Nenhum POST/PUT/DELETE foi executado na análise inicial. Em canário posterior Monteralis, sitemap_exclude/list_exclude=true e hide_header=false persistiram no shell e no readback. Tradução draft com meta_title/meta_description/excerpt também persistiu. Publicação, review e fan-out não foram testados.

## 4. Scopes e proteção de chaves
- Leituras 200 comprovam acesso aos recursos consultados, não write:* nem lista exata de scopes concedidos. /llm.txt pode ser público segundo linha duplicada do screenshot, então HTTP 200 autenticado não prova sozinho read:llm efetivo.
- Não há introspecção de scopes documentada. Confirmar configuração da chave na interface ou aproveitar uma operação real de escrita autorizada; nunca mutação fictícia/invalid body como probe.
- Tenant-scoped não significa autorização global. Inicialmente cada chave listou apenas o seu domínio. Revalidar antes de operar.

## 5. Outros detalhes não assumidos
- q de authors: imagem diz nome parcial case-insensitive; TXT diz nome ou slug. Buscar slug não foi testado.
- read:categories existe, porém sem GET categories standalone; metadata pode vir em artigo. Não inventar endpoint.
- /llm.txt é path real testado, não /llms.txt; screenshots duplicam scope e divergem sobre público/auth.
- GET translation expõe campos extras como scheduled_at/OG/canonical/noindex; leitura não demonstra escrita/agendamento suportado.
- Upload de logo/favicon não aplica identidade global. Bloco landing-page possui flags de ads, mas isso não concede controle de rede/loader/posições globais nem supera monetização protegida.
- Não há suporte documentado a publish scheduling, idempotency keys, PUT concorrente seguro, restaurar deletes ou restore integral.
