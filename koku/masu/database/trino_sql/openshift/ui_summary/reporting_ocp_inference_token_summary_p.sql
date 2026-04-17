INSERT INTO postgres.{{schema | sqlsafe}}.reporting_ocp_inference_token_summary_p (
    id,
    cluster_id,
    cluster_alias,
    usage_start,
    usage_end,
    namespace,
    node,
    model_name,
    inference_service,
    input_tokens,
    output_tokens,
    total_tokens,
    source_uuid
)
SELECT uuid(),
    {{cluster_id}} as cluster_id,
    {{cluster_alias}} as cluster_alias,
    date(itk.interval_start) as usage_start,
    date(itk.interval_start) as usage_end,
    itk.namespace,
    itk.node,
    itk.model_name,
    itk.inference_service,
    sum(itk.input_tokens) as input_tokens,
    sum(itk.output_tokens) as output_tokens,
    sum(itk.input_tokens) + sum(itk.output_tokens) as total_tokens,
    cast({{source_uuid}} as UUID)
FROM hive.{{schema | sqlsafe}}.openshift_inference_token_usage_line_items_daily AS itk
WHERE itk.source = {{source_uuid}}
    AND itk.year = {{year}}
    AND lpad(itk.month, 2, '0') = {{month}} -- Zero pad the month when fewer than 2 characters
    AND date(itk.interval_start) >= date({{start_date}})
    AND date(itk.interval_start) <= date({{end_date}})
GROUP BY itk.namespace,
    itk.node,
    itk.model_name,
    itk.inference_service,
    itk.interval_start
