# MGS Router — resultado da verificação persistente

## Autoridade e diagnóstico

Rodolfo, mensagem `1556022368042876989`, thread `1555381168894115912`, pediu corrigir o estado verde que desaparecia após atualizar a página e perguntou se Verificar consulta online.

Causa reproduzida: `web/app.js` guardava o resultado somente em um Map em memória do navegador; o backend retornava o resultado de `/api/domains/check` sem persistir. Recarregar eliminava o Map. Quatro testes RED demonstraram perda de estado, ausência de carga após restart, erro de persistência não reportado e store malformado aceito.

## Correção publicada

- `/var/lib/mgs-router/domain-checks.json` guarda a última observação por host: host, verified, message, checked_at. Gravação atômica, permissão0600, privada e fora do Git.
- Startup carrega/valida o store; erro ou registro inválido falha fechado. Falha ao gravar retornaHTTP500 sem alegar sucesso persistido.
- `/api/domains` autenticado inclui `checks`; UI reidrata o Map ao abrir/recarregar. Estado compartilhado por Rodolfo/Geizian e preservado após restart do Router.
- Botão Verificar continua executando DNS público+HTTPS real, sem redirects, com challenge novo e prova HMAC de que o host chega a este Router. Origem, CSRF e proteção contra SSRF mantidas.
- Verde salvo não é monitoramento contínuo. UI mostra horário da última verificação e informa que o resultado é salvo; novo clique consulta online novamente e substitui sucesso/falha antigos.

## Validação real

- 46 testes Go passaram, incluindo Chromium local, regressões positivas/negativas de persistência, storage error e malformed store; race, vet, JS e build aprovados.
- Chromium público nas contas rodolfo/geizian verificou online, recarregou e manteve estado; zero errosJS e overflow mobile.
- Após restart real exclusivo do Router, as duas contas consultaram API e receberam os mesmos resultados verdes/timestamps sem reexecutar a consulta online.
- `card.wantabrand.com` e `tarjeta.wantabrand.com`: resultados verdes reais e persistentes.
- Todas as41 rotas Wantabrand tiveram GET+HEAD,82 requests,zero falhas; destinos,raw query,privacy headers preservados.
- Hashes de rotas/domínios/usuários/unidade e PIDs Zeus/Atena/Ares permaneceram iguais. Nenhuma mudançaDNS ou na migração dos onze sites.
- Backup binário+estado anterior validado: `/root/.local/share/mgs-router-rollbacks/1556022368042876989/`.
- Receipt: `data/mgs-router-domain-check-persistence-receipt.json`; QA público: `data/mgs-router-public-validation.json`.

## Separação da migração

A fonte Keitaro já foi recuperada/salva completamente. A migração dos onze sites continua no checkpoint `mgs-router-keitaro-11-domains-20261003`, bloqueada pela fidelidade dos pesos fracionários e pelas duas configurações defeituosas anteriores da origem; esta correção de UI não significa importação ou cutover.
