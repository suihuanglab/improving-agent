"""This module provides resources to query the RENCI node-normalization
API to retrieve equivalent identifiers (CURIEs) for nodes encountered
in ARS queries and KP responses"""
import re
from typing import Any, Dict, Iterable, List

import requests
from werkzeug.utils import cached_property

from improving_agent.util import get_evidara_logger

NODE_NORMALIZATION_BASE_URL = "https://nodenormalization-sri.renci.org"
NODE_NORMALIZATION_CURIE_IDENTIFER = "curie"
NODE_NORMALIZATION_CURIE_PREFIXES_ENDPOINT = "get_curie_prefixes"
NODE_NORMALIZATION_NORMALIZED_NODES_ENDPOINT = "get_normalized_nodes"
NODE_NORMALIZATION_SEMANTIC_TYPES_ENDPOINT = "get_semantic_types"
NODE_NORMALIZATION_SEMANTIC_TYPE_IDENTIFIER = "semantictype"

NODE_NORMALIZATION_CURIE_QUERY_FORMATTERS = {}

logger = get_evidara_logger(__name__)


def register_curie_formatter(regex):
    def wrapper(f):
        NODE_NORMALIZATION_CURIE_QUERY_FORMATTERS[regex] = f
        return f
    return wrapper


@register_curie_formatter('^CHEMBL[0-9]+')
def _format_chembl(curie):
    return f"CHEMBL.COMPOUND:{curie}"


@register_curie_formatter('^DB[0-9]+')
def _format_drugbank(curie):
    return f"DRUGBANK:{curie}"


def reformat_curie(curie):
    for k, v in NODE_NORMALIZATION_CURIE_QUERY_FORMATTERS.items():
        if re.match(k, curie):
            return v(curie)

    return curie


class SriNodeNormalizer():
    """Query functionality for RENCI's node-normalization service"""

    def __init__(self) -> None:
        self.normalized_node_cache = {}

    def _check_cache_and_reformat_curies(self, curies):
        cached = {}
        subset = {}

        for curie in curies:
            if curie in self.normalized_node_cache:
                if self.normalized_node_cache[curie] is not None:
                    cached[curie] = self.normalized_node_cache[curie]
                continue
            subset[reformat_curie(curie)] = curie

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
            logger.warning(f"No results for {list(subset.values())} in SRI node normalizer")
            for curie in subset.values():
                self.normalized_node_cache[curie] = None
            return cached

        if response.status_code != 200:
            logger.warning(f"Node normalization query failed with {response.status_code} and {response.text}")
            response.raise_for_status()

        normalized_nodes = response.json()

        successful_nodes = {}
        failed_curies = []

        for k, v in normalized_nodes.items():
            self.normalized_node_cache[subset[k]] = v
            if v is None:
                failed_curies.append(subset[k])
            else:
                successful_nodes[subset[k]] = v

        if failed_curies:
            logger.warning(f"Failed to retrieve normalized nodes for {failed_curies}")

        return {**cached, **successful_nodes}

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
