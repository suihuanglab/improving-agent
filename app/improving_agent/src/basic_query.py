from collections import Counter, namedtuple

import neo4j
from werkzeug.exceptions import BadRequest

from improving_agent import models  # TODO: replace with direct imports after fixing definitions
from improving_agent.src.exceptions import MissingComponentError
from improving_agent.src.improving_agent_constants import ATTRIBUTE_TYPE_PSEV_WEIGHT
from improving_agent.src.kps.biggim import BigGimClient
from improving_agent.src.kps.cohd import CohdClient
from improving_agent.src.kps.text_miner import TextMinerClient
from improving_agent.src.psev import get_psev_weights
from improving_agent.src.spoke_constants import (
    BIOLINK_SPOKE_NODE_MAPPINGS,
    SPOKE_BIOLINK_NODE_MAPPINGS,
    SPOKE_BIOLINK_EDGE_MAPPINGS
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


class BasicQuery:
    """A class for making basic queries to the SPOKE neo4j database"""

    def __init__(self, qnodes, qedges, query_options={}, n_results=200):
        """Instantiates a new BasicQuery object"""
        self.qnodes = qnodes
        self.qedges = qedges
        self.query_options = query_options
        self.n_results = n_results

        self.knowledge_map = {"edges": {}, "nodes": {}}
        self.node_identifier_to_knowledge_map = {}
        self.knowledge_node_counter = 0
        self.knowledge_edge_counter = 0

        self.n_results = self.n_results if self.n_results < 200 else 200
        # TODO: write a message in the response that the max results is 200

    # neo4j
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
        query_part (QNode or QEdge): a node or edge from a QueryGraph
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
        spoke_mapping = BIOLINK_SPOKE_NODE_MAPPINGS.get(query_part.category[0])  # TODO: Allow multiple labels
        if spoke_mapping is None:
            if query_part.category:  # allow climbing of hierarchy?
                raise BadRequest(f"Bad Request: {query_part.category} not supported")
            spoke_mapping = ("", "no split")

        if spoke_mapping[0]:
            spoke_label = spoke_mapping[0]
            node_repr += f":{spoke_label} "
            # add a parameter if we can
            if query_part.id:
                # handle different configs for different node identifiers
                # TODO: better CURIE handling and lookup
                if spoke_mapping[1] == "split":
                    curie = query_part.id.split(":")
                    if len(curie) > 2:
                        curie = ":".join(curie[1:])
                    else:
                        curie = curie[1]
                else:
                    curie = query_part.id
                try:
                    # TODO make sure no CURIES are floats
                    # currently none in spoke, but this could easily happen
                    curie = int(curie)
                except ValueError:
                    pass
                parameter_string = self.get_n4j_param_str({"identifier": curie})
                node_repr += f"{parameter_string}"
        node_repr += ")"
        return node_repr

    # query construction
    def validate_qnodes(self):
        """Validates that SPOKE contains requested node types

        Parameters
        ----------
        nodes (list of QNode): array of nodes from a QueryGraph

        Returns
        -------
        node_map (dict of str): dictionary of str -> QNode
        """
        # here we just validate that we can actually look up nodes of a
        # requested type
        node_map = {}  # TODO: don't rebuild dict, just return it
        errors = []
        for qnode_id, qnode in self.qnodes.items():
            setattr(qnode, 'qnode_id', qnode_id)
            if qnode.category:
                try:
                    qnode.spoke_label = BIOLINK_SPOKE_NODE_MAPPINGS[qnode.category[0]]
                except KeyError:
                    errors.append(
                        f"Node type {qnode.category} not (yet) supported by imProving Agent"
                    )
            # TODO: determine strategy for incoming node CURIE lookup here
            node_map[qnode_id] = qnode  # TODO: don't rebuild dict, just return it

        if len(errors):
            error_string = ", ".join(errors)
            raise BadRequest(error_string)

        return node_map

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
            terminal_nodes = list(self.query_nodes_map.keys())

        # start query order with either of the terminal nodes
        self.query_order = [self.query_nodes_map[terminal_nodes[0]]]
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
                    self.query_order.append(self.query_nodes_map[next_node[0]])
                else:
                    raise MissingComponentError(f"Missing one of {next_node}")

    def query_setup(self):
        # get nodes as dict for later lookup by identifier
        self.query_nodes_map = self.validate_qnodes()
        self.make_query_order()

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
            node = self.knowledge_map['nodes'][knode.id]
            for attribute in node.attributes:
                score_func = IMPROVING_AGENT_SCORING_FUCNTIONS.get(attribute.type)
                if score_func:
                    score += score_func(attribute)

        for kedge in result.edge_bindings.values():
            edge = self.knowledge_map['edges'][kedge.id]
            for attribute in edge.attributes:
                score_func = IMPROVING_AGENT_SCORING_FUCNTIONS.get(attribute.type)
                if score_func:
                    score += score_func(attribute)

        return score

    def score_results(self, results):
        scored_results = []
        for result in results:
            score = self.score_result(result)
            setattr(result, 'improving_agent_score', score)
            scored_results.append(result)
        return scored_results

    def make_result_node(self, n4j_object):
        """Instantiates a reasoner-standard Node to return as part of a
        KnowledgeGraph result

        Parameters
        ----------
        n4j_object (neo4j.types.graph.Node): a `Node` object returned from a
            neo4j.bolt.driver.session Cypher query

        Returns
        -------
        result_node (models.Node): a reasoner-standard `Edge` object for
            inclusion as part of a KnowledgeGraph result
        """
        name = n4j_object.get("pref_name")
        if not name:
            name = n4j_object.get("name")

        result_node = models.Node(
            name=name,
            category=[SPOKE_BIOLINK_NODE_MAPPINGS[label] for label in list(n4j_object.labels)],
        )
        result_node.attributes = [
            # TODO: filter these to something reasonable
            models.Attribute(type=k, value=v) for k, v in n4j_object.items()
        ]
        if "psev-context" in self.query_options:
            try:
                result_node.attributes.append(
                    models.Attribute(
                        type=ATTRIBUTE_TYPE_PSEV_WEIGHT,
                        value=get_psev_weights(
                            node_identifier=n4j_object["identifier"],
                            disease_identifier=self.query_options["psev-context"],
                        ),
                    )
                )
            except IndexError:  # TODO is this really a 0?
                result_node.attributes.append(
                    models.Attribute(type=ATTRIBUTE_TYPE_PSEV_WEIGHT, value=0)
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
            # TODO get correlations score for P100/cohort data
            predicate=SPOKE_BIOLINK_EDGE_MAPPINGS.get(n4j_object.type, 'biolink:Association'),
            relation=n4j_object.type,  # TODO: get the RO CURIE here
            subject=n4j_object.start_node["identifier"],  # TODO: get the proper CURIE here
            object=n4j_object.end_node["identifier"],
        )
        result_edge.attributes = [
            models.Attribute(type=k, value=v) for k, v in n4j_object.items()
        ]
        return result_edge

    def extract_result(self, n4j_result, query_names, query_mapping):
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
        <unnamed> (models.Result): TRAPI Result that can be
            returned to the user/ARS
        """
        # set up objects to collect results and query mappings
        edge_bindings, node_bindings = {}, {}

        # iterate through results and add to result objects
        #
        #
        # This has fundamentally changed. Result.nodes and Result.edges
        # are now Result.node_bindings and Result.edge_bindings and they
        # are now simply lists of Node and EdgeBindings to the single
        # KnowledgeGraph for the entire set of results
        for name in query_names:
            if isinstance(n4j_result[name], neo4j.types.graph.Node):
                # TODO: spoke_curie needs to be normalized -- do this now or later?
                # TODO: figure out the best way to do this for querying efficiency
                spoke_curie = n4j_result[name]['identifier']
                knode_id = self.node_identifier_to_knowledge_map.get(spoke_curie)
                if not knode_id:
                    knode_id = f'kn{self.knowledge_node_counter}'
                    self.knowledge_node_counter += 1
                    self.node_identifier_to_knowledge_map[spoke_curie] = knode_id

                result_node = self.make_result_node(n4j_result[name])
                self.knowledge_map['nodes'][knode_id] = result_node
                node_bindings[query_mapping['nodes'][name]] = models.NodeBinding(knode_id)

            else:
                spoke_edge_id = n4j_result[name].id  # TODO: is there a way to make this consistent?
                edge_bindings[query_mapping['edges'][name]] = models.EdgeBinding(spoke_edge_id)
                result_edge = self.make_result_edge(n4j_result[name])
                self.knowledge_map['edges'][spoke_edge_id] = result_edge

        return models.Result(node_bindings, edge_bindings)

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
        try:
            self.query_setup()
        except (NotImplementedError, MissingComponentError) as e:  # TODO: just raise these and handle outside
            return e

        # spoke diameter is <7 but consider enforcing max query length anyway
        # TODO: get rid of this naming and use the now-available `qedge_id` or `qnode_id` attr
        query_names = "abcdefghijklmn"[: len(self.query_order)]
        query_parts = []
        query_mapping = {"edges": {}, "nodes": {}}
        for query_part, name in zip(self.query_order, query_names):
            query_parts.append(self.get_n4j_str_repr(query_part, name))
            if isinstance(query_part, models.QNode):
                query_mapping["nodes"][name] = query_part.qnode_id
            else:
                query_mapping["edges"][name] = query_part.qedge_id
        query_string = "-".join(query_parts)
        # set max results b/c reasoner-standard default is None
        # possibly enforce a max on the query too
        r = session.run(f"match p = {query_string} " f"return * limit {self.n_results}")

        # create the results
        results = [
            self.extract_result(record, query_names, query_mapping)
            for record in r.records()
        ]

        query_kps = self.query_options.get('query_kps')
        if query_kps == 'true':
            # check KPs for annotations
            cohd = CohdClient()
            tm = TextMinerClient()
            results = cohd.query_for_associations_in_cohd(self.query_order, results)
            results = tm.query_for_associations_in_text_miner(self.query_order, results)

        scored_results = self.score_results(results)
        sorted_scored_results = sorted(scored_results, key=lambda x: x.improving_agent_score, reverse=True)

        if query_kps == 'true':
            # check BigGIM
            big_gim = BigGimClient()
            results = big_gim.annotate_edges_with_biggim(
                session,
                self.query_order,
                sorted_scored_results,
                self.query_options.get("psev-context"),
            )

        return sorted_scored_results, self.knowledge_map
