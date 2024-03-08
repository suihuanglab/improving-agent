from collections import Counter, namedtuple
from typing import Dict, List, Optional, Tuple, Union
from string import ascii_letters

import neo4j
from improving_agent import models  # TODO: replace with direct imports after fixing definitions
from improving_agent.exceptions import MissingComponentError, NonLinearQueryError
from improving_agent.src.biolink.spoke_biolink_constants import (
    BIOLINK_ASSOCIATION_TYPE,
    BIOLINK_ASSOCIATION_RELATED_TO,
    BIOLINK_ENTITY_CHEMICAL_ENTITY,
    BIOLINK_ENTITY_DRUG,
    BIOLINK_ENTITY_GENE,
    BIOLINK_ENTITY_SMALL_MOLECULE,
    BIOLINK_SLOT_HIGHEST_FDA_APPROVAL,
    BIOLINK_SLOT_MAX_RESEARCH_PHASE,
    INFORES_IMPROVING_AGENT,
    KNOWLEDGE_TYPE_LOOKUP,
    KNOWN_UNMAPPED_ATTRS,
    MAX_PHASE_FDA_APPROVAL_MAP,
    PHASE_BL_CT_PHASE_ENUM_MAP,
    QUALIFIERS,
    SPOKE_ANY_TYPE,
    SPOKE_BIOLINK_EDGE_MAPPINGS,
    SPOKE_BIOLINK_EDGE_ATTRIBUTE_MAPPINGS,
    SPOKE_BIOLINK_NODE_MAPPINGS,
    SPOKE_BIOLINK_NODE_ATTRIBUTE_MAPPINGS,
    SPOKE_LABEL_COMPOUND,
    SPOKE_PROPERTY_NATIVE_SPOKE,
)
from improving_agent.src.constraints import get_node_constraint_cypher_clause
from improving_agent.src.improving_agent_constants import (
    ATTRIBUTE_TYPE_PSEV_WEIGHT,
    SPOKE_NODE_PROPERTY_SOURCE
)
from improving_agent.src.kps.biggim import annotate_edges_with_biggim
from improving_agent.src.kps.cohd import annotate_edges_with_cohd
# from improving_agent.src.kps.text_miner import TextMinerClient
from improving_agent.src.normalization import SearchNode
from improving_agent.src.normalization.node_normalization import normalize_spoke_nodes_for_translator
from improving_agent.src.provenance import (
    make_publications_attribute,
    make_retrieval_sources,
    SPOKE_PROVENANCE_FIELDS,
    SPOKE_PUBLICATION_FIELDS,
)
from improving_agent.src.psev import get_psev_scores
from improving_agent.src.result_handling import (
    resolve_epc_kl_at,
    get_edge_qualifiers,
)
from improving_agent.src.scoring.scoring_utils import normalize_results_scores
from improving_agent.util import get_evidara_logger

logger = get_evidara_logger(__name__)
ExtractedResult = namedtuple('ExtractedResult', ['nodes', 'edges'])

# attributes
SPOKE_GRAPH_TYPE_EDGE = 'edge'
SPOKE_GRAPH_TYPE_NODE = 'node'
ATTRIBUTE_MAPS = {
    SPOKE_GRAPH_TYPE_EDGE: SPOKE_BIOLINK_EDGE_ATTRIBUTE_MAPPINGS,
    SPOKE_GRAPH_TYPE_NODE: SPOKE_BIOLINK_NODE_ATTRIBUTE_MAPPINGS
}

# grouped constants
SUPPORTED_COMPOUND_CATEGORIES = [
    BIOLINK_ENTITY_CHEMICAL_ENTITY,
    BIOLINK_ENTITY_DRUG,
    BIOLINK_ENTITY_SMALL_MOLECULE,
]

# what follows is (hopefully) temporary handling of "special" attributes,
# e.g. max phase transformation to biolink's highest fda approval enums
SPECIAL_ATTRIBUTE_HANDLERS = {}


def register_special_attribute_handler(attribute_name):
    def wrapper(f):
        SPECIAL_ATTRIBUTE_HANDLERS[attribute_name] = f
        return f
    return wrapper


# max phase for nodes
@register_special_attribute_handler(BIOLINK_SLOT_HIGHEST_FDA_APPROVAL)
def _map_max_phase_to_fda_approval(property_value):
    return MAX_PHASE_FDA_APPROVAL_MAP[property_value]

# phase for edges
@register_special_attribute_handler(BIOLINK_SLOT_MAX_RESEARCH_PHASE)
def _map_max_phase_to_fda_approval(property_value):
    return PHASE_BL_CT_PHASE_ENUM_MAP[property_value]


def _transform_special_attributes(slot_type, property_value):
    '''Returns a transformed property name and value if biolink
    compliance requires it.

    Parameters
    ----------
    slot_type (str): the name of the property (biolink slot)
    property_value (str, list(str), int, float): the value of the property

    Returns
    -------
    property_value (str, list(str), int, float): the updated value, if necessary
    '''
    attr_transformer = SPECIAL_ATTRIBUTE_HANDLERS.get(slot_type)
    if attr_transformer:
        return attr_transformer(property_value)
    return property_value


# scoring
IMPROVING_AGENT_SCORING_FUCNTIONS = {}


def register_scoring_function(attribute_name):
    def wrapper(f):
        IMPROVING_AGENT_SCORING_FUCNTIONS[attribute_name] = f
        return f
    return wrapper


@register_scoring_function('cohd_paired_concept_freq_concept_frequency')
def get_cohd_edge_score(value):
    return value * 1000


@register_scoring_function('has_feature_importance')
def get_multiomics_model_score(value):
    return value


@register_scoring_function(ATTRIBUTE_TYPE_PSEV_WEIGHT)
def get_psev_score(value):
    return value * 10000


@register_scoring_function('spearman_correlation')
def get_evidential_score(value):
    return value


@register_scoring_function('text_miner_max_ngd_for_sub_obj')
def get_text_miner_score(value):
    return value


# Cypher
def make_qnode_filter_clause(name, query_node):
    labels_clause = ''
    if query_node.spoke_labels:
        if SPOKE_ANY_TYPE not in query_node.spoke_labels:
            labeled_names = [f'{name}:{label}' for label in query_node.spoke_labels]
            labels_clause = f'({" OR ".join(labeled_names)})'

    identifiers_clause = ''
    if query_node.spoke_identifiers:
        spoke_search_ids = list(query_node.spoke_identifiers.keys())
        identifiers_clause = f'{name}.identifier IN [{",".join(spoke_search_ids)}]'
        # TODO: this will quickly become untenable as we add better querying
        # and we'll need specific funcs; see also drug below
        if SPOKE_LABEL_COMPOUND in query_node.spoke_labels:
            identifiers_clause = f'({identifiers_clause} OR {name}.chembl_id IN [{",".join(spoke_search_ids)}])'
    if query_node.categories:
        if (
            BIOLINK_ENTITY_DRUG in query_node.categories
            and BIOLINK_ENTITY_CHEMICAL_ENTITY not in query_node.categories
            and BIOLINK_ENTITY_SMALL_MOLECULE not in query_node.categories
        ):
            if identifiers_clause:
                identifiers_clause = f'{identifiers_clause} AND'
            identifiers_clause = f'{identifiers_clause} {name}.max_phase > 0'

    constraints_clause = ''
    if query_node.constraints:
        constraints_clause = ' AND '.join([
            get_node_constraint_cypher_clause(query_node, name, constraint)
            for constraint
            in query_node.constraints
        ])

    filter_clause = ' AND '.join([
        clause for clause
        in (labels_clause, identifiers_clause, constraints_clause)
        if clause
    ])

    if filter_clause:
        return f'({filter_clause})'

    return ''


def make_qedge_cypher_repr(name, query_edge):
    edge_repr = f'[{name}'
    if SPOKE_ANY_TYPE not in query_edge.spoke_edge_types:
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
    def __init__(
        self,
        qnodes,
        qedges,
        query_options={},
        n_results=200,
        query_type=KNOWLEDGE_TYPE_LOOKUP,
    ):
        """Instantiates a new BasicQuery object"""
        self.qnodes = qnodes
        self.qedges = qedges
        self.query_options = query_options
        self.n_results = n_results
        self.query_type = query_type

        self.knowledge_graph = {"edges": {}, "nodes": {}}
        self.knowledge_node_counter = 0
        self.knowledge_edge_counter = 0

        self.nodes_to_normalize = set()
        self.result_nodes_spoke_identifiers = set()
        self.results = []

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
        try:
            self.query_order = [self.qnodes[terminal_nodes[0]]]
        except IndexError:
            raise NonLinearQueryError('imProving Agent currently only supports linear queries')

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
        self.query_names = list(ascii_letters[: len(self.query_order)])
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

        match_clause = f'MATCH path={"-".join(query_parts)}'
        where_clause = ''
        if node_filter_clauses:
            where_clause = f'WHERE {" AND ".join(node_filter_clauses)}'
        return_clause = f'RETURN * limit {self.n_results}'

        return f'{match_clause} {where_clause} {return_clause};'

    # Result handling
    def _get_psev_scores(
        self,
        psev_contexts: List[str]
    ) -> Dict[str, Dict[Union[str, int], float]]:
        """Query the PSEV API to get scores for all nodes and contexts

        Eventually this will "intelligently" figure out concepts if they
        are not defined, but that algorithm remains to be developed.
        """
        # TODO: find reasonable concepts when no concepts are given
        if not psev_contexts:
            return {'no-concepts': {si: 0 for si in self.result_nodes_spoke_identifiers}}
        if psev_contexts and isinstance(psev_contexts, str):
            psev_contexts = [psev_contexts]
        psev_scores = get_psev_scores(psev_contexts, self.result_nodes_spoke_identifiers)
        return psev_scores

    def score_result(
        self,
        result: 'models.Result',
        psev_scores: Dict[str, Dict[Union[str, int], float]]
    ):
        """Returns a score based on psev weights, cohort edge correlations,
            both, or none

        Parameters
        ----------
        result (Result): TRAPI Result object containing node_bindings
            and edge_bindings,
        psev_scores: psev scores for all result nodes for all conepts
            related to the query

        Returns
        -------
        scores (dict): mapping of score (str) -> float and
            score name (str) -> str

        NOTE: currently for linear queries, all knowledge graphs are of the
            length, but dividing the sum score by `n` may make sense in the
            future
        """
        score = 0
        psev_context = self.query_options.get('psev_context')

        for knode in result.node_bindings.values():
            # knode is a list of node_bindings, but we only support
            # one, so index at 0
            # TODO: reconsider upon version upgrade
            node = self.knowledge_graph['nodes'][knode[0].id]
            for attribute in node.attributes:
                attribute_name = attribute.original_attribute_name
                value = attribute.value
                # first lookup psev if possible
                if psev_context and attribute_name == 'identifier':
                    attribute_name = 'psev'
                    # iterate on all PSEV concepts and sum the
                    # psev value for the node of interest across all
                    # conepts
                    psev_sum = 0
                    for concept in psev_scores:
                        psev_sum += psev_scores[concept].get(value, 0.0)
                    value = psev_sum
                score_func = IMPROVING_AGENT_SCORING_FUCNTIONS.get(attribute_name)
                if score_func:
                    score += score_func(value)

        for kedge in result.analyses[0].edge_bindings.values():
            # kedge is a list of node_bindings, but we only support
            # one, so index at 0
            # TODO: reconsider upon version upgrade
            edge = self.knowledge_graph['edges'][kedge[0].id]
            for attribute in edge.attributes:
                score_func = IMPROVING_AGENT_SCORING_FUCNTIONS.get(attribute.original_attribute_name)
                if score_func:
                    score += score_func(attribute.value)
        return score

    def score_results(self, results):
        scored_results = []
        psev_concepts = self.query_options.get('psev_context')
        psev_scores = self._get_psev_scores(psev_concepts)
        for result in results:
            result.analyses[0].score = self.score_result(result, psev_scores)
            scored_results.append(result)
        return scored_results

    def _make_result_attribute(
        self,
        property_type,
        property_value,
        edge_or_node,
        spoke_object_type
    ):
        """Returns a TRAPI-spec attribute for a result node or edge

        Parameters
        ----------
        property_type: the neo4j-SPOKE property type
        property_value: the value of the property
        edge_or_node: string 'edge' or 'node' specifiying the type of
            graph object that is described by this attributee
        spoke_object_type: the neo4j node label or edge type from SPOKE

        Returns
        -------
        models.Attribute or None
        """
        if edge_or_node not in ATTRIBUTE_MAPS:
            raise ValueError(
                f'Got {edge_or_node=} but it must be one of "edge" or "node"'
            )
        
        if property_type in KNOWN_UNMAPPED_ATTRS:
            return

        if property_type in SPOKE_PUBLICATION_FIELDS:
            return make_publications_attribute(property_type, property_value)

        object_properties = ATTRIBUTE_MAPS[edge_or_node].get(spoke_object_type)
        if not object_properties:
            logger.warning(
                f'Could not find any properties in the attribute map for {spoke_object_type=}'
            )
            return

        attribute_mapping = object_properties.get(property_type)
        if not attribute_mapping:
            logger.warning(
                f'Could not find an attribute mapping for {spoke_object_type=} and {property_type=}'
            )
            return
        attribute_type_id = attribute_mapping.biolink_type
        property_value = _transform_special_attributes(attribute_type_id, property_value)

        attribute = models.Attribute(
            attribute_type_id=attribute_type_id,
            original_attribute_name=property_type,
            value=property_value
        )
        if attribute_mapping.attribute_source:  # temporary until node mappings are done
            attribute.attribute_source = attribute_mapping.attribute_source

        if attribute_mapping.attributes:
            attribute.attributes = attribute_mapping.attributes
        return attribute

    def make_result_node(self, n4j_object, spoke_curie):
        """Instantiates a reasoner-standard Node to return as part of a
        KnowledgeGraph result

        Parameters
        ----------
        n4j_object (neo4j.graph.Node): a `Node` object returned from a
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

        spoke_node_labels = list(n4j_object.labels)
        result_node_categories = [
            SPOKE_BIOLINK_NODE_MAPPINGS[label]
            for label
            in spoke_node_labels
        ]

        node_source = None
        result_node_attributes = []
        for k, v in n4j_object.items():
            if k == SPOKE_PROPERTY_NATIVE_SPOKE:
                continue
            if k == SPOKE_NODE_PROPERTY_SOURCE:
                node_source = v
            node_attribute = self._make_result_attribute(
                k, v, SPOKE_GRAPH_TYPE_NODE, spoke_node_labels[0]
            )
            if node_attribute:
                result_node_attributes.append(node_attribute)

        result_node = models.Node(
            name=name,
            categories=result_node_categories,
            attributes=result_node_attributes
        )

        # set up downstream searches
        self.result_nodes_spoke_identifiers.add(spoke_curie)  # for PSEV retrieval

        # for normalization
        search_node = SearchNode(result_node.categories[0], spoke_curie, node_source)
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
        edge_type = n4j_object.type
        biolink_map_info = SPOKE_BIOLINK_EDGE_MAPPINGS.get(edge_type)
        if not biolink_map_info:
            predicate = BIOLINK_ASSOCIATION_RELATED_TO
        else:
            qualifiers = biolink_map_info.get(QUALIFIERS)
            if qualifiers:
                qualifiers = get_edge_qualifiers(qualifiers)
            predicate = biolink_map_info[BIOLINK_ASSOCIATION_TYPE]

        edge_attributes = []
        provenance_retrieval_sources = []
        for k, v in n4j_object.items():
            if k == SPOKE_PROPERTY_NATIVE_SPOKE:
                continue
            if k in SPOKE_PROVENANCE_FIELDS:
                retrieval_sources = make_retrieval_sources(k, v)
                provenance_retrieval_sources.extend(retrieval_sources)
                continue
            edge_attribute = self._make_result_attribute(k, v, SPOKE_GRAPH_TYPE_EDGE, edge_type)
            if edge_attribute:
                if isinstance(edge_attribute, list):
                    edge_attributes.extend(edge_attribute)
                else:
                    edge_attributes.append(edge_attribute)

        updated_predicate, attrs, sources = resolve_epc_kl_at(
            edge_type,
            edge_attributes,
            provenance_retrieval_sources,
            self.query_type,
        )
        if updated_predicate is not None:
            predicate = updated_predicate

        result_edge = models.Edge(
            attributes=attrs,
            object=n4j_object.end_node["identifier"],
            predicate=predicate,
            qualifiers=qualifiers,
            sources=sources,
            subject=n4j_object.start_node["identifier"],
        )

        return result_edge

    def find_query_id(self, query_name, spoke_curie, result_node):
        qnode_id = self.query_mapping["nodes"][query_name]
        qnode = self.qnodes[qnode_id]
        if not qnode.ids:
            return None

        query_id = None
        if any(i in result_node.categories for i in SUPPORTED_COMPOUND_CATEGORIES):
            drugbank_id, chembl_id = None, None
            for attribute in result_node.attributes:
                if attribute.original_attribute_name == 'drugbank_id':
                    drugbank_id = attribute.value
                    continue
                if attribute.original_attribute_name == 'chembl_id':
                    chembl_id = attribute.value
            for identifier in [spoke_curie, drugbank_id, chembl_id]:
                query_id = qnode.spoke_identifiers.get(f"'{identifier}'")
                if query_id:
                    break

        elif BIOLINK_ENTITY_GENE in result_node.categories:
            # don't double quote
            query_id = qnode.spoke_identifiers.get(f"{spoke_curie}")
        else:
            query_id = qnode.spoke_identifiers.get(f"'{spoke_curie}'")

        return query_id

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
            if isinstance(n4j_result[name], neo4j.graph.Node):
                spoke_curie = n4j_result[name]['identifier']
                result_node = self.make_result_node(n4j_result[name], spoke_curie)
                self.knowledge_graph['nodes'][spoke_curie] = result_node

                # get query_id for mapping this node back to a specific
                # CURIE on a QNode's ids
                query_id = self.find_query_id(name, spoke_curie, result_node)
                node_bindings[self.query_mapping['nodes'][name]] = models.NodeBinding(
                    spoke_curie, query_id
                )

            else:
                # these are ints, but we want them as strings for TRAPI spec
                spoke_edge_id = str(n4j_result[name].id)  # TODO: is there a way to make this consistent?
                edge_bindings[self.query_mapping['edges'][name]] = [models.EdgeBinding(spoke_edge_id)]
                result_edge = self.make_result_edge(n4j_result[name])
                self.knowledge_graph['edges'][spoke_edge_id] = result_edge
                result_analysis = models.Analysis(
                    resource_id=INFORES_IMPROVING_AGENT.infores_id,
                    edge_bindings=edge_bindings,
                )

        return models.Result(node_bindings, [result_analysis])

    # normalization
    def normalize(self):
        # search the node normalizer for nodes collected in result creation
        node_search_results = normalize_spoke_nodes_for_translator(self.nodes_to_normalize)
        for spoke_curie, normalized_curie in node_search_results.items():
            self.knowledge_graph['nodes'][normalized_curie] = self.knowledge_graph['nodes'].pop(spoke_curie)

        for edge in self.knowledge_graph['edges'].values():
            setattr(edge, 'object', node_search_results[edge.object])
            setattr(edge, 'subject', node_search_results[edge.subject])

        new_results = []
        for result in self.results:
            new_node_bindings = {}
            for qnode, node in result.node_bindings.items():
                normalized_node_id = node_search_results[node.id]
                if node.query_id == normalized_node_id:
                    node.query_id = None
                new_node_bindings[qnode] = [models.NodeBinding(normalized_node_id, node.query_id)]
            new_results.append(models.Result(new_node_bindings, result.analyses))

        self.results = new_results

    def run_query(self, tx, query_string):
        r = tx.run(query_string)
        self.results = [self.extract_result(record) for record in r]

    # Query
    def do_query(
        self,
        session: neo4j.Session,
        norm_scores: bool = True,
    ) -> Tuple[List[models.Result], models.KnowledgeGraph, List[Optional[str]]]:
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
        session.read_transaction(self.run_query, query_string)

        if not self.results:
            return self.results, self.knowledge_graph, []

        # normalize the knowledge_graph and results
        self.normalize()

        # query kps
        query_kps = self.query_options.get('query_kps')
        if query_kps:
            # check KPs for annotations
            self.knowledge_graph['edges'] = annotate_edges_with_cohd(self.knowledge_graph)
        #     self.results = tm.query_for_associations_in_text_miner(self.query_order, self.results)

        scored_results = self.score_results(self.results)
        if norm_scores is True:
            scored_results = normalize_results_scores(scored_results)
        sorted_scored_results = sorted(scored_results, key=lambda x: x.analyses[0].score, reverse=True)

        if query_kps:
            # check BigGIM
            self.knowledge_graph['edges'] = annotate_edges_with_biggim(
                session,
                self.query_order,
                self.knowledge_graph['edges'],
                sorted_scored_results,
                self.query_options.get("psev_context"),
            )

        return sorted_scored_results, self.knowledge_graph, {}
