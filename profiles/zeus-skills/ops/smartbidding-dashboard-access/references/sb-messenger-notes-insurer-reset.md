# Smart Bidding Messenger Page — reset massivo de `NOTES`

## When to Use

Use quando Rodolfo pedir para limpar o `NOTES` de todas as páginas e reiniciá-lo com a identificação do segurador como primeira linha.

## Contrato

- O valor inicial é exatamente `Segurador: <nome>`.
- Conteúdo antigo, inclusive códigos, é removido no reset.
- Crons podem acrescentar códigos depois, sempre após o prefixo do segurador.
- Nunca invente segurador: resolva por `FB_PAGE_ID`/`PAGE_ID` na DTR e use apenas fallbacks inequívocos documentados.

## Sequência segura

1. Leia o escopo completo de publishers `digital-trust` + `digital-trust-2` e congele a lista de IDs internos da SB.
2. Gere backup JSON 0600 de cada linha completa antes da primeira escrita, com hash e manifesto.
3. Monte o plano por ID interno da SB. Priorize associação DTR por `FB_PAGE_ID`; aceite fallback de `NOTES` estruturado, `PROFILE_NAME` ou histórico DTR apenas quando o nome for único e confirmado.
4. Pare se houver mudança de escopo ou divergência em `ID`, `PUBLISHER_ID`, `PAGE_ID` ou `FB_PAGE_ID` entre plano e execução.
5. Faça canário por fonte de associação e valide por leitura direta + leitura da lista completa.
6. Atualize cada linha por `POST /campaigns/Messenger` com o payload modal completo permitido, alterando somente `NOTES`.
7. Em HTTP 500/timeout, releia antes de repetir: a escrita pode ter sido aplicada apesar do erro. Repita somente IDs ainda divergentes.
8. Faça readback final do escopo completo. Sucesso exige todos os IDs presentes e cada `NOTES` igual ao alvo ou começando por `<alvo> - ` caso um cron já tenha acrescentado código.

## Pitfall confirmado — `update-many`

Não confie em `PUT /campaigns/Messenger/update-many` para reset de `NOTES` sem prova por readback. Em operação real, o endpoint retornou HTTP 200 vazio em 156 chamadas, mas não alterou os 1.546 registros pendentes. Trate HTTP 200 como transporte aceito, não como mudança aplicada; faça fallback por ID.

## Concorrência

- Concorrência alta satura o backend: 60 workers produziram HTTP 500 em 2.456 de 2.526 tentativas.
- Use no máximo 20 workers para a rota por ID e retries limitados com readback entre tentativas.
- Após cinco falhas consecutivas do mesmo ID/ferramenta, pare e escale com diagnóstico.

## Evidência mínima

Registre: escopo/publishers, quantidade de linhas, fontes de associação, hashes do backup/plano, canário, tentativas, códigos HTTP agregados e readback final (`validated`, `missing`, `mismatch`). Não registre token ou credencial.
