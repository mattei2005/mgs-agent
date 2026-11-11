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

## Estender naming a uma modalidade de duplicação

1. Identificar o recorte autorizado: contas, intenção de duplicação, deltas de Page/mídia/copy, sequência global, contador da Page de destino e tratamento do sufixo de duplicação. Registrar a exceção na política canônica e apontá-la no contrato da operação com supersessão parcial explícita; preservar histórico e modalidades não abrangidas.
2. Confrontar a regra com o contrato v3 e a conta exata em `config.accounts`: conferir `supported_modes`, flags de write, regex/policy de naming e overrides por modo. Não presumir que um campo descritivo novo integra o executor. Classificar separadamente **regra aprovada**, **contexto sincronizado** e **execução compatível**; comunicar qualquer integração pendente antes de apresentar a mudança como utilizável em produção.
3. Preparar o nome por consulta read-only: resolver o token pg inteiro na linha Messenger do publisher autorizado, consultar somente os históricos permitidos e o ledger e calcular a prévia pelo helper canônico. Usar o contador da Page alvo quando essa for a regra aprovada; não copiar automaticamente o CXX ou prefixo da fonte. Não reservar número nem mídia para responder a um exemplo.
4. Distinguir nome confirmado no cadastro SB de identidade Meta diretamente validada. Falta de provenance scoped não autoriza bypass do guard, token alternativo ou cadastro artificial; uma prévia pode indicar sua fonte limitada, mas não satisfaz o gate de Page da publicação.
5. Sincronizar a rota afetada e Regras pelo sincronizador canônico. Comparar fonte, versão local e contexto ativo; verificar por GET cada projeção e preservar os demais prompts/configurações. Não ampliar a alteração para outros consumidores nem habilitar um modo somente para fazer a prévia passar.
6. Verificar separadamente a preservação da política-base, o escopo da exceção, os contadores globais/locais, a ausência de nova alocação no preview e a aceitação do nome pelo modo aplicável. Testes do formatter ou da criação do zero não comprovam suporte de clone; registrar essa cobertura como pendente quando o modo ainda não estiver integrado. Mostrar primeiro o nome literal, seguido apenas das ressalvas necessárias.

## Renomear uma campanha existente com sequência compartilhada

1. Recuperar o ID da campanha entregue pelo request/checkpoint e aplicar a admissão da conta antes da alteração. Se houver modelo e cópia com nomes parecidos, usar o vínculo da entrega, não o primeiro resultado pelo nome. Um writer de outro pedido não deve ser liberado por inferência.
2. Fazer GET da campanha com `id,account_id,name,status,effective_status,daily_budget` e ler os conjuntos/anúncios necessários para congelar IDs, nomes, início e tracking. Confirmar que Page, pg e `utm_campaign` correspondem ao nome literal solicitado.
3. Ler as histórias completas das contas exatas do grupo e o ledger de números. Reservar o número solicitado sob lock, usando uma identidade idempotente para o rename. Se houver colisão ou a reserva produzir outro número, parar antes do write: não substituir silenciosamente o nome aprovado pelo próximo livre. Exemplo ou preview não faz reserva; rename real faz.
4. Persistir intenção e pre-read; chamar o helper Meta canônico `graph_post_once(campaign_id, token, {"name": nome_literal})`. Não enviar status, budget, copy ou tracking junto, e não chamar criação/clone do Engine. Após resposta incerta, reler o mesmo ID antes de qualquer repetição.
5. Fazer GET do alvo e exigir o nome exato. Comparar os demais campos congelados, normalizando somente ordem dos edges e cursores de paginação. Guardar a confirmação do rename e preservar os manifests/audits originais como evidência histórica, sem modificar seus selos.
6. Confirmar no ledger o número, nome, conta e o mesmo campaign ID; atualizar o apontador de nome atual no request e o checkpoint. Reconciliar o próximo número considerando a campanha renomeada e as reservas compartilhadas, sem contar o mesmo número duas vezes nem reiniciar a sequência por conta.
7. Refletir a alteração na projeção da rota e em Regras pelo sincronizador canônico, com GET de cada mensagem. A exceção explícita de rename atual não vira autorização para renomear o restante do histórico.

Aceite: mesmo campaign ID antes/depois, payload exclusivamente `name`, nome literal confirmado, budget/status/hierarquia/tracking preservados, número comprometido no ledger e continuidade/projeções coerentes. Na resposta ao operador, mostrar apenas o novo nome e a confirmação operacional útil.

## Cobertura de todas as threads solicitadas

- Auditar cada rota funcional pelo binding canônico exato, não apenas o consumidor ativo ou a política central. Uma regra pode estar correta globalmente e faltar no prompt local das demais contas. Registrar por thread: fonte, versão, contexto ativo e mensagem de referência relida; agregar e deduplicar os resultados em código contra a quantidade pedida.
- Se a regra já autorizada abrange essas rotas, completar somente a projeção faltante. Thread de conta candidata pode receber contexto de escopo/naming sem ser promovida a consumidor ativo: preservar contratos, credenciais, readiness e flags. Não herdar a conta do canal pai como fallback quando a thread tem conta própria registrada.
- Para chave de prompt inexistente, usar adição tipada no sincronizador, comparar o YAML versionado inteiro com o estado esperado e reler o mapping ativo preservando outros valores. Não sobrescrever o conjunto com uma entrada isolada nem editar YAML ativo à mão.
- Antes de publicar em thread arquivada, ler título, parent, archived e locked. Reabrir somente se necessário para a projeção autorizada, publicar e conferir a mensagem; restaurar o estado archived original no finally, preservando título, parent e locked. Não criar outra thread, desbloquear permissões ou apagar histórico.
- Uma confirmação de padrão salvo não comprova que a conta está pronta para publicar campanhas. Distinguir cobertura de contexto da operação/credencial/readiness, sem cobrar novamente aprovação já concedida para a regra.

## Drift

Qualquer diferença entre família, contrato da operação, registry, prompt, config ativo ou projeção Discord deixa a sincronização incompleta. Não declarar atualização antes de todos os readbacks aplicáveis fecharem.
