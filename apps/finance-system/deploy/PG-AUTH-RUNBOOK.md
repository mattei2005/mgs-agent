# MGS Finance — PostgreSQL e acesso autenticado

## Estado e autoridade

Confirmação crítica de Rodolfo: `1545934831664242748`, thread `1545426987756298340`. Supersede, somente quanto a banco/login/transporte, o estado histórico de preparação descrito em `deploy/README.md`. Não encerra a migração funcional integral nem troca a fonte financeira oficial.

- Acesso: https://dash.mgsdigitalcorp.com/login.
- Administrador único: `rodolfo`. Senha somente no 1Password, item `MGS Finance - rodolfo - dash.mgsdigitalcorp.com`. Sem cadastro público ou autorização de outras pessoas.
- MatteiInc01, RunCloud server 290075, webapp 3012868. Document root continua sem dados financeiros.
- Release ativo: `/home/mgsfinance/releases/pg-auth-1545934831664242748`.
- Aplicação: `mgs-finance-dash.service` + `mgs-finance-dash.socket`, Node isolado v22.23.2. Socket `/run/mgs-finance-dash.sock`, owner mgsfinance, grupo runcloud-www, modo 0660. PrivateNetwork=true e restrição AF_UNIX preservam isolamento.
- PostgreSQL 18.6: `/opt/mgs-postgresql18`, serviço independente `mgs-postgresql18`. Binários de pacotes oficiais extraídos em prefixo privado; não é uma instalação gerenciada pelo dpkg. PostgreSQL e cliente usam sua própria libpq via LD_LIBRARY_PATH. A simulação de apt exigia atualizar a libpq global; a instalação isolada evitou isso.
- Dados PG: `/var/lib/mgs-postgresql18/data`; socket `/run/mgs-postgresql18`. Sem listener TCP. Usuário administrativo OS/DB `mgs_pg`; role app `mgsfinance`, banco `mgs_finance`, autenticação peer, sem senha de banco nem superuser na aplicação.
- Node global v18.20.8, libpq global 14.24, MariaDB, 77 webapps e 577 arquivos Nginx anteriores preservados e verificados.
- Repositório PGDG tem pin baixo para não atualizar dependências compartilhadas por efeito lateral. Atualizações desse PostgreSQL isolado exigem workflow explícito: versões verificadas, novo prefixo, backup, compatibilidade, canário e rollback; apt/unattended-upgrades não mantém este runtime privado.
- Nginx encaminha apenas este hostname ao socket. Cloudflare tem regra Configuration Rule `ssl=strict` exclusiva para este hostname; SSL global não foi alterado.

## Autenticação e permissões

- Registro de hash/salt scrypt fora do Git: `/home/mgsfinance/.config/finance/auth.json`; senha original somente no 1Password. Não registrar payloads de login, cookies, hash/salt ou respostas integrais de 1Password em logs.
- Sessões persistidas no PostgreSQL; tokens aleatórios ficam no cookie, somente hash no banco. Cookie `__Host-mgs_finance`: Secure, HttpOnly, SameSite=Strict, Path=/, sem Domain.
- Expiração absoluta de 8 horas e inatividade de 30 minutos; logout revoga a sessão no banco. CSRF exigido nas mutações; Host/Origin validados. Login tem limitação de tentativas por IP e global.
- Eventos usam identidade do login; role da aplicação não pode reescrever/apagar auditoria, alterar fontes importadas ou modificar baseline/cenários bloqueados. Grants e trigger, além da API, protegem os dados.
- Todas as APIs/dados/assets do sistema exigem login. `/login`, `/login.js`, `/login.css` são públicos. Sem autenticação, APIs retornam 401; arquivos privados nunca são servidos, mesmo autenticado.
- Um link externo pode abrir GET /login: não bloquear navegação segura apenas por Sec-Fetch-Site cross-site. Mutações cross-site continuam bloqueadas.
- Produção emite CSP restritiva, HSTS por um ano, Permissions-Policy fechada, cookie `__Host-` Secure/HttpOnly/SameSite=Strict, Host/Origin e CSRF. `/api/health` autenticado identifica corretamente `mode=production` e `production=true`.
- MFA individual obrigatório está ativo sob confirmação crítica `1548916113142976544` para as sete identidades atuais. Rodolfo está `active`, com TOTP e dez recovery codes apenas no próprio item do 1Password. Geizian, Ícaro, Isliago, Joe, Kelly e Nicolas estão `pending`: no próximo login por senha, cada um deve escanear seu QR individual no Google Authenticator ou compatível, confirmar o código e guardar dez recovery codes; antes disso não recebe sessão nem acessa dados financeiros. Segredos únicos ficam AES-256-GCM no banco e somente hashes dos recovery codes são persistidos; replay TOTP é bloqueado.
- `Confiar neste dispositivo por 30 dias` está ativo como opção: cookie aleatório HttpOnly/Secure/SameSite=Strict, somente hash no servidor, vinculado a usuário e user-agent; dispensa somente TOTP após senha correta, não prolonga a sessão de 8h/idle 30min, limita cinco dispositivos e é revogado no logout. O canário produtivo confirmou trust no mesmo dispositivo, rejeição em user-agent diferente e revogação após logout.
- Per-hostname Cloudflare AOP não pode ser exigido no Nginx deste host enquanto o BitNinja terminar TLS antes de `nginx-rc`: canário `optional` retornou `$ssl_client_verify=NONE` pela Cloudflare e também com o certificado correto apresentado diretamente. Nunca ativar `ssl_verify_client on` nessa arquitetura sem um canário `SUCCESS`; o teste autorizado foi revertido por hash. Sob confirmação crítica `1548887444995313759`, o origin passou a usar header secreto em camada HTTP: Transform Rule Cloudflare exclusiva de `dash.mgsdigitalcorp.com` sobrescreve o header e o vhost financeiro o exige. Readback final: edge normal/forjado HTTP 200, origin direto sem header ou com header incorreto HTTP 403; outros webapps e AOP global inalterados.

## Migração e evidência

PGlite antigo foi parado antes de exportar. Migração preservou os seis conjuntos de tabelas legadas por contagem e hash semântico, incluindo 85.868 registros de células (auditoria + dependências de fronteira). PostgreSQL recebeu o esquema, registros e permissões; inicialização em produção não executa DDL nem reimporta dados.

- `deploy/export-pglite.mjs`: exportação SQL transacional + manifesto, usando conversão JSON pelo próprio PostgreSQL/PGlite.
- `storage.mjs`: adapter pg com transação em conexão dedicada; PGlite permanece apenas para testes/rollback histórico.
- Baseline de agosto: PARITY_PASS e resultado de referência R$ 90.840,88. A planilha não foi alterada; mês continua provisório quanto a taxas efetivas de liquidação.
- Restore isolado `mgs_finance_restore` comprovou paridade, rollback transacional, persistência, privilégios e proteção do baseline. Dados de teste pertencem ao banco isolado, não ao cenário de referência.
- Browser público: nove telas, zero erros JS, viewport 390px, cookie seguro, CSRF, logout e revogação. Script `tests/public-auth.mjs` recebe credenciais via stdin, nunca imprime valores nem salva sessão.
- Evidências privadas: `private/pg-auth-1545934831664242748/`, em especial `final-summary.json`, `browser-public-evidence.json`, manifesto de migração e readback Cloudflare. Não anexar esses arquivos sem solicitação.

## Backup e limites operacionais

- Backup anterior e dump PG validado: `/home/zeus/mgs-finance-backups/1545934831664242748/`, MatteiInc01.
- Dump consistente `mgs_finance-first.dump` restaurado no banco isolado; segunda cópia no host Zeus em `private/pg-auth-1545934831664242748/mgs_finance-first.dump`, hash idêntico e permissões restritas.
- O DR recorrente completo agora inclui profiles, MGS OS, código versionável da aplicação, fontes documentais registradas e um dump PostgreSQL custom atual. O bundle é criptografado antes do upload e a execução de recuperação valida download/hash, componentes, ZIPs, SQLite, conhecimento institucional e catálogo do dump PostgreSQL. O monitor falha imediatamente quando a tentativa de restore mais recente falha, em vez de confiar apenas na idade do último sucesso.
- O restore PostgreSQL materializado deve usar um banco isolado e validar schema/contagens/consultas sem tocar `mgs_finance`; o descarte desse banco isolado exige confirmação destrutiva específica.
- Drill materializado `1548867037416259627` concluído com o componente off-site: `mgs_finance_dr_1548835136693600328` restaurou 121 cenários, 85.868 source cells, 799 audit events e ledger vazio legítimo; após PASS, somente esse banco isolado foi descartado. O banco produtivo e `mgs_finance_restore` permaneceram preservados.
- Preservar release antigo, backups e banco de restore. Não excluir nem aplicar retenção automática por inferência.

## Verificação e rollback

1. `systemctl is-active mgs-postgresql18 mgs-finance-dash mgs-finance-dash.socket`; validar PostgreSQL pelo socket, usando identidade peer correta e cliente do prefixo isolado.
2. `sudo -n /usr/local/sbin/nginx-rc -t`; aviso preexistente ssl_stapling Wantabrand não é causado pela aplicação.
3. HTTPS validado sem -k: `/login` 200; `/api/scenarios` sem cookie 401. Health interno pelo socket exige autenticação; não confundir 401 com processo parado.
4. Login real: baseline PARITY_PASS, cookie correto, CSRF e logout. Nunca imprimir cookie/senha. Auditoria registra esses acessos de validação.
5. Em falha de segurança, restaurar somente o gate financeiro 503 a partir do artefato histórico, testar Nginx e recarregar. Preservar banco e investigar antes de reabrir.
6. Rollback de aplicação pode retornar ao release/PGlite histórico **somente com o gate público fechado**, pois o código antigo não possui login. Não reabrir o proxy sobre a versão antiga.
7. Rollback de banco exige backup adicional de quaisquer lançamentos posteriores. Jamais sobrescrever o PostgreSQL ativo ou toda a árvore Nginx compartilhada para reverter uma implantação.

O unit `mgs-finance-dash.service` foi endurecido sob confirmação `1548867037416259627`: SHA-256 ativo `18b9a69351f7868a07e396630ce94148e4f0acc312734b1b1c1ee23e5634d8eb`, `systemd-analyze security` 2.2 OK, capability set vazio, devices/kernel/namespaces/`/proc` restritos. Backup exato anterior permanece em `/home/mgsfinance/backups/finance-systemd-1548867037416259627/`.

## Escopo integral ainda aberto

Cadastros versionados completos, vigências, inativação, abertura/fechamento nativo de períodos e retirada da dependência do grafo de fórmulas continuam como limites de evolução. Login e PostgreSQL reais colocam a aplicação em produção, mas não a transformam por si só em substituta integral de todas as fontes da planilha.
