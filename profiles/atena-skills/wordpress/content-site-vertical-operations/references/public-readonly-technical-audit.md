# Auditoria técnica pública somente leitura

- Revalide o gate antes da primeira rede com `python /root/mgs-agent/scripts/mgs-domain-scope.py check --agent atena --json <domínio>`; o domínio é argumento posicional, não `--domain`.
- Congele o manifesto canônico e confira em código quantidade, unicidade e igualdade de domínio/ID/URL. Use apenas GET público sem credenciais; helpers antigos chamados readonly podem importar WPClient e abrir vault/context=edit sem necessidade.
- Salve bytes do HTML, headers/cadeia HTTP, head completo, hora, hash e campos por URL; mantenha progresso incremental e agregue achados por código com alvos exatos. Reanalise os arquivos salvos para ampliar classificações sem refazer rede.
- Separe HTTP/canonical/title/description, robots de HTML e header e regras Googlebot do robots.txt. Header noindex da REST, robots.txt ou XML não demonstra noindex da página de artigo.
- Compare OG, primeira imagem interna e imagem referenciada por Article.image com as URLs de tamanhos realmente enumeradas pelo attachment público. Resolva Article.image → ImageObject por @id; JSON-LD parseável não prova imagem atual. Não adivinhe variantes por normalização de nomes.
- Se twitter:image estiver ausente, registre fallback de OG e não invente uma imagem Twitter explícita antiga; uma única divergência pode afetar ambos os canais sem duplicar o número de artigos distintos.
- Confira separadamente HTML lang, schema inLanguage, OG locale e idioma da data principal. No tema CompanyBRS, a data do artigo está em `.single-post-meta`; `.related-card-date` pertence a outro artigo. Compare dia local visível e instantes ISO/GMT antes de classificar erro factual de data.
- Percorra os índices de sitemap, confira inclusão literal e lastmod contra modified_gmt; registre também filhos listados que retornam erro. Separe alertas de infraestrutura encontrados no índice alternativo dos bloqueios das URLs do lote. Não execute purge/reindex/config como extensão da auditoria.
- Não chame divergência pública de cache comprovado apenas porque REST difere do HTML. Registre causas como não determinadas até haver evidência da camada real.
- Reconte códigos, união de artigos afetados e distribuição por domínio em código; verifique hashes dos bytes e reconcilie alvos com pendências históricas. Novos testes não provam regressões recentes.
- Não declare indexação no Google sem Search Console. HTTP 200, canonical self, robots favorável e presença no sitemap são evidências públicas distintas, não prova de indexação.
