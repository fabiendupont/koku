import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ("reporting", "0347_add_singleton_to_tenantsettings"),
    ]

    operations = [
        migrations.CreateModel(
            name="OCPInferenceTokenSummaryP",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False)),
                ("cluster_id", models.TextField()),
                ("cluster_alias", models.TextField(null=True)),
                ("namespace", models.CharField(max_length=253, null=True)),
                ("node", models.CharField(max_length=253, null=True)),
                ("usage_start", models.DateField()),
                ("usage_end", models.DateField()),
                ("model_name", models.CharField(max_length=253, null=True)),
                ("inference_service", models.CharField(max_length=253, null=True)),
                ("organization", models.CharField(max_length=253, null=True)),
                ("sla_compliance", models.DecimalField(decimal_places=4, max_digits=5, null=True)),
                ("sla_good", models.DecimalField(decimal_places=4, max_digits=5, null=True)),
                ("sla_degraded", models.DecimalField(decimal_places=4, max_digits=5, null=True)),
                ("sla_breached", models.DecimalField(decimal_places=4, max_digits=5, null=True)),
                ("input_tokens", models.DecimalField(decimal_places=15, max_digits=33, null=True)),
                ("output_tokens", models.DecimalField(decimal_places=15, max_digits=33, null=True)),
                ("total_tokens", models.DecimalField(decimal_places=15, max_digits=33, null=True)),
                ("cost_model_inference_cost", models.DecimalField(decimal_places=15, max_digits=33, null=True)),
                ("cost_model_rate_type", models.TextField(null=True)),
                (
                    "source_uuid",
                    models.ForeignKey(
                        db_column="source_uuid",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="reporting.tenantapiprovider",
                    ),
                ),
                (
                    "cost_category",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="reporting.openshiftcostcategory",
                    ),
                ),
                ("raw_currency", models.TextField(null=True)),
            ],
            options={
                "db_table": "reporting_ocp_inference_token_summary_p",
                "indexes": [
                    models.Index(fields=["usage_start"], name="ocpinftoksumm_usage_start"),
                    models.Index(fields=["cluster_id"], name="ocpinftoksumm_cluster_idx"),
                    models.Index(fields=["namespace"], name="ocpinftoksumm_namespace_idx"),
                    models.Index(fields=["model_name"], name="ocpinftoksumm_model_idx"),
                ],
            },
        ),
    ]
