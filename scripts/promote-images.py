#!/usr/bin/env python3
"""Update local GitOps image digests. Does not commit, push, or contact Kubernetes."""
import argparse
from pathlib import Path
import re

parser = argparse.ArgumentParser(description=__doc__)
for component in ("backend", "frontend", "notification-service"):
    parser.add_argument("--" + component, help="Full OCIR image reference ending in @sha256:<64 hex characters>")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
updates = {}
for component in ("backend", "frontend", "notification-service"):
    image = getattr(args, component.replace("-", "_"))
    if not image:
        continue
    if not re.fullmatch(r"phx\.ocir\.io/axkouhjvgred/online-store/" + re.escape(component) + r"@sha256:[a-f0-9]{64}", image):
        parser.error("Invalid digest reference for " + component)
    path = root / "apps" / component / "base/deployment.yaml"
    original = path.read_text()
    updated, count = re.subn(r"(?m)^(\s*(?:- )?image:) .+$", lambda m: m[1] + " " + image, original)
    if count != 1:
        parser.error("Expected exactly one container image in " + str(path))
    updates[path] = updated
if not updates:
    parser.error("Provide at least one image digest")
kustomization = root / "environments/prod/kustomization.yaml"
content = kustomization.read_text()
for component in ("frontend", "notification-service"):
    if getattr(args, component.replace("-", "_")):
        entry = "  - apps/" + component + ".yaml"
        if entry not in content.splitlines():
            content += entry + "\n"
updates[kustomization] = content
for path, content in updates.items():
    path.write_text(content)
    print("Updated", path.relative_to(root))
print("Review, render, then commit and push to deploy through Argo CD.")
