"""The code herein handles four cases of the generic query
compound affects gene. In two, the gene is known, whereas the compound
is known in the other two.
"""
from copy import deepcopy
from random import randint
from typing import Any, Tuple

from .template_query_base import template_matches_inferred_one_hop, TemplateQueryBase
from improving_agent.models.attribute import Attribute
from improving_agent.models.auxiliary_graph import AuxiliaryGraph
from improving_agent.models.edge import Edge
from improving_agent.models.edge_binding import EdgeBinding
from improving_agent.models.node_binding import NodeBinding
from improving_agent.models.q_edge import QEdge
from improving_agent.models.q_node import QNode
from improving_agent.src.basic_query import BasicQuery
from improving_agent.src.biolink.spoke_biolink_constants import (
    BIOLINK_ASSOCIATION_AFFECTS,
    BIOLINK_ASSOCIATION_REGULATES,
    BIOLINK_ENTITY_CHEMICAL_ENTITY,
    BIOLINK_ENTITY_GENE,
    BIOLINK_SLOT_SUPPORT_GRAPHS,
    BL_QUALIFIER_DIRECTION_DECREASED,
    BL_QUALIFIER_DIRECTION_INCREASED,
    INFORES_IMPROVING_AGENT,
    SPOKE_EDGE_TYPE_DOWNREGULATES_CdG,
    SPOKE_EDGE_TYPE_DOWNREGULATES_GPdG,
    SPOKE_EDGE_TYPE_DOWNREGULATES_KGdG,
    SPOKE_EDGE_TYPE_DOWNREGULATES_OGdG,
    SPOKE_EDGE_TYPE_UPREGULATES_CuG,
    SPOKE_EDGE_TYPE_UPREGULATES_GPuG,
    SPOKE_EDGE_TYPE_UPREGULATES_KGuG,
    SPOKE_EDGE_TYPE_UPREGULATES_OGuG,
)
from improving_agent.src.provenance import make_internal_retrieval_source
from improving_agent.src.scoring.scoring_utils import normalize_results_scores
from improving_agent.util import get_evidara_logger


logger = get_evidara_logger(__name__)

DECREASE_EXPRESSION_EDGE_COMBOS = {
    SPOKE_EDGE_TYPE_DOWNREGULATES_CdG: [
        SPOKE_EDGE_TYPE_DOWNREGULATES_KGdG,
        SPOKE_EDGE_TYPE_UPREGULATES_GPuG,
        SPOKE_EDGE_TYPE_UPREGULATES_OGuG,
    ],
    SPOKE_EDGE_TYPE_UPREGULATES_CuG: [
        SPOKE_EDGE_TYPE_DOWNREGULATES_GPdG,
        SPOKE_EDGE_TYPE_DOWNREGULATES_OGdG,
        SPOKE_EDGE_TYPE_UPREGULATES_KGuG,
    ],
}

INCREASE_EXPRESSION_EDGE_COMBOS = {
    SPOKE_EDGE_TYPE_DOWNREGULATES_CdG: [
        SPOKE_EDGE_TYPE_DOWNREGULATES_GPdG,
        SPOKE_EDGE_TYPE_DOWNREGULATES_OGdG,
        SPOKE_EDGE_TYPE_UPREGULATES_KGuG,
    ],
    SPOKE_EDGE_TYPE_UPREGULATES_CuG: [
        SPOKE_EDGE_TYPE_DOWNREGULATES_KGdG,
        SPOKE_EDGE_TYPE_UPREGULATES_GPuG,
        SPOKE_EDGE_TYPE_UPREGULATES_OGuG,
    ],
}

DIRECTION_COMBO_MAP = {
    BL_QUALIFIER_DIRECTION_DECREASED: DECREASE_EXPRESSION_EDGE_COMBOS,
    BL_QUALIFIER_DIRECTION_INCREASED: INCREASE_EXPRESSION_EDGE_COMBOS,
}


def template_matches_compound_gene_template(
    qedges: dict[Any],
    qnodes: dict[Any],
) -> bool:
    """Returns bool whether the input TRAPI query matches the templates
    supported in this module
    """
    format_match = template_matches_inferred_one_hop(
        qedges,
        qnodes,
        [BIOLINK_ENTITY_CHEMICAL_ENTITY],
        [BIOLINK_ENTITY_GENE],
        [BIOLINK_ASSOCIATION_AFFECTS]
    )
    if format_match is False:
        return False

    # note the above func checks that we only have one edge
    qedge = list(qedges.values())[0]
    qualifier_constraints = qedge.qualifier_constraints
    if not qualifier_constraints:
        return False
    found_abundance_and_direction = False
    for qualifier_constraint in qualifier_constraints:
        for qualifier_set in qualifier_constraint.values():
            found_abundance = False
            found_direction = False
            for qualifier in qualifier_set:
                if qualifier['qualifier_type_id'] == 'biolink:object_aspect_qualifier':
                    if qualifier['qualifier_value'] == 'activity_or_abundance':
                        found_abundance = True
                if qualifier['qualifier_type_id'] == 'biolink:object_direction_qualifier':
                    if qualifier['qualifier_value'] in (
                        BL_QUALIFIER_DIRECTION_DECREASED,
                        BL_QUALIFIER_DIRECTION_INCREASED,
                    ):
                        found_direction = True
                if found_abundance is True and found_direction is True:
                    found_abundance_and_direction = True
    if found_abundance_and_direction is False:
        return False

    subject_ids = qnodes[qedge.subject].ids or []
    object_ids = qnodes[qedge.object].ids or []

    if len(subject_ids) == 0 and len(object_ids) == 0:
        return False
    if len(subject_ids) == 1:
        if len(object_ids) != 0:
            return False
    if len(object_ids) == 1:
        if len(subject_ids) != 0:
            return False

    return True


class CompoundAffectsWhichGenes(TemplateQueryBase):
    """Answers the queries
    (known) compound increases abundance of genes
    (known) compound decreases abundance of genes
    """
    template_query_name = 'compound -- may affect -- genes'

    def __init__(self):
        pass

    @staticmethod
    def matches_template(qedges, qnodes):
        return template_matches_compound_gene_template(
            qedges,
            qnodes,
        )


class CompoundAffectsGene(TemplateQueryBase):
    """Answers the queries
    (known) compound increases abundance of genes
    (known) compound decreases abundance of genes
    compounds increase abundance of (known) gene
    compounds decrease abundance of (known) gene
    """
    template_query_name = 'compound -- affects -- gene'

    def __init__(self, qnodes, qedges, query_options, max_results):
        # query config
        self.qnodes = qnodes
        self.qedges = qedges
        self.query_options = query_options
        self.max_results = max_results

        # convenience references
        self.edge_id_affects = list(self.qedges.keys())[0]
        self.node_id_compound = self.qedges[self.edge_id_affects].subject
        self.node_id_gene = self.qedges[self.edge_id_affects].object

        # results
        self.knowledge_graph = None

    @staticmethod
    def matches_template(qedges, qnodes):
        return template_matches_compound_gene_template(
            qedges,
            qnodes,
        )

    def _make_new_inferred_edge(
        self,
        i: int,
        j: int,
        aux_graph_id: str,
        node_bindings: dict[str: list[NodeBinding]],
    ) -> Tuple[str, Edge]:
        """Returns an identifier and new inferred edge between the query's
        original subject and object
        """
        retrieval_source = make_internal_retrieval_source([], INFORES_IMPROVING_AGENT)
        supporting_edges_attr = Attribute(
            attribute_source=INFORES_IMPROVING_AGENT,
            attribute_type_id=BIOLINK_SLOT_SUPPORT_GRAPHS,
            value=[aux_graph_id],
        )

        object_id = node_bindings[self.node_id_gene][0].id
        subject_id = node_bindings[self.node_id_compound][0].id
        new_edge = Edge(
            attributes=[supporting_edges_attr],
            object=object_id,
            predicate=BIOLINK_ASSOCIATION_AFFECTS,
            qualifiers=self.qedges[self.edge_id_affects].qualifier_constraints,
            subject=subject_id,
            sources=[retrieval_source],
        )
        return f'inferred_edge_{i}-{j}', new_edge

    def do_query(self, session):
        """Returns results from three subsequent BasicQueries: known
        results and expanded two hops to ask conceptually the
        same question via an additional Gene node
        """
        logger.info(f'Doing query {self.template_query_name}')

        # First, do a one hop for known results
        one_hop_query = BasicQuery(
            self.qnodes,
            self.qedges,
            self.query_options,
            self.max_results,
        )
        results, knowledge_graph, _ = one_hop_query.do_query(session, norm_scores=False)

        count_to_get = self.max_results - len(results)
        if count_to_get == 0:
            return results, knowledge_graph, {}

        # we have fewer than the max requested results, so we do a
        # second query.
        two_hop_qnodes = deepcopy(self.qnodes)
        i_gene_qnode_id = f'intermediate_gene_{randint(10000, 99999)}'
        intermediate_node = QNode(
            categories=['biolink:Gene']
        )
        setattr(QNode, 'spoke_labels', ['Gene'])
        setattr(QNode, 'spoke_identifiers', [])
        setattr(QNode, 'qnode_id', i_gene_qnode_id)
        two_hop_qnodes[i_gene_qnode_id] = intermediate_node

        # determine the directionality of the "affects"
        qedge_qualifiers = self.qedges[self.edge_id_affects].qualifier_constraints
        affects_direction = None
        for qedge_qualifier in qedge_qualifiers:
            for qualifier_set in qedge_qualifier.values():
                activity_or_abundance = False
                direction = None
                for qualifier in qualifier_set:
                    if qualifier['qualifier_type_id'] == 'biolink:object_aspect_qualifier':
                        if qualifier['qualifier_value'] != 'biolink:activity_or_abundance':
                            activity_or_abundance = True
                    if qualifier['qualifier_type_id'] == 'biolink:object_direction_qualifier':
                        direction = qualifier['qualifier_value']
                if activity_or_abundance is True and direction is not None:
                    affects_direction = direction

        compound_igene_edge = QEdge(
            subject=self.node_id_compound,
            object=i_gene_qnode_id,
            predicates=[
                BIOLINK_ASSOCIATION_AFFECTS
            ]
        )
        setattr(compound_igene_edge, 'qedge_id', 'compound-igene')

        igene_gene_edge = QEdge(
            subject=i_gene_qnode_id,
            object=self.node_id_gene,
            predicates=[
                BIOLINK_ASSOCIATION_REGULATES
            ]
        )
        setattr(igene_gene_edge, 'qedge_id', 'igene-gene')

        # do subsequent queries with the different combinations of edges
        # that result in the desired direction
        edge_combos = DIRECTION_COMBO_MAP.get(affects_direction)
        if not edge_combos:
            logger.warn(f'An unconfigured direction was received: {affects_direction=}')
            return results, knowledge_graph, {}

        result_sets = []
        for predicate_edge_1, predicates_edge_2 in edge_combos.items():
            setattr(compound_igene_edge, 'spoke_edge_types', [predicate_edge_1])
            setattr(igene_gene_edge, 'spoke_edge_types', predicates_edge_2)
            two_hop_querier = BasicQuery(
                qnodes=two_hop_qnodes,
                qedges={
                    compound_igene_edge.qedge_id: compound_igene_edge,
                    igene_gene_edge.qedge_id: igene_gene_edge,
                },
                query_options=self.query_options,
                n_results=count_to_get,
            )
            _results, _knowledge_graph, _ = two_hop_querier.do_query(session, norm_scores=False)

            result_sets.append((_results, _knowledge_graph))

        # resolve the kgs
        # add a prefix to the edge names in the results and the kg
        _nodes = {}
        _edges = {}
        _results = []
        _aux_graphs = {}
        for i, (_r, _kg) in enumerate(result_sets):
            _nodes |= {**_kg['nodes']}

            for j, result in enumerate(_r):

                # make the aux graphs
                aux_graph_edges = []
                for bindings in result.analyses[0].edge_bindings.values():
                    for binding in bindings:
                        # new binding id created below as well
                        updated_edge_id = f'{binding.id}-i{i}'
                        aux_graph_edges.append(updated_edge_id)
                        _edges[updated_edge_id] = _kg['edges'][binding.id]

                aux_graph_id = f'ag_{i}_{j}'
                _aux_graphs[aux_graph_id] = AuxiliaryGraph(edges=aux_graph_edges)

                # make a new inferred edge and add it to the kg
                new_edge_id, new_inferred_edge = self._make_new_inferred_edge(
                    i, j, aux_graph_id, result.node_bindings,
                )
                _edges[new_edge_id] = new_inferred_edge

                # update the results
                result.analyses[0].support_graphs = [aux_graph_id]

                if result.analyses[0].score:
                    result.analyses[0].score = result.analyses[0].score / 2  # penalize

                result.analyses[0].edge_bindings = {
                    self.edge_id_affects: [EdgeBinding(id=new_edge_id)]
                }

                _results.append(result)

        two_hop_results = sorted(_results, key=lambda x: x.analyses[0].score, reverse=True)[:count_to_get]
        two_hop_knowledge_graph = {'edges': {}, 'nodes': {}}
        two_hop_aux_graphs = {}
        for two_hop_result in two_hop_results:
            for edge_binding in two_hop_result.analyses[0].edge_bindings.values():
                for edge in edge_binding:
                    two_hop_knowledge_graph['edges'][edge.id] = _edges[edge.id]

            for supporting_graph in two_hop_result.analyses[0].support_graphs:
                two_hop_aux_graphs[supporting_graph] = _aux_graphs[supporting_graph]
                for aux_edge_id in _aux_graphs[supporting_graph].edges:
                    two_hop_knowledge_graph['edges'][aux_edge_id] = _edges[aux_edge_id]

            for node_binding in two_hop_result.node_bindings.values():
                for node in node_binding:
                    two_hop_knowledge_graph['nodes'][node.id] = _nodes[node.id]

        results.extend(two_hop_results)
        results = normalize_results_scores(results)
        knowledge_graph['nodes'] |= two_hop_knowledge_graph['nodes']
        knowledge_graph['edges'] |= two_hop_knowledge_graph['edges']

        return results, knowledge_graph, two_hop_aux_graphs
