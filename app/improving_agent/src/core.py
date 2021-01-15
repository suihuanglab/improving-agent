#!/usr/bin/env python
# These functions should contain the core logic of evidARA-SPOKE
# interactions

from werkzeug.exceptions import BadRequest

from improving_agent.__main__ import get_db
from improving_agent.models import Message, QueryGraph, QEdge, Response
from improving_agent.src.basic_query import BasicQuery
from improving_agent.src.normalization.node_normalization import validate_normalize_qnodes
from improving_agent.util import get_evidara_logger

logger = get_evidara_logger(__name__)


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
        # as we unpack queries here and elsewhere, note that we never
        # use the classmethod `from_dict` because we've added some
        # openAPI-incompatible classes that prevent these from
        # deserializing using openAPI tools
        try:
            query_message = Message(**query.message)
            query_graph = QueryGraph(**query_message.query_graph)
        except TypeError:
            raise BadRequest("Couldn't deserialize query_message or query_graph")
        qnodes = validate_normalize_qnodes(query_graph.nodes)

        qedges = {}
        for qedge_id, qedge in query_graph.edges.items():
            qedge = QEdge(**qedge)
            setattr(qedge, 'qedge_id', qedge_id)
            qedges[qedge_id] = qedge

    except TypeError as e:
        return f"Bad Request with keyword {str(e)}", 400

    # TODO: logic for different query types
    querier = BasicQuery(
        qnodes, qedges  # query_message.query_options, query_message.n_results TODO: add these back
    )
    # now query SPOKE
    with get_db() as session:
        try:
            results, knowledge_graph = querier.linear_spoke_query(session)
            if isinstance(results, str):
                return results, 400
        except BadRequest as e:
            return str(e), 400
        response_message = Message(results, query_graph, knowledge_graph)
        response = Response(response_message, 'Success')
    return response
