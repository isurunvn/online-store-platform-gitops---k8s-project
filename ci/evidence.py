"""Validate authenticated GitHub build evidence. Never execute artifact contents."""
import hashlib,io,json,re,subprocess,zipfile,tempfile,pathlib
REPOS={'backend':'isurunvn/online-store-platform-backend---k8s-project','frontend':'isurunvn/online-store-platform-frontend---k8s-project','notification-service':'isurunvn/online-store-notification-service---k8s-project'}
def api(path):return json.loads(subprocess.check_output(['gh','api',path]))
def verified(component,run_id,require_current=True):
    repo=REPOS[component]
    if not str(run_id).isdigit():raise ValueError('Invalid run ID')
    run=api(f'repos/{repo}/actions/runs/{run_id}')
    if not (run['conclusion']=='success' and run['head_branch']=='main' and
            run['head_repository']['full_name']==repo and run['event'] in ['workflow_run','workflow_dispatch'] and
            run['path'].split('@')[0]=='.github/workflows/build-image.yml'):
        raise ValueError('Publication run is not an authorized successful main build')
    artifacts=api(f'repos/{repo}/actions/runs/{run_id}/artifacts')['artifacts']
    matches=[a for a in artifacts if a['name']=='release-evidence' and not a['expired']]
    if len(matches)!=1:raise ValueError('Expected one unexpired release-evidence artifact')
    if matches[0]['size_in_bytes']>50_000_000:raise ValueError('Oversized evidence archive')
    data=subprocess.check_output(['gh','api',f'repos/{repo}/actions/artifacts/{matches[0]["id"]}/zip'])
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if sum(i.file_size for i in z.infolist())>100_000_000:raise ValueError('Oversized evidence contents')
        e=json.loads(z.read('evidence.json'))
        if e.get('signing') == 'sigstore-keyless':
            with tempfile.TemporaryDirectory() as tmp:
                record=pathlib.Path(tmp)/'evidence.json';record.write_bytes(z.read('evidence.json'))
                bundle=pathlib.Path(tmp)/'bundle.json';bundle.write_bytes(z.read('signature.bundle.json'))
                subprocess.run(['cosign','verify-blob','--bundle',str(bundle),'--certificate-identity',f'https://github.com/{repo}/.github/workflows/build-image.yml@refs/heads/main','--certificate-oidc-issuer','https://token.actions.githubusercontent.com',str(record)],check=True)
        elif e.get('signing','unsigned') != 'unsigned':
            raise ValueError('Unknown signing mode')
        for name in ['trivy-image.json','sbom.cdx.json']:
            content=z.read(name)
            if hashlib.sha256(content).hexdigest()!=e['reports'][name]:raise ValueError('Report hash mismatch')
            json.loads(content)
    if e['schema_version']!=1 or e['component']!=component or e['source_repository']!=repo or e['run_id']!=int(run_id):raise ValueError('Evidence identity mismatch')
    if e['run_attempt']!=run['run_attempt'] or e['workflow']!='build-image.yml':raise ValueError('Evidence run mismatch')
    if not re.fullmatch(r'[a-f0-9]{40}',e['source_sha']):raise ValueError('Invalid source SHA')
    if require_current and api(f'repos/{repo}/commits/main')['sha']!=e['source_sha']:raise ValueError('Stale source commit')
    if run['head_sha']!=e['source_sha']:raise ValueError('Run/source mismatch')
    if e['platform']!='linux/arm64':raise ValueError('Unsupported platform')
    if not re.fullmatch(re.escape('phx.ocir.io/axkouhjvgred/online-store/'+component)+r'@sha256:[a-f0-9]{64}',e['image']):raise ValueError('Unapproved image')
    if e['security_policy']!='baseline-report-only':raise ValueError('Unknown security policy')
    ci=api(f'repos/{repo}/actions/runs/{e["ci_run_id"]}')
    if not (ci['conclusion']=='success' and ci['event']=='push' and ci['head_branch']=='main' and ci['head_sha']==e['source_sha'] and ci['path'].split('@')[0]=='.github/workflows/check.yml'):
        raise ValueError('Required source validation not successful')
    return e
