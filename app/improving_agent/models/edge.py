# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from improving_agent.models.base_model_ import Model
from improving_agent.models.attribute import Attribute
from improving_agent import util

from improving_agent.models.attribute import Attribute  # noqa: E501

class Edge(Model):
    """NOTE: This class is auto generated by OpenAPI Generator (https://openapi-generator.tech).

    Do not edit the class manually.
    """

    def __init__(self, predicate=None, subject=None, object=None, attributes=None):  # noqa: E501
        """Edge - a model defined in OpenAPI

        :param predicate: The predicate of this Edge.  # noqa: E501
        :type predicate: str
        :param subject: The subject of this Edge.  # noqa: E501
        :type subject: str
        :param object: The object of this Edge.  # noqa: E501
        :type object: str
        :param attributes: The attributes of this Edge.  # noqa: E501
        :type attributes: List[Attribute]
        """
        self.openapi_types = {
            'predicate': str,
            'subject': str,
            'object': str,
            'attributes': List[Attribute]
        }

        self.attribute_map = {
            'predicate': 'predicate',
            'subject': 'subject',
            'object': 'object',
            'attributes': 'attributes'
        }

        self._predicate = predicate
        self._subject = subject
        self._object = object
        self._attributes = attributes

    @classmethod
    def from_dict(cls, dikt) -> 'Edge':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Edge of this Edge.  # noqa: E501
        :rtype: Edge
        """
        return util.deserialize_model(dikt, cls)

    @property
    def predicate(self):
        """Gets the predicate of this Edge.


        :return: The predicate of this Edge.
        :rtype: str
        """
        return self._predicate

    @predicate.setter
    def predicate(self, predicate):
        """Sets the predicate of this Edge.


        :param predicate: The predicate of this Edge.
        :type predicate: str
        """

        self._predicate = predicate

    @property
    def subject(self):
        """Gets the subject of this Edge.

        A Compact URI, consisting of a prefix and a reference separated by a colon, such as UniProtKB:P00738. Via an external context definition, the CURIE prefix and colon may be replaced by a URI prefix, such as http://identifiers.org/uniprot/, to form a full URI.  # noqa: E501

        :return: The subject of this Edge.
        :rtype: str
        """
        return self._subject

    @subject.setter
    def subject(self, subject):
        """Sets the subject of this Edge.

        A Compact URI, consisting of a prefix and a reference separated by a colon, such as UniProtKB:P00738. Via an external context definition, the CURIE prefix and colon may be replaced by a URI prefix, such as http://identifiers.org/uniprot/, to form a full URI.  # noqa: E501

        :param subject: The subject of this Edge.
        :type subject: str
        """
        if subject is None:
            raise ValueError("Invalid value for `subject`, must not be `None`")  # noqa: E501

        self._subject = subject

    @property
    def object(self):
        """Gets the object of this Edge.

        A Compact URI, consisting of a prefix and a reference separated by a colon, such as UniProtKB:P00738. Via an external context definition, the CURIE prefix and colon may be replaced by a URI prefix, such as http://identifiers.org/uniprot/, to form a full URI.  # noqa: E501

        :return: The object of this Edge.
        :rtype: str
        """
        return self._object

    @object.setter
    def object(self, object):
        """Sets the object of this Edge.

        A Compact URI, consisting of a prefix and a reference separated by a colon, such as UniProtKB:P00738. Via an external context definition, the CURIE prefix and colon may be replaced by a URI prefix, such as http://identifiers.org/uniprot/, to form a full URI.  # noqa: E501

        :param object: The object of this Edge.
        :type object: str
        """
        if object is None:
            raise ValueError("Invalid value for `object`, must not be `None`")  # noqa: E501

        self._object = object

    @property
    def attributes(self):
        """Gets the attributes of this Edge.

        A list of additional attributes for this edge  # noqa: E501

        :return: The attributes of this Edge.
        :rtype: List[Attribute]
        """
        return self._attributes

    @attributes.setter
    def attributes(self, attributes):
        """Sets the attributes of this Edge.

        A list of additional attributes for this edge  # noqa: E501

        :param attributes: The attributes of this Edge.
        :type attributes: List[Attribute]
        """

        self._attributes = attributes
