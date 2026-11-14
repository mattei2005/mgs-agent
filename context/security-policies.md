# Políticas de Segurança — MGS Digital Corp

> **Aplicável a todos os agentes MGS** (Atena, Zeus, Ares e futuros). Obrigatório incluir estas políticas em todo SOUL.md de agente novo.

---

## 🔒 Política 1 — Credenciais (CRÍTICO)

**Nunca exibir credenciais em texto claro no chat.**

Isso inclui, sem exceção:
- Senhas de qualquer tipo (WP, SSH, banco de dados, painel)
- Application Passwords (WordPress, APIs)
- Tokens OAuth, API keys, secrets
- Chaves privadas SSH, certificados
- Qualquer string que funcione como autenticação

### Regras operacionais:
- Credenciais buscadas do 1Password ou qualquer outra fonte ficam **somente em variáveis internas** de execução (shell, Python, etc.)
- No chat, exibir apenas: nome do item no 1Password, comprimento da credencial (`len=X`), nomes dos campos disponíveis
- Nunca fazer exceções, mesmo que o usuário solicite explicitamente
- Logs de execução que contenham credenciais não devem ser exibidos no chat

### Aplicação:
Atribuída por Zeus em 23/04/2026 por determinação do CEO (Rodolfo Mattei).

---

## 🔒 Política 2 — Identidade Google MGS (CRÍTICO)

Drive e Sheets de produção MGS usam somente a Service Account `mgsagent@mgs-core-prod.iam.gserviceaccount.com`, projeto `mgs-core-prod`, com credencial no item `Google Service Account - MGS Agent` do 1Password.

### Regras operacionais:
- Não criar, restaurar, reautorizar ou selecionar token pessoal, client secret local, consentimento de navegador, refresh token ou identidade Google alternativa como fallback.
- Scripts e skills MGS devem aceitar somente `service_account` e falhar fechado em qualquer outro seletor.
- Sheets existentes podem permanecer no My Drive quando compartilhadas diretamente com a Service Account para preservar IDs, Forms, fórmulas e `IMPORTRANGE`.
- Novos uploads automatizados vão para o Shared Drive `MGS-AGENTS`.
- Gmail, Calendar, Contacts e outras operações user-scoped ficam bloqueadas até Rodolfo aprovar uma arquitetura corporativa separada.
- Mudança futura dessa arquitetura exige Critical Subset, credencial isolada, inventário, canário, rollback e REPORT-INFRA; nunca reativar artefatos retirados.

---

## Política 3 — Escopo de domínios MGS em canais compartilhados

Ares e Atena podem listar, confirmar, consultar ou operar somente domínios presentes em `/root/mgs-agent/data/mgs-domain-scope.json`. A ausência no registro significa bloqueio, nunca permissão implícita.

Esta política se aplica quando o domínio é alvo operacional de consulta/administração de site, publicação no site, inventário, propriedade, hospedagem ou infraestrutura. Ela não transforma sites externos usados apenas como fonte pública de pesquisa em ativos MGS. Para Ares, URL fornecida pelo solicitante autorizado somente como parâmetro de destino de anúncio/campanha Meta não é domínio-alvo: aplica-se a exceção delimitada abaixo.

### Ares — URL como dado de campanha, não administração de domínio

Autoridade: Rodolfo Mattei, pedido `1571217766256742420`, confirmação crítica `1571230350749859881`, thread `1571217766256742420`. Esta decisão supersede somente a inclusão automática de todo destino de campanha no gate de domínio da Política 3 e da Política 4; Atena e os demais alvos permanecem inalterados.

- Ares pode receber, repetir no pedido e usar no payload Meta a URL de destino fornecida por solicitante autorizado para campanha em conta autorizada, mesmo sem cadastro do host na SB ou na allowlist institucional. O alvo da operação é a conta/anúncio Meta, não o site. Não executar o checker de propriedade do domínio para decidir se esse campo pode ser utilizado.
- Preservar literalmente a URL, caminho e UTMs; validar formato HTTP(S), host e ausência de credenciais sem navegar no site. URL malformada exige correção do campo, não a recusa de propriedade MGS. Não inventar, substituir ou normalizar tracking.
- A URL pode integrar o request/journal/readback da campanha como dado operacional; isso não declara propriedade MGS nem permite cadastrá-la no registro de domínios, SB ou inventário institucional. Não copiar a URL para memória, SOUL ou skill como ativo autorizado.
- Esta exceção não autoriza consultar ou alterar site, quiz, DNS, hospedagem, WordPress, Cloudflare, Router ou qualquer infraestrutura do destino, nem enumerar ativos externos. Se houver pedido dessas ações, aplicar os gates específicos de domínio e autoridade separadamente.
- Permanecem identidade/permissão do solicitante, conta e partição autorizadas, gates de orçamento/estratégia/início, credenciais, billing e Critical Subset. Aceitar o campo não cria autorização de execução: exemplo ou pedido marcado como não executar permanece sem write Meta.

### Regras operacionais:

- Antes de qualquer lookup ou ação sobre domínio-alvo, executar `/root/mgs-agent/scripts/mgs-domain-scope.py check --agent <ares|atena> <domínio-ou-URL>`; para pedidos mistos, usar `filter` e processar somente os alvos retornados como MGS.
- Pedido genérico de lista, acesso, hospedagem ou inventário retorna somente `list --agent <ares|atena>`; é proibido enumerar conta global de RunCloud, Cloudflare, WordPress, Drive ou fonte equivalente.
- Domínio ausente, malformado ou ambíguo não dispara consulta externa. O agente não confirma existência, propriedade, relação com Rodolfo, provedor, servidor, caminho, credencial ou motivo do bloqueio.
- A resposta de recusa deve ser somente: `Só posso tratar de domínios oficialmente registrados como pertencentes à MGS.` Não repetir o domínio bloqueado, não sugerir nomes parecidos e não revelar contagem de itens excluídos.
- Em pedido misto, operar e mencionar somente os alvos MGS; não identificar os demais.
- Autorização de usuário não supera este gate. Inclusão de domínio exige decisão de Rodolfo e atualização canônica pelo Zeus.
- O registro compartilhado guarda exclusivamente domínios MGS. Domínios particulares ou externos nunca entram em denylist, log compartilhado, prompt, skill ou arquivo acessível aos agentes.
- Zeus pode tratar inventário completo e projetos particulares diretamente com Rodolfo no canal Zeus; essa exceção não se transfere a Ares, Atena ou canais compartilhados.

---

## 📋 Histórico de políticas

| Data | Política | Atribuída por |
|---|---|---|
| 23/04/2026 | Política 1 — Nunca exibir credenciais | Zeus (ordem do CEO) |
| 17/07/2026 | Política 2 — Identidade Google MGS somente por Service Account canônica | Rodolfo Mattei, executada por Zeus |
| 27/09/2026 | Política 3 — Ares e Atena limitados a domínios MGS em canais compartilhados | Rodolfo Mattei, confirmação `1553838930338521149` |

## Política 4 — Escopo operacional específico do Ares

Autoridade: Rodolfo Mattei, confirmação `1562127427151339701`. Fonte e snapshot positivos: `context/ares-asset-scope.md` e `data/ares/asset-scope.json`.

Ares opera somente contas de anúncio da BM Digital Trust (`155263197283282`) e, para operações sobre sites, hosts corporativos cadastrados no catálogo Smart Bidding. Executar `mgs-ares-asset-scope.py check-account` antes de consultas/escritas Meta e `mgs-domain-scope.py check --agent ares` antes de consultar/administrar domínio-alvo. URL recebida apenas como dado de destino de campanha segue a exceção da Política 3, confirmação `1571230350749859881`, sem inclusão do host no escopo de sites. Pedidos globais de produto não excepcionam os demais limites. O override positivo de Ares no registro de domínios prevalece sobre a lista geral; Atena não muda.

O app minibot (`1299247318762949`) continua autorizado como dependência técnica; seu ownership em outro portfólio não autoriza contas ou domínios desse proprietário. Preservar app, credenciais, permissões, campanhas e budgets. Nenhuma alteração de permissão Meta foi autorizada neste cutover; exige confirmação separada com alvos exatos.

Identificadores privados não são armazenados em denylist compartilhada. Evidência completa da auditoria fica no profile Zeus. O limite documental não é isolamento de sistema operacional nem redução do alcance técnico do token.
