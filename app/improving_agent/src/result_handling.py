"""This module is a WIP, with result handling features migrated here
as there is time.
"""
from copy import deepcopy
from typing import Optional

from improving_agent.models.attribute import Attribute
from improving_agent.models.retrieval_source import RetrievalSource
from improving_agent.src.biolink.spoke_biolink_constants import (
    BIOLINK_ASSOCIATION_TREATS,
    BIOLINK_ASSOCIATION_IN_CLINICAL_TRIALS_FOR,
    BIOLINK_ASSOCIATION_IN_PRECLINICAL_TRIALS_FOR,
    BIOLINK_SLOT_AGENT_TYPE,
    BIOLINK_SLOT_KNOWLEDGE_LEVEL,
    BIOLINK_SLOT_MAX_RESEARCH_PHASE,
    BL_ATTR_PRIMARY_KNOWLEDGE_SOURCE,
    BL_MAX_RESEARCH_PHASE_ENUM_NOT_PROVIDED,
    BL_MAX_RESEARCH_PHASE_ENUM_PC_RESEARCH_PHASE,
    BL_MAX_RESEARCH_PHASE_ENUM_PHASE_4,
    KNOWLEDGE_TYPE_INFERRED,
    KNOWLEDGE_TYPE_LOOKUP,
    PHASE_BL_CT_PHASE_ENUM_MAP,
    TRAPI_KNOWLEDGE_LEVEL_KNOWLEDGE_ASSERTION,
    TRAPI_AGENT_TYPE_ENUM_MANUAL_AGENT,
    Infores,
    INFORES_CHEMBL,
    INFORES_DRUGCENTRAL,
    INFORES_IMPROVING_AGENT,
    INFORES_SPOKE,
    SPOKE_EDGE_TYPE_TREATS_CtD,
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

def _get_kl_at_attrs_for_lookup() -> list[Attribute]:
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
    kl_at_attrs = _get_kl_at_attrs_for_lookup()

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
    edge_type: str,
    attributes: list[Attribute],
    retrieval_sources: list[RetrievalSource],
) -> tuple[Optional[str], Optional[list[Attribute]]]:
    """Returns an updated predicate and attribute list with knowledge
    level and agent type, if configured
    """
    if edge_type != SPOKE_EDGE_TYPE_TREATS_CtD:
        # KL and AT are not configured
        return None, attributes, retrieval_sources
    predicate, new_attrs, sources = _evaluate_treats_lookup(
        attributes,
        retrieval_sources,
    )
    attrs = deepcopy(attributes)
    attrs.extend(new_attrs)
    return predicate, attrs, sources


def evaluate_kl_at_for_inferred_query():
    pass


def resolve_epc_kl_at(
    edge_type: str,
    attributes: list[Attribute],
    provenance_sources: list[RetrievalSource],
    query_type: str,
) -> tuple[str, list[Attribute], list[RetrievalSource]]:
    """Returns an updated predicate, attributes, and provenance sources
    as appropriate to accommodate Translator requirements.

    NOTE: There is some pretty complicated logic called as part of this
    function to handle the equally complicated requirements on the
    Translator side. Side effects can include a nearly full mutation of
    the provenance-retrieval trail, or as noted above, an entirely
    different predicate
    """
    # first, get agent type and knowledge level, the evaluation of which
    # may result in a new predicate and/or provenance-retrieval
    if query_type == KNOWLEDGE_TYPE_LOOKUP:
        updated_predicate, attrs, sources = evaluate_kl_at_for_lookup_query(
            edge_type,
            attributes,
            provenance_sources,
        )
    elif query_type == KNOWLEDGE_TYPE_INFERRED:
        updated_predicate, attrs, sources = evaluate_kl_at_for_inferred_query()
        return None, attributes, provenance_sources
    else:
        raise ValueError('Unsupported knowledge type=%s' % query_type)

    # now deal with sources
    if not sources:
        sources = [make_default_retrieval_sources(edge_type)]
    primary_sources = [s for s in sources if s.resource_role==BL_ATTR_PRIMARY_KNOWLEDGE_SOURCE]
    if len(primary_sources) > 1:
        sources = choose_primary_source(sources, edge_type)
    sources.extend(get_internal_retrieval_sources(sources))

    return updated_predicate, attrs, sources
