# Visualizar como usuário — dashboard financeira

Autoridade: Rodolfo `1558474267975229541`, em resposta à proposta `1558473759181250744`, thread `1545426987756298340`. Finalidade: conferir a tela e os limites reais de cada usuário sem usar sua senha/2FA, nem desativar MFA.

## Contrato aprovado

- Exclusivo ao usuário autenticado `rodolfo`, role `owner`. Usuários ativos `partner` e `manager` podem ser alvo; Rodolfo, usuários desativados/inexistentes e roles desconhecidas não podem.
- Em **Usuários**, botão **Visualizar como este usuário**. A faixa identifica a pessoa e **Somente leitura**, com **Voltar à minha conta**.
- Usar as próprias telas, consultas e regras de permissão do alvo. Não montar uma cópia visual com dados de administrador.
- Todas as mutações de dados, propostas, pagamentos, perfil, credenciais e logout ficam bloqueadas na prévia. As únicas operações próprias do recurso são iniciar/encerrar a visualização e registrar auditoria sob o ator real **Rodolfo**.
- Não criar sessão em nome do alvo, alterar roles/cadastro, redefinir senha/2FA, compartilhar código ou revogar sessões/dispositivos de outras pessoas. A sessão do próprio Rodolfo continua sujeita aos controles normais de MFA, expiração/revogação e CSRF.
- Escopo por aba/requisição, não um cookie global: outra aba de Rodolfo permanece administrativa. Navegação, recarga, mudança de mês e atualização automática preservam o alvo.
- O parâmetro `__preview` e o header `X-MGS-Preview-User` não são credenciais nem concessões: o servidor autentica Rodolfo, relê a identidade ativa do alvo, aplica sua role e bloqueia métodos de escrita. Seletores inválidos/duplicados/divergentes falham fechados. Remover o parâmetro deliberadamente equivale a voltar ao próprio acesso de administrador, não a entrar na conta de outra pessoa.
- A consulta não testa posse da senha/TOTP do alvo: testa sua tela, dados e autorização a partir da sessão administrativa auditada.

## Implementação e validação

Candidato e evidências: `apps/finance-system/private/preview-1558474267975229541/`. Código em `auth.mjs`, `server.mjs`, `public/navigation.js`, `public/navigation.css` e `public/operations.js`; regressões em `tests/auth.test.mjs` e `tests/navigation-profile.test.mjs`.

Início e retorno usam POST próprio com Origin/CSRF; consultas seguem os endpoints existentes. Eventos `PREVIEW_STARTED`, `PREVIEW_VIEWED` e `PREVIEW_ENDED` registram alvo, somente leitura e ator Rodolfo. Esses eventos não invalidam a versão financeira de atualização automática. Filtros/caches continuam conforme as versões mensais existentes.

Aceitação exige gates Node/Python completos; paridade de respostas alvo versus prévia em banco isolado; seis alvos em desktop/mobile; retorno e isolamento de abas; bloqueio de APIs/métodos, alvo desativado e sessão revogada; backup exato, publication journal, hashes remotos e verificação financeira/segurança em produção.

**Estado:** candidato validado em testes focados e stage; publicação/gates integrais ainda em andamento. A conclusão deve ser resolvida pelo checkpoint `ZEUS-FINANCE-PREVIEW-1558474267975229541` e pelo relatório `reports/finance-preview-1558474267975229541.md`, quando publicado. Não inferir disponibilidade produtiva a partir desta autorização.
