# Gateway API CRD installation plan

Status: planning only. This directory is not referenced by the production root
Application. Nothing in this document installs resources.

## Why the CRDs come first

Kubernetes does not provide Gateway API resource types by default. A
CustomResourceDefinition (CRD) adds a type to the Kubernetes API. The API server
must know the GatewayClass, Gateway, HTTPRoute, and ReferenceGrant types before
it can accept those objects or before NGINX Gateway Fabric can manage them.

The read-only check on 2026-10-25 found none of those four CRDs in the OKE
cluster. The active context was `context-devops-prod-cluster-cc4xx4zk64a`.

## Pinned source to review

NGINX Gateway Fabric 2.8.0 documents Gateway API 1.6.3 compatibility and
requires the Gateway API standard-channel CRDs before its controller is
installed. Its installation guide uses this version-pinned Kustomize source:

```text
https://github.com/nginx/nginx-gateway-fabric/config/crd/gateway-api/standard?ref=v2.8.0
```

Use the standard channel for the initial GatewayClass, Gateway, HTTPRoute,
ReferenceGrant, and HTTPS routing work. Do not use an unpinned branch or the
experimental channel without a separate feature review. The upstream source
may contain additional standard-channel CRDs; inspect the complete rendered
set before installation.

Official references:

- https://docs.nginx.com/nginx-gateway-fabric/overview/technical-specifications/
- https://docs.nginx.com/nginx-gateway-fabric/install/helm/
- https://gateway-api.sigs.k8s.io/concepts/versioning/

## Proposed GitOps sequence, each action requires separate approval

1. Render the pinned upstream CRDs locally and review their names, versions,
   and source. Rendering must not include `kubectl apply` or Argo CD sync.
2. Choose and document how Argo CD will track this pinned CRD source. Use a
   separate CRD Application so its cluster-scoped lifecycle is independent of
   the NGINX Gateway Fabric Helm Application and application HTTPRoutes.
3. Review the CRD Application manifest without adding it to
   `environments/prod/kustomization.yaml`. That Kustomization is watched by an
   automatically syncing root Application, so referencing a new Application
   there and pushing to `main` can deploy it.
4. After explicit installation approval, install the CRDs first. Verify they
   are Established and serve the expected versions. Only then consider the
   separately approved NGINX Gateway Fabric controller installation.
5. Treat future CRD upgrades and deletion as cluster-wide changes. Do not
   automatically prune CRDs: deleting one also deletes its custom resources.

The exact Argo CD source layout and manifest will be reviewed in a later step.
This plan does not create an Argo CD Application or a Gateway.

## Read-only checks before and after a future installation

First confirm the intended context:

```bash
kubectl config current-context
```

It must print `context-devops-prod-cluster-cc4xx4zk64a`. To render the pinned
source without contacting or changing the cluster:

```bash
kubectl kustomize \
  'https://github.com/nginx/nginx-gateway-fabric/config/crd/gateway-api/standard?ref=v2.8.0'
```

Review that output before approving any installation. After an approved
installation, list the four initial CRDs without exposing Secret data:

```bash
kubectl --context context-devops-prod-cluster-cc4xx4zk64a get crd \
  gatewayclasses.gateway.networking.k8s.io \
  gateways.gateway.networking.k8s.io \
  httproutes.gateway.networking.k8s.io \
  referencegrants.gateway.networking.k8s.io
```

For each installed CRD, inspect `Established=True` and its served API
versions before installing the controller. A successful CRD installation
does not deploy an NGINX pod, create a LoadBalancer Service, or route traffic.
