# std library
from collections import Counter, namedtuple

# third party
import neo4j

# locals
from improving_agent import models
from improving_agent.src.exceptions import MissingComponentError
from improving_agent.src.kps.biggim import BigGimClient
from improving_agent.src.kps.cohd import CohdClient
from improving_agent.src.kps.text_miner import TextMinerClient
from improving_agent.src.psev import get_psev_weights
from improving_agent.src.spoke_constants import (
    BIOLINK_SPOKE_NODE_MAPPINGS,
    SPOKE_BIOLINK_NODE_MAPPINGS,
)

# logger
from improving_agent.util import get_evidara_logger

logger = get_evidara_logger(__name__)
ExtractedResult = namedtuple('ExtractedResult', ['nodes', 'edges', 'knowledge_map'])

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


@register_scoring_function('psev_weight')
def get_psev_score(node_attribute):
    return node_attribute.value * 10000


@register_scoring_function('spearman_correlation')
def get_evidential_score(edge_attribute):
    return edge_attribute.value


@register_scoring_function('text_miner_max_ngd_for_sub_obj')
def get_text_miner_score(edge_attribute):
    return edge_attribute.value


class BasicQuery:
    """A class for making basic queries to the SPOKE neo4j database"""

    def __init__(self, nodes, edges, query_options, n_results):
        """Instantiates a new BasicQuery object"""
        self.nodes = nodes
        self.edges = edges
        self.query_options = query_options if query_options else {}
        self.n_results = n_results if n_results else 200
        self.result_nodes = {}

        self.n_results = self.n_results if self.n_results < 200 else 200

        # check for query_options and replace saves lots of `if`ing later
        if not query_options:
            self.query_options = {}

    def query_setup(self):
        """"""
        # get nodes as dict for later lookup by identifier
        self.query_nodes_map = self.make_node_dictionary(self.nodes)
        if isinstance(self.query_nodes_map, str):
            raise NotImplementedError(f"{self.query_nodes_map}")
        self.make_query_order()

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

    def get_n4j_str_repr(self, query_part, name):
        """Returns string representation of node or edge for Cypher
        querying

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
        # not supporting specific edge types until mapped to biolink
        if isinstance(query_part, models.QEdge):
            return f"[{name}]"

        # start constructing the string, then add optional features
        node_repr = f"({name}"
        # add a label if we can, then add parameters if possible
        spoke_label_id_config = BIOLINK_SPOKE_NODE_MAPPINGS[query_part.type]
        if spoke_label_id_config[0]:
            spoke_label = spoke_label_id_config[0]
            node_repr += f":{spoke_label} "
            # add a parameter if we can
            if query_part.curie:
                # handle different configs for different node identifiers
                if spoke_label_id_config[1] == "split":
                    curie = query_part.curie.split(":")
                    if len(curie) > 2:
                        curie = ":".join(curie[1:])
                    else:
                        curie = curie[1]
                else:
                    curie = query_part.curie
                try:
                    # TODO make sure this isn't a float
                    # currently none in spoke, but this could easily happen
                    curie = int(curie)
                except ValueError:
                    pass
                parameter_string = self.get_n4j_param_str({"identifier": curie})
                node_repr += f"{parameter_string}"
        node_repr += ")"
        return node_repr

    def make_node_dictionary(self, nodes):
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
                    node.spoke_label = BIOLINK_SPOKE_NODE_MAPPINGS[node.type][0]
                except KeyError:
                    errors.append(
                        f"Node type {node.type} not (yet) supported by evidARA"
                    )
            node_d[node.node_id] = node
        if len(errors):
            return ", ".join(errors)
        return node_d

    def make_query_order(self):
        """Constructs a list of QNodes and QEdges in the order in which
        they should be sent to neo4j for querying
        """
        # process edges to find terminal nodes so the query can be ordered
        if len(self.edges) > 1:
            node_appearances = []
            _ = [
                node_appearances.extend([e.source_id, e.target_id]) for e in self.edges
            ]
            node_count = Counter(node_appearances)
            terminal_nodes = [node for node in node_count if node_count[node] == 1]
        else:
            terminal_nodes = list(self.query_nodes_map.keys())

        # start query order with either of the terminal nodes
        self.query_order = [self.query_nodes_map[terminal_nodes[0]]]
        target_query_length = len(self.nodes) + len(self.edges)

        # create copy of edges that can be destroyed
        edges_copy = self.edges.copy()
        while len(self.query_order) < target_query_length:
            found_flag = False
            if isinstance(self.query_order[-1], models.QNode):
                for i, edge in enumerate(edges_copy):
                    if self.query_order[-1].node_id in (edge.source_id, edge.target_id):
                        found_flag = True
                        break
                if found_flag:
                    self.query_order.append(edges_copy.pop(i))
                else:
                    raise MissingComponentError(
                        "Couldn't find edge corresponding to "
                        f"{self.query_order[-1].node_id}"
                    )
            else:
                next_node = [
                    self.query_order[-1].source_id,
                    self.query_order[-1].target_id,
                ]
                next_node.remove(self.query_order[-2].node_id)
                if len(next_node) == 1:
                    self.query_order.append(self.query_nodes_map[next_node[0]])
                else:
                    raise MissingComponentError(f"Missing one of {next_node}")

    def extract_results(self, n4j_result, query_names, query_mapping):
        """Constructs a reasoner-standard result from the result of a neo4j
        query

        Parameters
        ----------
        n4j_result (neo4j.BoltStatementResult): result of a SPOKE Cypher
            query
        record_number (int): record index
        query_names (str): string of letters corresponding to aliases in
            `n4j_result`
        query_mapping (dict): str -> str mappings of QNode/QEdge ids to
            query names

        Returns
        -------
        <unnamed> (models.Result): reasoner-standard result that can be
            returned to the user/ARS
        """
        # set up objects to collect results and query mappings
        result_nodes, result_edges = [], []
        knowledge_map = {"edges": {}, "nodes": {}}
        # iterate through results and add to result objects
        for name in query_names:
            if isinstance(n4j_result[name], neo4j.types.graph.Node):
                result_nodes.append(self.make_result_node(n4j_result[name]))
                knowledge_map["nodes"][query_mapping["nodes"][name]] = result_nodes[
                    -1
                ].id
            else:
                result_edges.append(self.make_result_edge(n4j_result[name]))
                knowledge_map["edges"][query_mapping["edges"][name]] = result_edges[
                    -1
                ].id
        return ExtractedResult(result_nodes, result_edges, knowledge_map)

    def score_result(self, nodes, edges):
        """Returns a score based on psev weights, cohort edge correlations,
            both, or none

        Parameters
        ----------
        nodes (list of models.Node): reasoner-standard Nodes that have
            a NodeAttribute for psev_weight. This is currently implemented
            to only check the final element in the list of NodeAttributes
            for each Node
        edges (list of models.Edge): reasoner-standard Edges that have
            an EdgeAttribute for cohort_correlation. This is currently
            implemented to only check the final element in the list of
            EdgeAttributes for each Edge

        Returns
        -------
        scores (dict): mapping of score (str) -> float and
            score name (str) -> str


        NOTE: currently for linear queries, all knowledge graphs are of the
            length, but dividing the sum score by `n` may make sense in the
            future
        """
        score = 0
        for node in nodes:
            for node_attribute in node.node_attributes:
                score_func = IMPROVING_AGENT_SCORING_FUCNTIONS.get(node_attribute.type)
                if score_func:
                    score += score_func(node_attribute)

        for edge in edges:
            for edge_attribute in edge.edge_attributes:
                score_func = IMPROVING_AGENT_SCORING_FUCNTIONS.get(edge_attribute.type)
                if score_func:
                    score += score_func(edge_attribute)

        scores = {'score': score, 'score_name': 'improving agent score'}
        return scores

    def get_scored_result(self, record_number, result):
        # score result, instantiate result objects and return
        scores = self.score_result(result.nodes, result.edges)
        result_knowledge_graph = models.KnowledgeGraph(result.nodes, result.edges)
        return models.Result(
            id=record_number,
            result_graph=result_knowledge_graph,
            knowledge_map=result.knowledge_map,
            **scores,
        )

    def make_result_node(self, n4j_object):
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
            id=n4j_object[
                "identifier"
            ],  # TODO look up and include database for standards
            name=n4j_object.get("name"),
            type=[
                SPOKE_BIOLINK_NODE_MAPPINGS[label] for label in list(n4j_object.labels)
            ],
            description=n4j_object.get("description"),
        )
        result_node.node_attributes = [
            models.NodeAttribute(type=k, value=v) for k, v in n4j_object.items()
        ]
        if "psev-context" in self.query_options:
            try:
                result_node.node_attributes.append(
                    models.NodeAttribute(
                        type="psev_weight",
                        value=get_psev_weights(
                            node_identifier=n4j_object["identifier"],
                            disease_identifier=self.query_options["psev-context"],
                        ),
                    )
                )
            except IndexError:  # TODO is this really a 0?
                result_node.node_attributes.append(
                    models.NodeAttribute(type="psev_weight", value=0)
                )
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
        result_edge = models.Edge(
            # TODO next two lines look up and include database per standards
            # TODO get reliable edge identifiers for `id` attribute
            # TODO get correlations score
            id=n4j_object.id,
            source_id=n4j_object.start_node["identifier"],
            target_id=n4j_object.end_node["identifier"],
            type=n4j_object.type,
        )
        result_edge.edge_attributes = [
            models.EdgeAttribute(type=k, value=v) for k, v in n4j_object.items()
        ]
        return result_edge

    def linear_spoke_query(self, session):
        """Returns the SPOKE node label equivalent to `node_type`

        Parameters
        ----------
        session (neo4j.driver.session): active neo4j session

        Returns
        -------
        results (dict or str): one key (`results`) mapped to a list of
            reasoner-standard evidara.models.Result objects; alternatively
            returns str message on error
        """
        try:
            self.query_setup()
        except (NotImplementedError, MissingComponentError) as e:
            return e

        # spoke diameter is <7 but consider enforcing max query length anyway
        query_names = "abcdefghijklmn"[: len(self.query_order)]
        query_parts = []
        query_mapping = {"edges": {}, "nodes": {}}
        for query_part, name in zip(self.query_order, query_names):
            query_parts.append(self.get_n4j_str_repr(query_part, name))
            if isinstance(query_part, models.QNode):
                query_mapping["nodes"][name] = query_part.node_id
            else:
                query_mapping["edges"][name] = query_part.edge_id
        query_string = "-".join(query_parts)
        # set max results b/c reasoner-standard default is None
        # possibly enforce a max on the query too
        r = session.run(f"match p = {query_string} " f"return * limit {self.n_results}")

        # create the results
        results = [
            self.extract_results(record, query_names, query_mapping)
            for record in r.records()
        ]

        if 'query_kps' in self.query_options:
            # check COHD for annotations
            cohd = CohdClient()
            tm = TextMinerClient()
            results = cohd.query_for_associations_in_cohd(self.query_order, results)
            results = tm.query_for_associations_in_text_miner(self.query_order, results)

        sorted_scored_results = sorted(
            [self.get_scored_result(i, result) for i, result in enumerate(results)],
            key=lambda x: x.score,
            reverse=True,
        )

        if 'query_kps' in self.query_options:
            # check BigGIM, currently here, but a better `process_results`
            # function should be created in the future
            big_gim = BigGimClient()
            results = big_gim.annotate_edges_with_biggim(
                session,
                self.query_order,
                sorted_scored_results,
                self.query_options.get("psev-context"),
            )

        return {"results": sorted_scored_results}
