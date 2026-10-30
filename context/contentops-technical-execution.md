# ContentOps — execução técnica autônoma

Status: ativo; aplicação da autoridade ContentOps já vigente, sem grant global novo.
Dono: Rodolfo Mattei. Executor: Atena. Fonte humana: mensagem `1565746078425423954`, thread `1565555821188878377`.
Fonte de autoridade: `data/atena/editorial-manager-authority.json`; Critical Subset e exclusões continuam em `AGENT.md` e `context/permissions-matrix.md`.

## Resultado esperado

Atena usa diretamente os meios técnicos já autorizados e disponíveis para entregar o pedido editorial completo. Não tratar terminal, API, 1Password, SSH/WP-CLI ou acesso administrativo canônico como ferramentas exclusivas de Zeus. Não pedir aprovação de Zeus para descobrir referências, testar acesso em leitura, preparar código local ou executar uma etapa não crítica já coberta pelo pedido. Uma falta de receita exige pesquisa/preparação, não transferência automática do trabalho.

Isso não concede acesso a todos os ativos da empresa, identidade não autorizada, finanças/Router, infraestrutura global ou nova credencial. Uma autorização de uso não prova capacidade técnica inexistente nem dispensa uma confirmação crítica realmente aplicável.

## Ferramenta pronta: preflight de acesso WordPress

Executar pelo terminal da própria Atena, para um domínio literal já aceito pelo gate:

```
python3 /root/mgs-agent/scripts/mgs-contentops-preflight.py --domain DOMINIO_EXATO
```

O helper:
- verifica primeiro o gate de domínio da Atena;
- resolve somente o item canônico `Wordpress - DOMINIO_EXATO` no cofre corporativo pelo wrapper `/root/mgs-agent/scripts/mgs-op-with-service-account.sh`;
- usa as referências existentes, sem copiar segredos entre perfis nem alterar usuário/role;
- reconhece os campos REST cadastrados, compõe a base sem duplicar `/wp/v2` e faz somente GET;
- retorna HTTP, papel, capacidades e estado dos componentes de manutenção, sem senha/token/cookie;
- falha fechado para item ausente/ambíguo, origem divergente, credencial REST ausente ou resposta não verificável.

O resultado `administrator` comprova capacidade da identidade cadastrada, não autorização para qualquer ação administrativa. Usar somente dentro do pedido e da política vigente. Não confundir erro de URL montada com falha de credencial.

## Seleção de transporte para executar o pedido

1. Reconciliar pedido, alvo, IDs, pausas, checkpoint e writer atual.
2. Validar domínio, instalação e identidade reais. Fazer backup e definir recuperação antes do write.
3. Usar o caminho existente mais restrito adequado: API editorial para campos editoriais; SSH/PHP/WP-CLI já autorizado para manutenção nativa; painel administrativo quando a função existir ali.
4. SSH pode autenticar por senha OU chave. Porta 22, host key conhecida ou SFTP bem-sucedido não comprovam shell. Uma conta SFTP-only não prova ausência de outro SSH. Procurar apenas referências autorizadas ligadas ao host/instalação exatos, sem tentar credenciais alheias.
5. RunCloud API/SSH só vale para a instalação comprovadamente gerenciada naquele servidor. Não transportar a credencial de um servidor para outro por associação de nome ou empresa.
6. Se faltar transporte, registrar o que foi testado e preparar localmente a alternativa segura. Revisão, lint e testes locais podem avançar sem deployment. Não dizer que há trabalho em andamento após encerrar o turno nem marcar o reparo como concluído.
7. Novo transporte executável, alteração de credencial/ACL e remoção de componentes temporários continuam sujeitos aos gates específicos. Não usar WPCode executável em Bitnami sem recuperação SSH certificada, nem criar endpoint público de manutenção.
8. Somente a ação concretamente protegida deve parar. Não exigir de novo aprovação editorial, não bloquear tarefas independentes e não devolver a coordenação rotineira a Zeus/Raquel/Rodolfo.

## Caso atual: Yoast em OpenZed e Cliquet

Alvos: `finanzas.openzed.com` (posts 52410, 52413, 52416) e `cliquet.com` (61948, 61951, 61954). Fincgriffin permanece pausado.

O terminal nativo carregado com o perfil Atena executou este preflight com sucesso nos dois alvos: 1Password legível, identidade WordPress administrativa HTTP 200 e plugins HTTP 200. Não foi criada credencial nem ampliada permissão. SSH/SFTP/PHP/Python já existem no ambiente local; isso não implica shell remoto disponível.

O reparo identificado é reconstruir o objeto derivado compartilhado da home pelo watcher nativo do Yoast, uma vez por instalação, preservando o acervo. Não fazer indexação geral, toggles de options, SQL cego, republicação ou alteração dos seis textos. A execução completa depende de transporte seguro e backup/recuperação certificados; não foi comprovada por este preflight.

Não repetir a mesma busca por SSH sem uma referência nova. Se os acessos permitidos forem esgotados, apresentar uma única decisão delimitada para a alternativa, não reabrir uma cadeia de permissões genéricas. O plugin temporário proposto ainda não recebeu confirmação específica de implantação/remoção.

## Validação e entrega

Atena é a única executora e dona do QA/planilha. Exigir canário, readback nativo e URLs públicas normais, preservando IDs/URLs/conteúdo. Informar separadamente acesso comprovado, método preparado, execução realizada e aceite público. Encaminhamento, documentação e ACK não são entrega do reparo.
