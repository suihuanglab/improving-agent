from collections import namedtuple

from requests.exceptions import HTTPError

from improving_agent.models.attribute import Attribute
from improving_agent.src.kps.cohd_client import COHD_CLIENT
from improving_agent.util import get_evidara_logger

logger = get_evidara_logger(__name__)

COHD_NODES_TO_QUERY = ['biolink:Disease', 'biolink:ChemicalSubstance']

TripletIds = namedtuple('TripletIds', ['node1_id', 'edge_id', 'node2_id'])


def _get_cohd_queryable_triplet_identifiers(knowledge_graph):
    """Returns list of triplets identifiers that can be annotated by COHD

    Parameters
    ----------
    knowledge_map (BasicQuery.knowledge_graph)
    """
    edges_to_search = []
    for kedge_id, kedge in knowledge_graph['edges'].items():
        if (any(category in COHD_NODES_TO_QUERY for category in knowledge_graph['nodes'][kedge.subject].category)
        and any(category in COHD_NODES_TO_QUERY for category in knowledge_graph['nodes'][kedge.object].category)):  # NOQA: E128
            edges_to_search.append(TripletIds(kedge.subject, kedge_id, kedge.object))

    return edges_to_search


def _make_cohd_edge_attributes(clinical_frequencies={}, chi_square_results={}):
    cohd_edge_attributes = []
    for k, v in clinical_frequencies.items():
        cohd_edge_attributes.append(Attribute(type=f"cohd_paired_concept_freq_{k}", value=v, source='Columbia Open Health Data'))

    for k, v in chi_square_results.items():
        cohd_edge_attributes.append(Attribute(type=f"cohd_chi_square_association_{k}", value=v, source='Columbia Open Health Data'))

    return cohd_edge_attributes


def _update_kedge_with_cohd_annotation(triplet_identifiers, knowledge_graph):
    concept_1 = COHD_CLIENT.get_recommended_omop_concept(triplet_identifiers.node1_id)
    concept_2 = COHD_CLIENT.get_recommended_omop_concept(triplet_identifiers.node2_id)

    if not concept_1 or not concept_2:
        return

    clinical_frequencies = COHD_CLIENT.get_paired_concept_frequencies(f"{concept_1},{concept_2}")
    chi_square_results = COHD_CLIENT.get_chi_square_associations(concept_1, concept_id_2=concept_2)
    cohd_annotations = _make_cohd_edge_attributes(clinical_frequencies, chi_square_results)

    edge_attributes = knowledge_graph['edges'][triplet_identifiers.edge_id].attributes + cohd_annotations
    setattr(knowledge_graph['edges'][triplet_identifiers.edge_id], 'attributes', edge_attributes)


def annotate_edges_with_cohd(knowledge_graph):
    # check for appropriate query
    triplet_identifiers_list = _get_cohd_queryable_triplet_identifiers(knowledge_graph)

    if not triplet_identifiers_list:
        logger.info("No edges appropriate for COHD search")
        return knowledge_graph['edges']

    for triplet_identifiers in triplet_identifiers_list:
        try:
            _update_kedge_with_cohd_annotation(triplet_identifiers, knowledge_graph)
        except HTTPError as e:
            logger.exception(f"Failed to get results from COHD with {e}")

    return knowledge_graph['edges']
