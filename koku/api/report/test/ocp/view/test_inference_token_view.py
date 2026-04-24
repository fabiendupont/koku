#
# Copyright 2025 Red Hat Inc.
# SPDX-License-Identifier: Apache-2.0
#
"""Test the Inference Token Report views."""
from unittest.mock import patch
from urllib.parse import urlencode

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from api.iam.test.iam_test_case import IamTestCase


class OCPInferenceTokenViewTest(IamTestCase):
    """Tests for the inference token report view."""

    def setUp(self):
        """Set up the customer view tests."""
        super().setUp()
        self.client = APIClient()

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=True)
    def test_inference_token_endpoint_exists(self, mock_unleash):
        """Test that the inference token endpoint is accessible."""
        url = reverse("reports-openshift-inference-tokens")
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=True)
    def test_group_by_model_name(self, mock_unleash):
        """Test inference token endpoint with group_by model_name."""
        url = reverse("reports-openshift-inference-tokens")
        query_params = {"group_by[model_name]": "*"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=True)
    def test_filter_by_model_name(self, mock_unleash):
        """Test inference token endpoint with filter by model_name."""
        url = reverse("reports-openshift-inference-tokens")
        query_params = {"filter[model_name]": "llama-3-8b"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=False)
    def test_endpoint_blocked_when_unleash_flag_disabled(self, mock_unleash):
        """Test that inference token endpoint returns 403 when Unleash flag is disabled."""
        url = reverse("reports-openshift-inference-tokens")
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_unleash.assert_called_once()

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=True)
    def test_response_structure(self, mock_unleash):
        """Test that inference token endpoint returns proper response structure."""
        url = reverse("reports-openshift-inference-tokens")
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)
        self.assertIn("meta", response.data)

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=True)
    def test_order_by_invalid_field_fails(self, mock_unleash):
        """Test that ordering by an invalid field (uptime) returns 400."""
        url = reverse("reports-openshift-inference-tokens")
        query_params = {"order_by[uptime]": "desc"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=True)
    def test_order_by_cost_succeeds(self, mock_unleash):
        """Test that ordering by cost succeeds."""
        url = reverse("reports-openshift-inference-tokens")
        query_params = {"order_by[cost]": "desc"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=True)
    def test_order_by_input_tokens_succeeds(self, mock_unleash):
        """Test that ordering by input_tokens succeeds."""
        url = reverse("reports-openshift-inference-tokens")
        query_params = {"order_by[input_tokens]": "desc"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=True)
    def test_combined_params(self, mock_unleash):
        """Test inference token endpoint with combined filter, group_by, and order_by."""
        url = reverse("reports-openshift-inference-tokens")
        query_params = {
            "filter[model_name]": "llama-3-8b",
            "group_by[cluster]": "*",
            "order_by[cost]": "desc",
        }
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=True)
    def test_filter_limit_with_group_by(self, mock_unleash):
        """Test inference token endpoint with filter[limit] and group_by[model_name] does not crash."""
        url = reverse("reports-openshift-inference-tokens")
        query_params = {"group_by[model_name]": "*", "filter[limit]": "1"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=True)
    def test_tag_filter_accepted(self, mock_unleash):
        """Inference token API accepts tag filters in query without validation error; tag filters are dropped."""
        url = reverse("reports-openshift-inference-tokens")
        query_params = {"group_by[model_name]": "*", "filter[tag:application]": "Istio"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        err_msg = (
            f"Inference token API must accept tag filter (UI parity). "
            f"Got: {getattr(response, 'data', response.content)}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, err_msg)
        self.assertIn("data", response.data)

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=True)
    def test_group_by_cluster(self, mock_unleash):
        """Test inference token endpoint with group_by[cluster]."""
        url = reverse("reports-openshift-inference-tokens")
        query_params = {"group_by[cluster]": "*"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=True)
    def test_group_by_node(self, mock_unleash):
        """Test inference token endpoint with group_by[node]."""
        url = reverse("reports-openshift-inference-tokens")
        query_params = {"group_by[node]": "*"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=True)
    def test_group_by_inference_service(self, mock_unleash):
        """Test inference token endpoint with group_by[inference_service]."""
        url = reverse("reports-openshift-inference-tokens")
        query_params = {"group_by[inference_service]": "*"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=True)
    def test_filter_by_inference_service(self, mock_unleash):
        """Test inference token endpoint with filter by inference_service."""
        url = reverse("reports-openshift-inference-tokens")
        query_params = {"filter[inference_service]": "llama-3-8b-service"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=True)
    def test_group_by_organization(self, mock_unleash):
        """Test inference token endpoint with group_by[organization]."""
        url = reverse("reports-openshift-inference-tokens")
        query_params = {"group_by[organization]": "*"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=True)
    def test_filter_by_organization(self, mock_unleash):
        """Test inference token endpoint with filter by organization."""
        url = reverse("reports-openshift-inference-tokens")
        query_params = {"filter[organization]": "acme-corp"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=True)
    def test_group_by_operation_name(self, mock_unleash):
        """Test inference token endpoint with group_by[operation_name]."""
        url = reverse("reports-openshift-inference-tokens")
        query_params = {"group_by[operation_name]": "*"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=True)
    def test_filter_by_operation_name(self, mock_unleash):
        """Test inference token endpoint with filter by operation_name."""
        url = reverse("reports-openshift-inference-tokens")
        query_params = {"filter[operation_name]": "chat"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=True)
    def test_accessible_when_unleash_flag_enabled(self, mock_unleash):
        """Test that inference token endpoint is accessible when Unleash flag is enabled."""
        url = reverse("reports-openshift-inference-tokens")
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_unleash.assert_called_once()
