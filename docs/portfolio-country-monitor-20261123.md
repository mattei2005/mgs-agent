# Cloudflare — monitor de países do portfólio por 30 dias

## Autoridade e escopo

- Solicitante: santosoliv_dev_br (`963808102891798649`), Full técnico no infra-dev e threads, conforme `data/authorized-users.json`.
- Origem: thread `1574415087257780367`, pedido `1574524021737783399`, corte confirmado em `1574524345575809116`.
- Executor único: Zeus. Somente leitura Cloudflare; nenhuma alteração de DNS, WAF, WordPress, servidores ou credenciais. Monitor Vagaaqui existente preservado.
- Coorte congelada em `data/portfolio-country-monitor-20261123/selection.json`: **38 domínios** do ranking publicado, estritamente acima de 1.000 requisições estimadas entre `2026-11-22T13:15:00Z` e `2026-11-23T13:15:00Z`. Mínimo selecionado: 1.044. Não é filtro que reescolhe sites diariamente.
- Preservados exatamente os subdomínios corporativos usados naquele ranking: 114 hostnames literais, incluindo variantes www. Sem somar a zona inteira indiscriminadamente. Domínios sem dados de Analytics não recebem zero e não entram por suposição.

## Período e métricas

- Início: `2026-11-23T20:42:31Z`; fim exclusivo: `2026-12-23T20:42:31Z`.
- Exatamente 30 períodos contíguos de 24 horas, sem sobreposição. Não usar mês calendário nem 31 fatias civis parciais neste contrato.
- Dataset `httpRequestsAdaptiveGroups`, `requestSource=eyeball`, hostnames literais e agrupamento `clientCountryName`.
- `count` é a estimativa fornecida pela Cloudflare; não multiplicar por `sampleInterval`. País deriva do IP e pode refletir VPN/proxy. Requisições incluem páginas, arquivos, bots e acessos bloqueados; não são pessoas, visitas ou sessões.
- Settings são conferidos na mesma consulta de cada site: enabled, maxDuration e notOlderThan. HTTP200 com errors/data:null é falha, nunca tráfego zero. Categorias XX/T1 e todos os países ficam no agregado persistido.
- Referência inicial: 24 horas anteriores ao início, salva separadamente em `initial-reference.json`; não entra no acumulado final.

## Agenda e continuidade

- Runner: `/usr/bin/python3 /root/mgs-agent/scripts/monitor-portfolio-country.py`.
- Entradas: `52 0-5,7-23 * * *` e `2 6 * * *`, America/New_York, stagger +25s, timeout externo600s, orçamento interno420s. Uma verificação por hora civil, publicação só quando houver intervalo fechado há3h.
- Exceção das06h evita a manutenção mensal do host às06:52 do dia1. Não classificar todos os jobs densos como baseline: detectores SB e intake de criativos são operacionais. Preflight atual, timezone declarado, virada de mês e janela final ficam no diretório de estado. O primeiro candidato foi substituído antes de qualquer instalação.
- Boletim normal: por volta de `23:52 UTC` / `20:52 Brasília`, a partir de24/11. Fechamento final após23/12, no mesmo slot quando o provedor e transporte responderem normalmente.
- Locks: `/var/lock/monitor-portfolio-country.lock` no wrapper e `data/portfolio-country-monitor-20261123/writer.lock` no processo; estado separado de Vagaaqui. Mesma credencial Cloudflare existente, uma leitura somente por etapa de coleta com sites faltantes; nenhum acesso 1Password quando não houver coleta.
- Os wrappers já existentes de Service Account e transporte Discord são usados, sem guardar segredos. Nenhum browser ou writer de origem é usado. Finance long-poll e demais dispatchers registrados não compartilham este state/lock/arquivo/recurso.
- A coleta salva cada site antes de seguir. Interrupção retoma somente os sites faltantes. Estouro do orçamento rende controle ao consumidor seguinte sem perder o progresso. Três tentativas limitadas em falha transitória com backoff; Retry-After longo fica persistido, não é ignorado.
- Auth/credenciais ou cinco ciclos consecutivos falhos bloqueiam chamadas e mantêm pendência com próximo passo na origem. Lacunas não são zero nem fechamento completo. Recuperação só é declarada depois da coleta e entrega faltantes, não ao apenas avançar parte do lote.

## Publicação e encerramento

- Um boletim consolidado por dia em **cinco partes**, oito sites por parte exceto a última. Cada site mostra top10 países/categorias, contagem e percentual; demais categorias são agrupadas em Outros. Distribuição completa continua no estado agregado local, sem IPs, cookies ou identificadores pessoais.
- Referência inicial e fechamento final também têm cinco partes. Content vazio, embeds sem mentions; nunca criar outra thread.
- Outbox persistida antes de POST; nonce estável/enforce_nonce. POST ambíguo exige varrer a janela temporal com paginação e conferir marcador/autor antes de reenviar. GET exato valida destino, autor, content, campos e ausência de mentions.
- Fechamento só ocorre depois de30/30 períodos para38/38 domínios, todos com entrega verificada. Estado completed torna ticks posteriores inertes: sem Cloudflare, 1Password, Discord ou republicação. Entradas permanecem instaladas como no-op para preservar histórico; sua retirada futura é manutenção separada.
- Dependência de código: funções normalize/aggregate e transporte do módulo existente `monitor-vagaaqui-country.py`, importado como instância privada com destino separado. O script e monitor original não foram editados.

## Testes e rollback

- `python3 tests/test_portfolio_country_monitor.py -v`: fixtures offline para duração, cohort/filtros, amostragem, limites de payload, coleta parcial, dedupe, GET exato, authz, Retry-After, cinco falhas e término sem novas consultas.
- `python3 tests/test_vagaaqui_country_monitor.py -v`: regressão do módulo reutilizado, incluindo poster real com endpoint HTTP mock local.
- Preflight real em38/38 domínios; ativação com cinco recibos GET e primeiro tick cron real documentados em `validation.json`.
- Backup do crontab em `backups/portfolio-country-monitor-20261123/root-crontab.before` e candidato validado com crontab -n. Suspensão deve retirar apenas o bloco marcado `MGS PORTFOLIO COUNTRY MONITOR`, preservando mudanças concorrentes e todos os recibos. Não restaurar o crontab inteiro antigo.
