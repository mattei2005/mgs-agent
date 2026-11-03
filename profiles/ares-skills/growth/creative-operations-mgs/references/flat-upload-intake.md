# Entrada simples MGS — contexto explícito de pedido

## Autoridade e estado vivo

Redesenho aprovado por Rodolfo em `1566814476626563115`; preservação/reaplicação dos mesmos acessos confirmada em `1566825959645253764`, thread Zeus `1562078493498540042`. Fonte canônica: `context/drive-flat-intake-cutover.md`. Confirmar `ares_flat_intake.policy()` / `data/ares/creative-ops/30tb-archive/flat-intake-binding.json`: somente `phase=active` é fluxo implantado. Não confundir preparação ou teste técnico com uma campanha real.

## Regra de entrada

- A pessoa envia IMG/VID diretamente na mesma `UPLOAD MANUAL`, ID `1ARBvLammWUHuAclNmcriwkkgeedKryBd`. Não exigir subpasta de nicho ou gestor.
- Operação, gestor e finalidade vêm do pedido humano autorizado; o nome do arquivo, uploader, pasta antiga ou referência não substituem esse contexto.
- Congelar os IDs exatos do lote informado. Não absorver imagens vizinhas, inferir o gestor dos pendentes ou reaproveitar um comando antigo para fontes novas. Se o lote/contexto for ambíguo, perguntar somente a informação que falta.
- `common` destina à organização `01_READY`, preservando os demais gates de elegibilidade/reserva; `exclusive` destina a `<NOME> - Exclusivos`. Não liberar reservas ou promover referência a criativo final pelo simples modo de armazenamento.
- As antigas pastas de envio por operação/gestor foram preservadas nos 30 TB como histórico técnico. Não pedir que usuários continuem enviando nelas nem recriá-las no MGS.

## Registrar e executar sem writer paralelo

Ares identifica e valida o pedido original, depois usa o helper com o autor humano real, a thread/canal e a mensagem reais:

```
python3 /root/mgs-agent/scripts/ares_flat_intake.py register --operation SHEIN_US_ES --manager Nicolas --destination exclusive --source-id ID_EXATO --requester-id AUTOR_HUMANO --channel-id THREAD_ORIGEM --message-id MENSAGEM_ORIGINAL
```

Acrescentar `--source-id` para os demais membros congelados. Primeiro conferir o plano; aplicar o mesmo comando com `--apply`. O helper valida a mensagem Discord nativa, whitelist/canal, origem exata e IDs/hashes/versionamento; não cria campanhas, não trata mídia e não move arquivos. Não inventar mensagem/autor nem cadastrar o lote em nome de Rodolfo se outra pessoa pediu.

Quando o pedido for o starter de uma auto-thread, o snowflake da thread pode ser igual ao da mensagem humana, mas o recurso da mensagem pertence ao canal pai. Se o GET da mensagem na thread retornar 404, consultar o mesmo message ID no pai real e validar `author.id`, `channel_id` e conteúdo antes do registro. Passar em `--channel-id` o canal nativo da mensagem que o helper realmente valida; preservar separadamente a thread de execução/resposta no checkpoint. Um 404 nessa combinação não prova falta de acesso nem ausência do pedido. Validar a correção com plano sem writes, registro e readback dos mesmos IDs; não usar outra identidade ou inventar uma mensagem substituta.

O registro alimenta o **mesmo** job `528c5710269d`. Não lançar outro executor manual em paralelo. O monitor entrega um batch determinístico com `scope_type=flat_request`, operação, gestor, destino e fonte humana. O claim atual revalida o pedido e o conjunto, congela o inventário protegido e preserva os mesmos IDs no replay. O lote técnico continua limitado pelo `intake-config.json`; uma divisão técnica não descarta o saldo do pedido.

Se uma execução manual já era dona das fontes, continuar pelo manifesto original e sua conclusão canônica, sem cadastrar outro request para os mesmos IDs. Não roubar claim, resetar o batch ou usar outro processo apenas para acelerar.

## Tratamento e entrega

Preservar classificação visual, naming, sanitização, dedupe, hashes, QA e inventário do contrato principal. No batch flat, usar **o autor e o contexto reais do batch**, não os campos históricos fixos de “automação pelo CEO”. O staging `_PROCESSAMENTO` continua técnico e temporário; caminhos OP/IMG|VID/READY|LEGACY ali não são a organização permanente oferecida ao usuário.

`complete` valida RAW/clean, archive request/receipt/ACK, provider e stock. No destino exclusivo, o finalizador flat chama a entrega dedicada por mesmo ID e registra o destino permanente exato; falha dessa etapa volta como `archive_ready`, nunca novo tratamento. Duplicatas mantêm a linhagem, reservas, uso e destino anteriores: não mover uma peça usada de volta para Exclusivos.

O mecanismo de manutenção existente, executado pelo componente privado isolado, arquiva por **mesmos IDs** as gerações concluídas do staging e encaminha relatórios permanentes que apareçam na raiz para o corporativo. Só admite fontes com conclusão/bytes/ACK, snapshots e escopo nativo correspondentes. Não usa DELETE/trash; no modo flat o controlador criativo mantém preservação por movimento, sem alterar a retenção de backups corporativos. Não importar credencial owner no agente nem abrir um transporte genérico para contornar as validações.

## Campanhas e resposta

Upload/registro/tratamento não autorizam campanha. Só continuar a criação/clone pelo pedido de Campaign Ops válido e pelos gates vigentes, preservando conta, orçamento, estratégia e início. Apenas mídia realmente atribuída nos anúncios passa de Exclusivos para Usados; falha e saldo não utilizado permanecem exclusivos.

Responder com o link permanente real e o mapa original → final. Separar recebidos, novos, duplicatas e pendentes; não dizer que todo material da entrada foi tratado porque um batch terminou. Os arquivos sem contexto continuam preservados para o pedido correto, sem classificação por adivinhação.
