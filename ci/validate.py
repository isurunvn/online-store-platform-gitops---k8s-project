#!/usr/bin/env python3
"""Render active local Applications without contacting a Kubernetes cluster."""
import pathlib
import re
import subprocess
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = "https://github.com/isurunvn/online-store-platform-gitops---k8s-project.git"
APPS = {name: f"phx.ocir.io/axkouhjvgred/online-store/{name}" for name in
        ("backend", "frontend", "notification-service")}
EXTERNAL = {
    "gateway-api-crds": ("https://github.com/nginx/nginx-gateway-fabric.git", "v2.8.0", "config/crd/gateway-api/standard"),
    "nginx-gateway-fabric": ("ghcr.io/nginx/charts", "2.8.0", "nginx-gateway-fabric"),
}


def check_image(app, image):
    if not isinstance(image, str) or any(p in image.upper() for p in
            ("BUILD_REQUIRED", "REPLACE_ME", "CHANGEME", "TODO", "<DIGEST>")):
        raise ValueError(f"{app}: missing or placeholder image")
    if app in APPS and not re.fullmatch(re.escape(APPS[app]) + r"@sha256:[a-f0-9]{64}", image):
        raise ValueError(f"{app}: expected approved OCIR repository and immutable SHA256 digest")


def local_path(source):
    path = (ROOT / source).resolve()
    if not path.is_relative_to(ROOT) or path == ROOT:
        raise ValueError("Application source escapes repository")
    return path


def render(path):
    result = subprocess.run(["kustomize", "build", str(path)], check=True, capture_output=True, text=True)
    return [d for d in yaml.safe_load_all(result.stdout) if d]


def validate():
    output = ROOT / ".ci-output" / "rendered"
    output.mkdir(parents=True, exist_ok=True)
    applications = render(ROOT / "environments/prod")
    seen = set()
    for app in applications:
        if app.get("apiVersion") != "argoproj.io/v1alpha1" or app.get("kind") != "Application":
            raise ValueError("Production root must contain only Argo CD Applications")
        name = app["metadata"]["name"]
        if name in seen or not re.fullmatch(r"[a-z0-9-]+", name):
            raise ValueError("Duplicate or invalid Application name")
        seen.add(name)
        spec = app["spec"]
        assert spec["project"] and spec["destination"]["server"] == "https://kubernetes.default.svc"
        source = spec["source"]
        if source["repoURL"] != REPO:
            actual = (source["repoURL"], source["targetRevision"], source.get("path", source.get("chart")))
            if EXTERNAL.get(name) != actual:
                raise ValueError(f"Unreviewed external source: {name}")
            print(f"{name}: pinned external source, scoped schema/render exception; see ci/schemas/README.md")
            continue
        docs = render(local_path(source["path"]))
        for doc in docs:
            kind = doc["kind"]
            if kind == "Secret":
                raise ValueError(f"{name}: Secret resources require a separately approved encrypted-secret design")
            template = doc.get("spec", {}).get("template", {}).get("spec", {})
            for container in template.get("containers", []) + template.get("initContainers", []):
                check_image(name, container.get("image"))
        target = output / (name + ".yaml")
        target.write_text(yaml.safe_dump_all(docs, sort_keys=False))
        subprocess.run(["kubeconform", "-strict", "-summary", "-kubernetes-version", "1.36.0",
                        "-schema-location", "https://raw.githubusercontent.com/yannh/kubernetes-json-schema/47163ead3738a996c3e30be9691bb37b8071d9d3/{{ .NormalizedKubernetesVersion }}-standalone{{ .StrictSuffix }}/{{ .ResourceKind }}{{ .KindSuffix }}.json", "-schema-location",
                        str(ROOT / "ci/schemas/{{ .Group }}/{{ .ResourceKind }}_{{ .ResourceAPIVersion }}.json"),
                        str(target)], check=True)
        print(f"{name}: {len(docs)} resources validated")
    if not set(APPS).issubset(seen):
        raise ValueError("Application activation changes require explicit review; expected three active application sources")


if __name__ == "__main__":
    try:
        validate()
    except (ValueError, KeyError, AssertionError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"GitOps validation failed: {exc}")
