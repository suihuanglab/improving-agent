from werkzeug.exceptions import BadRequest

from improving_agent.exceptions import (
    AmbiguousPredicateMappingError,
    MissingComponentError,
    UnsupportedTypeError
)
from improving_agent.models import QEdge
from improving_agent.src.spoke_biolink_constants import BIOLINK_SPOKE_EDGE_MAPPINGS, PREDICATES


def _deserialize_qedge(qedge_id, qedge):
    try:
        qedge = QEdge(**qedge)
        setattr(qedge, 'qedge_id', qedge_id)
    except TypeError:
        raise BadRequest(f'Could not deserialize query edge {qedge_id}')

    return qedge


def _disambiguate_edge_type(predicate, qedge, query_graph):
    """Returns the specific SPOKE edge types that map to the requested
    ambiguous biolink predicate given the subject and object correspeonding
    to the predicate in the query_graph
    """
    subject_node = query_graph.nodes.get(qedge.subject)
    object_node = query_graph.nodes.get(qedge.object)
    if not subject_node or not object_node:
        raise MissingComponentError(f'Subject or object missing for query edge {qedge.qedge_id}')

    if not subject_node.category or not object_node.category:
        raise AmbiguousPredicateMappingError(
            f'Requested {predicate} is ambiguous in SPOKE. Categories for '
            'the corresponding subject and object query nodes must be specified'
        )

    objects_map = PREDICATES.get(subject_node.category[0])
    if not objects_map:
        raise UnsupportedTypeError(f'Could not find any supported predicates for subject category: {subject_node.category[0]}')

    predicates_map = objects_map.get(object_node.category[0])
    if not predicates_map:
        raise UnsupportedTypeError(
            f'Could not find any supported predicates for subject category: '
            f'{subject_node.category[0]} and object category: {object_node.category[0]}'
        )

    spoke_edge_types = predicates_map.get(predicate)
    if not spoke_edge_types:
        raise UnsupportedTypeError(
            f'Requested {predicate}, but it is not valid for subject category '
            f'{subject_node.category[0]} and object category {object_node.category[0]}'
        )

    if isinstance(spoke_edge_types, str):
        spoke_edge_types = [spoke_edge_types]

    return spoke_edge_types


def _assign_spoke_edge_types(qedge, query_graph):
    spoke_edge_types = []
    if qedge.predicate:
        for predicate in qedge.predicate:
            spoke_edge_mappings = BIOLINK_SPOKE_EDGE_MAPPINGS.get(predicate)
            if not spoke_edge_mappings:
                raise UnsupportedTypeError(f'imProving Agent does not currently accept predicates of type {predicate}')
            if len(spoke_edge_mappings) > 1:
                spoke_edge_mappings = _disambiguate_edge_type(predicate, qedge, query_graph)
            spoke_edge_types.extend(spoke_edge_mappings)

    setattr(qedge, 'spoke_edge_types', set(spoke_edge_types))
    return qedge


def validate_normalize_qedges(query_graph):
    qedges = {}
    for qedge_id, qedge in query_graph.edges.items():
        qedge = _deserialize_qedge(qedge_id, qedge)
        qedge = _assign_spoke_edge_types(qedge, query_graph)
        qedges[qedge_id] = qedge

    return qedges
