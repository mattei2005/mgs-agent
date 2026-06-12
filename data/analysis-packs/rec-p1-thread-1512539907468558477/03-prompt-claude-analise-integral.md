# Prompt para Claude externo — análise integral REC/P1 sem resumo

Você vai analisar o fluxo REC/P1 da Atena/MGS. Regra crítica: NÃO faça resumo genérico. Trabalhe com reconstrução integral e rastreável.

Entrada que você deve receber junto deste prompt:
1. Transcrição integral da thread Discord `1512539907468558477`, com mensagens numeradas `MSG XXX`.
2. Lista de arquivos obrigatórios e inventário de arquivos da operação.
3. Conteúdo integral dos arquivos obrigatórios quando fornecido.

Tarefa:
- Reconstruir o fluxo REC e P1 passo a passo, desde o pedido natural do Rodolfo até publicação/validação/report final.
- Separar REC de P1 e depois mostrar onde eles se encontram.
- Listar exatamente quais arquivos a Atena precisa ler, em que ordem, e por quê.
- Identificar regras que pertencem ao SOUL, à SKILL, aos contracts, aos templates, aos scripts e às references.
- Apontar contradições entre thread, arquivos e implementação.
- Não inventar etapa. Toda afirmação operacional deve citar `MSG XXX` ou path de arquivo.
- Onde faltar evidência, escrever `LACUNA`.
- Produzir uma especificação implementável para Atena, não um resumo.

Formato obrigatório de saída:
1. Mapa de fontes lidas
2. Linha do tempo detalhada por `MSG XXX`
3. Fluxo REC detalhado
4. Fluxo P1 detalhado
5. Handoff REC→P1
6. Arquivos obrigatórios por etapa
7. Regras que devem virar SOUL/SKILL/contract/template/script/reference
8. Gates de qualidade e validação
9. Riscos de perda de regra se a thread virar só resumo
10. Plano de implementação com checklist verificável
