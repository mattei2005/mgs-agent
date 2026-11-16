"""Reconstruct three lost wheel ZIPs from real retained bytes and frozen times."""
import pathlib,json,gzip,zipfile,struct,datetime,subprocess,os
OUT=pathlib.Path(__file__).parent;PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-uv-1571959754081837281');CACHE=pathlib.Path('/root/.cache/uv')
rows={r['relative']:r for r in (json.loads(x)for x in gzip.open(PRIVATE/'metadata-second.jsonl.gz','rt'))};hashes=json.load(gzip.open(PRIVATE/'retained-payloads.json.gz','rt'));first=json.load(open(OUT/'unplanned-provider-first-pass.json'));scan=json.load(open(OUT/'unplanned-wheel-provider-scan.json'))
def digest(data):return subprocess.check_output(['sha256sum'],input=data).split()[0].decode()
def dt(ns):
 d=datetime.datetime.fromtimestamp(ns/1e9,datetime.timezone.utc);return d.replace(second=d.second//2*2,microsecond=0,tzinfo=None)
def dos(d):return (d.hour<<11)|(d.minute<<5)|(d.second//2),((d.year-1980)<<9)|(d.month<<5)|d.day
staged=PRIVATE/'incident-wheel-reconstruction';staged.mkdir(mode=0o700,exist_ok=False);results=[]
for target,wanted in first['remaining'].items():
 old=pathlib.Path(target);templates=[x for x in scan['templates']if pathlib.Path(x['path']).parent.parent==old.parent.parent];assert len(templates)==1
 template=pathlib.Path(templates[0]['path']);raw=template.read_bytes();z=zipfile.ZipFile(template);infos=z.infolist();assert all(not i.is_dir()and not i.extra for i in infos)
 linkrows=[r for rel,r in rows.items()if pathlib.Path(rel).parent==old.parent.relative_to(CACHE)and r['kind']=='link'];assert len(linkrows)==1
 archive_id=pathlib.PurePosixPath(linkrows[0]['target']).name
 for i in infos:assert digest(z.read(i))==hashes[str(CACHE/'archive-v0'/archive_id/i.filename)],'Retained wheel member differs from old payload'
 oldbase=dt(rows[str(old.relative_to(CACHE))]['mtime_ns']);newbase=dt(template.stat().st_mtime_ns);delta=oldbase-newbase
 strategies=[]
 strategies.append(('shift_real_template_times',{i.filename:datetime.datetime(*i.date_time)+delta for i in infos}))
 strategies.append(('uniform_frozen_wheel_mtime',{i.filename:oldbase for i in infos}))
 for seconds in [-4,-2,2,4]:strategies.append(('license_offset_'+str(seconds),{i.filename:oldbase+datetime.timedelta(seconds=seconds)if '/licenses/'in i.filename else oldbase for i in infos}))
 found=None
 for label,dates in strategies:
  b=bytearray(raw)
  for i in infos:
   assert b[i.header_offset:i.header_offset+4]==b'PK\x03\x04';time,date=dos(dates[i.filename]);struct.pack_into('<HH',b,i.header_offset+10,time,date)
  offset=z.start_dir
  for i in infos:
   assert b[offset:offset+4]==b'PK\x01\x02';nlen,elen,clen=struct.unpack_from('<HHH',b,offset+28);name=bytes(b[offset+46:offset+46+nlen]).decode('utf-8');assert name==i.filename;time,date=dos(dates[name]);struct.pack_into('<HH',b,offset+12,time,date);offset+=46+nlen+elen+clen
  h=digest(bytes(b))
  if h==wanted:
   dest=staged/(str(len(results))+'.whl');dest.write_bytes(bytes(b));assert subprocess.check_output(['sha256sum',str(dest)],text=True).split()[0]==wanted
   found=dict(target=target,provider=str(dest),sha256=wanted,template=str(template),strategy=label,members_verified=len(infos),exact_original_digest_matched=True);break
 assert found is not None,'No exact wheel reconstruction for '+target
 results.append(found)
(OUT/'unplanned-wheels-reconstructed.json').write_text(json.dumps(dict(status='PASS',files=len(results),results=results,no_cache_files_written=True),indent=2)+'\n');print(json.dumps(dict(status='PASS',files=len(results),results=results)))
