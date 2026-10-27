---
name: content-article-quality-audit
description: Conferir artigos WordPress antigos/atuais de sites MGS, validando inventário completo via yydev-show-pages, tags REC/P1, links REC→P1, botões/CTAs e planilhas de auditoria.
---

# content-article-quality-audit

## Quando usar

Use esta skill quando Rodolfo ou Raquel pedir conferência/auditoria de artigos WordPress já publicados, especialmente:

- validar se todos os artigos de um site entraram em uma planilha;
- conferir tags de REC e P1;
- identificar artigos faltando tags padrão;
- mapear REC → P1 por botões/cards/LazyBlocks;
- encontrar links divergentes em botões/CTAs;
- auditar conteúdo antigo antes de correção editorial.

Esta skill é de **Content Operations** e pertence à Atena. Zeus pode auditar/orquestrar quando houver erro recorrente, divergência de contagem ou risco técnico.

## Definir cobertura antes da coleta

1. Classifique o pedido como inventário completo do site, lote fechado de artigos ou revisão de IDs existentes.
2. Para lote fechado, use o manifesto autorizado como denominador: preserve os IDs esperados, inclusive bloqueados e ainda não criados. Confira unicidade e cobertura em código; não enumere o site inteiro para reconstruir um lote conhecido.
3. Para inventário completo de um site autorizado, use a lista autenticada de `yydev-show-pages` e reconcilie os IDs com os registros consultados. Uma contagem isolada ou um sitemap não prova cobertura integral.
4. Filtre registros institucionais por ID, chave ou fonte editorial pertinente **antes** de emitir saída; um lookup de continuidade não deve virar dump de registro global ou inventário de outros escopos.

## Inventário completo de um site

Quando esse for o escopo autorizado, consulte `yydev-show-pages`:


1. Logar no WordPress do domínio.
2. Abrir no navegador:

```text
https://dominio.com/wp-admin/admin.php?page=yydev-show-pages
```

3. Ler a seção:

```text
There are xxx published posts
```

4. Usar essa lista/contagem como referência para cobertura.
5. Só usar `post-sitemap.xml` como fallback/proxy quando não houver sessão WP Admin. Se usar sitemap, reportar que ele pode esconder posts e não é validação 100%.

## Estados e evidências por artigo

- Separe conteúdo preparado, cadastro confirmado, `publish` observado e QA público aprovado. HTTP 200, gravação de metadata ou score isolado não encerra o artigo.
- Vincule cada aceite ao domínio, post ID, URL, status e hash do corpo atual, com caminhos e hashes de evidências reais. Uma revisão de corpo exige nova análise e novas provas; não reaproveite silenciosamente o aceite anterior.
- Defina os gates pelo briefing antes de escrever o relatório. Quando `Não verificado` for expressamente aceito para uma métrica, mantenha a limitação explícita, sem nota/cor inventada nem bloqueio adicional não solicitado; isso não dispensa os demais gates ou supersede contratos com exigência de score mínimo.
- Use rótulos distintos para falta de comprovação e defeito observado: ausência nas páginas de arquivo consultadas não prova ausência no arquivo inteiro; divergência de HTML/schema pode exigir diagnóstico mesmo com cadastro correto.
- Superseda uma pendência histórica somente com prova atual do mesmo objeto e gate. Preserve o histórico e os outros blockers; resolver a bio não aprova automaticamente sitemap, idioma ou layout.
- Grave cada nova coleta em arquivo/label próprio. Não sobrescreva evidências referenciadas por aceites com hash, pois isso invalida sua proveniência.

## Explicar pendências de um relatório existente

1. Localize o checkpoint da iniciativa e siga seu índice até a projeção e o relatório atuais. Não use os contadores iniciais do manifesto nem uma mensagem antiga como estado vigente: o manifesto pode preservar o plano enquanto os recibos registram a execução posterior.
2. Leia a aba exata da planilha pela API e selecione por nomes de cabeçalho o ID local, status e etapa/pendências. Agregue os motivos por código antes de emitir saída; não imprima todas as células nem o registro institucional inteiro para responder uma pergunta de andamento.
3. Reconcilie os motivos com as evidências atuais por artigo. Use o relatório consolidado para os totais, mas a prova mais recente do mesmo objeto/gate para saber o que ainda falta; um diagnóstico antigo de biografia ou layout pode ter sido supersedido sem encerrar outros gates. Não apresente uma coleta histórica como nova verificação pública.
4. Agrupe a explicação em linguagem editorial: presença em categoria/sitemap; autoria; idioma/datas/canonical; layout; fontes externas. Separe falta de comprovação de defeito confirmado e indique quais grupos dependem de execução editorial, manutenção técnica ou decisão humana. Não atribua todos os casos a cache nem trate indexação no Google como requisito automático de QA.
5. Abra com a distinção entre publicado e validado; mantenha artigos ainda não publicados em grupo separado. Dê um exemplo específico apenas quando sustentado pela evidência atual. Se informar contagens por motivo, deduplique por ID e avise que os grupos podem se sobrepor; não some pendências sobrepostas como se fossem artigos diferentes.

## Colunas padrão da planilha

Para auditoria REC/P1 completa, usar:

1. `Data REC`
2. `Artigo REC`
3. `Tags REC`
4. `Data P1`
5. `Artigo P1 / Link Final`
6. `Tags P1`
7. `Tipo`
8. `Links nos botões`
9. `Alerta links`
10. `Tags faltando` quando Rodolfo pedir auditoria de tags padrão.

Manter uma linha por REC/artigo principal. Se uma P1 já aparece na coluna E como destino de uma REC, ela **não deve aparecer duplicada na coluna B**.

## Descoberta REC → P1

A relação REC→P1 vem dos links reais dentro do artigo, não do slug.

1. Abrir o artigo público.
2. Extrair links apenas do corpo editorial real:
   - `article.main-content`, `jd-post-content`, conteúdo do post;
   - botões/cards/LazyBlocks;
   - comentários HTML com LazyBlock devem ser desempacotados para leitura.
3. Ignorar:
   - menu;
   - footer;
   - sidebar;
   - breadcrumbs;
   - related posts;
   - category/tag/archive links;
   - social links;
   - imagens e anexos.
4. Se muitos RECs apontarem para a mesma P1 sem sentido, parar: provavelmente o parser capturou related posts/widget, não CTA real.
5. Seguir redirects de links internos antes de classificar P1. A URL final/canônica é a que deve ir na coluna E.
6. Manter URL original em `Links nos botões` quando for útil para auditoria, especialmente IP legado ou typo corrigido por redirect.

## Tags REC/P1

Para cada URL interna representada na planilha:

1. Extrair post ID do HTML público:
   - `postid-123`;
   - `/wp-json/wp/v2/posts/123`;
   - shortlink `?p=123`.
2. Buscar dados pela rota correta:

```text
/wp-json/wp/v2/posts/{id}?_fields=id,date,link,slug,tags,title,status
```

3. Resolver tags via:

```text
/wp-json/wp/v2/tags?include=...
```

4. Não confiar só em `/wp-json/wp/v2/posts?slug=...`; em sites MGS essa rota pode retornar `[]` para posts publicados e causar falso “sem tag”.
5. Coluna `Tags REC` e `Tags P1` não devem ficar vazias para artigo interno.
6. Se a rota correta por ID confirmar `tags: []`, escrever exatamente:

```text
SEM TAGS NO WP
```

Não apagar a linha e não deixar vazio.

## Auditoria de tags faltando

Quando Rodolfo pedir para identificar tags padrão faltando, adicionar coluna `Tags faltando`.

Não tentar adivinhar qual país ou vertical específica deveria ser. Validar só a presença das classes obrigatórias.

Para REC, deve existir:

- uma tag de vertical, ex.: `cc`, `emp`, `car` etc.;
- uma tag de país, ex.: `br`, `us`, `es`, `za` etc.;
- uma tag de língua, ex.: `lang_en`, `lang_es`, `lang_pt` etc.;
- a tag `rec`.

Para P1 interna, deve existir:

- uma tag de vertical;
- uma tag de país;
- uma tag de língua;
- a tag `p1`.

Formato da coluna:

```text
OK
REC faltando: vertical, país
P1 faltando: língua, p1
REC faltando: país | P1 faltando: p1
N/A
```

Use `N/A` apenas quando a linha não for REC/P1 interna auditável, por exemplo artigo SEO sem P1 interna.

## Links e botões

Para cada artigo:

1. Conferir todos os botões/cards/LazyBlocks dentro do corpo editorial.
2. Preencher `Links nos botões` com todos os destinos encontrados.
3. Se mais de um destino real aparecer, preencher `Alerta links` com:

```text
LINKS DIFERENTES NOS BOTÕES
```

4. Se houver mais de uma P1 interna possível:

```text
MAIS DE UMA URL INTERNA/P1
```

5. Se link com IP legado for canonicalizado:

```text
IP LEGADO CANONICALIZADO
```

6. Se tudo estiver consistente:

```text
OK
```

## Fontes públicas: transporte, conteúdo e aderência factual

- Registre separadamente HTTP/URL final efetivamente observados, recuperação de conteúdo substantivo e sustentação do trecho citado. Texto obtido pelo extrator sem status/frescor expostos não autoriza declarar GET direto 200 ou recurso atual comprovado.
- Não rotule 403, desafio 202 vazio, falha TLS ou timeout como link morto/404. Use tentativas independentes limitadas e mantenha a limitação explícita; não troque hrefs só para esconder uma barreira de acesso.
- Compare o parágrafo exato com a fonte lida. Não equipare automaticamente materiais, termos legais ou características parecidas. Se um termo não estiver sustentado, registre a lacuna e prepare a menor correção editorial com revisão/hash/análise correspondentes; não fabrique apoio factual ou recalcule uma nota fixa.

## Escrita em Google Sheets

Drive e Sheets usam exclusivamente a Service Account corporativa `mgsagent@mgs-core-prod.iam.gserviceaccount.com`, projeto `mgs-core-prod`, pelo helper `/root/mgs-agent/scripts/mgs_google_workspace_auth.py`. Confirme a identidade/projeto e use somente os IDs de arquivos do escopo. Falha de acesso/API bloqueia a escrita externa: não usar token pessoal, consentimento de navegador, edição pública/browser paste ou outra identidade como fallback. Preserve o snapshot local e reporte o bloqueio. Arquivos novos de automação vão para `MGS-AGENTS`; Sheets existentes precisam estar compartilhadas com a SA.

Valide o range escrito por GET da API e igualdade integral com a base local; export CSV é evidência complementar quando disponível, não substituto da identidade canônica.

### Apresentação de planilhas para revisão humana

Quando a gestora pedir reorganização, aplique o formato solicitado sem mudar os resultados da auditoria: domínio na primeira coluna, linhas de subtítulo por domínio, categorias/tags apenas com nomes e IDs técnicos fora da apresentação. Preserve a relação interna artigo → linha em artefato local, incluindo os ainda não publicados, e conte somente artigos, nunca as linhas de subtítulo. Traduza cada pendência a partir da evidência atual do objeto, diferenciando defeito observado, falta de comprovação e dependência de autorização; não exponha dicionários, flags ou pendências históricas já supersedidas. Mantenha limitações aceitas do Yoast separadas de bloqueios reais.

Antes de reestruturar, salve valores/formatação/permissões, confira fórmulas, notas, proteções e alterações humanas concorrentes. Use somente a Service Account canônica. Compartilhamento individual com a própria gestora autorizada deve preservar os demais acessos e ser confirmado pelo GET da permissão exata. Após o write, compare todas as células com a intenção, valide agrupamentos, IDs removidos, estados preservados e uma linha além do fim. Registre o novo contrato de apresentação na continuidade da tarefa; nenhum atualizador legado pode reintroduzir o formato antigo ou sobrescrever edições humanas sem reconciliação.

**Pitfall de Google Sheets:** uma célula mesclada não pode atravessar a fronteira entre colunas congeladas e não congeladas. Para subtítulos mesclados na largura inteira, congele apenas o cabeçalho ou mantenha todas as colunas da mesclagem do mesmo lado. Uma rejeição de batch por esse conflito exige GET para confirmar o estado, preservação da intenção anterior e envio de uma nova intenção corrigida, sem replay cego.

Para atualizar o relatório:

1. Reutilize o Spreadsheet ID e a aba confirmados; preserve outras abas, colunas humanas e ACLs. Recriação ou limpeza ampla não é pré-requisito de atualização.
2. Monte a matriz completa em snapshot local, na ordem de colunas pedida, antes do write. Envie valores `RAW` e formato `TEXT` para preservar URLs, identificadores e datas literais, sem fórmulas ou coerção numérica.
3. Confira por GET a igualdade de todas as células e a quantidade exata de linhas; leia também uma linha além do fim esperado para detectar resíduos.
4. Se houver linhas antigas excedentes, limpe somente o intervalo residual confirmado e autorizado. Revalide valores e formatação após a escrita; alguns writes normalizam o formato de célula.
5. Rotule snapshots de progresso como progresso e mantenha timestamps de observação, pois GETs entre vários sites não formam uma transação única.

## Validação final obrigatória

Antes de dizer que terminou:

- [ ] cobertura e IDs batem com o manifesto do lote fechado; em inventário completo, foram reconciliados com `yydev-show-pages` quando disponível;
- [ ] se usou sitemap, reportou que é fallback e listou diferenças;
- [ ] coluna B está A-Z se Rodolfo pediu ordenação;
- [ ] sem linhas totalmente vazias;
- [ ] coluna B sem vazio;
- [ ] `Tags REC` sem vazio para URL interna;
- [ ] `Tags P1` sem vazio para P1 interna;
- [ ] `SEM TAGS NO WP` só quando `/posts/{id}` confirmou `tags: []`;
- [ ] P1 representada na coluna E não aparece duplicada na coluna B;
- [ ] `Links nos botões` preenchido;
- [ ] `Alerta links` preenchido;
- [ ] `Tags faltando` preenchida quando existir essa coluna;
- [ ] GET da API confirma integralmente a matriz final e detecta linhas excedentes; CSV, quando usado, também bate com a base local.

## Entrega e escalonamento

Entregue o relatório solicitado e os bloqueios materiais, não o trace completo da coleta. Informe falha, efeito parcial e limitação de prova sem transformar hipótese em causa. Encaminhe dependências técnicas com URLs/IDs/evidências delimitados, separando-as da autorização editorial; um retorno técnico não amplia o escopo autorizado.
