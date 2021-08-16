"""This module provides functions for creating attributes that relate
the provenance of the data contained within SPOKE. It relies on many
constants defined in the spoke_biolink_constants module
"""

import logging
from typing import Dict, List, Union

from improving_agent import models
from improving_agent.src.biolink.spoke_biolink_constants import (
    BIOLINK_ENTITY_ARTICLE,
    BIOLINK_ENTITY_INFORMATION_RESOURCE,
    BL_ATTR_PRIMARY_KNOWLEDGE_SOURCE,
    INFORES_IMPROVING_AGENT,
    INFORES_SPOKE,
    SPOKE_EDGE_DEFAULT_SOURCE,
    SPOKE_PROPERTY_PMID_LIST,
    SPOKE_PROPERTY_PREPRINT_LIST,
    SPOKE_PROPERTY_PUBMED,
    SPOKE_PROPERTY_SOURCE,
    SPOKE_PROPERTY_SOURCES,
    SPOKE_SOURCE_INFORES_MAP
)

logger = logging.getLogger(__name__)

SPOKE_PROVENANCE_FIELDS = [
    SPOKE_PROPERTY_PMID_LIST,
    SPOKE_PROPERTY_PREPRINT_LIST,
    SPOKE_PROPERTY_PUBMED,
    SPOKE_PROPERTY_SOURCE,
    SPOKE_PROPERTY_SOURCES
]

IMPROVING_AGENT_PROVENANCE_ATTR = models.Attribute(
    attribute_source=INFORES_IMPROVING_AGENT.infores_id,
    attribute_type_id=INFORES_IMPROVING_AGENT.source_type,
    value_type_id=BIOLINK_ENTITY_INFORMATION_RESOURCE,
    value=INFORES_IMPROVING_AGENT.infores_id
)
SPOKE_KP_PROVENANCE_ATTR = models.Attribute(
    attribute_source=INFORES_SPOKE.infores_id,
    attribute_type_id=INFORES_SPOKE.source_type,
    value_type_id=BIOLINK_ENTITY_INFORMATION_RESOURCE,
    value=INFORES_SPOKE.infores_id
)


def _make_source_provenance_attribute(source_or_sources):
    # each edge needs at least two attributes
    # 1. the src attribute with a tag that spoke is the attribute_source
    # 2. the aggregator attribute with a tag that spoke is the attribute_source and the informationation resource
    # improving agentshould have a third tag that has itself as the info resource and attribute_source

    # attribute_source: 	infores:rtx-kg2
    # attribute_type_id: 	biolink:aggregator_knowledge_source
    # value_type_id: 	biolink:InformationResource
    # value: 	infores:semmeddb
    source_attributes = []
    if not isinstance(source_or_sources, list):
        source_or_sources = [source_or_sources]

    for source in source_or_sources:
        source_infores = SPOKE_SOURCE_INFORES_MAP.get(source)
        if not source_infores:
            logger.warning(f'Could not find infores for {source=}')
            continue
        attribute = models.Attribute(
            attribute_source=INFORES_SPOKE.infores_id,
            attribute_type_id=source_infores.source_type,
            original_attribute_name='source',
            value_type_id=BIOLINK_ENTITY_INFORMATION_RESOURCE,
            value=source_infores.infores_id
        )
        source_attributes.append(attribute)

    return source_attributes


def _make_article_provenance_attribute(
    articles,
    attribute_name,
    value_prefix='',
    url_prefix=''
):
    source_attributes = []
    if isinstance(articles, list):
        articles = [articles]

    for article in articles:
        attribute = models.Attribute(
            attribute_source=INFORES_SPOKE.infores_id,
            attribute_type_id=BL_ATTR_PRIMARY_KNOWLEDGE_SOURCE,
            original_attribute_name=attribute_name,
            value_type_id=BIOLINK_ENTITY_ARTICLE,
            value=f'{value_prefix}{article}',
            value_url=f'{url_prefix}{article}' if url_prefix else article
        )
        source_attributes.append(attribute)

    return source_attributes


def make_provenance_attributes(
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
        return _make_source_provenance_attribute(field_value)

    if field_name in (SPOKE_PROPERTY_PUBMED, SPOKE_PROPERTY_PMID_LIST):
        return _make_article_provenance_attribute(
            field_value, field_name, 'pmid:', 'https://pubmed.ncbi.nlm.nih.gov/'
        )

    if field_name == SPOKE_PROPERTY_PREPRINT_LIST:
        return _make_article_provenance_attribute(field_value, field_name)

    return []


def make_default_provenance_attribute(spoke_type):
    source_infores = SPOKE_EDGE_DEFAULT_SOURCE[spoke_type]
    return models.Attribute(
        attribute_source=INFORES_SPOKE.infores_id,
        attribute_type_id=source_infores.source_type,
        value_type_id=BIOLINK_ENTITY_INFORMATION_RESOURCE,
        value=source_infores.infores_id
    )
