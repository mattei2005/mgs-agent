"""Document-only acceptance: no runtime imports or campaign operations."""
from pathlib import Path
import datetime
import difflib
import fcntl
import hashlib
import json
import os

BASE = Path(__file__).resolve().parent
P = json.loads((BASE / 'prewrite.json').read_text())
C, M = Path(P['canonical']), Path(P['mirror'])
sha = lambda b: hashlib.sha256(b).hexdigest()
before, after = (BASE / 'canonical.before.md').read_bytes(), C.read_bytes()
old, new = before.decode(), after.decode()
heading = '## Revisão temporal ASAP no gate — sem efeitos de campanha\n\n'
next_heading = '## Continuação imediata parcial — mesmo shell e selo'
section = new.split(heading, 1)[1].split(next_heading, 1)[0]
oldline = next(x for x in old.splitlines() if x.startswith('- Prepare nunca publica campanha:'))
newline = next(x for x in new.splitlines() if x.startswith('- Prepare nunca publica campanha:'))
checks = {
    'backups_intact': sha(before) == sha((BASE / 'mirror.before.md').read_bytes()) == P['before_sha256'],
    'only_expected_line_and_section_changed': new.replace(heading + section, '', 1).replace(newline, oldline, 1) == old,
    'new_section_unique': new.count(heading) == 1,
    'original_command': all(x in section for x in ['--input <mesmo request.json>', '--approved-digest <digest ORIGINAL>', '--approval-message-id <OK ORIGINAL>']),
    'authenticated_posterior_instruction': 'posterior ao OK original, autenticada' in section,
    'request_scoped_hash_grant': 'grant request-scoped hash-pinado' in section,
    'exact_now_allowlist': 'allowlist NOW exata' in section,
    'future_and_expired_start': 'tanto um início ainda futuro quanto um vencido' in section,
    'fresh_message_gets': 'GETs frescos da aprovação e da instrução ASAP' in section,
    'fresh_identity_helper': 'graph_get_credential_metadata' in section and 'Ana/app' in section,
    'receipt_not_runtime_proof': 'não substituem runtime proof' in section,
    'pre_revision_gates': all(x in section for x in ['admissão/lease', 'fonte, Page/PBIA, reservas', 'ausência de efeitos de campanha ou intents incertos', 'writer único e locks']),
    'canonical_helper_five_minutes': all(x in section for x in ['target_start_revision.py', 'immediate_execute_start', '5 minutos']),
    'only_start_time_delta': 'delta comercial permitido é exclusivamente `start_time`' in section,
    'revalidation_before_engine': 'Reexecutar prevalidation, account policy e dry-run' in section,
    'originals_retained': 'start-revisions/original' in section and 'request/manifest/plan/summary, selos e OK originais' in section,
    'cas_and_redo': all(x in section for x in ['CAS numeradas', 'redo determinístico', 'cadeia de predecessor']),
    'retry_reuses_revision': 'reutilizar a revisão ainda futura' in section,
    'expired_successor_chain': all(x in section for x in ['sucessora', 'antes de qualquer efeito de campanha', 'preservando toda a cadeia', 'sem pedir novo OK']),
    'effects_uncertainty_fail_closed': all(x in section for x in ['efeitos confirmados ou incerteza', 'nunca re-clock', 'recriação de shells']),
    'sameids_continuation_grant': all(x in section for x in ['IDs existentes', 'mesmo request', 'journal/readback', 'grant próprio de continuation']),
    'no_bypass_or_fromzero_revise': 'não há bypass de schema, digest ou aprovação' in section and 'Não chamar `revise` do runner from-zero' in section,
    'no_documentary_runtime_execution': 'Não importar/executar runtime em manutenção documental' in section,
    'alias_native_rules_unchanged': old.split('## Reconciliação de leitura e variantes derivadas', 1)[1].split(next_heading, 1)[0] in new,
    'continuation_manual_rules_unchanged': old.split(next_heading, 1)[1] == new.split(next_heading, 1)[1],
    'narrow_explicit_supersession': 'Essa exceção supersede somente' in newline,
    'delivery_owner_only': 'somente o dono da entrega executa e comunica a campanha na origem' in section,
}
assert all(checks.values()), json.dumps(checks)
with (BASE / 'documentary-cas.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    assert C.read_bytes() == after, 'canonical CAS conflict'
    current = M.read_bytes()
    if current == after:
        mode = 'already_desired_exact_hash_readback_no_write'
    else:
        assert sha(current) == P['before_sha256'], 'mirror CAS conflict'
        temporary = BASE / 'mirror.install.tmp'
        temporary.write_bytes(after)
        os.chmod(temporary, M.stat().st_mode)
        os.replace(temporary, M)
        mode = 'baseline_cas_atomic_install'
    checks['mirror_exact_hash_readback'] = sha(M.read_bytes()) == sha(C.read_bytes()) == sha(after)
assert all(checks.values())
diff = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile='canonical.before.md', tofile='canonical.after.md'))
(BASE / 'skill.diff').write_text(diff)
receipt = {
    'task_id': 't_2b06442a', 'scope': 'documentary-only',
    'canonical': str(C), 'mirror': str(M),
    'before_sha256': P['before_sha256'], 'after_sha256': sha(after),
    'mirror_sha256': sha(M.read_bytes()), 'mirror_reconciliation': mode,
    'initial_mirror_cas': 'refused_baseline_mismatch; subsequent_readback_confirmed_exact_desired_bytes',
    'backup_canonical': P['backup_canonical'], 'backup_mirror': P['backup_mirror'],
    'diff_path': str(BASE / 'skill.diff'), 'diff_sha256': sha(diff.encode()),
    'tests_passed': sum(checks.values()), 'tests_total': len(checks), 'checks': checks,
    'runtime_imported_or_executed': False, 'campaign_or_external_writes': False,
    'shared_report_owner': 't_3950b5d9',
    'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
(BASE / 'receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n')
print(json.dumps({'tests_passed': receipt['tests_passed'], 'tests_total': receipt['tests_total'], 'after_sha256': sha(after), 'mirror_reconciliation': mode, 'receipt': str(BASE / 'receipt.json'), 'receipt_sha256': sha((BASE / 'receipt.json').read_bytes())}, indent=2))
