"""Read only import of hash-verified audit evidence. No auth or network at runtime."""
import json,hashlib,pathlib,re,collections
ROOT=pathlib.Path(__file__).parent
SOURCE=pathlib.Path('/root/mgs-agent/work/finance-final-reaudit-1545877165982355557')
def col(n):
 s=''
 while n:n,r=divmod(n-1,26);s=chr(65+r)+s
 return s
def cells(s):
 for b in s.get('data',[]):
  for r,row in enumerate(b.get('rowData',[]),b.get('startRow',0)+1):
   for c,x in enumerate(row.get('values',[]),b.get('startColumn',0)+1):
    if any(k in x for k in ['userEnteredValue','effectiveValue','formattedValue','note']):yield col(c)+str(r),x
def convert(book,sheet,cell,x,boundary=False):
 u=x.get('userEnteredValue',{});e=x.get('effectiveValue',{});v=next(iter(e.values()),'')
 if 'errorValue' in e:raise ValueError('Source error at '+book+'|'+sheet+'|'+cell)
 d={'id':book+'|'+sheet+'|'+cell,'book':book,'sheet':sheet,'cell':cell,'expected':v,'formatted':x.get('formattedValue',''),'format':x.get('effectiveFormat',{}).get('numberFormat',{})}
 if boundary:d.update(input=v,kind='historical_boundary',source_formula=u.get('formulaValue',''))
 elif 'formulaValue' in u:
  d.update(formula=u['formulaValue'],kind='formula')
  if 'GOOGLEFINANCE' in u['formulaValue']:d.update(kind='external_quote',input=v)
 elif u:d.update(input=next(iter(u.values())),kind='input')
 else:d.update(kind='spill_or_label')
 return d

def main():
 hashes=json.loads((SOURCE/'SHA256SUMS.json').read_text());bad=[]
 for f,h in hashes.items():
  if hashlib.sha256((SOURCE/f).read_bytes()).hexdigest()!=h:bad.append(f)
 if bad:raise ValueError('Audit hash mismatch '+str(bad))
 manifest=json.loads((SOURCE/'manifest.json').read_text());out={'schema_version':1,'as_of':manifest['principal']['captured_at'][:10],'sources':{},'cells':[],'boundaries':[]}
 for book,m in manifest.items():
  p=SOURCE/(book+'.json');data=json.loads(p.read_text());out['sources'][book]={'id':m['id'],'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'captured_at':m['captured_at']}
  for s in data['sheets']:
   title=s['properties']['title'];assert title!='USUARIOS BOT'
   out['cells'].extend(convert(book,title,a,x) for a,x in cells(s))
 for title,cc in json.loads((SOURCE/'support-dependencies.json').read_text()).items():
  assert title!='USUARIOS BOT'
  for a,x in cc.items():out['cells'].append(convert('principal',title,a,x,True))
  out['boundaries'].append({'sheet':title,'count':len(cc),'mode':'imported historical results; not recomputed month'})
 out['blocks']=json.loads((SOURCE/'live-blocks.json').read_text());out['manager_mapping']=json.loads((SOURCE/'manager-mapping-review.json').read_text())
 out['audit_hashes_verified']=len(hashes)
 p=ROOT/'private';p.mkdir(exist_ok=True)
 text=json.dumps(out,ensure_ascii=False,separators=(',',':'));(p/'source.json').write_text(text)
 h=hashlib.sha256(text.encode()).hexdigest();(p/'source-sha256.txt').write_text(h+'\n')
 print(json.dumps({'hashes_verified':len(hashes),'source_sha256':h,'cells':len(out['cells']),'kinds':dict(collections.Counter(x['kind'] for x in out['cells']))}))
if __name__=='__main__':main()
