"""Narrow verified MGS source/WordPress identity boundary. No campaign policy."""
import re,json,sys,pathlib

def trusted_message(message, *, author_ids=None, webhook_ids=None):
    # This candidate trusts only known MGS identities until an exact source policy is approved.
    author_ids=set(author_ids if author_ids is not None else ('344196393512075265','1496296175014252634'))
    webhook_ids=set(webhook_ids or ())
    webhook=str(message.get('webhook_id') or '')
    if webhook: return webhook in webhook_ids
    return str((message.get('author') or {}).get('id') or '') in author_ids

def require_post_identity(post,post_id,expected_slug):
    if not re.fullmatch('[1-9][0-9]*',str(post_id)): raise ValueError('invalid post_id')
    if not expected_slug or int(post.get('id') or 0)!=int(post_id) or post.get('slug')!=expected_slug: raise ValueError('post identity mismatch')
    if post.get('status') in ('trash','auto-draft'): raise ValueError('post state not writable')

if __name__=='__main__':
    if len(sys.argv)!=5 or sys.argv[1]!='post-identity':raise SystemExit('unsupported boundary command')
    p=pathlib.Path(sys.argv[2])
    if not p.is_file() or p.stat().st_size>8*1024*1024:raise SystemExit('invalid post readback')
    require_post_identity(json.loads(p.read_text()),sys.argv[3],sys.argv[4])
