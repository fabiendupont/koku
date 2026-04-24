INSERT INTO postgres.{{schema | sqlsafe}}.reporting_ocpusagelineitem_daily_summary (
    uuid,
    report_period_id,
    cluster_id,
    cluster_alias,
    data_source,
    usage_start,
    usage_end,
    namespace,
    node,
    all_labels,
    source_uuid,
    cost_model_rate_type,
    cost_model_gpu_cost,
    monthly_cost_type,
    cost_category_id
)
SELECT
    uuid() as uuid,
    {{report_period_id}} as report_period_id,
    {{cluster_id}} as cluster_id,
    {{cluster_alias}} as cluster_alias,
    'Agent' as data_source,
    date(ab.interval_start) as usage_start,
    date(ab.interval_start) as usage_end,
    ab.namespace as namespace,
    ab.node as node,
    cast(map(
        ARRAY['agent-name', 'agent-id', 'model-name', 'organization', 'input-tokens', 'output-tokens', 'cache-read-tokens', 'llm-call-count', 'tool-call-count', 'duration-seconds'],
        ARRAY[
            ab.agent_name,
            ab.agent_id,
            ab.model_name,
            ab.organization,
            CAST(ab.input_tokens AS varchar),
            CAST(ab.output_tokens AS varchar),
            CAST(ab.cache_read_tokens AS varchar),
            CAST(ab.llm_call_count AS varchar),
            CAST(ab.tool_call_count AS varchar),
            CAST(ab.duration_seconds AS varchar)
        ]
    ) as json) as all_labels,
    CAST(ab.source AS uuid) as source_uuid,
    {{rate_type}} AS cost_model_rate_type,
    -- Agent cost = (input_tokens + output_tokens) * rate / amortized_denominator
    -- Cache and SLA discounts are applied via negative markup on the cost model,
    -- not as automatic multipliers. cache_read_tokens is a reporting field for
    -- operators to see cache utilization and decide on markup adjustments.
    {%- if rate is defined %}
    (COALESCE(ab.input_tokens, 0) + COALESCE(ab.output_tokens, 0))
        * (CAST({{rate}} AS decimal(24,9)) / CAST({{amortized_denominator}} AS decimal(24,9))),
    {%- elif value_rates is defined %}
    CASE
        {%- for value, value_rate in value_rates.items() %}
        WHEN ab.agent_name = '{{value | sqlsafe}}'
        THEN (COALESCE(ab.input_tokens, 0) + COALESCE(ab.output_tokens, 0))
            * (CAST({{value_rate}} AS decimal(24,9)) / CAST({{amortized_denominator}} AS decimal(24,9)))
        {%- endfor %}
        {%- if default_rate is defined %}
        ELSE (COALESCE(ab.input_tokens, 0) + COALESCE(ab.output_tokens, 0))
            * (CAST({{default_rate}} AS decimal(24,9)) / CAST({{amortized_denominator}} AS decimal(24,9)))
        {%- endif %}
    END,
    {%- elif default_rate is defined %}
    (COALESCE(ab.input_tokens, 0) + COALESCE(ab.output_tokens, 0))
        * (CAST({{default_rate}} AS decimal(24,9)) / CAST({{amortized_denominator}} AS decimal(24,9))),
    {%- else %}
    0,
    {%- endif %}
    'Tag' AS monthly_cost_type,
    cat_ns.cost_category_id
FROM hive.{{schema | sqlsafe}}.openshift_agent_billing_line_items AS ab
LEFT JOIN postgres.{{schema | sqlsafe}}.reporting_ocp_cost_category_namespace AS cat_ns
    ON ab.namespace LIKE cat_ns.namespace
WHERE date(ab.interval_start) >= DATE({{start_date}})
  AND date(ab.interval_start) <= DATE({{end_date}})
  AND ab.source = {{source_uuid}}
  AND ab.year = {{year}}
  AND lpad(ab.month, 2, '0') = {{month}}
  AND ab.agent_name = '{{tag_key | sqlsafe}}'
  {%- if value_rates is defined %}
  AND (
      {%- for value, value_rate in value_rates.items() %}
      {%- if not loop.first %} OR {%- endif %}
      ab.agent_name = '{{value | sqlsafe}}'
      {%- endfor %}
  )
  {%- endif %}
;
