# Trial expiry and recovery, inspected 31 October 2026

## Verified inventory and limits of this assessment

All 11 Argo CD Applications were Synced/Healthy. Two database PVCs are Bound:
PostgreSQL 50 GiB (`oci-bv-retain`) and RabbitMQ 50 GiB (`oci-bv`). PostgreSQL
and Keycloak share the PostgreSQL server/volume but use separate databases.

Read-only OCI inventory found three OKE A1 workers (each 1 OCPU, 6 GB RAM),
and an additional `oci-vm-01` A1 instance (2 OCPUs, 12 GB RAM). Totals:
1 + 1 + 1 + 2 = 5 OCPUs; 6 + 6 + 6 + 12 = 30 GB RAM.
Boot volumes: 47 + 47 + 47 + 50 = 191 GB. Data volumes: 50 + 50 = 100 GB.
Combined storage: 191 + 100 = 291 GB. A NAT gateway exists; no OCI load balancer
was found. Terraform specifies an ENHANCED_CLUSTER, which is not an Always Free
control-plane entitlement. Confirm the live cluster type in the Console before
making billing decisions. Registry storage and service connectivity remain dependencies.

The exact subscription expiration and remaining credit were NOT confirmed by the
available CLI queries. November 1 is the owner's reported deadline, not an API-
verified expiration timestamp. The installed OneSubscription API requires a plan,
subscription ID or buyer email; no billing identifiers were guessed or exposed.
Check the Console trial banner and subscription page now; record time zone too.

Oracle's current documentation says paid resources may be reclaimed after the
trial ends, while eligible Always Free resources continue. It does not justify
assuming everything disappears at midnight, nor does it guarantee a grace period.
The current Free Tier page states a 2 OCPU/12 GB A1 post-trial allowance; confirm
your own tenancy entitlement because offers and legacy entitlements can differ.
This tenancy's 5 OCPU/30 GB total exceeds even the older 4 OCPU/24 GB allowance.
291 GB also exceeds the documented 200 GB combined Always Free block allowance.
Do not assume a particular volume is protected merely because it is individually
small. NAT, enhanced OKE, registry and network services must be assessed separately;
no claim of end-to-end Always Free availability is made.

Sources checked 31 October 2026:
- https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm
- https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- https://docs.oracle.com/en-us/iaas/Content/GSG/Tasks/signingup_topic-What_Happens_When_the_Promotion_Expires.htm

## Export before the deadline

These are opt-in instructions. No data backups were created automatically.
Use a protected directory OUTSIDE all five repositories on an encrypted local
volume. Keep a second protected copy. `umask 077` is essential. Never upload these
files to Actions or Git, paste their contents, or commit credentials.

1. PostgreSQL: export both databases plus global roles. The dumps contain customer
   data and Keycloak identity data. The globals export contains password hashes.
   Keep the existing image/version recorded with the dumps.

   ```bash
   umask 077
   backup_dir="$HOME/online-store-recovery-$(date +%Y%m%d-%H%M%S)"
   mkdir -m 700 "$backup_dir"
   ctx=context-devops-prod-cluster-cc4xx4zk64a
   for db in online_store keycloak; do
     kubectl --context "$ctx" -n data exec postgresql-0 -- \
       sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" exec pg_dump -h 127.0.0.1 -U "$POSTGRES_USER" -Fc "$1"' sh "$db" \
       > "$backup_dir/$db.dump"
   done
   kubectl --context "$ctx" -n data exec postgresql-0 -- \
     sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" exec pg_dumpall -h 127.0.0.1 -U "$POSTGRES_USER" --globals-only' \
     > "$backup_dir/postgres-globals.sql"
   ```

   Check command exit codes and nonempty files; `pg_restore --list` validates
   readability but is not a restore test. Test restoring in a disposable local
   PostgreSQL 17 instance before considering the backup proven. Independent
   database dumps are not one distributed application transaction snapshot.

2. Keycloak: its full persistent state is in `keycloak.dump`. The Git realm import
   is only bootstrap configuration and does not include later users/passwords.
   Preserve the image version and hostname/client configuration. Do not overwrite
   a restored realm by assuming a fresh import is equivalent.

3. RabbitMQ: export definitions through the management UI using a localhost-only
   port-forward. Store the export in the protected directory. It may contain user
   password hashes. Definitions preserve topology/users/policies, NOT queued
   messages. Record queue depth and drain the demo queues deliberately if appropriate.
   Preserving queued messages requires a separately planned, consistent broker-data
   backup/restoration procedure with matching node identity and version. Retaining
   a volume is not a tested backup. Do not stop the broker automatically.

4. Secrets: retain original passwords/auth tokens securely in your password manager.
   If a Kubernetes Secret export is necessary, explicitly redirect it only to the
   protected directory, never a terminal or CI log. No Secret values were exported
   during this implementation. Recreate per-namespace credentials during recovery.

5. Terraform: copy local state and lock file to protected storage. State can contain
   secrets. Preserve `.tfvars` separately and encrypted. Never put state/tfvars in a
   workflow artifact. Record resource ownership, region and provider version.

6. Git and images: push reviewed source branches and preserve selected release
   evidence/SBOM artifacts before retention expiry. Export the deployed ARM64 images
   locally with authenticated registry access if registry survival is uncertain.
   Verify digests before and after export. Git alone does not contain image layers.

## Recovery order

Verify account/quota access; review Terraform plan manually; provision only with
explicit approval. Restore namespaces/Secrets, PostgreSQL roles/databases, RabbitMQ
configuration/data, Keycloak, then application images and gateway configuration.
Bootstrap Argo CD and review sync settings before allowing production reconciliation.
Run `scripts/verify-deployment.py`, then test login, catalog, checkout and notification
behavior. A healthy pod alone is not an end-to-end recovery test.

## Teardown checklist, never automatic

Inventory Terraform-owned infrastructure, CSI-created data volumes and the separate
VM. Verify backups and record which volumes must survive. Review a protected local
`terraform plan -destroy` only with authorization; do not upload the plan or state.
Check PVC retention, PV reclaim policy and OCI ownership separately. PostgreSQL uses
Retain; RabbitMQ's default StorageClass uses Delete, even if the StatefulSet retains
its claims. Do not delete claims or remove protection annotations as a cleanup shortcut.
Only an explicitly approved teardown may run destroy or delete resources. Afterwards
verify orphan volumes, NAT, registry storage and billing in the Console. No billing
upgrade, shutdown, deletion or paid provisioning was performed by this task.
