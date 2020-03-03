# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from evidara_api.models.base_model_ import Model
from evidara_api import util


class MessageTerms(Model):
    """NOTE: This class is auto generated by OpenAPI Generator (https://openapi-generator.tech).

    Do not edit the class manually.
    """

    def __init__(
        self,
        disease=None,
        protein=None,
        anatomical_entity=None,
        chemical_substance=None,
        metabolite=None,
    ):  # noqa: E501
        """MessageTerms - a model defined in OpenAPI

        :param disease: The disease of this MessageTerms.  # noqa: E501
        :type disease: str
        :param protein: The protein of this MessageTerms.  # noqa: E501
        :type protein: str
        :param anatomical_entity: The anatomical_entity of this MessageTerms.  # noqa: E501
        :type anatomical_entity: str
        :param chemical_substance: The chemical_substance of this MessageTerms.  # noqa: E501
        :type chemical_substance: str
        :param metabolite: The metabolite of this MessageTerms.  # noqa: E501
        :type metabolite: str
        """
        self.openapi_types = {
            "disease": str,
            "protein": str,
            "anatomical_entity": str,
            "chemical_substance": str,
            "metabolite": str,
        }

        self.attribute_map = {
            "disease": "disease",
            "protein": "protein",
            "anatomical_entity": "anatomical_entity",
            "chemical_substance": "chemical_substance",
            "metabolite": "metabolite",
        }

        self._disease = disease
        self._protein = protein
        self._anatomical_entity = anatomical_entity
        self._chemical_substance = chemical_substance
        self._metabolite = metabolite

    @classmethod
    def from_dict(cls, dikt) -> "MessageTerms":
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Message_terms of this MessageTerms.  # noqa: E501
        :rtype: MessageTerms
        """
        return util.deserialize_model(dikt, cls)

    @property
    def disease(self):
        """Gets the disease of this MessageTerms.


        :return: The disease of this MessageTerms.
        :rtype: str
        """
        return self._disease

    @disease.setter
    def disease(self, disease):
        """Sets the disease of this MessageTerms.


        :param disease: The disease of this MessageTerms.
        :type disease: str
        """

        self._disease = disease

    @property
    def protein(self):
        """Gets the protein of this MessageTerms.


        :return: The protein of this MessageTerms.
        :rtype: str
        """
        return self._protein

    @protein.setter
    def protein(self, protein):
        """Sets the protein of this MessageTerms.


        :param protein: The protein of this MessageTerms.
        :type protein: str
        """

        self._protein = protein

    @property
    def anatomical_entity(self):
        """Gets the anatomical_entity of this MessageTerms.


        :return: The anatomical_entity of this MessageTerms.
        :rtype: str
        """
        return self._anatomical_entity

    @anatomical_entity.setter
    def anatomical_entity(self, anatomical_entity):
        """Sets the anatomical_entity of this MessageTerms.


        :param anatomical_entity: The anatomical_entity of this MessageTerms.
        :type anatomical_entity: str
        """

        self._anatomical_entity = anatomical_entity

    @property
    def chemical_substance(self):
        """Gets the chemical_substance of this MessageTerms.


        :return: The chemical_substance of this MessageTerms.
        :rtype: str
        """
        return self._chemical_substance

    @chemical_substance.setter
    def chemical_substance(self, chemical_substance):
        """Sets the chemical_substance of this MessageTerms.


        :param chemical_substance: The chemical_substance of this MessageTerms.
        :type chemical_substance: str
        """

        self._chemical_substance = chemical_substance

    @property
    def metabolite(self):
        """Gets the metabolite of this MessageTerms.


        :return: The metabolite of this MessageTerms.
        :rtype: str
        """
        return self._metabolite

    @metabolite.setter
    def metabolite(self, metabolite):
        """Sets the metabolite of this MessageTerms.


        :param metabolite: The metabolite of this MessageTerms.
        :type metabolite: str
        """

        self._metabolite = metabolite