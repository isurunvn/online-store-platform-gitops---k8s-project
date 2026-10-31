#!/usr/bin/env python3
"""Read-only live checks and localhost-only port forwarding. Requires kubectl."""
import argparse,json,socket,subprocess,time,urllib.request
parser=argparse.ArgumentParser();parser.add_argument('--context',required=True)
parser.add_argument('--gateway-service',default='online-store-gateway-nginx')
a=parser.parse_args();kubectl=['kubectl','--context',a.context]
def get(*args):return subprocess.check_output(kubectl+list(args),text=True)
apps=json.loads(get('-n','argocd','get','applications','-o','json'))['items']
for app in apps:
 s=app.get('status',{});name=app['metadata']['name']
 if s.get('sync',{}).get('status')!='Synced' or s.get('health',{}).get('status')!='Healthy':raise SystemExit(name+' is not Synced/Healthy')
 print(name+': Synced/Healthy')
for name in ['backend','frontend','notification-service']:
 subprocess.run(kubectl+['-n','online-store','rollout','status','deployment/'+name,'--timeout=120s'],check=True)
def check(namespace,service,remote,paths):
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 p=subprocess.Popen(kubectl+['-n',namespace,'port-forward','--address','127.0.0.1','service/'+service,f'{port}:{remote}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  for path,kind in paths:
   for attempt in range(40):
    if p.poll() is not None:raise SystemExit('Port-forward failed for '+service)
    try:
     with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=3) as r:body=r.read()
     break
    except OSError:time.sleep(0.25)
   else:raise SystemExit('HTTP check failed: '+service+path)
   if kind=='health' and json.loads(body).get('status')!='UP':raise SystemExit(service+' unhealthy')
   if kind=='products' and 'content' not in json.loads(body):raise SystemExit('Unexpected API response')
   if kind=='html' and b'<html' not in body.lower():raise SystemExit('Unexpected frontend response')
   print(service+path+': PASS')
 finally:
  p.terminate()
  try:p.wait(timeout=5)
  except subprocess.TimeoutExpired:p.kill();p.wait()
check('online-store','backend',8083,[('/actuator/health','health')])
check('online-store','notification-service',8084,[('/actuator/health','health')])
check('online-store','frontend',8080,[('/healthz','text'),('/','html')])
check('platform',a.gateway_service,80,[('/','html'),('/api/products','products'),('/realms/online-store/.well-known/openid-configuration','json')])
print('Read-only smoke tests passed. Customer login/checkout/email delivery need separate functional testing.')
