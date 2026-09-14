# Remediação da auditoria integral financeira — 1548835136693600328

## Estado executivo

A autorização ampla de Rodolfo foi executada até o limite não crítico. Na confirmação crítica `1548867037416259627`, Rodolfo adiou MFA e autorizou origin mTLS, hardening do unit e restore+DROP isolado. O hardening e o restore foram concluídos. O mTLS foi tentado em canário opcional, provou-se incompatível com a terminação TLS transparente do BitNinja e foi revertido antes de qualquer modo estrito. O núcleo financeiro permanece íntegro.

### Atualização crítica — 1548867037416259627

- **Systemd concluído:** unit atual substituído pelo candidato SHA-256 `18b9a69351f7868a07e396630ce94148e4f0acc312734b1b1c1ee23e5634d8eb`; exposição caiu de 7.2 MEDIUM para 2.2 OK. Serviço, socket e browser integral passaram depois do restart.
- **Restore PostgreSQL concluído:** o componente do backup off-site `1RLKDwgyafYUM77-H039OhkFAmHh0LQr7` foi restaurado em `mgs_finance_dr_1548835136693600328`; readback: 121 cenários, 85.868 source cells, 799 audit events e ledger legitimamente vazio. O banco isolado foi descartado e `mgs_finance` permaneceu intacto.
- **AOP bloqueado e revertido:** certificado per-hostname foi criado e associado com status Cloudflare `active`, mantendo AOP global `off`. Nginx em modo `optional` recebeu `$ssl_client_verify=NONE` tanto pela Cloudflare quanto quando o próprio certificado foi apresentado diretamente. Isso prova que o BitNinja termina TLS antes do Nginx. O modo obrigatório não foi ativado; associação foi invalidada, arquivos `/etc` removidos por hash e Nginx/public/direct retornaram ao estado anterior validado.
- **Origin HTTP concluído — `1548887444995313759`:** segredo de 32 bytes armazenado no 1Password; Transform Rule Cloudflare `6cdf2882fe324a2d9db8eed147b615c2`/`2ee1ca5d27324dc0af7a43475663f770` injeta e sobrescreve o header somente em `dash.mgsdigitalcorp.com`; Nginx exige o valor no vhost financeiro. Canário: edge `200/PASS`, direto `200/MISS`; enforcement: edge normal e com header forjado HTTP 200, direto sem header e com header incorreto HTTP 403. Hash do segredo confere entre 1Password, Cloudflare e Nginx; outros 77 webapps, AOP global e firewall permaneceram inalterados.
- **MFA all-user ativo — `1548916113142976544`:** enforcement obrigatório ativado para Rodolfo, Geizian, Ícaro, Joe, Isliago, Kelly e Nicolas. Rodolfo foi pré-configurado somente no próprio 1Password, com OTP live e dez recovery codes; os outros seis receberam estados `pending` e QR individual no próximo login, sem dependência do 1Password. Chave mestra está protegida no 1Password e auth config; sete segredos estão AES-256-GCM no banco. Canário produtivo: senha owner sem OTP→202, OTP incorreto→401, OTP correto→200, replay→401, trust mesmo navegador→200, user-agent diferente e trust revogado→202; seis secrets distintos, zero cookie antes de enrollment. `Confiar neste dispositivo por 30 dias` dispensa somente TOTP depois da senha, limita cinco devices e é revogado no logout.

## Concluído e validado

### Disaster recovery

- O pacote full passou a incluir o código versionável de `apps/finance-system`, excluindo `private`, `node_modules` e caches.
- Toda fonte documental em `reports/` referenciada pelo registry é incluída; o primeiro canário revelou duas fontes superseded ausentes, a seleção foi corrigida para preservar também fontes históricas requeridas pelo validator, e o segundo canário passou.
- Um dump PostgreSQL custom atual de `mgs_finance` é criado como componente próprio, com tamanho, SHA-256 e catálogo `pg_restore --list`.
- Novo backup full criptografado criado sem retenção destrutiva: Drive ID `1RLKDwgyafYUM77-H039OhkFAmHh0LQr7`, 3.945.932.314 bytes, zero arquivos antigos descartados.
- Restore desse arquivo passou: 5 componentes, 3 profiles, 15 SQLite, knowledge validation PASS e catálogo PostgreSQL PASS.
- Depois do hardening, um novo full atual passou a incluir também 16 arquivos críticos do runtime remoto — units, Nginx, certificado/chave TLS, auth protegido e configuração PostgreSQL — como sexto componente. Drive ID `1z9CSZ1kRe1y9pTiIXMu2TB6Uwim08lDF`, 3.949.809.165 bytes, sem retenção destrutiva; restore 6/6, knowledge PASS, 15 SQLite, infraestrutura 16/16 e catálogo PostgreSQL PASS.
- O monitor agora registra toda tentativa e falha imediatamente quando a tentativa mais recente falha, mesmo se houver um sucesso anterior dentro do SLA.
- O dump do primeiro full corrigido foi materializado em `mgs_finance_dr_1548835136693600328`, validado e descartado após PASS; o banco produtivo `mgs_finance` permaneceu intocado. O segundo full usa o mesmo caminho determinístico de geração e passou em hash, catálogo e infraestrutura restaurada.

### Performance

- `/api/workspace` ganhou cache LRU do payload serializado, limitado a quatro revisões.
- Chave: cenário + revisão + revisão de contas + timestamp de cotações. Mudança de revisão força miss e hit preserva o payload byte a byte.
- Observabilidade: `X-MGS-Workspace-Cache` e `Server-Timing`.
- Assets autenticados passaram de `no-store` para `private, no-cache` com ETag; APIs continuam `no-store`.
- p95 de 20 consultas concorrentes caiu de 27,14 s para 3,35 s: redução de 87,7%.
- p95 sequencial atual de `/api/workspace`: 0,68 s; última medição anterior pós-warm ficou entre 0,38 s e 0,94 s.
- O payload bruto de 5,84 MB permanece, mas deixou de gerar recomputação repetida. Slicing/lazy endpoints foi evitado nesta fase porque aumentaria a superfície de regressão financeira sem benefício proporcional depois da redução medida.

### Segurança e runtime

- `/api/health` autenticado agora informa `mode=production` e `production=true`.
- HSTS por um ano e Permissions-Policy restritiva estão ativos; CSP, cookie `__Host-`, CSRF, Host/Origin e arquivos privados continuaram aprovados.
- Sessões atualizam `last_seen` no máximo uma vez por minuto, mantendo idle timeout de 30 minutos. Readback produtivo: duas sessões recentes tiveram delta `last_seen-created_at=0` durante múltiplos requests.
- Nenhuma sessão ou histórico de auditoria foi apagado.
- Suporte TOTP foi implantado de forma fail-closed, mas segue desativado porque a configuração e o 1Password ainda não têm segredo OTP. Vetor RFC 6238 e login com/sem código passaram em testes isolados.
- O cron preflight não depende mais de `croniter` em cache. O expansor stdlib foi comparado contra croniter em 69 expressões × 3 janelas, incluindo DST: 207/207 equivalentes. Preflight real `3 9 * * *` foi reexecutado sem `PYTHONPATH` de cache e passou sem conflito operacional.

### Documentação e skill

- `finance-system-product-direction.md`, `README.md` e `PG-AUTH-RUNBOOK.md` foram atualizados para produção, cutoff dinâmico, horários 08:03/08:08/08:18/08:28, remuneração confirmada, rollout dos cinco gestores, DR atual e hardening vigente.
- `mgs-finance-dashboard` passou para v0.1.52, ganhou referência progressiva de segurança/performance/DR e removeu a trava histórica Nicolas-only.
- O monólito histórico da skill foi preservado; uma extração estrutural ampla não foi feita na mesma alteração semântica para não misturar migração de conteúdo com correção de regras.

## Evidência atual

- Node: 141/141 PASS.
- Python finance-system: 98/98 PASS.
- DR unitário: 9/9 PASS.
- Knowledge validation: zero erros.
- Knowledge regression: 17/17 PASS.
- Browser público: owner, partner e cinco gestores; 24 competências, desktop/mobile, zero erro JavaScript, zero POST financeiro.
- Segurança: 401/403/404 esperados, HSTS/CSP/Permissions-Policy/cookie/CSRF aprovados.
- Produção: serviço ativo, socket privado ativo e login público aprovado.

## Estado crítico final

1. MFA de todos: `mfa_required=true`, trust 30 dias, Rodolfo `active`, outros seis `pending`, sete segredos criptografados e dez recovery hashes do owner. Nenhuma sessão válida de teste permaneceu. Os seis usuários pending ficam sem acesso financeiro até confirmar o próprio Google Authenticator ou compatível.
2. Origin: gate Cloudflare/Nginx ativo; edge HTTP 200, direto HTTP 403, outros 77 webapps inalterados.
3. Systemd: unit SHA-256 `18b9a69351f7868a07e396630ce94148e4f0acc312734b1b1c1ee23e5634d8eb` aplicado, runtime ativo e exposição 2.2 OK.
4. Restore PostgreSQL: drill materializado concluído; `mgs_finance_dr_1548835136693600328` ausente após DROP confirmado e `mgs_finance_restore` preservado.

## Incidentes autocorrigidos

- Primeiro canário MGS falhou por duas fontes registry históricas ausentes; a cobertura foi ampliada e o segundo canário passou.
- Primeiro deploy de higiene de sessão causou login HTTP 500 porque o role produtivo não tem DELETE, como deveria. A limpeza destrutiva foi retirada, o serviço corrigido/reiniciado e login voltou a PASS; nenhum dado financeiro foi afetado.
- Primeira validação local do socket usou o caminho errado e depois Host incorreto; o runtime estava ativo. A validação foi repetida com `/run/mgs-finance-dash.sock`, usuário correto e Host canônico, passando.
- Auditoria posterior atingiu 429 por executar repetidos logins de QA dentro de 15 minutos. Somente o estado transitório de rate limit foi zerado, o teste foi repetido e passou; a proteção permaneceu ativa.
- Rodolfo reportou em `1548936711084572714` que o botão `Verificar código` não fazia nada. Reprodução real mostrou primeiro POST=1 e segundo POST=0: ao esconder a etapa de credenciais, o JavaScript limpava a senha, mas mantinha o input oculto como `required`; a validação nativa do navegador bloqueava o submit antes do handler. A correção desabilita inputs ocultos por etapa. Readback produtivo: owner fez segundo POST=1, OTP real redirecionou para a dashboard em mobile sem erro; Geizian fez segundo POST=1, código inválido exibiu erro e não criou sessão.

## Gate final atualizado

Hardening systemd, restore materializado, bloqueio do origin e MFA obrigatório estão concluídos. O full pós-correção de login `1JH3NVdNPWAXwXkkbvfEb8zej8AxQTsMn` contém 6 componentes, infraestrutura 17/17, auth protegido e banco MFA, com restore PASS e zero retenção destrutiva. Implementação encerrada; resta ação humana individual de Geizian e dos cinco gestores para escanear o QR e mudar seus estados de `pending` para `active`.
