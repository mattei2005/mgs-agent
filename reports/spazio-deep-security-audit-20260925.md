# Spazio — auditoria profunda de segurança e integridade

**Estado:** CONCLUÍDA — SEM MALWARE/INVASÃO COMPROVADOS; REMEDIAÇÕES P1 PENDENTES  
**Data:** 2026-09-25 UTC / 2026-09-24 America/New_York  
**Domínio:** `spaziokitchensandbaths.com`  
**Servidor:** SpazioVPS / RunCloud server ID `266820` / `157.230.212.128`  
**Webapp:** `spaziokitchensandbaths` / app ID `1376648`  
**Pedido:** Discord `1552877432665800715`  
**Confirmação crítica do SSH temporário:** Discord `1552877919867502676`

## Conclusão executiva

A auditoria profunda não encontrou evidência confirmada de webshell, malware ativo, usuário WordPress desconhecido, processo minerador, cron de persistência, PHP executável em uploads, trigger/evento de banco malicioso ou nova alteração de código após a recuperação.

O site está operacional:

- homepage pública e origem: HTTP 200;
- painel: HTTP 302 esperado para a tela de login;
- REST: HTTP 200;
- banco: `wp db check` PASS;
- core WordPress `7.1.2`: checksum oficial PASS;
- zero novo fatal no log após a recuperação das `02:46 UTC`;
- nenhuma mensagem de erro crítico ou W3 nas superfícies públicas verificadas.

Isso não significa que o ambiente está seguro. Foram confirmadas exposições públicas e riscos estruturais P1 que precisam de uma fase de correção separada e reversível.

## Achados P1

### 1. Arquivos internos publicamente acessíveis

Duas rotas retornam o arquivo real, tanto pelo Cloudflare quanto diretamente na origem:

- `/nginx.conf`: HTTP 200, 14.199 bytes, SHA-256 `de3b5cc2c63c8602990c55ff4f7037530798c278cdb6a788c024ccbb6b3863cc`;
- `/wp-admin/error_log`: HTTP 200, 67.035 bytes, SHA-256 `e9fed3f8148128d9d9c2fefbd920bf783ac5bb953406dc9533be1299f5b20926`.

A análise não encontrou senhas, tokens, chaves privadas, emails ou connection strings nesses dois arquivos. Mesmo assim, o log expõe 788 linhas históricas, incluindo 102 fatals e 79 warnings, e o arquivo Nginx expõe detalhes internos de configuração. Eles devem ser bloqueados no servidor e removidos do webroot com backup/rollback.

### 2. Integridade de plugins continua não canônica

- 47 plugins normais: 26 ativos e 21 inativos.
- Checksum estrito: 12 passaram, 25 falharam e 10 não têm checksum público aplicável.
- Os mesmos 25 plugins divergentes da auditoria de 23/09 foram comparados arquivo a arquivo com o manifesto anterior: todos permanecem byte a byte iguais ao baseline, incluindo o plugin single-file `hello.php` após normalização do slug.
- Portanto, não houve novo drift nesses 25 plugins durante o incidente. O problema histórico de árvores misturadas continua real.
- 35 plugins têm atualização disponível; 19 deles estão ativos.
- A atualização em lote não é segura: a tentativa anterior produziu Elementor `4.3.1` com Elementor Pro `3.31.2` e derrubou o site.

### 3. SSH e exposição do host

Configuração efetiva:

- `PermitRootLogin yes`;
- `PasswordAuthentication yes`;
- `PubkeyAuthentication yes`;
- `MaxAuthTries 6`;
- `AllowTcpForwarding yes`;
- `X11Forwarding yes`.

Nos sete dias do journal:

- 9.719 falhas de senha;
- 10.606 tentativas com usuário inválido;
- 17 eventos de máximo de autenticações;
- 87 logins por senha, todos atribuídos às contas temporárias MGS/Hermes usadas nas operações autorizadas;
- 143 logins por chave pública, somente `root` e `runcloud` na mesma origem MGS observada.

Não foi observado login aceito por senha em `root`, `admin` ou outro usuário desconhecido. Há somente um usuário UID 0: `root`.

Duas chaves válidas preexistentes de root permanecem com os mesmos fingerprints da auditoria anterior. Uma terceira linha não parseável já estava no arquivo antes da auditoria atual; o `authorized_keys` de root não mudou desde 22/09. Não foi classificada como chave nova.

### 4. Firewall, listeners e manutenção do servidor

- Política base de `iptables`/`nftables`: `INPUT ACCEPT`.
- Fail2Ban está ativo e filtra `sshd`, `sshd-ddos` e `runcloud-agent`.
- Portas em todas as interfaces: 22, 25, 80, 443 e 34210.
- MariaDB 3306 está somente em loopback.
- Ubuntu 22.04.3, kernel `5.15.0-67-generic`.
- 107 pacotes atualizáveis.
- `/var/run/reboot-required` presente.
- `unattended-upgrades.service` falhou.
- PHP 8.0.30 está fora de suporte upstream.

Não foi feito update, reboot, restart ou alteração de firewall nesta auditoria.

### 5. Permissões e configuração WordPress

- `wp-config.php`: modo `0644`, `runcloud:runcloud`, com segredos potencialmente legíveis por processos locais fora do owner/grupo.
- `DISALLOW_FILE_EDIT` não está definido no arquivo atual.
- `WP_DEBUG=false`, oito salts definidos, `WP_CACHE=true`.
- Diretório `.tmb`: modo `0777`, único item world-writable na aplicação.
- Todo o restante do webroot está sob `runcloud:runcloud`; zero SUID/SGID e zero symlink atual.

### 6. Capacidade de disco

- Volume: aproximadamente 33,74 GiB.
- Uso atual: 78,0%; livre: aproximadamente 7,40 GiB.
- Crescimento desde a coleta interna de 23/09: aproximadamente 10,30 GiB.

A maior parte é compatível com o backup protegido de 4,18 GiB, o restore isolado completo e os artefatos de incidente preservados. A retenção autorizada vai até pelo menos 24/10; não houve limpeza nesta auditoria.

## Achados P2

- Dois ZIPs idênticos de Pantry estão públicos em uploads, cada um com 6.397.352 bytes. São arquivos ZIP válidos, sem PHP, sem path traversal e sem assinatura heurística de webshell; ainda assim, não precisam ficar publicamente baixáveis.
- `/readme.html` está público.
- `/wp-json/wp/v2/users` permite enumeração pública de autores. Endpoints de plugins, temas e contexto administrativo retornam 401.
- XML-RPC está ativo. Na janela mais recente de 50 MiB do access log, houve 15.831 POSTs HTTP 200 a `/xmlrpc.php`; HTTP 200 não comprova autenticação bem-sucedida, mas confirma uma superfície fortemente atacada.
- Ausentes nos headers da homepage: CSP, `Referrer-Policy` e `Permissions-Policy`. HSTS, `X-Frame-Options` e `X-Content-Type-Options` estão presentes.
- O certificado público Cloudflare é válido até 11/11/2026. A origem apresenta cadeia incompleta para um cliente que exige validação (`curl` 60, verify result 20); o acesso com SNI e validação ignorada responde normalmente.
- Autoload está estável em relação ao baseline bruto: 505 linhas e 1.108.653 bytes; 875.287 bytes pertencem ao transient de tamanho de diretórios. É risco de desempenho, não indicador de invasão.
- 297 comentários estão pendentes e 17 aprovados. Nenhum spam publicado novo foi comprovado.
- O plugin W3 Total Cache voltou no snapshot apenas como inativo; `object-cache.php` continua ausente. O drop-in atual é somente `advanced-cache.php` e seu SHA-256 coincide exatamente com `speedycache/main/advanced-cache.php`.

## Varredura de filesystem e malware

Cobertura:

- 49.060 arquivos e 6.555 diretórios;
- aproximadamente 4,52 GiB lidos e hasheados;
- digest lógico do manifesto: `edf6c651567f5ec9a84c44f9b4efda2abe93b14fc2ea75fdad4993cdfdef4114`;
- zero PHP em `wp-content/uploads`;
- zero executável disfarçado confirmado;
- zero symlink;
- zero SUID/SGID;
- zero processo com padrão de minerador/webshell;
- zero cron de sistema contendo `curl`/`wget`;
- zero arquivo com assinatura direta `eval(base64_decode())`, `gzinflate`, execução de shell por input HTTP, C99, R57, WSO ou B374K.

Falsos positivos classificados:

- `wp-includes/Text/Diff/Engine/shell.php` pertence ao core oficial e o checksum do core passou.
- arquivos `Mailer.php` do WP Mail SMTP, scripts do Elementor e arquivos do WP File Manager foram marcados apenas pelo nome do arquivo/diretório.
- `really-simple-ssl/class-admin.php` e `security/firewall-manager.php` pertencem à árvore histórica já auditada; nenhum payload externo ou input-to-shell foi encontrado.
- os dois ZIPs Pantry foram marcados inicialmente porque bytes comprimidos continham a sequência `<?php`; a inspeção estrutural confirmou zero entrada PHP.

Limitação: ClamAV, RKHunter e Chkrootkit não estão instalados e nenhum scanner foi instalado durante a auditoria. A cobertura foi feita por hash integral, checksum oficial, comparação de baseline, padrões de código, banco, logs, runtime e superfícies pública/origem. Dez plugins privados/pro e os temas Pantry não têm fonte pública canônica para certificação independente.

## Banco, usuários e persistência

- 127 tabelas; `wp db check` PASS.
- Zero trigger e zero evento MariaDB.
- Usuários atuais, iguais ao artefato bruto de 23/09:
  - `rmmaster`: administrator;
  - `raqueloliveira`: administrator;
  - `zeus`: administrator;
  - `atena`: editor.
- Duas application passwords MGS: `Atena API - MGS` e `Zeus API - MGS`; nenhum segredo foi lido ou persistido.
- Uma sessão WordPress ativa no `rmmaster` durante a coleta.
- 30 eventos WP-Cron, todos associados a core/plugins conhecidos.
- 10 snippets WPCode: hashes, status e tamanhos idênticos ao baseline de 23/09.
- Referências externas dos snippets publicados: Tawk.to, Google Tag Manager, Facebook/Instagram e o próprio domínio. Nenhuma função de shell/webshell foi encontrada.
- Dezoito registros `_elementor_data` contêm `String.fromCharCode`, mas correspondem a seis hashes repetidos derivados do mesmo snippet histórico WPCode `41615`; não possuem host externo, `eval`, `document.write`, base64, shell ou alteração recente. Classificados como código histórico ofuscado/empacotado, não como malware confirmado.
- Conteúdo com iframe é majoritariamente cache `_oembed`; nenhum item recente após 22/09 foi encontrado.

## Logs e incidente anterior

Os fatals de Elementor observados até `02:45 UTC` pertencem ao incidente já recuperado. A partir de `02:46 UTC`, a nova leitura de logs encontrou:

- zero fatal;
- zero warning;
- zero erro de permissão;
- zero timeout upstream;
- zero erro de banco.

Na janela de access log analisada, sondagens para `.env`, phpinfo, shell e caminhos falsos retornaram 403/404. Não houve resposta 2xx para path suspeito de shell, dump, `.env`, `.git`, backup de configuração ou PHP em uploads.

## Credenciais temporárias

Três ciclos SSH temporários foram usados porque a primeira coleta teve consultas SQL/parsers parciais e a política exige correção automática e retry:

1. coleta integral de filesystem, WordPress, banco, logs e host;
2. retry focado em banco, SSH, manifests completos, arquivos ZIP e logs pós-recuperação;
3. triagem semântica dos registros históricos com `String.fromCharCode`.

Em todos os ciclos:

- identidade/topologia do webapp validada antes da conexão;
- uma única credencial temporária por ciclo;
- remoção em `finally`;
- GET final 404;
- lista final RunCloud com zero credenciais;
- chave removida recusada pelo SSH;
- material privado local destruído;
- zero segredo emitido.

Estado final: zero credencial SSH temporária restante.

## Recomendação operacional

Executar uma fase separada, em canário e com rollback, nesta ordem:

1. bloquear e retirar do webroot `nginx.conf` e `wp-admin/error_log`;
2. remover acesso público aos ZIPs e `readme.html`;
3. endurecer `wp-config.php`, desativar editor de arquivos e corrigir `.tmb` sem quebrar runtime;
4. restringir SSH/root/password e firewall preservando canal canário RunCloud;
5. atualizar sistema/PHP com backup, janela e reboot validado;
6. reconstruir plugins por unidades compatíveis em staging, começando pelos 19 ativos desatualizados;
7. avaliar desativação/restrição do XML-RPC e enumeração pública de usuários;
8. corrigir a cadeia TLS da origem;
9. planejar limpeza dos backups somente após 24/10 e nova confirmação crítica.

Nenhuma dessas remediações foi executada nesta auditoria somente leitura.

## Aprendizado operacional persistido

A skill `wordpress-plugin-integrity-audits` foi ampliada com três guardrails reutilizáveis:

- testar arquivos extras/resíduos publicamente, porque checksum de core não cobre `nginx.conf`, logs e archives;
- separar validação TLS da origem de um probe HTTP com verificação ignorada;
- nunca classificar ZIP como PHP/malware por bytes crus antes de inspecionar entries e path traversal.

Skill canônica e mirror MGS foram sincronizados e validados com SHA-256 idêntico `bb421b3f2620aec0bb354e5ed0c7d4b38eb92776c3f20fce0c5fd831434ea13a`.

## Evidências

Workspace restrito:

`/root/.hermes/profiles/zeus/workspace/spazio-deep-audit-20260925/`

Artefatos principais:

- `deep-audit-live.json`;
- `deep-audit-lifecycle-receipt.json`;
- `deep-audit-followup-live.json`;
- `deep-audit-followup-lifecycle-receipt.json`;
- `db-semantic-triage-live.json`;
- `db-semantic-triage-lifecycle-receipt.json`;
- `external-audit.json`;
- `plugin-baseline-comparison.json`.
