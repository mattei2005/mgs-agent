# Manutenção completa e controlada da VPS

Use quando Rodolfo quiser deixar a VPS realmente atualizada, incluindo pacotes APT em phased rollout e tooling global Node (`corepack`/`npm`). O objetivo não é prometer risco zero, mas isolar cada classe de mudança, manter rollback e validar empiricamente entre lotes.

## Regra operacional

Pacote em phased rollout não está necessariamente bloqueado por incompatibilidade; a distribuição gradual é uma proteção contra regressões. Se Rodolfo pedir “atualizar tudo”, não encerrar dizendo apenas para aguardar o phasing. Simular, mostrar o risco e oferecer execução controlada. Não misturar um major de npm no mesmo passo cego dos pacotes Ubuntu.

## Fluxo validado

1. **Inventário e simulação**
   - Atualizar índices APT e listar `apt list --upgradable`.
   - Simular cada grupo com `apt-get -s install --only-upgrade <pacotes>`.
   - Confirmar zero remoções e zero dependências inesperadas.
   - Consultar `npm view corepack@<versão> engines dist.shasum --json` e o equivalente para npm; conferir compatibilidade com o Node vivo.
   - Registrar versões atuais, gateways, `dpkg --audit`, reboot flag e espaço em disco.

2. **Confirmação crítica**
   - A alteração toca `/usr` e pacotes de sistema; apresentar alvo, estado atual/novo, rollback e afirmar que reboot não será feito sem confirmação separada.

3. **Rollback antes da mutação Node**
   - Criar backup fora do Git, em diretório `700`, por exemplo `/root/.hermes/secure-backups/vps-maintenance/<timestamp>/`.
   - Arquivar `/usr/lib/node_modules/npm` e `/usr/lib/node_modules/corepack`.
   - Gerar SHA-256, validar o arquivo com `tar -tzf` e `sha256sum -c`.
   - Salvar snapshot JSON das versões e serviços.

4. **APT em lotes explícitos**
   - Aplicar somente os nomes simulados, com `--only-upgrade` e `Dpkg::Options::=--force-confold`.
   - Ordem recomendada para o conjunto Ubuntu observado: `apport/python` → `libheif` → `fwupd` → `plymouth` por último.
   - Após **cada** lote: `dpkg --audit` vazio e Zeus/Atena/Ares/agente legado, cron e autocommit ativos. Parar imediatamente se qualquer gate falhar.
   - Segurança/Monarx já liberados podem ser tratados antes desses lotes, também com validação.

5. **Tooling Node separado**
   - Atualizar Corepack primeiro e validar `corepack --version`, Node/npm inalterados e gateways ativos.
   - Atualizar npm major por último.
   - Validar `npm --version`, `npm ping`, um `npm exec` real, prefixo global e `npm outdated -g --depth=0 --json` vazio.

6. **Gates finais**
   - `apt list --upgradable` vazio.
   - `npm outdated -g` vazio.
   - `dpkg --audit` vazio e nenhum package hold inesperado.
   - `needrestart -b`, kernel atual/esperado e reboot flag.
   - Zero failed units; Zeus/Atena/Ares/agente legado, cron, autocommit e serviços de segurança ativos.
   - Verificar erros de prioridade alta no journal desde o início da manutenção.
   - Atualizar inventário/audit log e registrar REPORT-INFRA no destino correto antes de concluir.

## Comunicação executiva

Reportar quantos pacotes APT foram atualizados, versões finais de Node/npm/Corepack, pendências APT/npm, gateways, `dpkg`, journal, reboot e localização do rollback. Diferenciar claramente VPS concluída de Hermes ainda pendente. Nunca apresentar “phased” como impedimento absoluto; é decisão de risco que pode ser superada de forma controlada quando Rodolfo autoriza.