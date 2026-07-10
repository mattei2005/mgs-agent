### Limpeza pós-loop de regras persistidas

Se um loop multiagente levou à criação apressada de skills/memórias/regras, tratar como correção operacional, não como aprendizado automático bruto:
- Auditar mudanças recentes em SOUL, skills e memórias dos agentes envolvidos.
- Remover regras amplas do tipo “sempre mencionar Zeus/Atena” em thread compartilhada.
- Consolidar em um único skill guarda-chuva por agente; evitar 2–3 skills estreitas sobre o mesmo incidente.
- Preservar no máximo uma referência concisa do incidente, com política final segura.
- Validar que a regra final diferencia thread compartilhada de cross-channel: em thread, texto simples por padrão; cross-channel pode exigir mention para roteamento.

