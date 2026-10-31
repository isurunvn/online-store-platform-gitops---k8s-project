# Schema scope

Gateway and HTTPRoute schemas are extracted from the official Gateway API v1.6.3
CRDs, the version referenced by NGF v2.8.0. Sources:
https://github.com/kubernetes-sigs/gateway-api/tree/v1.6.3/config/crd/standard
Upstream license: Apache-2.0. Kubernetes built-in schemas use kubeconform strict
schemas for v1.36.0 (the cluster runs v1.36.4).

The root Argo Application objects have a scoped exception from kubeconform, with
required source/destination fields and allowed repositories checked in validate.py.
The two external Applications (NGF Helm 2.8.0 and its Gateway CRD bundle) are
allowlisted by exact source/revision. Their remote resource bodies are not rendered
by this local-source validator. Their upgrades require separate chart/CRD review.
No global `ignore-missing-schemas` is used: unknown local resource kinds fail.
