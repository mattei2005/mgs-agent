"""Verify reconstruction using only surviving DEBs, never original duplicate files."""
import pathlib,json,subprocess,hashlib,sys
OUT=pathlib.Path(__file__).parent

def sha(path):return subprocess.check_output(['sha256sum','--',str(path)],text=True).split()[0]
def verify(rows):
 results=[]
 for row in rows:
  assert sha(row['retained_deb'])==row['retained_deb_sha256'],'retained DEB changed'
  p=subprocess.Popen(['ar','p',row['retained_deb'],row['member']],stdout=subprocess.PIPE,stderr=subprocess.PIPE);assert p.stdout;h=subprocess.run(['sha256sum'],stdin=p.stdout,capture_output=True,text=True);p.stdout.close();err=p.stderr.read()if p.stderr else b'';assert p.wait()==0 and h.returncode==0,err.decode(errors='replace');assert h.stdout.split()[0]==row['sha256'];results.append({'source':row['source'],'retained_member_verified':True})
 return {'status':'PASS','retained_only':True,'verified':len(results),'original_sources_read':0}
if __name__=='__main__':
 rows=json.load(open(OUT/'intermediate-duplicate-proof.json'))['rows'];print(json.dumps(verify(rows)))
