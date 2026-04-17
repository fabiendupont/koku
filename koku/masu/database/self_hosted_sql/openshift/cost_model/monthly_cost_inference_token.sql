INSERT INTO {{schema | sqlsafe}}.reporting_ocpusagelineitem_daily_summary (
    uuid,
    report_period_id,
    cluster_id,
    cluster_alias,
    data_source,
    usage_start,
    usage_end,
    namespace,
    node,
    resource_id,
    all_labels,
    source_uuid,
    cost_model_rate_type,
    cost_model_gpu_cost,
    monthly_cost_type,
    cost_category_id
)
SELECT
    uuid_generate_v4() as uuid,
    {{report_period_id}} as report_period_id,
    {{cluster_id}} as cluster_id,
    {{cluster_alias}} as cluster_alias,
    'InferenceToken' as data_source,
    tok.usage_start,
    tok.usage_start as usage_end,
    tok.namespace as namespace,
    tok.node as node,
    tok.model_name as resource_id,
    jsonb_build_object(
        'model-name', tok.model_name,
        'inference-service', tok.inference_service,
        'input-tokens', tok.input_tokens::varchar,
        'output-tokens', tok.output_tokens::varchar
    ) as all_labels,
    tok.source::uuid as source_uuid,
    {{rate_type}} AS cost_model_rate_type,
    -- Inference token cost calculation:
    -- cost = input_tokens * input_rate + output_tokens * output_rate
    -- For simplicity, a single rate is applied per-token (input + output).
    {%- if rate is defined %}
    (tok.input_tokens + tok.output_tokens) * CAST({{rate}} AS decimal(24,9)) / CAST({{amortized_denominator}} AS decimal(24,9)),
    {%- elif value_rates is defined %}
    CASE
        {%- for value, value_rate in value_rates.items() %}
        WHEN tok.model_name = '{{value | sqlsafe}}'
        THEN (tok.input_tokens + tok.output_tokens) * CAST({{value_rate}} AS decimal(24,9)) / CAST({{amortized_denominator}} AS decimal(24,9))
        {%- endfor %}
        {%- if default_rate is defined %}
        ELSE (tok.input_tokens + tok.output_tokens) * CAST({{default_rate}} AS decimal(24,9)) / CAST({{amortized_denominator}} AS decimal(24,9))
        {%- endif %}
    END,
    {%- elif default_rate is defined %}
    (tok.input_tokens + tok.output_tokens) * CAST({{default_rate}} AS decimal(24,9)) / CAST({{amortized_denominator}} AS decimal(24,9)),
    {%- else %}
    0,
    {%- endif %}
    'Tag' AS monthly_cost_type,
    cat_ns.cost_category_id
FROM {{schema | sqlsafe}}.openshift_inference_token_usage_line_items AS tok
LEFT JOIN {{schema | sqlsafe}}.reporting_ocp_cost_category_namespace AS cat_ns
    ON tok.namespace LIKE cat_ns.namespace
WHERE tok.usage_start >= DATE({{start_date}})
  AND tok.usage_start <= DATE({{end_date}})
  AND tok.source = {{source_uuid}}
  AND tok.year = {{year}}
  AND lpad(tok.month, 2, '0') = {{month}}
  AND tok.model_name LIKE '{{tag_key | sqlsafe}}%'
  {%- if value_rates is defined %}
  AND (
      {%- for value, value_rate in value_rates.items() %}
      {%- if not loop.first %} OR {%- endif %}
      tok.model_name = '{{value | sqlsafe}}'
      {%- endfor %}
  )
  {%- endif %}
RETURNING 1;
