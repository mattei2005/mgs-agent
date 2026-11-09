# Comunicado individual de outubro

## Decisão ativa — Rodolfo1569167402279764110

Thread1545426987756298340, autorDiscord344196393512075265. O texto aprovado em1569167241943973980 e autorizado por1569167402279764110 **supersede** a versão numérica1569165518093426809: sem valores, percentuais, comparação antes/depois ou parágrafo especial deÍcaro. Resolve o bloqueio de conteúdo numérico encontrado no primeiro preflight; não muda regras financeiras.

Destinatários exatos, ativos, role manager e manager_key correspondente: `icaro`, `isliago`, `joe`, `kelly`, `nicolas`. Saudações: Ícaro, Isliago, Joe, Kelly, Nicolas. Rodolfo e Geizian não recebem o aviso. Não há destinatário por simples acesso global nem por correspondência parcial do nome.

## Texto aprovado

Título: **Atualização do resultado de outubro**

Olá, {nome}.

Identificamos que os gastos com anúncios de Mavroa, Vizioid e Escalatepower estavam registrados nos sites, mas não estavam sendo descontados do seu resultado individual de outubro.

Essa falha foi corrigida. Os gastos passaram a ser considerados no cálculo, e seu resultado e sua remuneração foram atualizados conforme as regras já existentes.

Você pode consultar os dados atualizados na Dash.

Qualquer dúvida, pode me chamar.

Att.,
Rodolfo

Botão: **Entendido**

## Comportamento e limites

- Exibir no próximo acesso à interface autenticada. Sessões persistentes existentes não precisam ser revogadas; não exigir novo login para receber o comunicado.
- Enquanto não houver ciência, o aviso permanece pendente. Fechar aba/sair não registra leitura. Para o gestor, Esc/backdrop não equivalem a Entendido.
- Confirmação persistente na conta, no servidor, por usuário e ID imutável `october-result-1569167402279764110`; após confirmação, não reapresentar esse comunicado em outros acessos, dispositivos ou browsers. Não usar localStorage/cookie como fonte da ciência.
- Clique significa leitura, não aprovação do cálculo, pagamento ou consentimento a novas regras.
- Salvar somente com identidade autenticada, Origin/CSRF válidos, papel/manager_key/usuário elegíveis e conta ativa. Revalidar usuário e serializar por lock de linha, tornando repetição e concorrência idempotentes.
- Recibo em `audit_events`, ação `NOTICE_ACKNOWLEDGED`, actor real e after_data com notice_id, autoridade, meaning=read_receipt_only e hash do conteúdo. Não alterar cenários, ledger, história financeira, permissões, MFA ou sessões dos gestores. Nenhuma migração de schema/grants necessária.
- `GET /api/auth/notices`: somente conteúdo do próprio destinatário ou owner-preview autorizado. `POST /api/auth/notices/:id/ack`: corpo vazio; sem seletor de outro usuário. Responder sucesso somente após commit e readback. Erro/timeout mantém dialogo e oferece tentativa idempotente.
- Owner-preview é somente leitura, com Entendido desabilitado; Esc fecha somente a prévia local, sem gravar ciência. Zeus não confirma em nome de gestor durante QA produtivo.
- Recebimentos não alteram o marcador de atualização financeira global. Novo comunicado futuro precisa de nova autoridade e novoID; não reciclar esteID para forçar reexibição.

## Estado de implementação

Verificar checkpoint `ZEUS-FINANCE-NOTICE-1569165518093426809`, journal `manager-notice-1569167402279764110` e relatório `reports/finance-october-manager-notice-1569167402279764110.md`. Esta decisão não prova publicação por si só.

Pacote privado: `apps/finance-system/private/notice-1569167402279764110/`. Candidato isolado, snapshot real revisão1524 e testes sintéticos de identidade somente no banco isolado. Não copiar sessões/segredos de gestores.

## Histórico supersedido

A primeira proposta1569165518093426809 incluía valores e faixa deÍcaro. Preflight2026-11-09T01:44:52.827Z encontrou valores posteriores por câmbio provisório e pela correçãoZuout autorizada1569051595935850601. Fontes: `reports/finance-zuout-g006-1569051595935850601.md`, `apps/finance-system/private/fb-oct-fix-1569031159805911112/final-executive-values.json`. Não era nova falha nem anomalia. Propostas subsequentes emUSD oupercentual também foram descartadas pela aprovação final sem números. Nenhuma quantia histórica deve ser incorporada ao aviso ativo.
