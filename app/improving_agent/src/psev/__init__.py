import logging
from typing import List, Union

from improving_agent.src.config import app_config
from .psev_client import PsevClient

logger = logging.getLogger(__name__)


def get_psev_scores(concepts: List[Union[int, str]],
                    identifiers: List[Union[int, str]]):
    """A wrapper function to call the psev-service to get psev scores
    for the requested nodes. Converts int IDs to str and vice versa upon
    return.

    If the call proceeds as intended, the caller will receive a dict of
    {concept: {identifier: score}}. On error, the caller will receive
    None

    TODO: should this return a collapsed PSEV value for each identifier?
    We are effectively doing this downstream, but might want keep the
    concepts separate for one reason or another.
    """
    q_concepts, q_ids = [], []
    for concept in concepts:
        if isinstance(concept, int):
            q_concepts.append(str(concept))
        elif isinstance(concept, str):
            q_concepts.append(concept)
        else:
            raise ValueError('`concepts` must be list of str or int')

    for _id in identifiers:
        if isinstance(_id, int):
            q_ids.append(str(_id))
        elif isinstance(_id, str):
            q_ids.append(_id)
        else:
            raise ValueError('`identifiers` must be list of str or int')

    psev_client = PsevClient(app_config.PSEV_API_KEY, app_config.PSEV_SERVICE_URL)
    try:
        result = psev_client.get_psev_scores(q_concepts, q_ids)
    except Exception as e:
        logger.exception(
            f'Failed to retrieve PSEV values from psev service, error was: {e}'
        )
        empty_results = {}
        for concept in concepts:
            for _id in identifiers:
                empty_results[concept][_id] = 0
        return empty_results

    resulting_psevs = {}
    for concept in concepts:
        resulting_psevs[concept] = {}
        for identifier in identifiers:
            if isinstance(identifier, int):
                resulting_psevs[concept][identifier] = result[concept][str(identifier)]
            else:
                resulting_psevs[concept][identifier] = result[concept][identifier]

    return resulting_psevs
