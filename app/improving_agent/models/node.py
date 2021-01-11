# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from improving_agent.models.base_model_ import Model
from improving_agent.models.attribute import Attribute
from improving_agent.models.one_ofstringarray import OneOfstringarray
from improving_agent import util

from improving_agent.models.attribute import Attribute  # noqa: E501
from improving_agent.models.one_ofstringarray import OneOfstringarray  # noqa: E501

class Node(Model):
    """NOTE: This class is auto generated by OpenAPI Generator (https://openapi-generator.tech).

    Do not edit the class manually.
    """

    def __init__(self, name=None, category=None, attributes=None):  # noqa: E501
        """Node - a model defined in OpenAPI

        :param name: The name of this Node.  # noqa: E501
        :type name: str
        :param category: The category of this Node.  # noqa: E501
        :type category: OneOfstringarray
        :param attributes: The attributes of this Node.  # noqa: E501
        :type attributes: List[Attribute]
        """
        self.openapi_types = {
            'name': str,
            'category': OneOfstringarray,
            'attributes': List[Attribute]
        }

        self.attribute_map = {
            'name': 'name',
            'category': 'category',
            'attributes': 'attributes'
        }

        self._name = name
        self._category = OneOfstringarray.deserialize(category)
        self._attributes = attributes

    @classmethod
    def from_dict(cls, dikt) -> 'Node':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Node of this Node.  # noqa: E501
        :rtype: Node
        """
        return util.deserialize_model(dikt, cls)

    @property
    def name(self):
        """Gets the name of this Node.

        Formal name of the entity  # noqa: E501

        :return: The name of this Node.
        :rtype: str
        """
        return self._name

    @name.setter
    def name(self, name):
        """Sets the name of this Node.

        Formal name of the entity  # noqa: E501

        :param name: The name of this Node.
        :type name: str
        """

        self._name = name

    @property
    def category(self):
        """Gets the category of this Node.


        :return: The category of this Node.
        :rtype: OneOfstringarray
        """
        return self._category

    @category.setter
    def category(self, category):
        """Sets the category of this Node.


        :param category: The category of this Node.
        :type category: OneOfstringarray
        """

        self._category = category

    @property
    def attributes(self):
        """Gets the attributes of this Node.

        A list of attributes describing the node  # noqa: E501

        :return: The attributes of this Node.
        :rtype: List[Attribute]
        """
        return self._attributes

    @attributes.setter
    def attributes(self, attributes):
        """Sets the attributes of this Node.

        A list of attributes describing the node  # noqa: E501

        :param attributes: The attributes of this Node.
        :type attributes: List[Attribute]
        """

        self._attributes = attributes
