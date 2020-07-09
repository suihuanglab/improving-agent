"""This module provides resources to query the RENCI node-normalization
API to retrieve equivalent identifiers (CURIEs) for nodes encountered
in ARS queries and KP responses"""
from typing import List

import requests

from evidara_api.util import get_evidara_logger

NODE_NORMALIZATION_BASE_URL = "https://nodenormalization-sri.renci.org"
NODE_NORMALIZATION_CURIE_IDENTIFER = "curie"
# TODO: NODE_NORMALIZATION_CURIE_PREFIXES_ENDPOINT = "get_curie_prefixes"
NODE_NORMALIZATION_NORMALIZED_NODES_ENDPOINT = "get_normalized_nodes"
# TODO: NODE_NORMALIZATION_SEMANTIC_TYPES_ENDPOINT = "get_semantic_types"

logger = get_evidara_logger(__name__)


class NodeNormalization():
    """Query functionality for RENCI's node-normalization service"""

    def __init__(self) -> None:
        pass

    def get_normalized_nodes(self, nodes: List[str]):
        """Returns 'normalized' nodes from the node-normalization
        endpoint for every node in `nodes`
        """
        payload = [(NODE_NORMALIZATION_CURIE_IDENTIFER, node) for node in nodes]
        response = requests.get(
            f"{NODE_NORMALIZATION_BASE_URL}/{NODE_NORMALIZATION_NORMALIZED_NODES_ENDPOINT}",
            params=payload
        )

        if not response.status_code == 200:
            logger.warning(
                f"Node normalization query failed with {response.status_code}"
                f" and {response.text}"
            )
            return  # make this an exception going forward

        normalized_nodes = response.json()
        failed_nodes = [key for key, value in normalized_nodes.items() if value is None]
        logger.warning(f"Failed to retrieve normalized nodes for {failed_nodes}")

        return normalized_nodes
