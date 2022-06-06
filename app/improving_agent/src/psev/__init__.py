import logging
from typing import Dict, List, Optional, Union

from improving_agent.src.biolink.spoke_biolink_constants import SPOKE_LABEL_COMPOUND

from .psev_client import (
    PsevClient,
    PSEV_SERVICE_SUPPORTED_NODE_TYPES,
    PSEV_SERVICE_SUPPORTED_PSEV_CONCEPT_TYPES
)
from improving_agent.models import QNode
from improving_agent.src.config import app_config

logger = logging.getLogger(__name__)


def get_psev_scores(concepts: List[Union[int, str]],
                    identifiers: Optional[List[Union[int, str]]] = None,
                    node_type: Optional[str] = None):
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

    # psev service requires all node identifiers be str, so convert here
    if identifiers:
        for _id in identifiers:
            if isinstance(_id, int):
                q_ids.append(str(_id))
            elif isinstance(_id, str):
                q_ids.append(_id)
            else:
                raise ValueError('`identifiers` must be list of str or int')

    # check that the node type is supported by PSEV service
    if node_type and node_type not in PSEV_SERVICE_SUPPORTED_NODE_TYPES:
        raise ValueError(f'`node_type may only be one of` {", ".join(PSEV_SERVICE_SUPPORTED_NODE_TYPES)}')

    # query
    psev_client = PsevClient(app_config.PSEV_API_KEY, app_config.PSEV_SERVICE_URL)
    try:
        result = psev_client.get_psev_scores(q_concepts, q_ids, node_type)
    except Exception as e:
        logger.exception(
            f'Failed to retrieve PSEV values from psev service, error was: {e}'
        )
        return {concept: {} for concept in concepts}

    # handle the result
    if not identifiers:  # node_type query
        # Some node types (e.g. Gene) require that their identifiers
        # be converted back to int from str. Handlers will need to be
        # written accordingly to implement other node types not listed
        # below.
        if node_type not in [SPOKE_LABEL_COMPOUND]:
            raise ValueError(
                'This is a safety exception. Only some node types are '
                'supported. Ensure that new node types do not need to be '
                'converted back to a non-str and add them to the test '
                'that raises this error.'
            )
        return result

    # convert ids back to int, as necessary
    resulting_psevs = {}
    for concept in concepts:
        resulting_psevs[concept] = {}
        for identifier in identifiers:
            if isinstance(identifier, int):
                resulting_psevs[concept][identifier] = result[concept][str(identifier)]
            else:
                resulting_psevs[concept][identifier] = result[concept][identifier]

    return resulting_psevs


def _get_supported_psev_concepts(qnode: QNode) -> List[Union[str, int]]:
    '''Returns a list of identifiers from a single QNode that may be
    supported as PSEVs
    '''
    for spoke_label in qnode.spoke_labels:
        if spoke_label in PSEV_SERVICE_SUPPORTED_PSEV_CONCEPT_TYPES:
            return qnode.spoke_identifiers

    return []


def get_psev_concepts(qnodes: Dict[str, QNode]) -> List[Union[str, int]]:
    '''Returns a list of identifiers that may have PSEV contexts. As of
    2021-09, this is only for nodes that are identifiable as Disease
    or Compound

    Parameters
    ----------
    qnodes:
        dict of QNode: Qnodes that have been normalized and given their
        SPOKE label equivalents
    '''
    psev_concepts = []
    for qnode in qnodes.values():
        psev_concepts.extend(_get_supported_psev_concepts(qnode))

    # we double quote identifiers elsewhere for Cypher compilation
    return [i.replace("'", '') for i in psev_concepts]
