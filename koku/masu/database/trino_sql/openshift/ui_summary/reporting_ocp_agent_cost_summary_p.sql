INSERT INTO postgres.{{schema | sqlsafe}}.reporting_ocp_agent_cost_summary_p (
    id,
    cluster_id,
    cluster_alias,
    usage_start,
    usage_end,
    namespace,
    agent_name,
    agent_id,
    model_name,
    organization,
    input_tokens,
    output_tokens,
    cache_read_tokens,
    total_tokens,
    llm_call_count,
    tool_call_count,
    invocation_count,
    avg_duration_seconds,
    source_uuid,
    cost_category_id
)
SELECT uuid(),
    {{cluster_id}} as cluster_id,
    {{cluster_alias}} as cluster_alias,
    date(ab.interval_start) as usage_start,
    date(ab.interval_start) as usage_end,
    ab.namespace,
    ab.agent_name,
    ab.agent_id,
    ab.model_name,
    ab.organization,
    sum(ab.input_tokens) as input_tokens,
    sum(ab.output_tokens) as output_tokens,
    sum(ab.cache_read_tokens) as cache_read_tokens,
    sum(COALESCE(ab.input_tokens, 0) + COALESCE(ab.output_tokens, 0)) as total_tokens,
    sum(ab.llm_call_count) as llm_call_count,
    sum(ab.tool_call_count) as tool_call_count,
    count(*) as invocation_count,
    avg(ab.duration_seconds) as avg_duration_seconds,
    cast({{source_uuid}} as UUID),
    max(cat_ns.cost_category_id)
FROM hive.{{schema | sqlsafe}}.openshift_agent_billing_line_items AS ab
LEFT JOIN postgres.{{schema | sqlsafe}}.reporting_ocp_cost_category_namespace AS cat_ns
        ON ab.namespace LIKE cat_ns.namespace
WHERE ab.source = {{source_uuid}}
    AND ab.year = {{year}}
    AND lpad(ab.month, 2, '0') = {{month}}
    AND date(ab.interval_start) >= date({{start_date}})
    AND date(ab.interval_start) <= date({{end_date}})
GROUP BY ab.namespace,
    ab.agent_name,
    ab.agent_id,
    ab.model_name,
    ab.organization,
    ab.interval_start
