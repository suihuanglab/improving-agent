from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from improving_agent.models.base_model import Model
from improving_agent import util


class AsyncQueryResponse(Model):
    """NOTE: This class is auto generated by OpenAPI Generator (https://openapi-generator.tech).

    Do not edit the class manually.
    """

    def __init__(self, status=None, description=None, job_id=None):  # noqa: E501
        """AsyncQueryResponse - a model defined in OpenAPI

        :param status: The status of this AsyncQueryResponse.  # noqa: E501
        :type status: str
        :param description: The description of this AsyncQueryResponse.  # noqa: E501
        :type description: str
        :param job_id: The job_id of this AsyncQueryResponse.  # noqa: E501
        :type job_id: str
        """
        self.openapi_types = {
            'status': str,
            'description': str,
            'job_id': str
        }

        self.attribute_map = {
            'status': 'status',
            'description': 'description',
            'job_id': 'job_id'
        }

        self._status = status
        self._description = description
        self._job_id = job_id

    @classmethod
    def from_dict(cls, dikt) -> 'AsyncQueryResponse':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The AsyncQueryResponse of this AsyncQueryResponse.  # noqa: E501
        :rtype: AsyncQueryResponse
        """
        return util.deserialize_model(dikt, cls)

    @property
    def status(self) -> str:
        """Gets the status of this AsyncQueryResponse.

        One of a standardized set of short codes: e.g. Accepted, QueryNotTraversable, KPsNotAvailable  # noqa: E501

        :return: The status of this AsyncQueryResponse.
        :rtype: str
        """
        return self._status

    @status.setter
    def status(self, status: str):
        """Sets the status of this AsyncQueryResponse.

        One of a standardized set of short codes: e.g. Accepted, QueryNotTraversable, KPsNotAvailable  # noqa: E501

        :param status: The status of this AsyncQueryResponse.
        :type status: str
        """

        self._status = status

    @property
    def description(self) -> str:
        """Gets the description of this AsyncQueryResponse.

        A brief human-readable description of the result of the async_query submission.  # noqa: E501

        :return: The description of this AsyncQueryResponse.
        :rtype: str
        """
        return self._description

    @description.setter
    def description(self, description: str):
        """Sets the description of this AsyncQueryResponse.

        A brief human-readable description of the result of the async_query submission.  # noqa: E501

        :param description: The description of this AsyncQueryResponse.
        :type description: str
        """

        self._description = description

    @property
    def job_id(self) -> str:
        """Gets the job_id of this AsyncQueryResponse.

        An identifier for the submitted job that can be used with /async_query_status to receive an update on the status of the job.  # noqa: E501

        :return: The job_id of this AsyncQueryResponse.
        :rtype: str
        """
        return self._job_id

    @job_id.setter
    def job_id(self, job_id: str):
        """Sets the job_id of this AsyncQueryResponse.

        An identifier for the submitted job that can be used with /async_query_status to receive an update on the status of the job.  # noqa: E501

        :param job_id: The job_id of this AsyncQueryResponse.
        :type job_id: str
        """
        if job_id is None:
            raise ValueError("Invalid value for `job_id`, must not be `None`")  # noqa: E501

        self._job_id = job_id
