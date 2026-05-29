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

## Pasta nova vs retomada por manifest

Para uma pasta nova (ex.: NICOLAS), não começar com `download:from-manifest` se ainda não existir JSON fonte válido. Esse modo depende de uma lista-mestre/manifest anterior com `{name, designId}`; se o arquivo estiver vazio/inválido, ele deve falhar com "Manifest fonte inválido ou vazio". Primeiro gerar lista/manifest via `download:v2`/audit/coleta; só depois usar `download:from-manifest` para retry/retomada.

Validação mínima quando chegam dois arquivos V2:

```text
Arquivo                         | Validação
--------------------------------|------------------------------------------------
download-v2-designs_<GESTOR>    | total coletado, designId ausente/duplicado
download-v2-manifest_<OUT>      | status OK/erro, formatos, arquivos, designId
Comparação designs x manifest   | IDs iguais, interseção 100%, nenhum faltante
```

Pitfall observado: comando com argumento `999` pode virar nome/pasta de saída (`downloads_V2/999` e `download-v2-manifest_999.json`), não necessariamente limite. Ao receber esse manifest, validar pelo conteúdo real e avisar que a pasta de saída ficou como `999`.

Antes de tratar V2 como final, confirmar o total real da pasta Canva. Se a coleta retornar só 60 itens, isso só é aceitável se o Canva mostrar 60 designs; se houver mais, é o mesmo problema de virtual scroll do GEORGE e a lista-mestre está incompleta.

### NICOLAS V3: manifest parcial + Cloudflare + IDs extras

Quando a pasta tem downloads parciais válidos mas os manifests estão errados/incompletos, não montar seed a partir de lista colada no Discord. Ler os arquivos reais no disco (`output/downloads_V2/<GESTOR>` e eventuais pastas acidentais como `999`), extrair `designId` do sufixo `__designId.ext`, copiar para `output/downloads_V3/<GESTOR>` e gerar seed por IDs únicos.

Se Playwright/Chromium cair em loop de Cloudflare no Canva, não insistir abrindo novos perfis. Pedir para Rodolfo abrir Chrome normal com `--remote-debugging-port=9222`, passar Cloudflare/login manualmente e conectar o script via `chromium.connectOverCDP('http://127.0.0.1:9222')` à aba Canva já aberta.

Pitfall: coletar IDs por regex no HTML inteiro pode capturar IDs extras de cache/preview. Exemplo NICOLAS: `342/334` coletados e `283` pendentes, quando o correto era `334/334` e `275`. Nesses casos, não baixar; filtrar master para IDs com `name` ou `url` de linha real e só prosseguir quando `master limpo = total Canva` e `pendentes = total Canva - seed OK`.

Detalhes e comandos de diagnóstico/filtro: `references/canva-nicolas-v3-cdp-recovery.md`.

Retry de erros: enquanto cada rodada `errors` continuar recuperando arquivos, vale repetir. Só declarar exceção manual quando os mesmos poucos designs persistirem sem progresso, especialmente erros "menu abriu sem opção Baixar".
