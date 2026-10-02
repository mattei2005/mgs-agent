# DevDay 2026 — continuidade dos pilotos MGS

Origem e autoridade: Rodolfo, mensagem `1555607570746572942`, thread `1555583048899104933`: “Sobre sua ordem recomendada. Continue o que falta.”
Dono: Zeus. Status: recorte source-only autorizado; scan real em execução no sandbox; resultados ainda não disponíveis.

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
- Verificação de imutabilidade durante o scan:1948 hashes confrontados, zero arquivos alterados. O recorte não cobre o estado produtivo, alterações não commitadas nem os candidatos excluídos.
- Home dedicado: `/root/.hermes/profiles/zeus/codex-pilots/security-host`; resultados fora do repo em `.../codex-pilots/security-results`.
- Restrição importante da documentação: scans usam permissões locais, approvalPolicy=never e profile codex_security_scan; --codex não torna o scanner read-only. Não rodar diretamente como root sobre o ambiente produtivo. Antes do scan real: snapshot isolado do código autorizado, sem credenciais/dados operacionais desnecessários, namespace com leitura somente da fonte e escrita somente nos artefatos; rede e exposição de dados limitadas ao necessário. Qualquer redução do conjunto autorizado deve ser alinhada, não promovida silenciosamente como scan integral.
- Pré-teste de isolamento bwrap: PASS; namespace sem /root/mgs-agent ou /root/.hermes. Isso prova apenas a capacidade básica do host, não um sandbox final validado para Security.
- Não usados --mock, --patch, --create-pr ou install-hook. Não existe findings.json/report.md de scan real. Não declarar repositório seguro por dry-run.

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
