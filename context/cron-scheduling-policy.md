# MGS OS — Política Global de Agendamento de Crons

> Status: canônico v1.0  
> Dono executivo: Rodolfo Mattei  
> Orquestração técnica: Zeus  
> Aplicação: todos os agentes, profiles e schedulers MGS

## 1. Regra central

Antes de criar ou alterar qualquer cron, o agente responsável deve inventariar os agendamentos habilitados de todos os agentes e escolher um minuto de início que não coincida com outro job agendável existente.

A regra independe de quem pediu, de qual agente executa e de qual scheduler será usado.

## 2. Inventário obrigatório

O preflight deve consultar, no mínimo:

- root crontab;
- `/etc/crontab` e `/etc/cron.d/`;
- systemd timers;
- jobs Hermes de todos os profiles operacionais;
- schedulers próprios registrados em contratos/data;
- duração, lock, conta/API, destino e recurso compartilhado dos jobs relevantes.

Normalizar todos os horários para o timezone do job e expandir as próximas oito datas civis para detectar colisões reais de dia/hora/minuto.

## 3. Alocação do minuto

1. Colisão de início com outro job agendável bloqueia o write.
2. Escolher o minuto livre mais próximo que preserve a cadência e a intenção operacional pedidas.
3. Nunca mudar silenciosamente frequência, período de referência ou checkpoint apenas para abrir espaço.
4. Se não existir minuto livre compatível, apresentar o conflito e obter uma alternativa antes de criar o cron.
5. Separar o minuto não substitui `flock`, lease, idempotência, timeout, quota ou reconciliação.

## 4. Baselines contínuas e densas

Jobs `* * * * *`, watchdogs contínuos e schedules densos de infraestrutura (por exemplo, a cada 3/5/9/15 minutos) podem, em conjunto, ocupar todos os 60 resíduos de minuto. O inventário MGS de 31/08/2026 confirmou que não existe minuto absolutamente vazio quando essas baselines são somadas.

Eles são baseline excepcional e obrigatória no relatório de colisão. A exceção não permite colisão silenciosa com outro job operacional. Um novo cron ainda deve:

- ter zero colisão com outro job operacional/agendável fora das baselines densas;
- usar o minuto com menor contenção de baseline quando nenhum minuto absolutamente livre existir;
- provar que não disputa o mesmo lock, arquivo, conta, API, browser, state ou writer;
- possuir lock/lease próprio quando houver risco de sobreposição;
- registrar no audit quais baselines inevitáveis coincidem;
- não adotar frequência a cada minuto ou outra cadência densa sem necessidade explícita, aprovação operacional e isolamento comprovado.

## 5. Write seguro e readback

Fluxo obrigatório:

```text
inventário global
→ expansão das agendas
→ análise de minuto + duração + recurso
→ seleção do minuto livre
→ dry-run/preflight
→ backup do scheduler aplicável
→ write único
→ readback exato do schedule/enabled/runner/delivery
→ nova auditoria global de colisão
→ inventário + REPORT-INFRA
```

Em crontab, preservar a regra de segurança vigente: backup → arquivo temporário → validação → diff → aplicação. Nunca usar heredoc dentro de command substitution enviado ao `crontab`.

## 6. Critério de conclusão

Um cron só está criado/alterado quando:

- o minuto de início está livre entre jobs agendáveis;
- baselines contínuas e recursos compartilhados foram avaliados;
- frequência, timezone e semântica permanecem corretos;
- lock/idempotência/recovery estão definidos quando aplicáveis;
- o scheduler confirma o estado por readback;
- a auditoria pós-write não encontra nova colisão;
- a mudança foi inventariada e reportada.
