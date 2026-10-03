"""Cross-process serialization without changing financial authorization or quotas."""
from __future__ import annotations
import contextlib,fcntl,functools,hashlib,os,pathlib,stat

@contextlib.contextmanager
def request_lock(root, request_id, *, blocking=True):
    root=pathlib.Path(root)
    root.mkdir(parents=True,exist_ok=True)
    # Keep identifiers exact; derive a filename rather than normalizing caller data.
    key=hashlib.sha256(str(request_id).encode('utf-8')).hexdigest()
    fd=os.open(root/(key+'.request.lock'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):raise ValueError('regular request lock required')
        fcntl.flock(fd,fcntl.LOCK_EX|(0 if blocking else fcntl.LOCK_NB))
        try:yield
        finally:fcntl.flock(fd,fcntl.LOCK_UN)
    finally:os.close(fd)

def serialized_creation_request(fn):
    @functools.wraps(fn)
    def wrapped(args,*rest,**kw):
        with request_lock(pathlib.Path(fn.__globals__['STATE_ROOT'])/'request-locks',args.request_id):
            return fn(args,*rest,**kw)
    return wrapped

def serialized_inventory(fn):
    @functools.wraps(fn)
    def wrapped(*args,**kw):
        path=pathlib.Path(fn.__globals__['INVENTORY_PATH'])
        with request_lock(path.parent/'inventory-locks',str(path.resolve())):
            return fn(*args,**kw)
    return wrapped

def serialized_engine(fn):
    @functools.wraps(fn)
    def wrapped(self,manifest,*args,**kw):
        with request_lock(pathlib.Path(self.config['state_root'])/'request-locks',manifest.request_id):
            return fn(self,manifest,*args,**kw)
    return wrapped
