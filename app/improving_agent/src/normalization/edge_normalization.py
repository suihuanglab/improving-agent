from collections import defaultdict

from werkzeug.exceptions import BadRequest, NotImplemented

from improving_agent.exceptions import (
    MissingComponentError,
    UnsupportedKnowledgeType,
    UnsupportedQualifier,
    UnsupportedTypeError
)
from improving_agent.models import QEdge
from improving_agent.src.biolink.biolink import EDGE, get_supported_biolink_descendants
from improving_agent.src.biolink.spoke_biolink_constants import (
    BIOLINK_ASSOCIATION_AFFECTS,
    BIOLINK_ASSOCIATION_TREATS,
    BIOLINK_ENTITY_CHEMICAL_ENTITY,
    BIOLINK_ENTITY_DISEASE,
    BIOLINK_ENTITY_DRUG,
    BIOLINK_ENTITY_GENE,
    BIOLINK_ENTITY_SMALL_MOLECULE,
    BIOLINK_SPOKE_EDGE_MAPPINGS,
    BL_QUALIFIER_TYPE_OBJECT_ASPECT,
    BL_QUALIFIER_TYPE_OBJECT_DIRECTION,
    BL_QUALIFIER_TYPE_QUALIFIED_PREDICATE,
    KNOWLEDGE_TYPE_INFERRED,
    KNOWLEDGE_TYPE_LOOKUP,
    PREDICATES,
    QUALIFIERS,
    SPOKE_ANY_TYPE,
    SPOKE_BIOLINK_EDGE_MAPPINGS,
)


SUPPORTED_KNOWLEDGE_TYPES = (KNOWLEDGE_TYPE_INFERRED, KNOWLEDGE_TYPE_LOOKUP)
SUPPORTED_INFERRED_DRUG_SUBJ = [
    BIOLINK_ENTITY_CHEMICAL_ENTITY,
    BIOLINK_ENTITY_DRUG,
    BIOLINK_ENTITY_SMALL_MOLECULE
]

SUPPORTED_INFERRED_PRED_SUBJ_OBJ_MAP = {
    BIOLINK_ASSOCIATION_AFFECTS: {
        'subject': [BIOLINK_ENTITY_CHEMICAL_ENTITY],
        'object': [BIOLINK_ENTITY_GENE],
    },
    BIOLINK_ASSOCIATION_TREATS: {
        'subject': SUPPORTED_INFERRED_DRUG_SUBJ,
        'object': [BIOLINK_ENTITY_DISEASE],
    }
}


def _verify_qedge_kt_support(qedge, subj_qnode, obj_qnode):
    """Raises if the requested knowledge_type on the edge is not
    supported

    TODO: Depending on how extensive knowledge_type becomes, it may make
    sense to move this function to a different module and refactor it
    accordingly.
    """
    if qedge.knowledge_type is None or qedge.knowledge_type == KNOWLEDGE_TYPE_LOOKUP:
        return
    if qedge.knowledge_type not in SUPPORTED_KNOWLEDGE_TYPES:
        raise UnsupportedKnowledgeType(
            f'imProving Agent only supports knowledge types: {", ".join(i for i in SUPPORTED_KNOWLEDGE_TYPES)}'
        )
    if qedge.knowledge_type == KNOWLEDGE_TYPE_INFERRED:
        if len(qedge.predicates) > 1:
            raise UnsupportedKnowledgeType('"inferred" knowledge_type queries only allow one predicate')
        predicate = qedge.predicates[0]
        supported_node_types = SUPPORTED_INFERRED_PRED_SUBJ_OBJ_MAP.get(predicate)
        if not supported_node_types:
            raise UnsupportedKnowledgeType(
                'Only "biolink:affects" or "biolink:treats" are allowed for "inferred" queries'
            )
        if not subj_qnode.categories or not obj_qnode.categories:
            raise UnsupportedKnowledgeType(
                'imProving Agent requires that qnodes must have a "categories" '
                f'property when using "inferred" predicate "{predicate}"'
            )
        if not all(cat in supported_node_types['subject'] for cat in subj_qnode.categories):
            raise UnsupportedKnowledgeType(
                f'Unsupported qnode subject for "inferred" predicate "{predicate}"'
            )
        if not all(cat in supported_node_types['object'] for cat in obj_qnode.categories):
            raise UnsupportedKnowledgeType(
                f'Unsupported qnode object for "inferred" predicate "{predicate}"'
            )


def _deserialize_qedge(qedge_id, qedge):
    try:
        subject = qedge['subject']
        object_ = qedge['object']

        constraints = qedge.get('attribute_constraints')
        knowledge_type = qedge.get('knowledge_type')
        predicates = qedge.get('predicates')
        qualifiers = qedge.get('qualifier_constraints')

        qedge = QEdge(
            attribute_constraints=constraints,
            knowledge_type=knowledge_type,
            predicates=predicates,
            object=object_,
            subject=subject,
            qualifier_constraints=qualifiers,
        )
        setattr(qedge, 'qedge_id', qedge_id)

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


def _are_qualifiers_compatible(qedge, spoke_edge):
    query_qualifiers = qedge.qualifier_constraints
    if not query_qualifiers:
        return True

    spoke_edge_qualifiers = SPOKE_BIOLINK_EDGE_MAPPINGS[spoke_edge].get(QUALIFIERS)
    if not spoke_edge_qualifiers:
        return False

    for qualifier_set in query_qualifiers:
        query_data = {
            'aspects': [],
            'directions': [],
            'qualified_predicates': [],
        }
        for qualifier in qualifier_set['qualifier_set']:
            qualifier_type = qualifier['qualifier_type_id']
            if qualifier_type == BL_QUALIFIER_TYPE_OBJECT_ASPECT:
                query_data['aspects'].append(qualifier['qualifier_value'])
            elif qualifier_type == BL_QUALIFIER_TYPE_OBJECT_DIRECTION:
                query_data['directions'].append(qualifier['qualifier_value'])
            elif qualifier_type == BL_QUALIFIER_TYPE_QUALIFIED_PREDICATE:
                query_data['qualified_predicates'].append(qualifier['qualifier_value'])
            else:
                raise UnsupportedQualifier(
                    'imProving Agent does not support '
                    f'qualifier_type_id={qualifier_type}'
                )

        if query_data['directions'] and not query_data['aspects']:
            raise UnsupportedQualifier(
                'imProving Agent does not support qualifier directions '
                'without a qualifier aspect'
            )

    if not all(
        aspect in spoke_edge_qualifiers[BL_QUALIFIER_TYPE_OBJECT_ASPECT]
        for aspect
        in query_data['aspects']
    ):
        return False
    if not all(
        direction in spoke_edge_qualifiers[BL_QUALIFIER_TYPE_OBJECT_DIRECTION]
        for direction
        in query_data['directions']
    ):
        return False
    if query_data['qualified_predicates']:
        if not all(
            predicate in spoke_edge_qualifiers[BL_QUALIFIER_TYPE_QUALIFIED_PREDICATE]
            for predicate
            in query_data['qualified_predicates']
        ):
            return False

    return True


def _get_compatible_spoke_edges(qedge):
    compatible_edges = []
    compatible_predicates = get_supported_biolink_descendants(qedge.predicates, EDGE)
    for predicate in compatible_predicates:
        spoke_edge_mappings = BIOLINK_SPOKE_EDGE_MAPPINGS.get(predicate)
        if not spoke_edge_mappings:
            raise UnsupportedTypeError(f'imProving Agent does not currently accept predicates of type {predicate}')

        for spoke_edge_type in spoke_edge_mappings:
            if _are_qualifiers_compatible(qedge, spoke_edge_type):
                compatible_edges.append(spoke_edge_type)

    if not compatible_edges:
        raise UnsupportedTypeError(
            'imProving Agent could not match this combination of predicates '
            'and (if present) qualifier constraints'
        )

    return compatible_edges


def _assign_spoke_edge_types(qedge):
    spoke_edge_types = []
    if qedge.qualifier_constraints:
        if not qedge.predicates:
            raise MissingComponentError(
                'imProving Agent requires that queries with constraints '
                'include predicates for validation '
            )

    if qedge.predicates:
        spoke_edge_types.extend(_get_compatible_spoke_edges(qedge))
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
