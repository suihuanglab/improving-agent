from collections import defaultdict

from werkzeug.exceptions import BadRequest

from improving_agent.exceptions import (
    MissingComponentError,
    UnsupportedKnowledgeType,
    UnsupportedTypeError
)
from improving_agent.models import QEdge
from improving_agent.src.biolink.biolink import EDGE, get_supported_biolink_descendants
from improving_agent.src.biolink.spoke_biolink_constants import BIOLINK_SPOKE_EDGE_MAPPINGS, PREDICATES, SPOKE_ANY_TYPE

BIOLINK_DISEASE = 'biolink:Disease'
BIOLINK_DRUG = 'biolink:Drug'
BIOLINK_TREATS = 'biolink:treats'
BIOLINK_SMALL_MOL = 'biolink:SmallMolecule'

KNOWLEDGE_TYPE_INFERRED = 'inferred'
KNOWLEDGE_TYPE_KNOWN = 'known'
SUPPORTED_KNOWLEDGE_TYPES = (KNOWLEDGE_TYPE_INFERRED, KNOWLEDGE_TYPE_KNOWN)
SUPPORTED_INFERRED_DRUG_SUBJ = [BIOLINK_DRUG, BIOLINK_SMALL_MOL]


def _verify_qedge_kt_support(qedge, subj_qnode, obj_qnode):
    """Raises if the requested knowledge_type on the edge is not
    supported

    TODO: Depending on how extensive knowledge_type becomes, it may make
    sense to move this function to a different module and refactor it
    accordingly.
    """
    if qedge.knowledge_type is None or qedge.knowledge_type == KNOWLEDGE_TYPE_KNOWN:
        return None
    if qedge.knowledge_type not in SUPPORTED_KNOWLEDGE_TYPES:
        raise UnsupportedKnowledgeType(
            f'imProving Agent only supports knowledge types: {", ".join(i for i in SUPPORTED_KNOWLEDGE_TYPES)}'
        )
    if qedge.knowledge_type == KNOWLEDGE_TYPE_INFERRED:
        if qedge.predicates != [BIOLINK_TREATS]:
            raise UnsupportedKnowledgeType(
                'Only a single "biolink:treats" is supported for "inferred" knowledge_type'
            )
        if not all(cat in SUPPORTED_INFERRED_DRUG_SUBJ for cat in subj_qnode.categories):
            raise UnsupportedKnowledgeType(
                'Inferred knowledge_type "biolink:treats" only supported qnode subject '
                f'categories {", ".join(SUPPORTED_INFERRED_DRUG_SUBJ)}'
            )
        if obj_qnode.categories != [BIOLINK_DISEASE]:
            raise UnsupportedKnowledgeType(
                'Inferred knowledge_type "biolink:treats" only supported qnode object '
                f'categories {", ".join([BIOLINK_DISEASE])}'
            )


def _deserialize_qedge(qedge_id, qedge):
    try:
        subject = qedge['subject']
        object_ = qedge['object']
        constraints = qedge.get('constraints')
        predicates = qedge.get('predicates')
        knowledge_type = qedge.get('knowledge_type')
        qedge = QEdge(
            predicates=predicates,
            subject=subject,
            object=object_,
            constraints=constraints
        )
        setattr(qedge, 'qedge_id', qedge_id)
        setattr(qedge, 'knowledge_type', knowledge_type)

    except (KeyError, TypeError):
        raise BadRequest(f'Could not deserialize query edge {qedge_id}')

    return qedge


def _get_objects_maps(subj_qnode):
    if not subj_qnode.category:
        return list(PREDICATES.values())

    objects_maps = []
    for category in subj_qnode.category:
        objects_map = PREDICATES.get(category)
        if objects_map:
            objects_maps.append(objects_map)

    if not objects_maps:
        raise UnsupportedTypeError(f'Could not find any supported predicates for subject category: {subj_qnode.category}')

    return objects_maps


def _get_potential_predicate_maps(subj_qnode, obj_qnode):
    objects_maps = _get_objects_maps(subj_qnode)
    potential_predicates_map = defaultdict(list)
    if not obj_qnode.category:
        for objects_map in objects_maps:
            for predicate, spoke_edges in objects_map.items():
                potential_predicates_map[predicate].extend(spoke_edges)
        return potential_predicates_map

    for category in obj_qnode.category:
        for objects_map in objects_maps:
            predicates_map = objects_map.get(category)
            if not predicates_map:
                continue
            for predicate, spoke_edges in predicates_map.items():
                potential_predicates_map[predicate].extend(spoke_edges)

    if not potential_predicates_map:
        raise UnsupportedTypeError(
            'Could not find any supported predicates for subject category: '
            f'{subj_qnode.category} and object category: {obj_qnode.category}'
        )
    return potential_predicates_map


def _get_subject_object_qnodes(query_graph, qedge):
    subject_node = query_graph.nodes.get(qedge.subject)
    object_node = query_graph.nodes.get(qedge.object)
    if not subject_node or not object_node:
        raise MissingComponentError(f'Subject or object missing for query edge {qedge.qedge_id}')

    return subject_node, object_node


def _assign_spoke_edge_types(qedge):
    spoke_edge_types = []
    if qedge.predicates:
        compatible_predicates = get_supported_biolink_descendants(qedge.predicates, EDGE)
        for predicate in compatible_predicates:
            spoke_edge_mappings = BIOLINK_SPOKE_EDGE_MAPPINGS.get(predicate)
            if not spoke_edge_mappings:
                raise UnsupportedTypeError(f'imProving Agent does not currently accept predicates of type {predicate}')
            spoke_edge_types.extend(spoke_edge_mappings)
        if not spoke_edge_types:
            raise UnsupportedTypeError(
                f'imProving Agent does not currently accept predicates of type {qedge.predicates}'
            )
    else:
        spoke_edge_types.append(SPOKE_ANY_TYPE)

    setattr(qedge, 'spoke_edge_types', set(spoke_edge_types))
    return qedge


def validate_normalize_qedges(query_graph):
    qedges = {}
    for qedge_id, qedge in query_graph.edges.items():
        qedge = _deserialize_qedge(qedge_id, qedge)
        subj_qnode, obj_qnode = _get_subject_object_qnodes(query_graph, qedge)
        _verify_qedge_kt_support(qedge, subj_qnode, obj_qnode)
        qedge = _assign_spoke_edge_types(qedge)
        qedges[qedge_id] = qedge

    return qedges
