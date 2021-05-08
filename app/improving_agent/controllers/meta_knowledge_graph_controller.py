from functools import cache

import connexion
import six

from improving_agent.models.meta_knowledge_graph import MetaKnowledgeGraph  # noqa: E501
from improving_agent.models.meta_edge import MetaEdge
from improving_agent.models.meta_node import MetaNode
from improving_agent import util
from improving_agent.src.biolink.spoke_biolink_constants import (
    BIOLINK_ENTITY_NAMED_THING,
    BIOLINK_SPOKE_NODE_MAPPINGS,
    PREDICATES
)
from improving_agent.src.normalization.sri_node_normalizer import (
    NODE_NORMALIZATION_CURIE_PREFIX,
    SRI_NODE_NORMALIZER
)


def _get_supported_prefixes(sri_prefixes, node_type, local_prefixes):
    sri_node_prefixes = sri_prefixes.get(node_type)
    if not sri_node_prefixes:
        return local_prefixes
    return list(sri_node_prefixes[NODE_NORMALIZATION_CURIE_PREFIX].keys())


@cache
def _make_meta_kg():
    nodes = {}
    sri_curie_prefixes = SRI_NODE_NORMALIZER.get_curie_prefixes([])
    for node, mapping in BIOLINK_SPOKE_NODE_MAPPINGS.items():
        if node == BIOLINK_ENTITY_NAMED_THING:
            continue
        prefixes = _get_supported_prefixes(sri_curie_prefixes, node, mapping.prefixes)
        nodes[node] = MetaNode(id_prefixes=prefixes)

    edges = []
    for biolink_subject, biolink_objects in PREDICATES.items():
        for biolink_object, biolink_predicates in biolink_objects.items():
            for predicate in biolink_predicates:
                edges.append(MetaEdge(
                    subject=biolink_subject,
                    object=biolink_object,
                    predicate=predicate
                ))

    return MetaKnowledgeGraph(nodes=nodes, edges=edges)


def meta_knowledge_graph_get():  # noqa: E501
    """Meta knowledge graph representation of this TRAPI web service.

     # noqa: E501


    :rtype: MetaKnowledgeGraph
    """
    return _make_meta_kg()
