from typing import Dict, List

import requests

PSEV_SERVICE_PSEV_ENDPOINT = 'psev'
PSEV_SERVICE_CONCEPTS = 'concepts'
PSEV_SERVICE_IDENTIFIERS = 'node_identifiers'


class PsevClient:
    def __init__(self, api_key, service_url):
        self._api_key = api_key
        self._service_url = '/'.join([service_url, PSEV_SERVICE_PSEV_ENDPOINT])

    def get_psev_scores(
        self, concepts: List[str], node_identifiers: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """Returns PSEV scores for all `node_identifiers` for all
        `conepts` as a dict of {concept: {identifier: score}}

        Note that all concepts and node_identifiers should be strings,
        thus the caller should convert and lookup str equivalents of
        integer identifiers, e.g. Gene
        """
        if not isinstance(concepts, list) or not all(isinstance(i, str) for i in concepts):
            raise ValueError('`concepts` must be a list of str')
        if (
            not isinstance(node_identifiers, list)
            or not all(isinstance(i, str) for i in node_identifiers)
        ):
            raise ValueError('`node_identifiers` must be a list of str')
        payload = {
            'token': self._api_key,
            PSEV_SERVICE_CONCEPTS: concepts,
            PSEV_SERVICE_IDENTIFIERS: node_identifiers
        }
        r = requests.get(self._service_url, params=payload)
        r.raise_for_status()

        return r.json()
