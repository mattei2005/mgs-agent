# Google Ads MCC, perfis e logo quadrado — 1546702931384991834

## Autoridade
Rodolfo, thread 1545426987756298340. Google Ads/cadastro: 1546702931384991834. Logo quadrado: 1546703031033405501. Meu perfil/editar administrador/menu Usuários último/acesso SA MCC: 1546705557996699699. Ativação Google Ads API confirmada diretamente por Rodolfo durante a execução e depois validada por API HTTP200.

## Resultado publicado
- Contas cadastradas pela UI com metadados reais da MCC: Gamingadx-US-01 / 278-030-0411 / BRL / America/New_York; Mattei 1 / 517-249-8094 / BRL / America/Sao_Paulo. IDs originais com hífens preservados para exibição; transporte usa os dez dígitos após validação do formato.
- Botão + Conta Google Ads consulta a MCC 813-701-6595 pelo worker protegido do Zeus. Inventário paginado retornou 40 contas de anúncio (não inclui gerenciadoras); dropdown pós-cadastro apresenta 38 ainda não cadastradas. Não guardar IDs de contas filhas no 1Password. Credenciais, inclusive chave SA/developer token, não saem do Zeus.
- Cadastro não cria conta no Google. Descoberta não cadastra automaticamente toda a MCC. Nenhuma campanha, orçamento ou billing foi alterado.
- As duas contas foram cadastradas sem vínculos de site e sem source_links: não foi presumida atribuição financeira. Valores originais e contas Facebook preservados. Importador/scheduler diário de gastos não foi ativado.
- Meu perfil disponível no menu da conta autenticada, com nome completo, e-mail, telefone e ID Discord. A edição própria resolve a identidade pela sessão e recusa username/role/enabled/credenciais em payloads.
- Tela Usuários agora oferece Editar inclusive para Rodolfo. Login/senha/permissões administrativas seguem protegidos. Dados do administrador usam o registro não financeiro master-owner-profile no store JSON existente, criado apenas quando ele salvar; sem novas tabelas/grants nem credencial no registro. Rotas genéricas para esse registro são bloqueadas.
- Geizian pode editar seus próprios contatos diretamente; alterações em terceiros/financeiro continuam propostas. Nicolas continua único piloto, sem novos logins reais.
- Usuários é o último item do menu. Logo completo, exatamente os pixels RGB da arte quadrada original 1024x1024, renderizado em160x160 no login e112x112 na lateral. Sem recorte, distorção, redesenho ou mudança de favicon nesta release.

## Validação real
- Logo/perfil: 41 testes Node e43 Python PASS; restore PostgreSQL isolado com self-profile nos três perfis, CSRF, IDOR, revisões vencidas, edição Rodolfo, senha existente preservada, permissões/pagamentos anteriores preservados.
- Google: 44 testes Node PASS antes do hotfix de binding; quatro testes focados PASS depois, incluindo controle negativo que reproduz a abertura automática indevida e valida o callback corrigido. Exercício PostgreSQL real com fila Google/API e Meta/API, duas contas, campos forjados ignorados, outro ator recusado, valores financeiros intactos.
- Browser público após o hotfix: duas contas realmente salvas pela UI e lidas de volta; outras contas e cash do mês idênticos; próxima descoberta MCC funcionando, zero JS. Logo, Editar Rodolfo, Meu perfil desktop/mobile, Usuários último e asset hash aprovados. Nenhuma edição de contato/senha real executada como teste.
- Publicações pequenas, backup fresco de código + dump PG, segunda cópia com SHA256 e restore isolado em ambas as fases. Apenas serviço financeiro e worker de consulta reiniciados; nenhum gateway, /etc, grant, senha/token ou planilha alterado pelo Zeus.

## Falhas resolvidas e limites
- Pré-requisito Google: HTTP403 SERVICE_DISABLED duas vezes. Rodolfo adicionou SA à MCC e ativou API no projeto mgs-core-prod (624323035542); reteste HTTP200, MCC/contas/metadata confirmados. Não confundir enablement Cloud com acesso à MCC.
- Testes Node iniciais excederam limite externo de180s; novo limite540s, suíte concluiu em aproximadamente193s. Verificado que processo anterior terminou. Tentativa de inspeção com psutil falhou por dependência ausente; diagnóstico feito com stdlib, sem instalar pacote.
- Patch inicial do cache do logo procurou string sem versão; corrigido pelo HTML real.
- Primeiro browser Google detectou modal abrindo durante render por onclick=newGoogleAccountEditor(); zero contas escritas nessa tentativa, comprovado em consulta DB. Correção de callback publicada com backup/hashes, negativo de regressão e novo browser completo PASS.
- Captura mobile inicial foi feita após reduzir viewport desktop com drawer aberto. Refeita com menu fechado por controle real antes da redução; perfil completo confirmado visualmente.

## Artefatos e recuperação
- Local: apps/finance-system/private/google-square-1546702931384991834/ e private/google-accounts-1546702931384991834/.
- Remoto: /home/zeus/mgs-finance-backups/1546703031033405501 e /home/zeus/mgs-finance-backups/1546702931384991834.
- Restore: mgs_finance_square_1546703031033405501 e mgs_finance_google_1546702931384991834; stages homônimos em /var/tmp/mgs-finance-square-* e /var/tmp/mgs-finance-google-*.
- Worker anterior guardado em private/google-square-1546702931384991834/meta-lookup-worker-before.py. Hotfix tem backup app-before-click-fix.js e hashes em click-hotfix.json.
- Backups/stages retidos, nenhuma exclusão autorizada por inferência. Rollback de código não autoriza sobrescrever banco com os novos cadastros.

## Fontes externas
- https://developers.google.com/google-ads/api/docs/oauth/service-accounts
- https://developers.google.com/google-ads/api/docs/account-management/get-account-hierarchy
- https://developers.google.com/google-ads/api/docs/release-notes
