# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from improving_agent.models.message import Message  # noqa: E501
from improving_agent.models.query import Query  # noqa: E501
from improving_agent.test import BaseTestCase


class TestQueryController(BaseTestCase):
    """QueryController integration test stubs"""

    def test_query(self):
        """Test case for query

        Query reasoner via one of several inputs
        """
        body = {
            "asynchronous": "false",
            "query_message": "{}",
            "max_results": 100,
            "reasoner_ids": ["BigGIM", "Robokop"],
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        response = self.client.open(
            "/api/v1/query",
            method="POST",
            headers=headers,
            data=json.dumps(body),
            content_type="application/json",
        )
        self.assert200(response, "Response body is : " + response.data.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
