# Remediação da auditoria integral financeira — 1548835136693600328

## Estado executivo

A autorização ampla de Rodolfo foi executada até o limite não crítico. Na confirmação crítica `1548867037416259627`, Rodolfo adiou MFA e autorizou origin mTLS, hardening do unit e restore+DROP isolado. O hardening e o restore foram concluídos. O mTLS foi tentado em canário opcional, provou-se incompatível com a terminação TLS transparente do BitNinja e foi revertido antes de qualquer modo estrito. O núcleo financeiro permanece íntegro.

### Atualização crítica — 1548867037416259627

- **Systemd concluído:** unit atual substituído pelo candidato SHA-256 `18b9a69351f7868a07e396630ce94148e4f0acc312734b1b1c1ee23e5634d8eb`; exposição caiu de 7.2 MEDIUM para 2.2 OK. Serviço, socket e browser integral passaram depois do restart.
- **Restore PostgreSQL concluído:** o componente do backup off-site `1RLKDwgyafYUM77-H039OhkFAmHh0LQr7` foi restaurado em `mgs_finance_dr_1548835136693600328`; readback: 121 cenários, 85.868 source cells, 799 audit events e ledger legitimamente vazio. O banco isolado foi descartado e `mgs_finance` permaneceu intacto.
- **AOP bloqueado e revertido:** certificado per-hostname foi criado e associado com status Cloudflare `active`, mantendo AOP global `off`. Nginx em modo `optional` recebeu `$ssl_client_verify=NONE` tanto pela Cloudflare quanto quando o próprio certificado foi apresentado diretamente. Isso prova que o BitNinja termina TLS antes do Nginx. O modo obrigatório não foi ativado; associação foi invalidada, arquivos `/etc` removidos por hash e Nginx/public/direct retornaram ao estado anterior validado.
- **MFA:** suporte permanece implantado, mas desativado, conforme decisão de deixar por último.

## Concluído e validado

### Disaster recovery

- O pacote full passou a incluir o código versionável de `apps/finance-system`, excluindo `private`, `node_modules` e caches.
- Toda fonte documental em `reports/` referenciada pelo registry é incluída; o primeiro canário revelou duas fontes superseded ausentes, a seleção foi corrigida para preservar também fontes históricas requeridas pelo validator, e o segundo canário passou.
- Um dump PostgreSQL custom atual de `mgs_finance` é criado como componente próprio, com tamanho, SHA-256 e catálogo `pg_restore --list`.
- Novo backup full criptografado criado sem retenção destrutiva: Drive ID `1RLKDwgyafYUM77-H039OhkFAmHh0LQr7`, 3.945.932.314 bytes, zero arquivos antigos descartados.
- Restore desse arquivo passou: 5 componentes, 3 profiles, 15 SQLite, knowledge validation PASS e catálogo PostgreSQL PASS.
- O monitor agora registra toda tentativa e falha imediatamente quando a tentativa mais recente falha, mesmo se houver um sucesso anterior dentro do SLA.
- Resta somente materializar o dump exato em `mgs_finance_dr_1548835136693600328`, validar schema/contagens/consultas e descartar esse banco isolado. O banco produtivo `mgs_finance` não será tocado.

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

- Node: 139/139 PASS.
- Python finance-system: 98/98 PASS.
- DR unitário: 8/8 PASS.
- Knowledge validation: 309 registros, zero erros.
- Knowledge regression: 17/17 PASS.
- Browser público: owner, partner e cinco gestores; 24 competências, desktop/mobile, zero erro JavaScript, zero POST financeiro.
- Segurança: 401/403/404 esperados, HSTS/CSP/Permissions-Policy/cookie/CSRF aprovados.
- Produção: serviço ativo, socket privado ativo e login público aprovado.

## Canários críticos preparados

1. MFA de Rodolfo: estado atual sem OTP no 1Password e sem `totp_secret` no auth.json; código já suporta TOTP sem mudar logins enquanto desativado.
2. Origin: acesso direto atual retorna HTTP 200. Plano per-hostname mTLS/AOP preserva os outros 77 webapps e mantém o AOP global desligado. Cloudflare Free confirmou endpoints hostname/certificate disponíveis por leitura.
3. Systemd: unit atual SHA-256 `f5a1ec88235c248a68c3d4c9d5e07cd5ca82fd9973294e40e245bbf7bce830ea`, exposição 7.2 MEDIUM. Candidato SHA-256 `18b9a69351f7868a07e396630ce94148e4f0acc312734b1b1c1ee23e5634d8eb`, canário runtime ativo e exposição 2.2 OK.
4. Restore PostgreSQL: alvo `mgs_finance_dr_1548835136693600328` está ausente; o banco antigo `mgs_finance_restore` permanece preservado com 71.833.279 bytes.

## Incidentes autocorrigidos

- Primeiro canário MGS falhou por duas fontes registry históricas ausentes; a cobertura foi ampliada e o segundo canário passou.
- Primeiro deploy de higiene de sessão causou login HTTP 500 porque o role produtivo não tem DELETE, como deveria. A limpeza destrutiva foi retirada, o serviço corrigido/reiniciado e login voltou a PASS; nenhum dado financeiro foi afetado.
- Primeira validação local do socket usou o caminho errado e depois Host incorreto; o runtime estava ativo. A validação foi repetida com `/run/mgs-finance-dash.sock`, usuário correto e Host canônico, passando.
- Auditoria posterior atingiu 429 por executar repetidos logins de QA dentro de 15 minutos. Somente o estado transitório de rate limit foi zerado, o teste foi repetido e passou; a proteção permaneceu ativa.

## Gate final atualizado

Hardening systemd e restore materializado estão concluídos. MFA permanece conscientemente adiado. O único bloqueio técnico é substituir o mTLS, inviável atrás do BitNinja atual, por um controle de origin em camada HTTP: um header secreto inserido pela Cloudflare e exigido somente pelo vhost financeiro. Essa alternativa muda o mecanismo confirmado e requer nova autorização crítica antes de criar o segredo/regra e gravar a configuração Nginx.
