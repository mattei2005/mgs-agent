# Dashboard: sessão persistente e atualização automática segura

## Autoridade e supersessão

- Origem: thread `1555563097375383643`.
- Rodolfo `1555568204607135796`: remover logout por inatividade3h/duração8h; inicialmente sugeriu tarja com atualização voluntária.
- Rodolfo `1555569927891718275`: preferiu atualização automática com retorno ao ponto onde estava.
- Confirmação final `1555570216912560151`: aplicar login persistente para todos e atualização automática protegida. **Este desenho supersede a tarja manual anterior.**
- Estado: **publicado e validado**, release `persistent-session-1555570216912560151`. O registro anterior de confirmação pendente é histórico. A política idle3h/absoluta8h de `1551947602562392085` foi supersedida exclusivamente para sessões; demais regras financeiras daquele release permanecem.

## Comportamento ativo

### Sessão

- Novos logins usam sessão sem expiração temporal no servidor (`expires_at='infinity'`). Não há logout por3h de inatividade nem8h desde o login.
- Cookie `__Host-mgs_finance`, HttpOnly/Secure/SameSite=Strict, persistente por400dias e renovado em cada requisição autenticada. O limite do navegador continua existindo; não prometer permanência literal após limpeza de cookies, uso anônimo ou imposição do cliente.
- Sessão anterior finita só é convertida se ainda estiver válida pela política anterior. Sessões expiradas/revogadas não são ressuscitadas e podem exigir um último login na transição.
- Sair, Sair e esquecer este dispositivo, desativação/troca de acesso e revogação continuam encerrando o acesso; identidade é validada a cada requisição. Senha, MFA, limite de tentativas, papéis, Host/Origin e CSRF preservados.
- Trust MFA30dias continua independente: dispensa apenas TOTP em um novo login com senha válida, nunca cria login automaticamente.
- Risco aceito: quem acessa um navegador já autenticado pode acessar os dados financeiros até saída/revogação/remoção da sessão.

### Atualização

- Detecta alterações por consulta autenticada a cada30segundos enquanto a aba está visível e ao voltar à aba/janela.
- Hash da versão deriva dos arquivos de código efetivamente publicados no início do processo; não depende de lembrar de mudar um número manual de versão.
- Marcador de dados deriva da auditoria, excluindo eventos LOGIN/MFA/LOGOUT; só devolve hashes opacos, sem valores financeiros, identidades ou conteúdo de auditoria.
- Números/cadastros: nova leitura dos dados, sem recarregar o documento e sem POST financeiro.
- Estrutura/código: recarga completa com restauração por aba de tela, competência, filtros, seleção de beneficiário, paginação, detalhes abertos e rolagem quando os elementos ainda existem. Estado transitório não contém senha, token ou campos de edição.
- Editor aberto, formulário próprio alterado, requisição em andamento ou operação explícita de atualização bloqueiam a recarga. Tarja: “Atualização disponível. Será aplicada ao concluir sua edição ou operação.” Ao concluir/cancelar, a atualização é aplicada automaticamente e a tarja some após sucesso.
- Falha de transporte não vira confirmação de atualização: dados anteriores e estado pendente são preservados, com nova tentativa limitada. Sessão revogada continua indo ao login.
- O antigo refresh principal de5min foi substituído pelo mecanismo compartilhado. Dashboard, Operações/Gestores/Pagamentos, Histórico e Conferência usam o mesmo controle.
- A primeira aba aberta com o código anterior precisa de uma atualização manual para carregar este novo mecanismo; ele não pode se instalar retroativamente em JavaScript já carregado.
- Proteções de revisão/conflito de gravação permanecem; números desatualizados não autorizam sobrescrita concorrente.

## Evidência e limites

- Relatório: `reports/finance-persistent-session-1555570216912560151.md`.
- Candidato/testes/manifesto/readback: `apps/finance-system/private/persistent-session-1555570216912560151/`.
- Gates completos:240Node +188Python =428testes, zero skips/falhas.
- Stage HTTPS real isolado:17checks desktop1440/mobile390, incluindo recarga estrutural real, revisão de dados, formulário sem salvar, requisição retida, falha de leitura e recuperação; zero erro JavaScript/POST financeiro.
- Produção:28checks desktop/mobile, sessão persistente confirmada no PostgreSQL, login real com senha+MFA, cookies seguros, reabertura de contexto, vistas administrativas dos cinco gestores, health e logout/revogação da sessão de teste. Não declarar esses previews como login humano dos gestores; seus papéis/MFA são cobertos pelos gates isolados, sem contornar seus autenticadores.
- Cenários, revisões, ledger e auditoria financeira idênticos antes/depois do cutover. Nenhuma alteração de números, fontes, Google Sheets, salários, comissões ou pagamentos.
- Não há garantia de restauração de uma tela/campo removido por uma futura versão incompatível; o destino deve recuar para uma tela válida sem reexecutar gravações.

## Backup e rollback

- Dump PostgreSQL validado por catálogo: `/home/zeus/mgs-finance-backups/persistent-session-1555570216912560151/finance-before.dump`.
- Backups exatos de código e journal: `apps/finance-system/private/releases/persistent-session-1555570216912560151/`.
- Rollback da sessão exige considerar as sessões persistentes criadas ou convertidas: restaurar só o código antigo reaplica idle3h, mas não recria automaticamente o limite absoluto8h de registros com infinity. Caso o rollback seja necessário, revisar e autorizar a conversão limitada de `expires_at='infinity'` para `created_at + interval '8 hours'`, preservando revogações e sem restaurar todo o banco financeiro. Não executar essa conversão preventivamente.
