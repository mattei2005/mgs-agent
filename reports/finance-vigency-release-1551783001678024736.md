# Vigência documental e prévia mensal — publicado e validado

## Autoridade e limite

Rodolfo `1551783001678024736`, thread `1545426987756298340`, aprovou a proposta após confirmar que setembro e competências posteriores não teriam valores ou regras aprovadas alterados. Esta entrega acrescenta consulta, não um executor de novas regras. Supersede o estado “próximo pacote não executado” do relatório `finance-prevention-release-1551755722700624003.md` somente quanto à prévia documental aqui descrita. Fechamento/aprovação versionada, abertura nativa, migração integral das regras implícitas e retirada do grafo legado continuam fora desta entrega.

## Resultado publicado

- Painel **Vigência e prévia do próximo mês**, no menu owner-only Conferência mensal.
- Endpoint autenticado GET `/api/period-preview?period=YYYY-MM`, com revisão opcional obrigatoriamente conferida quando enviada pela interface.
- Catálogo documental de nove decisões: SMS de agosto, Yolokfx agosto MGS, quatro origens Openzed agosto, ponte CPV16 agosto, WavesBee CAD agosto/setembro, remuneração mensal desde agosto, SB Tech CAD desde julho, originais CAD/USD independentes e Boostingecon fora do rateio desde setembro. Cada item possui fonte, autoridade, categoria e vigência.
- Compara os sites, configurações originais de despesas e vínculos de contas efetivamente existentes nos dois meses. Reutiliza a resolução atual de contas, distinguindo cadastro mensal explícito de fallback. Não presume recorrência ou autorização na ausência de registro.
- Campos convertidos/calculados, marcações de conferência e comprovantes não são promovidos a cadastros permanentes. Pagamentos/créditos não são repetidos; o saldo anterior continua sendo responsabilidade do ledger original.
- Fonte, destino e cadastro de contas são lidos numa transação REPEATABLE READ READ ONLY. A interface mostra as revisões; snapshot de origem obsoleto retorna 409. Competência inválida retorna 400. Final do horizonte em dezembro/2027 não cria outro mês.
- Nenhum botão ou endpoint de aplicar, copiar, recalcular, fechar ou modificar foi adicionado. Nenhum cálculo, importador, agendamento, taxa, sessão, permissão ou credencial foi alterado.

## Preservação e cobertura

Os fingerprints imediatamente anteriores à publicação, posteriores ao restart e finais após toda a aceitação são iguais: **170 cenários**, revisões, resultados, overrides, additions, ledger e contagem da auditoria financeira preservados. Sessões de teste/autenticação seguem sua auditoria normal e foram encerradas. Zero escrita financeira ou em planilhas.

A cobertura do catálogo é explicitamente não exaustiva: nove decisões documentadas, não todos os caminhos históricos do motor. Cadastros comparados são estados já existentes, não propostas autorizadas de substituição.

Setembro→outubro apresentou **190 cadastros**, 177 iguais e 13 diferenças já existentes. São vínculos/origem de vínculo das contas, configuração de Vizioid, WavesBee e Yolokfx. Nenhuma diferença foi corrigida, normalizada ou classificada como anomalia. Uma pendência documental explícita: WavesBee tem autorização CAD limitada a agosto/setembro; continuidade posterior requer confirmação, sem mudar o cadastro futuro. Outubro→novembro apresenta uma diferença de rótulo da despesa `company|142`. Não converter isso em autorização de reescrita financeira.

## Validação executada

- TDD RED confirmado antes do módulo existir; os dez testes novos passaram posteriormente.
- Gate completo: **184 testes Node + 121 Python = 305**, zero falhas/skips/TODO/cancelamentos. Fixture real protegido de agosto e manifesto de código obrigatórios.
- Dependências: npm audit retornou zero vulnerabilidades conhecidas.
- Backup exato dos arquivos anteriores e dump PostgreSQL com hash transferido, catálogo pg_restore e restauração materializada no banco isolado `mgs_finance_prevention_1551783001678024736`.
- API PostgreSQL stage: 17 competências, bloqueio de revisão obsoleta/competência inválida, autorização owner, negação 403 a partner/manager, leitura dos cinco gestores, zero instruções SQL mutáveis durante a aceitação e fingerprints idênticos.
- UI candidata e UI publicada: cada uma passou em 17 competências × 1440/390 px (34 combinações), sem overflow horizontal, erros JavaScript ou POST financeiro; seleção de período, fim do horizonte e comparação expandida exercitados.
- Regressão da conferência anterior em produção: 17 competências, pesquisa das oito projeções bidirecionais das quatro origens Openzed, navegação e cinco leituras de gestor preservadas.
- Partner e cinco gestores: 12 verificações de browser com projeção isolada de auth/me, menu protegido ausente e redirecionamento antes da consulta protegida. Isto testa a UI por papel, não é alegação de login/MFA real de todos os usuários. Negação do backend foi testada separadamente no stage.
- HTTPS: login público 200; nova API, health e fonte privada não autenticadas 401. CSP, HSTS e no-store preservados. Serviços remotos PostgreSQL, dashboard e socket ativos.
- Performance autenticada: workspace com cinco leituras sequenciais e vinte concorrentes, 25 cache hits e payload idêntico; cinco consultas concorrentes da nova prévia sem falha. Números medidos em `public-performance.json`; nenhuma alteração de cache/headers foi feita.
- Os cinco hashes publicados e os manifestos dos dois gates foram reconferidos no encerramento.

## Falhas de ensaio recuperadas

- Descoberta de schema usou `kind` obrigatório e encontrou entradas nativas legadas sem esse campo. A inspeção foi corrigida para leitura opcional, sem alteração de dados.
- Smoke de papel mobile aguardava menu visível, mas a navegação mobile fechada é intencionalmente hidden/inert. Corrigido para aguardar attachment; as doze combinações passaram. Nenhuma correção de runtime foi necessária.
- Não houve incidente de indisponibilidade identificado nesta entrega; o restart limitado da aplicação integra a publicação autorizada.

## Arquivos e recuperação

Arquivos publicados: `period-preview.mjs`, `monthly-review-routes.mjs`, `public/period-preview.js`, `public/review.js`, `public/review.html`.

Workspace/evidência protegida: `/root/mgs-agent/apps/finance-system/private/vigency-release-1551783001678024736/`.

Backup remoto: `/home/zeus/mgs-finance-backups/gam-email/2026-09-21-36d306e33e0b-complete-df4f40f6bbf4/` (dump e `vigency-code-before.tar.gz`). Cópias locais protegidas e hashes registrados em `backup.json`. Stage: `/var/tmp/mgs-finance-prevention-1551783001678024736`. Preservados sem limpeza destrutiva.

Rollback delimitado: restaurar os três entrypoints/arquivos preexistentes do tar, validar seus hashes e reiniciar somente a aplicação/socket. Não restaurar o banco ativo nem apagar os dois novos arquivos por inferência; após restaurar os entrypoints ficam sem rota/uso. MFA, firewall, unidades systemd e credenciais não fazem parte da alteração.

## Continuidade

Skill dona: `mgs-finance-dashboard/references/preventive-release-gate-and-review.md`, seção Published documentary vigency / next-period preview. Checkpoint: `ZEUS-FINANCE-VIGENCY-1551783001678024736`. Inventário: `finance-vigency-release-1551783001678024736`.

Próximo passo recomendado: analisar as diferenças cadastrais já existentes para outubro e confirmar apenas as decisões que realmente mudariam sua configuração, começando pela vigência de WavesBee. Esta entrega não autoriza nem aplica nenhuma dessas mudanças. Fechamento definitivo com comprovantes e confirmação cambial permanece etapa separada.
