# Agent Billing Design (COST-7165)

**Purpose:** Design proposal for per-agent cost tracking in
Koku, enabling operators to bill for agentic AI workloads
where a single user request triggers multiple LLM calls,
tool executions, and retrieval operations.

**Status:** Prototype implementation — backend API and data model
are implemented; trace collection worker is not yet built.

**Related:** COST-7165 (Implement per-AI agent),
COST-7164 (Cost of MaaS — prerequisite)

---

## Problem

An AI agent is not "one thing" but a bill of materials.
A single agent invocation may involve:

- Multiple LLM calls (reasoning, tool selection, response)
- Tool executions (search, database, API calls)
- Retrieval operations (vector DB lookups)
- Multiple models (cheap model for routing, expensive for
  generation)
- Cache reads and writes

Metric-based billing (COST-7164) tracks tokens per model
per namespace per hour. It cannot answer "how much did
this agent call cost?" because the agent's components are
spread across multiple spans in a trace, not aggregated
in a Prometheus counter.

---

## What OTel GenAI Provides

The OpenTelemetry GenAI semantic conventions define
agent-specific spans and attributes:

### Metric-level (available today)

| Attribute | On `gen_ai.client.token.usage` | Use |
|-----------|-------------------------------|-----|
| `gen_ai.operation.name` | `invoke_agent`, `chat`, `execute_tool`, `embeddings` | Distinguishes agent tokens from direct inference |

This is already collected in our `genai-dimensions` branch.
It enables billing by operation type but not per-agent.

### Span-level (requires trace integration)

| Attribute | Type | Use |
|-----------|------|-----|
| `gen_ai.agent.id` | string | Unique agent identifier |
| `gen_ai.agent.name` | string | Human-readable agent name (billing entity) |
| `gen_ai.agent.version` | string | Agent version |
| `gen_ai.conversation.id` | string | Groups operations in one session |
| `gen_ai.usage.input_tokens` | int | Per-span input token count |
| `gen_ai.usage.output_tokens` | int | Per-span output token count |
| `gen_ai.usage.cache_read.input_tokens` | int | Tokens served from cache (cheaper) |
| `gen_ai.usage.cache_creation.input_tokens` | int | Tokens written to cache |

### Operations hierarchy

```
invoke_agent (root span)
  ├── chat (LLM call — reasoning)
  │   └── gen_ai.usage.input_tokens: 1200
  │       gen_ai.usage.output_tokens: 340
  ├── execute_tool (search API)
  ├── chat (LLM call — process results)
  │   └── gen_ai.usage.input_tokens: 2400
  │       gen_ai.usage.output_tokens: 890
  └── chat (LLM call — final response)
      └── gen_ai.usage.input_tokens: 800
          gen_ai.usage.output_tokens: 1200

Agent cost = sum of all child span token costs
           = (1200+2400+800) × input_rate
           + (340+890+1200) × output_rate
```

---

## Why This Requires Traces, Not Metrics

Prometheus metrics aggregate across time and instances.
`gen_ai.client.token.usage` with `operation_name=invoke_agent`
tells you "this pod consumed X agent tokens in the last hour"
— but not "agent call #12345 cost $0.47 across 3 LLM calls
and 1 tool execution."

Per-agent billing needs per-request granularity:
- Each `invoke_agent` span → one billing record
- Child spans → line items in the agent's bill of materials
- `gen_ai.agent.name` → the billing entity
- `gen_ai.conversation.id` → session-level aggregation

This is fundamentally different from hourly Prometheus
scraping → CSV → Parquet → summary table. It needs a
trace-to-billing pipeline.

---

## Data Sources

### MLflow (primary for RHOAI)

MLflow 3.2+ exports traces with OTel GenAI semantic
conventions when `MLFLOW_ENABLE_OTEL_GENAI_SEMCONV=true`.
Each span carries token counts, model ID, and cost
(calculated by MLflow from provider pricing).

MLflow supports dual export — traces go to both the
MLflow tracking server and an OTel collector
simultaneously.

### OTel Collector → Trace Backend

Traces flow through the RHOAI OTel Collector to a trace
backend (Red Hat build of Tempo). The billing pipeline
would query the trace backend for completed agent traces
and extract billing records.

### LlamaStack

LlamaStack (deployed via RHOAI) also emits OTel traces
with GenAI conventions. Same trace format, same pipeline.

---

## Proposed Architecture

```
Agent call → MLflow/LlamaStack → OTel Collector
                                      │
                                      ▼
                                 Tempo (traces)
                                      │
                                      ▼
                           koku-agent-billing-worker
                           (new: queries Tempo API)
                                      │
                                      ▼
                              Koku backend
                              (new: OCPAgentCostSummaryP)
                                      │
                                      ▼
                      GET /reports/openshift/agents/
```

### Key difference from metric-based billing

| | Metric-based (COST-7164) | Trace-based (COST-7165) |
|---|---|---|
| Data source | Prometheus counters | Tempo trace backend |
| Collection | koku-metrics-operator (hourly CSV) | New worker (periodic Tempo query) |
| Granularity | Per-hour aggregates | Per-request |
| Billing entity | Namespace × model × hour | Agent × invocation |
| Bill of materials | No | Yes (child spans) |

---

## Proposed Data Model

### OCPAgentCostSummaryP

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `cluster_id` | varchar | OpenShift cluster |
| `usage_start` | date | Day |
| `namespace` | varchar | Agent's namespace |
| `agent_name` | varchar | `gen_ai.agent.name` |
| `agent_id` | varchar | `gen_ai.agent.id` |
| `organization` | varchar | Identity-based tenant |
| `invocation_count` | integer | Number of agent calls |
| `total_input_tokens` | decimal | Sum across all spans |
| `total_output_tokens` | decimal | Sum across all spans |
| `cache_read_tokens` | decimal | Tokens from cache |
| `llm_call_count` | integer | Number of LLM calls per invocation |
| `tool_call_count` | integer | Number of tool executions |
| `avg_duration_seconds` | decimal | Average invocation duration |
| `cost_model_agent_cost` | decimal | Calculated cost |
| `cost_model_rate_type` | text | Infrastructure/Supplementary |

---

## Implementation Phases

### Phase 1: Design alignment (this doc)

Get agreement from Koku PM and RHOAI team on:
- Is Tempo the right trace backend to query?
- What trace retention is available?
- Should the agent billing worker be part of
  koku-metrics-operator or a separate component?

### Phase 2: Trace query worker

Build a worker that periodically queries Tempo for
completed `invoke_agent` traces, extracts billing
records, and writes them to CSV or directly to the
Koku database.

### Phase 3: Koku backend

Add `OCPAgentCostSummaryP` model, cost model integration,
and `GET /reports/openshift/agents/` API endpoint.
Follow the same patterns as inference token billing.

### Phase 4: Cache-aware billing

Use `gen_ai.usage.cache_read.input_tokens` to apply
discounts for cached inference. Cached tokens use less
compute and should cost less.

---

## What Is Implemented

- **Data model:** `OCPAgentCostSummaryP` partitioned summary table
  with agent_name, agent_id, model_name, token counts (input/output/cache),
  LLM/tool call counts, invocation count, avg duration, and cost fields.
- **Migration:** `0348_ocpagentcostsummaryp.py`
- **API endpoint:** `GET /reports/openshift/agents/`
  - group_by: cluster, project, agent_name, model_name
  - filter: cluster, project, agent_name, model_name
  - order_by: date, agent_name, model_name, input_tokens, output_tokens,
    invocation_count, cost
- **Feature flag:** `cost-management.backend.ocp_agent_cost_model`
  (enabled by default on-prem via MockUnleashClient)
- **UI summary SQL:** PostgreSQL, Trino, and self-hosted variants
- **Tests:** Endpoint accessibility, group_by, filter, order_by, Unleash gate

### Not yet implemented

- Trace collection worker (Phase 2) — queries Tempo for `invoke_agent` traces
- Cost model rate integration for agents
- Cache-aware billing discounts (Phase 4)

---

## Dependencies

| Dependency | Status | Required for |
|-----------|--------|-------------|
| COST-7164 (token billing) | Prototype complete | Foundation — agent billing extends it |
| MLflow in RHOAI | Shipping in RHOAI 3.x | Primary trace source |
| Tempo in RHOAI | Tech Preview (3.3) | Trace backend to query |
| OTel GenAI semconv GA | Development status | Attribute names may change |
| `genai-dimensions` branch | Prototype complete | `operation_name=invoke_agent` distinguishes agent tokens |

---

## Relationship to COST-7164

COST-7164 (metric-based token billing) and COST-7165
(trace-based agent billing) are complementary:

- COST-7164 answers: "How many tokens did namespace X
  consume on model Y this month?"
- COST-7165 answers: "How much did agent Z cost per
  invocation, and what's the bill of materials?"

Both use the same cost model rates. The agent BOM is
the detail behind the aggregate token counts.

Operators can use COST-7164 alone for simple billing,
or both for detailed agent-level cost visibility.
