import re
from functools import lru_cache
from typing import Any, Dict, Optional

import requests

from improving_agent.src.normalization.sri_node_normalizer import SRI_NODE_NORMALIZER
from improving_agent.util import get_evidara_logger

logger = get_evidara_logger(__name__)

COHD_ACCEPTABLE_CURIE_PREFIXES_REGEX = '^CHEBI|^DB|^DOID|^MESH'
COHD_BASE_URL = 'http://tr-kp-clinical.ncats.io/api/'
COHD_DATASET_ID_PARAM = 'dataset_id'


def _warn_for_no_acceptable_curie(curie):
    logger.warning(f"Couldn't find acceptable curie for {curie}")


class CohdClient():
    # TODO: this should be refactored a bit to keep things a bit more in
    # scope of only dealing with COHD itself. The SRI querying via the
    # query_xref_to_omop func could stand to be removed to external
    # funcs; it's pretty odd that a COHD client would be querying SRI...
    def __init__(self) -> None:
        pass

    def _get_cache_string(self, **kwargs):
        return "_".join([f"{k}-{v}" for k, v in kwargs.items()])

    def _query_sri_for_acceptable_curie(self, curie):
        try:
            sri_results = SRI_NODE_NORMALIZER.get_normalized_nodes([curie])
            if not sri_results:
                _warn_for_no_acceptable_curie(curie)
                return

        except requests.exceptions.HTTPError:
            return

        if re.match(COHD_ACCEPTABLE_CURIE_PREFIXES_REGEX, sri_results[curie]['id']['identifier']):
            return sri_results[curie]['id']['identifier']

        equivalent_identifiers = sri_results[curie].get('equivalent_identifiers')
        if not equivalent_identifiers:
            _warn_for_no_acceptable_curie(curie)
            return

        for equivalent_identifier in equivalent_identifiers:
            if re.match(COHD_ACCEPTABLE_CURIE_PREFIXES_REGEX, equivalent_identifier['identifier']):
                return equivalent_identifier['identifier']

        _warn_for_no_acceptable_curie(curie)

    # OMOP resolution
    def _query_xref_to_omop(self, curie: str, **kwargs) -> Dict[Any, Any]:
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

    @lru_cache(maxsize=500)
    def get_recommended_omop_concept(self, curie: str) -> Optional[int]:
        """Gets COHD's recommended OMOP concept for a given CURIE"""
        normalized_curie = curie
        if not re.match(COHD_ACCEPTABLE_CURIE_PREFIXES_REGEX, curie):
            normalized_curie = self._query_sri_for_acceptable_curie(normalized_curie)
            if not normalized_curie:
                return

        logger.info(f"Querying COHD for recommended OMOP id for {normalized_curie}")
        result = self._query_xref_to_omop(normalized_curie, recommend=True)

        concept = result.get('omop_standard_concept_id', 'no xref')
        if concept == 'no xref':
            return

        return concept

    # Associations and frequencies
    @lru_cache(maxsize=500)
    def get_chi_square_associations(self, concept_1: int, dataset_id: int = 3, **kwargs):
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

        # check results and return
        if not results:
            return {}

        return results[0]

    @lru_cache(maxsize=500)
    def get_paired_concept_frequencies(self, q: str, dataset_id: int = 3):
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
            return {}

        return results[0]


COHD_CLIENT = CohdClient()
