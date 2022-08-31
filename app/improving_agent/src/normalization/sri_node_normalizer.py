"""This module provides resources to query the RENCI node-normalization
API to retrieve equivalent identifiers (CURIEs) for nodes encountered
in ARS queries and KP responses"""
from typing import Any, Dict, Iterable, List

import requests
from werkzeug.utils import cached_property

from improving_agent.util import get_evidara_logger

SRI_NN_BASE_URL = "https://nodenormalization-sri.renci.org/1.3/"
SRI_NN_CURIE_IDENTIFER = "curie"
SRI_NN_CURIE_PREFIX = "curie_prefix"
SRI_NN_CURIE_PREFIXES_ENDPOINT = "get_curie_prefixes"
SRI_NN_NORMALIZED_NODES_ENDPOINT = "get_normalized_nodes"
SRI_NN_PARAM_CURIES = 'curies'
SRI_NN_RESPONSE_VALUE_EQUIVALENT_IDENTIFIERS = 'equivalent_identifiers'
SRI_NN_RESPONSE_VALUE_ID = 'id'
SRI_NN_RESPONSE_VALUE_IDENTIFIER = 'identifier'
SRI_NN_RESPONSE_VALUE_TYPE = 'type'
SRI_NN_SEMANTIC_TYPES_ENDPOINT = "get_semantic_types"
SRI_NN_SEMANTIC_TYPE_IDENTIFIER = "semantictype"

logger = get_evidara_logger(__name__)


class SriNodeNormalizer:
    """Query functionality for RENCI's node-normalization service"""

    def __init__(self) -> None:
        self.normalized_node_cache = {}

    def _check_cache_and_reformat_curies(self, curies):
        cached = {}
        subset = set()

        for curie in curies:
            if curie in self.normalized_node_cache:
                if self.normalized_node_cache[curie] is not None:
                    cached[curie] = self.normalized_node_cache[curie]
                continue
            subset.add(curie)

        return cached, subset

    def get_normalized_nodes(self, curies: Iterable[str]) -> Dict[str, Any]:
        """Returns 'normalized' nodes from the node-normalization
        endpoint for every node curie in `curies`

        Parameters
        ----------
        curies:
            an iterable of CURIEs to search against the get_normalized_nodes
            API endpoint

        Returns
        -------
        Dict[str, Any]:
            JSON response from the node-normalization API
        """
        cached, subset = self._check_cache_and_reformat_curies(curies)
        if not subset:
            return cached

        logger.info(f'Querying SRI to normalize {subset}')
        data = {SRI_NN_PARAM_CURIES: list(subset)}
        response = requests.post(
            f"{SRI_NN_BASE_URL}/{SRI_NN_NORMALIZED_NODES_ENDPOINT}", json=data
        )
        if response.status_code == 404:
            logger.warning(f"No results for {list(subset)} in SRI node normalizer")
            for curie in subset:
                self.normalized_node_cache[curie] = None
            empty_results = {curie: None for curie in subset}
            return {**empty_results, **cached}

        if response.status_code != 200:
            logger.warning(f"Node normalization query failed with {response.status_code} and {response.text}")
            response.raise_for_status()

        normalized_nodes = response.json()
        failed_curies = []

        for search_curie, normalized_node in normalized_nodes.items():
            self.normalized_node_cache[search_curie] = normalized_node
            if normalized_node is None:
                failed_curies.append(search_curie)

        if failed_curies:
            logger.warning(f"Failed to retrieve normalized nodes for {failed_curies}")

        return {**cached, **normalized_nodes}

    def get_curie_prefixes(self, semantic_types: Iterable[str]) -> Dict[str, Dict[str, List[Dict[str, int]]]]:
        """Returns mappings of `semantic_types` to counts of CURIE
        prefixes present in the node-normalization API

        Parameters
        ----------
        semantic_types:
            an iterable of semantic types for which to search in the
            get_curie_prefixes API endpoint

        Returns
        -------
        Dict[str, Dict[str, List[Dict[str, int]]]]:
            json response from the get_curie_prefixes endpoint

        NOTE: this endpoint will 404 if any semantic type is bad
        """
        payload = [
            (SRI_NN_SEMANTIC_TYPE_IDENTIFIER, semantic_type) for semantic_type in semantic_types
        ]

        response = requests.get(
            f"{SRI_NN_BASE_URL}/{SRI_NN_CURIE_PREFIXES_ENDPOINT}", params=payload
        )

        if response.status_code != 200:
            logger.error(f"Failed to get curie prefixes with {response.status_code} and {response.text}")
            response.raise_for_status()

        return response.json()

    @cached_property
    def semantic_types(self) -> List[str]:
        """Returns a list of semantic types valid for the other
        node-normalization endpoints

        Returns
        -------
        List[str]:
            list of valid semantic types
        """
        response = requests.get(f"{SRI_NN_BASE_URL}/{SRI_NN_SEMANTIC_TYPES_ENDPOINT}")
        if response.status_code != 200:
            logger.error(f"Failed to get semantic types with {response.status_code} and {response.text}")
            response.raise_for_status()

        return response.json()["semantic_types"]["types"]


SRI_NODE_NORMALIZER = SriNodeNormalizer()
