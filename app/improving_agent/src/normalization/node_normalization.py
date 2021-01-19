from werkzeug.exceptions import BadRequest
from werkzeug.exceptions import NotImplemented as NotImplemented501
from .curie_formatters import (
    format_curie_for_sri,
    get_spoke_identifier_from_normalized_node,
    is_qnode_curie_already_acceptable_for_spoke,
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

QNODE_CURIE_SPOKE_IDENTIFIER = 'spoke_identifier'

logger = get_evidara_logger(__name__)


def normalize_spoke_nodes_for_translator(spoke_search_nodes):
    """Returns a mapping of SPOKE CURIE to their normalized equivalents
    If normalized equivalents are not found, the SPOKE CURIE is returned

    Parameters
    ----------
    spoke_search_nodes (list of SearchNode)
    """
    # don't search proteins
    formatted_curie_node_map = {format_curie_for_sri(search_node): search_node for search_node in spoke_search_nodes}
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
    spoke_label = ""
    if qnode.category:
        if len(qnode.category) > 1:
            # developer warning: this could error if we stop getting lists of categories
            # which is currently happening due to an openAPI generator workaround
            # TODO: Support multi-label/category nodes
            raise NotImplemented501('imProving Agent currently only accepts single-category query nodes')
        spoke_label = BIOLINK_SPOKE_NODE_MAPPINGS.get(qnode.category[0])
        if spoke_label is None:
            raise NotImplemented501(f'imProving Agent does not accept query nodes of category {qnode.category[0]}')
    setattr(qnode, 'spoke_label', spoke_label)
    return qnode


def _check_and_format_qnode_curies_for_search(qnodes):
    normalized_qnodes = {}
    formatted_search_nodes = {}
    for qnode_id, qnode in qnodes.items():
        if qnode.id:
            if len(qnode.id) > 1:  # this is a list
                raise NotImplemented501('imProving Agent currently only accepts single-CURIE query nodes')
            if is_qnode_curie_already_acceptable_for_spoke(qnode.spoke_label, qnode.id[0]):
                if qnode.spoke_label == SPOKE_LABEL_GENE:
                    setattr(qnode, QNODE_CURIE_SPOKE_IDENTIFIER, int(qnode.id[0]))
                else:
                    setattr(qnode, QNODE_CURIE_SPOKE_IDENTIFIER, qnode.id[0])
                normalized_qnodes[qnode_id] = qnode
                continue
            else:
                formatted_search_nodes[format_curie_for_sri(qnode)] = qnode_id
        else:
            setattr(qnode, QNODE_CURIE_SPOKE_IDENTIFIER, '')
            normalized_qnodes[qnode_id] = qnode

    return normalized_qnodes, formatted_search_nodes


def _normalize_query_nodes_for_spoke(qnodes):
    normalized_qnodes, formatted_search_nodes = _check_and_format_qnode_curies_for_search(qnodes)
    if formatted_search_nodes:
        search_results = SRI_NODE_NORMALIZER.get_normalized_nodes(list(formatted_search_nodes.keys()))
        for formatted_curie, qnode_id in formatted_search_nodes.items():
            normalized_node = search_results.get(formatted_curie)
            qnode = qnodes[qnode_id]
            if normalized_node is None:
                # TODO make a more helpful message that includes the preferred curie for a given Biolink category
                raise UnmatchedIdentifierError(f'Specified search CURIE {qnode.id[0]} could not be mapped to SPOKE')
            spoke_identifier = get_spoke_identifier_from_normalized_node(qnode.spoke_label, normalized_node, qnode.id[0])
            setattr(qnode, QNODE_CURIE_SPOKE_IDENTIFIER, spoke_identifier)
            normalized_qnodes[qnode.qnode_id] = qnode

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
