from werkzeug.exceptions import BadRequest
from werkzeug.exceptions import NotImplemented as NotImplemented501
from .curie_formatters import (
    format_curie_for_sri,
    get_spoke_identifier_from_normalized_node,
    get_label_if_appropriate_spoke_curie,
)
from .sri_node_normalizer import (
    NODE_NORMALIZATION_RESPONSE_VALUE_ID,
    NODE_NORMALIZATION_RESPONSE_VALUE_IDENTIFIER,
    SRI_NODE_NORMALIZER
)
from improving_agent.models import QNode
from improving_agent.exceptions import UnmatchedIdentifierError
from improving_agent.src.spoke_biolink_constants import (
    BIOLINK_ENTITY_PROTEIN,
    BIOLINK_SPOKE_NODE_MAPPINGS,
    SPOKE_LABEL_GENE
)
from improving_agent.util import get_evidara_logger

QNODE_CURIE_SPOKE_IDENTIFIERS = 'spoke_identifiers'

logger = get_evidara_logger(__name__)


def normalize_spoke_nodes_for_translator(spoke_search_nodes):
    """Returns a mapping of SPOKE CURIE to their normalized equivalents
    If normalized equivalents are not found, the SPOKE CURIE is returned

    Parameters
    ----------
    spoke_search_nodes (list of SearchNode)
    """
    # don't search proteins
    formatted_curie_node_map = {
        format_curie_for_sri(search_node.category, search_node.curie): search_node
        for search_node
        in spoke_search_nodes
    }
    search_results = SRI_NODE_NORMALIZER.get_normalized_nodes(list(formatted_curie_node_map.keys()))
    result_map = {}
    for formatted_curie, search_node in formatted_curie_node_map.items():
        if search_node.category == BIOLINK_ENTITY_PROTEIN:
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


def _deserialize_qnode(qnode_id, qnode):
    """Returns a QNode from a single deserialized QueryGraph node in a
    TRAPI request
    """
    try:
        qnode = QNode(**qnode)
        setattr(qnode, 'qnode_id', qnode_id)
    except TypeError:
        raise BadRequest(f'Could not deserialize qnode={qnode}')

    return qnode


def _assign_spoke_node_label(qnode):
    spoke_labels = []
    if qnode.category:
        for category in qnode.category:
            spoke_label = BIOLINK_SPOKE_NODE_MAPPINGS.get(category)
            if spoke_label is None:
                raise NotImplemented501(f'imProving Agent does not accept query nodes of category {category}')
            if isinstance(spoke_label, str):
                spoke_label = [spoke_label]
            spoke_labels.extend(spoke_label)

    setattr(qnode, 'spoke_labels', spoke_labels)
    return qnode


def _check_and_format_qnode_curies_for_search(qnodes):
    normalized_qnodes = {}
    formatted_search_nodes = {}
    for qnode_id, qnode in qnodes.items():
        setattr(qnode, QNODE_CURIE_SPOKE_IDENTIFIERS, [])
        if qnode.id:
            if not qnode.spoke_labels:
                raise NotImplemented501(
                    'imProving Agent requires that identifiers have a specified biolink category'
                )
            for curie in qnode.id:
                matched_label = get_label_if_appropriate_spoke_curie(qnode.spoke_labels, curie)
                if matched_label:
                    # str formatting for where clauses
                    if matched_label == SPOKE_LABEL_GENE:
                        qnode.spoke_identifiers.append(curie)
                    else:
                        qnode.spoke_identifiers.append(f"'{curie}'")
                    normalized_qnodes[qnode_id] = qnode
                    continue
                else:
                    # Not sure this actually does anything useful if don't already recognize its pattern
                    for category in qnode.category:
                        formatted_search_nodes[format_curie_for_sri(category, curie)] = qnode_id
        else:
            normalized_qnodes[qnode_id] = qnode

    return normalized_qnodes, formatted_search_nodes


def _normalize_query_nodes_for_spoke(qnodes):
    normalized_qnodes, formatted_search_nodes = _check_and_format_qnode_curies_for_search(qnodes)
    if formatted_search_nodes:
        search_results = SRI_NODE_NORMALIZER.get_normalized_nodes(list(formatted_search_nodes.keys()))
        for formatted_curie, qnode_id in formatted_search_nodes.items():
            normalized_node = search_results.get(formatted_curie)
            if normalized_node is None:
                continue

            qnode = normalized_qnodes.get(qnode_id)
            if not qnode:
                qnode = qnodes[qnode_id]

            spoke_identifier = get_spoke_identifier_from_normalized_node(
                qnode.spoke_labels,
                normalized_node,
                formatted_curie
            )
            if not spoke_identifier:
                continue

            qnode.spoke_identifiers.append(spoke_identifier)
            normalized_qnodes[qnode.qnode_id] = qnode

    if not qnodes.keys() == normalized_qnodes.keys():  # we were unable to map some of the qnodes
        raise UnmatchedIdentifierError(
            f'No identifiers for qnodes {qnodes.keys() - normalized_qnodes.keys()} could be mapped to SPOKE'
        )
    return normalized_qnodes


def validate_normalize_qnodes(qnodes):
    """Returns deserializes QNodes that have been mapped for SPOKE
    querying

    Parameters
    ----------
    qnodes: Query.Message.QueryGraph.nodes -- the nodes component of
        the QueryGraph from a TRAPI query
    """
    for qnode_id, qnode in qnodes.items():
        qnode = _deserialize_qnode(qnode_id, qnode)
        qnode = _assign_spoke_node_label(qnode)
        qnodes[qnode_id] = qnode

    return _normalize_query_nodes_for_spoke(qnodes)
