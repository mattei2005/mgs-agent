# Exceção pública de autoria — implementação e QA escopados

Use somente após decisão humana específica para alterar a proteção de autoria, preservando a fonte canônica de autoridade. Acesso técnico, publicação editorial ou aprovação de cache não autorizam desligar hardening. Não ampliar para outros autores, paginação, aliases, métodos ou parâmetros fora da lista literal aprovada.

## Preflight e bytes

1. Antes de delimitar a exceção, levante os links nativos de paginação e o conjunto de artigos do autor; inclua no plano o percurso completo necessário ao pedido, em vez de descobrir uma segunda rota só depois da implantação. Exija escopo humano explícito para esse conjunto finito, sem wildcard para autores ou páginas futuras. Confira a mensagem humana real, a lista exata de URLs/autor/métodos e os dois caminhos de implementação/estágio/rollback. Resolva domínio, instalação, owner, ausência de symlink e estado anterior; se houver intent/arquivo inesperado, reconcilie sem sobrescrever/repetir.
2. Leia o método e o hook efetivamente registrados do fornecedor, versão, prioridade, valor salvo/efetivo e SHA do arquivo. A exceção deve remover somente o callback conhecido da memória daquela requisição após guards completos; não alterar a opção, chamar save de segurança ou desativar o plugin globalmente.
3. Teste o código contra o método capturado e doubles declarados, com positivos e negativos. Preservar os artefatos anteriores e registrar supersessão de hash/expectativa quando um safeguard precisar de revisão; teste local não comprova produção.

## Cache e reversibilidade

- Investigue cache antes do deploy. Um novo HTML200 de autoria pode ser servido antes dos hooks em requisições posteriores, quebrando guards de query e rollback. Não aceite ausência anterior de cache403 como prova de que a página liberada não será armazenada.
- Inspecione a API request-local de exclusão do cache instalado e seus callbacks. Na versão WPFC verificada, `wpfc_exclude_current_page()` define um marcador que faz o callback retornar sem gerar o arquivo; não é purge. `DONOTCACHEPAGE` isolado não é garantia universal: a implementação examinada só o respeita em situações específicas.
- Quando necessário à exceção aprovada, use exclusão request-local e headers `no-store` somente no alvo admitido, sem alterar opções globais ou excluir cache. Exija que desktop/mobile permaneçam sem cópia em disco e que queries/métodos/rotas negativas não obtenham acesso novo. Se os headers/cache forem alterados no candidato, o teste positivo deve exigir o novo comportamento, preservando os controles negativos.
- Confira o PHP-FPM real do aplicativo pelo pool/socket/include escopados; CLI pode usar outra versão. Leia a cadeia de configuração e o SAPI FPM para timestamp/revalidação do OPcache, sem inferir pelo CLI, publicar phpinfo ou alterar /etc/reiniciar. O resultado HTTP da origem e da borda ainda precisa provar que os bytes novos são executados.

## Escrita controlada e aceite

1. Sob executor único, crie o arquivo de estágio não executável pelo loader com exclusividade/no-follow, owner/modo previstos, bytes/hash validados e fsync. Faça lint com o PHP do aplicativo. Renomeie atomicamente dentro do mesmo diretório somente após conferir estado/hash anterior do alvo; registre intenção/recibo e ausência do estágio. Não usar escrita truncante como se fosse atômica.
2. Prepare rollback pelos bytes inertes no mesmo alvo e pelo mesmo estágio aprovado, sem remover arquivo/diretório ou restaurar opções globais. Não declare rollback produtivo testado se só houve lint/harness ou se não foi acionado.
3. Exija GET/HEAD normais sem login/query na origem e no público, nome/biografia nativos, canonical e desktop/mobile. Compare estados nativos protegidos e fornecedor/opção/hooks antes/depois.
4. Compare negativos reais com o baseline, sem impor403 quando o mecanismo já retorna404/redirect. Inclua enumeração, REST/users, outro autor real, queries de tracking/autor, paginação/feed e métodos fora da allowlist; não siga redirects para classificar bypass.
5. Inspecione a navegação visível e exercite os links reais de ida/volta. Confira em código que a união dos artigos nas páginas aprovadas corresponde ao conjunto nativo esperado, sem duplicatas ou lacunas, nos dois perfis de viewport. Se uma paginação continua bloqueada por exclusão explícita do contrato, registre e informe a limitação; não libere silenciosamente a rota nem declare o arquivo inteiro irrestrito. Ao completar uma paginação autorizada, use allowlist de caminho e valor nativo de `paged` coerentes; mantenha autor/host/métodos/query e demais negativos protegidos. O rollback dessa extensão deve restaurar a versão anterior que já funcionava na página-base, não desativar toda a correção.

## Continuidade

Registre aprovação, revision/hash efetivos, recibo, provas e limites na fonte canônica da tarefa e no checkpoint. Reporte o escopo real e os efeitos verificados, não promessa de imunidade a mudanças futuras do plugin. Uma mudança do fornecedor invalida a revisão e deve falhar fechada até nova comprovação; não remova pins para manter a aparência de sucesso.
