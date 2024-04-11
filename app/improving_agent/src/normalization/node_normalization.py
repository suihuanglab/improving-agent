from werkzeug.exceptions import BadRequest

from .curie_formatters import (
    format_curie_for_sri,
    get_spoke_identifiers_from_normalized_node,
    get_label_if_appropriate_spoke_curie,
)
from .sri_node_normalizer import (
    SRI_NN_RESPONSE_VALUE_ID,
    SRI_NN_RESPONSE_VALUE_IDENTIFIER,
    SRI_NODE_NORMALIZER
)
from improving_agent.models import AttributeConstraint, QNode
from improving_agent.exceptions import (
    UnmatchedIdentifierError,
    UnsupportedSetInterpretation,
    UnsupportedTypeError,
)
from improving_agent.src.biolink.biolink import get_supported_biolink_descendants, NODE
from improving_agent.src.biolink.spoke_biolink_constants import (
    BIOLINK_ENTITY_PROTEIN,
    BIOLINK_SPOKE_NODE_MAPPINGS,
    SPOKE_LABEL_GENE
)
from improving_agent.src.constraints import validate_constraint_support
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
        format_curie_for_sri(search_node.category, search_node.curie, search_node.source): search_node
        for search_node
        in spoke_search_nodes
    }
    search_curies = list(formatted_curie_node_map.keys())
    search_results = {}

    # chunk per SRI guidance
    chunk_size = 1000
    start = 0
    end = start + chunk_size
    while start <= len(search_curies):
        search_chunk = search_curies[start:end]
        search_results = {**search_results, **SRI_NODE_NORMALIZER.get_normalized_nodes(search_chunk)}
        start += chunk_size
        end += chunk_size

    result_map = {}
    for formatted_curie, search_node in formatted_curie_node_map.items():
        if search_node.category == BIOLINK_ENTITY_PROTEIN:
            # the node normalizer will suggest the NCBIGENE curies for proteins
            # so we keep the UNIPROT CURIE here instead
            result_map[search_node.curie] = formatted_curie
            continue
        normalized_node = search_results.get(formatted_curie)
        if normalized_node is None:
            result_map[search_node.curie] = formatted_curie
        else:
            result_map[search_node.curie] = \
                normalized_node[SRI_NN_RESPONSE_VALUE_ID][SRI_NN_RESPONSE_VALUE_IDENTIFIER]
    return result_map


def _deserialize_qnode(qnode_id, qnode):
    """Returns a QNode from a single deserialized QueryGraph node in a
    TRAPI request
    """
    constraints = []
    try:
        ids = qnode.get('ids')
        categories = qnode.get('categories')
        req_constraints = qnode.get('attribute_constraints')
        set_interpretation = qnode.get('set_interpretation', 'BATCH')
        if set_interpretation != 'BATCH':
            raise UnsupportedSetInterpretation(
                'imProving Agent only supports BATCH set interpretation'
            )
        if req_constraints:
            for constraint in req_constraints:
                try:
                    attribute_constraints = AttributeConstraint(**constraint)
                    constraints.append(attribute_constraints)
                except TypeError:
                    BadRequest(f'Could not deserialize constraint={constraint}')
        qnode = QNode(ids, categories, set_interpretation, constraints)
        setattr(qnode, 'qnode_id', qnode_id)
    except TypeError:
        raise BadRequest(f'Could not deserialize qnode={qnode}')

    return qnode


def _assign_spoke_node_label(qnode):
    spoke_labels = []
    if qnode.categories:
        compatible_categories = get_supported_biolink_descendants(qnode.categories, NODE)
        for category in compatible_categories:
            node_mapping = BIOLINK_SPOKE_NODE_MAPPINGS.get(category)
            if node_mapping is None:
                continue
            spoke_label = node_mapping.spoke_label
            if isinstance(spoke_label, str):
                spoke_label = [spoke_label]
            spoke_labels.extend(spoke_label)
        if not spoke_labels:
            raise UnsupportedTypeError(f'imProving Agent could not find query nodes of category {qnode.categories}')

    setattr(qnode, 'spoke_labels', spoke_labels)
    return qnode


def _check_and_format_qnode_curies_for_search(qnodes):
    normalized_qnodes = {}
    formatted_search_nodes = {}
    for qnode_id, qnode in qnodes.items():
        setattr(qnode, QNODE_CURIE_SPOKE_IDENTIFIERS, {})
        if qnode.ids:
            # TODO: Consider axing this pre-check logic and just sending
            # everything to SRI node normalizer. At this point (2021-09)
            # the NN is reliable and robust and we're not trying to
            # return results from SPOKE that aren't represented in NN
            for curie in qnode.ids:
                matched_label = get_label_if_appropriate_spoke_curie(qnode.spoke_labels, curie)
                if matched_label:
                    # str formatting for where clauses
                    if matched_label == SPOKE_LABEL_GENE:
                        qnode.spoke_identifiers[curie] = curie
                    else:
                        qnode.spoke_identifiers[f"'{curie}'"] = curie
                    normalized_qnodes[qnode_id] = qnode
                    continue
                else:
                    if qnode.categories:
                        for category in qnode.categories:
                            formatted_curies = format_curie_for_sri(category, curie)
                            if isinstance(formatted_curies, str):
                                formatted_curies = [formatted_curies]
                            for formatted_curie in formatted_curies:
                                formatted_search_nodes[formatted_curie] = qnode_id
                    else:
                        formatted_search_nodes[curie] = qnode_id
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

            spoke_identifiers, updated_spoke_labels = get_spoke_identifiers_from_normalized_node(
                qnode.spoke_labels,
                normalized_node,
            )
            setattr(qnode, 'spoke_labels', updated_spoke_labels)
            if not spoke_identifiers:
                continue

            for identifier in spoke_identifiers:
                qnode.spoke_identifiers[identifier] = formatted_curie
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

    normalized_nodes = _normalize_query_nodes_for_spoke(qnodes)

    # check constraints; we do this last because we need the SPOKE labels
    for normalized_node in normalized_nodes.values():
        if normalized_node.constraints:
            for node_constraint in normalized_node.constraints:
                validate_constraint_support(node_constraint, normalized_node.spoke_labels)

    return normalized_nodes
