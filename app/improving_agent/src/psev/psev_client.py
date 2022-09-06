from collections import defaultdict
from http import HTTPStatus
from typing import Dict, List, Optional

import requests

from improving_agent.src.biolink.spoke_biolink_constants import (
    SPOKE_LABEL_COMPOUND,
    SPOKE_LABEL_DISEASE
)

PSEV_SERVICE_CONCEPTS = 'concepts'
PSEV_SERVICE_HEADER_X_API_KEY = 'X-API-KEY'
PSEV_SERVICE_IDENTIFIERS = 'node_identifiers'
PSEV_SERVICE_MORE_AVAILABLE = 'more_available'
PSEV_SERVICE_NODE_TYPE = 'node_type'
PSEV_SERVICE_PAGE = 'page'
PSEV_SERVICE_PSEV_ENDPOINT = 'psev'
PSEV_SERVICE_SUPPORTED_NODE_TYPES = [SPOKE_LABEL_COMPOUND]
PSEV_SERVICE_SUPPORTED_PSEV_CONCEPT_TYPES = [SPOKE_LABEL_COMPOUND, SPOKE_LABEL_DISEASE]


class PsevClient:
    def __init__(self, api_key, service_url):
        self._api_key = api_key
        self._service_url = '/'.join([service_url, PSEV_SERVICE_PSEV_ENDPOINT])

    def _call(
        self,
        url,
        params,
        req_body,
        headers={},
    ):
        headers = {**headers, PSEV_SERVICE_HEADER_X_API_KEY: self._api_key}
        r = requests.post(url, headers=headers, params=params, json=req_body)
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if r.status_code == HTTPStatus.NOT_FOUND:
                raise ValueError('Concept not found')
            raise e
        return r.json()

    def _get_scores_for_concept(
        self,
        concept,
        node_identifiers,
        node_type,
    ):
        page = 0
        concept_scores = {}

        params = {
            PSEV_SERVICE_PAGE: page,
        }
        req_body = {
            PSEV_SERVICE_IDENTIFIERS: node_identifiers,
            PSEV_SERVICE_NODE_TYPE: node_type,
        }
        req_url = f'{self._service_url}/{concept}'

        more_available = True
        while more_available:
            try:
                response = self._call(req_url, params, req_body)
                for identifier, psev_value in response[concept].items():
                    concept_scores[identifier] = psev_value

                more_available = response[PSEV_SERVICE_MORE_AVAILABLE]
                params[PSEV_SERVICE_PAGE] += 1

            except ValueError:  # concept not found
                return {}

        return concept_scores

    def get_psev_scores(
        self,
        concepts: List[str],
        node_identifiers: Optional[List[str]] = None,
        node_type: Optional[str] = None,
    ) -> Dict[str, Dict[str, float]]:
        """Returns PSEV scores for all nodes identified in ONE of
        `node_identifiers` or `node_type` for all `concepts` as a dict
        of {concept: {identifier: score}}

        Note that all concepts and node identifiers should be strings,
        thus the caller should convert and lookup str equivalents of
        integer identifiers, e.g. Gene

        `node_type` should be a string with the SPOKE name of the node
        type, e.g. Compound
        """
        if (node_identifiers and node_type) or not(node_identifiers or node_type):
            raise ValueError(
                'Must specify exactly one of `node_identifiers` or `node_type`'
            )

        if not isinstance(concepts, list) or not all(isinstance(i, str) for i in concepts):
            raise ValueError('`concepts` must be a list of str')

        if node_identifiers and (
            not isinstance(node_identifiers, list)
            or not all(isinstance(i, str) for i in node_identifiers)
        ):
            raise ValueError('`node_identifiers` must be a list of str')

        if node_type and not isinstance(node_type, str):
            raise ValueError('`node_type` must be a string')

        scores = defaultdict(dict)
        for concept in concepts:
            scores[concept] = self._get_scores_for_concept(
                concept, node_identifiers, node_type
            )

        return scores
