import ast
import copy
from pathlib import Path
import sys
import unittest

class RouteBlocked(ValueError):
    pass

source = ast.parse(Path(sys.argv.pop(1)).read_text())
function = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == '_batch')
namespace = {'RouteBlocked': RouteBlocked}
exec(compile(ast.Module(body=[function], type_ignores=[]), '<candidate-read-only-batch>', 'exec'), namespace)
batch = namespace['_batch']

class Fake:
    def __init__(self, rows, direct=(200, {'id':'page'}, {}), http=200):
        self.rows=rows; self.direct=direct; self.http=http; self.gets=[]; self.batches=0
    def graph_batch_get(self, token, requests):
        self.batches+=1
        return self.http, copy.deepcopy(self.rows), {}
    def graph_get(self, path, token, params):
        self.gets.append((path, token, params))
        return self.direct

Q=[{'name':'good','path':'act_1867022354284742','params':{'fields':'id'}},
   {'name':'limited','path':'540397952481732/assigned_users','params':{'fields':'id,name,tasks','business':'155263197283282','limit':100}}]
def good():return {'name':'good','code':200,'body':{'id':'act_1867022354284742'}}
def bad(code=4, transient=True):return {'name':'limited','code':403,'body':{'error':{'code':code,'is_transient':transient}}}

class ReadBatchTests(unittest.TestCase):
    def test_success_no_retry(self):
        c=Fake([good(),{'name':'limited','code':200,'body':{'id':'page'}}]);self.assertEqual(batch(c,'identity',Q)['limited'],{'id':'page'});self.assertEqual(c.gets,[])
    def test_only_failed_transient_read_recovered(self):
        c=Fake([good(),bad()]);r=batch(c,'identity',Q);self.assertEqual(r['good'],good()['body']);self.assertEqual(r['limited'],{'id':'page'});self.assertEqual(c.batches,1);self.assertEqual(c.gets,[(Q[1]['path'],'identity',Q[1]['params'])])
    def test_persistent_limit_stays_blocked(self):
        c=Fake([good(),bad()],direct=(403,{'error':{'code':4,'is_transient':True}},{}))
        with self.assertRaises(RouteBlocked):batch(c,'identity',Q)
        self.assertLessEqual(len(c.gets),1)
    def test_permission_failure_never_retried(self):
        c=Fake([good(),bad(10)])
        with self.assertRaises(RouteBlocked):batch(c,'identity',Q)
        self.assertEqual(c.gets,[])
    def test_nontransient_limit_never_retried(self):
        c=Fake([good(),bad(4,False)])
        with self.assertRaises(RouteBlocked):batch(c,'identity',Q)
        self.assertEqual(c.gets,[])
    def test_malformed_body_never_accepted(self):
        c=Fake([good(),{'name':'limited','code':200,'body':'invalid'}])
        with self.assertRaises(RouteBlocked):batch(c,'identity',Q)
    def test_identity_mismatch_never_retried(self):
        c=Fake([good(),{'name':'different','code':403,'body':{'error':{'code':4,'is_transient':True}}}])
        with self.assertRaises(RouteBlocked):batch(c,'identity',Q)
        self.assertEqual(c.gets,[])
    def test_outer_failure_never_retried(self):
        c=Fake([good(),bad()],http=500)
        with self.assertRaises(RouteBlocked):batch(c,'identity',Q)
        self.assertEqual(c.gets,[])
    def test_direct_permission_error_not_promoted_to_success(self):
        c=Fake([good(),bad()],direct=(400,{'error':{'code':10}},{}))
        with self.assertRaises(RouteBlocked):batch(c,'identity',Q)
    def test_direct_malformed_success_not_accepted(self):
        c=Fake([good(),bad()],direct=(200,[],{}))
        with self.assertRaises(RouteBlocked):batch(c,'identity',Q)

if __name__ == '__main__':unittest.main()
