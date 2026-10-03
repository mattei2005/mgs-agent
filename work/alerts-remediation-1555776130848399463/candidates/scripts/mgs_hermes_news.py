"""Deterministic explanations for our own structured Git monitor.
No model call is needed to explain already computed version/runtime metrics.
"""
from __future__ import annotations
import re


def fields(message):
    return {f.get('name', ''): f.get('value', '') for e in message.get('embeds') or [] for f in e.get('fields') or []}


def explain_monitor(message):
    f = fields(message)
    release = f.get('Última release oficial', 'não informada')
    runtime = f.get('Runtime MGS', f.get('Versão local', 'não informado'))
    stable = f.get('Atualização estável', 'não comprovada')
    main = f.get('Main de desenvolvimento', f.get('Upstream oficial', f.get('Upstream', 'não informado')))
    new = f.get('Novos no main desde último alerta', f.get('Novos desde o último alerta', 'não informado'))
    if re.search(r'rc\.|canary|alpha|beta', release, re.I):
        return ('O que mudou: a fonte usa uma tag RC/canary e não comprova release estável. '
                'Impacto: não recomendar atualização estável com esse rótulo. '
                'Exige ação: o estado do main é separado; confirmar o grafo e o runtime no fluxo autorizado.')
    if stable.startswith('Nenhuma'):
        result = 'Nenhuma atualização estável pendente: a release oficial já está contida no runtime.'
    elif stable.startswith('Disponível'):
        result = 'Há uma release estável ainda não contida no runtime; executar somente com autorização, patches, backup e validação.'
    else:
        result = 'A fonte não comprova o estado da atualização estável; não recomendar deploy por inferência.'
    pieces = [result, f'Release: {release}. Runtime: {runtime}.', f'Main: {main}. Novos desde o aviso anterior: {new}.']
    pieces.append('Na MGS, atualizar tudo significa alcançar o main. Isso não transforma RC em release estável nem autoriza instalação ou restart automático.')
    pending = re.search(r'main pendente no runtime\s*:\s*(?:\*\*)?(\d+)', main, re.I)
    if pending and int(pending.group(1)) > 0:
        pieces.append('Há pendência de main: revisar atualização controlada no fluxo autorizado, mesmo sem release estável nova.')
    elif pending:
        pieces.append('A fonte indica zero commits de main pendentes no runtime.')
    else:
        pieces.append('A fonte não fornece uma contagem comprovada de main pendente; confirmar o grafo antes de decidir.')
    if f.get('Atraso'):
        pieces.append('Contagem declarada pela fonte legada (não reinterpretada como release estável): ' + f['Atraso'])
    pieces.append('Nenhuma atualização, configuração ou restart foi aplicado por este resumo.')
    for key in ('Principais features', 'Principais fixes'):
        value = str(f.get(key) or '').strip()
        if value and not value.startswith(('nenhuma', 'nenhum')):
            pieces.append(f'{key}: {value[:450]}')
    return ('O que mudou: ' + '\n'.join(pieces[1:3]) + '\n\nImpacto: ' + pieces[0] + '\n\nExige ação: ' + '\n'.join(pieces[3:]))[:3800]
