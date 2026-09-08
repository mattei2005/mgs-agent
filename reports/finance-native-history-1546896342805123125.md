# Histórico nos menus nativos — publicado e validado

Autoridade: Rodolfo1546894693135028234 e correção1546896342805123125, thread1545426987756298340. Supersede somente o desenho de menu/tela separada do release1546884731436671056. Importação imutável, isolamento, valores e fechamento julho→agosto preservados.

## Resultado
- Janeiro–julho ficam nos mesmos menus da dash de agosto. Seletor não abre Histórico separado. Mês acompanha navegação. Cartões, receita, mídia, despesas, parâmetros, domínios/diários e pagamentos continuam no shell existente.
- Site→diário inclui os blocos inferiores e os fechamentos por site. Total fechado/ROI vem da célula original, não de regras de agosto. Datas/valores vazios não viram zero.
- Pagamentos mostra o saldo remanescente no menu correto, com todos os ajustes/pagamentos numéricos e as datas efetivamente registradas. Julho alimenta agosto internamente, e agosto→setembro foi conferido. Não foram criados pagamentos, transferências, ajustes ou quitações novos.
- Visões individuais permanecem isoladas. Ícaro usa `george` apenas como origem técnica legada; nome público Ícaro. Janeiro/fevereiro salário-only. Remuneração histórica não usa a política de agosto.
- Menu Histórico fechado removido. URL legada `/history` encaminha à tela nativa correspondente, preservando autorização. Arquivos antigos retidos como rollback, sem exclusão.

## Evidência real
Diretório: `apps/finance-system/private/history-ui-1546894693135028234/`.

- `unit-readback.json`:64testes,64PASS,0falhas.
- `coverage-readback.json`:40documentos,504blocos,858headersGross sem omissão e194814valores numéricos diários conferidos contra as células. Nenhum snapshot modificado pela projeção.
- `stage-pg.json`:40payloads/377906células exatas;217negações;85meses atuais de gestor;cenários preservados.
- `production-readback.json`:6logins reais (Rodolfo,Nicolas,Joe,Isliago,Kelly,Ícaro);42perfil-meses (todos7meses por6perfis);42telas Pagamentos;84viewports390/1440;16negações;0errosJS;504blocos;377906células idênticas. AlternânciaJulho↔Agosto passou.2entradas legadas302 validadas nos perfis remanescentes.
- A primeira rodada publicada terminou após4perfis porque stage+produção consumiram o limite10logins/IP/15min. `auth_limits` confirmou11tentativas e janela restante. Não houve alteração/bypass do limite; a validação retomou somenteKelly/Ícaro após expiração e consolidou42perfil-meses. Não é uma falha ainda pendente.
- `published.json` e `deploy-readback.json`:9arquivos com hashes locais/remotos iguais;serviço financeiro/socket/PostgreSQL ativos. Dados de source_cells,scenarios,finance_ledger,finance_users e finance_history intactos no cutover. Grants da aplicação para histórico:t/f/f/f(SELECT/INSERT/UPDATE/DELETE).

## Backups e rollback
Cópias local e remota iguais porSHA256; restauraçãoPGisolada conferida antes do cutover.
- Remoto:`/home/zeus/mgs-finance-backups/1546896342805123125`.
- Local:diretório de evidência acima, `code-before.tar.gz` e `finance-before.dump`.
- Stage:`/var/tmp/mgs-finance-history-ui-1546896342805123125`.
- Banco isolado:`mgs_finance_history_ui_1546896342805123125`.
- Rollback pelo código anterior; nunca sobrescrever novas escritas financeiras restaurando todo o banco. Backups/stage/artefatos antigos retidos, sem exclusão autorizada.

## Ressalvas preservadas
- OrigemMarço fecha−67.10478401868022;Abril abre0.7264772738271859. Diferença sinalizada, não ajustada.
- NicolasJan/Fev mantém referências anteriormente autorizadas como indisponíveis.
- Layouts antigos sem consolidado por país/gestor mostram ausência e detalhes originais; não foi inventado consolidado moderno.
- Cadastro de contas de anúncio históricas não consta do snapshot; vínculos atuais não são projetados no passado.
- Remuneração sem data/valor de quitação não é classificada como paga nem como dívida anterior acumulada.

## Pedido sequencial: transcrição PT
Zeus `stt.local.language=pt`, config ativo+mirror. Diagnóstico anterior: detector escolheu `en` em modo automático. Mesmo áudio retranscrito com sucesso em português e novo áudio seguinte recebido em português. Sem trocar modelo/provider, credenciais ou reiniciar gateway. Evidência: `work/stt-portuguese-1546894693135028234/readback.json`, com readback de ambosconfigs e resolved_language=pt. USER registra preferência por transcrição PT, uso3203/3600; nenhuma compactação necessária.

## Governança
Skill financeira0.1.32 e `references/native-closed-month-views.md`; procedimento STT emHermesoperations `references/portuguese-stt-language.md`. Direção do produto atualizada. Registroativo `FINANCE-NATIVE-HISTORY-1546896342805123125` supersede explicitamente o desenho anterior da chave `finance.closed-history-jan-jul`. Registry/checkpoint passam pelo controle canônico. Inventário/audit/REPORT-INFRA ficam em `final-readback.json` após execução do registrador.

Nenhuma escritaSheets, mutação de valores financeiros ou usuários em produção, mudança de credencial, transferência, exclusão, alteração de sistema operacional ou restartde gateway nesta correção. Houve restart delimitado do serviço financeiro/socket para publicar o código. Não se declara migração integral ou aposentadoria das planilhas.
