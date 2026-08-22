# MGS Honcho Memory Standard

> Status: decisão canônica aprovada
> Dono executivo: Rodolfo Mattei
> Vigência: 2026-07-17
> Origem: Discord thread `1527558141397700618`, mensagem `1527673289781153803`

## Decisão

Honcho deve ser integrado nativamente a todos os agentes MGS atuais e futuros como camada de memória entre sessões, perfil do usuário e conclusões derivadas.

A integração deve usar o memory provider nativo do Hermes, e não apenas um copilot externo ou execução manual sob demanda.

## Papel e precedência

Honcho é uma camada de contexto, recuperação semântica e hipóteses. Ele não substitui as fontes canônicas MGS.

A precedência permanece:

1. runtime, APIs, bancos e dashboards para estado real;
2. MGS OS, registros e dados canônicos para política, ownership e decisões;
3. audit/Git para rastreabilidade;
4. USER/MEMORY como cache pequeno e sempre ativo;
5. Honcho para continuidade, perfil, contexto e conclusões que ainda exigem validação antes de ação operacional.

Credenciais nunca são memória e permanecem exclusivamente no 1Password.

## Escopo

A regra cobre Zeus, Atena, Ares e todo novo agente MGS. Cada agente deve manter peer/perfil isolado e receber apenas o contexto compatível com sua função e seus usuários autorizados.

## Relação com USER/MEMORY

USER/MEMORY continuam sempre ativos e limitados a preferências e invariantes que precisam estar presentes em todo turno. Honcho atua diretamente sobre o perfil do usuário a partir das conversas persistidas e absorve a pressão de crescimento causada por histórico, contexto longitudinal e conclusões derivadas.

Com Honcho nativo ativo, a modelagem automática pós-turno pertence exclusivamente ao Honcho. `memory.nudge_interval` permanece `0` em Zeus, Atena e Ares: o background review automático continua aprendendo procedimentos em skills, mas não grava USER.md/MEMORY.md. O runtime também remove mecanicamente o tool `memory` de reviews skill-only, impedindo gravação acidental. Gravações foreground explícitas continuam permitidas; um `add` bem-sucedido no alvo `user` também é espelhado como conclusão Honcho. USER/MEMORY permanecem a camada exata, pequena e sempre ativa; Honcho é a camada longitudinal e semântica.

O autocompactor de USER/MEMORY deixa de ser a solução principal e passa a ser somente proteção residual para gravações foreground excepcionais. A cada dez minutos, o monitor descobre os profiles operacionais, mede USER/MEMORY e, quando um store atinge 90%, aciona compactação fail-closed para alvo preferencial de 89% sem pedir aprovação por ocorrência. Cada entrada aceita exige restauração determinística de literais e verificação semântica independente; não existe terceiro veredito global redundante. Cada aplicação exige backup protegido, lock, escrita atômica, rollback/readback e relatório metadata-only em `#limites-90`. Falha de modelo, JSON, semântica, timeout ou concorrência preserva a fonte e gera alerta com anti-spam; nenhum conteúdo de memória vai ao Discord. O monitor de pending writes não duplica alertas de capacidade nem cria propostas zero por padrão.

Artefatos canônicos:

- monitor: `scripts/monitor-hermes-memory-capacity.py`;
- compactor: `scripts/hermes-memory-autocompactor.py`;
- estado: `data/hermes-memory-capacity-state.json`;
- cron: `4,14,24,34,44,54 * * * *`, protegido por `flock`;
- backup: `/root/.hermes/secure-backups/memory-autocompaction/`;
- canal: `#limites-90` (`1527401973698007060`).

## Estado verificado na decisão

Em 2026-07-17, os profiles operacionais (`zeus`, `atena`, `ares`) foram migrados para o provider Honcho nativo após o baseline inicial sem `memory.provider`.

## Gate de implantação

A decisão de integrar todos os agentes e usar Honcho managed com persistência das conversas operacionais foi confirmada por Rodolfo em 2026-07-17. Isso não autoriza o envio de credenciais nem altera a precedência das fontes canônicas.

A implantação ocorre por agente, com backup, configuração nativa, isolamento de peer, orçamento de contexto, canário real, rollback e readback. A chave permanece protegida nos ambientes locais dos profiles e nunca entra em Git, logs ou chat.
