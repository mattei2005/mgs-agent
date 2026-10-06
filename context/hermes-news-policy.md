# Hermes News — política de anúncios MGS

- Status: ativo; autoridade Rodolfo Mattei, mensagem `1556908630278803478`, thread `1556907799626260531`.
- Fonte técnica: `scripts/monitor-hermes-updates.sh` → `scripts/mgs_hermes_release_monitor.py`.
- Canal: `#alerts-hermes-news`, ID `1505609056771899644`.

## Regra ativa

Anunciar uma única vez cada nova release oficial publicada do Hermes. Validar metadata oficial GitHub (`draft=false`, `prerelease=false`) e rejeitar RC/canary/alpha/beta. Deduplicar pela versão e SHA da release, não pelo avanço do main nem por alterações do runtime MGS.

O avanço comum do `main` continua medido no state para consulta; não gera alerta recorrente. A frequência de verificação existente é preservada. Na adoção/migração, a última release já conhecida vira baseline silenciosa, sem reanunciar histórico.

A fonte do resumo é a nova release: notas oficiais e delta desde a release anteriormente anunciada. Não repetir o acumulado desde o runtime como se fossem novidades do aviso. O explicador entrega PT-BR com mudanças relevantes, impacto prático e necessidade de ação. Não inferir que um recurso disponível já está configurado ou utilizado na MGS. Se o conteúdo for insuficiente ou a geração contextual falhar, explicitar a lacuna.

Entrega usa estado/outbox persistido, nonce estável, ID aceito preservado e readback exato. Falha de GET após POST não autoriza repost. Resultado ambíguo exige reconciliação, nunca retry cego. Produtor e watchdog reconhecem o mesmo contrato `Hermes Agent — nova versão oficial`.

## Limites e supersessão

Esta decisão substitui a política anterior de avisar cada avanço do `main`. Ela altera somente notificações: **“atualizar tudo” continua significando alcançar o main oficial**, no fluxo autorizado com backup, patches, rollback e validação. Release oficial, runtime RC/canary, pendência de main e progresso desde último aviso continuam sendo fatos separados.

O monitor não instala, configura ou reinicia Hermes. Não exclui mensagens históricas do canal. Anúncios externos legítimos continuam recebendo explicação; esta política trata a geração recorrente do monitor Git MGS.
