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

## Migrar uma operação de User token para BISU

1. Leia o contrato e todas as referências atuais de credencial antes de tocar no cutover. Preserve o User token vigente como rollback; nunca o sobrescreva com o candidato.
2. Com o token vigente, faça um único batch account-scoped para confirmar `business`/ownership das contas, Página e Pixel exatos. Ownership comum apenas prova que a migração é possível; não prova que o BISU recebeu esses ativos.
3. Sonde o BISU candidato com `/me` e GETs diretos dos mesmos IDs. Trate `403`/`400` como ausência de delegação e mantenha as referências produtivas intactas; não tente corrigir trocando o token primeiro.
4. Autorize somente os ativos mínimos da operação. Prefira um item de cofre separado por operação quando isso reduzir blast radius e permitir rollback independente, mesmo que a identidade system-user e o app sejam compartilhados.
5. Armazene o novo token diretamente no cofre e valide `/debug_token`, App ID, `client_business_id`, scopes, conta, Página, Pixel, timezone, moeda, saúde e headers de uso. Não persista token ou Page token em contrato, state ou audit.
6. Execute smokes read-only e dry-run; só então atualize referências canônicas, caches e allowlists de forma atômica. Um canário `PAUSED` é uma autorização de write separada e não fica implícito na migração da credencial.
7. Reporte o benefício correto: BISU melhora identidade server-to-server, estabilidade e independência de reautenticação humana. Se app, conta e `ads_api_access_tier` permanecerem iguais, não alegue aumento do teto principal da Marketing API; User e BISU continuam sujeitos aos limites account/app/BUC e diferem principalmente na camada de identidade e em certos limites Graph/Pages.

## Comparar apps e decidir cutover

Ao comparar um app novo com o app operacional, siga esta ordem:

1. Identifique nome e App ID de ambos. Se a captura não mostrar a identidade, trate o app como não identificado e não associe um ID por semelhança.
2. Separe quatro evidências que não são equivalentes:
   - **App Dashboard:** `Approved`/`Renewed` prova o nível concedido à permissão ou feature no app.
   - **`/debug_token`:** prova validade, App ID e scopes concedidos ao token; não prova Advanced Access do app para usuários externos.
   - **Header vivo:** `ads_api_access_tier=standard_access` em resposta da conta prova o tier operacional da Marketing API; aprovação visual sem esse readback ainda não fecha o runtime.
   - **Readback do ativo:** conta, Page, Instagram e pixel acessíveis provam somente a delegação efetiva daquele token sobre aqueles ativos.
3. Normalize os nomes e calcule interseção, itens exclusivos e contagens por código, não de cabeça. Exclua ou rotule separadamente features como `Business Asset User Profile Access` e scopes automáticos como `public_profile`, para não comparar categorias diferentes como se fossem permissões OAuth idênticas.
4. Classifique cada item exclusivo pelo fluxo que ele habilita. Não atribua ganho de Campaign Ops a permissões de outro produto:
   - `instagram_content_publish`: publicação orgânica;
   - `instagram_manage_comments`: comentários e menções;
   - `instagram_manage_messages`: Direct inbox/CRM;
   - `instagram_manage_insights`: métricas orgânicas da conta e conteúdo;
   - `pages_user_timezone`: personalização e horário de mensagens no Messenger.
   Essas permissões não melhoram criação, entrega, revisão, ROI ou Ads Insights de campanhas apenas por estarem aprovadas.
5. Compare tier e quota separadamente das permissões. Se ambos os apps retornarem `standard_access`, substituir um pelo outro não aumenta o teto principal da Marketing API. Uma divisão real de consumidores entre apps pode isolar parte do uso por app+conta, mas só declare ganho depois de tokens distintos e headers vivos mostrarem a separação; mover todos os consumidores apenas transfere a mesma carga.
6. Antes de recomendar migração global, compare o benefício específico com o custo do cutover. Tokens são vinculados ao app e não são reaproveitados: emitir/autorizar novos tokens, reconciliar ativos, atualizar referências 1Password/configurações/cache/allowlists, executar smokes read-only/dry-run e validar conta, Page, Instagram, pixel e header vivo. Objetos de campanha existentes permanecem, mas a identidade da aplicação que os opera muda.
7. Prefira coexistência controlada: mantenha o app validado em produção, valide o novo em uma conta não crítica e faça canário `PAUSED` somente com autorização de write própria. Use o novo como contingência ou app dedicado a Instagram/Messenger quando esse for o benefício real; não faça cutover apenas porque a lista de permissões é maior.

Reporte a conclusão primeiro, depois um bloco alinhado com tier, validação viva, itens comuns e exclusivos. Declare explicitamente quando App ID, token ou header do novo app não estiverem disponíveis.

## Fonte oficial

- Meta, Facebook Login for Business: https://developers.facebook.com/docs/facebook-login/facebook-login-for-business/

A documentação oficial define User token para ações em tempo real baseadas na entrada do usuário e Business Integration System User token para automação contínua, server-to-server e Ads Insights automatizado.
