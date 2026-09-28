# Spazio — correção de resíduos visuais e técnicos (2026-09-27)

## Resultado

A correção da aplicação WordPress e a manutenção do host de `spaziokitchensandbaths.com` foram concluídas e validadas em público, origem, crawl integral e navegador desktop/mobile.

Autorizações:

- correção integral e primeiro acesso temporário: Discord `1553790893302087831`;
- acesso temporário final e hash candidato: Discord `1553823395219505174`.

## Mudanças aplicadas

- Removida da renderização pública a string de verificação que aparecia abaixo do formulário.
- Removidas cinco ocorrências da string no banco; readback final: zero.
- Criado o arquivo de verificação Google no webroot com conteúdo exato e HTTP 200.
- Corrigidas seis superfícies não canônicas com redirecionamento 301:
  - `/pricing/` → `/contact-us/`;
  - `/portfolio-properties/` → `/portfolio/`;
  - `/hardware/` → `/category/hardware/`;
  - três variantes hierárquicas de `/contact-us/` → `/contact-us/`.
- Corrigidos títulos duplicados de arquivos/tags e paginação.
- Preenchidas descrições ALT para 296 anexos e aplicado fallback restrito para imagens legadas/CAPTCHA; o crawl passou de 499 para zero ocorrências sem ALT.
- Protegidos os dois links `mailto:` com o mecanismo oficial `email_off`, eliminando a injeção Cloudflare cujo decoder retornava 404.
- Instalado/atualizado o MU plugin `mgs-spazio-corrections.php`.
  - hash final: `6a92cfc8ccd1f41a287036e8a2a8866c1305cab5a2f2e1b1c9916ce5dd4c872a`.
- Elementor e Elementor Pro preservados em `3.31.2`.

## Backup e rollback

- Banco pré-correção: `/home/runcloud/.mgs-backups/spazio-full-correction-20260927/spazio-pre.sql.gz`.
- SHA-256: `1e55cc5b34166ded5af3c50c49a4cd22ca652482c2121286ec3b790378042e0d`.
- Versão anterior do MU plugin preservada no mesmo conjunto de backup.
- Credenciais SSH temporárias removidas e ausência validada por GET 404.

## Validação final

- Crawl: 17 sitemaps, 290 páginas, 1.306 assets.
- Páginas com erro: 0.
- Fatais: 0.
- Mixed content: 0.
- Canonicals ausentes: 0.
- Imagens sem ALT: 0 de 1.864.
- Problemas acionáveis após classificação: 0.
- Navegador: 16/16 execuções aprovadas em desktop/mobile.
- Imagens quebradas, overflow, erros de página, links legados e falhas internas: 0.
- Verificação Google: HTTP 200, 54 bytes, conteúdo exato.
- String visível indevida: 0 em público e origem.
- Decoder Cloudflare quebrado: 0 referências públicas.

Os três retornos auxiliares restantes são comportamento esperado e não defeitos:

- oEmbed sem parâmetro obrigatório: 400;
- usuário REST protegido: 404;
- XML-RPC bloqueado: 403.

## Observações de host reconciliadas

- O sinal anterior `securityUpdate=true` do RunCloud foi reconciliado pelo estado real: APT sem pacotes pendentes, `dpkg --audit` limpo, kernel atual e zero processos listados por `needrestart` após o reboot.
- `Referrer-Policy`, `Permissions-Policy` e CSP estão presentes na resposta base, cache, resposta dinâmica, público e origem.
- O SSL da origem é `custom`, válido no RunCloud até 2038 e destinado ao caminho Cloudflare→origem. O edge público possui TLS válido; a origem direta não é confiável pela CA pública do sistema, portanto não foi classificada como falha pública de TLS.

## Host maintenance — 2026-09-27

O manifesto crítico `29ca3b6505cb70df29d30448320ccbfc293eda56c08d0eb80e21535d700ca2ab`, confirmado na mensagem Discord `1553834997222342657`, foi aplicado.

- `libaudit-common`: `1:3.0.7-1build1` → `1:3.0.7-1ubuntu0.1`.
- `libaudit1`: `1:3.0.7-1build1` → `1:3.0.7-1ubuntu0.1`.
- APT após a transação: zero pacotes pendentes; `dpkg --audit` limpo.
- Include criado: `/etc/nginx-rc/extra.d/spaziokitchensandbaths.headers.mgs-modern-security.conf`.
- SHA-256: `e3f18e8bbdd7f808f9f1046e44a74dc43ce2d819aacb8ccca07f07dd589caddc`.
- `nginx-rc -t`: aprovado; reload aplicado; Nginx, PHP 8.3, MariaDB, RunCloud Agent, Fail2Ban e unattended-upgrades ativos com PIDs protegidos inalterados.
- Headers confirmados em cache, dinâmico, público e origem: Referrer Policy, Permissions Policy e CSP.
- Browser real com CSP em produção: 16/16 aprovado, zero violações CSP, erros de página, requests internos falhos, imagens quebradas ou overflow.
- Crawl pós-host: 290 páginas, 1.306 assets, zero erros acionáveis e zero ALT ausente em 1.864 imagens.
- Credencial SSH temporária removida por readback.
- Rollback dos pacotes preservado em `/root/.mgs-secure-backups/spazio-host-fix-20260927T182833Z` com os dois `.deb` anteriores validados por metadados e SHA-256.

A transação atualizou `libaudit1`, que já estava carregada por 16 serviços/sessões do sistema. O reboot controlado autorizado na mensagem `1553839885868339467` concluiu em quatro ciclos de recuperação: boot ID alterado, kernel atual, zero `NEEDRESTART-SVC`, zero failed units, APT/dpkg limpos, serviços ativos e credencial temporária removida.

A validação estrita encontrou duas linhas críticas no journal do novo boot:

- o ciclo de ordenação do `cloud-init` foi reconciliado como não acionável: `cloud-init status --long` retorna `done`, todos os estágios têm `Result=success` e não existem erros ou erros recuperáveis;
- o `rsyslog` não conseguia criar `/var/log/mail.log`. A falha era preexistente nos boots anteriores: o arquivo estava ausente e a ação `mail.*` ficava suspensa. Durante a investigação, `/var/log` convergiu para `root:syslog`, modo `0755` e ACL efetiva `mask::r-x`; a correção final não ampliou a escrita no diretório.

A correção ACL v1 foi bloqueada antes de qualquer mutação porque o preestado mudou de `mask::rwx` para `mask::r-x`. A investigação de recorrência mostrou que conceder escrita ao diretório seria mais amplo e menos durável que corrigir os alvos de log. O manifesto v2, confirmado na mensagem Discord `1553872315853443193`, foi aplicado: `/var/log/mail.log` foi criado como `syslog:adm 0640` e `create 0640 syslog adm` foi acrescentado ao bloco existente de `/etc/logrotate.d/rsyslog`, garantindo recriação após rotações. A ACL de `/var/log`, inclusive `group:users-rc:---`, permaneceu byte a byte igual.

A primeira execução do v2 criou e validou o log, mas um erro local de nome de variável no pós-check acionou o rollback automático do arquivo logrotate e preservou o log conforme o manifesto. O erro foi corrigido, o estado parcial foi atribuído pelo marcador autorizado e a repetição concluiu: `logrotate --debug` aprovado, dois probes `mail.info` gravados, crescimento final de 130 bytes, zero novos erros de permissão/suspensão no journal, `rsyslogd -N1` aprovado, serviço ativo, APT/dpkg limpos, zero failed units, zero `NEEDRESTART-SVC` e credencial SSH removida. Nenhum restart ou reboot adicional ocorreu.

## Evidências

- Validação consolidada: `/root/.hermes/profiles/zeus/workspace/spazio-full-correction-20260927/final-validation.json` — `e84721a11e8c44e6d55bae059d1c157b261b1c2b7ffc9570e0fa270844c697df`.
- Crawl pós-host: `/root/.hermes/profiles/zeus/workspace/spazio-full-correction-20260927/post-public-crawl.json` — `27d26707958b1d2ff3509c4233fab50f336787e47fa3c472efc76e8dd3b06a0e`.
- Browser CSP/headers ao vivo: `/root/.hermes/profiles/zeus/workspace/spazio-full-correction-20260927/live-headers-browser-validation.json` — `e7a66611434b323728e01d17ca03969e27cd3f1685406ca632c942900286989f`.
- Provas focadas: `/root/.hermes/profiles/zeus/workspace/spazio-full-correction-20260927/targeted-validation.json` — `e2bbf037c5229aade5c4563a27f91b1d918d3d6cb120b4f9c2bdc4316ed2441e`.
- Recibo do host: `/root/.hermes/profiles/zeus/workspace/spazio-full-correction-20260927/host-fix-receipt.json` — `5c03092ea89076834db394b260eba9ea854a981491f794ebd4319c4d8fcb3c85`.
- Validação pós-host: `/root/.hermes/profiles/zeus/workspace/spazio-full-correction-20260927/host-post-validation.json` — `711bbfd1b01ae412d2af018c0cb3556e1eb50807192aad10373f2f171d1df099`.
- Recibo do reboot: `/root/.hermes/profiles/zeus/workspace/spazio-full-correction-20260927/host-reboot-receipt.json` — `405a3a7a81d736c184aa74bebc2b9b94e98124d517d4e263b82fceba37d996e8`.
- Diagnóstico pós-reboot: `/root/.hermes/profiles/zeus/workspace/spazio-full-correction-20260927/post-reboot-journal-diagnosis.json` — `ef48c122d027312b339ef3e32c3d9543deb539ac685080aec6f1a316366389d0`.
- Manifesto ACL v1 supersedido, sem mutação: `/root/.hermes/profiles/zeus/workspace/spazio-full-correction-20260927/rsyslog-acl-fix-manifest-v1.json` — `0fe0d149581bf6663db1ae1dd0e026b45b1060f8ec5bf8ce9fa38944e8097aae`.
- Manifesto rsyslog v2 aplicado: `/root/.hermes/profiles/zeus/workspace/spazio-full-correction-20260927/rsyslog-mail-log-fix-manifest-v2.json` — `9731b70e7b7dbd73c6c444404a04aa471f4d254b4dc9d327a9b50aef447487fa`.
- Recibo rsyslog v2: `/root/.hermes/profiles/zeus/workspace/spazio-full-correction-20260927/rsyslog-mail-log-fix-v2-receipt.json` — `042ce890343a3ce6da70a717c7f1f8f8ca77d911a9c028833d515b3f30aeb19c`.
- Ciclo SSH: `/root/.hermes/profiles/zeus/workspace/spazio-full-correction-20260927/final-phase-receipt.json` — `143449320575de8b2091b05c62b5b1d2fd049113c12834bb97117e6c020c8ec1`.
