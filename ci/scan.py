#!/usr/bin/env python3
"""Run scanners, retain reports, distinguish findings from execution failures."""
import json, pathlib, subprocess, sys, os
out=pathlib.Path(".ci-output");out.mkdir(exist_ok=True)
mode=sys.argv[1]
def run(args): subprocess.run(args,check=True)
if mode=="source":
    run(["gitleaks","git",".","--redact","--no-banner","--report-format","json","--report-path",str(out/"gitleaks.json")])
    run(["semgrep","scan","--config","ci/semgrep.yml","--metrics=off","--disable-version-check","--error","--json","--output",str(out/"sast.json"),"src"])
    run(["trivy","fs","--quiet","--scanners","vuln,misconfig","--skip-dirs",".git","--skip-dirs","node_modules","--skip-dirs",".ci-output","--format","json","--output",str(out/"trivy-source.json"),"."])
elif mode=="image":
    run(["trivy","image","--quiet","--input",sys.argv[2],"--scanners","vuln","--format","json","--output",str(out/"trivy-image.json")])
    run(["trivy","image","--quiet","--input",sys.argv[2],"--format","cyclonedx","--output",str(out/"sbom.cdx.json")])
elif mode=="config":
    run(["trivy","config","--quiet","--skip-dirs",".terraform","--skip-files","*.tfvars","--skip-files","*.tfstate*","--format","json","--output",str(out/"trivy-config.json"),sys.argv[2]])
else: raise SystemExit("Unknown scan mode")
count=0
for path in out.glob("trivy-*.json"):
    data=json.loads(path.read_text())
    findings=[v for r in data.get("Results",[]) for key in ["Vulnerabilities","Misconfigurations"] for v in (r.get(key) or [])]
    count+=len(findings)
    print(path.name+": "+str(len(findings))+" findings (baseline report-only)")
if count: print("::warning::Trivy findings require triage. Baseline policy does not enforce vulnerability severity yet.")
if os.environ.get("GITHUB_STEP_SUMMARY"):
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:
        f.write(f"\nSecurity mode: {mode}. Trivy findings: {count}. Policy: baseline-report-only. See security reports.\n")
