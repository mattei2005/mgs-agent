# MGS Router — publicação e acessos validados

## Fonte e autoridade

Rodolfo confirmou o conjunto exato na mensagem `1555623974673842279`, thread `1555381168894115912`, após o pedido inicial `1555607199915708487`. Esta fonte sucede `docs/mgs-router-initial-implementation.md` para o estado de implantação.

## Estado vigente

Extensão vigente de domínios, instruções DNS e importação ponderada: `docs/mgs-router-domain-and-keitaro-import.md` (41 rotas importadas; nenhum cutover DNS). Organização vigente do painel e catálogo: `docs/mgs-router-catalog-layout.md` (Rotas/Destinos/Grupos/Cadastro domínios). Esta extensão não muda DNS nem links ativos.

- Painel: https://route.mgsdigitalcorp.com/login
- Software próprio, somente rotas/redirecionamentos + interface; sem Keitaro, tracking, estatísticas ou relatórios.
- Origem: VPS atual `2.25.165.171`.
- Cloudflare: registro A `route.mgsdigitalcorp.com` → `2.25.165.171`, proxied=true, ttl=1 (Auto), readback exato confirmado. Demais registros e SSL global da zona não alterados.
- Serviço `mgs-router.service` ativo/running e enabled. Processo não-root `mgs-router`, CPUQuota=50% de um core, MemoryHigh=192M, MemoryMax=256M, TasksMax=64; NoNewPrivileges e ProtectSystem=strict confirmados.
- HTTPS público validado com certificado do edge Cloudflare. Origem usa certificado autoassinado; chave em 1Password e cópia operacional root-only. Acesso direto à origem bloqueado pela aplicação (HTTP403); somente peers da lista oficial Cloudflare são aceitos. Sem alteração de firewall.
- Contas `rodolfo` e `geizian` provisionadas e com login, API autenticada, UI pública desktop/mobile e logout validados individualmente. Ambos gerenciam rotas; nenhum acesso adicional à VPS, Cloudflare ou agentes foi concedido.
- Senhas: 1Password, vault `MGS Conteúdo`, itens `MGS Router - Rodolfo` e `MGS Router - Geizian`. TLS: `MGS Router - Origin TLS`. Nenhum valor secreto enviado por Discord ou gravado em Git. Compartilhamento de vaults/itens não foi executado.
- Estado atual: 41 rotas Wantabrand importadas, catálogo com 94 destinos e 3 grupos. DNS, Keitaro, DTR e SB não alterados; sem cutover de tráfego. O estado vazio pertencia somente à publicação inicial.

## Validação

### Correção de login nativo

O incidente de Rodolfo `1555628473278533742` revelou uma lacuna nos smokes iniciais: o login era testado por HTTP com Origin definido manualmente e a UI por cookies já autenticados, não pelo transporte do formulário nativo. O cabeçalho `Referrer-Policy: no-referrer` fazia Chromium enviar `Origin: null` em POST de formulário e o servidor rejeitava com `invalid origin`. A reprodução pública confirmou403; trocar apenas o cabeçalho do documento para `same-origin` fez o navegador enviar a origem correta. A correção foi aplicada apenas às páginas HTML, sem aceitar Origin null e sem relaxar CSRF, preservando no-referrer nos redirects de tráfego.

18 testes passaram após a correção, incluindo regressão em navegador do envio nativo de formulário vazio (sem credenciais), rejeição de origens opacas/externas e privacidade de redirects. Os logins reais das duas contas por HTTPS, API, UI autenticada e logout foram revalidados separadamente. Não afirmar que o smoke com formulário vazio foi um login com senha pelo DOM. Receipt de correção: `data/mgs-router-login-origin-repair.json`. Senhas, chave TLS, unidade e PIDs dos agentes permaneceram inalterados; somente o serviço do roteador foi reiniciado após troca atômica de binário, com rollback preservado fora de Git.

### Validação inicial e controles preservados

- 15 testes locais e checks de race/vet/JS/build passaram na implementação.
- Publicação: `/healthz` HTTP200 via Cloudflare; API anônima HTTP401; origem direta HTTP403.
- Para cada conta: login HTTP303 para `/admin`; cookies Secure/HttpOnly/SameSite Strict; API autorizada HTTP200; navegador real confirmou username correto, formulário de nova rota, ausência de rotas, layout mobile sem overflow e zero erros JavaScript; logout invalidou a sessão (API volta a401).
- PIDs Zeus/Atena/Ares permaneceram idênticos ao pre-deploy. Nenhum restart dos agentes ou reboot da VPS.
- Configuração e chaves operacionais com permissões restritas; sem credenciais de produção em código/argv/output.

## Fontes técnicas

- Código: `apps/mgs-router/`.
- Unidade: `/etc/systemd/system/mgs-router.service` (draft versionado em `apps/mgs-router/deploy/`).
- Binário e redes Cloudflare: `/opt/mgs-router/`.
- Estado privado do aplicativo: `/var/lib/mgs-router/` (fora de Git).
- Custódia operacional TLS: `/root/.local/share/mgs-router-private/` (fora de Git).
- Receipt: `data/mgs-router-deployment.json`.
- Prova pública sanitizada: `data/mgs-router-public-validation.json`.
- Executor inicial vinculado à confirmação: `scripts/mgs-router-deploy-initial.py`; não é autorização permanente para mudanças futuras.
- Verificação sem alterar rotas: `scripts/mgs-router-verify-public.py`.

## Limites e próxima etapa

Ainda não há comprovação de capacidade em tráfego real ou mitigação de DDoS da VPS inteira; os limites do processo não isolam o domínio de falha da máquina. Migração para VPS nova exige novo conjunto autorizado se incluir custos/credenciais/configuração crítica.

A publicação inicial não incluiu importação nem pesos; as aprovações posteriores documentadas nas extensões vigentes autorizaram distribuição ponderada, importação das 41 rotas e catálogo/grupos. Troca DNS/cutover e alteração de links DTR/SB continuam separadas e não executadas. Geofiltros, tracking, relatórios e cadastro público não estão aprovados.

Rollback imediato seguro: parar somente o novo serviço para conter falha, preservando código, estado e evidências. Remoção de arquivos/contas/DNS e rotação de credenciais continuam sujeitas aos gates aplicáveis.
