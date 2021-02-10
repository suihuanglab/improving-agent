# These functions should contain the core logic of evidARA-SPOKE
# interactions
from datetime import datetime

from werkzeug.exceptions import BadRequest

from improving_agent.__main__ import get_db
from improving_agent.exceptions import (
    AmbiguousPredicateMappingError,
    MissingComponentError,
    NonLinearQueryError,
    UnmatchedIdentifierError,
    UnsupportedTypeError
)
from improving_agent.models import Message, Query, QueryGraph, Response
from improving_agent.src.basic_query import BasicQuery
from improving_agent.src.normalization.edge_normalization import validate_normalize_qedges
from improving_agent.src.normalization.node_normalization import validate_normalize_qnodes
from improving_agent.util import get_evidara_logger

logger = get_evidara_logger(__name__)


def deserialize_query(raw_json):
    """Returns a Query and query_options

    This is done manually so we can ignore other options that are sent,
    for example, the `callback` key from the ARS.
    """
    try:
        message = raw_json['message']
    except KeyError:
        raise BadRequest('`message` must be present in Query')

    max_results = raw_json.get('max_results')
    if not max_results:
        max_results = 1000
    query_kps = raw_json.get('query_kps')
    psev_context = raw_json.get('psev_context')
    # this might seem odd, but we let connexion do type checking here
    # before we construct the query_options
    try:
        query = Query(message=message, query_kps=query_kps, psev_context=psev_context, max_results=max_results)
    except TypeError as e:
        raise BadRequest(f'Could not deserialize Query on error {e}')

    query_options = query_options = {
        'psev_context': query.psev_context,
        'query_kps': query.query_kps
    }

    return query, query_options


def process_query(raw_json):
    """Maps query nodes to SPOKE equivalents

    Parameters
    ----------
    query (models.Query): user/ARS query from the query_controller
    handler

    Returns
    -------
    res (dict or str): one key (`results`) mapped to a list of
        reasoner-standard evidara.models.Result objects; alternatively
        returns str message on error
    """
    logger.info(f"Got query {raw_json}...")
    # as we unpack queries here and elsewhere, note that we never
    # use the classmethod `from_dict` because we've added some
    # openAPI-incompatible classes that prevent these from
    # deserializing using openAPI tools
    query, query_options = deserialize_query(raw_json)
    try:
        query_message = Message(**query.message)
        qedges = query_message.query_graph['edges']
        qnodes = query_message.query_graph['nodes']
        query_graph = QueryGraph(nodes=qnodes, edges=qedges)
    except (KeyError, TypeError):
        raise BadRequest('Could not deserialize query_message or query_graph')

    qnodes = validate_normalize_qnodes(query_graph.nodes)
    qedges = validate_normalize_qedges(query_graph)

    querier = BasicQuery(qnodes, qedges, query_options, query.max_results)

    # now query SPOKE
    with get_db() as session:
        results, knowledge_graph = querier.linear_spoke_query(session)
        response_message = Message(results, query_graph, knowledge_graph)
        response = Response(response_message, f'Success. Returning {len(results)} results...')
    return response


def try_query(query):
    try:
        return process_query(query)
    except (AmbiguousPredicateMappingError, BadRequest, MissingComponentError) as e:
        return Response(message=Message(), status=400, description=str(e)), 400
    except (NonLinearQueryError, UnmatchedIdentifierError, UnsupportedTypeError) as e:
        return Response(Message(), status=200, description=f'{str(e)}; returning empty message...'), 200
    except Exception as e:
        logger.exception(str(e))
        timestamp = datetime.now().isoformat()
        error_description = (
            'Something went wrong. If this error is reproducible using the same '
            'query configuration, please post an issue in the imProving Agent GitHub '
            'page https://github.com/suihuanglab/improving-agent '
            f'timestamp: {timestamp}'
        )
        return Response(Message(), status=500, description=error_description), 500
