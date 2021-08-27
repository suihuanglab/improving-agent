# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from improving_agent.models.base_model_ import Model
from improving_agent.models.any_type import AnyType
from improving_agent.models.sub_attribute import SubAttribute
from improving_agent import util

from improving_agent.models.any_type import AnyType  # noqa: E501
from improving_agent.models.sub_attribute import SubAttribute  # noqa: E501

class Attribute(Model):
    """NOTE: This class is auto generated by OpenAPI Generator (https://openapi-generator.tech).

    Do not edit the class manually.
    """

    def __init__(self, attribute_type_id=None, original_attribute_name=None, value=None, value_type_id=None, attribute_source=None, value_url=None, description=None, attributes=None):  # noqa: E501
        """Attribute - a model defined in OpenAPI

        :param attribute_type_id: The attribute_type_id of this Attribute.  # noqa: E501
        :type attribute_type_id: str
        :param original_attribute_name: The original_attribute_name of this Attribute.  # noqa: E501
        :type original_attribute_name: str
        :param value: The value of this Attribute.  # noqa: E501
        :type value: AnyType
        :param value_type_id: The value_type_id of this Attribute.  # noqa: E501
        :type value_type_id: str
        :param attribute_source: The attribute_source of this Attribute.  # noqa: E501
        :type attribute_source: str
        :param value_url: The value_url of this Attribute.  # noqa: E501
        :type value_url: str
        :param description: The description of this Attribute.  # noqa: E501
        :type description: str
        :param attributes: The attributes of this Attribute.  # noqa: E501
        :type attributes: List[SubAttribute]
        """
        self.openapi_types = {
            'attribute_type_id': str,
            'original_attribute_name': str,
            'value': AnyType,
            'value_type_id': str,
            'attribute_source': str,
            'value_url': str,
            'description': str,
            'attributes': List[SubAttribute]
        }

        self.attribute_map = {
            'attribute_type_id': 'attribute_type_id',
            'original_attribute_name': 'original_attribute_name',
            'value': 'value',
            'value_type_id': 'value_type_id',
            'attribute_source': 'attribute_source',
            'value_url': 'value_url',
            'description': 'description',
            'attributes': 'attributes'
        }

        self._attribute_type_id = attribute_type_id
        self._original_attribute_name = original_attribute_name
        self._value = value
        self._value_type_id = value_type_id
        self._attribute_source = attribute_source
        self._value_url = value_url
        self._description = description
        self._attributes = attributes

    @classmethod
    def from_dict(cls, dikt) -> 'Attribute':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Attribute of this Attribute.  # noqa: E501
        :rtype: Attribute
        """
        return util.deserialize_model(dikt, cls)

    @property
    def attribute_type_id(self):
        """Gets the attribute_type_id of this Attribute.

        A Compact URI, consisting of a prefix and a reference separated by a colon, such as UniProtKB:P00738. Via an external context definition, the CURIE prefix and colon may be replaced by a URI prefix, such as http://identifiers.org/uniprot/, to form a full URI.  # noqa: E501

        :return: The attribute_type_id of this Attribute.
        :rtype: str
        """
        return self._attribute_type_id

    @attribute_type_id.setter
    def attribute_type_id(self, attribute_type_id):
        """Sets the attribute_type_id of this Attribute.

        A Compact URI, consisting of a prefix and a reference separated by a colon, such as UniProtKB:P00738. Via an external context definition, the CURIE prefix and colon may be replaced by a URI prefix, such as http://identifiers.org/uniprot/, to form a full URI.  # noqa: E501

        :param attribute_type_id: The attribute_type_id of this Attribute.
        :type attribute_type_id: str
        """
        if attribute_type_id is None:
            raise ValueError("Invalid value for `attribute_type_id`, must not be `None`")  # noqa: E501

        self._attribute_type_id = attribute_type_id

    @property
    def original_attribute_name(self):
        """Gets the original_attribute_name of this Attribute.

        The term used by the original source of an attribute to describe the meaning or significance of the value it captures. This may be a column name in a source tsv file, or a key in a source json document for the field in the data that held the attribute's value. Capturing this information  where possible lets us preserve what the original source said. Note that the data type is string' but the contents of the field could also be a CURIE of a third party ontology term.  # noqa: E501

        :return: The original_attribute_name of this Attribute.
        :rtype: str
        """
        return self._original_attribute_name

    @original_attribute_name.setter
    def original_attribute_name(self, original_attribute_name):
        """Sets the original_attribute_name of this Attribute.

        The term used by the original source of an attribute to describe the meaning or significance of the value it captures. This may be a column name in a source tsv file, or a key in a source json document for the field in the data that held the attribute's value. Capturing this information  where possible lets us preserve what the original source said. Note that the data type is string' but the contents of the field could also be a CURIE of a third party ontology term.  # noqa: E501

        :param original_attribute_name: The original_attribute_name of this Attribute.
        :type original_attribute_name: str
        """

        self._original_attribute_name = original_attribute_name

    @property
    def value(self):
        """Gets the value of this Attribute.

        Value of the attribute. May be any data type, including a list.  # noqa: E501

        :return: The value of this Attribute.
        :rtype: AnyType
        """
        return self._value

    @value.setter
    def value(self, value):
        """Sets the value of this Attribute.

        Value of the attribute. May be any data type, including a list.  # noqa: E501

        :param value: The value of this Attribute.
        :type value: AnyType
        """
        if value is None:
            raise ValueError("Invalid value for `value`, must not be `None`")  # noqa: E501

        self._value = value

    @property
    def value_type_id(self):
        """Gets the value_type_id of this Attribute.

        CURIE describing the semantic type of an  attribute's value. Use a Biolink class if possible, otherwise a term from an external ontology. If a suitable CURIE/identifier does not exist, enter a descriptive phrase here and submit the new type for consideration by the appropriate authority.  # noqa: E501

        :return: The value_type_id of this Attribute.
        :rtype: str
        """
        return self._value_type_id

    @value_type_id.setter
    def value_type_id(self, value_type_id):
        """Sets the value_type_id of this Attribute.

        CURIE describing the semantic type of an  attribute's value. Use a Biolink class if possible, otherwise a term from an external ontology. If a suitable CURIE/identifier does not exist, enter a descriptive phrase here and submit the new type for consideration by the appropriate authority.  # noqa: E501

        :param value_type_id: The value_type_id of this Attribute.
        :type value_type_id: str
        """

        self._value_type_id = value_type_id

    @property
    def attribute_source(self):
        """Gets the attribute_source of this Attribute.

        The source of the core assertion made by the key-value pair of an attribute object. Use a CURIE or namespace designator for this resource where possible.  # noqa: E501

        :return: The attribute_source of this Attribute.
        :rtype: str
        """
        return self._attribute_source

    @attribute_source.setter
    def attribute_source(self, attribute_source):
        """Sets the attribute_source of this Attribute.

        The source of the core assertion made by the key-value pair of an attribute object. Use a CURIE or namespace designator for this resource where possible.  # noqa: E501

        :param attribute_source: The attribute_source of this Attribute.
        :type attribute_source: str
        """

        self._attribute_source = attribute_source

    @property
    def value_url(self):
        """Gets the value_url of this Attribute.

        Human-consumable URL linking to a web document that provides additional information about an  attribute's value (not the node or the edge fom which it hangs).  # noqa: E501

        :return: The value_url of this Attribute.
        :rtype: str
        """
        return self._value_url

    @value_url.setter
    def value_url(self, value_url):
        """Sets the value_url of this Attribute.

        Human-consumable URL linking to a web document that provides additional information about an  attribute's value (not the node or the edge fom which it hangs).  # noqa: E501

        :param value_url: The value_url of this Attribute.
        :type value_url: str
        """

        self._value_url = value_url

    @property
    def description(self):
        """Gets the description of this Attribute.

        Human-readable description for the attribute and its value.  # noqa: E501

        :return: The description of this Attribute.
        :rtype: str
        """
        return self._description

    @description.setter
    def description(self, description):
        """Sets the description of this Attribute.

        Human-readable description for the attribute and its value.  # noqa: E501

        :param description: The description of this Attribute.
        :type description: str
        """

        self._description = description

    @property
    def attributes(self):
        """Gets the attributes of this Attribute.

        A list of attributes providing further information about the parent attribute (for example to provide provenance information about the parent attribute).  # noqa: E501

        :return: The attributes of this Attribute.
        :rtype: List[SubAttribute]
        """
        return self._attributes

    @attributes.setter
    def attributes(self, attributes):
        """Sets the attributes of this Attribute.

        A list of attributes providing further information about the parent attribute (for example to provide provenance information about the parent attribute).  # noqa: E501

        :param attributes: The attributes of this Attribute.
        :type attributes: List[SubAttribute]
        """

        self._attributes = attributes
