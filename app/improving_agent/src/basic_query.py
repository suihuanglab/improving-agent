from collections import Counter, namedtuple

import neo4j
from improving_agent import models  # TODO: replace with direct imports after fixing definitions
from improving_agent.exceptions import MissingComponentError
from improving_agent.src.improving_agent_constants import (
    ATTRIBUTE_TYPE_PSEV_WEIGHT,
    SPOKE_NODE_PROPERTY_SOURCE
)
from improving_agent.src.kps.biggim import annotate_edges_with_biggim
from improving_agent.src.kps.cohd import annotate_edges_with_cohd
from improving_agent.src.kps.text_miner import TextMinerClient
from improving_agent.src.normalization import SearchNode
from improving_agent.src.normalization.node_normalization import normalize_spoke_nodes_for_translator
from improving_agent.src.psev import get_psev_weights
from improving_agent.src.spoke_biolink_constants import (
    BIOLINK_ASSOCIATION_TYPE,
    BIOLINK_ASSOCIATION_RELATED_TO,
    RELATIONSHIP_ONTOLOGY_CURIE,
    SPOKE_BIOLINK_NODE_MAPPINGS,
    SPOKE_BIOLINK_EDGE_MAPPINGS,
)
from improving_agent.util import get_evidara_logger

logger = get_evidara_logger(__name__)
ExtractedResult = namedtuple('ExtractedResult', ['nodes', 'edges'])

IMPROVING_AGENT_SCORING_FUCNTIONS = {}


def register_scoring_function(attribute_name):
    def wrapper(f):
        IMPROVING_AGENT_SCORING_FUCNTIONS[attribute_name] = f
        return f
    return wrapper


@register_scoring_function('cohd_paired_concept_freq_concept_frequency')
def get_cohd_edge_score(edge_attribute):
    return edge_attribute.value * 1000


@register_scoring_function('has_feature_importance')
def get_multiomics_model_score(edge_attribute):
    return edge_attribute.value


@register_scoring_function(ATTRIBUTE_TYPE_PSEV_WEIGHT)
def get_psev_score(node_attribute):
    return node_attribute.value * 10000


@register_scoring_function('spearman_correlation')
def get_evidential_score(edge_attribute):
    return edge_attribute.value


@register_scoring_function('text_miner_max_ngd_for_sub_obj')
def get_text_miner_score(edge_attribute):
    return edge_attribute.value


# Cypher
def make_qnode_filter_clause(name, query_node):
    labels_clause = ''
    if query_node.spoke_labels:
        labeled_names = [f'{name}:{label}' for label in query_node.spoke_labels]
        labels_clause = f'({" OR ".join(labeled_names)})'

    identifiers_clause = ''
    if query_node.spoke_identifiers:
        identifiers_clause = f'{name}.identifier IN [{",".join(query_node.spoke_identifiers)}]'

    if labels_clause:
        if identifiers_clause:
            return f'({labels_clause} AND {identifiers_clause})'
        else:
            return labels_clause
    if identifiers_clause:
        return f'({identifiers_clause})'
    return ''


def make_qedge_cypher_repr(name, query_edge):
    edge_repr = f'[{name}'
    if query_edge.spoke_edge_types:
        edge_repr = f'{edge_repr}:{"|".join(query_edge.spoke_edge_types)}'
    edge_repr += ']'
    return edge_repr


def get_n4j_param_str(self, parameters):
    """Returns a string properly formatted for neo4j parameter-based
    searching

    Parameters
    ----------
    parameters (dict of str -> int|str): parameter mappings to
    convert to string suitable for Cypher querying

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


class BasicQuery:
    """A class for making basic queries to the SPOKE neo4j database"""

    def __init__(self, qnodes, qedges, query_options={}, n_results=200):
        """Instantiates a new BasicQuery object"""
        self.qnodes = qnodes
        self.qedges = qedges
        self.query_options = query_options
        self.n_results = n_results

        self.knowledge_graph = {"edges": {}, "nodes": {}}
        self.knowledge_node_counter = 0
        self.knowledge_edge_counter = 0

        self.nodes_to_normalize = set()
        self.results = []

        self.n_results = self.n_results if self.n_results < 200 else 200
        # TODO: write a message in the response that the max results is 200

    def make_query_order(self):
        """Constructs a list of QNodes and QEdges in the order in which
        they should be sent to neo4j for querying
        """
        # process edges to find terminal nodes so the query can be ordered
        if len(self.qedges) > 1:
            node_appearances = []
            for qedge in self.qedges.values():
                node_appearances.extend([qedge.subject, qedge.object])

            node_count = Counter(node_appearances)
            terminal_nodes = [node for node in node_count if node_count[node] == 1]

        else:  # one-hop query
            terminal_nodes = list(self.qnodes.keys())

        # start query order with either of the terminal nodes
        self.query_order = [self.qnodes[terminal_nodes[0]]]
        target_query_length = len(self.qnodes) + len(self.qedges)

        # create copy of edges that can be destroyed
        qedges_copy = self.qedges.copy()
        while len(self.query_order) < target_query_length:
            if isinstance(self.query_order[-1], models.QNode):
                found_flag = False
                for qedge_id, qedge in qedges_copy.items():
                    if self.query_order[-1].qnode_id in (qedge.subject, qedge.object):
                        found_flag = True
                        break
                if found_flag:
                    self.query_order.append(qedges_copy.pop(qedge_id))  # qedge
                else:
                    raise MissingComponentError(
                        "Couldn't find edge corresponding to "
                        f"{self.query_order[-1].qnode_id}"
                    )

            else:
                next_node = [
                    self.query_order[-1].subject,
                    self.query_order[-1].object,
                ]
                next_node.remove(self.query_order[-2].qnode_id)
                if len(next_node) == 1:
                    self.query_order.append(self.qnodes[next_node[0]])
                else:
                    raise MissingComponentError(f"Missing one of {next_node}")

    def make_cypher_query_string(self):
        # spoke diameter is <7 but consider enforcing max query length anyway
        # TODO: get rid of this silly naming and use the now-available `qedge_id` or `qnode_id` attr
        self.query_names = list("abcdefghijklmn"[: len(self.query_order)])
        query_parts = []
        node_filter_clauses = []
        self.query_mapping = {"edges": {}, "nodes": {}}
        for query_part, name in zip(self.query_order, self.query_names):
            if isinstance(query_part, models.QNode):
                self.query_mapping["nodes"][name] = query_part.qnode_id
                query_parts.append(f'({name})')
                node_filter_clause = make_qnode_filter_clause(name, query_part)
                if node_filter_clause:
                    node_filter_clauses.append(node_filter_clause)

            else:
                self.query_mapping["edges"][name] = query_part.qedge_id
                query_parts.append(make_qedge_cypher_repr(name, query_part))

        match_clause = f'MATCH p={"-".join(query_parts)}'
        where_clause = ''
        if node_filter_clauses:
            where_clause = f'WHERE {" AND ".join(node_filter_clauses)}'
        return_clause = f'RETURN * limit {self.n_results}'

        return f'{match_clause} {where_clause} {return_clause};'

    # Result handling
    def score_result(self, result):
        """Returns a score based on psev weights, cohort edge correlations,
            both, or none

        Parameters
        ----------
        result (Result): TRAPI Result object containing node_bindings
            and edge_bindings

        Returns
        -------
        scores (dict): mapping of score (str) -> float and
            score name (str) -> str

        NOTE: currently for linear queries, all knowledge graphs are of the
            length, but dividing the sum score by `n` may make sense in the
            future
        """
        score = 0

        for knode in result.node_bindings.values():
            node = self.knowledge_graph['nodes'][knode.id]
            for attribute in node.attributes:
                score_func = IMPROVING_AGENT_SCORING_FUCNTIONS.get(attribute.type)
                if score_func:
                    score += score_func(attribute)

        for kedge in result.edge_bindings.values():
            edge = self.knowledge_graph['edges'][kedge.id]
            for attribute in edge.attributes:
                score_func = IMPROVING_AGENT_SCORING_FUCNTIONS.get(attribute.type)
                if score_func:
                    score += score_func(attribute)
        return score

    def score_results(self, results):
        scored_results = []
        for result in results:
            result.score = self.score_result(result)
            scored_results.append(result)
        return scored_results

    def make_result_node(self, n4j_object, spoke_curie):
        """Instantiates a reasoner-standard Node to return as part of a
        KnowledgeGraph result

        Parameters
        ----------
        n4j_object (neo4j.types.graph.Node): a `Node` object returned from a
            neo4j.bolt.driver.session Cypher query
        spoke_curie (str): spoke 'identifier'

        Returns
        -------
        result_node (models.Node): a reasoner-standard `Edge` object for
            inclusion as part of a KnowledgeGraph result
        """
        name = n4j_object.get("pref_name")
        if not name:
            name = n4j_object.get("name")

        result_node_attributes = []
        node_source = None
        for k, v in n4j_object.items():
            # TODO: filter these to something reasonable
            result_node_attributes.append(models.Attribute(type=k, value=v))
            if k == SPOKE_NODE_PROPERTY_SOURCE:
                node_source = v

        result_node = models.Node(
            name=name,
            category=[SPOKE_BIOLINK_NODE_MAPPINGS[label] for label in list(n4j_object.labels)],
            attributes=result_node_attributes
        )

        psev_context = self.query_options.get('psev_context')
        if psev_context:
            try:
                result_node.attributes.append(
                    models.Attribute(
                        type=ATTRIBUTE_TYPE_PSEV_WEIGHT,
                        value=get_psev_weights(
                            node_identifier=n4j_object["identifier"],
                            disease_identifier=psev_context,
                        ),
                    )
                )
            except IndexError:  # TODO is this really a 0?
                result_node.attributes.append(
                    models.Attribute(type=ATTRIBUTE_TYPE_PSEV_WEIGHT, value=0)
                )

        search_node = SearchNode(result_node.category[0], spoke_curie, node_source)
        self.nodes_to_normalize.add(search_node)
        return result_node

    def make_result_edge(self, n4j_object):
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
        biolink_map_info = SPOKE_BIOLINK_EDGE_MAPPINGS.get(n4j_object.type)
        if not biolink_map_info:
            biolink_edge_data = {'predicate': BIOLINK_ASSOCIATION_RELATED_TO}
        else:
            biolink_edge_data = {
                'predicate': biolink_map_info[BIOLINK_ASSOCIATION_TYPE],
                'relation': biolink_map_info[RELATIONSHIP_ONTOLOGY_CURIE]
            }

        result_edge = models.Edge(
            # TODO get correlations score for P100/cohort data
            subject=n4j_object.start_node["identifier"],
            object=n4j_object.end_node["identifier"],
            **biolink_edge_data
        )
        result_edge.attributes = [
            models.Attribute(type=k, value=v) for k, v in n4j_object.items()
        ]
        return result_edge

    def extract_result(self, n4j_result):
        """Constructs a reasoner-standard result from the result of a neo4j
        query

        Parameters
        ----------
        n4j_result (neo4j.BoltStatementResult): result of a SPOKE Cypher
            query
        record_number (int): record index

        Returns
        -------
        <unnamed> (models.Result): TRAPI Result that can be
            returned to the user/ARS
        """
        # set up objects to collect results and query mappings
        edge_bindings, node_bindings = {}, {}

        # iterate through results and add to result objects
        for name in self.query_names:
            if isinstance(n4j_result[name], neo4j.types.graph.Node):
                spoke_curie = n4j_result[name]['identifier']
                result_node = self.make_result_node(n4j_result[name], spoke_curie)
                self.knowledge_graph['nodes'][spoke_curie] = result_node
                node_bindings[self.query_mapping['nodes'][name]] = models.NodeBinding(spoke_curie)

            else:
                spoke_edge_id = n4j_result[name].id  # TODO: is there a way to make this consistent?
                edge_bindings[self.query_mapping['edges'][name]] = models.EdgeBinding(spoke_edge_id)
                result_edge = self.make_result_edge(n4j_result[name])
                self.knowledge_graph['edges'][spoke_edge_id] = result_edge

        return models.Result(node_bindings, edge_bindings)

    # normalization
    def normalize(self):
        # search the node normalizer for nodes collected in result creation
        node_search_results = normalize_spoke_nodes_for_translator(list(self.nodes_to_normalize))
        for spoke_curie, normalized_curie in node_search_results.items():
            self.knowledge_graph['nodes'][normalized_curie] = self.knowledge_graph['nodes'].pop(spoke_curie)

        for edge in self.knowledge_graph['edges'].values():
            setattr(edge, 'object', node_search_results[edge.object])
            setattr(edge, 'subject', node_search_results[edge.subject])

        new_results = []
        for result in self.results:
            new_node_bindings = {}
            for qnode, node in result.node_bindings.items():
                new_node_bindings[qnode] = models.NodeBinding(node_search_results[node.id])
            new_results.append(models.Result(new_node_bindings, result.edge_bindings))

        self.results = new_results

    # Query
    def linear_spoke_query(self, session):
        """Returns the SPOKE node label equivalent to `node_type`

        Parameters
        ----------
        session (neo4j.driver.session): active neo4j session

        Returns
        -------
        sorted_scored_results (list of Result): TRAPI Result objects that have been
            fetched from SPOKE and scored

        knowledge_graph (KnowledgeGraph): TRAPI KnowledgeGraph object
            containing all identified nodes and edges in the response
        """
        # query setup
        self.make_query_order()
        query_string = self.make_cypher_query_string()

        # query
        logger.info(f'Querying SPOKE with {query_string}')
        r = session.run(query_string)
        self.results = [self.extract_result(record) for record in r.records()]
        if not self.results:
            return self.results, self.knowledge_graph

        # normalize the knowledge_graph and results
        self.normalize()

        # query kps
        query_kps = self.query_options.get('query_kps')
        if query_kps:
            # check KPs for annotations
            self.knowledge_graph['edges'] = annotate_edges_with_cohd(self.knowledge_graph)
        #     self.results = tm.query_for_associations_in_text_miner(self.query_order, self.results)

        scored_results = self.score_results(self.results)
        sorted_scored_results = sorted(scored_results, key=lambda x: x.score, reverse=True)

        if query_kps:
            # check BigGIM
            self.knowledge_graph['edges'] = annotate_edges_with_biggim(
                session,
                self.query_order,
                self.knowledge_graph['edges'],
                sorted_scored_results,
                self.query_options.get("psev_context"),
            )

        return sorted_scored_results, self.knowledge_graph
