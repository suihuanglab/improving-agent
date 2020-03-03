# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from evidara_api.models.base_model_ import Model
from evidara_api import util


class Query(Model):
    """NOTE: This class is auto generated by OpenAPI Generator (https://openapi-generator.tech).

    Do not edit the class manually.
    """

    def __init__(
        self, asynchronous=None, max_results=None, reasoner_ids=None, query_message=None
    ):  # noqa: E501
        """Query - a model defined in OpenAPI

        :param asynchronous: The asynchronous of this Query.  # noqa: E501
        :type asynchronous: str
        :param max_results: The max_results of this Query.  # noqa: E501
        :type max_results: int
        :param reasoner_ids: The reasoner_ids of this Query.  # noqa: E501
        :type reasoner_ids: List[str]
        :param query_message: The query_message of this Query.  # noqa: E501
        :type query_message: object
        """
        self.openapi_types = {
            "asynchronous": str,
            "max_results": int,
            "reasoner_ids": List[str],
            "query_message": object,
        }

        self.attribute_map = {
            "asynchronous": "asynchronous",
            "max_results": "max_results",
            "reasoner_ids": "reasoner_ids",
            "query_message": "query_message",
        }

        self._asynchronous = asynchronous
        self._max_results = max_results
        self._reasoner_ids = reasoner_ids
        self._query_message = query_message

    @classmethod
    def from_dict(cls, dikt) -> "Query":
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Query of this Query.  # noqa: E501
        :rtype: Query
        """
        return util.deserialize_model(dikt, cls)

    @property
    def asynchronous(self):
        """Gets the asynchronous of this Query.

        Set to true in order to receive an incomplete message_id if the query will take a while. Client can then periodically request that message_id for a status update and eventual complete message  # noqa: E501

        :return: The asynchronous of this Query.
        :rtype: str
        """
        return self._asynchronous

    @asynchronous.setter
    def asynchronous(self, asynchronous):
        """Sets the asynchronous of this Query.

        Set to true in order to receive an incomplete message_id if the query will take a while. Client can then periodically request that message_id for a status update and eventual complete message  # noqa: E501

        :param asynchronous: The asynchronous of this Query.
        :type asynchronous: str
        """

        self._asynchronous = asynchronous

    @property
    def max_results(self):
        """Gets the max_results of this Query.

        Maximum number of individual results to return  # noqa: E501

        :return: The max_results of this Query.
        :rtype: int
        """
        return self._max_results

    @max_results.setter
    def max_results(self, max_results):
        """Sets the max_results of this Query.

        Maximum number of individual results to return  # noqa: E501

        :param max_results: The max_results of this Query.
        :type max_results: int
        """

        self._max_results = max_results

    @property
    def reasoner_ids(self):
        """Gets the reasoner_ids of this Query.

        List of KPs (formerly reasoners) to consult for the query  # noqa: E501

        :return: The reasoner_ids of this Query.
        :rtype: List[str]
        """
        return self._reasoner_ids

    @reasoner_ids.setter
    def reasoner_ids(self, reasoner_ids):
        """Sets the reasoner_ids of this Query.

        List of KPs (formerly reasoners) to consult for the query  # noqa: E501

        :param reasoner_ids: The reasoner_ids of this Query.
        :type reasoner_ids: List[str]
        """

        self._reasoner_ids = reasoner_ids

    @property
    def query_message(self):
        """Gets the query_message of this Query.

        Message object that represents the query to be answered  # noqa: E501

        :return: The query_message of this Query.
        :rtype: object
        """
        return self._query_message

    @query_message.setter
    def query_message(self, query_message):
        """Sets the query_message of this Query.

        Message object that represents the query to be answered  # noqa: E501

        :param query_message: The query_message of this Query.
        :type query_message: object
        """

        self._query_message = query_message