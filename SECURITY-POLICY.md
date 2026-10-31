# Security policy and baseline

Secret detections (Gitleaks with redaction), selected high-confidence local
Semgrep rules, tests, compiler failures and invalid deployment references block CI.
Scanner execution failures also block; a missing report is never a clean report.

Trivy dependency and misconfiguration findings initially produce visible JSON
reports and workflow warnings. This is a deliberate baseline stage, not a claim
that vulnerabilities passed a severity gate. The publication evidence records
`baseline-report-only`. Never describe these images as vulnerability-free.
Before changing this policy to block High/Critical findings, triage the reports,
fix reachable/fixable problems, and review remaining findings. Known exploitable
serious issues require explicit release acceptance even during baseline rollout.

Exceptions must name the rule/CVE, exact package/resource, rationale, owner,
approval and expiry. No blanket `ignore-unfixed`, global skip, or silently ignored
scanner error is permitted. No vulnerability exceptions are pre-approved here.
Reports expire after 14 days; release evidence after 90 days. Archive selected
release evidence securely before expiry. SBOMs may reveal private package names.

Semgrep CE 1.183.0 is LGPL-2.1. The repository-authored rules are a small starting
set, not comprehensive SAST. No Semgrep SaaS login or private source upload is used.
CodeQL private-repository entitlement was not established, so it is not enabled.
Trivy is Apache-2.0 and Gitleaks CLI is MIT. Review licenses again on upgrades.

Official references:
- https://semgrep.dev/products/community-edition/
- https://docs.github.com/en/code-security/reference/code-scanning/troubleshoot-analysis-errors/private-repository-enablement
- https://github.com/aquasecurity/trivy/blob/main/LICENSE
- https://github.com/gitleaks/gitleaks/blob/master/LICENSE
