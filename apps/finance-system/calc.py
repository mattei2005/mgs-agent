"""Deterministic migration calculator. Expected results are never calculation inputs.

Formula graph is a compatibility/migration layer, not the final coordinate-free
business domain. Captured market quotes and historical-month boundaries are
explicit external inputs. Decimal(28), rounding only for display/reconciliation.
"""
from __future__ import annotations
import re,sys,json,calendar,operator,fnmatch,pathlib,collections
from decimal import Decimal, localcontext, InvalidOperation
from datetime import date,timedelta
from dataclasses import dataclass
from functools import lru_cache
D=Decimal
EPOCH=date(1899,12,30)
class CalculationError(Exception):pass
class Unsupported(CalculationError):pass
class Cycle(CalculationError):pass

def col(n):
 s=''
 while n:n,r=divmod(n-1,26);s=chr(65+r)+s
 return s
def ci(s):
 n=0
 for c in s.upper():n=n*26+ord(c)-64
 return n
def address(s):
 m=re.fullmatch(r'([A-Z]+)(\d+)',s.upper());return int(m[2]),ci(m[1])
def numeric(v):return isinstance(v,(int,float,Decimal)) and not isinstance(v,bool)
def decimal(v):return D(str(v)) if numeric(v) else v
def flat(v):return [z for x in v for z in flat(x)] if isinstance(v,list) else [v]
def scalar(v):
 if isinstance(v,list):
  f=flat(v)
  if len(f)!=1:raise CalculationError('nonscalar')
  return f[0]
 return v
def num(v):
 v=scalar(v)
 if v is None or v=='':return D(0)
 if isinstance(v,bool):return D(int(v))
 try:return D(str(v))
 except InvalidOperation:raise CalculationError('non-numeric input')
def binary(op,a,b):
 if isinstance(a,list) or isinstance(b,list):
  if not isinstance(a,list):a=[[a]*len(b[0]) for _ in b]
  if not isinstance(b,list):b=[[b]*len(a[0]) for _ in a]
  if len(a)!=len(b) or any(len(x)!=len(y) for x,y in zip(a,b)):raise CalculationError('array shape')
  return [[binary(op,x,y) for x,y in zip(ar,br)] for ar,br in zip(a,b)]
 if op=='&':return str(a)+str(b)
 if op in ('=','<>'):
  same=a==b
  if isinstance(a,str) and numeric(b) or isinstance(b,str) and numeric(a):same=False
  return same if op=='=' else not same
 if op in ('<','>','<=','>='):
  if not (isinstance(a,str) and isinstance(b,str)):a,b=num(a),num(b)
  return {'<':operator.lt,'>':operator.gt,'<=':operator.le,'>=':operator.ge}[op](a,b)
 try:return {'+':operator.add,'-':operator.sub,'*':operator.mul,'/':operator.truediv,'^':operator.pow}[op](num(a),num(b))
 except (ZeroDivisionError,InvalidOperation):raise CalculationError('arithmetic domain')
TOKEN=re.compile(r'''\s*("(?:[^"]|"")*"|(?:'(?:[^']|'')*'|[A-Za-z_][A-Za-z_0-9.]*)!\$?[A-Za-z]+\$?\d*(?::\$?[A-Za-z]*\$?\d*)?|\$?[A-Za-z]+\$?\d+(?::\$?[A-Za-z]*\$?\d*)?|\$?[A-Za-z]+:\$?[A-Za-z]+|\d+:\d+|[A-Za-z_][A-Za-z_0-9.]*|(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|<>|<=|>=|[{}()+\-*/^%=<>&,:;])''')
class Parser:
 def __init__(self,f):
  self.t=[];self.i=0;p=0;f=f.strip().lstrip('=')
  while p<len(f):
   m=TOKEN.match(f,p)
   if not m:
    if not f[p:].strip():break
    raise Unsupported('token '+f[p:p+30])
   self.t.append(m[1]);p=m.end()
 def peek(self):return self.t[self.i] if self.i<len(self.t) else None
 def pop(self):v=self.peek();self.i+=1;return v
 def expect(self,t):
  if self.pop()!=t:raise CalculationError('expected '+t)
 def expr(self,p=0):
  t=self.pop()
  if t in ('+','-'):node=('unary',t,self.expr(60))
  elif t=='(' :node=self.expr();self.expect(')')
  elif t=='{':
   rows=[[]]
   while True:
    rows[-1].append(self.expr());sep=self.pop()
    if sep=='}':break
    if sep==';':rows.append([])
    elif sep!=',':raise CalculationError('array delimiter')
   node=('array',rows)
  elif t and t.startswith('"'):node=('literal',t[1:-1].replace('""','"'))
  elif t and re.fullmatch(r'(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',t):node=('literal',D(t))
  elif self.peek()=='(':
   self.pop();args=[]
   if self.peek()!=')':
    while True:
     args.append(self.expr())
     if self.peek() not in (',',';'):break
     self.pop()
   self.expect(')');node=('call',t.upper(),args)
  else:node=('ref',t)
  levels={'=':10,'<>':10,'<':10,'>':10,'<=':10,'>=':10,'&':20,'+':30,'-':30,'*':40,'/':40,'^':50,'%':70}
  while self.peek() in levels and levels[self.peek()]>p:
   op=self.pop();node=('bin','/',node,('literal',D(100))) if op=='%' else ('bin',op,node,self.expr(levels[op]))
  return node
 def parse(self):
  node=self.expr()
  if self.peek() is not None:raise Unsupported('remaining formula tokens')
  return node
@lru_cache(maxsize=70000)
def parse(f):return Parser(f).parse()
@dataclass
class Ref:
 book:str;sheet:str;r1:int;c1:int;r2:int;c2:int

class Workbook:
 def __init__(self,data,overrides=None,as_of=None):
  self.data=data;self.records={(x['book'],x['sheet'],x['cell']):x for x in data['cells']};self.overrides=overrides or {};self.cache={};self.active=set();self.spills={};self.errors={};self.extents={};self.formula_spills={}
  self.as_of=date.fromisoformat(as_of or data['as_of']);self.ids={v['id']:k for k,v in data.get('sources',{}).items()}
  for b,s,c in self.records:
   r,co=address(c);old=self.extents.get((b,s),(1,1));self.extents[b,s]=(max(r,old[0]),max(co,old[1]))
  for (b,s,c),x in self.records.items():
   if x.get('kind')=='external_quote' or not x.get('formula'):continue
   node=parse(x['formula'])
   if node[0]=='ref' or node[0]=='call' and node[1] in ('IMPORTRANGE','INDEX'):
    rr=self.reference(node,b,s,c)
    if rr:
     r0,c0=address(c);self.formula_spills[b,s,c]=rr
     for dr in range(rr.r2-rr.r1+1):
      for dc in range(rr.c2-rr.c1+1):
       dest=(b,s,col(c0+dc)+str(r0+dr));src=(rr.book,rr.sheet,col(rr.c1+dc)+str(rr.r1+dr))
       if dest!=(b,s,c) and dest in self.records and self.records[dest].get('formula'):raise CalculationError('spill collision')
       self.spills[dest]=src
 def ref(self,text,b,s):
  text=text.replace('$','')
  if '!' in text:s,text=text.rsplit('!',1);s=s.strip("'").replace("''", "'")
  if (b,s) not in self.extents:raise Unsupported('Uncaptured sheet '+b+':'+s)
  bits=text.upper().split(':');ext=self.extents[b,s]
  def part(p,end=False):
   m=re.fullmatch(r'([A-Z]+)?(\d+)?',p)
   if not m:raise Unsupported('Bad reference '+text)
   return int(m[2]) if m[2] else (ext[0] if end else 1),ci(m[1]) if m[1] else (ext[1] if end else 1)
  r1,c1=part(bits[0]);r2,c2=part(bits[-1],True) if len(bits)>1 else (r1,c1)
  return Ref(b,s,r1,c1,r2,c2)
 def matrix(self,r):return [[self.get(r.book,r.sheet,col(c)+str(row)) for c in range(r.c1,r.c2+1)] for row in range(r.r1,r.r2+1)]
 def reference(self,node,b,s,c):
  if node[0]=='ref':return self.ref(node[1],b,s)
  if node[0]!='call':return None
  fn,args=node[1:]
  if fn=='IMPORTRANGE':
   ident=scalar(self.ev(args[0],b,s,c));m=re.search(r'/d/([\w-]+)',ident);ident=m[1] if m else ident
   if ident not in self.ids:raise Unsupported('unresolved import')
   return self.ref(scalar(self.ev(args[1],b,s,c)),self.ids[ident],s)
  if fn=='INDEX':
   rr=self.reference(args[0],b,s,c)
   if rr is None:raise Unsupported('nonreference INDEX')
   rn=int(num(self.ev(args[1],b,s,c)));cn=int(num(self.ev(args[2],b,s,c))) if len(args)>2 else 1
   return Ref(rr.book,rr.sheet,rr.r1+rn-1 if rn else rr.r1,rr.c1+cn-1 if cn else rr.c1,rr.r1+rn-1 if rn else rr.r2,rr.c1+cn-1 if cn else rr.c2)
  return None
 def get(self,b,s,c):
  key=(b,s,c);ident='|'.join(key)
  if key in self.cache:return self.cache[key]
  if key in self.active:raise Cycle('cycle at '+ident)
  if key in self.errors:raise CalculationError(self.errors[key])
  self.active.add(key)
  try:
   x=self.records.get(key,{})
   if ident in self.overrides:
    if x.get('kind') not in ('input','external_quote') and 'input' not in x:raise CalculationError('override is not an input')
    v=num(self.overrides[ident]) if numeric(x.get('input')) else self.overrides[ident]
   elif key in self.spills:
    v=self.get(*self.spills[key])
    # Direct range links render blank as 0, IMPORTRANGE preserves blank.
    source=self.records.get(self.spills[key],{})
    if v=='' and x.get('formula') and 'IMPORTRANGE' not in x['formula'] and not source.get('formula') and self.spills[key] not in self.spills:v=D(0)
   elif x.get('kind')=='external_quote' or not x.get('formula'):v=decimal(x.get('input',''))
   else:
    v=self.ev(parse(x['formula']),b,s,c)
    if isinstance(v,list):
     r0,c0=address(c)
     for dr,row in enumerate(v):
      for dc,item in enumerate(row):self.cache[b,s,col(c0+dc)+str(r0+dr)]=item
     v=v[0][0] if v and v[0] else ''
   self.cache[key]=v;return v
  except CalculationError as e:self.errors[key]=str(e);raise
  finally:self.active.remove(key)
 def ev(self,n,b,s,c):
  ev=lambda x:self.ev(x,b,s,c);typ=n[0]
  if typ=='literal':return n[1]
  if typ=='ref':return self.matrix(self.ref(n[1],b,s))
  if typ=='unary':return binary('*',ev(n[2]),D(-1) if n[1]=='-' else D(1))
  if typ=='bin':return binary(n[1],ev(n[2]),ev(n[3]))
  if typ=='array':
   result=[]
   for row in n[1]:
    chunks=[ev(x) for x in row];chunks=[x if isinstance(x,list) else [[x]] for x in chunks]
    if len({len(x) for x in chunks})!=1:raise CalculationError('array literal shape')
    result.extend([sum((x[i] for x in chunks),[]) for i in range(len(chunks[0]))])
   return result
  fn,args=n[1:]
  if fn=='IF':return ev(args[1]) if scalar(ev(args[0])) else ev(args[2])
  if fn=='IFERROR':
   try:return ev(args[0])
   except (Unsupported,Cycle):raise
   except CalculationError:return ev(args[1]) if len(args)>1 else ''
  if fn=='GOOGLEFINANCE':raise Unsupported('market quote must be frozen external input')
  if fn=='SHEETNAME':return s
  if fn in ('IMPORTRANGE','INDEX'):return self.matrix(self.reference(n,b,s,c))
  if fn=='ROW':
   if not args:return D(address(c)[0])
   rr=self.reference(args[0],b,s,c);return [[D(r)] for r in range(rr.r1,rr.r2+1)]
  if fn=='FILTER':
   m=ev(args[0]);conditions=[ev(x) for x in args[1:]]
   if len(m)==1:out=[[v for i,v in enumerate(m[0]) if all(bool(x[0][i]) for x in conditions)]]
   else:out=[row for i,row in enumerate(m) if all(bool(x[i][0]) for x in conditions)]
   if not out or not out[0]:raise CalculationError('empty filter')
   return out
  vs=[ev(a) for a in args]
  if fn=='SUM':return sum((v for x in vs for v in flat(x) if numeric(v)),D(0))
  if fn in ('MIN','MAX'):
   seq=[v for x in vs for v in flat(x) if numeric(v)];return (min if fn=='MIN' else max)(seq) if seq else D(0)
  if fn=='SUMIF':
   criterion=str(scalar(vs[1]));data=flat(vs[0]);values=flat(vs[2]) if len(vs)>2 else data
   return sum((v for h,v in zip(data,values) if numeric(v) and fnmatch.fnmatchcase(str(h),criterion)),D(0))
  if fn=='ABS':return abs(num(vs[0]))
  if fn=='AND':return all(bool(v) for x in vs for v in flat(x))
  if fn=='OR':return any(bool(v) for x in vs for v in flat(x))
  if fn=='COUNTUNIQUE':return D(len(set(flat(vs[0]))))
  if fn=='COUNTIF':
   crit=str(scalar(vs[1]));mm=re.fullmatch(r'([<>=]+)?(.*)',crit);op=mm[1] or '=';rhs=mm[2]
   try:rhs=D(rhs)
   except InvalidOperation:pass
   def matches(v):
    if numeric(rhs) and not numeric(v):return False
    return binary(op,v,rhs)
   return D(sum(matches(v) for v in flat(vs[0])))
  if fn=='DATE':
   y,m,d=[int(num(v)) for v in vs];y,m0=divmod(y*12+m-1,12);return D((date(y,m0+1,1)+timedelta(days=d-1)-EPOCH).days)
  if fn=='TODAY':return D((self.as_of-EPOCH).days)
  if fn=='EOMONTH':
   dt=EPOCH+timedelta(days=int(num(vs[0])));y,m=divmod(dt.year*12+dt.month-1+int(num(vs[1])),12)
   return D((date(y,m+1,calendar.monthrange(y,m+1)[1])-EPOCH).days)
  if fn=='DAY':return D((EPOCH+timedelta(days=int(num(vs[0])))).day)
  if fn=='QUERY':return self.query(vs[0],str(scalar(vs[1])))
  raise Unsupported('function '+fn)
 def query(self,rows,q):
  # Fail-closed subset used by the captured analytical queries; not arbitrary SQL.
  m=re.fullmatch(r"select (.*?) (?:group by Col(\d+) )?(?:order by (Col\d+|sum\(Col\d+\))( desc)? )?(?:limit (\d+) )?label (.*)",q)
  if not m:raise Unsupported('QUERY grammar')
  selections=m[1].split(',');group=int(m[2])-1 if m[2] else None;result=[]
  if group is not None:
   groups=collections.defaultdict(list)
   for row in rows:groups[row[group]].append(row)
   for key,rr in groups.items():
    line=[]
    for sel in selections:
     sm=re.fullmatch(r'sum\(Col(\d+)\)',sel)
     if sm:line.append(sum((r[int(sm[1])-1] for r in rr if numeric(r[int(sm[1])-1])),D(0)))
     elif sel==f'Col{group+1}':line.append(key)
     else:raise Unsupported('QUERY select')
    result.append(line)
  else:
   if any(not re.fullmatch(r'Col\d+',x) for x in selections):raise Unsupported('QUERY select')
   result=[[r[int(x[3:])-1] for x in selections] for r in rows]
  if m[3]:
   idx=selections.index(m[3]);result.sort(key=lambda r:r[idx],reverse=bool(m[4]))
  if m[5]:result=result[:int(m[5])]
  labels=dict(re.findall(r"(Col\d+|sum\(Col\d+\)) '([^']*)'",m[6]));header=[labels.get(x,x) for x in selections]
  # QUERY omits an all-empty labels row; mixed labels retain empty cells.
  return ([header] if any(header) else [])+result

def equal(a,b):
 if numeric(a) and numeric(b):return abs(num(a)-num(b))<=max(D('0.0000001'),abs(num(b))*D('0.000000001'))
 return a==b

def json_default(x):
 if isinstance(x,Decimal):return str(x)
 raise TypeError(type(x).__name__)
def export(data,overrides=None,as_of=None):
 w=Workbook(data,overrides,as_of);rows=[];counts=collections.Counter();issues=[]
 # Arrays must be evaluated before their result-only cells.
 ordered=sorted(data['cells'],key=lambda x:not bool(x.get('formula')))
 for x in ordered:
  key=(x['book'],x['sheet'],x['cell']);ident='|'.join(key)
  try:
   v=w.get(*key);status='pass' if equal(v,x.get('expected','')) else 'mismatch'
   if x['kind'] in ('input','external_quote','historical_boundary'):status=x['kind']
   if status=='mismatch':issues.append({'id':ident,'expected':x.get('expected',''),'actual':v})
   result=dict(x,actual=v,status=status)
  except CalculationError as e:
   status='error';result=dict(x,actual=None,status=status,error=str(e));issues.append({'id':ident,'error':str(e)})
  counts[status]+=1;rows.append(result)
 return w,{'rows':rows,'counts':dict(counts),'issues':issues,'as_of':w.as_of.isoformat(),'quote_mode':'frozen provisional snapshot','boundaries':data.get('boundaries',[])}
if __name__=='__main__':
 root=pathlib.Path(__file__).parent;data=json.loads((root/'private/source.json').read_text());overrides=json.loads(sys.argv[1]) if len(sys.argv)>1 else {}
 w,result=export(data,overrides)
 (root/'private/recalculated.json').write_text(json.dumps(result,ensure_ascii=False,default=json_default))
 print(json.dumps({'counts':result['counts'],'issues':result['issues'][:20]},ensure_ascii=False,default=json_default))
