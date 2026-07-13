# Validação controlada de alteração task-local do collector

Use este procedimento quando uma correção temporária no collector for descrita como “validada”, mas o runtime canônico não puder ser alterado durante a tarefa.

## Evidência mínima

1. Copiar o collector canônico para dois arquivos task-local sob `artifacts/meta-library/`:
   - baseline byte-identical ao canônico;
   - candidato com somente a mudança sob teste.
2. Registrar SHA-256 dos dois collectors e um diff unificado. O diff do candidato deve conter apenas a alteração declarada.
3. Executar baseline e candidato contra a mesma URL, perfil persistente, proxy, lock, parâmetros de scroll/download e janela operacional comparável.
4. Preservar os dois `report.json` brutos e registrar seus SHA-256.
5. Comparar resultados por métricas que provem o efeito, não apenas por `success=true` ou HTTP 200.
6. Quando a mudança tratar associação DOM → Library ID, exigir:
   - baseline com resultado anterior observado;
   - candidato com `mediaLinkedToCardCount > 0`;
   - ao menos um download selecionado com `libraryId` não nulo;
   - preferencialmente o mesmo arquivo selecionado nas duas execuções, confirmado por SHA-256, para isolar a associação do conteúdo baixado.
7. Provar que o collector canônico não mudou:
   - SHA-256 antes e depois idênticos;
   - `git diff --exit-code -- <collector-canônico>` retornando 0.
8. Se a evidência sustentar uma pending de skill, registrar caminho e SHA-256 da pending e não aprová-la, rejeitá-la, editar ou remover sem decisão explícita do revisor.

## Caso de referência: `nearestLibraryId`

Comparação controlada na mesma busca da Meta Library:

```text
Condição                         depth 10       depth 40
Library IDs observados           91             91
Imagens / vídeos                 5 / 48         5 / 48
mediaLinkedToCardCount           0              53
Library ID do download           null           não nulo
SHA-256 da mídia selecionada     igual          igual
```

O diff isolado foi somente:

```diff
- depth < 10
+ depth < 40
```

Isso demonstra que o ganho veio da profundidade de associação DOM, e não de outra mudança no collector ou de um arquivo diferente selecionado.

## Artefato consolidado recomendado

Além dos `report.json` brutos, gerar `evidence-report.json` contendo:

- paths e hashes dos collectors;
- paths e hashes dos reports;
- métricas baseline/candidato;
- download selecionado e hash real do arquivo;
- hash antes/depois e status Git do canônico;
- path/hash/estado da pending relacionada;
- checks booleanos de aceitação.

O report consolidado facilita revisão, mas nunca substitui os `report.json` originais.