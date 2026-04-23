DELETE FROM {{schema | sqlsafe}}.reporting_ocp_inference_token_summary_p
WHERE usage_start >= {{start_date}}::date
    AND usage_start <= {{end_date}}::date
    AND source_uuid = {{source_uuid}}
;

INSERT INTO {{schema | sqlsafe}}.reporting_ocp_inference_token_summary_p (
    id,
    cluster_id,
    cluster_alias,
    namespace,
    node,
    usage_start,
    usage_end,
    model_name,
    inference_service,
    organization,
    sla_compliance,
    sla_good,
    sla_degraded,
    sla_breached,
    input_tokens,
    output_tokens,
    total_tokens,
    cost_model_inference_cost,
    source_uuid,
    cost_model_rate_type
)
    SELECT uuid_generate_v4() as id,
        cluster_id,
        cluster_alias,
        namespace,
        node,
        usage_start,
        usage_start as usage_end,
        all_labels->>'model-name' as model_name,
        all_labels->>'inference-service' as inference_service,
        all_labels->>'organization' as organization,
        avg((all_labels->>'sla-compliance')::numeric) as sla_compliance,
        avg((all_labels->>'sla-good')::numeric) as sla_good,
        avg((all_labels->>'sla-degraded')::numeric) as sla_degraded,
        avg((all_labels->>'sla-breached')::numeric) as sla_breached,
        sum((all_labels->>'input-tokens')::numeric) as input_tokens,
        sum((all_labels->>'output-tokens')::numeric) as output_tokens,
        sum((all_labels->>'input-tokens')::numeric) + sum((all_labels->>'output-tokens')::numeric) as total_tokens,
        sum(cost_model_gpu_cost) as cost_model_inference_cost,
        source_uuid,
        max(cost_model_rate_type) as cost_model_rate_type
    FROM {{schema | sqlsafe}}.reporting_ocpusagelineitem_daily_summary
    WHERE data_source = 'InferenceToken'
        AND usage_start >= {{start_date}}::date
        AND usage_start <= {{end_date}}::date
        AND source_uuid = {{source_uuid}}
    GROUP BY cluster_id,
        cluster_alias,
        namespace,
        node,
        all_labels->>'model-name',
        all_labels->>'inference-service',
        all_labels->>'organization',
        usage_start,
        source_uuid
;
