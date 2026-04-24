DELETE FROM {{schema | sqlsafe}}.reporting_ocp_agent_cost_summary_p
WHERE usage_start >= {{start_date}}::date
    AND usage_start <= {{end_date}}::date
    AND source_uuid = {{source_uuid}}
;

INSERT INTO {{schema | sqlsafe}}.reporting_ocp_agent_cost_summary_p (
    id,
    cluster_id,
    cluster_alias,
    namespace,
    usage_start,
    usage_end,
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
    cost_model_agent_cost,
    cost_model_rate_type,
    source_uuid,
    cost_category_id,
    raw_currency
)
    SELECT uuid_generate_v4() as id,
        cluster_id,
        cluster_alias,
        namespace,
        usage_start,
        usage_start as usage_end,
        all_labels->>'agent-name' as agent_name,
        all_labels->>'agent-id' as agent_id,
        all_labels->>'model-name' as model_name,
        all_labels->>'organization' as organization,
        sum((all_labels->>'input-tokens')::numeric) as input_tokens,
        sum((all_labels->>'output-tokens')::numeric) as output_tokens,
        sum((all_labels->>'cache-read-tokens')::numeric) as cache_read_tokens,
        sum(
            COALESCE((all_labels->>'input-tokens')::numeric, 0)
            + COALESCE((all_labels->>'output-tokens')::numeric, 0)
        ) as total_tokens,
        sum((all_labels->>'llm-call-count')::numeric::integer) as llm_call_count,
        sum((all_labels->>'tool-call-count')::numeric::integer) as tool_call_count,
        count(*) as invocation_count,
        avg((all_labels->>'duration-seconds')::numeric) as avg_duration_seconds,
        sum(cost_model_gpu_cost) as cost_model_agent_cost,
        max(cost_model_rate_type) as cost_model_rate_type,
        source_uuid,
        cost_category_id,
        max(raw_currency) as raw_currency
    FROM {{schema | sqlsafe}}.reporting_ocpusagelineitem_daily_summary
    WHERE data_source = 'Agent'
        AND usage_start >= {{start_date}}::date
        AND usage_start <= {{end_date}}::date
        AND source_uuid = {{source_uuid}}
    GROUP BY cluster_id,
        cluster_alias,
        namespace,
        all_labels->>'agent-name',
        all_labels->>'agent-id',
        all_labels->>'model-name',
        all_labels->>'organization',
        usage_start,
        source_uuid,
        cost_category_id
;
