import pickle
from collections import defaultdict, namedtuple
from copy import deepcopy

import requests

from improving_agent.src.config import TEXT_MINER_NODE_MAP
from improving_agent.models.edge_attribute import EdgeAttribute
from improving_agent.util import get_evidara_logger

logger = get_evidara_logger(__name__)


TEXT_MINER_BASE_URL = 'https://biothings.ncats.io/text_mining_co_occurrence_kp/'
TEXT_MINER_NODES_TO_QUERY = ['biolink:ChemicalSubstance', 'biolink:Disease']
TEXT_MINER_QUERY_URL = 'query'

with open(TEXT_MINER_NODE_MAP, 'rb') as inpickle:
    TEXT_MINER_LOCAL_NODE_CACHE = pickle.load(inpickle)

Triplet = namedtuple('Triplet', ['node1', 'edge', 'node2'])
TripletIds = namedtuple('TripletIds', ['node1_id', 'edge_id', 'node2_id'])


class TextMinerClient:
    # NOTE: RELAY hacked together, refactor with a better understanding of API
    # make sure to map relation ontology properly, remove unnecessary copied
    # code
    def __init__(self):
        self.cache = {}

    def _check_cache(self, subject, obj):
        c1 = self.cache.get(f'{subject}_{obj}')
        c2 = self.cache.get(f'{obj}_{subject}')
        return c1 if c1 else c2

    def _query_text_miner(self, subject, obj):
        subject_domain = subject.split(':')[0]
        obj_domain = obj.split(':')[0]

        payload = [('q', f'object.{obj_domain}:"{obj}" AND subject.{subject_domain}:"{subject}"'), ('size', 200)]

        response = requests.get(f'{TEXT_MINER_BASE_URL}{TEXT_MINER_QUERY_URL}', payload)
        if response.status_code != 200:
            logger.warning(f"TextMiner query to {response.request.url} failed with {response.status_code} and {response.text}")
            response.raise_for_status()

        return response.json()

    def _get_text_miner_ngd(self, subject, obj):
        try:
            results = self._query_text_miner(subject, obj)
        except requests.exceptions.HTTPError:
            return

        hits = results.get('hits')
        if not hits:
            return

        top_hit = 0
        for hit in hits:
            association = hit.get('association')
            if not association:
                continue
            ngd = association.get('ngd')
            if not ngd:
                continue

            if ngd > top_hit:
                top_hit = ngd

        return top_hit if top_hit else None

    def get_max_text_miner_ngd(self, concept_1, concept_2):
        ngd1 = self._get_text_miner_ngd(concept_1, concept_2)
        ngd2 = self._get_text_miner_ngd(concept_2, concept_1)

        if not ngd1 and not ngd2:
            return

        if ngd1 and ngd2:
            return max(ngd1, ngd2)

        return ngd1 if ngd1 else ngd2

    def _get_text_miner_triplets(self, query_order):

        triplets_to_search = []

        first = iter(query_order)
        second = iter(query_order[2::2])

        for triplet in zip(first, first, second):
            if triplet[0].type in TEXT_MINER_NODES_TO_QUERY and triplet[2].type in TEXT_MINER_NODES_TO_QUERY:
                triplets_to_search.append(Triplet(triplet[0], triplet[1], triplet[2]))

        return triplets_to_search

    def _extract_triplet_ids(self, triplets, result):
        return ([
            TripletIds(
                result.knowledge_map["nodes"][triplet.node1.node_id],
                result.knowledge_map["edges"][triplet.edge.edge_id],
                result.knowledge_map["nodes"][triplet.node2.node_id]
            )
            for triplet in triplets
        ])

    def _make_text_miner_edge_attributes(self, ngd=None):
        text_miner_edge_attributes = []
        if ngd:
            text_miner_edge_attributes.append(EdgeAttribute(type="text_miner_max_ngd_for_sub_obj", value=ngd))

        return text_miner_edge_attributes

    def _make_result_with_text_miner_annotation(self, result, triplets_to_search):
        annotated_result = deepcopy(result)
        result_triplet_ids = self._extract_triplet_ids(triplets_to_search, annotated_result)

        text_miner_annotations = defaultdict(list)
        for result_triplet in result_triplet_ids:
            concept_1 = TEXT_MINER_LOCAL_NODE_CACHE.get(result_triplet.node1_id)
            concept_2 = TEXT_MINER_LOCAL_NODE_CACHE.get(result_triplet.node2_id)

            if not concept_1 or not concept_2:
                text_miner_annotations[result_triplet.node2_id].extend(self._make_text_miner_edge_attributes())
                continue

            ngd = self.get_max_text_miner_ngd(concept_1, concept_2)

            text_miner_annotations[result_triplet.edge_id].extend(
                self._make_text_miner_edge_attributes(ngd)
            )

        for edge in annotated_result.edges:
            if edge.id in text_miner_annotations:
                edge.edge_attributes.extend(text_miner_annotations[edge.id])

        return annotated_result

    def query_for_associations_in_text_miner(self, query_order, results):
        # check for appropriate query
        triplets_to_search = self._get_text_miner_triplets(query_order)

        if not triplets_to_search:
            logger.info("No triplets appropriate for TextMiner search")
            return results

        annotated_results = []
        for result in results:
            annotated_results.append(self._make_result_with_text_miner_annotation(result, triplets_to_search))

        return annotated_results
