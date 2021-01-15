"""This module provides resources to query the RENCI node-normalization
API to retrieve equivalent identifiers (CURIEs) for nodes encountered
in ARS queries and KP responses"""
from typing import Any, Dict, Iterable, List

import requests
from werkzeug.utils import cached_property

from improving_agent.util import get_evidara_logger

NODE_NORMALIZATION_BASE_URL = "https://nodenormalization-sri.renci.org"
NODE_NORMALIZATION_CURIE_IDENTIFER = "curie"
NODE_NORMALIZATION_CURIE_PREFIXES_ENDPOINT = "get_curie_prefixes"
NODE_NORMALIZATION_NORMALIZED_NODES_ENDPOINT = "get_normalized_nodes"
NODE_NORMALIZATION_RESPONSE_VALUE_EQUIVALENT_IDENTIFIERS = 'equivalent_identifiers'
NODE_NORMALIZATION_RESPONSE_VALUE_ID = 'id'
NODE_NORMALIZATION_RESPONSE_VALUE_IDENTIFIER = 'identifier'
NODE_NORMALIZATION_SEMANTIC_TYPES_ENDPOINT = "get_semantic_types"
NODE_NORMALIZATION_SEMANTIC_TYPE_IDENTIFIER = "semantictype"

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
        payload = [(NODE_NORMALIZATION_CURIE_IDENTIFER, curie) for curie in subset]
        response = requests.get(
            f"{NODE_NORMALIZATION_BASE_URL}/{NODE_NORMALIZATION_NORMALIZED_NODES_ENDPOINT}", params=payload
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
            (NODE_NORMALIZATION_SEMANTIC_TYPE_IDENTIFIER, semantic_type) for semantic_type in semantic_types
        ]

        response = requests.get(
            f"{NODE_NORMALIZATION_BASE_URL}/{NODE_NORMALIZATION_CURIE_PREFIXES_ENDPOINT}", params=payload
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
        response = requests.get(f"{NODE_NORMALIZATION_BASE_URL}/{NODE_NORMALIZATION_SEMANTIC_TYPES_ENDPOINT}")
        if response.status_code != 200:
            logger.error(f"Failed to get semantic types with {response.status_code} and {response.text}")
            response.raise_for_status()

        return response.json()["semantic_types"]["types"]


SRI_NODE_NORMALIZER = SriNodeNormalizer()
