# MGS Router — publicação e acessos validados

## Fonte e autoridade

Rodolfo confirmou o conjunto exato na mensagem `1555623974673842279`, thread `1555381168894115912`, após o pedido inicial `1555607199915708487`. Esta fonte sucede `docs/mgs-router-initial-implementation.md` para o estado de implantação.

## Estado vigente

- Painel: https://route.mgsdigitalcorp.com/login
- Software próprio, somente rotas/redirecionamentos + interface; sem Keitaro, tracking, estatísticas ou relatórios.
- Origem: VPS atual `2.25.165.171`.
- Cloudflare: registro A `route.mgsdigitalcorp.com` → `2.25.165.171`, proxied=true, ttl=1 (Auto), readback exato confirmado. Demais registros e SSL global da zona não alterados.
- Serviço `mgs-router.service` ativo/running e enabled. Processo não-root `mgs-router`, CPUQuota=50% de um core, MemoryHigh=192M, MemoryMax=256M, TasksMax=64; NoNewPrivileges e ProtectSystem=strict confirmados.
- HTTPS público validado com certificado do edge Cloudflare. Origem usa certificado autoassinado; chave em 1Password e cópia operacional root-only. Acesso direto à origem bloqueado pela aplicação (HTTP403); somente peers da lista oficial Cloudflare são aceitos. Sem alteração de firewall.
- Contas `rodolfo` e `geizian` provisionadas e com login, API autenticada, UI pública desktop/mobile e logout validados individualmente. Ambos gerenciam rotas; nenhum acesso adicional à VPS, Cloudflare ou agentes foi concedido.
- Senhas: 1Password, vault `MGS Conteúdo`, itens `MGS Router - Rodolfo` e `MGS Router - Geizian`. TLS: `MGS Router - Origin TLS`. Nenhum valor secreto enviado por Discord ou gravado em Git. Compartilhamento de vaults/itens não foi executado.
- Painel ainda sem rotas reais cadastradas. DTR, SB e domínios de tráfego Wantabrand intactos.

## Validação

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

Cadastro/importação das rotas reais e eventual troca de links DTR/SB são etapas separadas; não foram executados nesta publicação. Não tratar a versão atual como aprovada para incluir pesos, geofiltros, tracking, relatórios ou cadastro público.

Rollback imediato seguro: parar somente o novo serviço para conter falha, preservando código, estado e evidências. Remoção de arquivos/contas/DNS e rotação de credenciais continuam sujeitas aos gates aplicáveis.
