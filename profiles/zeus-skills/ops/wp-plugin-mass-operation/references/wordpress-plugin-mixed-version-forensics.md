# Forense de árvores de plugins WordPress com versões misturadas

Use quando `wp plugin verify-checksums --all --strict` reportar muitos `File was added` ou uma árvore parecer conter artefatos de versões diferentes.

## Regra de classificação

Não classifique todos os extras como malware e não aceite apenas a versão do header como prova da árvore real. Uma atualização/cópia parcial pode preservar todos os arquivos da versão declarada e acrescentar arquivos de versões posteriores.

## Procedimento somente leitura

1. Execute o checksum estrito com `--skip-plugins --skip-themes` e agregue por plugin e classe (`added`, `modified`, `missing`, sem checksum). Não persista código-fonte ou payloads de configuração.
2. Para cada plugin público afetado, gere um manifesto vivo `path -> SHA-256` com `sha256sum --zero`; trate plugins single-file, como Hello Dolly, separadamente.
3. Baixe por HTTPS o ZIP oficial exato da versão declarada e o ZIP oficial atual. Registre também o SHA-256 dos ZIPs.
4. Gere os dois manifestos oficiais com `sha256sum --zero` e compare programaticamente:
   - arquivo vivo igual à versão declarada;
   - igual à versão atual;
   - presente somente em uma das versões;
   - diferente de ambas;
   - ausente no vivo.
5. Classifique a árvore como:
   - `exact_installed`;
   - `exact_latest`;
   - `mixed_known_versions`;
   - `mixed_with_unknown_files`;
   - `no_public_reference`.
6. Cruze mtimes representativos e reconcilie origem na ordem canônica MGS: audit log, inventário, REPORT-INFRA, Git e session history. Sem atribuição suficiente, reporte `mudança concorrente não atribuída`; não promova para malware sem evidência funcional/integridade adicional.
7. Para heurísticas de código (`eval`, `base64`, `curl`, etc.), compare o SHA-256 do arquivo vivo com o pacote oficial antes de declarar suspeita. Uma coincidência exata é falso positivo da heurística.
8. Nunca repare in-place durante a auditoria. Primeiro congele o manifesto, faça backup filesystem+DB, valide restore isolado e preserve uma cópia forense dos arquivos que não coincidem com referências.

## Remediação recomendada

- Reconstrua em staging a partir do pacote canônico aprovado.
- Faça swap atômico de um plugin por vez, com rollback da árvore anterior.
- Valide checksum, status/versão WP-CLI, páginas públicas, REST e logs após cada unidade.
- Em rollback integral de `wp-content/plugins`, use o manifesto do snapshot como prova canônica da árvore e derive dinamicamente as contagens de plugins ativos/inativos. Não fixe a contagem observada em um estado intermediário: o snapshot pode restaurar plugins inativos adicionais sem representar falha.
- Separe critérios de saúde obrigatórios (HTTP, ausência de fatal, plugins necessários ativos, banco/core, manifesto exato e rollback preservado) de deltas apenas inventariais, como a quantidade de plugins inativos.
- Antes de um rollback automático por falha de validação, persista uma matriz reduzida de cada critério (`pass/fail` e valor observado). Isso permite corrigir um validador excessivamente rígido sem repetir o cutover às cegas.
- Plugins Pro/custom exigem pacote licenciado/canônico próprio; ausência no WordPress.org não autoriza substituição pelo homônimo gratuito.
- Remoção de árvores inativas, reboot, alteração de PHP/SSH e descarte de evidência são escopos separados e sujeitos à governança aplicável.
