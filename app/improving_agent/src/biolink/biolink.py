from functools import cache

from bmt.toolkit import Toolkit

from .spoke_biolink_constants import (
    BIOLINK_ASSOCIATION_RELATED_TO,
    BIOLINK_ENTITY_NAMED_THING,
    BIOLINK_SPOKE_EDGE_MAPPINGS,
    BIOLINK_SPOKE_NODE_MAPPINGS,
)

BMT = Toolkit('https://raw.githubusercontent.com/biolink/biolink-model/615629a4e3ad198b68c3ef08c4e8935816c7deb3/biolink-model.yaml')  # NOQA biolink 2.1

EDGE = 'edge'
NODE = 'node'

BIOLINK_SPOKE_MAPPINGS = {
    EDGE: BIOLINK_SPOKE_EDGE_MAPPINGS,
    NODE: BIOLINK_SPOKE_NODE_MAPPINGS
}

BIOLINK_MODEL_ELEMENT_URI_MAPPINGS = {
    EDGE: 'slot_uri',
    NODE: 'class_uri'
}


@cache
def _get_entity_descendents(entity, entity_type):
    mappings = BIOLINK_SPOKE_MAPPINGS.get(entity_type)
    if mappings is None:
        raise ValueError(
            f'`entity_type` must be one of {list(BIOLINK_SPOKE_MAPPINGS.keys())}, got {entity_type=}'
        )
    uri_attr = BIOLINK_MODEL_ELEMENT_URI_MAPPINGS[entity_type]

    _supported_descendants = set()
    search_entities = BMT.get_descendants(entity)
    for descendant in search_entities:
        biolink_element = BMT.get_element(descendant)
        element_uri = getattr(biolink_element, uri_attr)
        if element_uri in mappings:
            _supported_descendants.add(element_uri)
    return _supported_descendants


def _check_for_wildcard(entities, entity_type):
    if entity_type == NODE:
        if BIOLINK_ENTITY_NAMED_THING in entities:
            return BIOLINK_ENTITY_NAMED_THING
    else:
        if BIOLINK_ASSOCIATION_RELATED_TO in entities:
            return BIOLINK_ASSOCIATION_RELATED_TO


def get_supported_biolink_descendants(entities, entity_type):
    """Returns a set of str biolink class URIs that are supported for
    lookup in SPOKE
    """
    wildcard = _check_for_wildcard(entities, entity_type)
    if wildcard:
        return set([wildcard])

    supported_descendants = set()
    for entity in entities:
        valid_entity_descendants = _get_entity_descendents(entity, entity_type)
        supported_descendants = supported_descendants.union(valid_entity_descendants)
    return supported_descendants


def get_supported_inverse_predicates(entities):
    inverses = set()
    for entity in entities:
        if inverse := BMT.get_element(entity).inverse:
            inverses.add(inverse)

    return get_supported_biolink_descendants(inverses, EDGE)
