# Meta Facebook Login for Business — seleção de token

## Regra de decisão

Antes da escolha, ler o contrato operacional e o checkpoint canônico. A automação contínua, sozinha, não autoriza trocar a identidade planejada do token.

- Se a operação registra `one_user_access_token_per_manager_profile=true` ou exige um token separado por perfil pessoal anunciante, usar **User access token**. O fato de o uso posterior ser automatizado não converte essa arquitetura em system-user.
- Use **Business Integration System User access token** quando a unidade de identidade pretendida for o Business Portfolio cliente e seus ativos explicitamente delegados, com ações programáticas/automatizadas server-to-server ou necessidade de evitar reautenticação futura.
- Use **User access token** também quando as ações ocorrerem em tempo real a partir da interação do usuário, quando a API exigir permissão administrativa do usuário ou quando os ativos só estiverem acessíveis pelo perfil pessoal e não puderem ser delegados por um Business Portfolio cliente.

Trocar User por system-user em uma iniciativa existente é mudança de arquitetura, não otimização local; exige confirmação explícita do dono e atualização/supersessão do contrato canônico antes de continuar.
## Pré-requisitos do system-user

Antes de concluir a configuração:

1. Confirmar que o app está associado a um Business Portfolio sob controle integral da MGS/Tech Provider.
2. Confirmar que esse portfólio é separado do Business Portfolio cliente que delegará os ativos.
3. Confirmar que quem autoriza tem controle total do Business Portfolio cliente.
4. Validar no wizard que as contas de anúncio/Páginas/Instagram necessárias aparecem para delegação.
5. Não clicar em **Create** até reconciliar os ativos e permissões mínimos.

System-user muda a unidade de identidade: é um token por Business Portfolio cliente/configuração delegada, não um token por perfil pessoal anunciante. Se a operação foi desenhada como “um token por perfil”, reavaliar a arquitetura antes da escolha irreversível.

## Páginas próprias versus compartilhadas

- Não exija que uma Página externa vire propriedade do Business Portfolio cliente apenas para usar um Business Integration System User token. Ativos próprios **ou compartilhados** podem ser usados, mas o app recebe somente os ativos explicitamente designados na autorização.
- Para Página de anunciante/cliente, prefira **Request shared access**, confirme a aprovação e conceda apenas as tarefas necessárias. Use **Add an existing Facebook Page** somente quando a transferência/centralização de propriedade for realmente pretendida.
- Preserve propriedade na origem para reduzir acoplamento administrativo e facilitar revogação, mas não prometa isolamento absoluto: restrições de Página ainda podem afetar anúncios, contas e outros ativos relacionados segundo a aplicação de políticas da Meta.
- Antes do login, confirme que Página e conta de anúncios estão visíveis no mesmo Business Portfolio cliente e que o autorizador tem controle total desse portfólio.

## Seleção de tipos de ativos

Selecionar um tipo o disponibiliza no fluxo de autorização. A caixa **Asset Required** é que obriga o usuário a conceder pelo menos um ativo daquele tipo no login. Aplique privilégio mínimo: não exponha tipos sem uso; use tipo opcional ou configuração separada quando a necessidade não for universal.

- **Instagram accounts:** não selecionar apenas porque haverá posicionamento no Instagram. Quando o anúncio usa a própria Página como identidade/voz no Instagram e não há conta profissional conectada para administrar, `Pages` cobre a identidade necessária; selecione Instagram somente para uma conta profissional real que a integração precise acessar.
- **Pixels:** quando apenas uma operação usa um pixel compartilhado, pode ser selecionado com **Asset Required desmarcado** em uma configuração geral; durante a autorização relevante, conceda explicitamente o pixel. Para campanhas que criam ou alteram ad sets com `pixel_id`, validar a permissão real sobre o pixel e seu compartilhamento com cada ad account. Uma configuração dedicada continua preferível quando for necessário isolar acesso.
- **Catalogs:** selecionar somente para fluxos de catálogo/dynamic ads.

## Permissões para configuração Ares Ads

Para uma configuração dedicada a Campaign Ops/Marketing API, comece pelo conjunto mínimo:

- `ads_management`
- `ads_read`
- `business_management`
- `pages_manage_ads`
- `pages_read_engagement`
- `pages_show_list`

`ads_read` cobre Ads Insights; não adicionar `read_insights` apenas para relatórios de anúncios. Não misturar permissões de bot, Messenger, publicação orgânica, moderação, lead forms ou Instagram em uma configuração de Ads quando esses fluxos não fazem parte do escopo. Remover esses itens da configuração não revoga permissões globais do app nem altera outras configurações existentes.

O conjunto mínimo é recomendação de governança, não bloqueio técnico. Se todas as permissões selecionadas já tiverem Advanced Access vigente e o dono autorizado decidir conscientemente criar uma configuração ampla para múltiplos fluxos do mesmo app, manter o conjunto ampliado não inicia nova revisão nem executa ações por si só. Registrar que o trade-off aceito é maior escopo no consentimento/token e maior superfície de impacto; não alegar App Review adicional sem evidência do dashboard.

Antes de criar, reconciliar o contador exibido pelo seletor com a lista visível; dependências automáticas podem acrescentar permissões. Nunca clicar em **Create** com item não identificado.

## Fonte oficial

- Meta, Facebook Login for Business: https://developers.facebook.com/docs/facebook-login/facebook-login-for-business/

A documentação oficial define User token para ações em tempo real baseadas na entrada do usuário e Business Integration System User token para automação contínua, server-to-server e Ads Insights automatizado.
