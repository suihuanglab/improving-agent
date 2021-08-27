# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from improving_agent.models.base_model_ import Model
from improving_agent.models.query_constraint import QueryConstraint
from improving_agent import util

from improving_agent.models.query_constraint import QueryConstraint  # noqa: E501

class QEdge(Model):
    """NOTE: This class is auto generated by OpenAPI Generator (https://openapi-generator.tech).

    Do not edit the class manually.
    """

    def __init__(self, predicates=None, subject=None, object=None, constraints=None):  # noqa: E501
        """QEdge - a model defined in OpenAPI

        :param predicates: The predicates of this QEdge.  # noqa: E501
        :type predicates: List[str]
        :param subject: The subject of this QEdge.  # noqa: E501
        :type subject: str
        :param object: The object of this QEdge.  # noqa: E501
        :type object: str
        :param constraints: The constraints of this QEdge.  # noqa: E501
        :type constraints: List[QueryConstraint]
        """
        self.openapi_types = {
            'predicates': List[str],
            'subject': str,
            'object': str,
            'constraints': List[QueryConstraint]
        }

        self.attribute_map = {
            'predicates': 'predicates',
            'subject': 'subject',
            'object': 'object',
            'constraints': 'constraints'
        }

        self._predicates = predicates
        self._subject = subject
        self._object = object
        self._constraints = constraints

    @classmethod
    def from_dict(cls, dikt) -> 'QEdge':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The QEdge of this QEdge.  # noqa: E501
        :rtype: QEdge
        """
        return util.deserialize_model(dikt, cls)

    @property
    def predicates(self):
        """Gets the predicates of this QEdge.


        :return: The predicates of this QEdge.
        :rtype: List[str]
        """
        return self._predicates

    @predicates.setter
    def predicates(self, predicates):
        """Sets the predicates of this QEdge.


        :param predicates: The predicates of this QEdge.
        :type predicates: List[str]
        """

        self._predicates = predicates

    @property
    def subject(self):
        """Gets the subject of this QEdge.

        Corresponds to the map key identifier of the subject concept node anchoring the query filter pattern for the query relationship edge.  # noqa: E501

        :return: The subject of this QEdge.
        :rtype: str
        """
        return self._subject

    @subject.setter
    def subject(self, subject):
        """Sets the subject of this QEdge.

        Corresponds to the map key identifier of the subject concept node anchoring the query filter pattern for the query relationship edge.  # noqa: E501

        :param subject: The subject of this QEdge.
        :type subject: str
        """
        if subject is None:
            raise ValueError("Invalid value for `subject`, must not be `None`")  # noqa: E501

        self._subject = subject

    @property
    def object(self):
        """Gets the object of this QEdge.

        Corresponds to the map key identifier of the object concept node anchoring the query filter pattern for the query relationship edge.  # noqa: E501

        :return: The object of this QEdge.
        :rtype: str
        """
        return self._object

    @object.setter
    def object(self, object):
        """Sets the object of this QEdge.

        Corresponds to the map key identifier of the object concept node anchoring the query filter pattern for the query relationship edge.  # noqa: E501

        :param object: The object of this QEdge.
        :type object: str
        """
        if object is None:
            raise ValueError("Invalid value for `object`, must not be `None`")  # noqa: E501

        self._object = object

    @property
    def constraints(self):
        """Gets the constraints of this QEdge.

        A list of contraints applied to a query edge. If there are multiple items, they must all be true (equivalent to AND)  # noqa: E501

        :return: The constraints of this QEdge.
        :rtype: List[QueryConstraint]
        """
        return self._constraints

    @constraints.setter
    def constraints(self, constraints):
        """Sets the constraints of this QEdge.

        A list of contraints applied to a query edge. If there are multiple items, they must all be true (equivalent to AND)  # noqa: E501

        :param constraints: The constraints of this QEdge.
        :type constraints: List[QueryConstraint]
        """

        self._constraints = constraints
