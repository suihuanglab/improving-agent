"""This module is a WIP, with result handling features migrated here
as there is time.
"""
from copy import deepcopy

import neo4j
import neo4j.graph

from improving_agent.models.attribute import Attribute
from improving_agent.models.edge import Edge
from improving_agent.models.knowledge_graph import KnowledgeGraph
from improving_agent.models.node import Node
from improving_agent.models.node_binding import NodeBinding
from improving_agent.models.result import Result
from improving_agent.models.retrieval_source import RetrievalSource
from improving_agent.src.biolink.spoke_biolink_constants import (
    BIOLINK_ASSOCIATION_IN_CLINICAL_TRIALS_FOR,
    BIOLINK_ASSOCIATION_IN_PRECLINICAL_TRIALS_FOR,
    BIOLINK_ASSOCIATION_RELATED_TO,
    BIOLINK_ASSOCIATION_TREATS,
    BIOLINK_ASSOCIATION_TYPE,
    BIOLINK_SLOT_AGENT_TYPE,
    BIOLINK_SLOT_HIGHEST_FDA_APPROVAL,
    BIOLINK_SLOT_KNOWLEDGE_LEVEL,
    BIOLINK_SLOT_MAX_RESEARCH_PHASE,
    BL_ATTR_PRIMARY_KNOWLEDGE_SOURCE,
    BL_MAX_RESEARCH_PHASE_ENUM_PC_RESEARCH_PHASE,
    BL_MAX_RESEARCH_PHASE_ENUM_PHASE_4,
    BL_RELATION_SOURCE_KL_AT_MAP,
    KNOWLEDGE_TYPE_INFERRED,
    KNOWLEDGE_TYPE_LOOKUP,
    KNOWN_UNMAPPED_ATTRS,
    MAX_PHASE_FDA_APPROVAL_MAP,
    PHASE_BL_CT_PHASE_ENUM_MAP,
    QUALIFIERS,
    SPOKE_BIOLINK_EDGE_ATTRIBUTE_MAPPINGS,
    SPOKE_BIOLINK_EDGE_MAPPINGS,
    SPOKE_BIOLINK_NODE_ATTRIBUTE_MAPPINGS,
    SPOKE_BIOLINK_NODE_MAPPINGS,
    SPOKE_PROPERTY_NATIVE_SPOKE,
    TRAPI_AGENT_TYPE_ENUM_MANUAL_AGENT,
    TRAPI_AGENT_TYPE_ENUM_NOT_PROVIDED,
    TRAPI_KNOWLEDGE_LEVEL_KNOWLEDGE_ASSERTION,
    TRAPI_KNOWLEDGE_LEVEL_NOT_PROVIDED,
    Infores,
    INFORES_CHEMBL,
    INFORES_DRUGCENTRAL,
    INFORES_SPOKE,
)
from improving_agent.src.improving_agent_constants import (
    SPOKE_NODE_PROPERTY_SOURCE,
)
from improving_agent.src.normalization import SearchNode
from improving_agent.src.normalization.node_normalization import (
    normalize_spoke_nodes_for_translator,
)
from improving_agent.src.provenance import (
    choose_primary_source,
    get_internal_retrieval_sources,
    make_default_retrieval_sources,
    make_publications_attribute,
    make_retrieval_sources,
    SPOKE_PROVENANCE_FIELDS,
    SPOKE_PUBLICATION_FIELDS,
    TREATS_LOOKUP_RETRIEVAL_SOURCE_MAP,
)
from improving_agent.util import get_evidara_logger


_logger = get_evidara_logger(__name__)


def get_edge_qualifiers(qualifier_map):
    qualifiers = []
    for qualifier_type, value in qualifier_map.items():
        qualifiers.append({
            'qualifier_type_id': qualifier_type,
            'qualifier_value': value,
        })
    return qualifiers


def _make_attribute(
    type_: str,
    value: str,
    source: Infores,
):
    return Attribute(
        attribute_type_id=type_,
        value=value,
        attribute_source=source.infores_id,
    )


def get_max_research_phase_attr(attr_val: int) -> Attribute:
    """Returns a biolink compliant attribute for the TREATS_CtD
    max_phase property that comes from ChEMBL
    """
    pass


def _get_unknown_kl_at_attrs() -> list[Attribute]:
    at_attr = _make_attribute(BIOLINK_SLOT_AGENT_TYPE, TRAPI_AGENT_TYPE_ENUM_NOT_PROVIDED, INFORES_SPOKE)
    kl_attr = _make_attribute(BIOLINK_SLOT_KNOWLEDGE_LEVEL, TRAPI_KNOWLEDGE_LEVEL_NOT_PROVIDED, INFORES_SPOKE)
    return [at_attr, kl_attr]


def _get_default_kl_at_attrs(
    predicate: str,
    retrieval_sources: list[RetrievalSource],
) -> list[Attribute]:
    """Returns a list of two attributes for an edge based on the edge
    type and the source of the edge
    """
    primary_source = None
    for rs in retrieval_sources:
        if rs.resource_role == BL_ATTR_PRIMARY_KNOWLEDGE_SOURCE:
            primary_source = rs.resource_id

    predicate_source_klat_map = BL_RELATION_SOURCE_KL_AT_MAP.get(predicate)

    if primary_source is None or predicate_source_klat_map is None:
        return _get_unknown_kl_at_attrs()

    edge_source_klat = predicate_source_klat_map.get(primary_source)
    if edge_source_klat is None:
        return _get_unknown_kl_at_attrs()

    return [
        _make_attribute(BIOLINK_SLOT_AGENT_TYPE, edge_source_klat.agent_type, INFORES_SPOKE),
        _make_attribute(BIOLINK_SLOT_KNOWLEDGE_LEVEL, edge_source_klat.knowledge_level, INFORES_SPOKE),
    ]


def _get_kl_at_attrs_for_treats_lookup() -> list[Attribute]:
    # for spoke LOOKUPs, all supported edges are currently the same
    # knowledge level
    kl_attr = _make_attribute(
        BIOLINK_SLOT_KNOWLEDGE_LEVEL,
        TRAPI_KNOWLEDGE_LEVEL_KNOWLEDGE_ASSERTION,
        INFORES_SPOKE,
    )
    at_attr = _make_attribute(
        BIOLINK_SLOT_AGENT_TYPE,
        TRAPI_AGENT_TYPE_ENUM_MANUAL_AGENT,
        INFORES_SPOKE,
    )
    return [kl_attr, at_attr]


# knowledge level and agent type (kl & at)
def _evaluate_treats_lookup(
    attributes: list[Attribute],
    retrieval_sources: list[RetrievalSource],
) -> tuple[str, list[Attribute], list[RetrievalSource]]:
    kl_at_attrs = _get_kl_at_attrs_for_treats_lookup()

    # evaluate sources to guide logic below
    chembl_in_source = False
    drugcentral_in_source = False
    for retrieval_source in retrieval_sources:
        if retrieval_source.resource_id == INFORES_DRUGCENTRAL.infores_id:
            drugcentral_in_source = True
        if retrieval_source.resource_id == INFORES_CHEMBL.infores_id:
            chembl_in_source = True

    if chembl_in_source is True:
        phase_enum = None
        for attribute in attributes:
            if attribute.attribute_type_id == BIOLINK_SLOT_MAX_RESEARCH_PHASE:
                phase_enum = attribute.value
                break
        if phase_enum == BL_MAX_RESEARCH_PHASE_ENUM_PHASE_4:
            primary_ks = INFORES_SPOKE
            predicate = BIOLINK_ASSOCIATION_TREATS
        elif phase_enum == BL_MAX_RESEARCH_PHASE_ENUM_PC_RESEARCH_PHASE:
            primary_ks = INFORES_CHEMBL
            predicate = BIOLINK_ASSOCIATION_IN_PRECLINICAL_TRIALS_FOR
        else:
            primary_ks = INFORES_CHEMBL
            predicate = BIOLINK_ASSOCIATION_IN_CLINICAL_TRIALS_FOR

    elif drugcentral_in_source is True and chembl_in_source is False:
        primary_ks = INFORES_DRUGCENTRAL
        predicate = BIOLINK_ASSOCIATION_TREATS

    else:
        raise ValueError(
            'Found a "treats" edge from a source other than Chembl or '
            'DrugCentral, which is unexpected and not configured',
        )

    updated_retrieval_sources = deepcopy(
        TREATS_LOOKUP_RETRIEVAL_SOURCE_MAP[primary_ks.infores_id],
    )
    return predicate, kl_at_attrs, updated_retrieval_sources


def evaluate_kl_at_for_lookup_query(
    predicate: str,
    attributes: list[Attribute],
    retrieval_sources: list[RetrievalSource],
) -> tuple[str, list[Attribute], list[RetrievalSource]]:
    """Returns an updated predicate and attribute list with knowledge
    level and agent type, if configured
    """
    if predicate == BIOLINK_ASSOCIATION_TREATS:
        predicate, new_attrs, sources = _evaluate_treats_lookup(
            attributes,
            retrieval_sources,
        )
    else:
        sources = retrieval_sources
        new_attrs = _get_default_kl_at_attrs(predicate, retrieval_sources)
    attrs = deepcopy(attributes)
    attrs.extend(new_attrs)
    return predicate, attrs, sources


def evaluate_kl_at_for_inferred_query(
    predicate: str,
    attributes: list[Attribute],
    retrieval_sources: list[RetrievalSource],
):
    return predicate, attributes, retrieval_sources


def get_predicate_and_qualifiers(edge_type: str) -> tuple[str, list[dict[str, str]]]:
    """Returns the predicate and a list of qualifiers based on the
    edge type alone
    """
    biolink_map_info = SPOKE_BIOLINK_EDGE_MAPPINGS.get(edge_type)
    if not biolink_map_info:
        predicate = BIOLINK_ASSOCIATION_RELATED_TO
        qualifiers = None
    else:
        qualifiers = biolink_map_info.get(QUALIFIERS)
        if qualifiers:
            qualifiers = get_edge_qualifiers(qualifiers)
        predicate = biolink_map_info[BIOLINK_ASSOCIATION_TYPE]
    return predicate, qualifiers


def resolve_epc_kl_at(
    edge_type: str,
    attributes: list[Attribute],
    provenance_sources: list[RetrievalSource],
    query_type: str,
) -> tuple[str, list[Attribute], list[RetrievalSource], list[dict[str, str]]]:
    """Returns predicate, attributes, provenance sources, and qualifiers
    as appropriate to accommodate Translator requirements.

    NOTE: There is some pretty complicated logic called as part of this
    function to handle the equally complicated requirements on the
    Translator side. Side effects can include a nearly full mutation of
    the provenance-retrieval trail, or as noted above, an entirely
    different predicate
    """
    # get predicate based on the edge type alone
    predicate, qualifiers = get_predicate_and_qualifiers(edge_type)

    # get agent type and knowledge level, the evaluation of which
    # may result in a new predicate and/or provenance-retrieval
    if query_type == KNOWLEDGE_TYPE_LOOKUP:
        updated_predicate, attrs, sources = evaluate_kl_at_for_lookup_query(
            predicate,
            attributes,
            provenance_sources,
        )
    elif query_type == KNOWLEDGE_TYPE_INFERRED:
        updated_predicate, attrs, sources = evaluate_kl_at_for_inferred_query()
        return updated_predicate, attributes, provenance_sources
    else:
        raise ValueError('Unsupported knowledge type=%s' % query_type)

    # now deal with sources
    if not sources:
        sources = [make_default_retrieval_sources(edge_type)]
    primary_sources = [s for s in sources if s.resource_role == BL_ATTR_PRIMARY_KNOWLEDGE_SOURCE]
    if len(primary_sources) > 1:
        sources = choose_primary_source(sources, edge_type)
    sources.extend(get_internal_retrieval_sources(sources))

    return updated_predicate, attrs, sources, qualifiers


# attributes
SPOKE_GRAPH_TYPE_EDGE = 'edge'
SPOKE_GRAPH_TYPE_NODE = 'node'
ATTRIBUTE_MAPS = {
    SPOKE_GRAPH_TYPE_EDGE: SPOKE_BIOLINK_EDGE_ATTRIBUTE_MAPPINGS,
    SPOKE_GRAPH_TYPE_NODE: SPOKE_BIOLINK_NODE_ATTRIBUTE_MAPPINGS,
}

# what follows is (hopefully) temporary handling of "special" attributes,
# e.g. max phase transformation to biolink's highest fda approval enums
SPECIAL_ATTRIBUTE_HANDLERS = {}


def register_special_attribute_handler(attribute_name):
    def wrapper(f):
        SPECIAL_ATTRIBUTE_HANDLERS[attribute_name] = f
        return f
    return wrapper


# max phase for nodes
@register_special_attribute_handler(BIOLINK_SLOT_HIGHEST_FDA_APPROVAL)
def _map_max_phase_to_fda_approval(property_value):
    return MAX_PHASE_FDA_APPROVAL_MAP[property_value]


# phase for edges
@register_special_attribute_handler(BIOLINK_SLOT_MAX_RESEARCH_PHASE)
def _map_max_phase_to_fda_approval(property_value):
    return PHASE_BL_CT_PHASE_ENUM_MAP[property_value]


def _transform_special_attributes(slot_type, property_value):
    """Returns a transformed property name and value if biolink
    compliance requires it.

    Parameters
    ----------
    slot_type (str): the name of the property (biolink slot)
    property_value (str, list(str), int, float): the value of the property

    Returns
    -------
    property_value (str, list(str), int, float): the updated value, if necessary
    """
    attr_transformer = SPECIAL_ATTRIBUTE_HANDLERS.get(slot_type)
    if attr_transformer:
        return attr_transformer(property_value)
    return property_value


def _make_result_attribute(
    property_type,
    property_value,
    edge_or_node,
    spoke_object_type,
):
    """Returns a TRAPI-spec attribute for a result node or edge

    Parameters
    ----------
    property_type: the neo4j-SPOKE property type
    property_value: the value of the property
    edge_or_node: string 'edge' or 'node' specifiying the type of
        graph object that is described by this attributee
    spoke_object_type: the neo4j node label or edge type from SPOKE

    Returns
    -------
    models.Attribute or None
    """
    if edge_or_node not in ATTRIBUTE_MAPS:
        raise ValueError(
            f'Got {edge_or_node=} but it must be one of "edge" or "node"',
        )

    if property_type in KNOWN_UNMAPPED_ATTRS:
        return

    if property_type in SPOKE_PUBLICATION_FIELDS:
        return make_publications_attribute(property_type, property_value)

    object_properties = ATTRIBUTE_MAPS[edge_or_node].get(spoke_object_type)
    if not object_properties:
        _logger.warning(
            f'Could not find any properties in the attribute map for {spoke_object_type=}',
        )
        return

    attribute_mapping = object_properties.get(property_type)
    if not attribute_mapping:
        _logger.warning(
            f'Could not find an attribute mapping for {spoke_object_type=} and {property_type=}',
        )
        return
    attribute_type_id = attribute_mapping.biolink_type
    property_value = _transform_special_attributes(attribute_type_id, property_value)

    attribute = Attribute(
        attribute_type_id=attribute_type_id,
        original_attribute_name=property_type,
        value=property_value,
    )
    if attribute_mapping.attribute_source:  # temporary until node mappings are done
        attribute.attribute_source = attribute_mapping.attribute_source

    if attribute_mapping.attributes:
        attribute.attributes = attribute_mapping.attributes
    return attribute


def make_result_edge(
    n4j_object: neo4j.graph.Relationship,
    query_type: str,
):
    """Instantiates a reasoner-standard Edge to return as part of a
    KnowledgeGraph result

    Parameters
    ----------
    n4j_object (abc.<neo4j edge type>): a `relationship` object returned
        from a neo4j.bolt.driver.session Cypher query

    Returns
    -------
    result_edge (models.Edge): reasoner-standard Edge object for
        inclusion as a part of a KnowledgeGraph result
    """
    edge_type = n4j_object.type

    edge_attributes = []
    provenance_retrieval_sources = []
    for k, v in n4j_object.items():
        if k == SPOKE_PROPERTY_NATIVE_SPOKE:
            continue
        if k in SPOKE_PROVENANCE_FIELDS:
            retrieval_sources = make_retrieval_sources(k, v)
            provenance_retrieval_sources.extend(retrieval_sources)
            continue
        edge_attribute = _make_result_attribute(k, v, SPOKE_GRAPH_TYPE_EDGE, edge_type)
        if edge_attribute:
            if isinstance(edge_attribute, list):
                edge_attributes.extend(edge_attribute)
            else:
                edge_attributes.append(edge_attribute)

    predicate, attrs, sources, qualifiers = resolve_epc_kl_at(
        edge_type,
        edge_attributes,
        provenance_retrieval_sources,
        query_type,
    )

    result_edge = Edge(
        attributes=attrs,
        object=n4j_object.end_node['identifier'],
        predicate=predicate,
        qualifiers=qualifiers,
        sources=sources,
        subject=n4j_object.start_node['identifier'],
    )

    return result_edge


def make_result_node(n4j_object: neo4j.graph.Node):
    """Instantiates a reasoner-standard Node to return as part of a
    KnowledgeGraph result

    Parameters
    ----------
    n4j_object (neo4j.graph.Node): a `Node` object returned from a
        neo4j.bolt.driver.session Cypher query

    Returns
    -------
    result_node (models.Node): a reasoner-standard `Edge` object for
        inclusion as part of a KnowledgeGraph result
    """
    name = n4j_object.get('pref_name')
    if not name:
        name = n4j_object.get('name')
    spoke_curie = n4j_object['identifier']

    spoke_node_labels = list(n4j_object.labels)
    result_node_categories = [
        SPOKE_BIOLINK_NODE_MAPPINGS[label]
        for label
        in spoke_node_labels
    ]

    node_source = None
    result_node_attributes = []
    for k, v in n4j_object.items():
        if k == SPOKE_PROPERTY_NATIVE_SPOKE:
            continue
        if k == SPOKE_NODE_PROPERTY_SOURCE:
            node_source = v
        node_attribute = _make_result_attribute(
            k, v, SPOKE_GRAPH_TYPE_NODE, spoke_node_labels[0],
        )
        if node_attribute:
            result_node_attributes.append(node_attribute)

    result_node = Node(
        name=name,
        categories=result_node_categories,
        attributes=result_node_attributes,
    )

    # set up downstream searches
    # for PSEV retrieval
    # TODO: add this elsewhere -> self.result_nodes_spoke_identifiers.add(spoke_curie)
    # for normalization
    search_node = SearchNode(result_node.categories[0], spoke_curie, node_source)
    return result_node, search_node


def normalize(
    nodes_to_normalize: list[SearchNode],
    knowledge_graph: KnowledgeGraph,
    results: list[Result],
) -> tuple[KnowledgeGraph, list[Result]]:
    # search the node normalizer for nodes collected in result creation
    node_search_results = normalize_spoke_nodes_for_translator(nodes_to_normalize)
    for spoke_curie, normalized_curie in node_search_results.items():
        knowledge_graph['nodes'][normalized_curie] = knowledge_graph['nodes'].pop(spoke_curie)

    for edge in knowledge_graph['edges'].values():
        setattr(edge, 'object', node_search_results[edge.object])
        setattr(edge, 'subject', node_search_results[edge.subject])

    new_results = []
    for result in results:
        new_node_bindings = {}
        for qnode, node in result.node_bindings.items():
            normalized_node_id = node_search_results[node.id]
            if node.query_id == normalized_node_id:
                node.query_id = None
            new_node_bindings[qnode] = [NodeBinding(
                id=normalized_node_id,
                query_id=node.query_id,
                attributes=[],
            )]
        new_results.append(Result(new_node_bindings, result.analyses))

    return knowledge_graph, new_results
