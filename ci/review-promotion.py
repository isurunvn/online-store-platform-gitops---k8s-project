#!/usr/bin/env python3
"""Privileged PR review: read candidate YAML as data, execute only base-branch code."""
import base64,json,os,re,sys
import yaml
from evidence import api,verified
repo=os.environ['GITHUB_REPOSITORY']
event=json.load(open(os.environ['GITHUB_EVENT_PATH']))
pr=event['pull_request'];number=pr['number']
files=api(f'repos/{repo}/pulls/{number}/files?per_page=100')
if pr['changed_files']>100:raise SystemExit('PR too large for evidence review; split it')
def content(path,ref):
    return base64.b64decode(api(f'repos/{repo}/contents/{path}?ref={ref}')['content']).decode()
def image(doc):return yaml.safe_load(doc)['spec']['template']['spec']['containers'][0]['image']
changed=[]
for f in files:
    m=re.fullmatch(r'apps/(backend|frontend|notification-service)/base/deployment.yaml',f['filename'])
    if not m:continue
    if f['status']!='modified':raise SystemExit('Application deletion/addition requires separate review')
    old=image(content(f['filename'],pr['base']['sha']))
    new=image(content(f['filename'],pr['head']['sha']))
    if old!=new:changed.append((m[1],new))
if not changed:print('No application image changes; no artifact promotion to verify');raise SystemExit(0)
if len(changed)!=1:raise SystemExit('Promote one application per PR')
if '--detect' in sys.argv:
    with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('needed=true\n')
    raise SystemExit(0)
component,new=changed[0]
allowed={f'apps/{component}/base/deployment.yaml',f'releases/{component}.json'}
if {f['filename'] for f in files}!=allowed:raise SystemExit('Promotion PR must contain only one Deployment and its evidence record')
candidate=json.loads(content(f'releases/{component}.json',pr['head']['sha']))
rollback = any(label['name'] == 'rollback-approved' for label in pr.get('labels', []))
if rollback:
    reviews = api(f'repos/{repo}/pulls/{number}/reviews?per_page=100')
    approved = False
    for review in reviews:
        if review['state'] != 'APPROVED' or review['commit_id'] != pr['head']['sha'] or review['user']['type'] != 'User':
            continue
        permission = api(f"repos/{repo}/collaborators/{review['user']['login']}/permission")['permission']
        if permission in ['admin', 'maintain', 'write']:
            approved = True
    if not approved:
        raise SystemExit('Rollback requires a current-head human maintainer approval before adding rollback-approved')
# SOURCE_TOKEN is read-only across the three source repos. Never execute candidate scripts.
os.environ['GH_TOKEN']=os.environ['SOURCE_TOKEN']
authentic=verified(component,candidate['run_id'],require_current=not rollback)
if candidate!=authentic or authentic['image']!=new:raise SystemExit('Candidate differs from authenticated build evidence')
print(f'{component}: authenticated main build, CI, report hashes and exact ARM64 image evidence verified')
print('::warning::Baseline vulnerability policy is report-only; review findings before approving production promotion.')
