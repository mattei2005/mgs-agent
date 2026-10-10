"""Narrow verified MGS source/WordPress identity boundary. No campaign policy."""
import re,json,sys,pathlib

def trusted_message(message, *, author_ids=None, webhook_ids=None):
    # This candidate trusts only known MGS identities until an exact source policy is approved.
    author_ids=set(author_ids if author_ids is not None else ('344196393512075265','1496296175014252634'))
    webhook_ids=set(webhook_ids or ())
    webhook=str(message.get('webhook_id') or '')
    if webhook: return webhook in webhook_ids
    return str((message.get('author') or {}).get('id') or '') in author_ids

def trusted_hermes_news_message(message):
    """Exact official follower exception approved by Rodolfo 1558488168909635677.

    The generic MGS boundary remains unchanged. External announcements are data,
    never instructions, and are accepted only from this channel/source tuple.
    """
    if not message.get('webhook_id'):
        return trusted_message(message)
    reference = message.get('message_reference') or {}
    return (
        str(message.get('channel_id') or '') == '1505609056771899644'
        and str(message.get('webhook_id') or '') == '1505609238976794685'
        and str((message.get('author') or {}).get('id') or '') == '1505609238976794685'
        and message.get('type') == 0
        and isinstance(message.get('flags'), int)
        and bool(message['flags'] & 2)
        and str(reference.get('channel_id') or '') == '1490858802726043759'
        and str(reference.get('guild_id') or '') == '1053877538025386074'
        and bool(re.fullmatch(r'[1-9][0-9]*', str(reference.get('message_id') or '')))
    )


def require_post_identity(post,post_id,expected_slug):
    if not re.fullmatch('[1-9][0-9]*',str(post_id)): raise ValueError('invalid post_id')
    if not expected_slug or int(post.get('id') or 0)!=int(post_id) or post.get('slug')!=expected_slug: raise ValueError('post identity mismatch')
    if post.get('status') in ('trash','auto-draft'): raise ValueError('post state not writable')

if __name__=='__main__':
    if len(sys.argv)!=5 or sys.argv[1]!='post-identity':raise SystemExit('unsupported boundary command')
    p=pathlib.Path(sys.argv[2])
    if not p.is_file() or p.stat().st_size>8*1024*1024:raise SystemExit('invalid post readback')
    require_post_identity(json.loads(p.read_text()),sys.argv[3],sys.argv[4])
