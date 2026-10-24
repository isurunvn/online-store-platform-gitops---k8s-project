# Keycloak database setup plan

## Summary

Keycloak will use the existing PostgreSQL server in the `data` namespace, but it
will have its own `keycloak` database and `keycloak_app` login role. Both
databases will share the PostgreSQL pod and its existing persistent volume.
This document is a plan only. Nothing here runs automatically through Argo CD.

Read-only inspection on 2026-10-24 found the `online_store` database and the
`online_store_admin` bootstrap superuser. It found no `keycloak` database or
`keycloak_app` role. The PostgreSQL Service has one ready endpoint on port 5432.

## 1. Review the existing database and privileges

**What:** Before any change, list database names, owners, login roles, and
database connection grants using read-only PostgreSQL catalog queries.

**Why:** A dedicated Keycloak role should not inherit broad access to the
online-store database. PostgreSQL may grant database `CONNECT` to `PUBLIC`, so
separate database names alone do not guarantee connection isolation.

**Example queries:**

```sql
SELECT datname, pg_get_userbyid(datdba) AS owner, datacl
FROM pg_database
WHERE datname IN ('online_store', 'keycloak');

SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole
FROM pg_roles
WHERE rolname IN ('online_store_admin', 'keycloak_app');
```

## 2. Prepare a dedicated Keycloak credential

**What:** Generate a unique, strong password and keep it in the chosen password
manager. Do not put it in this repository, a SQL file, a shell command line,
or terminal output. Enter it interactively when setting the PostgreSQL role
password. Later, create a separate Kubernetes Secret named
`identity/keycloak-db-auth` with key `KC_DB_PASSWORD` containing the same value.
The non-secret username can be configured as `KC_DB_USERNAME=keycloak_app`.

**Why:** Keycloak must not reuse `data/postgresql-auth`, which is the password
for the PostgreSQL bootstrap superuser. Kubernetes Secrets are namespace-scoped,
so an `identity` pod cannot directly reference a Secret in `data`.

**Example:** In an interactive `psql` session, `\password keycloak_app` prompts
for the role password without writing it into the SQL history. Do this only
after the role exists and after separate approval for database changes.

## 3. Create the role and database after approval

**What:** In separately approved actions, create a login role without elevated
server privileges, set its password interactively, then create a database it
owns. The following SQL is for review and must not be executed as part of this
documentation step:

```sql
CREATE ROLE keycloak_app
  LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;

-- In interactive psql, use: \password keycloak_app

CREATE DATABASE keycloak OWNER keycloak_app;
REVOKE CONNECT ON DATABASE keycloak FROM PUBLIC;
GRANT CONNECT ON DATABASE keycloak TO keycloak_app;
```

**Why:** Keycloak must be able to create and update its own tables without
having superuser or database-creation privileges. Database ownership gives it
control of its own database. The existing bootstrap superuser will still have
server-wide administrative access.

**Example connection target:**

```text
jdbc:postgresql://postgresql.data.svc.cluster.local:5432/keycloak
```

`CREATE DATABASE` must run outside a transaction block. Review the current
`online_store` database grants before separately deciding whether to revoke
`CONNECT` from `PUBLIC` there and grant it only to intended application roles.
That change must account for any clients that exist at execution time.

## 4. Verify without revealing credentials

**What:** After the future database actions, rerun the queries in step 1 and
test a connection using the dedicated role. Check only Secret metadata, such as
its name and key names, in Kubernetes.

**Why:** A successful catalog check proves the role and database exist. A
connection test proves the credential, Service DNS, and permissions work
together. It does not require printing the password.

**Example queries for the future connection test:**

```sql
SELECT current_database(), current_user;
SELECT has_database_privilege('keycloak_app', 'online_store', 'CONNECT');
```

The first query should return `keycloak` and `keycloak_app`. The second should
return `false` only after connection privileges on `online_store` have been
reviewed and restricted. Do not assume it is already false.

Reference: [PostgreSQL 17 CREATE ROLE](https://www.postgresql.org/docs/17/sql-createrole.html),
[CREATE DATABASE](https://www.postgresql.org/docs/17/sql-createdatabase.html), and
[database privileges](https://www.postgresql.org/docs/17/ddl-priv.html).
