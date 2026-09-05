"""Read-only formula interpreter; uses captured precedents, not Sheets writes."""
from audit import *
import calendar, operator, math
from dataclasses import dataclass
from datetime import date, timedelta

class CalcError(Exception):pass
class Unsupported(Exception):pass
GRIDS={(name,s['properties']['title']):cells(s) for name in IDS for s in load(name)['sheets']}
DEPS=ROOT/'support-dependencies.json'
if DEPS.exists():
 for title,cc in json.loads(DEPS.read_text()).items():GRIDS[('principal',title)]=cc
ID_NAMES={v:k for k,v in IDS.items()}
EPOCH=date(1899,12,30)
@dataclass
class Ref:
 book:str;sheet:str;r1:int;c1:int;r2:int;c2:int
 def matrix(self):
  if (self.book,self.sheet) not in GRIDS:raise Unsupported('Missing sheet '+self.book+':'+self.sheet)
  cc=GRIDS[(self.book,self.sheet)]
  return [[val(cc.get(col(c)+str(r),{})) for c in range(self.c1,self.c2+1)] for r in range(self.r1,self.r2+1)]

def ref(text,book,sheet):
 text=text.replace('$','')
 if '!' in text:
  sheet,text=text.rsplit('!',1);sheet=sheet.strip("'").replace("''", "'")
 bits=text.upper().split(':')
 def part(p,end=False):
  m=re.fullmatch(r'([A-Z]+)?(\d+)?',p)
  if not m:raise Unsupported('Bad ref '+text)
  return int(m[2]) if m[2] else (max([int(re.search(r'\d+',a)[0]) for a in GRIDS.get((book,sheet),{})] or [1]) if end else 1),ci(m[1]) if m[1] else (1100 if end else 1)
 r1,c1=part(bits[0]);r2,c2=part(bits[-1],True) if len(bits)>1 else (r1,c1)
 return Ref(book,sheet,r1,c1,r2,c2)

def material(x):return x.matrix() if isinstance(x,Ref) else x
def flat(x):
 x=material(x)
 if isinstance(x,list):return [z for y in x for z in flat(y)]
 return [x]
def scalar(x):
 x=material(x)
 if isinstance(x,list):
  f=flat(x)
  if len(f)!=1:raise CalcError('nonscalar')
  return f[0]
 return x
def num(x):
 x=scalar(x)
 if x=='' or x is None:return 0
 if isinstance(x,(int,float)):return x
 if isinstance(x,dict):raise CalcError('source error')
 try:return float(x)
 except (ValueError,TypeError):raise CalcError('nonnumeric '+str(x))
def binary(op,a,b):
 a=material(a);b=material(b)
 if isinstance(a,list) or isinstance(b,list):
  if not isinstance(a,list):a=[[a]*len(b[0]) for _ in b]
  if not isinstance(b,list):b=[[b]*len(a[0]) for _ in a]
  if len(a)!=len(b) or len(a[0])!=len(b[0]):raise CalcError('array shape')
  return [[binary(op,x,y) for x,y in zip(ar,br)] for ar,br in zip(a,b)]
 if op=='&':return str(a)+str(b)
 if op in ['=','<>']:
  same=(a==b) or (a=='' and b==0) or (a==0 and b=='')
  # Formula-generated empty strings must not equal numeric zero for IF guards.
  if isinstance(a,str) and isinstance(b,(int,float)) or isinstance(b,str) and isinstance(a,(int,float)):same=False
  return same if op=='=' else not same
 if op in ['<','>','<=','>=']:
  if isinstance(a,str) and isinstance(b,str):return {'<':operator.lt,'>':operator.gt,'<=':operator.le,'>=':operator.ge}[op](a,b)
  return {'<':operator.lt,'>':operator.gt,'<=':operator.le,'>=':operator.ge}[op](num(a),num(b))
 try:return {'+':operator.add,'-':operator.sub,'*':operator.mul,'/':operator.truediv,'^':operator.pow}[op](num(a),num(b))
 except ZeroDivisionError:raise CalcError('division zero')

TOKEN_RE=re.compile(r'''\s*("(?:[^"]|"")*"|'(?:[^']|'')*'!\$?[A-Za-z]+\$?\d*(?::\$?[A-Za-z]*\$?\d*)?|(?:\$?[A-Za-z]+\$?\d+)(?::\$?[A-Za-z]*\$?\d*)?|\$?[A-Za-z]+:\$?[A-Za-z]+|\d+:\d+|[A-Za-z_][A-Za-z_0-9.]*|(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|<>|<=|>=|[()+\-*/^%=<>&,:;])''')
class Parser:
 def __init__(self,f):
  self.t=[];p=0;f=f.strip().lstrip('=')
  while p<len(f):
   m=TOKEN_RE.match(f,p)
   if not m:
    if not f[p:].strip():break
    raise Unsupported('token '+f[p:p+40])
   self.t.append(m[1]);p=m.end()
  self.i=0
 def peek(self):return self.t[self.i] if self.i<len(self.t) else None
 def pop(self):v=self.peek();self.i+=1;return v
 def expr(self,p=0):
  t=self.pop()
  if t in ('+','-'):node=('unary',t,self.expr(60))
  elif t=='(':
   node=self.expr();assert self.pop()==')'
  elif t and t.startswith('"'):node=('literal',t[1:-1].replace('""','"'))
  elif t and re.fullmatch(r'(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',t):node=('literal',float(t))
  elif self.peek()=='(':
   self.pop();args=[]
   if self.peek()!=')':
    while True:
     args.append(self.expr())
     if self.peek() not in (',',';'):break
     self.pop()
   assert self.pop()==')';node=('call',t.upper(),args)
  else:node=('ref',t)
  levels={'=':10,'<>':10,'<':10,'>':10,'<=':10,'>=':10,'&':20,'+':30,'-':30,'*':40,'/':40,'^':50,'%':70}
  while self.peek() in levels and levels[self.peek()]>p:
   op=self.pop()
   if op=='%':node=('bin','/',node,('literal',100))
   else:node=('bin',op,node,self.expr(levels[op]))
  return node
 def parse(self):
  node=self.expr()
  if self.peek() is not None:raise Unsupported('remaining '+str(self.t[self.i:]))
  return node

def evaluate(node,book,sheet,cell):
 typ=node[0]
 ev=lambda x:evaluate(x,book,sheet,cell)
 if typ=='literal':return node[1]
 if typ=='ref':return ref(node[1],book,sheet)
 if typ=='unary':return num(ev(node[2]))*(-1 if node[1]=='-' else 1)
 if typ=='bin':return binary(node[1],ev(node[2]),ev(node[3]))
 fn,args=node[1:]
 if fn=='IF':return ev(args[1]) if scalar(ev(args[0])) else ev(args[2])
 if fn=='IFERROR':
  try:return ev(args[0])
  except CalcError:return ev(args[1]) if len(args)>1 else ''
 if fn in ['GOOGLEFINANCE']:raise Unsupported('volatile provider function')
 if fn=='SHEETNAME':return sheet
 if fn=='IMPORTRANGE':
  ident=scalar(ev(args[0]));m=re.search(r'/d/([\w-]+)',ident);ident=m[1] if m else ident
  if ident not in ID_NAMES:raise Unsupported('external unresolved '+ident)
  return ref(scalar(ev(args[1])),ID_NAMES[ident],sheet)
 if fn=='ROW':
  if not args:return int(re.search(r'\d+',cell)[0])
  r=ev(args[0]);return [[n] for n in range(r.r1,r.r2+1)]
 if fn=='INDEX':
  r=ev(args[0]);rn=int(num(ev(args[1])));cn=int(num(ev(args[2]))) if len(args)>2 else 1
  if not isinstance(r,Ref):raise Unsupported('nonref INDEX')
  return Ref(r.book,r.sheet,r.r1+rn-1 if rn else r.r1,r.c1+cn-1 if cn else r.c1,r.r1+rn-1 if rn else r.r2,r.c1+cn-1 if cn else r.c2)
 if fn=='FILTER':
  matrix=material(ev(args[0]));conditions=[material(ev(x)) for x in args[1:]]
  if len(matrix)==1:
   mask=[all(bool(c[0][i]) for c in conditions) for i in range(len(matrix[0]))]
   out=[[v for v,b in zip(matrix[0],mask) if b]]
  else:
   out=[row for i,row in enumerate(matrix) if all(bool(c[i][0]) for c in conditions)]
  if not out or not out[0]:raise CalcError('filter empty')
  return out
 vals=[ev(x) for x in args]
 if fn=='SUM':return sum(v for x in vals for v in flat(x) if isinstance(v,(float,int)))
 if fn=='ABS':return abs(num(vals[0]))
 if fn=='AND':return all(bool(v) for x in vals for v in flat(x))
 if fn=='OR':return any(bool(v) for x in vals for v in flat(x))
 if fn=='MAX':return max(v for x in vals for v in flat(x) if isinstance(v,(int,float)))
 if fn=='COUNTA':return sum(v!='' for x in vals for v in flat(x))
 if fn in ('COUNTIF','AVERAGEIF'):
  data=flat(vals[0]);crit=scalar(vals[1]);mm=re.fullmatch(r'([<>=]+)?(.*)',str(crit));op=mm[1] or '=';rhs=mm[2]
  try:rhs=float(rhs)
  except ValueError:pass
  selected=[v for v in data if binary(op,v,rhs)]
  if fn=='COUNTIF':return len(selected)
  selected=[v for v in selected if isinstance(v,(int,float))]
  if not selected:raise CalcError('average empty')
  return sum(selected)/len(selected)
 if fn=='DATE':
  y,m,d=map(lambda v:int(num(v)),vals);y,m0=divmod(y*12+m-1,12)
  return (date(y,m0+1,1)+timedelta(days=d-1)-EPOCH).days
 if fn=='TODAY':return (date.today()-EPOCH).days
 if fn=='EOMONTH':
  dt=EPOCH+timedelta(days=num(vals[0]));y,m=divmod(dt.year*12+dt.month-1+int(num(vals[1])),12)
  return (date(y,m+1,calendar.monthrange(y,m+1)[1])-EPOCH).days
 if fn=='DAY':return (EPOCH+timedelta(days=num(vals[0]))).day
 raise Unsupported('function '+fn)

def same(a,b):
 if isinstance(a,(int,float)) and isinstance(b,(int,float)):return math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-7)
 return a==b

def run():
 results={};all_records=[]
 for (book,title),cc in GRIDS.items():
  if title not in ['Agosto 2026','CAIXA SINTETICO']:continue
  records=[]
  for cell,x in cc.items():
   f=formula(x)
   if not f:continue
   rec={'cell':cell,'formula':f}
   try:
    result=evaluate(Parser(f).parse(),book,title,cell)
    if isinstance(result,Ref):
     r0,c0=int(re.search(r'\d+',cell)[0]),ci(re.match(r'[A-Z]+',cell)[0]);mm=result.matrix();mism=[];n=0
     for dr,row in enumerate(mm):
      for dc,v in enumerate(row):
       dest=col(c0+dc)+str(r0+dr);actual=val(cc.get(dest,{}));n+=1
       # Blank imported cells return numeric zero for a direct reference, but IMPORTRANGE preserves blank.
       if not same(v,actual) and not (v=='' and actual==0 and 'IMPORTRANGE' not in f):mism.append({'dest':dest,'source':col(result.c1+dc)+str(result.r1+dr),'expected':v,'actual':actual})
     rec.update(status='mismatch' if mism else 'pass',spill_cells=n,mismatches=mism)
    else:
     result=scalar(result);actual=val(x);rec.update(status='pass' if same(result,actual) else 'mismatch',expected=result,actual=actual)
   except Unsupported as e:rec.update(status='unsupported',reason=str(e))
   except Exception as e:rec.update(status='engine_review',reason=type(e).__name__+': '+str(e))
   records.append(rec);all_records.append(dict(book=book,sheet=title,**rec))
  results[book+':'+title]={'counts':dict(__import__('collections').Counter(x['status'] for x in records)),'spill_cells':sum(x.get('spill_cells',0) for x in records),'issues':[x for x in records if x['status']!='pass']}
 with (ROOT/'formula-recomputation.jsonl').open('w') as f:
  for rec in all_records:f.write(json.dumps(rec,ensure_ascii=False)+'\n')
 save('formula-recomputation-summary.json',results)
 for k,v in results.items():print(k,v['counts'],'spill',v['spill_cells'],'issues',[(x['cell'],x['status'],x.get('reason'),x.get('expected'),x.get('actual')) for x in v['issues'][:12]])
if __name__=='__main__':run()
