#!/usr/bin/env python
# These functions should contain the core logic of evidARA-SPOKE
# interactions

# locals
from evidara_api.__main__ import get_db
from evidara_api.basic_query import BasicQuery
from evidara_api.biggim import BigGimRequester
from evidara_api import models
from evidara_api.util import get_evidara_logger

logger = get_evidara_logger(__name__)

# set up globabl caches for knowledge providers
# depending on the future of translator, this might be better handled
# by an explicit caching system like `requests-cache`
kp_caches = {"big_gim": BigGimRequester()}


def process_query(query):
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
    # manually unpack query, checking for model compliance along the way
    # raise and return 400 on failure to instantiate
    try:
        logger.info("Got query...")
        # hopefully these recursively unpack in the future upon creation
        # of the Query object, but if not, we can also consider the
        # .from_dict() method on these objects instead of ** syntax
        query_message = models.Message(**query.query_message)
        query_graph = models.QueryGraph(**query_message.query_graph)
        nodes = [models.QNode(**node) for node in query_graph.nodes]
        edges = [models.QEdge(**edge) for edge in query_graph.edges]
    except TypeError as e:
        return f"Bad Request with keyword {str(e).split()[-1]}", 400

    # TODO: logic for different query types
    querier = BasicQuery(
        nodes, edges, query_message.query_options, query_message.n_results, kp_caches
    )
    # now query SPOKE
    with get_db() as session:
        res = querier.linear_spoke_query(session)
        if isinstance(res, str):
            return res, 400
    return res
