# Consolidar rotas funcionais com histórico preservado

1. Autentique handoff e comando humano por IDs; confirme conta, origem, autoridade e gates. Roteamento não aprova campanha nem retoma request antigo.
2. Faça backup das fontes exatas e preserve gates por comparação semântica integral dos campos não relacionados ao roteamento.
3. Alinhe registry de rotas, consumidor, contratos da operação/engine, prompts de destino, mapa/context, registro institucional e verificadores de configuração. Mantenha contratos/modos distintos mesmo quando compartilham thread_id; selecione só a intenção pedida. Nunca execute ambos por uma colisão de ID.
4. Não edite skills de outro agente sem Critical Subset. Uma skill genérica que já resolve modo pelo contrato pode não precisar de edição.
5. Releia o destino antigo antes de declará-lo retirado. Decisão humana posterior que o reutiliza exige supersessão parcial explícita; preserve o novo dono e coordene um único writer para campos compartilhados.
6. Config vivo/versionado usa writer nativo do Hermes. Strings de prompts devem ser texto, não JSON serializado dentro de YAML. Não passe strings longas por helpers que possam interpretar aspas/escapes como valor literal. Confirme texto parseado igual ao prompt canônico e que só as chaves autorizadas mudaram.
7. Diferencie equivalência semântica de igualdade binária: quebra de linhas/quoting YAML pode variar sem mudar valores. Comprove o diff semântico antes de diagnosticar drift; correção de whitespace deve preservar o documento parseado.
8. Testes verificam rotas funcionais, destino compartilhado intencional e eventual uso novo do destino antigo, não uma hipótese fixa de uma thread por função. Registre falhas preexistentes separadamente; não enfraqueça gates para produzir verde.
9. Feche com validação do sincronizador em modo sem publicação, testes locais, inventário/audit, REPORT-INFRA por embed e GET do ID exato. Notifique o executor da leitura canônica sem sugerir que a sessão já carregou o prompt ou que uma publicação real foi testada.
