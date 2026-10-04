#!/usr/bin/env python3
"""Current reusable finance preparation entrypoint; source-only and shared admission."""
import argparse,json,pathlib,sys
from source_stage import prepare,output_dirs
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from finance_release_guard import lease,release_state,SAFE_STATES

def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--destination',type=pathlib.Path,required=True);p.add_argument('--outputs-only',action='store_true');a=p.parse_args()
 destination=a.destination.absolute()
 if not destination.is_relative_to(ROOT/'private') or destination==ROOT/'private':raise ValueError('candidate must be under app/private')
 with lease(ROOT,timeout=5,recover_pending=False):
  state=release_state(ROOT)
  if state and state.get('state') not in SAFE_STATES:raise ValueError('release recovery required; preparation does not recover or publish')
  manifest=json.loads(a.manifest.read_text())
  if a.outputs_only:
   if not destination.is_dir() or not manifest.get('authority') or not manifest.get('producer'):raise ValueError('existing stage/provenance required')
   result={'files':[],'copied_bytes':0,'test_output_dirs':output_dirs(destination,manifest.get('test_output_dirs',[]))}
  else:result=prepare(ROOT,destination,manifest)
 print(json.dumps({'pass':True,'files':len(result['files']),'copied_bytes':result['copied_bytes'],'shared_admission':True,'destination':str(destination),'financial_writes':0,'deletions':0}))
if __name__=='__main__':main()
