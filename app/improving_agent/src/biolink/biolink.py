from functools import cache

from bmt.toolkit import Toolkit

from improving_agent.src.config import app_config

from .spoke_biolink_constants import (
    BIOLINK_ASSOCIATION_RELATED_TO,
    BIOLINK_ENTITY_NAMED_THING,
    BIOLINK_SPOKE_EDGE_MAPPINGS,
    BIOLINK_SPOKE_NODE_MAPPINGS,
)

BMT = Toolkit(f'https://raw.githubusercontent.com/biolink/biolink-model/v{app_config.BIOLINK_VERSION}/biolink-model.yaml')

EDGE = 'edge'
NODE = 'node'

BIOLINK_SPOKE_MAPPINGS = {
    EDGE: BIOLINK_SPOKE_EDGE_MAPPINGS,
    NODE: BIOLINK_SPOKE_NODE_MAPPINGS
}


def _format_uri(element_name, entity_type):
    if entity_type == NODE:
        return f'biolink:{element_name.title().replace(" ", "")}'
    return f'biolink:{element_name.replace(" ", "_")}'


@cache
def _get_entity_descendents(entity, entity_type, mapped_only=True):
    mappings = BIOLINK_SPOKE_MAPPINGS.get(entity_type)
    if mappings is None:
        raise ValueError(
            f'`entity_type` must be one of {list(BIOLINK_SPOKE_MAPPINGS.keys())}, got {entity_type=}'
        )

    _supported_descendants = set()
    search_entities = BMT.get_descendants(entity)
    for descendant in search_entities:
        biolink_element = BMT.get_element(descendant)
        element_name = _format_uri(biolink_element.name, entity_type)
        if mapped_only is True:
            if element_name in mappings:
                _supported_descendants.add(element_name)
            continue
        _supported_descendants.add(element_name)

    return _supported_descendants


def _check_for_wildcard(entities, entity_type):
    if entity_type == NODE:
        if BIOLINK_ENTITY_NAMED_THING in entities:
            return BIOLINK_ENTITY_NAMED_THING
    else:
        if BIOLINK_ASSOCIATION_RELATED_TO in entities:
            return BIOLINK_ASSOCIATION_RELATED_TO


def get_supported_biolink_descendants(
    entities,
    entity_type,
    mapped_only=True,
):
    """Returns a set of str biolink class URIs that are supported for
    lookup in SPOKE
    """
    wildcard = _check_for_wildcard(entities, entity_type)
    if wildcard:
        return set([wildcard])

    supported_descendants = set()
    for entity in entities:
        valid_entity_descendants = _get_entity_descendents(
            entity,
            entity_type,
            mapped_only,
        )
        supported_descendants = supported_descendants.union(valid_entity_descendants)
    return supported_descendants


def get_supported_inverse_predicates(entities):
    inverses = set()
    for entity in entities:
        if inverse := BMT.get_element(entity).inverse:
            inverses.add(inverse)

    return get_supported_biolink_descendants(inverses, EDGE)
