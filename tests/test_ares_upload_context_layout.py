"""Offline fixtures only: non-destructive approved upload context layout."""
import importlib.util,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('upload_layout',ROOT/'scripts/ares_upload_context_layout.py')
assert spec is not None and spec.loader is not None
class FakeDrive:
 def __init__(self):
  self.rows={'UPLOADFIX':{'id':'UPLOADFIX','name':'UPLOAD MANUAL','mimeType':'application/vnd.google-apps.folder','parents':['CREATIVEFIX'],'driveId':'DRIVEFIX','trashed':False,'capabilities':{'canAddChildren':True}}};self.writes=[]
 def meta(self,i):return self.rows[i].copy()
 def listing(self,p):return [r.copy() for r in self.rows.values() if r.get('parents')==[p]]
 def api(self,method,path,params=None,payload=None):
  assert method=='POST' and path=='files' and isinstance(payload,dict);self.writes.append(payload.copy());i='CREATED'+str(len(self.writes));self.rows[i]=dict(payload,id=i,driveId='DRIVEFIX',trashed=False,capabilities={'canAddChildren':True});return {'id':i}
class LayoutTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.m=importlib.util.module_from_spec(spec);assert spec.loader;spec.loader.exec_module(cls.m)
 def setUp(self):
  self.d=FakeDrive();self.c={'upload_root_id':'UPLOADFIX','source_root_id':'CREATIVEFIX','source_drive_id':'DRIVEFIX','authority_message_id':'1562164883766902888'};self.ops=[{'id':'OPERATIONFIX','name':'SHEIN_US_ES','mimeType':self.m.FOLDER,'parents':['CREATIVEFIX']}];self.managers={'g006':'Nicolas','g005':'Kelly'}
  self.d.rows['OPERATIONFIX']={**self.ops[0],'driveId':'DRIVEFIX','trashed':False,'capabilities':{'canAddChildren':True}}
 def test_injected_unregistered_row_blocks_before_writes(self):
  rows=self.m.plan(self.ops,self.managers);rows[0]['operation']='UNKNOWN_US_ES'
  with self.assertRaises(self.m.LayoutError):self.m.apply_layout(self.d,self.c,rows)
  self.assertEqual(self.d.writes,[])
 def test_changed_operation_root_blocks_before_writes(self):
  rows=self.m.plan(self.ops,self.managers);self.d.rows['OPERATIONFIX']['parents']=['OUTSIDE']
  with self.assertRaises(self.m.LayoutError):self.m.apply_layout(self.d,self.c,rows)
  self.assertEqual(self.d.writes,[])
 def test_plan_uses_existing_operations_and_exact_manager_names(self):
  p=self.m.plan(self.ops,self.managers);self.assertEqual(len(p),2);self.assertEqual({r['manager_code'] for r in p},{'g006','g005'});self.assertTrue(all(r['operation']=='SHEIN_US_ES' for r in p))
 def test_control_and_numeric_and_manager_folders_not_operations(self):
  self.assertEqual(self.m.plan([{'id':'x','name':x,'mimeType':self.m.FOLDER} for x in ['00_ARQUIVO_CONTROLE','1234','Nicolas','UPLOAD MANUAL']],self.managers),[])
 def test_duplicate_operation_name_blocks(self):
  with self.assertRaises(self.m.LayoutError):self.m.plan(self.ops+self.ops,self.managers)
 def test_unknown_manager_code_blocks(self):
  with self.assertRaises(self.m.LayoutError):self.m.plan(self.ops,{'g099':'Invented'})
 def test_non_destructive_create_and_replay(self):
  self.d.rows['NUMERICFIX']={'id':'NUMERICFIX','name':'1234567','mimeType':self.m.FOLDER,'parents':['UPLOADFIX']};before=self.d.rows['NUMERICFIX'].copy();p=self.m.plan(self.ops,self.managers)
  a=self.m.apply_layout(self.d,self.c,p);b=self.m.apply_layout(self.d,self.c,p)
  self.assertEqual(a['slots'],b['slots']);self.assertEqual(len(self.d.writes),3);self.assertEqual(self.d.rows['NUMERICFIX'],before);self.assertTrue(all('permissions' not in x for x in self.d.writes))
 def test_duplicate_existing_slot_blocks_no_new_copy(self):
  for i in ['A','B']:self.d.rows[i]={'id':i,'name':'SHEIN_US_ES','mimeType':self.m.FOLDER,'parents':['UPLOADFIX']}
  with self.assertRaises(self.m.LayoutError):self.m.apply_layout(self.d,self.c,self.m.plan(self.ops,self.managers))
  self.assertEqual(self.d.writes,[])
 def test_wrong_drive_stops_before_write(self):
  self.d.rows['UPLOADFIX']['driveId']='OTHER'
  with self.assertRaises(self.m.LayoutError):self.m.apply_layout(self.d,self.c,self.m.plan(self.ops,self.managers))
  self.assertEqual(self.d.writes,[])
 def test_root_without_write_capability_blocks(self):
  self.d.rows['UPLOADFIX']['capabilities']['canAddChildren']=False
  with self.assertRaises(self.m.LayoutError):self.m.apply_layout(self.d,self.c,self.m.plan(self.ops,self.managers))
 def test_slot_validation_rejects_rename(self):
  result=self.m.apply_layout(self.d,self.c,self.m.plan(self.ops,self.managers));slot=result['slots'][0];self.d.rows[slot['folder_id']]['name']='Another'
  with self.assertRaises(self.m.LayoutError):self.m.validate_slot(self.d,self.c,slot)
 def test_slot_validation_rejects_changed_parent(self):
  result=self.m.apply_layout(self.d,self.c,self.m.plan(self.ops,self.managers));slot=result['slots'][0];self.d.rows[slot['folder_id']]['parents']=['OUTSIDE']
  with self.assertRaises(self.m.LayoutError):self.m.validate_slot(self.d,self.c,slot)
if __name__=='__main__':unittest.main()
