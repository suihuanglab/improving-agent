"""This module is a WIP, with result handling features migrated here
as there is time.
"""
from copy import deepcopy
from typing import Optional

from improving_agent.models.attribute import Attribute
from improving_agent.models.retrieval_source import RetrievalSource
from improving_agent.src.biolink.spoke_biolink_constants import (
    BIOLINK_ASSOCIATION_IN_CLINICAL_TRIALS_FOR,
    BIOLINK_ASSOCIATION_IN_PRECLINICAL_TRIALS_FOR,
    BIOLINK_ASSOCIATION_RELATED_TO,
    BIOLINK_ASSOCIATION_TREATS,
    BIOLINK_ASSOCIATION_TYPE,
    BIOLINK_SLOT_AGENT_TYPE,
    BIOLINK_SLOT_KNOWLEDGE_LEVEL,
    BIOLINK_SLOT_MAX_RESEARCH_PHASE,
    BL_ATTR_PRIMARY_KNOWLEDGE_SOURCE,
    BL_MAX_RESEARCH_PHASE_ENUM_PC_RESEARCH_PHASE,
    BL_MAX_RESEARCH_PHASE_ENUM_PHASE_4,
    BL_RELATION_SOURCE_KL_AT_MAP,
    KNOWLEDGE_TYPE_INFERRED,
    KNOWLEDGE_TYPE_LOOKUP,
    QUALIFIERS,
    SPOKE_BIOLINK_EDGE_MAPPINGS,
    TRAPI_AGENT_TYPE_ENUM_MANUAL_AGENT,
    TRAPI_AGENT_TYPE_ENUM_NOT_PROVIDED,
    TRAPI_KNOWLEDGE_LEVEL_KNOWLEDGE_ASSERTION,
    TRAPI_KNOWLEDGE_LEVEL_NOT_PROVIDED,
    Infores,
    INFORES_CHEMBL,
    INFORES_DRUGCENTRAL,
    INFORES_SPOKE,
)
from improving_agent.src.provenance import (
    choose_primary_source,
    get_internal_retrieval_sources,
    make_default_retrieval_sources,
    TREATS_LOOKUP_RETRIEVAL_SOURCE_MAP,
)

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
        _make_attribute(BIOLINK_SLOT_KNOWLEDGE_LEVEL, edge_source_klat.knowledge_level, INFORES_SPOKE)
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
            'DrugCentral, which is unexpected and not configured'
        )
    
    updated_retrieval_sources = deepcopy(
        TREATS_LOOKUP_RETRIEVAL_SOURCE_MAP[primary_ks.infores_id]
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
    primary_sources = [s for s in sources if s.resource_role==BL_ATTR_PRIMARY_KNOWLEDGE_SOURCE]
    if len(primary_sources) > 1:
        sources = choose_primary_source(sources, edge_type)
    sources.extend(get_internal_retrieval_sources(sources))

    return updated_predicate, attrs, sources, qualifiers
