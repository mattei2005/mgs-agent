# F023 — Fechamento da rota XML-RPC alternativa em wrnoticia.com

**Estado:** RESOLVIDA E VALIDADA  
**Data:** 2026-09-23 UTC  
**Domínio:** `wrnoticia.com`  
**Aplicação:** `wrnoticia-home` / MatteiInc01  
**Autorização crítica:** Discord `1552151365915246696`

## Diagnóstico

O arquivo `/home/runcloud/webapps/wrnoticia-home/apagar_xmlrpc.php` estava publicamente acessível e aceitava POST XML-RPC, retornando `system.listMethods` em HTTP 200.

A investigação estática confirmou:

- tamanho: 3.238 bytes;
- SHA-256: `352625a34afa7e0fe44839a1753351466eed6e0a36b488eb7b5ed49c517fc090`;
- correspondência byte a byte com `xmlrpc.php` do pacote oficial WordPress 6.2;
- nenhuma referência interna ao nome `apagar_xmlrpc.php`;
- nenhum indicador de `eval`, `base64_decode`, shell ou execução externa;
- nenhum indício de webshell;
- único acesso encontrado nessa rota: POST read-only da própria auditoria de 22/09/2026.

O risco não era malware: era uma segunda entrada XML-RPC que poderia escapar de controles aplicados apenas ao caminho padrão.

## Escopo confirmado

Hash do escopo: `fdd000d4e3920a3265d3acdb3674ef00ba6954f1a48cb0a172cce0eff5988a5a`.

Ações autorizadas:

1. backup e remoção exclusiva de `apagar_xmlrpc.php`;
2. criação de bloqueio Nginx exclusivo para essa rota;
3. `nginx-rc -t`, reload e validação HTTP.

Preservado explicitamente:

- `/xmlrpc.php` original;
- banco, conteúdo, usuários, plugins e temas;
- `eng.wrnoticia.com`, `es.wrnoticia.com` e `wr.wrnoticia.com`;
- vhost gerado pelo RunCloud.

## Aplicação

- Arquivo removido do webroot por movimentação atômica para a quarentena protegida.
- Include criado:
  `/etc/nginx-rc/extra.d/wrnoticia-home.location.main-before.mgs-apagar-xmlrpc-containment.conf`
- SHA-256 do include:
  `4ef843322d8f55b8728282683a8a0ee1bfccffd9f565306b729e3b72d610ef05`
- `nginx-rc -t`: PASS.
- `nginx-rc`: ativo após reload.
- Vhost gerado preservado com SHA-256:
  `19907b582f0e4bdf85eceaf6211d8036cc5340062d9248e7e5bf6878766aedc0`.

## Falha inicial e recuperação

A primeira aplicação parou em uma asserção antes da movimentação do arquivo. O estado foi reconciliado imediatamente:

- bloqueio Nginx já instalado e válido;
- serviço ativo;
- arquivo original ainda presente e com o hash autorizado;
- backup íntegro e restore-tested;
- quarentena ainda ausente.

A execução foi retomada somente a partir desse estado comprovado. A movimentação exata terminou e toda a validação foi repetida. Não houve ampliação de escopo nem estado parcial remanescente.

## Backup e rollback

Diretório protegido: `/var/backups/mgs-wrnoticia-f023-20260923/` — modo `0700`.

- `apagar_xmlrpc.php.pre-removal`: SHA-256 original, modo `0600`, restauração byte a byte testada.
- `apagar_xmlrpc.php.removed-original`: original removido do webroot, mesmo SHA-256, modo `0600`.
- manifesto autorizado e receipt preservados no mesmo diretório.

Rollback:

1. restaurar o arquivo pelo backup;
2. mover somente o include MGS para fora de `extra.d`;
3. executar `nginx-rc -t`;
4. recarregar o Nginx;
5. validar HTTP e hashes.

## Validação final

`final-validation.json`: **PASS**.

Rota removida, na origem e no público:

- GET: HTTP 403;
- POST: HTTP 403;
- query string: HTTP 403;
- path-info: HTTP 403;
- variação de caixa: HTTP 403;
- corpo de bloqueio canônico confirmado na origem e na borda.

Controles:

- home: HTTP 200 na origem e no público;
- REST: HTTP 200 na origem e no público;
- XML-RPC original: preservado e funcional na origem; borda continua aplicando Cloudflare HTTP 403;
- WordPress core checksum: PASS;
- zero alteração em banco, conteúdo, usuários, plugins, temas ou subdomínios;
- vhost gerado intacto;
- arquivo alvo ausente do webroot.

## Planilha

A planilha canônica foi atualizada pela Service Account oficial:

- `Prioridades!24`;
- `Domínios!112`;
- `Limpeza!11`;
- `Pendências limpeza!56`;
- `Fechamento final!12`.

Canário foi gravado, relido e removido. Valores foram relidos integralmente e 54 células tiveram estado visual verde confirmado por `effectiveFormat`.

## Evidências

Workspace:
`/root/.hermes/profiles/zeus/workspace/wrnoticia-f023-resolution-20260923/`

Principais artefatos:

- `audit-live.json`
- `authorized-scope.json`
- `state-after-failure.json`
- `apply-receipt.json`
- `final-validation.json`
- `sheet-before.json`
- `sheet-update-receipt.json`

## Conclusão

F023 está **RESOLVIDA E VALIDADA**. A rota XML-RPC alternativa foi removida e bloqueada sem afetar o endpoint original, o site, o conteúdo, os subdomínios ou o vhost gerado. Não há evidência de que a cópia oficial legada tenha sido explorada.
