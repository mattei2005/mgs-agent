# Carcreditad — segunda auditoria de segurança e resíduos

> **Atualização posterior autorizada:** os resíduos de cache/metadados e as 93 referências de Yoast dos achados 1 e 2 foram removidos e validados em `reports/carcreditad-residual-cleanup-20260922.md`, com autoridade `1551795786193575979`. Rodolfo excluiu configurar/corrigir a home desta etapa; a recomendação de patch de tema abaixo permanece apenas histórica, não é tarefa autorizada. Os demais riscos de segurança não foram alterados.

## Autoridade e escopo

- Rodolfo: mensagem `1551783357552001087`, thread `1551768281688580096`.
- Segunda auditoria read-only, após a limpeza autorizada por `1551777897759375400`.
- Alvo: MatteiInc02, `/home/runcloud2/webapps/carcreditad`, banco `carcreditad_1770831260`.
- Métodos: leitura estática/SELECT, análise de permissões, inventário e comparação de hashes, pacotes oficiais de temas inativos, HTTP GET público sem autenticação, metadados HTML e logs. Sem gravação administrativa no site, exploração de escrita, atualização de plugin/tema, remoção de arquivos ou mudança de acesso.
- GETs normais podem gerar logs, caches, transients e métricas da aplicação; isso não constitui alteração administrativa de produção.

## Conclusão e retificação

Foram encontrados resíduos adicionais e riscos não detalhados na primeira auditoria. A limpeza anterior removeu corretamente os 80 blocos e 97 links dos seis conteúdos; os seis hashes limpos continuam iguais. **A validação anterior foi insuficiente quanto aos metadados derivados no cache.** Persistem descrições sociais de apostas em dois HTMLs de cache, embora o banco e a renderização sem cache estejam limpos desses trechos.

Esta conclusão qualifica/supersede a declaração ampla de limpeza concluída de `reports/carcreditad-content-cleanup-20260922.md`; não invalida os readbacks específicos de conteúdo, links, backups e preservação legítima daquele relatório. Nenhum dos novos itens foi corrigido nesta auditoria.

## Achados novos

### 1. Resíduo confirmado — descrições sociais em dois caches

- `/contact-us/` (ID 13) e `/home-english/` (ID 61590) respondem HTTP 200 e ainda incluem `og:description` com expressões de cassino/apostas.
- As mesmas URLs com parâmetro de bypass retornam HTTP 200 sem essas descrições. Cloudflare informa DYNAMIC; as descrições também estão nos objetos HTML locais já inventariados.
- Os hashes dos seis post_content são os mesmos da limpeza e não contêm os links removidos. Portanto, a evidência aponta para resíduo da renderização antiga, não reinjeção nova no banco.
- Causa da lacuna anterior: foram saneados os nós ocultos nos caches, mantendo o restante byte a byte. Isso preservou descrições automáticas derivadas do texto injetado. A verificação anterior buscou domínios maliciosos e não detectou texto de apostas sem esses domínios em meta tags.
- Impacto: prévias sociais/robôs podem continuar recebendo descrições de apostas dessas URLs.
- Recomendação: regenerar de forma dirigida esses caches e conferir todas as meta tags/JSON-LD nas respostas públicas e sem cache; aprovação separada da auditoria.

### 2. Resíduo interno — índice de links do Yoast

- Confirmados 93 registros em `wp_yoast_seo_links` referenciando os domínios maliciosos já removidos dos conteúdos.
- Distribuição por página: ID 3=16; ID 13=14; ID 61581=14; ID 61590=21; ID 61652=15; ID 61653=13.
- Esses 93 registros não equivalem aos 97 links HTML: o índice tem sua própria representação/deduplicação.
- Não encontrei esses domínios no HTML de nenhuma das 95 URLs publicadas verificadas. São resíduos de índice interno, não 93 novas injeções públicas.
- As 80 revisões contaminadas históricas também continuam preservadas intencionalmente; não restaurá-las automaticamente. Consulta anônima das revisões testadas retornou 401.
- Recomendação: reconstrução dirigida dos índices das seis páginas com backup e readback, sem apagar histórico forense por padrão.

### 3. Alto — alcance lateral por permissões globais de banco

- O usuário SQL do próprio Carcreditad está restrito ao escopo do banco e tem USAGE global; não é o problema identificado.
- Porém, existem **11 outras contas não-sistêmicas** com privilégios globais no mesmo MariaDB, incluindo SELECT, UPDATE, SUPER e FILE. Essas permissões abrangem também o banco Carcreditad.
- Fechar a porta externa/escutar em localhost não isola o banco de aplicações locais cujas contas tenham esses privilégios.
- Isso é risco de arquitetura/permissões, não prova de que essas contas foram usadas na invasão nem classificação de concessão não autorizada. Não foi feita tentativa de escrita ou acesso cruzado a dados de outros sites.
- Evidência: `information_schema.USER_PRIVILEGES` e `SCHEMA_PRIVILEGES`. Lista restrita em `privileges-and-yoast.json`/`deep-scan.json`.
- Recomendação: mapear os consumidores dessas contas e reduzir privilégios com canário e rollback. Exige confirmação crítica; revogação cega pode interromper aplicações e automações.

### 4. Defeito funcional do tema — página espanhola HTTP 500

- `https://carcreditad.com/es/home-espanol/` (ID 61595) responde 500, inclusive repetição sem cache.
- O log atual registra `Cannot redeclare companybrs_lang_query_args()`.
- A função existe em `functions.php:409` e é redeclarada em `page-home.php:24` (o fatal aponta o fim da declaração em linha 39).
- O mesmo erro já aparece em logs de agosto; os arquivos do tema não foram alterados pela limpeza anterior. Isso é defeito do template, não evidência de código injetado.
- Recomendação: eliminar a dupla declaração preservando comportamento e validar a página espanhola, homepage e demais templates; patch não autorizado por um pedido apenas de auditoria.

## Risco conhecido verificado com mais precisão

Ad Inserter 2.8.15 aceita diagnóstico de código sem autenticação: o teste GET com parâmetro de debug retorna painéis de header/footer. Porém, o conteúdo não vazio observado (334 caracteres após normalizar escapes de transporte) é HTML/JavaScript **já presente na resposta pública normal**. O teste não demonstrou exposição de senha, PHP original ou dado privado. Mantém-se a recomendação de atualização baseada nos avisos anteriores, sem inflar o impacto desta reprodução nem atribuí-la como causa da invasão.

A opção Ad Inserter usa formato `:AI:` + base64 de PHP serialization. Foi decodificada estaticamente com classes proibidas, sem carregar/executar WordPress ou snippets. Não foram encontrados os indicadores de spam/backdoor consultados no código configurado; valores do código não foram publicados.

## Cobertura e resultados negativos

- 25 tabelas: 14.166 linhas inventariadas, inspeção dos campos textuais aplicáveis. Valores de autenticação nunca exportados; resultados contêm apenas referências/indicadores.
- 13.311 arquivos inventariados no webroot, inclusive uploads e caches. Um JS oficial acima de 10 MB recebeu hash suplementar, igual ao baseline; não foi tratado como arquivo alterado por estar ausente da coleta limitada.
- Todo o conjunto de 95 posts/páginas publicados foi consultado e contado por IDs: 94 respostas 200 e uma 500; zero ocorrências dos domínios maliciosos conhecidos no HTML. As únicas descrições sociais com apostas detectadas foram as duas citadas.
- Seis hashes de conteúdo limpo continuam iguais; não encontrei nova reinjeção nesses conteúdos.
- Não encontrei novo PHP/backdoor evidente no escopo revisado nem mudanças de hashes dos arquivos de código abrangidos pelo baseline anterior.
- 768 PNGs deram 1.404 coincidências binárias curtas `<?=`, todas dentro de chunks IDAT. CRCs válidos, sem trailer após IEND; não foram classificados como malware. Outros quatro hits vieram de documentação/código oficial de tema.
- GeneratePress 3.6.1 inativo: 144 arquivos iguais ao pacote oficial.
- Twenty Twenty-Five 1.4 inativo: oito nomes truncados correspondem a bytes idênticos aos arquivos oficiais (incluindo template sem extensão), e style.min.css diverge. O CSS inspecionado contém regras de estilo, sem evidência de payload no trecho analisado. Não foi classificado como vetor nem corrigido nesta auditoria; integridade desse tema não recebeu PASS total.
- Não há `.user.ini` nos três diretórios ancestrais consultados. Nenhum auto_prepend identificado nas configurações locais selecionadas.
- Probes `.env`, `.git/HEAD`, `.user.ini` e backups wp-config testados responderam 403; debug.log respondeu 404. Nenhum segredo dessas rotas foi registrado.
- XML-RPC permanece 403. A rota debug-lang do tema retorna corpo vazio sem bootstrap e possui guarda manage_options quando usada como template.
- REST público lista três autores, comportamento de divulgação de perfil público, não prova de bypass de autenticação.
- Logs recentes contêm POST `/wp-json/batch/v1` com 207; sem corpo/autoria não é possível atribuir conteúdo à chamada. Não foi classificado como ataque. Os hashes editoriais consultados não demonstram reinjeção.

## Limitações e próximos passos

A segunda passada não prova ausência absoluta de vulnerabilidade nem resolve a origem de obtenção da credencial. Continuam pendentes os riscos já registrados: rodmaster/acessos, plugins com correções, PHP 8.1, borda/origem, 2FA e avaliação das chaves mencionadas no incidente de coleta anterior. Não houve pentest de escrita, credencial, restauração isolada, auditoria integral de todos os outros sites ou execução completa de todas as cadeias de scripts externos/GTM.

Prioridade recomendada: (1) finalizar resíduos cache/Yoast e corrigir o template espanhol com escopo pequeno e backup; (2) tratar acessos/atualizações; (3) plano específico de privilégio SQL e isolamento, sem revogação automática.

## Evidência privada e aprendizado

Workspace: `/root/.hermes/profiles/zeus/workspace/carcreditad-second-audit/`.

Artefatos principais: `summary.json`, `deep-scan.json`, `public-probes.json`, `crawl.jsonl`, `privileges-and-yoast.json`, `binary-triage.json`, `inactive-theme-integrity.json`, `focused-source.json`, `ad-inserter-validation.json`, `decoded-ad-options.json`, `debug-code-impact.json`.

Skill `wp-plugin-mass-operation/references/wordpress-irrelevant-posts-incident-audit.md` corrigida: validar metadados sociais/JSON-LD/Yoast, separar cache versus runtime, decodificar formatos nativos, tratar falsos positivos de binários, comprovar impacto de debug público e auditar privilégios SQL globais. Checkpoint e inventário registram a auditoria; mudanças de produção permanecem dependentes de autorização.
