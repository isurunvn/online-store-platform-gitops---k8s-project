import hashlib,io,json,unittest,zipfile
from unittest.mock import patch
import evidence
class EvidenceTests(unittest.TestCase):
 def fixture(self):
  repo=evidence.REPOS['frontend'];sha='a'*40
  report=b'{"Results":[]}'
  e={'schema_version':1,'component':'frontend','source_repository':repo,'source_sha':sha,'run_id':10,'run_attempt':1,'workflow':'build-image.yml','ci_run_id':9,'platform':'linux/arm64','image':'phx.ocir.io/axkouhjvgred/online-store/frontend@sha256:'+'b'*64,'security_policy':'baseline-report-only','reports':{n:hashlib.sha256(report).hexdigest() for n in ['trivy-image.json','sbom.cdx.json']}}
  def api(path):
   if path.endswith('/artifacts'):return {'artifacts':[{'name':'release-evidence','expired':False,'id':2,'size_in_bytes':1000}]}
   if path.endswith('/commits/main'):return {'sha':sha}
   if path.endswith('/runs/9'):return {'conclusion':'success','event':'push','head_branch':'main','head_sha':sha,'path':'.github/workflows/check.yml'}
   return {'conclusion':'success','head_branch':'main','head_repository':{'full_name':repo},'event':'workflow_run','path':'.github/workflows/build-image.yml','head_sha':sha,'run_attempt':1}
  def archive(meta,body):
   b=io.BytesIO()
   with zipfile.ZipFile(b,'w') as z:
    z.writestr('evidence.json',json.dumps(meta))
    for n in ['trivy-image.json','sbom.cdx.json']:z.writestr(n,body)
   return b.getvalue()
  return e,api,archive,report
 def test_valid_evidence(self):
  e,api,archive,r=self.fixture()
  with patch('evidence.api',side_effect=api),patch('evidence.subprocess.check_output',return_value=archive(e,r)):
   self.assertEqual(evidence.verified('frontend',10),e)
 def test_tampered_report(self):
  e,api,archive,r=self.fixture()
  with patch('evidence.api',side_effect=api),patch('evidence.subprocess.check_output',return_value=archive(e,b'{}')):
   with self.assertRaises(ValueError):evidence.verified('frontend',10)
 def test_wrong_platform(self):
  e,api,archive,r=self.fixture();e['platform']='linux/amd64'
  with patch('evidence.api',side_effect=api),patch('evidence.subprocess.check_output',return_value=archive(e,r)):
   with self.assertRaises(ValueError):evidence.verified('frontend',10)
 def test_wrong_registry(self):
  e,api,archive,r=self.fixture();e['image']='example.com/attacker@sha256:'+'b'*64
  with patch('evidence.api',side_effect=api),patch('evidence.subprocess.check_output',return_value=archive(e,r)):
   with self.assertRaises(ValueError):evidence.verified('frontend',10)
 def test_stale_source(self):
  e,api,archive,r=self.fixture()
  def stale(path):return {'sha':'c'*40} if path.endswith('/commits/main') else api(path)
  with patch('evidence.api',side_effect=stale),patch('evidence.subprocess.check_output',return_value=archive(e,r)):
   with self.assertRaises(ValueError):evidence.verified('frontend',10)
if __name__=='__main__':unittest.main()
