"""This module provides functions for creating attributes that relate
the provenance of the data contained within SPOKE. It relies on many
constants defined in the spoke_biolink_constants module
"""

import logging
from typing import Dict, List, Union

from improving_agent import models
from improving_agent.src.biolink.spoke_biolink_constants import (
    BL_ATTR_AGGREGATOR_KNOWLEDGE_SOURCE,
    BL_ATTR_PRIMARY_KNOWLEDGE_SOURCE,
    BIOLINK_ENTITY_ARTICLE,
    BIOLINK_SLOT_PUBLICATIONS,
    INFORES_SPOKE,
    INFORES_BINDINGDB,
    INFORES_DISEASES,
    INFORES_DRUGCENTRAL,
    INFORES_GWAS,
    INFORES_OMIM,
    SPOKE_EDGE_DEFAULT_SOURCE,
    SPOKE_EDGE_TYPE_ASSOCIATES_DaG,
    SPOKE_EDGE_TYPE_BINDS_CbP,
    SPOKE_PROPERTY_PMID_LIST,
    SPOKE_PROPERTY_PREPRINT_LIST,
    SPOKE_PROPERTY_PUBMED,
    SPOKE_PROPERTY_SOURCE,
    SPOKE_PROPERTY_SOURCES,
    SPOKE_SOURCE_INFORES_MAP,
)

logger = logging.getLogger(__name__)

SPOKE_PROVENANCE_FIELDS = [
    SPOKE_PROPERTY_SOURCE,
    SPOKE_PROPERTY_SOURCES
]
SPOKE_PUBLICATION_FIELDS = [
    SPOKE_PROPERTY_PMID_LIST,
    SPOKE_PROPERTY_PREPRINT_LIST,
    SPOKE_PROPERTY_PUBMED,
]

PREFERRED_ORDER_MULTI_SOURCE = {
    # NCATS requires "one and only one" primary source for edges,
    # however, some of SPOKE's edges are merged from multiple sources,
    # thus have multiple primary sources. When this is the case, we use
    # the priority map below to set one edge as primary to the others
    SPOKE_EDGE_TYPE_ASSOCIATES_DaG: {
        INFORES_DISEASES.infores_id: 2,
        INFORES_GWAS.infores_id: 1,
        INFORES_OMIM.infores_id: 3,
    },
    SPOKE_EDGE_TYPE_BINDS_CbP: {
        INFORES_BINDINGDB.infores_id: 1,
        INFORES_DRUGCENTRAL.infores_id: 2,
    }
}


def make_internal_retrieval_source(
    retrieval_sources: list[str],
    infores_id: str
) -> models.RetrievalSource:
    upstream_sources = set()
    for retrieval_source in retrieval_sources:
        upstream_sources.add(retrieval_source.resource_id)

    resource_role = BL_ATTR_AGGREGATOR_KNOWLEDGE_SOURCE if upstream_sources else BL_ATTR_PRIMARY_KNOWLEDGE_SOURCE

    return models.RetrievalSource(
        resource_id=infores_id,
        resource_role=resource_role,
        upstream_resource_ids=list(upstream_sources)
    )


def _make_retrieval_source(source_or_sources):
    retrieval_sources = []
    if not isinstance(source_or_sources, list):
        source_or_sources = [source_or_sources]

    for source in source_or_sources:
        source_infores = SPOKE_SOURCE_INFORES_MAP.get(source)
        if not source_infores:
            logger.warning(f'Could not find infores for {source=}')
            continue
        retrieval_source = models.RetrievalSource(
            resource_id=source_infores.infores_id,
            resource_role=source_infores.biolink_type,
        )
        retrieval_sources.append(retrieval_source)

    return retrieval_sources


def _make_publications_attribute(
    articles,
    attribute_name,
    value_prefix='',
    url_prefix=''
):
    publication_attributes = []
    if not isinstance(articles, list):
        articles = [articles]

    for article in articles:
        pub_attr = models.Attribute(
            attribute_source=INFORES_SPOKE.infores_id,
            attribute_type_id=BIOLINK_SLOT_PUBLICATIONS,
            original_attribute_name=attribute_name,
            value_type_id=BIOLINK_ENTITY_ARTICLE,
            value=f'{value_prefix}{article}',
            value_url=f'{url_prefix}{article}' if url_prefix else article
        )
        publication_attributes.append(pub_attr)

    return publication_attributes


def make_publications_attribute(
    field_name: str, field_value: Union[str, int, List[str]]
):
    if field_name in (SPOKE_PROPERTY_PUBMED, SPOKE_PROPERTY_PMID_LIST):
        return _make_publications_attribute(
            field_value, field_name, 'pmid:', 'https://pubmed.ncbi.nlm.nih.gov/'
        )

    if field_name == SPOKE_PROPERTY_PREPRINT_LIST:
        return _make_publications_attribute(field_value, field_name)


def make_retrieval_sources(
    field_name: str, field_value: Union[str, int, List[str]]
) -> List[Dict[str, Union[str, int]]]:
    """Returns a list of source-provenance attributes to be attached
    to the result node or edge

    field_name (str):
        the name of the property that contains the source provenance
    field_value (str):
        the value of the source provenance
    """
    if field_name in (SPOKE_PROPERTY_SOURCE, SPOKE_PROPERTY_SOURCES):
        return _make_retrieval_source(field_value)
    return []


def make_default_retrieval_sources(spoke_type):
    source_infores = SPOKE_EDGE_DEFAULT_SOURCE[spoke_type]
    return models.RetrievalSource(
        resource_id=source_infores.infores_id,
        resource_role=source_infores.biolink_type,
    )


def choose_primary_source(
    retrieval_sources: List[models.RetrievalSource],
    edge_type: str,
):
    """Returns a mutated list of sources with one source being deemed
    "primary" and others being categorized as "aggregator"
    Context: NCATS requires one and only one primary source for all
    edges, but some edges in SPOKE are merged from multiple sources.
    This hack allows compliance with NCATS
    """
    priority_ranks = PREFERRED_ORDER_MULTI_SOURCE.get(edge_type)
    if priority_ranks is None:
        # We haven't configured a mapping for this, so just pick the
        # first source
        retrieval_sources[0].resource_role = BL_ATTR_PRIMARY_KNOWLEDGE_SOURCE
        for source in retrieval_sources[1:]:
            source.resource_role = BL_ATTR_AGGREGATOR_KNOWLEDGE_SOURCE
        return retrieval_sources

    element_ranks = []
    for i, attr in enumerate(retrieval_sources):
        priority = priority_ranks.get(source.resource_id)
        if not priority:
            # we haven't configured this properly, so just go element-wise
            element_ranks.append(i)
            continue
        element_ranks.append(priority)

    min_priority = min(element_ranks)
    primary_set = False
    for i, rank in enumerate(priority_ranks):
        if rank == min_priority and primary_set is False:
            retrieval_sources[i].resource_role = BL_ATTR_PRIMARY_KNOWLEDGE_SOURCE
            primary_set = True
        else:
            retrieval_sources[i].resource_role = BL_ATTR_AGGREGATOR_KNOWLEDGE_SOURCE

    return retrieval_sources
