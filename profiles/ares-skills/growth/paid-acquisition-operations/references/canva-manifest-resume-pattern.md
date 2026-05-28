# Sessão GEORGE/NICOLAS — padrão de retomada por manifest

Use esta referência quando uma pasta Canva grande falhar por virtual scroll, coleta incompleta ou nomes repetidos.

## Problemas observados

- Pasta GEORGE tinha 261 designs; script inicial baixou 205 OK e 56 erros, mas salvava pelo nome do criativo e gerou sobrescritas.
- Explorer mostrou 153 arquivos reais apesar de manifest marcar 205 OK: diferença causada por nomes repetidos (`50 - Story Espanhol`, `77 - Story INGLES`, etc.).
- `download:v2` com rolagem lenta corrigiu nome seguro (`__designId`) e zerou sobrescrita, mas coletou só 60/261 por estabilizar cedo no virtual scroll.
- Modo assistido por tela (`download:visible`) é tecnicamente útil, mas operacionalmente ruim para Rodolfo: ele não quer ficar na frente do PC fazendo dezenas de rodadas.
- Ao sugerir novo npm script, primeiro entregar arquivo + linha `package.json`; se mandar comando antes, dá `Missing script`.

## Padrão recomendado

1. Manter uma **lista-mestre por designId** separada do manifest de execução.
2. Baixar sempre para pasta nova/versionada (`downloads_V3/<GESTOR>/`).
3. Nome final sempre: `safeName(nome)__designId.ext`.
4. Manifest final incremental: `download-v3-manifest_<GESTOR>.json`.
5. Se existir manifest V2 com OK e arquivos no disco, copiar esses arquivos para V3 e registrar `source: copied_from_v2` antes de baixar faltantes.
6. Rodar modo normal para todos, mas pular `status=ok` com arquivo existente.
7. Se falhar, rodar modo `errors` para tentar só erros/faltantes.
8. Antes de Drive, validar: total da lista-mestre = status OK = arquivos únicos no disco.

## Comandos-modelo

```powershell
npm run download:from-manifest -- "https://www.canva.com/folder/FAFeimwiZkw" "GEORGE" "output/download-pilot-manifest_GEORGE.json"

npm run download:from-manifest -- "https://www.canva.com/folder/FAFeimwiZkw" "GEORGE" "output/download-pilot-manifest_GEORGE.json" errors
```

## Quando o manifest fonte sumir/zerar

Se `download-pilot-manifest_GEORGE.json` existir com `Length 0` ou não existir:

- Não pedir para Rodolfo preencher JSON manualmente.
- Criar um `scripts/seed-<gestor>-manifest.js` que grava `output/download-pilot-manifest_<GESTOR>.json` a partir de uma lista compactada de `{name, designId}`.
- Para payload grande, usar base64+gzip no script seed para evitar colar 70KB de JSON bruto no Discord.
- O seed deve imprimir `Itens: N` e o agente deve pedir verificação de tamanho antes de rodar o download.

## Critério de sucesso

```text
Campo                         | Esperado
------------------------------|----------------------------
lista-mestre                  | total real da pasta Canva
manifest final                | mesmo total da lista-mestre
status OK                     | mesmo total da lista-mestre
erros                         | 0 ou lista explícita
arquivos únicos no disco      | igual a status OK
nomes                         | 100% com __designId.ext
```
