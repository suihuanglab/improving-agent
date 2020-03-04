#!/usr/bin/env python
# These functions should contain the core logic of evidARA-SPOKE
# interactions

# std lib
import json
import os
from collections import Counter

# third party
import neo4j

# locals
from evidara_api.__main__ import get_db
from evidara_api import models
from evidara_api.spoke_constants import (
    BIOLINK_SPOKE_NODE_MAPPINGS,
    SPOKE_BIOLINK_NODE_MAPPINGS,
    SPOKE_NODE_IDENTIFIERS,
)


def get_n4j_param_str(parameters):
    """Returns a string properly formatted for neo4j parameter-based 
    searching
    
    Parameters
    ----------
    parameters (dict of str -> int|str): parameter mappings to convert
        to string suitable for Cypher querying

    Returns
    -------
    <unnamed> (str): formatted string for parameter search
    """
    param_string = ", ".join(
        [
            f"{k}:'{v}'" if isinstance(v, str) else f"{k}:{v}"
            for k, v in parameters.items()
        ]
    )
    return "{" + param_string + "}"


def get_n4j_str_repr(query_part, name):
    """Returns string representation of node or edge for Cypher querying

    Parameters
    ----------
    query_part (models.QNode or models.QEdge): a node or edge from a 
        QueryGraph
    name (str): alias for Cypher

    Returns
    -------
    node_repr (str): string representation of a query part, 
        e.g. "(c:Compound {chembl_id: 'CHEMBL1234'})"
    """
    # TODO support empty query nodes, i.e. only a label, * node, etc.

    # not supporting specific edge types until mapped to biolink
    if isinstance(query_part, models.QEdge):
        return f"[{name}]"

    # start constructing the string, then add optional features
    node_repr = f"({name}"
    # add a label if we can, then add parameters if possible
    if query_part.type:
        spoke_label = BIOLINK_SPOKE_NODE_MAPPINGS[query_part.type]
        node_repr += f":{spoke_label} "
        # add a parameter if we can
        if query_part.curie:  # TODO change `id` to `curie` with change to qnode
            split_curie = query_part.curie.split(":")
            if len(split_curie) > 2:
                split_curie = [split_curie[0], ":".join(split_curie[1:])]
            try:
                # TODO make sure this isn't a float
                # currently none in spoke, but this could easily happen
                split_curie[1] = int(split_curie[1])
            except ValueError:
                pass
            parameter_string = get_n4j_param_str(
                {SPOKE_NODE_IDENTIFIERS[spoke_label]: split_curie[1]}
            )
            # need to make better label dict to handle lists of
            # possible identifiers, e.g. Compound's drugbank and
            # chembl_ids
            node_repr += f"{parameter_string}"
    node_repr += ")"
    return node_repr


def linear_spoke_query(session, nodes, edges, n_results):
    """Returns the SPOKE node label equivalent to `node_type`

    Parameters
    ----------
    session (neo4j.driver.session): active neo4j session
    nodes (list of evidara.models.Node): reasoner-standard Node objects
        that constitute the query graph
    edges (list of evidara.models.Edge): reasoner-standard Edge objects
        that consitute the query graph
    n_results (int): maximum number of results to return

    Returns
    -------
    results (dict or str): one key (`results`) mapped to a list of 
        reasoner-standard evidara.models.Result objects; alternatively 
        returns str message on error
    """
    # get nodes as dict for later lookup by identifier
    node_d = make_node_dictionary(nodes)
    if isinstance(node_d, str):
        return node_d
    # process edges to find terminal nodes so the query can be ordered
    if len(edges) > 1:
        node_appearances = []
        _ = [node_appearances.extend([e.source_id, e.target_id]) for e in edges]
        node_count = Counter(node_appearances)
        terminal_nodes = [node for node in node_count if node_count[node] == 1]
    else:
        terminal_nodes = list(node_d.keys())

    # start query order with either of the terminal nodes
    query_order = [node_d[terminal_nodes[0]]]
    target_query_length = len(nodes) + len(edges)
    # TODO remember need to map back to query
    # create copy of edges that can be destroyed
    edges_copy = edges.copy()
    while len(query_order) < target_query_length:
        found_flag = False
        if isinstance(query_order[-1], models.QNode):
            for i, edge in enumerate(edges_copy):
                if query_order[-1].node_id in (edge.source_id, edge.target_id):
                    found_flag = True
                    break
            if found_flag:
                query_order.append(edges_copy.pop(i))
            else:
                return f"Couldn't find edge corresponding to {query_order[-1].node_id}"
        else:
            next_node = [query_order[-1].source_id, query_order[-1].target_id]
            next_node.remove(query_order[-2].node_id)
            if len(next_node) == 1:
                query_order.append(node_d[next_node[0]])
            else:
                return f"Missing one of {next_node}"

    # spoke diameter is <7 but consider enforcing max query length anyway
    query_names = "abcdefghijklmn"[: len(query_order)]
    query_string = "-".join(
        [
            get_n4j_str_repr(query_part, name)
            for query_part, name in zip(query_order, query_names)
        ]
    )
    # set max results b/c no default set by reasoner-standard,
    # possibly enforce a max on the query too
    n_results = n_results if n_results else 30
    r = session.run(f"match p = {query_string} " f"return * limit {n_results}")

    # create the results
    results = [
        make_evidara_result(record, i, query_names)
        for i, record in enumerate(r.records())
    ]

    return {"results": results[0]}  # only returning one result during dev


def make_node_dictionary(nodes):
    """Validates that SPOKE contains requested node type and creates a 
    dictionary from a list of evidara.models.nodes

    Parameters
    ----------
    nodes (list of evidara.models.QNode): array of nodes from a 
        user/ARS QueryGraph

    Returns
    -------
    node_d (dict or str) OR errors(str): dictionary of 
        str -> evidara.models.QNode on success; string of incompatible
        node types on failure
    """
    # here we just validate that we can actually look up nodes of a 
    # requested type
    node_d = {}
    errors = []
    for node in nodes:
        if node.type:
            try:
                node.spoke_label = BIOLINK_SPOKE_NODE_MAPPINGS[node.type]
            except KeyError:
                errors.append(f"Node type {node.type} not (yet) supported by evidARA")
        node_d[node.node_id] = node
    if len(errors):
        return ", ".join(errors)
    return node_d


def make_evidara_result(n4j_result, record_number, query_names):
    """Constructs a reasoner-standard result from the result of a neo4j 
    query

    Parameters
    ----------
    n4j_result (neo4j.BoltStatementResult): result of a SPOKE Cypher
        query
    record_number (int): record index
    query_names (str): string of letters corresponding to aliases in
        `n4j_result`

    Returns
    -------
    <unnamed> (models.Result): reasoner-standard result that can be 
        returned to the user/ARS
    """
    # need to add mappings to qnodes/qedges here
    result_nodes, result_edges = [], []
    for name in query_names:
        if isinstance(n4j_result[name], neo4j.types.graph.Node):
            result_nodes.append(make_result_node(n4j_result[name]))
        else:
            result_edges.append(make_result_edge(n4j_result[name]))

    result_knowledge_graph = models.KnowledgeGraph(result_nodes, result_edges)
    return models.Result(id=record_number, result_graph=result_knowledge_graph)


def make_result_node(n4j_object):
    """Instantiates a reasoner-standard Node to return as part of a 
    KnowledgeGraph result

    Parameters
    ----------
    n4j_object (neo4j.types.graph.Node): a `Node` object returned from a
        neo4j.bolt.driver.session Cypher query

    Returns
    -------
    result_node (models.Edge): a reasoner-standard `Edge` object for
        inclusion as part of a KnowledgeGraph result

    """
    result_node = models.Node(
        id=n4j_object["identifier"],  # TODO look up and include database for standards
        name=n4j_object.get("name"),
        type=[SPOKE_BIOLINK_NODE_MAPPINGS[label] for label in list(n4j_object.labels)],
        description=n4j_object.get("description"),
    )
    result_node.node_attributes = [
        models.NodeAttribute(type=k, value=v) for k, v in n4j_object.items()
    ]
    return result_node


def make_result_edge(n4j_object):
    """Instantiates a reasoner-standard Edge to return as part of a 
    KnowledgeGraph result

    Parameters
    ----------
    n4j_object (abc.<neo4j edge type>): a `relationship` object returned
        from a neo4j.bolt.driver.session Cypher query

    Returns
    -------
    result_edge (models.Edge): reasoner-standard Edge object for
        inclusion as a part of a KnowledgeGraph result
    """
    result_edge = models.Edge(
        # TODO next two lines look up and include database per standards
        source_id=n4j_object.start_node["identifier"],
        target_id=n4j_object.end_node["identifier"],
        type=n4j_object.type,
    )
    result_edge.edge_attributes = [
        models.EdgeAttribute(type=k, value=v) for k, v in n4j_object.items()
    ]
    return result_edge


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
        # hopefully these recursively unpack in the future upon creation
        # of the Query object, but if not, we can also consider the
        # .from_dict() method on these objects instead of ** syntax
        query_message = models.Message(**query.query_message)
        query_graph = models.QueryGraph(**query_message.query_graph)
        nodes = [models.QNode(**node) for node in query_graph.nodes]
        edges = [models.QEdge(**edge) for edge in query_graph.edges]
    except TypeError as e:
        return f"Bad Request with keyword {str(e).split()[-1]}", 400
    # now query SPOKE
    with get_db() as session:
        res = linear_spoke_query(session, nodes, edges, query_message.n_results)
        if isinstance(res, str):
            return res, 400
    return res
