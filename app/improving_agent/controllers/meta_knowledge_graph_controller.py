from functools import cache

import connexion
import six

from improving_agent.models.meta_knowledge_graph import MetaKnowledgeGraph  # noqa: E501
from improving_agent.models.meta_attribute import MetaAttribute
from improving_agent.models.meta_edge import MetaEdge
from improving_agent.models.meta_node import MetaNode
from improving_agent import util
from improving_agent.src.biolink.spoke_biolink_constants import (
    BIOLINK_ENTITY_NAMED_THING,
    BIOLINK_SPOKE_NODE_MAPPINGS,
    SPOKE_BIOLINK_EDGE_ATTRIBUTE_MAPPINGS,
    SPOKE_BIOLINK_NODE_ATTRIBUTE_MAPPINGS,
    PREDICATES
)
from improving_agent.src.normalization.sri_node_normalizer import (
    NODE_NORMALIZATION_CURIE_PREFIX,
    SRI_NODE_NORMALIZER
)


def _get_supported_prefixes(sri_prefixes, node_type, local_prefixes):
    sri_node_prefixes = sri_prefixes.get(node_type)
    if not sri_node_prefixes:
        return local_prefixes
    return list(sri_node_prefixes[NODE_NORMALIZATION_CURIE_PREFIX].keys())


def _does_attr_already_exist(existing_attributes, new_attribute):
    for existing_attr in existing_attributes:
        if existing_attr == new_attribute:
            return True

    return False


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
                original_attribute_names=label_attr
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
                original_attribute_names=edge_attr,
            )
            if _does_attr_already_exist(attributes, meta_attr):
                continue
            attributes.append(meta_attr)
    return attributes


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
                edges.append(MetaEdge(
                    subject=biolink_subject,
                    object=biolink_object,
                    predicate=predicate,
                    attributes=attributes
                ))

    return MetaKnowledgeGraph(nodes=nodes, edges=edges)


def meta_knowledge_graph_get():  # noqa: E501
    """Meta knowledge graph representation of this TRAPI web service.

     # noqa: E501


    :rtype: MetaKnowledgeGraph
    """
    return _make_meta_kg()
