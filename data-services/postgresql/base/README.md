# PostgreSQL for OKE

This base prepares one PostgreSQL 17.11 instance in the existing `data` namespace. It is not enabled by the production environment Kustomization. Review the files, create the Secret and backup process, and explicitly approve synchronization before adding `environments/prod/apps/postgresql.yaml` to `environments/prod/kustomization.yaml`.

## Runtime and storage

- `postgres:17.11-bookworm` is an explicit PostgreSQL minor version with an ARM64 image. Review and update the image tag on each supported minor release; tags can be republished, so pin a verified multi-architecture digest as well if immutable images are required.
- The `postgresql` ClusterIP Service listens on 5432. `postgresql-headless` gives the StatefulSet a stable network identity. Neither service exposes the database outside the cluster.
- The StatefulSet requests 100m CPU and 512Mi memory, with limits of 500m CPU and 1Gi memory. These are starting values for a small workload; monitor memory, CPU throttling, connections, I/O, and query latency before increasing traffic.
- The `postgresql-data-postgresql-0` PVC will request 50Gi, `ReadWriteOnce`, from the nondefault `oci-bv-retain` StorageClass. The StorageClass uses the same OCI CSI provisioner, binding mode, and expansion setting as the cluster's default `oci-bv` class, but sets `reclaimPolicy: Retain`.
- Both StatefulSet PVC retention settings are `Retain`. Deleting the StatefulSet will leave its PVC; deleting that PVC will leave its PV and OCI Block Volume in the `Released` state for deliberate recovery or disposal. The volume can continue to incur charges until separately removed.

## Credentials and access

`postgresql-config` supplies the bootstrap database name and administrator username. Before any sync, create a strong, unique password in a password manager and create a `data/postgresql-auth` Secret with the single key `POSTGRES_PASSWORD`. For a one-time manual bootstrap, the following interactive example keeps the value out of the command line, shell history, and Git:

```bash
read -rsp 'PostgreSQL bootstrap password: ' POSTGRES_BOOTSTRAP_PASSWORD
printf '\n'
printf %s "$POSTGRES_BOOTSTRAP_PASSWORD" | kubectl --context context-devops-prod-cluster-cc4xx4zk64a -n data create secret generic postgresql-auth --from-file=POSTGRES_PASSWORD=/dev/stdin
unset POSTGRES_BOOTSTRAP_PASSWORD
```

Restrict RBAC access to Secrets, confirm Kubernetes Secret encryption at rest, and keep the password in the password manager for recovery. A future OCI Vault plus External Secrets integration would automate rotation and reconciliation, but requires a separately approved controller and OCI permissions. Do not commit a Secret manifest or a generated password. The PostgreSQL image uses `POSTGRES_USER` as a bootstrap superuser; create a separate least-privilege application role and its own Secret before deploying the backend. Changing these bootstrap variables or the Kubernetes Secret does not alter credentials in an initialized database; rotate the database role and Secret together.

Before connecting applications, decide how to enforce PostgreSQL client TLS and restrict port 5432 to approved namespaces or workloads. A ClusterIP Service is internal to Kubernetes but does not itself enforce either control. Confirm that the cluster CNI enforces Kubernetes NetworkPolicies before relying on one.

## Backup and recovery gate

Before production data is written, define an RPO, RTO, retention period, and backup owner. At minimum, schedule PostgreSQL-aware logical backups to a separate, encrypted OCI Object Storage location and test a restore into an isolated database. If point-in-time recovery is required, use coordinated base backups plus continuous WAL archiving, verify archive health, and rehearse a restore. Keep backup credentials outside Git. A retained Block Volume is useful for accidental PVC deletion but does not recover from data corruption, accidental SQL changes, or loss of the volume's failure domain. This single replica is not highly available; node or volume reattachment failures will interrupt service.

## GitOps rollout

The prepared `environments/prod/apps/postgresql.yaml` Application has no automated sync policy and is intentionally absent from `environments/prod/kustomization.yaml`. The child Application disables pruning and deletion of its managed resources. Its own annotations protect the Application if the parent stops managing it. The Secret is created outside Argo CD, so Argo CD does not manage or prune it. The generated PVC is retained by StatefulSet policy, and the resulting PV inherits `Retain` from the StorageClass. Operators must still handle deliberate cleanup, including retained OCI volumes.

Before enabling the Application, verify the `data` namespace exists, the Secret is present, the OCI CSI driver is healthy, backup and restore are ready, and the node has room for the requested resources. Then add the Application file to the production Kustomization and manually synchronize the child Application after review.
