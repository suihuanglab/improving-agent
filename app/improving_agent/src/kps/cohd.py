import re
from collections import defaultdict, namedtuple
from copy import deepcopy
from typing import Any, Dict, Optional

import requests

from improving_agent.models.edge_attribute import EdgeAttribute
from improving_agent.src.normalization.sri_node_normalizer import SriNodeNormalizer
from improving_agent.util import get_evidara_logger

logger = get_evidara_logger(__name__)

COHD_ACCEPTABLE_CURIE_PREFIXES_REGEX = '^CHEBI|^DB|^DOID|^MESH'
COHD_BASE_URL = 'http://tr-kp-clinical.ncats.io/api/'
COHD_DATASET_ID_PARAM = 'dataset_id'
COHD_NODES_TO_QUERY = ['biolink:Disease', 'biolink:ChemicalSubstance']

Triplet = namedtuple('Triplet', ['node1', 'edge', 'node2'])
TripletIds = namedtuple('TripletIds', ['node1_id', 'edge_id', 'node2_id'])


class CohdClient():
    def __init__(self) -> None:
        self.sri_nn = SriNodeNormalizer()
        self.cache = {
            'chi_square_associations': {},
            'curie_omop_map': {},
            'paired_concept_frequencies': {}
        }

    def _get_cache_string(self, **kwargs):
        return "_".join([f"{k}-{v}" for k, v in kwargs.items()])

    # OMOP resolution
    def _query_xref_to_omop(
        self,
        curie: str,
        **kwargs
    ) -> Dict[Any, Any]:
        """Query OxO via COHD to get OMOP standard concepts

        Parameters
        ----------
        curie: compact URI to map

        **kwargs that can be one of the following
        distance: int
            allowed distance for OxO to map to MeSH, UMLS;
            COHD may add a step to get OMOP (remote default = 2)
        local: bool
            use COHD's (faster) locally-cached version of OxO.
            COHD advice is to specify False unless concerned about
            performance
        recommend: bool
            return the one OMOP concept that COHD determines
            to be the best for their data

        Returns
        -------
        json response
        """
        payload = [("curie", curie)]
        payload.extend([(k, v) for k, v in kwargs.items()])

        response = requests.get(
            f"{COHD_BASE_URL}omop/xrefToOMOP", params=payload
        )
        if response.status_code != 200:
            logger.warning(f"COHD xrefToOMOP query failed with {response.status_code} and {response.text}")
            response.raise_for_status()

        results = response.json().get('results')
        if not results:
            return {}
        return results[0]

    def _warn_for_no_acceptable_curie(self, curie):  # move to utils?
        logger.warning(f"Couldn't find acceptable curie for {curie}")

    def _query_sri_for_acceptable_curie(self, curie):
        try:
            sri_results = self.sri_nn.get_normalized_nodes([curie])
            if not sri_results:
                self._warn_for_no_acceptable_curie(curie)
                return

        except requests.exceptions.HTTPError:
            return

        if re.match(COHD_ACCEPTABLE_CURIE_PREFIXES_REGEX, sri_results[curie]['id']['identifier']):
            return sri_results[curie]['id']['identifier']

        equivalent_identifiers = sri_results[curie].get('equivalent_identifiers')
        if not equivalent_identifiers:
            self._warn_for_no_acceptable_curie(curie)
            return

        for equivalent_identifier in equivalent_identifiers:
            if re.match(COHD_ACCEPTABLE_CURIE_PREFIXES_REGEX, equivalent_identifier['identifier']):
                return equivalent_identifier['identifier']

        self._warn_for_no_acceptable_curie(curie)

    def get_recommended_omop_concept(
        self,
        curie: str
    ) -> Optional[int]:
        """Gets COHD's recommended OMOP concept for a given CURIE"""
        concept = self.cache['curie_omop_map'].get(curie)
        if concept == 'no xref':
            return

        if concept is None:
            normalized_curie = curie
            if not re.match(COHD_ACCEPTABLE_CURIE_PREFIXES_REGEX, curie):
                normalized_curie = self._query_sri_for_acceptable_curie(normalized_curie)
                if not normalized_curie:
                    return

            logger.info(f"Querying COHD for recommended OMOP id for {normalized_curie}")
            result = self._query_xref_to_omop(normalized_curie, recommend=True)

            concept = result.get('omop_standard_concept_id', 'no xref')
            self.cache['curie_omop_map'][curie] = concept
            if concept == 'no xref':
                return

        return concept

    # Associations and frequencies
    def get_chi_square_associations(
        self, concept_1: int, dataset_id: int = 3, **kwargs
    ):
        # check cache
        cache_string = self._get_cache_string(concept_1=concept_1, dataset_id=dataset_id, **kwargs)
        cached = self.cache['chi_square_associations'].get(cache_string)
        if cached:
            return cached

        # construct payload
        payload = [("concept_id_1", concept_1), (COHD_DATASET_ID_PARAM, dataset_id)]
        payload.extend([(k, v) for k, v in kwargs.items()])

        logger.info(f"Querying COHD chi-square with {payload}")

        # query
        response = requests.get(
            f"{COHD_BASE_URL}association/chiSquare", params=payload
        )

        # handle response
        if response.status_code != 200:
            logger.warning(f"COHD chi-square query failed with {response.status_code} and {response.text}")
            response.raise_for_status()

        results = response.json().get('results')

        # check results, cache, and return
        if not results:
            self.cache['chi_square_associations'][cache_string] = {}
            return {}

        self.cache['chi_square_associations'][cache_string] = results[0]
        return results[0]

    def get_paired_concept_frequencies(self, q: str, dataset_id: int = 3):
        # check cache
        cache_string = self._get_cache_string(q=q, dataset_id=dataset_id)
        cached = self.cache['paired_concept_frequencies'].get(cache_string)
        if cached:
            return cached

        # construct payload and query
        payload = [("q", q), (COHD_DATASET_ID_PARAM, dataset_id)]

        logger.info(f"Querying COHD chi-square with {payload}")

        response = requests.get(
            f"{COHD_BASE_URL}frequencies/pairedConceptFreq", params=payload
        )

        # handle response
        if response.status_code != 200:
            logger.warning("COHD paired concept frequency query failed "
                           f"with {response.status_code} and {response.text}")
            response.raise_for_status()

        # get resuls, cache, and return
        results = response.json().get('results')
        if not results:
            self.cache['paired_concept_frequencies'][cache_string] = {}
            return {}

        self.cache['paired_concept_frequencies'][cache_string] = results[0]
        return results[0]

    # internal
    def _get_cohd_queryable_triplets(self, query_order):
        """Returns list of triplets that can be annotated by COHD

        Parameters
        ----------
        query_order (list of qnode and qedge objects)

        Returns
        -------
        triplets_to_search (list of tuples of qnode, qedge, qnode)
        """
        triplets_to_search = []

        first = iter(query_order)
        second = iter(query_order[2::2])

        for triplet in zip(first, first, second):
            if triplet[0].type in COHD_NODES_TO_QUERY and triplet[2].type in COHD_NODES_TO_QUERY:
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

    def _make_cohd_edge_attributes(self, clinical_frequencies={}, chi_square_results={}):
        cohd_edge_attributes = []
        for k, v in clinical_frequencies.items():
            cohd_edge_attributes.append(EdgeAttribute(type=f"cohd_paired_concept_freq_{k}", value=v))

        for k, v in chi_square_results.items():
            cohd_edge_attributes.append(EdgeAttribute(type=f"cohd_chi_square_association_{k}", value=v))

        return cohd_edge_attributes

    def _make_result_with_cohd_annotation(self, result, triplets_to_search):
        annotated_result = deepcopy(result)
        result_triplet_ids = self._extract_triplet_ids(triplets_to_search, annotated_result)

        cohd_annotations = defaultdict(list)
        for result_triplet in result_triplet_ids:
            concept_1 = self.get_recommended_omop_concept(result_triplet.node1_id)
            concept_2 = self.get_recommended_omop_concept(result_triplet.node2_id)

            if not concept_1 or not concept_2:
                cohd_annotations[result_triplet.node2_id].extend(self._make_cohd_edge_attributes())
                continue

            clinical_frequencies = self.get_paired_concept_frequencies(f"{concept_1},{concept_2}")
            chi_square_results = self.get_chi_square_associations(concept_1, concept_id_2=concept_2)

            cohd_annotations[result_triplet.edge_id].extend(
                self._make_cohd_edge_attributes(clinical_frequencies, chi_square_results)
            )

        for edge in annotated_result.edges:
            if edge.id in cohd_annotations:
                edge.edge_attributes.extend(cohd_annotations[edge.id])

        return annotated_result

    def query_for_associations_in_cohd(self, query_order, results):
        # check for appropriate query
        triplets_to_search = self._get_cohd_queryable_triplets(query_order)

        if not triplets_to_search:
            logger.info("No triplets appropriate for COHD search")
            return results

        annotated_results = []
        for result in results:
            try:
                annotated_results.append(self._make_result_with_cohd_annotation(result, triplets_to_search))
            except requests.exceptions.HTTPError as e:
                logger.warning(f"Failed to get results from COHD with {e}")

        return annotated_results
