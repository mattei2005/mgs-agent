# DevDay 2026 — continuidade dos pilotos MGS

Origem e autoridade: Rodolfo, mensagem `1555607570746572942`, thread `1555583048899104933`: “Sobre sua ordem recomendada. Continue o que falta.”
Dono: Zeus. Status: piloto Security produziu artefatos finais selados; cobertura parcial declarada de181/1948 arquivos e27 apontamentos estáticos; aplicabilidade em produção ainda não confirmada.

## Escopo autorizado

Continuar os itens restantes da recomendação: piloto Codex Security report-only no repositório MGS; definir um único plugin externo simples; manter Agents API, dots corporativos e plano mais caro em observação. Sem publicar plugin, contratar serviços, abrir PR de remediação, instalar hooks Git ou dar acesso a credenciais/produção. A migração dos modelos principais já foi feita em outro fluxo; a exceção Astra da thread1545426987756298340 permanece.

## Codex Security — execução real em sandbox

- Repositório canônico: `git@github.com:mattei2005/mgs-agent.git`, worktree `/root/mgs-agent`, branch main. Revisão observada no início: `f49a7a15b850d715616cbea208c38df26c44bb93`; worktree contém alterações concorrentes, não editadas por este piloto.
- Security Cloud inacessível no browser corrente: challenge “Just a moment”, DOM sem formulário de login. Isso não comprova indisponibilidade do serviço nem falta de entitlement da conta.
- Failover de preparação: CLI oficial `@openai/codex-security@0.1.31`, plugin bundled0.1.95, Codex0.156.1; Node22.23.3. Executados version, info, help e scan --dry-run.
- Dry-run do repositório inteiro: PASS; modo standard, `--auth chatgpt`, `gpt-6.1-sol`, xhigh; authentication.verified=false. Não analisou código, não chamou modelo, não validou acesso do usuário.
- Na preparação inicial, `login status` era Not logged in. Após nova autenticação confirmada por Rodolfo (`1555625953533894668`), processo `proc_97dba9627f99` terminou exit0 / Successfully logged in e status real retornou Logged in using ChatGPT. Credencial nova mantida no home dedicado, arquivo interno `state/plugins/codex-security/codex-home/auth.json`, modo600; conteúdos nunca lidos/exibidos. Não copiados tokens do Hermes nem usadas API keys. Entitlement do Security/Trusted Access for Cyber ainda não confirmado.
- Histórico do gate: o repositório completo tinha19784 arquivos rastreados e3.41GB, com data≈1.56GB e work≈1.38GB. Rodolfo autorizou explicitamente o recorte source-only na mensagem1555627720799559824. Nenhum arquivo removido do repositório.
- Snapshot aprovado:1948 arquivos,15096979 bytes, revisão MGS `a032a9d4beb5dc88e12657005a8276de779ebca5`, commit da cópia isolada `22f3738`. Manifesto individual de paths/blob/SHA-256 e exclusões em `/root/.hermes/profiles/zeus/codex-pilots/scans/1555627720799559824-v2/source-manifest.json`.
-95 candidatos excluídos por detecção conservadora de material semelhante a credencial (não significa95 vazamentos reais); demais exclusões são não-código/binário/backup/symlink. Nenhum valor detectado registrado ou enviado ao scanner. Detect-secrets1.5.0 usa pipeline contextual; tentativa inicial com scan_line produziu excesso de falso positivo e foi descartada do piloto, sem apagar artefatos.
- Proteções testadas: /source read-only/EROFS; /root e /etc/shadow ausentes; rede direta impossibilitada; proxy TLS CONNECT permite somente chatgpt.com/auth.openai.com/api.openai.com:443 e IP público; exemplo de host externo bloqueado403. Produção, SSH, 1Password e dados operacionais não montados. Estado da autenticação dedicado e resultados são as únicas áreas persistentes graváveis.
- Tentativa real com6.1 pelo CLI: HTTP400, modelo não suportado neste cliente com conta ChatGPT. Failover para o default oficial Security5.6-sol/xhigh, sem mudar modelos dos agentes. Modelo5.6 executou chamadas reais de análise.
- Primeira tentativa5.6 foi interrompida pelo limite420s da ferramenta foreground, antes de selar relatório. Retentativa em background silencioso `proc_70b0458ae737`, modo run-long, máximo45min; nenhum resultado de scan é declarado até ler os artefatos reais. Directories de falhas preservados; cada tentativa usa saída distinta.
- Atualização após autorização: /root/.local/bin/hermes -p zeus usage mostrou weekly98%used/2%remaining,4 resetcredits disponíveis, renovação2026-10-03 12:59EDT. Não há baseline anterior suficiente para atribuir98% ao scanner ou a um único consumidor.
- Scanner interrompido com SIGINT para preservar os agentes; processo `proc_70b0458ae737` saiu e retornou exit130 / Scan canceled by Ctrl-C. Nenhum scanner continua rodando. Proteções reportaram459 conexões OpenAI permitidas e22 recusadas; fonte permaneceu imutável na validação de1948 hashes.
- Último progresso publicado pelo produto:23/1948 arquivos; uso lógico reportado1950164 input uncached,42048128 cache reads,143573 output,44141865 total. Esses números não são dólares/cobrança adicional e não equivalem a cobertura validada. Saída parcial preservada em `.../1555627720799559824-v2/output/scan-run-long`; nenhum report.md/findings.json/coverage.json/scan-manifest.json final foi selado. Não há base para declarar zero vulnerabilidades nem scan completo.
- Gate anterior de franquia explicitamente superado pela autorização de Rodolfo `1555642311784800452` (“Sim pode fazer”), consumida em2026-10-02: consulta atual antes da ação weekly99%used/1%remaining e4 resets; resgate nativo `agent.account_usage.redeem_codex_reset_credit` retornou status=reset/windows_reset=1. Readback `/root/.local/bin/hermes -p zeus usage`: weekly0%used/100%remaining e3 resets, próximo reset2026-10-09 14:08EDT. Consumido exatamente1 crédito bancado; nenhum segundo reset, compra/API ou mudança de plano autorizado.
- Tentativa final Standard `proc_089590a09ecc`, scanId `87b0d2b8-d5f9-482a-99a8-0233e7e57f9e`, output exclusivo `output/scan-run-after-reset-v2`, encerrada com artefatos selados e exit2 por cobertura parcial, não por timeout. Mesmo snapshot/hash/modelo/autenticação/isolamento; nenhum novo reset consumido. Tentativa de retomada nativa `scans resume` retornou exit2 sem rede: “Resume requires a Deep Scan with a saved CLI launch recipe.” Não houve troca para Deep nem redução do escopo. Tentativas incompletas permanecem somente como histórico, não como resultados finais.
- Verificação de imutabilidade durante o scan:1948 hashes confrontados, zero arquivos alterados. O recorte não cobre o estado produtivo, alterações não commitadas nem os candidatos excluídos.
- Home dedicado: `/root/.hermes/profiles/zeus/codex-pilots/security-host`; resultados fora do repo em `.../codex-pilots/security-results`.
- Restrição importante da documentação: scans usam permissões locais, approvalPolicy=never e profile codex_security_scan; --codex não torna o scanner read-only. Não rodar diretamente como root sobre o ambiente produtivo. Antes do scan real: snapshot isolado do código autorizado, sem credenciais/dados operacionais desnecessários, namespace com leitura somente da fonte e escrita somente nos artefatos; rede e exposição de dados limitadas ao necessário. Qualquer redução do conjunto autorizado deve ser alinhada, não promovida silenciosamente como scan integral.
- Pré-teste de isolamento bwrap: PASS; namespace sem /root/mgs-agent ou /root/.hermes. Isso prova apenas a capacidade básica do host, não um sandbox final validado para Security.
- Não usados --mock, --patch, --create-pr ou install-hook. O encerramento real abaixo substitui os gates anteriores de ausência de relatório. Não declarar o repositório seguro por dry-run ou por ausência de achado em arquivos não revisados.

### Encerramento real — cobertura parcial e apontamentos do snapshot

- Scan `87b0d2b8-d5f9-482a-99a8-0233e7e57f9e`, producer codex-security-plugin0.1.95, status nativo completed, sealedAt2026-10-02T19:26:41.184938Z. Artefatos reais: report.md, findings.json, coverage.json, scan-manifest.json e results.sarif, em `.../1555627720799559824-v2/output/scan-run-after-reset-v2/`. Dois hashes referenciados pelo manifest (findings/coverage) confrontados e idênticos aos arquivos reais;27 findingIds distintos.
- CLI exit2 não foi timeout nem ausência de relatório: mensagem exata “Scan coverage is partial; results may be incomplete.” Revisão detalhada declarada pelo produto181/1948 arquivos (9.29%);1767 sem revisão integral. Não há prova independente de leitura linha a linha dos181; o número é a declaração registrada no coverage. Nenhuma redução adicional do snapshot foi feita pelo Zeus.
-27 apontamentos classificados pelo scanner:14 high,10 medium,3 low. Validação majoritariamente estática/condicional; não equivale a27 brechas exploráveis confirmadas em produção. Principais grupos: autorização de disparadores Discord, injeções em helpers/seleção de credenciais, barreiras de publicação/aprovação e concorrência, URLs/arquivos e superfícies públicas/SMS.
- Fixture jq independente e inofensiva confirmou que a interpolação do site_key na linha11 do resolver permite alterar a expressão. Não executado o resolver completo; nenhuma 1Password, credencial real, API ou sistema produtivo consultado. Evidência `independent-jq-fixture-validation.json`; aplicabilidade/explorabilidade produtiva não confirmada.
- Lacunas: restante do source, módulos auth.mjs/finance-ops.mjs ausentes, runtime/allowlists/configurações efetivas fora do snapshot e validações dinâmicas bloqueadas por desenho. Avaliar código/configuração produtivos ou incluir arquivos antes excluídos exige novo alinhamento de escopo; não promover os apontamentos estáticos como estado produtivo.
- Fonte imutável:1948 hashes revalidados, zero diferenças. Processo encerrado; nenhum wrapper scanner ativo. Proxy contabilizou614 conexões OpenAI permitidas e53 recusadas. Sem patch, PR, hooks ou publicação. Não foi consumido segundo reset nem usado API key; consulta final confirmou weekly4%used/96%remaining,3 créditos bancados, renovação2026-10-09 14:08EDT.
- Evidência consolidada: `.../1555627720799559824-v2/security-results-validation.json`. Próxima recomendação, ainda não autorizada: triagem somente leitura da aplicabilidade atual dos itens altos, sem credenciais nem alteração de produção; complementar a cobertura restante sem confundir os dois trabalhos.

### Contexto de ameaça preparado

O repositório implementa orquestração de agentes, scripts operacionais, integrações e automações. Dados de mensagem, DOM de páginas e respostas de APIs são entrada não confiável. Fronteiras prioritárias: Discord→autorização por ID, arquivos/JSON→comandos shell, 1Password→consumidores, processamento de URLs→rede, concorrência→persistência atomicamente consistente, outputs→logs/Discord. Priorizar vazamento de segredo, bypass de autorização, command/path injection e escrita concorrente. Não conectar dashboards de produção, enviar tokens, executar WordPress/Meta/DTR ou testar alvos externos. Achado deve incluir arquivo/linhas, fluxo, pré-condições, evidência de reprodução isolada e status validated/unvalidated; zero correção automática. Coverage complete/partial/unknown deve constar no resultado.

## Plugin externo definido — MGS Custo Claro

Hipótese de produto, não nova decisão comercial: comparação educativa do desembolso nominal entre2–5 propostas de crédito de parcelas fixas, fornecidas pelo próprio usuário, mesma moeda e mesmo valor recebido. Sem recomendar banco/produto, alegar elegibilidade ou estimar APR/CET com dados insuficientes.

- Implementado protótipo skills-only0.1.0 e marketplace local. Não é plugin do Hermes e não altera Zeus/Atena/Ares.
- Sem servidor público, MCP, credenciais, formulário de leads, redirecionamentos comerciais, rastreamento ou dependência de sistemas MGS.
- Cálculo determinístico via Decimal; tarifas explícitas; recusa dados faltantes/valores não finitos/extra fields. Não exportar CPF/SSN ou identifiers; labels neutros A/B.
- Pacote instalado em home Codex isolado: `/root/.hermes/profiles/zeus/codex-pilots/plugin-host`, pluginId `mgs-custo-claro@mgs-devday-pilot`; plugin list confirmou installed=true/enabled=true.
- TDD: RED por implementação ainda ausente → GREEN18 testes. Três testes CLI sobre cópia efetivamente instalada PASS. SHA-256 do script instalado e fonte idênticos: `893443959435093fdc4c6875f133f95022cab2e7ac9d26063e1b74738c515244`.
- Exemplo sintético: receberBRL1000; A12×100 sem tarifa →1200; B10×115+30 →1180. Apenas resultado matemático, não oferta bancária real.
- Documentados5 casos positivos e3 negativos para ativação do modelo. Essa avaliação de conversa/UX no ChatGPT/Codex AINDA NÃO foi executada.
- Não submetido/publicado no diretório e não instalado na conta ChatGPT do Rodolfo.
- Gate comercial: diretrizes exigem utilidade diferenciada de funções nativas; uma calculadora simples pode ser insuficiente. Este pacote valida empacotamento/isolamento, não demanda, distribuição nem aprovação. Antes de submissão, validar diferenciação, utilidade, UX, políticas, identidade verificada, suporte, privacidade e termos. Não inserir links afiliados/upsells/subscrição digital neste piloto.

Artefatos e evidências: `work/devday-2026-followup-1555607570746572942/` (plugin, testes, manifesto/marketplace, security-dry-run.txt e plugin-installed-smoke.json).

## Em observação

Agents API, dots corporativos e upgrade de plano continuam sem adoção, compra, credenciais ou cron novo. Reavaliar apenas com necessidade concreta de produto externo/escala, acesso corporativo confirmado ou medição de saturação do plano atual. Não há monitor automático criado por este piloto.

## Triagem autorizada dos itens altos — 1555683107045249128

Após autorização explícita de Rodolfo nesta thread, foi concluída a revisão de aplicabilidade dos **14/14 IDs high** do relatório selado por leitura de código, configuração não secreta, referências de callers e metadados de cron/serviços. Os 19 arquivos citados pelo scanner continuam idênticos ao snapshot. Não foram executados resolver de credenciais, helpers WordPress, campanhas, SSH, geração xAI, novo scanner ou novo reset. Nenhuma remediação produtiva foi aplicada.

A matriz privada distingue 9 lacunas em rotas atuais/suportadas, 3 mecanismos condicionais a entrada/chamada direta e 2 itens cuja exposição pela rota ativa não foi comprovada. Os guards dos callers, flock por rota, transporte MCP de dados e permissões locais foram preservados como contraevidência. A classificação não representa teste de exploração nem incidente confirmado. A cobertura original continua parcial (181/1.948), e 10 medium/3 low não foram triados nesta etapa.

Evidência privada: `/root/.hermes/profiles/zeus/codex-pilots/scans/1555627720799559824-v2/current-applicability-1555683107045249128/applicability-review.json`, respectivo Markdown e `validation-receipt.json`; IDs únicos/set contra o artefato selado e hashes da matriz validados. ACL efetiva de postagem Discord e entradas adversariais não demonstradas permanecem lacunas. Próximo gate: autorização separada para correções/testes em cópia isolada; credenciais/permissões/budget/restart e cutover produtivo mantêm suas confirmações próprias. A regra editorial atual de ofertas/redirects aprovados deve ser preservada; não adotar allowlist arbitrária de emissor.

## Fontes oficiais consultadas

- https://learn.chatgpt.com/docs/security/setup
- https://learn.chatgpt.com/docs/security/faq
- https://learn.chatgpt.com/docs/security/cli
- https://learn.chatgpt.com/docs/security/cli/reference
- https://developers.openai.com/plugins/build/plugins.md
- https://developers.openai.com/plugins/build/skills.md
- https://developers.openai.com/plugins/deploy/connect-chatgpt.md
- https://developers.openai.com/plugins/deploy/submission.md
- https://developers.openai.com/plugins/app-guidelines.md

## Preparação isolada autorizada — 1555702812946604143

- Autorização: Rodolfo, mensagem `1555702812946604143`, thread `1555583048899104933`. Somente preparar/testar candidatos; implantação, credenciais reais, permissões, budget, restart, novo scan e reset permanecem fora do escopo.
- Artefato privado: `/root/.hermes/profiles/zeus/codex-pilots/remediation-1555702812946604143/candidate.patch`; matriz finding→patch→teste e recibos em `evidence/`.
- 14/14 IDs reconciliados; 20 arquivos candidatos, sintaxe validada e `git apply --check` PASS. SHA-256 do patch: `d25bfc3e96aa9acd4dca78321f6d039d4b71f5cd09b89276c7430cc83cb95e19`.
- RED: 51 checks, 48 falhas esperadas, 0 erros de harness. GREEN: 51/51, sem skips — 42 casos de comportamento/fixtures e 9 contratos estáticos, não 51 testes de integração produtiva.
- 19 hashes das fontes anteriores permanecem iguais. Namespace sem egress direto, sem homes/credenciais produtivas e sem `/etc/shadow`.
- Smokes de importação: 7/9. Grok requer bootstrap do checkout Hermes real, ausente do recorte; o materializador Eggbev requer `ares_campaign_v3.eggbev_create`, ausente do snapshot. Não substituídos por validação fictícia.
- Candidatos fail-closed têm gates de compatibilidade: trust SSH real; fontes/webhooks exatos e dispatcher de reparos aprovado; raízes de mídia/ofertas afiliadas; aprovador assinado separado dos agentes; limpeza com post vinculado; revisão segura de posts publicados; canário/rollback de publicação e Windows MCP.
- Sem proteção produtiva declarada, sem exploração demonstrada. Resultado do Security continua parcial: 181/1.948 arquivos; 10 medium e 3 low permanecem fora desta etapa.
- Estado: preparação dos candidatos/fixtures disponível; integração completa e promoção **não aprovadas nem concluídas**.


## Complemento isolado autorizado — 1555741879214022747

- Escopo: fechar os dois gaps de código/bootstrap, sem credenciais reais, produção, novos scans Codex Security ou resets. Raiz privada: `/root/.hermes/profiles/zeus/codex-pilots/integration-1555741879214022747/`.
- Antes: 7/9 imports, reproduzidos com os dois erros originais. Depois: **9/9 imports nativos**, **11/11 verificações offline** (bootstrap real mínimo, contexto de perfil, CLI help, gates e isolamento) e **51/51 regressões** (42 casos de comportamento/fixtures + 9 contratos estáticos). Zero skips, falhas ou erros.
- Replay independente: baseline limpo + patch original intacto + complemento filtrado; todos os hashes candidatos conferidos; novamente **9/9 imports, 11/11 checks offline e 51/51 regressões**.
- Fontes adicionais: 3 arquivos de código filtrados (Eggbev, launcher Hermes e constantes nativas). Um hash público de integridade semântica foi classificado por AST/uso como falso positivo de entropia, com exceção estreita e auditada; nenhum segredo foi incorporado.
- Imutabilidade: patch original, 20 arquivos candidatos originais e 19 fontes produtivas preservados por hash. Nenhum patch implantado, PR, restart, chamada de geração/campanha, alteração de budget/policy/credencial ou novo reset.
- Supersessão: a limitação histórica de imports 7/9 descrita acima fica superada **somente no ambiente offline**; recibos anteriores permanecem como histórico. O bootstrap é mínimo para resolução/importação dos wrappers, não um Hermes CLI completo/autenticado.
- Evidência: `evidence/integration-closure-receipt.json`, `integration-artifacts.json`, `complement-manifest.json` e `patch-replay-verification.json`; procedimento salvo com readback na skill Zeus `openai-product-pilots`.
- Gates produtivos continuam separados: política de fontes/webhooks e compatibilidade dos reparos automáticos; emissão/ciclo de aprovações assinadas; confiança SSH, raízes de mídia e origens de oferta; identidade/revisão/limpeza de posts; canário e rollback sob nova autorização. Os 10 medium/3 low e a cobertura parcial original 181/1.948 não foram ampliados.
