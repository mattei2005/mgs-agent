# Auditoria de artigos irrelevantes/spam em WordPress

Use quando Rodolfo perceber posts publicados que não combinam com o domínio, especialmente cassino/apostas, conteúdo adulto, idiomas inesperados ou clusters automatizados.

## Escopo e segurança

- A auditoria é read-only: não alterar status, autor, conteúdo, tags ou arquivos.
- Coletar diretamente de WordPress runtime: WP-CLI/DB para RunCloud e REST autenticado para externos.
- Para cada site, obter até 500 posts publicados recentes com ID, data, modificação, título, slug, autor e categorias.
- Salvar a evidência detalhada em `reports/wordpress-spam-audit/` e manter checkpoint da iniciativa.

## Detecção em camadas

1. Buscar termos fortes de spam: casino/cassino, slot, betting/bahis, poker, roulette, Mostbet, 1xBet, Betandreas, Chicken Road, conteúdo adulto/pharma etc.
2. Detectar idiomas e marcas incompatíveis com o domínio.
3. Agrupar por site, autor e janela temporal.
4. Revisar todos os posts recentes do autor/cluster, não apenas títulos que bateram em keywords.
5. Validar controles para evitar falso positivo:
   - `Aviator` pode ser cartão AAdvantage;
   - `Banque Casino` pode ser instituição financeira;
   - “betting on AI” pode ser expressão editorial;
   - “slot” pode ser microSD/card slot.
6. Confirmar títulos da evidência do usuário e relacioná-los ao domínio/IDs reais.

## Critério de site comprometido/sinalizado

Sinalizar somente quando houver cluster coerente de posts recentes e incompatíveis, por exemplo:

- muitos posts em poucos dias/semanas;
- mesmo autor em vários domínios;
- títulos em múltiplos idiomas sem relação com a vertical;
- cassino, apostas, conteúdo adulto ou links promocionais externos;
- categorias legítimas reutilizadas para conteúdo incompatível.

Relatar por site:

- quantidade confirmada;
- primeira e última data;
- autor comum;
- 2–5 títulos de exemplo;
- correspondência com screenshot/link fornecido.

## Investigação forense além dos posts

- Em site possivelmente comprometido, começar por leitura estática de arquivos e SELECT em transação read-only; não carregar WordPress, tema ou MU-plugins via WP-CLI/PHP como root apenas para obter inventário.
- Auditar também todas as páginas publicadas, revisões e HTML de cache. A exclusão de artigos não remove links de apostas inseridos em páginas institucionais com `left:-9999px`, altura de 1px ou outros estilos ocultos. Confirmar cada alvo no banco e na URL pública; título legítimo não prova conteúdo íntegro.
- Correlacionar `post_date_gmt`/`post_modified_gmt` das revisões com access logs usando timestamps UTC e janela explícita. `post_author` indica atribuição à conta, não identifica a pessoa; HTTP 200 de XML-RPC pode conter erro e não prova autenticação ou publicação. Ausência de request bodies mantém essa lacuna mesmo com correlação forte.
- Distinguir comprometimento de conteúdo, backdoor em arquivo, exploração ativa e credencial suspeita. Checksums oficiais íntegros não eliminam injeção persistida no banco.
- Conferir IP real: endereços de proxies Cloudflare em access logs e sessões não identificam a origem do atacante. Não atribuir ações a IPs de proxy nem a user-agents autodeclarados.
- Comparar versões instaladas com advisories e changelogs oficiais. Separar versão afetada, exploração reproduzida e causa histórica; não chamar toda atualização de correção de segurança.

## Coleta sem exposição de credenciais

- Coletar somente metadados permitidos; nunca retornar o conteúdo de `wp-config.php`, mesmo com uma denylist de constantes. Chaves de plugins e salts adicionais escapam de listas fixas. Para flags, retornar nome/presença ou booleano; para autenticação, retornar apenas nomes, datas e contagens, sem hashes, tokens, TOTP ou códigos de recuperação.
- Restringir leitura de configuração Nginx a arquivos `.conf` exatos. Nunca usar glob que leia diretórios SSL completos: certificados e chaves privadas podem estar juntos.
- Agregar logs no servidor por janela, endpoint, status e user-agent; preservar linhas relevantes em evidência privada e retornar apenas resumo. Evitar duplicar milhões de linhas em JSON wrapper e JSON interno.
- Antes de classificar um usuário de sistema como sem acesso, confirmar que ele existe no host. Testes de isolamento de um servidor não se aplicam a outro host com o mesmo nome de usuário.
- Se um valor sensível escapar para um resultado, não o repetir nem declarar o histórico saneado. Conter cópias locais, corrigir e testar a coleta, comunicar a exposição e solicitar a confirmação crítica para a rotação; chaves de criptografia de 2FA exigem plano que preserve ou recadastre os autenticadores.

## Contenção e remediação

A auditoria não autoriza contenção. Mudanças de senha, application password, usuário, permissão ou credencial exigem confirmação crítica. Exclusão de posts também exige confirmação crítica e alvo exato. Antes de propor exclusão:

1. exportar IDs/títulos/datas/autores;
2. decidir quarentena (`draft`) versus exclusão;
3. provar que controles legítimos foram excluídos do target set;
4. criar backup/rollback;
5. validar publicamente após a ação.

## Limpeza cirúrgica de HTML injetado

- Interpretar aprovação de limpeza das páginas e caches como esse escopo somente; não estender para credenciais, 2FA, plugins, PHP, firewall, outros sites ou exclusão de revisões.
- Revalidar home/siteurl, tema, IDs, slugs, tipos/status e hashes antes de escrever. Preservar backup individual por página e por objeto de cache, fora do webroot e com acesso restrito; validar hashes por readback independente.
- Remover por offsets dos nós HTML revisados, sem reserializar o documento inteiro. Exigir simultaneamente ocultação reconhecida e links para domínios já classificados; abortar diante de domínio novo, sobreposição ou nó contendo formulário/script/iframe/imagem legítimos. Todo byte fora dos intervalos removidos deve permanecer idêntico.
- Se uma página auxiliar resultar vazia, verificar sua função/template e a configuração da homepage antes de aplicar. Não inventar conteúdo para preencher vazio; a homepage real pode ser renderizada pelo tema, independentemente do post_content auxiliar.
- Quando o core/plugins foram verificados mas bootstrap tem side effects indesejados, uma atualização restrita de post_content pode usar transação InnoDB, locks e compare-and-swap de hash. Validar primeiro a conversão UTF-8 em tabela temporária e checar engine, identidade e total de linhas. Ausência de object cache persistente deve ser confirmada; caso exista, planejar sua invalidação específica.
- Usar canário em uma página, validar publicamente e só então concluir o restante do conjunto autorizado. Preservar títulos, autores, slugs, status, metadados, revisões históricas e outros posts.
- Não confundir saneamento de cache com purge global. Se a estratégia aprovada for atualizar os mesmos fragmentos nos objetos HTML servidos, exigir os mesmos links por página, hashes antes/depois e troca atômica preservando owner/mode; isso não autoriza remover diretórios. Purgar Cloudflare somente pelas URLs afetadas, sem purge_everything.
- Validar banco, cache local, URL pública sem query, URL com cachebuster e origem direta. Comparar HTML público inteiro contra baseline menos as remoções aprovadas, além de scripts, formulários, iframes, homepage, ads.txt e sitemap. **Esse diff sozinho não prova limpeza completa**: uma cópia fiel pode preservar metadados derivados do spam. Auditar explicitamente `description`, `og:description`, `twitter:description`, JSON-LD, excerpts e tabelas auxiliares Yoast. Ampliar a autorização antes de editar campos não previstos; preferir regeneração dirigida dos objetos derivados quando aprovada. Não afirmar entrega real de anúncios ou envio do formulário quando apenas o código/markup foi validado.

## Segunda passada e validação de falsos positivos

- Varrer campos textuais de todas as tabelas do alvo, inclusive índices SEO e postmeta/options, emitindo somente IDs, nomes de campos e indicadores — nunca valores de autenticação. Separar conteúdo publicado, revisões históricas e índices derivados: `wp_yoast_seo_links` pode preservar URLs já retiradas do frontend sem constituir nova reinjeção.
- No `wp_yoast_indexable_hierarchy`, `ancestor_id=0` é o sentinela válido de raiz, não um ancestral órfão. O predicado correto para integridade é `indexable_id` inexistente ou (`ancestor_id<>0` e ancestral inexistente). Antes de apagar hierarquias em massa, comparar com backup restore-tested e validar os indexables que permanecerão; se o sentinela for classificado incorretamente, restaurar somente as linhas ainda válidas por manifesto, dry-run, canário e readback.
- Comparar descrição social na URL sem query com resposta sem cache. Spam apenas no HTML de cache e ausente do conteúdo/metadados de runtime é resíduo de renderização; purge de Cloudflare não elimina cache de aplicação. Verificar todo o conjunto de páginas/posts publicados, com coleta persistida por lote e count/dedupe programáticos.
- Decodificar formatos nativos de plugins antes de declarar snippets limpos. Ad Inserter pode usar prefixo `:AI:` seguido de base64 de PHP serialization; usar unserialize com `allowed_classes=false`, sem carregar WordPress nem avaliar o código. Retornar somente indicadores e hashes dos campos decodificados.
- Não classificar `<?=` encontrado em imagem como webshell. Validar formato, CRC, chunks e bytes após IEND em PNG; marcadores curtos em IDAT comprimido podem ser coincidências binárias. Código PHP longo em metadados/trailer exige investigação separada. Não executar a imagem como PHP para testar.
- Distinguir arquivo não coletado por limite de tamanho de arquivo alterado. Completar seu hash separadamente e comparar ao baseline. Em temas inativos, nomes truncados podem conter bytes idênticos ao pacote oficial; verificar equivalência antes de insinuar backdoor.
- Ao reproduzir diagnóstico público de plugin, medir o impacto: comparar o trecho devolvido ao HTML normal sem autenticação e identificar PHP versus HTML/JS. Painel de debug habilitado não prova exposição de senha nem de PHP se o conteúdo já era público. Nunca imprimir os trechos potencialmente sensíveis.
- Auditar privilégios SQL globais além do bind localhost e do usuário do próprio WordPress. Outras contas com SELECT/UPDATE/SUPER/FILE globais ampliam o risco ao banco do alvo, mesmo que a conta do site esteja restrita. Não revogar permissões sem mapa de consumidores, rollback e confirmação crítica; não atribuir concessões a invasão sem reconciliação institucional.
- Reproduzir falhas HTTP e correlacionar com log atual e linha de código. Separar defeito funcional do tema (como declaração duplicada de função) de vulnerabilidade usada na invasão. Auditoria read-only não autoriza patch de tema.

## Auditoria de portfólio e fechamento de cobertura

- Reconciliar API paginada de servidores/apps com `server_name` do Nginx e aliases www; contar apps e hostnames separadamente. Incluir servidores visíveis pela API sem SSH como cobertura parcial explícita, sem criar credenciais alternativas.
- Persistir cada lote e calcular cobertura/dedupe em código antes de consolidar. Respeitar `Retry-After`, reduzir concorrência e retomar somente objetos ausentes; não confundir timeout do coletor com indisponibilidade do site.
- Contar tabelas volumosas antes de selecionar indicadores; registrar quais campos tiveram leitura integral e quais foram filtrados. Aplicar `START TRANSACTION READ ONLY` e validar identificadores SQL antes da interpolação; não executar código WordPress para obter inventário.
- Comparar checksums por versão e locale corretos e revisar arquivos extras separadamente. Uma árvore com arquivos oficiais íntegros ainda pode conter loaders, login paralelo e webshells adicionados em outros nomes. Cruzar os hashes confirmados entre apps sem executar os arquivos suspeitos.
- Triar diferenças contra o pacote original: placeholders traduzidos, quebras de linha e cabeçalhos de distribuição não comprovam malware. Inspecionar alterações executáveis e valores de includes/URLs separadamente; normalização indiscriminada de todos os literais não prova equivalência funcional.
- Não deduzir ausência na origem a partir de um corpo vazio, redirect ou erro do transporte. Registrar status, tamanho e rota final de público/origem; prova no banco continua válida mesmo quando o template não renderiza o conteúdo ou a sonda de origem não entrega HTML.
- Manter credenciais e código de autenticação fora da planilha: exportar metadados, capacidades, hashes e caminhos necessários, nunca valores. Publicar com `RAW`, preservar o arquivo/ID e dados preexistentes, separar confirmação de candidato e conferir todas as células após a formatação pela Service Account canônica.
- Encerrar somente com totais de coleta conferidos, workers próprios terminados, limitações explícitas, Sheet relida e inventário/checkpoint/REPORT-INFRA registrados. Uma auditoria concluída não equivale a remediação autorizada.

## Fechamento de limpeza em lote e resíduos fora dos alvos

- Não usar o total de nós ocultos como total de publicações comprometidas. Examinar também artigos inteiros de spam, listas visíveis de links, anchors ocultos diretamente por CSS, metadados e objetos HTML de cache; cruzar resíduos Yoast por post_id com o status real do post. Índice órfão, artigo ainda publicado e cache que continua servindo um artigo são estados diferentes.
- Congelar domínios, IDs, caminhos e hashes do escopo confirmado. Se a validação revelar outras publicações ou arquivos fora desse manifesto, não ampliar nem reduzir silenciosamente o lote: documentar os novos alvos na planilha, distinguir a conclusão do lote da limpeza integral e pedir autorização explícita para a extensão. Não declarar um domínio totalmente limpo enquanto outro artigo confirmado continue público.
- Para variantes que o parser anterior não reconhecia, revisar os bytes antes de promover a regra. Nós p/a, listas de links visíveis, spam textual sem href e marcadores adjacentes exigem classificação explícita e manifesto por hash; ocultação ou a palavra casino isoladas não autorizam remover conteúdo. Preservar scripts, imagens, formulários e todos os bytes fora dos intervalos revisados.
- Em inventários SQL, uma lista vazia de slugs deve omitir o predicado, nunca virar post_name IN (''): isso seleciona milhares de drafts legítimos. Para correspondência byte-exata de slugs, usar literais hex binários e não misturar collations de múltiplos CONVERTs. Retornar o trecho final do erro SQL, não uma cópia enorme da query.
- Readback de metadata deve separar alterações operacionais de contadores/transients atualizados pelos próprios GETs. Identificar a chave exata e confirmar o código que a escreve; registrar a exceção específica, sem dispensar a comparação dos demais metadados nem prometer que nenhum metadado mudou.
- Verificar backups independentemente do processo que os criou e fora do webroot. Após remover arquivos maliciosos confirmados, validar ausência no filesystem e HTTP das rotas sem acioná-las antes da remoção. Atualizar a Sheet por células com comparação prévia, preservando decisões e fórmulas, e reler todos os dados após a formatação.

## Quarentena, redirecionamentos e fechamento de caches

- Antes de propor um lote como fechamento da limpeza de um domínio, reconciliar todo o conjunto publicado, não somente posts apontados pelo Yoast ou por hosts já conhecidos. Incluir padrões de spam de apostas, adulto/pharma, marcadores de verificação e publicações legítimas com injeção; separar candidatos de achados confirmados. Uma lista de indicadores é um detector, não um inventário exaustivo de comprometimento.
- Para quarentena, conferir simultaneamente `?p=ID` sem seguir redirects, permalink com e sem cachebuster, origem, ID do post no body e canonical final. O WordPress pode redirecionar um slug de post draft para outro post com slug semelhante: HTTP 200 no destino não prova falha da transição de status, mas também não prova recuperação pública se o destino contém spam.
- Inventariar caches depois das sondagens prévias e imediatamente antes do manifesto de confirmação: GETs podem criar novos objetos. Incluir home, categorias, autor, paginação, feeds/sitemaps e sidebars que ainda referenciam os posts, além do cache próprio de cada URL. Remover somente os caminhos autorizados; uma transição publish→draft não invalida automaticamente HTML estático quando aplicada por SQL.
- Se o conteúdo já está draft mas o permalink ainda entrega o mesmo post por cache não incluído na confirmação, reportar recuperação pública incompleta. Não substituir esse diagnóstico por sucesso no banco nem contornar o gate de exclusão alterando artificialmente o arquivo; pedir a ampliação necessária com o escopo completo de caches correlatos, em vez de novos recortes mínimos repetidos.
- Para exportações MySQL JSON por registro, separar stdout estritamente por `\n`, não por `str.splitlines()`: U+0085/U+2028/U+2029 podem existir legalmente dentro de strings JSON e quebrar artificialmente um registro. Testar a restauração dos backups em tabelas temporárias, nunca restaurar spam em produção para provar rollback.
- Em bases com dezenas de milhares de publicados, persistir cobertura de todos os registros, critérios de classificação e evidências por ID. Exigir coerência temática no corpo, abertura e promoção externa; rejeitar regras relaxadas que passam a classificar artigos legítimos sobre hotéis/tecnologia apenas por links injetados. Uma amostra validada não equivale a revisão humana individual de todo o conjunto. Preservar os inconclusivos e relatar seu número; não certificar limpeza integral a partir do sucesso da quarentena.
- Não usar `post_type=page`, um autor ou um intervalo de IDs como whitelist sem evidência individual: páginas também podem conter artigos promocionais completos e autores compartilhados não provam legitimidade. Reconciliar os registros excluídos do classificador com controles reais; candidatos inicialmente preservados não são sinônimo de conteúdo revisado/limpo.
- No RunCloud, um bloqueio de XML-RPC já confirmado pode usar include específico `extra.d/<app>.location.main-before.<nome>.conf`, sem modificar o vhost gerado. Revalidar o include e a identidade do app, guardar configuração/hash fora do webroot, executar `nginx-rc -t` antes/depois e reload com rollback. Validar GET/POST, query, www/redirect, case e path-info, além de home e REST. A confirmação de um domínio não dispensa o Critical Subset para outro alvo; autorização genérica de autonomia não altera AGENT.md.
- Comparar IDs antes/depois, além de hashes: um novo post durante a limpeza evidencia escrita concorrente, não falha da transição dos alvos anteriores. Reconciliar autoria/autorização e correlacionar UTC com logs sem atribuir autoria ao `post_author` ou sucesso a HTTP 200 do XML-RPC; uma limpeza de conteúdo não autoriza bloquear o endpoint ou rotacionar credenciais.
- Para conjuntos volumosos de conteúdo, evitar alternação regex grande tanto em SQL quanto no consumidor streaming. Usar leitura `mysql --quick` com limites de tempo e comparação literal/algoritmo adequado; persistir cobertura e resultados por lote. Um consumidor CPU-bound pode bloquear a leitura e fazer a query estourar `max_statement_time` mesmo sem problema de autenticação ou indisponibilidade do banco.

## Caso de referência 2026-08-17

Auditoria de 54 sites/12.950 posts detectou sete sites com 272 posts recentes incompatíveis, concentrados no autor `rodmaster`, entre 2026-07-20 e 2026-08-17. Três controles com o mesmo autor (`eggbev.com`, `zytiva.com`, `finanzas.newsoun.com`) tinham empréstimos legítimos e não foram sinalizados. Evidência: `reports/wordpress-spam-audit/20260817-irrelevant-posts.json`.
