#
# Copyright 2026 Red Hat Inc.
# SPDX-License-Identifier: Apache-2.0
#
"""Test the Agent Report views."""
from unittest.mock import patch
from urllib.parse import urlencode

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from api.iam.test.iam_test_case import IamTestCase


class OCPAgentViewTest(IamTestCase):
    """Tests for the agent report view."""

    def setUp(self):
        """Set up the customer view tests."""
        super().setUp()
        self.client = APIClient()

    def test_agent_endpoint_exists(self):
        """Test that the agent endpoint is accessible."""
        url = reverse("reports-openshift-agents")
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_group_by_agent_name(self):
        """Test agent endpoint with group_by agent_name."""
        url = reverse("reports-openshift-agents")
        query_params = {"group_by[agent_name]": "*"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    def test_filter_by_agent_name(self):
        """Test agent endpoint with filter by agent_name."""
        url = reverse("reports-openshift-agents")
        query_params = {"filter[agent_name]": "my-agent"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    @patch("api.report.ocp.view.is_feature_flag_enabled_by_schema", return_value=False)
    def test_endpoint_blocked_when_unleash_flag_disabled(self, mock_unleash):
        """Test that agent endpoint returns 403 when Unleash flag is disabled."""
        url = reverse("reports-openshift-agents")
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_unleash.assert_called_once()

    def test_order_by_invocation_count(self):
        """Test agent endpoint with order_by invocation_count."""
        url = reverse("reports-openshift-agents")
        query_params = {"order_by[invocation_count]": "desc"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_group_by_model_name(self):
        """Test agent endpoint with group_by model_name."""
        url = reverse("reports-openshift-agents")
        query_params = {"group_by[model_name]": "*"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    def test_group_by_organization(self):
        """Test agent endpoint with group_by organization."""
        url = reverse("reports-openshift-agents")
        query_params = {"group_by[organization]": "*"}
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)

    def test_combined_params(self):
        """Test agent endpoint with combined filter, group_by, and order_by."""
        url = reverse("reports-openshift-agents")
        query_params = {
            "filter[agent_name]": "my-agent",
            "group_by[cluster]": "*",
            "order_by[cost]": "desc",
        }
        url = url + "?" + urlencode(query_params, doseq=True)
        response = self.client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)
