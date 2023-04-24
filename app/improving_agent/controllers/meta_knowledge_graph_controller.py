from functools import cache

import connexion
import six

from improving_agent.models.meta_knowledge_graph import MetaKnowledgeGraph  # noqa: E501
from improving_agent.models.meta_attribute import MetaAttribute
from improving_agent.models.meta_edge import MetaEdge
from improving_agent.models.meta_node import MetaNode
from improving_agent.models.meta_qualifier import MetaQualifier
from improving_agent.src.biolink.spoke_biolink_constants import (
    BIOLINK_ASSOCIATION_KNOWLEDGE_TYPE_MAP,
    BIOLINK_ENTITY_NAMED_THING,
    BIOLINK_SPOKE_NODE_MAPPINGS,
    SPOKE_BIOLINK_EDGE_ATTRIBUTE_MAPPINGS,
    SPOKE_BIOLINK_EDGE_MAPPINGS,
    SPOKE_BIOLINK_NODE_ATTRIBUTE_MAPPINGS,
    PREDICATES,
    QUALIFIERS,
)
from improving_agent.src.normalization.sri_node_normalizer import (
    SRI_NN_CURIE_PREFIX,
    SRI_NODE_NORMALIZER
)


def _get_supported_prefixes(sri_prefixes, node_type, local_prefixes):
    sri_node_prefixes = sri_prefixes.get(node_type)
    if not sri_node_prefixes:
        return local_prefixes
    return list(sri_node_prefixes[SRI_NN_CURIE_PREFIX].keys())


def _does_attr_already_exist(existing_attributes, new_attribute):
    for existing_attr in existing_attributes:
        if existing_attr == new_attribute:
            return True

    return False


def _get_existing_meta_qualifier(meta_qualifiers, meta_qualifier):
    for index, mq in enumerate(meta_qualifiers):
        if mq.qualifier_type_id == meta_qualifier.qualifier_type_id:
            return index, mq

    return None, None


def _make_metanode(sri_curie_prefixes, node, mapping):
    prefixes = _get_supported_prefixes(sri_curie_prefixes, node, mapping.prefixes)

    # get node info from our mapping dict and unpack the attrs
    if isinstance(mapping.spoke_label, str):
        spoke_labels = [mapping.spoke_label]
    else:
        spoke_labels = mapping.spoke_label

    attributes = []
    for spoke_label in spoke_labels:
        label_attrs = SPOKE_BIOLINK_NODE_ATTRIBUTE_MAPPINGS.get(spoke_label)
        if not label_attrs:
            continue
        for label_attr, attr_mapping in label_attrs.items():
            meta_attr = MetaAttribute(
                attribute_type_id=attr_mapping.biolink_type,
                # attribute_source=attr_mapping.attribute_source,  TODO: uncomment when ready
                original_attribute_names=[label_attr]
            )
            if _does_attr_already_exist(attributes, meta_attr):
                continue
            attributes.append(meta_attr)
    return MetaNode(id_prefixes=prefixes, attributes=attributes)


def _get_edge_meta_attributes(spoke_edges):
    attributes = []
    for spoke_edge in spoke_edges:
        edge_attrs = SPOKE_BIOLINK_EDGE_ATTRIBUTE_MAPPINGS.get(spoke_edge)
        if not edge_attrs:
            continue
        for edge_attr, attr_mapping in edge_attrs.items():
            meta_attr = MetaAttribute(
                attribute_type_id=attr_mapping.biolink_type,
                attribute_source=attr_mapping.attribute_source,
                original_attribute_names=[edge_attr],
            )
            if _does_attr_already_exist(attributes, meta_attr):
                continue
            attributes.append(meta_attr)
    return attributes


def _get_edge_meta_qualifiers(spoke_edges):
    meta_qualifiers = []
    for spoke_edge in spoke_edges:
        edge_config = SPOKE_BIOLINK_EDGE_MAPPINGS.get(spoke_edge)
        if not edge_config:
            continue
        qualifiers = edge_config.get(QUALIFIERS)
        if not qualifiers:
            continue
        for qualifier_type, qualifier_value in qualifiers.items():
            meta_qualifier = MetaQualifier(
                qualifier_type_id=qualifier_type,
                applicable_values=[qualifier_value],
            )
            index, existing_mq = _get_existing_meta_qualifier(meta_qualifiers, meta_qualifier)
            if existing_mq:
                for applicable_value in meta_qualifier.applicable_values:
                    if applicable_value not in existing_mq.applicable_values:
                        existing_mq.applicable_values.append(applicable_value)
                meta_qualifiers[index] = existing_mq
            else:
                meta_qualifiers.append(meta_qualifier)

    return meta_qualifiers


@cache
def _make_meta_kg():
    nodes = {}
    sri_curie_prefixes = SRI_NODE_NORMALIZER.get_curie_prefixes([])
    for node, mapping in BIOLINK_SPOKE_NODE_MAPPINGS.items():
        if node == BIOLINK_ENTITY_NAMED_THING:
            continue
        nodes[node] = _make_metanode(sri_curie_prefixes, node, mapping)

    edges = []
    for biolink_subject, biolink_objects in PREDICATES.items():
        for biolink_object, biolink_predicate_map in biolink_objects.items():
            for predicate, spoke_edges in biolink_predicate_map.items():
                attributes = _get_edge_meta_attributes(spoke_edges)
                knowledge_types = BIOLINK_ASSOCIATION_KNOWLEDGE_TYPE_MAP.get(predicate)
                qualifiers = _get_edge_meta_qualifiers(spoke_edges)
                meta_edge = MetaEdge(
                    subject=biolink_subject,
                    object=biolink_object,
                    predicate=predicate,
                    attributes=attributes,
                    knowledge_types=knowledge_types,
                )
                if qualifiers:
                    meta_edge.qualifiers = qualifiers
                edges.append(meta_edge)

    return MetaKnowledgeGraph(nodes=nodes, edges=edges)


def meta_knowledge_graph_get():  # noqa: E501
    """Meta knowledge graph representation of this TRAPI web service.

     # noqa: E501


    :rtype: MetaKnowledgeGraph
    """
    return _make_meta_kg()
