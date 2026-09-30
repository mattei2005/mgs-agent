# Correção de conflito ao salvar cobranças da despesa

Autoridade: Rodolfo `1554689121836859475`, esclarecimento `1554689227017682967`, thread `1545426987756298340`.

## Resultado verificado

Correção publicada por `finance_release.py` em `public/app.js`; regressões persistidas em `tests/expense-sort.test.mjs`. Não houve gravação financeira de produção, alteração de câmbio, valores, permissões ou planilha. O usuário ainda precisa carregar a nova interface e salvar sua edição.

- SMS Funnel `company|121`, setembro2026: valor de origem preservado em95.000BRL. As três datas ainda não foram gravadas pelo agente.
- O backend exigia a revisão global exata; a rotina automática de câmbio avançava essa revisão enquanto o formulário permanecia aberto. Auditoria produtiva observada: `AUTO_QUOTES_UPDATED`2518, após operações do usuário2515–2517. Reproduzido HTTP409 no formulário anterior a partir do snapshot produtivo831, sem mutação produtiva.
- A interface agora compara a despesa aberta com sua versão atual antes de enviar. Atualizações não relacionadas, como a conversão cambial, não impedem salvar a despesa intacta. Alteração concorrente da mesma despesa continua bloqueada e mantém o rascunho.
- O backend, CAS transacional, recálculo, autenticação e permissões permanecem inalterados. Uma corrida entre a consulta e o POST admite somente um retry de409 conhecido, com nova comparação. Erros ambíguos não são reenviados automaticamente.

## Evidência

Diretório privado: `apps/finance-system/private/expense-conflict-1554689121836859475/`.

- TDD: três testes novos falharam antes da implementação; depois passaram. Gate integral:220Node +178Python =398 testes, sem skips. Dependências: zero vulnerabilidades reportadas.
- Stage real em banco isolado: desktop1440 e mobile390;01/09/2026=30.000,14/09/2026=35.000,24/09/2026=30.000; total95.000BRL; conferência30/09/2026. Dois POSTs no caso de corrida controlada, apenas uma gravação confirmada. Conflito da própria despesa e esgotamento de retry preservam os três campos/datas e não sobrescrevem dados concorrentes.
- Primeira execução do ensaio teve falha de harness por reset que reutilizava revisão já cacheada. Corrigido para revisões monotônicas e reexecutado integralmente com sucesso. Não foi necessário alterar o cache produtivo.
- Duas chamadas foreground do gate Python excederam o transporte420s; o gate integral foi concluído em execução silenciosa,483,675602s, exit0, resultado consumido antes da conclusão.
- Publicação coordenada com backups exatos em `private/releases/expense-conflict-1554689121836859475/`; readback dos hashes locais/remotos e comparação de todos os fingerprints financeiros antes/depois: idênticos.
- Browser produtivo autenticado:17meses ×2viewports =34 editores, mais8 verificações das outras telas; cinco consultas de gestores; anônimo401/redirect login; zero errosJS e zeroPOST financeiro. Hash do asset público idêntico ao candidato. Health autenticado produtivo aprovado.
- Procedimento persistido na skill `mgs-finance-dashboard`, referência `current-security-performance-and-dr.md`, seção de recuperação de conflitos em despesas.

## Limites e uso

A aba já aberta do usuário ainda contém o JavaScript antigo; recarregar uma vez é necessário para carregar a correção. Não afirmar recuperação de campos ainda não enviados no navegador remoto. Os valores/datas da captura permitem redigitá-los. Não prometer ausência de todo conflito: uma alteração real na mesma despesa deve continuar pedindo conferência.
