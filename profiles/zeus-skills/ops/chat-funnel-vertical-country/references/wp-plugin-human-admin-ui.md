# WordPress plugin human admin UI — MGS Chat Funnels

Sessão de origem: Rodolfo revisou o admin do plugin `MGS Chat Funnels` no OpenZed e rejeitou dois padrões técnicos demais: editor JSON bruto e textarea de ofertas com separador `|`.

## Correção operacional

Para chats/funnels usados por gestor de tráfego, a interface do WordPress precisa ser orientada a campos humanos, não a arquivo/config técnica.

O JSON pode existir como modo avançado, mas não deve ser a interface principal.

## Padrão aprovado para admin

A tela principal deve permitir:

- criar chat novo;
- duplicar chat existente;
- ao duplicar, escolher novo ID/nome e nova pasta/URL, ex. `/chat/emp/br2`;
- excluir chat;
- ver e abrir a URL pública do chat;
- editar campos do chat sem conhecer JSON;
- ver relatório/inventário operacional de chats, rotas, modo e número de ofertas.

## Campos humanos mínimos

### Identidade e URL

- ID do chat: `EMP-BR-02`, `CAR-BR-01`.
- Nome interno/título.
- URL/pasta pública: `/chat/emp/br2`.
- Marca/site.
- Vertical.
- País.
- Idioma.
- Modelo de oferta: `cards` ou `sequential`.

### Monetização e rastreamento

- Rewarded/interstitial ativo.
- Preservar UTMs.
- Quantidade de auctions.
- Timeout do anúncio.
- Tags.

### Persona

- Nomes possíveis.
- Nomes femininos, quando a lógica de foto depende disso.
- Cargo no header.
- Status.

### Gate inicial

- Gate ativo.
- Perguntas do gate.
- Texto de loading.
- Tempo de loading.
- Ícone final.
- Título final.
- Subtítulo final.
- CTA.
- Nota de rodapé.

### Conversa

- Mensagens de abertura.
- Botões iniciais.
- Perguntas do chat.
- Mensagens antes das ofertas.
- Headline das ofertas.

## Ofertas finais — pitfall crítico

Não usar textarea do tipo:

```text
Nome | URL | Botão aceitar | Botão recusar | mensagem 1; mensagem 2
```

Rodolfo rejeitou explicitamente esse padrão: ainda é formato técnico, ruim para humano.

Use blocos/repeaters por oferta.

### Modo sequential

Cada oferta deve ter campos separados:

- Nome da oferta.
- URL de destino.
- Botão aceitar.
- Botão recusar / próxima oferta.
- Mensagens da oferta, uma por linha.

### Modo cards

Cada oferta deve ter campos separados:

- Nome da oferta.
- URL de destino.
- Subtítulo / benefício.
- Logo.

Deixar alguns blocos vazios extras para adicionar novas ofertas. Ao salvar, ignorar blocos sem nome ou sem URL.

## JSON bruto

Manter JSON bruto apenas em `details` / seção avançada, para debug e manutenção. Não deve ser o caminho principal de edição.

## Validação recomendada após alterar admin

- WP Plugin Editor ou deploy salva sem fatal error.
- Plugins page mostra a versão nova.
- Admin page abre HTTP 200.
- Campos humanos principais aparecem.
- O texto técnico com `Nome | URL | ...` não aparece mais como instrução principal.
- Save humano de um chat existente retorna sucesso.
- Duplicação cria config e rota pública temporária.
- Rota duplicada abre HTTP 200.
- Exclusão do teste remove o chat.
- Relatórios abrem HTTP 200.
- Rotas canônicas existentes continuam HTTP 200.
- REPORT-INFRA vai para o canal correto, não para a thread de trabalho.
