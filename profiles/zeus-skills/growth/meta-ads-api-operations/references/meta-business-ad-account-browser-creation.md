# Meta Business — criação de conta de anúncios via sessão autenticada

Use quando Rodolfo pedir para reproduzir no Business Settings a criação de uma conta de anúncios usando um usuário do Facebook que já está logado.

## Identidade e rota

- Respeite a identidade pedida. Se o pedido diz “com o usuário logado”, não substitua silenciosamente por outro user token/API token, mesmo que ele consiga ler o Business.
- Confirme por readback o nome do perfil Facebook e o Business Portfolio antes de qualquer write.
- A rota observada no Business Settings usa `https://business.facebook.com/latest/settings/ad_accounts?business_id=<BUSINESS_ID>` (`ad_accounts` com underscore). Uma rota aproximada pode redirecionar para outro Business e criar risco de alvo errado.

## Reautenticação segura

1. Abra o Chromium headed com o perfil persistente e a rota residencial canônica; mantenha lock exclusivo do profile.
2. Exponha noVNC somente em localhost e peça a Rodolfo para acessar por túnel SSH local.
3. Rodolfo completa passkey/2FA diretamente na tela remota. Nunca peça senha ou código no Discord e nunca opere o desafio por ele.
4. Peça para manter a janela e o túnel abertos até o readback final.
5. Se o browser Playwright já estiver rodando sem CDP acessível, abra a URL alvo no mesmo processo via Chromium ProcessSingleton: invoque o mesmo executável com o mesmo `--user-data-dir` e a URL. O marcador esperado é `Opening in existing browser session.`; depois confirme a aba por screenshot/readback.

## Pré-write obrigatório

- Confirmar novamente Business Portfolio, seção `Ad accounts` e lista atual.
- Verificar se já existe conta com o nome pretendido; nomes repetidos podem ser permitidos, mas não presumir que o item visível foi recém-criado.
- Abrir `Add` → `Create a new ad account` e ler qualquer estado desabilitado/tooltip antes de preencher.
- Se a Meta mostrar `You've reached the maximum number of ad accounts allowed for a new business portfolio`, parar: nenhuma conta foi criada. Informar que a liberação depende de histórico/tempo de conformidade; não tentar contornar via outro Business ou identidade.

## Write e validação

Quando a criação estiver liberada e o pedido tiver parâmetros explícitos:

1. Preencher nome, timezone e moeda exatamente.
2. Selecionar quem usará a conta conforme o escopo autorizado.
3. Criar uma única conta.
4. Validar na lista o nome, o novo Ad Account ID e `Owned by` do Business correto.
5. Diferenciar claramente conta preexistente de conta criada no turno.
6. Encerrar o browser limpo, liberar o lock e validar que noVNC/VNC e processos do profile foram fechados.

## Caso observado em 2026-08-06

- A reautenticação do perfil foi concluída manualmente por Rodolfo em uma nova aba, mantendo a Ad Library aberta.
- O alvo correto foi confirmado por readback antes do write.
- Havia uma conta `001` preexistente.
- `Create a new ad account` ficou bloqueado pelo limite de portfólio novo; nenhuma conta adicional foi criada.
- A sessão foi encerrada e as portas localhost/noVNC e os processos do profile foram verificados como fechados.
