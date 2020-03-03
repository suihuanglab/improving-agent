# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from evidara_api.models.result import Result  # noqa: E501
from evidara_api.test import BaseTestCase


class TestResultController(BaseTestCase):
    """ResultController integration test stubs"""

    def test_get_result(self):
        """Test case for get_result

        Request stored result
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/api/v1/result/{result_id}'.format(result_id=56),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
