# Projeção e sincronização de threads

## Escopo

- `family`: valida e projeta em todos os consumidores ativos.
- `operation`: valida e projeta somente no consumidor selecionado.

Toda mudança projeta a rota afetada e `rules`. Se a rota alterada já for `rules`, existe uma única projeção.

## Ordem

1. readback da fonte canônica atual;
2. persistência com supersessão explícita;
3. validação do contrato e do consumer registry;
4. sincronização dos prompts/configs;
5. pre-read da mensagem de projeção;
6. PATCH da mensagem Ares conhecida ou POST se ainda não existir;
7. GET e comparação exata do conteúdo;
8. persistência de message ID, digest e audit.

## Preservação

O sincronizador nunca apaga mensagens. Só pode editar uma mensagem cujo ID esteja persistido e cujo autor seja o bot Ares. Mensagens humanas, eventos de sistema e conteúdo histórico permanecem intactos. Limpeza é uma operação separada e exige autorização específica.

## Texto multilinha no CLI atual

Prompts com bullets podem ser interpretados como listas/mappings em folhas dinâmicas sem schema textual. Não considerar `config set` com exit0 como prova: JSON entre aspas pode ser armazenado literalmente, com quotes e escapes, em vez do texto real. O sincronizador deve usar `config get --json` para ler o mapping tipado de prompts, mesclar somente a thread autorizada, aplicar o mapping pelo `hermes -p ares config set discord.channel_prompts` e reler o mapping completo. Preservar todos os demais valores, serializar a operação sob lock e falhar fechado se ultrapassar o limite seguro de argumento; não editar YAML ativo à mão nem reiniciar gateway. Comparar texto decodificado com fonte e versão local. Testar bullets, quotes, outros prompts intactos, payload excedido e drift no readback.

## Sequência e identidade na criação

Quando o contrato separar a sequência global de campanhas do identificador da Page, consultar somente o conjunto exato de contas permitido e paginar suas histórias por completo. Reservar números sob lock compartilhado, com idempotência por request/conta e sem consumi-los em exemplos ou testes. A mudança de conta não reinicia um contador global; o contador local da Page segue a regra da operação. Resolver o pg inteiro na SB, exigir uma única combinação de FB_PAGE_ID/nome e conferir a identidade Meta antes de selar. Nome de campanha, Page do creative/adset e utm_campaign devem concordar. Divergência ou colisão exige bloqueio/reconciliação, não credencial alternativa, renomeação da Page ou alteração silenciosa do tracking. Preservar manifests anteriores à regra e revalidar colisões antes do execute.

## Drift

Qualquer diferença entre família, contrato da operação, registry, prompt, config ativo ou projeção Discord deixa a sincronização incompleta. Não declarar atualização antes de todos os readbacks aplicáveis fecharem.
