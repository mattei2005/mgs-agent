# Auditoria de segurança RunCloud — 22/09/2026

## Autorização e entrega

- Solicitante: Rodolfo Mattei, mensagem `1551798675179708496`, thread `1551768281688580096`.
- Escopo: auditoria somente leitura de todos os domínios/apps acessíveis na RunCloud; consolidação na Sheet indicada. Não autoriza remediação do portfólio.
- Planilha: https://docs.google.com/spreadsheets/d/1_8vUodLSgxfIj0vW0DlDpvljHFgygfI8A5Txc_Mc858/edit?gid=0#gid=0
- Entrega: 10 abas, 32 pontos de revisão, 24.695 células conferidas integralmente pela Service Account canônica, inclusive após a formatação. O arquivo não estava compartilhado por link público na verificação; suas permissões não foram alteradas.
- Abas: Resumo, Prioridades, Domínios, Endereços, Conteúdo, Arquivos, Plugins, Amostras, Servidores, Método e limites.

## Cobertura reconciliada

- 120 aplicações, 238 hostnames e 4 servidores visíveis na API. A contagem anterior de três servidores descrevia somente os hosts com SSH, não o inventário completo.
- Auditoria interna de 119 apps nos três MatteiInc: 111 WordPress/bancos e oito outras aplicações.
- SpazioVPS / spaziokitchensandbaths.com: API e HTTP/origem examinados; ausência de SSH disponível limita a auditoria interna. Não foi criado acesso alternativo.
- 120/120 sondagens de origem, 238/238 sondagens públicas e 111/111 varreduras estruturadas de conteúdo WordPress persistidas.
- 282.247 registros de posts/revisões examinados; 1.143 registros analisados pelo detector DOM dirigido; 1.095.943 arquivos de código/texto lidos; 738.175 coincidências com checksums oficiais.
- Não houve crawl exaustivo dos 140.068 registros publicados do portfólio: frontend foi examinado por homes, endpoints e candidatos dirigidos. A terceira rechecagem do Carcreditad cobriu suas 95 URLs publicadas.

## Achados prioritários

1. **F001 — Folhadaterra:** 11 arquivos/cópias com funções de acesso paralelo, login administrativo por chave, shell, loaders, gerenciador de arquivos/banco e cloaking. Funções confirmadas por leitura estática, sem executar ou autenticar os artefatos. Logs consultados incluem GET/200 em rotas relacionadas; isso não prova autenticação nem exploração atual. Autoria e data real de implantação não foram comprovadas. Os mesmos hashes não foram encontrados em outros apps coletados.
2. **F002–F008 — spam oculto:** 36 publicações em sete domínios possuem nós ocultos de apostas no banco; 32 tiveram indicadores confirmados no HTML público. Domínios: apexwallet.de, autolendpro.com, mobileapp.com.br, portalbrasilnews.com, seniormenu.com, tapsaga.com e zionnmedia.com.
3. **Isolamento:** contas SQL com privilégios globais e usuários Unix compartilhados ampliam o risco lateral. MariaDB local-only não neutraliza esse risco.
4. **Manutenção:** 99 aplicações configuradas em PHP 8.0/8.1, fora de suporte upstream; 691 instalações ativas de plugins abaixo da versão pública. Seis sites possuem Ad Inserter gratuito ativo dentro da faixa dos avisos selecionados. Atualização disponível, vulnerabilidade e vetor histórico são conclusões diferentes.
5. **Acessos:** 479 de 574 contas administrativas por instalação não tinham cadastro TOTP identificado. Isso não prova ausência de outro MFA nem autoriza bloquear contas de serviço. XML-RPC respondeu à introspecção pública em 83 apps; uma cópia alternativa foi confirmada em wrnoticia.com.
6. **Endpoints:** 194 respostas finais 200, seis 403, 23 falhas de conexão e 15 TLS. Rechecagem dirigida confirmou ausência de resolução DNS nos 23 casos de conexão e distinguiu certificado inválido de falha de handshake nos demais. Um 403 ao auditor não prova falha para visitantes humanos.
7. **Carcreditad:** 95/95 URLs novamente verificadas sem os indicadores conhecidos avaliados; sem reinjeção identificada nos campos atuais examinados. O HTTP 500 espanhol já conhecido não foi corrigido. Home/tema foram preservados conforme orientação de Rodolfo. A rotação da chave WP 2FA exposta em coleta interna anterior permanece pendente de confirmação crítica e plano de preservação/recadastro; a pendência foi carregada para F032, sem publicar o valor.

## Limites e controles contra falso positivo

- Conteúdo de revisões históricas e índices derivados não equivale a reinjeção publicada. Candidatos editoriais por palavra-chave, especialmente Allincraft e Portal Brasil News, estão separados dos nós ocultos confirmados.
- Corpo vazio, redirect ou falha de transporte na origem não comprova ausência do conteúdo que foi observado no banco/público.
- Checksums corretos não excluem arquivos extras. Plugins Pro/custom sem distribuição licenciada de referência não receberam certificação integral; `eval` isolado não foi tratado como prova de malware.
- Placeholders traduzidos em wp-config-sample.php não correspondiam às credenciais ativas. Normalização de literais não foi usada como prova de equivalência funcional.
- Um HTML transitório de cache de jobscana, inicialmente maior que o limite de coleta, já não existia na leitura complementar; seu conteúdo histórico não foi certificado e não foi removido pelo auditor.
- Não houve exploração, tentativa de senha, envio real de formulários, comprovação de entrega de anúncios nem correlação histórica integral dos logs de todos os hosts.
- Sem atribuição encontrada nas fontes pesquisadas para os artefatos Folhadaterra: audit log, inventário, 300 REPORT-INFRA recentes, Git e histórico consultado. Ausência de registro não comprova autoria externa.

## Execução e recuperação

- API paginada, retomada por objetos persistidos, pacing e respeito ao rate limit; coleta interna estática/SELECT em transação read-only.
- Timeout de lote, separador Unicode do transporte e volume de cache foram diagnosticados; retomada concluiu 119/119 apps acessíveis por SSH, sem erros finais de coleta. Dois workers órfãos próprios foram encerrados; não foi reiniciado serviço.
- Uma leitura complementar encontrou cache já ausente, registrada como limitação. Um comando auxiliar de fechamento usou nome incorreto de arquivo de métricas; corrigido para `audit-summary.json`, sem afetar dados nem entrega.
- Não foram alterados sites, conteúdos, versões, permissões, credenciais, DNS ou firewall nesta auditoria ampliada. Escritas limitadas à Sheet solicitada, evidências locais, documentação/skill, inventário e checkpoints. GETs podem produzir logs/cache normais.
- Recomendação: iniciar a revisão por F001, definindo backup forense e contenção reversível com alvos exatos. Remoção, credenciais e controles críticos dependem da confirmação adicional aplicável.

## Evidências e aprendizado

- Workspace restrito: `/root/.hermes/profiles/zeus/workspace/runcloud-security-20260922/`.
- Resumo calculado: `audit-summary.json`; conjunto publicado: `sheet-bundle.json`; readback: `sheet-publication-verified.json` e `sheet-readback.json`.
- Rechecagem Carcreditad: `/root/.hermes/profiles/zeus/workspace/carcreditad-third-audit/crawl.jsonl`.
- Checkpoints: `runcloud-portfolio-security-20260922` e `carcreditad-third-audit-20260922`.
- Procedimento persistido na skill Zeus `wp-plugin-mass-operation`, referência `wordpress-irrelevant-posts-incident-audit.md`: cobertura por app/hostname, retomada, SQL read-only, arquivos extras, classificação sem falso positivo, limites de origem e readback integral de planilha.
