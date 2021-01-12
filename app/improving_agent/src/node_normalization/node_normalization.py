from .curie_formatters import format_curie
from .sri_node_normalizer import (
    NODE_NORMALIZATION_RESPONSE_VALUE_ID,
    NODE_NORMALIZATION_RESPONSE_VALUE_IDENTIFIER,
    SriNodeNormalizer
)
from improving_agent.src.spoke_biolink_constants import BIOLINK_ENTITY_PROTEIN
from improving_agent.util import get_evidara_logger

SRI_NODE_NORMALIZER = SriNodeNormalizer()

logger = get_evidara_logger(__name__)


def normalize_spoke_nodes_for_translator(spoke_search_nodes):
    """Returns a mapping of SPOKE CURIE to their normalized equivalents
    If normalized equivalents are not found, the SPOKE CURIE is returned

    Parameters
    ----------
    spoke_search_nodes (list of SearchNode)
    """
    # don't search proteins
    formatted_curie_node_map = {format_curie(search_node): search_node for search_node in spoke_search_nodes}
    search_results = SRI_NODE_NORMALIZER.get_normalized_nodes(list(formatted_curie_node_map.keys()))
    result_map = {}
    for formatted_curie, search_node in formatted_curie_node_map.items():
        if search_node.node_type == BIOLINK_ENTITY_PROTEIN:
            # the node normalizer will suggest the NCBIGene curies for proteins
            # so we keep the UNIPROT CURIE here instead
            result_map[search_node.curie] = formatted_curie
            continue
        normalized_node = search_results.get(formatted_curie)
        if normalized_node is None:
            result_map[search_node.curie] = formatted_curie
        else:
            result_map[search_node.curie] = normalized_node[NODE_NORMALIZATION_RESPONSE_VALUE_ID][NODE_NORMALIZATION_RESPONSE_VALUE_IDENTIFIER]
    return result_map


def normalize_query_nodes_for_spoke():
    pass
