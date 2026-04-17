DELETE FROM {{schema | sqlsafe}}.reporting_ocp_inference_token_summary_p
WHERE usage_start >= {{start_date}}::date
    AND usage_start <= {{end_date}}::date
    AND source_uuid = {{source_uuid}}::uuid
;

INSERT INTO {{schema | sqlsafe}}.reporting_ocp_inference_token_summary_p (
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
SELECT uuid_generate_v4(),
    {{cluster_id}} as cluster_id,
    {{cluster_alias}} as cluster_alias,
    tok.usage_start,
    tok.usage_start as usage_end,
    tok.namespace,
    tok.node,
    tok.model_name,
    tok.inference_service,
    sum(tok.input_tokens) as input_tokens,
    sum(tok.output_tokens) as output_tokens,
    sum(tok.input_tokens) + sum(tok.output_tokens) as total_tokens,
    {{source_uuid}}::uuid
FROM {{schema | sqlsafe}}.openshift_inference_token_usage_line_items AS tok
WHERE tok.source = {{source_uuid}}
    AND tok.year = {{year}}
    AND lpad(tok.month, 2, '0') = {{month}}
    AND tok.usage_start >= date({{start_date}})
    AND tok.usage_start <= date({{end_date}})
GROUP BY tok.namespace, tok.node, tok.model_name, tok.inference_service, tok.usage_start
RETURNING 1;
