# Tenant Provider Model for Service Provider Billing

**Purpose:** Design proposal for pluggable tenant identification
in Koku, enabling tamper-proof cost attribution for service
providers, sovereign clouds, and managed OpenShift deployments.

**Related:** COST-7102 (Service provider tenancy model),
COST-7106 (Cost Management for Sovereign Cloud)

---

## Problem

Koku identifies tenants via Kubernetes namespaces and
user-controlled labels. This works for internal IT
(teams won't cheat) but not for service providers billing
external customers:

- **Namespaces** are operator-controlled but coarse — a
  tenant may span multiple namespaces, or multiple tenants
  may share a namespace.
- **Labels** (e.g., `tenant=customer-123`) can be modified
  by the tenant. An untrusted tenant could change their
  label to reduce their bill.

Every major cloud provider solved this by tying billing
to an **identity plane** the tenant cannot modify:

| Provider | Tenant identity | Tamper-proof |
|----------|----------------|-------------|
| AWS | Account ID | Yes |
| Azure | AD Tenant + Subscription | Yes |
| GCP | Project ID | Yes |
| OpenStack | Keystone Project | Yes |
| Koku (today) | Namespace + labels | No |

Koku needs an equivalent mechanism for OpenShift-based
service providers.

---

## Proposal: Pluggable Tenant Providers

Instead of hardcoding one tenant identification strategy,
introduce a **tenant provider** abstraction — a pluggable
mapping from Kubernetes resources (namespaces, labels,
clusters) to an operator-controlled tenant identity.

```
Koku Data Pipeline
    │
    ▼
Tenant Resolution (pluggable)
    │  input: namespace, labels, cluster_id
    │  output: tenant_id, tenant_name
    ▼
Cost Attribution
    │  costs grouped by tenant_id
    ▼
Reports API
    └── group_by[tenant], filter[tenant]
```

The tenant provider is a **mapping function**, not a new
data source. It resolves tenant identity from metadata
the koku-metrics-operator already collects.

---

## Tenant Providers

### 1. Namespace (default, current behavior)

```
tenant_id = namespace
```

No configuration needed. Works today. Sufficient for
internal IT chargeback where namespaces map 1:1 to teams.

### 2. Label-based (current behavior)

```
tenant_id = labels["tenant"]  # configurable key
```

Works today via cost model tag-based rates. Vulnerable
to tenant label modification in service provider
scenarios.

### 3. OSAC Tenant CRD

```
tenant_id = osac_tenant.id  (from Tenant CR)
```

OSAC's `Tenant` CRD is the registration point for
service provider tenants. When a tenant is created, the
osac-operator maps tenant → namespaces, clusters,
quotas. These mappings are operator-controlled — tenants
cannot modify their Tenant CR.

**How it works:**
- koku-metrics-operator queries the OSAC API (or reads
  Tenant CRs via the Kubernetes API) for the
  tenant→namespace mapping
- Adds `osac_tenant_id` to the CSV report as an
  additional column
- Koku resolves namespace → tenant_id via this mapping
- Reports support `group_by[tenant]` and
  `filter[tenant]`

**Where it works:** Any OpenShift deployment with OSAC
— bare metal, cloud, virtualized. No infrastructure
controller dependency.

### 4. Cloud Account

```
tenant_id = cloud_account_id
```

On managed OpenShift services (ROSA, ARO, OSD), the
cloud account is the natural tenant identity:

| Platform | Tenant identity | Source |
|----------|----------------|--------|
| ROSA | AWS Account ID | AWS billing data already in Koku |
| ARO | Azure Subscription ID | Azure billing data already in Koku |
| OSD | GCP Project ID | GCP billing data already in Koku |

Koku already has this data for cloud cost reports. The
extension is mapping OCP-on-cloud clusters to their
cloud account and using that as the tenant identity for
OCP reports.

### 5. Operator-Defined Mapping (CMDB)

```
tenant_id = koku_db.tenant_mapping[(cluster_id, namespace)]
```

For self-managed OpenShift without OSAC, operators define
tenant→resource mappings directly in Koku. This is
COST-7102 option (b): a CRUD interface for tenant
definitions stored in Koku's database.

**How it works:**
- New API: `POST /tenants/` to create tenant definitions
  with associated clusters/namespaces
- Koku resolves namespace → tenant_id via its own DB
- No external dependency
- Operator-controlled — tenants have no access to the
  mapping API

### 6. External Identity Providers (future)

The pluggable model supports additional providers as
the ecosystem evolves:

- **NICo Org/Tenant** — for NCP deployments using
  NVIDIA's infrastructure controller, tenant identity
  comes from NICo's Keycloak-backed Org/Tenant model
- **Kessel** — Red Hat's emerging authorization service
- **Custom webhook** — operator-provided endpoint that
  resolves tenant from namespace/labels

---

## Implementation Approach

### Phase 1: Tenant resolution in the data pipeline

Add a `tenant_id` column to the daily summary table,
populated during data processing:

```python
class TenantProvider:
    def resolve(self, namespace, labels, cluster_id) -> str:
        raise NotImplementedError

class NamespaceTenantProvider(TenantProvider):
    def resolve(self, namespace, labels, cluster_id):
        return namespace

class OSACTenantProvider(TenantProvider):
    def __init__(self, tenant_mappings):
        self.ns_to_tenant = tenant_mappings

    def resolve(self, namespace, labels, cluster_id):
        return self.ns_to_tenant.get(
            (cluster_id, namespace), namespace
        )
```

The provider is selected per cost model (or globally),
matching COST-7164's requirement that metric selection
should be "per cost model."

### Phase 2: Report API

Add `tenant` as a group-by and filter dimension to all
OCP report types (costs, GPU, inference tokens, volumes).
This is a cross-cutting change — it applies to all
reports, not just new ones.

### Phase 3: UI

Add a tenant management page for the CMDB provider
(operator-defined mappings). For OSAC and cloud account
providers, the mapping is automatic — no UI needed.

---

## Relationship to Existing Features

### Cost Model Tag-Based Rates

Tag-based rates (COST-7164 requirement) remain
unchanged. The tenant provider adds a separate
dimension — you can have both:

- `group_by[tenant]` → operator-controlled identity
- Tag-based rates → per-model or per-tag pricing

They're complementary: the tenant says **who pays**,
the tag-based rate says **how much**.

### Inference Token Billing

Our inference token billing implementation uses
namespace as the tenant dimension today. When a tenant
provider is configured, it would automatically resolve
namespace → tenant_id. No changes to the token billing
code — the resolution happens in the data pipeline
before the summary tables are populated.

### GPU Billing

Same as inference tokens — GPU reports would inherit
tenant resolution automatically.

---

## What This Solves

| COST ticket | How tenant providers address it |
|-------------|-------------------------------|
| COST-7102 | Service providers get tamper-proof tenant identity via OSAC, cloud account, or CMDB provider |
| COST-7164 | Token billing supports per-tenant attribution via resolved tenant_id |
| COST-7165 | Agent billing inherits tenant resolution — agent costs attributed to the correct tenant |
| COST-7106 | Sovereign cloud operators get the billing infrastructure they need |

---

## Effort Estimate

| Phase | What | Effort |
|-------|------|--------|
| Phase 1 | Tenant provider interface + namespace/CMDB providers + pipeline integration | 4-6 weeks |
| Phase 2 | Report API `group_by[tenant]` across all OCP reports | 2-3 weeks |
| Phase 3 | CMDB tenant management UI | 3-4 weeks |
| OSAC provider | Query Tenant CR for namespace mappings | 1-2 weeks |
| Cloud account provider | Map OCP-on-cloud clusters to cloud accounts | 1-2 weeks |

Phase 1 + 2 deliver value without UI — operators can
configure tenant mappings via API and query reports
programmatically. Phase 3 adds the UI for non-technical
operators.
