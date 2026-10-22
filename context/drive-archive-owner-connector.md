# Conector proprietário de arquivo 30 TB — autorização isolada

## Autoridade

Rodolfo Mattei autorizou explicitamente em `1562888530265374731`, thread `1562078493498540042`, a substituição do executor de criativos Apps Script por um conector privado na VPS, com nova autorização de leitura/gravação no Drive da mesma conta de 30 TB. Proposta vinculada: `data/ares/creative-ops/30tb-archive/owner-connector-architecture-proposal-1562884023607492619.json`.

## Limites ativos da autorização

- Owner do conector: `mgsdigitalcorp@gmail.com`, Google permission ID `03783617840924670288`.
- Projeto de configuração: `mgs-core-prod`.
- Source Drive: `0AEwt4Ye690ocUk9PVA`; source criativo: `1h8wEYDcn2SYLZI-Cp4dMpxfwFUqQXhpa`.
- Arquivo criativo: `1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J`.
- OAuth novo exclusivamente para este componente, segredo persistente apenas no 1Password. Escopo necessário de Drive é de conta; limites de raízes/ações são impostos pelo programa, não uma alegação falsa de autorização OAuth por pasta.
- Os agentes continuam exclusivamente com a SA `mgsagent@mgs-core-prod.iam.gserviceaccount.com` e o helper canônico. Não alterar seus seletores, reutilizar client secrets/tokens pessoais retirados, introduzir fallback OAuth nos consumidores ou permitir Gmail/Calendar/Contacts.
- A autorização inclui configuração e consentimento iniciais. Não inclui mudar billing, concessões IAM, compartilhamentos, senha, 2FA, permissões de rede pública ou ampliar exclusão histórica.
- Não habilitar writer produtivo antes de autenticação real, canário e prova independente SA, reconciliação das cópias/intents antigos e handoff exclusivo. Preservar outros fluxos de backups/corporativo e as regras de retirada vigentes.

## Estado de implantação

**Autorizado, não implantado em produção.** Configuração/autenticação são uma fase separada da migração entregue. O Google recusou a entrada automatizada do usuário no navegador VPS antes de mostrar a senha: `This browser or app may not be secure`. Nenhuma senha foi preenchida, nenhum token antigo foi usado. É necessário usar o navegador normal do proprietário para a configuração Google inicial e consentimento; o PC não será executor permanente.

O bootstrap deve permanecer privado no tailnet, sem Funnel, API pública de execução ou exposição de segredos. O fluxo atual permanece preservado até handoff validado.
