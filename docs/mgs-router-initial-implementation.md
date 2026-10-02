# MGS Router — implementação inicial e gate de publicação

Dono: Rodolfo Mattei. Agente: Zeus. Fonte de autorização: mensagem Discord 1555607199915708487, thread 1555381168894115912.

## Decisão

Painel em `https://route.mgsdigitalcorp.com`, na VPS atual `2.25.165.171`. Contas individuais para Rodolfo e Geizian, somente no aplicativo de rotas. Não alterar `authorized-users.json` dos agentes nem dar acesso à VPS/Cloudflare aos usuários do painel.

## Estado confirmado

- Código local em `apps/mgs-router/`, Go stdlib e interface PT-BR.
- 15 testes passaram; teste real de navegador confirmou cadastro, edição de destino, filtro, layout mobile sem overflow, logout e zero erros JavaScript.
- `go test -race`, `go vet`, sintaxe JavaScript e build passaram.
- Sem implementação de tracking, relatórios ou cliques.
- Nenhuma rota real importada ainda. Testes usam rotas e usuários explicitamente sintéticos, somente localhost.
- Cloudflare: zona mgsdigitalcorp.com ativa e visível via item `Cloudflare MGS Admin Token - mattei20052`; item mattei2005 ativo mas sem essa zona. Registro `route.mgsdigitalcorp.com` ausente. SSL da zona é `full`.
- Origem pública verificada: `2.25.165.171`; sem listener em 443 no preflight.
- Zeus, Atena e Ares permaneceram ativos após os testes.
- Não publicado, sem usuários/senhas de produção criados e sem mudanças em DNS, DTR ou SB.

## Confirmação pendente (não executada)

1. Cloudflare: criar um único registro `A`, nome `route.mgsdigitalcorp.com`, conteúdo `2.25.165.171`, `proxied=true`, `ttl=1` (Auto). Não alterar SSL da zona inteira. Validar readback do registro e HTTPS público.
2. Sistema: criar usuário/grupo dedicado `mgs-router` sem shell/login administrativo; criar `/etc/systemd/system/mgs-router.service` a partir do draft em `apps/mgs-router/deploy/mgs-router.service`; serviço próprio HTTPS/443 com `CPUQuota=50%` (metade de um core), `MemoryHigh=192M`, `MemoryMax=256M`, `TasksMax=64`, sem restart dos agentes e sem reboot. Publicar binário em `/opt/mgs-router/`, estado em `/var/lib/mgs-router/`.
3. HTTPS origem: gerar certificado TLS autoassinado válido para `route.mgsdigitalcorp.com`, compatível com Cloudflare Full atual, com chave privada em custódia 1Password e cópia operacional protegida. Não é certificado publicamente confiável para acesso direto à origem. A aplicação restringirá peers aos 22 CIDRs oficiais Cloudflare e só então confiará no cabeçalho de IP do cliente. Certificado/chave são novo material criptográfico; exigem confirmação crítica.
4. Contas: gerar senhas individuais para usernames propostos `rodolfo` e `geizian`, ambos com gerenciamento de rotas (sem cadastro público, sem acesso à VPS/Cloudflare/agentes). Fonte canônica de segredos: 1Password `MGS Conteúdo`, itens propostos `MGS Router - Rodolfo` e `MGS Router - Geizian`. Nunca enviar valores por Discord. Sem compartilhamento de vaults ou links de credencial autorizado por este pedido.

Antes de aplicar, revalidar ausência de DNS/contas/unidade e origem. Drift significa novo precheck; não sobrescrever recursos concorrentes.

## Próximo passo

Obter a confirmação adicional das operações críticas e do diff DNS, aplicar somente esse conjunto e verificar: DNS exato, serviço restrito, HTTPS via Cloudflare, bloqueio direto à origem e login de cada usuário pelo fluxo protegido. Migração de rotas reais/DTR/SB fica separada, sem alteração automática nesta publicação.

## Rollback proposto

Parar apenas o novo serviço se algum canário falhar; manter código, evidências e estado para diagnóstico. Não remover arquivos, contas ou DNS sem o gate aplicável; revertê-los exige confirmação ou autorização de rollback exata. Não reiniciar os agentes.
