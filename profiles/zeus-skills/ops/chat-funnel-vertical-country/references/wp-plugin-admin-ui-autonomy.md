# WordPress plugin admin UI — autonomia operacional

Sessão de origem: Rodolfo validou que o plugin `MGS Chat Funnels` estava ativo, mas corrigiu o escopo: não basta aparecer em Installed Plugins; precisa ter menu próprio no WP Admin para edição autônoma, igual ao plugin de quiz.

## Lição operacional

Para plugin de chat/funnel MGS em produção, o MVP aceitável precisa incluir **interface administrativa**. O usuário precisa conseguir alterar textos, perguntas, ofertas, links, rotas e modo do funil sem depender de edição de arquivo, ZIP ou Zeus.

## Requisito mínimo de interface

- Menu no admin, ex.: `MGS Chats`.
- Página em `wp-admin/admin.php?page=mgs-chat-funnels` ou equivalente.
- Lista dos chats/configs existentes.
- Ação para criar novo chat.
- Editor de configuração com validação de JSON ou formulário estruturado.
- Botão salvar com nonce/capability check (`manage_options`).
- Ação para remover chat.
- Exibir rota pública e shortcode de cada chat.
- Salvar em arquivos `configs/*.json` ou store equivalente, sem editar PHP.

## Validação real esperada

Antes de reportar conclusão:

```text
- Menu aparece no WP Admin.
- Página admin abre HTTP 200 autenticada.
- Editor carrega configs existentes.
- Save no-op funciona e retorna notice de sucesso.
- Rota pública de cada chat continua HTTP 200.
- Shortcode/rota continuam renderizando o frontend.
- REPORT-INFRA vai para o canal correto, não para a thread de trabalho.
```

## Pitfall

Installed Plugins mostrando `MGS Chat Funnels` ativo **não prova autonomia**. Sem menu/admin UI, Rodolfo ainda depende de Zeus para qualquer ajuste — isso viola o objetivo operacional do plugin configurável.
