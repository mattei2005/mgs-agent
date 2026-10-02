# Sessão persistente e atualização voluntária da dashboard

## Pedido e estado

- Solicitante: Rodolfo Mattei, mensagem `1555568204607135796`, thread `1555563097375383643`.
- Pedido explícito: remover logout por inatividade3h e duração absoluta8h; manter login; quando houver atualização estrutural ou que impacte números, mostrar uma tarja superior com botão para atualizar quando a pessoa escolher, removendo a tarja após atualização.
- Estado: pedido registrado; implementação/publicação ainda não realizadas. Retirada da expiração das sessões de autenticação em produção encaminhada à confirmação adicional de segurança. Não confundir intenção aprovada com comportamento produtivo.
- Runtime confirmado nesta thread: `auth.mjs` do WorkingDirectory produtivo aplica idle3h, duração8h e cookie8h. Trust MFA30dias é independente.

## Desenho para confirmação

- Login persistente no mesmo navegador, sem os limites3h/8h. Sair, esquecer dispositivo, revogação de segurança e remoção dos cookies continuam válidos. Não reativar sessões já expiradas/revogadas; sessões antigas podem exigir novo login na transição.
- Cookie persistente está sujeito ao limite e à política do navegador: não prometer permanência literal após limpeza, modo anônimo ou expiração imposta pelo cliente.
- Manter senha, MFA no login aplicável, papéis, CSRF, validação de origem e revogação; não ampliar acesso de nenhum usuário.
- Tarja superior discreta com Atualizar agora, sem logout, recarga forçada, navegação automática ou descarte silencioso de edição.
- Após clique, carregar a versão/dados novos e manter tela/competência selecionada. Se existir edição não salva, avisar antes de descartá-la. Só remover a tarja depois da atualização bem-sucedida.
- Números exibidos antes da atualização podem estar desatualizados; manter bloqueio/reconciliação de gravação concorrente. A tarja não autoriza sobrescrever revisões mais novas.
- Investigar e substituir o refresh automático existente de5min apenas dentro do escopo confirmado, para não contradizer a atualização voluntária.
- Risco apresentado para confirmação: um navegador deixado autenticado mantém acesso aos dados financeiros até saída/revogação/remoção da sessão; recomenda-se uso em dispositivo pessoal protegido.

## Próxima execução

Após confirmação, preparar candidato isolado, testar sessão persistente/revogação/MFA e tarja desktop/mobile, executar gates completos e stage real, publicar pelo controlador coordenado com backup/rollback, validar hashes e navegador produtivo com zero mutações financeiras, e registrar supersessão da política antiga somente após readback.
