from datetime import datetime
from typing import NamedTuple, Optional
from uuid import uuid4

import neo4j
import neo4j.graph
from werkzeug.exceptions import BadRequest, NotImplemented

from improving_agent.exceptions import (
    AmbiguousPredicateMappingError,
    MissingComponentError,
    NoResultsError,
    NonLinearQueryError,
    TemplateQuerySpecError,
    UnmatchedIdentifierError,
    UnsupportedConstraint,
    UnsupportedKnowledgeType,
    UnsupportedQualifier,
    UnsupportedSetInterpretation,
    UnsupportedTypeError,
)
from improving_agent.models.analysis import Analysis
from improving_agent.models.attribute import Attribute
from improving_agent.models.auxiliary_graph import AuxiliaryGraph
from improving_agent.models.edge import Edge
from improving_agent.models.edge_binding import EdgeBinding
from improving_agent.models.knowledge_graph import KnowledgeGraph
from improving_agent.models.message import Message
from improving_agent.models.node import Node
from improving_agent.models.node_binding import NodeBinding
from improving_agent.models.q_edge import QEdge
from improving_agent.models.q_node import QNode
from improving_agent.models.query_graph import QueryGraph
from improving_agent.models.response import Response
from improving_agent.models.result import Result
from improving_agent.src.basic_query import make_qnode_filter_clause
from improving_agent.src.biolink.spoke_biolink_constants import (
    BIOLINK_ASSOCIATION_RELATED_TO,
    BIOLINK_ENTITY_CHEMICAL_ENTITY,
    BIOLINK_ENTITY_DRUG,
    BIOLINK_ENTITY_SMALL_MOLECULE,
    BIOLINK_SLOT_SUPPORT_GRAPHS,
    INFORES_IMPROVING_AGENT,
    KNOWLEDGE_TYPE_LOOKUP,
    KNOWLEDGE_TYPE_INFERRED,
    SPOKE_ANY_TYPE,
    SPOKE_BIOLINK_NODE_MAPPINGS,
    SPOKE_LABEL_COMPOUND,
    SPOKE_EDGE_TYPE_INTERACTS_PiP,
    SPOKE_EDGE_TYPE_NEGATIVELYCORRELATED_CaD,
    SPOKE_EDGE_TYPE_NEGATIVELYCORRELATED_DaD,
)
from improving_agent.src.config import app_config
from improving_agent.src.normalization import SearchNode
from improving_agent.src.normalization.node_normalization import (
    validate_normalize_qnodes,
)
from improving_agent.src.provenance import make_internal_retrieval_source
from improving_agent.src.result_handling import (
    make_result_edge,
    make_result_node,
    normalize,
)
from improving_agent.util import get_evidara_logger

_logger = get_evidara_logger(__name__)


class PathfinderConfig(NamedTuple):
    start_qnode: QNode
    end_qnode: QNode
    # start_curie: str
    # end_curie: str
    # start_labels: list[str]
    # end_labels: list[str]
    undesired_edges: list[str]
    intermediate_labels: Optional[list[str]] = None
    intermediate_ids: Optional[list[str]] = None


DEFAULT_EXCLUDE_EDGES = [
    SPOKE_EDGE_TYPE_INTERACTS_PiP,
    SPOKE_EDGE_TYPE_NEGATIVELYCORRELATED_CaD,
    SPOKE_EDGE_TYPE_NEGATIVELYCORRELATED_DaD,
]

#######################
#  Cypher query config
#######################


def cyph_get_path_string(n_hops: int) -> str:
    return (
        f'MATCH p=(start)-[path*{n_hops}]-(end) '
        'WHERE NONE(rel in relationships(p) WHERE type(rel) IN $undesired_edges) '  # (start.identifier=$start_curie AND end.identifier=$end_curie) '
        # 'AND NONE(rel in relationships(p) WHERE type(rel) IN $undesired_edges) '
    )


def cyph_make_qnode_filter_clause(name, query_node):
    labels_clause = ''
    if query_node.spoke_labels:
        if SPOKE_ANY_TYPE not in query_node.spoke_labels:
            labeled_names = [f'{name}:{label}' for label in query_node.spoke_labels]
            labels_clause = f'({" OR ".join(labeled_names)})'

    identifiers_clause = ''
    if query_node.spoke_identifiers:
        identifiers_clause = f'{name}.identifier IN ${name}_identifiers'
        # TODO: this will quickly become untenable as we add better querying
        # and we'll need specific funcs; see also drug below
        if SPOKE_LABEL_COMPOUND in query_node.spoke_labels:
            identifiers_clause = f'({identifiers_clause} OR {name}.chembl_id IN ${name}_identifiers)'
    if query_node.categories:
        if (
            BIOLINK_ENTITY_DRUG in query_node.categories
            and BIOLINK_ENTITY_CHEMICAL_ENTITY not in query_node.categories
            and BIOLINK_ENTITY_SMALL_MOLECULE not in query_node.categories
        ):
            if identifiers_clause:
                identifiers_clause = f'{identifiers_clause} AND'
            identifiers_clause = f'{identifiers_clause} {name}.max_phase > 0'

    # constraints_clause = ''
    # if query_node.constraints:
    #     constraints_clause = ' AND '.join([
    #         get_node_constraint_cypher_clause(query_node, name, constraint)
    #         for constraint
    #         in query_node.constraints
    #     ])

    filter_clause = ' AND '.join([
        clause for clause
        in (labels_clause, identifiers_clause)
        if clause
    ])

    if filter_clause:
        return f'({filter_clause})'

    return ''


def _get_label_clause(
        name: str,
        labels: Optional[list[str]],
) -> Optional[str]:
    if not labels:
        return
    labeled_names = [f'{name}:{label}' for label in labels]
    return f'({" OR ".join(labeled_names)})'


def cyph_get_label_constraints_clause(
    start_labels: Optional[list[str]] = None,
    end_labels: Optional[list[str]] = None,
) -> str | None:
    if not start_labels and not end_labels:
        return
    clauses = []
    for name, labels in (
        ('start', start_labels),
        ('end', end_labels),
    ):
        clause = _get_label_clause(name, labels)
        if clause:
            clauses.append(clause)

    return ' AND '.join(clauses)


def cyph_get_intermediate_node_label_constraints(labels: list[str]) -> str:
    labels_clause = _get_label_clause('i_node', labels)
    if not labels_clause:
        return
    return f'(ANY(i_node in nodes(p) WHERE {labels_clause}))'


def cyph_get_intermediate_node_id_constraints(identifiers: list[str]) -> str:
    if not identifiers:
        return
    return '(ANY(i_node in nodes(p) WHERE i_node.identifier in $i_node_ids))'


def _get_cypher(
        pathfinder_cfg: PathfinderConfig,
        n_hops: int,
        limit: Optional[int] = 1000,
        skip: Optional[int] = 0,
) -> str:
    cypher = cyph_get_path_string(n_hops)
    # labels_clause = cyph_get_label_constraints_clause(
    #     pathfinder_cfg.start_labels,
    #     pathfinder_cfg.end_labels,
    # )
    # if labels_clause:
    #     cypher += f'AND {labels_clause} '
    start_clause = cyph_make_qnode_filter_clause(
        'start',
        pathfinder_cfg.start_qnode,
    )
    cypher += f'AND {start_clause} '
    end_clause = cyph_make_qnode_filter_clause(
        'end',
        pathfinder_cfg.end_qnode,
    )
    cypher += f'AND {end_clause} '

    inode_labels_clause = cyph_get_intermediate_node_label_constraints(
        pathfinder_cfg.intermediate_labels,
    )
    if inode_labels_clause:
        cypher += f'AND {inode_labels_clause} '

    inode_ids_clause = cyph_get_intermediate_node_id_constraints(
        pathfinder_cfg.intermediate_ids,
    )
    if inode_ids_clause:
        cypher += f'AND {inode_ids_clause} '

    cypher += 'RETURN p '
    cypher += f'SKIP {skip} '
    cypher += f'LIMIT {limit};'

    return cypher

# Unpack; serialize results


def _get_path_edges(
    relationships: list[neo4j.graph.Relationship],
) -> dict[int, Edge]:
    rel_map = {}
    for rel in relationships:
        res_edge = make_result_edge(rel, KNOWLEDGE_TYPE_LOOKUP)
        rel_map[str(rel.id)] = res_edge
    return rel_map


def _get_path_nodes(
    nodes: list[neo4j.graph.Node],
) -> tuple[dict[str, Node], set[SearchNode]]:
    node_map = {}
    search_nodes = set()
    for node in nodes:
        res_node, search_node = make_result_node(node)
        search_nodes.add(search_node)
        node_map[node['identifier']] = res_node
    return node_map, search_nodes


def _get_path_components(
    path: neo4j.graph.Path,
) -> tuple[dict[str, Edge], dict[str, Node], set[SearchNode]]:
    edges = _get_path_edges(path.relationships)
    nodes, search_nodes = _get_path_nodes(path.nodes)
    return edges, nodes, search_nodes


def _make_pf_result(
    edges: dict[str, Edge],
    start_curie: str,
    end_curie: str,
) -> tuple[Result, dict[str, Edge], dict[str, AuxiliaryGraph]]:
    # set up objects to collect results and query mappings
    edge_bindings, node_bindings = {}, {}
    # make edge for kg for related_to
    node_bindings['start'] = NodeBinding(id=start_curie, query_id=start_curie)
    node_bindings['end'] = NodeBinding(id=end_curie, query_id=end_curie)

    provenance = make_internal_retrieval_source([], INFORES_IMPROVING_AGENT.infores_id)

    aux_graph_edges = list(edges.keys())
    aux_graph = AuxiliaryGraph(edges=aux_graph_edges)
    aux_graph_id = str(uuid4())
    aux_graph_map = {aux_graph_id: aux_graph}
    supporting_edges_attr = Attribute(
        attribute_source=INFORES_IMPROVING_AGENT.infores_id,
        attribute_type_id=BIOLINK_SLOT_SUPPORT_GRAPHS,
        value=[aux_graph_id],
    )

    related_to = Edge(
        attributes=[supporting_edges_attr],
        predicate='biolink:related_to',
        subject=start_curie,
        object=end_curie,
        sources=[provenance],
    )
    edge_id = str(uuid4())
    inferred_edge = {edge_id: related_to}
    edge_bindings['path'] = [EdgeBinding(edge_id)]

    result_analysis = Analysis(
        resource_id=INFORES_IMPROVING_AGENT.infores_id,
        edge_bindings=edge_bindings,
    )
    result = Result(node_bindings, [result_analysis])
    return result, inferred_edge, aux_graph_map


def _make_start_end_search_node(qnode: QNode) -> SearchNode:
    categories = [
        SPOKE_BIOLINK_NODE_MAPPINGS[label]
        for label
        in qnode.spoke_labels
    ]
    return SearchNode(
        categories[0],
        qnode.ids[0],
    )


def _consume_results(
    paths: list[neo4j.graph.Path],
    start_qnode: QNode,
    end_qnode: QNode,
) -> tuple[KnowledgeGraph, list[Result], dict[str, AuxiliaryGraph]]:
    knowledge_graph = {'edges': {}, 'nodes': {}}
    aux_graphs = {}
    results = []
    search_nodes = set()
    for path in paths:
        # get components and update kg, nodes to normalize
        p_edges, p_nodes, p_search_nodes = _get_path_components(path)
        knowledge_graph['edges'] |= p_edges
        knowledge_graph['nodes'] |= p_nodes
        search_nodes.update(p_search_nodes)

        # we need to find the start and end node curies by iterating
        # through the possibilies. This is necessary because we may
        # search for multiple identifiers for a single node; e.g. with
        # compound nodes
        start_curie, end_curie = '', ''
        start_identifiers = _get_spoke_identifiers(start_qnode)
        end_identifiers = _get_spoke_identifiers(end_qnode)
        for p_node_id in p_nodes.keys():
            if p_node_id in start_identifiers:
                start_curie = p_node_id
            if p_node_id in end_identifiers:
                end_curie = p_node_id

        # create a result object, inferred edge, and aux_graph, then update objects
        result, inf_edge, aux_graph = _make_pf_result(
            p_edges,
            start_curie,
            end_curie,
        )
        knowledge_graph['edges'] |= inf_edge
        aux_graphs |= aux_graph
        results.append(result)

    # add search nodes for start and end nodes, as those don't pass through
    # the typical flow
    # search_nodes.add(_make_start_end_search_node(start_qnode))
    # search_nodes.add(_make_start_end_search_node(end_qnode))
    norm_kg, norm_results = normalize(search_nodes, knowledge_graph, results)

    return norm_kg, norm_results, aux_graphs


def _get_pf_query_graph(start_curie: str, end_curie: str) -> QueryGraph:
    qnodes = {
        'start': {'ids': [start_curie]},
        'end': {'ids': [end_curie]},
    }
    qedges = {
        'path': QEdge(
            subject='start',
            object='end',
            predicates=[BIOLINK_ASSOCIATION_RELATED_TO],
            knowledge_type=KNOWLEDGE_TYPE_INFERRED,
        ),
    }
    return QueryGraph(nodes=qnodes, edges=qedges)


def _get_pf_intermediate_curies(intermediate_curies: list[str]) -> list[str]:
    if not intermediate_curies:
        return
    _qnodes = {}
    for i, ic in enumerate(intermediate_curies):
        _qnodes[i] = {'ids': [ic]}
    spoke_nodes = validate_normalize_qnodes(_qnodes)
    curies = []
    for sn in spoke_nodes.values():
        for spoke_id in sn.spoke_identifiers.keys():
            curies.append(spoke_id.strip('"').strip("'"))
    return curies


def _get_intermediate_labels(intermediate_types: list[str]) -> list[str]:
    if not intermediate_types:
        return
    _qnodes = {}
    for i, it in enumerate(intermediate_types):
        _qnodes[i] = {'categories': [it]}
    spoke_nodes = validate_normalize_qnodes(_qnodes)
    labels = []
    for sn in spoke_nodes.values():
        for spoke_label in sn.spoke_labels:
            labels.append(spoke_label)
    return labels


def _convert_gene_id(id_: str, labels: list[str]) -> str | int:
    if 'Gene' not in labels:
        return id_
    try:
        return int(id_)
    except ValueError:
        return id_


def _get_spoke_identifiers(qnode: QNode) -> list[str]:
    identifiers = []
    for id_ in qnode.spoke_identifiers.keys():
        id_ = id_.strip('"').strip("'")
        id_ = _convert_gene_id(id_, qnode.spoke_labels)
        identifiers.append(id_)
    return identifiers


def _get_query_config(
    start_curie: str,
    end_curie: str,
    intermediate_types: Optional[list[str]],
    intermediate_ids: Optional[list[str]],
) -> tuple[QueryGraph, PathfinderConfig]:
    query_graph = _get_pf_query_graph(start_curie, end_curie)
    spoke_nodes = validate_normalize_qnodes(query_graph.nodes)
    intermediate_curies = _get_pf_intermediate_curies(intermediate_ids)
    intermediate_labels = _get_intermediate_labels(intermediate_types)

    return query_graph, PathfinderConfig(
        spoke_nodes['start'],
        spoke_nodes['end'],
        # start_id,
        # end_id,
        # start_labels,
        # end_labels,
        undesired_edges=DEFAULT_EXCLUDE_EDGES,
        intermediate_ids=intermediate_curies,
        intermediate_labels=intermediate_labels,
    )


def _run_query(tx, cypher, **kwargs):
    result = tx.run(cypher, **kwargs)
    values = []
    for record in result:
        values.append(record.values())
    return values


def _iter_query(
    session: neo4j.Session,
    config: PathfinderConfig,
):
    results = []
    for n_hop in (2, 3, 4):
        cypher = _get_cypher(
            config,
            n_hop,
        )
        start_spoke_ids = _get_spoke_identifiers(config.start_qnode)
        end_spoke_ids = _get_spoke_identifiers(config.end_qnode)
        values = session.read_transaction(
            _run_query,
            cypher,
            undesired_edges=config.undesired_edges,
            start_identifiers=start_spoke_ids,
            end_identifiers=end_spoke_ids,
        )
        if not values:
            continue
        results = [v[0] for v in values]
        break
    return results


def _do_pathfinder(
    session: neo4j.Session,
    start_curie: str,
    end_curie: str,
    intermediate_types: Optional[list[str]],
    intermediate_ids: Optional[list[str]],
):
    query_graph, config = _get_query_config(
        start_curie,
        end_curie,
        intermediate_types,
        intermediate_ids,
    )
    raw_results = _iter_query(session, config)
    if not raw_results:
        raise NoResultsError('Could not find any paths for input parameters')
    knowledge_graph, results, aux_graphs = _consume_results(
        raw_results,
        config.start_qnode,
        config.end_qnode,
    )
    return query_graph, knowledge_graph, results, aux_graphs


def try_pathfinder(
    session: neo4j.Session,
    start_curie: str,
    end_curie: str,
    intermediate_types: Optional[list[str]],
    intermediate_ids: Optional[list[str]],
):
    try:
        q_graph, k_graph, results, aux_graphs = _do_pathfinder(
            session,
            start_curie,
            end_curie,
            intermediate_types,
            intermediate_ids,
        )
        message = Message(
            results,
            q_graph,
            k_graph,
            aux_graphs,
        )
        return Response(
            message=message,
            status='Success; returning paths..',
            description='Success',
            schema_version=app_config.TRAPI_VERSION,
            biolink_version=app_config.BIOLINK_VERSION,
            logs=[],
        ), 200
    except NoResultsError as e:
        return Response(
            message=Message(),
            status='No paths found',
            description=str(e),
            schema_version=app_config.TRAPI_VERSION,
            biolink_version=app_config.BIOLINK_VERSION,
            logs=[],
        ), 200
    except (
        AmbiguousPredicateMappingError,
        BadRequest,
        MissingComponentError,
        UnsupportedConstraint,
        UnsupportedKnowledgeType,
        TemplateQuerySpecError,
    ) as e:
        return Response(
            message=Message(),
            status='Bad Request',
            description=str(e),
            schema_version=app_config.TRAPI_VERSION,
            biolink_version=app_config.BIOLINK_VERSION,
            logs=[],
        ), 400
    except (
        NonLinearQueryError,
        UnmatchedIdentifierError,
        UnsupportedQualifier,
        UnsupportedTypeError,
    ) as e:
        return Response(
            message=Message(),
            status='Query unprocessable',
            description=f'{str(e)}; returning empty message...',
            schema_version=app_config.TRAPI_VERSION,
            biolink_version=app_config.BIOLINK_VERSION,
            logs=[],
        ), 200
    except (NotImplemented, UnsupportedSetInterpretation) as e:
        return Response(
            message=Message(),
            status='Not Implemented',
            description=str(e),
            schema_version=app_config.TRAPI_VERSION,
            biolink_version=app_config.BIOLINK_VERSION,
            logs=[],
        ), NotImplemented.code
    except Exception as e:
        _logger.exception(str(e))
        timestamp = datetime.now().isoformat()
        error_description = (
            'Something went wrong. If this error is reproducible using the same '
            'query configuration, please post an issue in the imProving Agent GitHub '
            'page https://github.com/suihuanglab/improving-agent '
            f'timestamp: {timestamp}'
        )
        return Response(
            message=Message(),
            status='Server Error',
            description=error_description,
            schema_version=app_config.TRAPI_VERSION,
            biolink_version=app_config.BIOLINK_VERSION,
            logs=[],
        ), 500



# TODO:
# deserialize query
# iterate through 2, 3, 4 hop
# run the transaction
# normalize
# form query graph, aux graphs
# make result