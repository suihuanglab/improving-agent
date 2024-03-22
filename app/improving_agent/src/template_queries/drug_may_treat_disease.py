from .template_query_base import template_matches_inferred_one_hop, TemplateQueryBase
from improving_agent.models import (
    Analysis,
    Attribute,
    AuxiliaryGraph,
    Edge,
    EdgeBinding,
    KnowledgeGraph,
    NodeBinding,
    Result,
)
from improving_agent.exceptions import TemplateQuerySpecError, UnmatchedIdentifierError
from improving_agent.src.basic_query import BasicQuery
from improving_agent.src.biolink.spoke_biolink_constants import (
    BIOLINK_ASSOCIATION_IN_CLINICAL_TRIALS_FOR,
    BIOLINK_ASSOCIATION_TREATS,
    BIOLINK_ENTITY_SMALL_MOLECULE,
    BIOLINK_ENTITY_DISEASE,
    BIOLINK_SLOT_AGENT_TYPE,
    BIOLINK_SLOT_KNOWLEDGE_LEVEL,
    BIOLINK_SLOT_SUPPORT_GRAPHS,
    INFORES_IMPROVING_AGENT,
    INFORES_SPOKE,
    SPOKE_LABEL_COMPOUND,
    SPOKE_LABEL_DISEASE,
    TRAPI_AGENT_TYPE_ENUM_MANUAL_AGENT,
    TRAPI_KNOWLEDGE_LEVEL_PREDICTION,
    TRAPI_KNOWLEDGE_LEVEL_STATISTICAL_ASSOCIATION,
)
from improving_agent.src.normalization.edge_normalization import SUPPORTED_INFERRED_DRUG_SUBJ
from improving_agent.src.normalization.node_normalization import (
    format_curie_for_sri,
    normalize_spoke_nodes_for_translator,
)
from improving_agent.src.provenance import make_internal_retrieval_source
from improving_agent.src.psev import get_psev_scores
from improving_agent.src.scoring.scoring_utils import normalize_results_scores
from improving_agent.util import get_evidara_logger

logger = get_evidara_logger(__name__)

CYPHER_COMPOUND_SEARCH = """
    MATCH (c:Compound)
    WHERE c.identifier in $identifiers
    RETURN c
"""

CYPHER_DISEASE_SEARCH = """
    MATCH (c:Disease)
    WHERE c.identifier in $identifiers
    RETURN c
"""


def _extract_node_result(record, querier):
    node_info = record['c']
    identifier = node_info['identifier']
    result_node = querier.make_result_node(node_info, identifier)
    return identifier, result_node


def _compound_search(tx, identifiers, querier):
    records = tx.run(CYPHER_COMPOUND_SEARCH, identifiers=identifiers)
    result_nodes = {}
    for record in records:
        identifier, result_node = _extract_node_result(record, querier)
        result_nodes[identifier] = result_node
    return result_nodes


def _disease_search(tx, identifiers, querier):
    records = tx.run(CYPHER_DISEASE_SEARCH, identifiers=identifiers)
    result_nodes = {}
    for record in records:
        identifier, result_node = _extract_node_result(record, querier)
        result_nodes[identifier] = result_node
    return result_nodes


class DrugMayTreatDisease(TemplateQueryBase):
    template_query_name = 'Drug -- may treat -- Disease'

    # TODO: abstract if possible once other templates are known
    def __init__(self, qnodes, qedges, query_options, max_results):
        # query config
        self.qnodes = qnodes
        self.qedges = qedges
        self.query_options = query_options
        self.max_results = max_results

        # convenience references
        self.edge_id_treats = list(self.qedges.keys())[0]
        self.node_id_compound = self.qedges[self.edge_id_treats].subject
        self.node_id_disease = self.qedges[self.edge_id_treats].object

        # results
        self.knowledge_graph = None

    @staticmethod
    def matches_template(qedges, qnodes):
        return template_matches_inferred_one_hop(
            qedges,
            qnodes,
            SUPPORTED_INFERRED_DRUG_SUBJ,
            [BIOLINK_ENTITY_DISEASE],
            [BIOLINK_ASSOCIATION_TREATS],
        )

    def make_result_edge(
        self,
        subj_id: str,
        obj_id: str,
        aux_graph_id: str
    ):
        attributes = [
            Attribute(
                attribute_source=INFORES_IMPROVING_AGENT.infores_id,
                attribute_type_id=BIOLINK_SLOT_SUPPORT_GRAPHS,
                value=[aux_graph_id],
            ),
            Attribute(
                attribute_source=INFORES_IMPROVING_AGENT.infores_id,
                attribute_type_id=BIOLINK_SLOT_AGENT_TYPE,
                value=TRAPI_AGENT_TYPE_ENUM_MANUAL_AGENT,
            ),
            Attribute(
                attribute_source=INFORES_IMPROVING_AGENT.infores_id,
                attribute_type_id=BIOLINK_SLOT_AGENT_TYPE,
                value=TRAPI_KNOWLEDGE_LEVEL_PREDICTION,
            ),
        ]

        return Edge(
            attributes=attributes,
            predicate='biolink:treats',
            subject=subj_id,
            object=obj_id,
            sources=[make_internal_retrieval_source([], INFORES_IMPROVING_AGENT.infores_id)]
        )
    
    def make_supporting_edge(self, subj_id: str, obj_id: str) -> str:
        """Returns a supporting edge that has been created and added to
        the knowledge graph
        """
        attributes = [
            Attribute(
                attribute_type_id=BIOLINK_SLOT_AGENT_TYPE,
                value=TRAPI_AGENT_TYPE_ENUM_MANUAL_AGENT,
                attribute_source=INFORES_IMPROVING_AGENT.infores_id,
            ),
            Attribute(
                attribute_type_id=BIOLINK_SLOT_KNOWLEDGE_LEVEL,
                value=TRAPI_KNOWLEDGE_LEVEL_STATISTICAL_ASSOCIATION,
                attribute_source=INFORES_IMPROVING_AGENT.infores_id,
            )
        ]
        supp_edge = Edge(
            predicate='biolink:associated_with',
            subject=subj_id,
            object=obj_id,
            attributes=attributes,
            sources=[make_internal_retrieval_source([], INFORES_SPOKE.infores_id)],
        )
        return supp_edge
    
    def make_aux_graph(
        self,
        subj_id: str,
        obj_id: str,
        result_number: int,
    ) -> tuple[str, AuxiliaryGraph]:
        """Returns a tuple of the id of an auxiliary graph and the aux
        graph itself with an edge that relates the clinical concept of
        the PSEV. A side effect is that an edge is added to the
        knowledge graph
        """
        # make supporting edge and add to the knowledge graph
        supporting_edge = self.make_supporting_edge(subj_id, obj_id)
        supporting_edge_id = f'psev_edge_{result_number}'
        self.knowledge_graph['edges'][supporting_edge_id] = supporting_edge

        # make the aux graph ID and aux graph, then return
        aux_graph_id = f'ag_{result_number}'
        aux_graph = AuxiliaryGraph(edges=[supporting_edge_id])
        return aux_graph_id, aux_graph
    
    def _make_new_predicted_treats_edge(
        self,
        subj_id: str,
        obj_id: str,
        ag_id: str
    ) -> Edge:
        attributes = [
            Attribute(
                attribute_type_id=BIOLINK_SLOT_AGENT_TYPE,
                value=TRAPI_AGENT_TYPE_ENUM_MANUAL_AGENT,
                attribute_source=INFORES_IMPROVING_AGENT.infores_id,
            ),
            Attribute(
                attribute_type_id=BIOLINK_SLOT_KNOWLEDGE_LEVEL,
                value=TRAPI_KNOWLEDGE_LEVEL_PREDICTION,
                attribute_source=INFORES_IMPROVING_AGENT.infores_id,
            ),
            Attribute(
                attribute_type_id=BIOLINK_SLOT_SUPPORT_GRAPHS,
                value=[ag_id],
                attribute_source=INFORES_IMPROVING_AGENT.infores_id
            ),
        ]
        return Edge(
            predicate=BIOLINK_ASSOCIATION_TREATS,
            subject=subj_id,
            object=obj_id,
            attributes=attributes,
            sources=[make_internal_retrieval_source([], INFORES_IMPROVING_AGENT.infores_id)]
        )

    def _mutate_clinical_trials_result(
            self,   
            result: Result,
            knowledge_graph: KnowledgeGraph,
            disease_qnode_id: str,
        ) -> tuple[Result, dict[str, Edge], dict[str, AuxiliaryGraph]]:
        """Returns an updated result and two dicts, one containing updates
        to the knowledge graph and one containing updates to the
        auxiliary_graphs with additional support edges if the
        edge binding in a given result points to a "in clinical trials for"
        edge in the knowledge graph
        """
        kg_edge_updates = {}
        aux_graph_updates = {}

        # there's only one edge in the edge bindings, but we iterate
        # anyway because the ID lookup is so sloppy
        for qg_edge_key, bindings in result.analyses[0].edge_bindings.items():
            kg_edge_key = bindings[0].id
            kg_edge = knowledge_graph['edges'][kg_edge_key]
            if kg_edge.predicate != BIOLINK_ASSOCIATION_IN_CLINICAL_TRIALS_FOR:
                # a true "treats" edge, no need to modify
                return result, kg_edge_updates, aux_graph_updates

        # NOTE: outside of the loop, but still have the variables
        # now setup auxiliary graph
        ag = AuxiliaryGraph(edges=[kg_edge_key])
        ag_id = f'ag_{kg_edge_key}'
        aux_graph_updates[ag_id] = ag
    
        ## make a new edge
        # get subject id
        for id_, node in self.qnodes.items():
            if any(i in SUPPORTED_INFERRED_DRUG_SUBJ for i in node.categories):
                compound_id = id_

        result_subj = result.node_bindings[compound_id][0].id
        result_obj = result.node_bindings[disease_qnode_id][0].id
        new_result_edge = self._make_new_predicted_treats_edge(
            result_subj,
            result_obj,
            ag_id,
        )
        new_edge_id = f'i_{kg_edge_key}'
        edge_bindings = {qg_edge_key: [EdgeBinding(new_edge_id)]}
        kg_edge_updates[new_edge_id] = new_result_edge

        updated_analysis = Analysis(
            edge_bindings=edge_bindings,
            score=result.analyses[0].score,
            resource_id=INFORES_IMPROVING_AGENT.infores_id,
            support_graphs=[ag_id],
        )

        updated_result = Result(
            result.node_bindings,
            [updated_analysis],
        )

        return updated_result, kg_edge_updates, aux_graph_updates


    def do_query(self, session):
        logger.info(f'Doing template query: {self.template_query_name}')
        # first get psev scores for concept; if we don't have it there's
        # no point continuing
        if len(self.query_options['psev_context']) > 1:
            raise TemplateQuerySpecError(
                f'For template query={self.template_query_name} imProving Agent '
                'expects exactly one disease specified on the object node. Disease '
                'identifier must map to Disease Ontology via the Node Normalizer.'
            )
        disease_concept = self.query_options['psev_context'][0]
        compound_psev_scores = get_psev_scores([disease_concept], node_type=SPOKE_LABEL_COMPOUND)[disease_concept]
        if not compound_psev_scores:
            raise UnmatchedIdentifierError(
                f'No ML predictions available for disease equivalent to {disease_concept}'
            )

        # get disease qnode-id
        qnode_id_disease_node = None
        for qnode_id, qnode in self.qnodes.items():
            if SPOKE_LABEL_DISEASE in qnode.spoke_labels:
                qnode_id_disease_node = qnode_id
                break
        if not qnode_id_disease_node:
            raise UnmatchedIdentifierError(
                'Could not find a supported qnode binding for template query'
            )

        # do lookup
        basic_query = BasicQuery(
            self.qnodes,
            self.qedges,
            self.query_options,
            self.max_results
        )
        results, knowledge_graph, _ = basic_query.do_query(session, norm_scores=False)
        
        # now we inspect the results and mutate them as necessary, 
        # specifically, we are looking to see if there are 
        # "in clinical trials for" edges that need to be converted to
        # "predicted to treats" edges

        # first set up containers
        auxiliary_graphs = {}
        mutated_results = []
        # iterate and mutate results; update KG and AG as needed
        for result in results:
            mutated_result, kg_updates, aux_graph_updates  = self._mutate_clinical_trials_result(
                result,
                knowledge_graph,
                qnode_id_disease_node,
            )
            mutated_results.append(mutated_result)
            knowledge_graph['edges'] |= kg_updates
            auxiliary_graphs |= aux_graph_updates

        # sort compound_psev_scores
        count_to_get = self.max_results - len(mutated_results)
        sorted_compound_scores = {
            k: v
            for k, v
            in sorted(compound_psev_scores.items(), reverse=True, key=lambda item: item[1])[:count_to_get]
        }

        # remove the known to treat compounds from the top scored
        for node in knowledge_graph['nodes'].values():
            for attribute in node.attributes:
                if attribute.original_attribute_name == 'identifier':
                    try:
                        sorted_compound_scores.pop(attribute.value)
                    except KeyError:
                        continue

        if not sorted_compound_scores:
            return mutated_results, knowledge_graph, {}

        # now we can add the remaining highly scored results
        self.knowledge_graph = knowledge_graph
        new_results = []

        # peek at knowledge graph to find the node binding for the disease
        if mutated_results:
            disease_identifier = mutated_results[0].node_bindings[qnode_id_disease_node][0].id
        else:
            # no results, manually add the disease node to the kg
            disease_spoke_ids = [
                _id.strip("'")  # we add extra parentheses elsewhere for search
                for _id
                in list(self.qnodes[qnode_id_disease_node].spoke_identifiers.keys())
            ]
            disease_nodes = session.read_transaction(_disease_search, disease_spoke_ids, basic_query)
            _disease_id, result_node = next(iter(disease_nodes.items()))
            nn_results = normalize_spoke_nodes_for_translator(basic_query.nodes_to_normalize)
            disease_identifier = nn_results[_disease_id]
            self.knowledge_graph['nodes'][disease_identifier] = result_node

        node_ids = list(sorted_compound_scores.keys())
        result_nodes = session.read_transaction(_compound_search, node_ids, basic_query)

        for i, spoke_id in enumerate(result_nodes):
            biolink_id = format_curie_for_sri(
                BIOLINK_ENTITY_SMALL_MOLECULE,
                spoke_id,
            )
            aux_graph_id, aux_graph = self.make_aux_graph(
                biolink_id,
                disease_identifier,
                i,
            )
            auxiliary_graphs[aux_graph_id] = aux_graph
            result_edge = self.make_result_edge(
                biolink_id,
                disease_identifier,
                aux_graph_id,
            )
            self.knowledge_graph['edges'][f'inferred_{i}'] = result_edge
            self.knowledge_graph['nodes'][biolink_id] = result_nodes[spoke_id]
            new_results.append(Result(
                node_bindings={self.node_id_disease: [NodeBinding(disease_identifier)],
                               self.node_id_compound: [NodeBinding(biolink_id)]},
                analyses=[Analysis(
                    resource_id=INFORES_IMPROVING_AGENT.infores_id,
                    edge_bindings={self.edge_id_treats: [EdgeBinding(f'inferred_{i}')]},
                    score=sorted_compound_scores[spoke_id] * 10000,
                    support_graphs=[aux_graph_id],
                )]
            ))
        mutated_results.extend(new_results)
        results = normalize_results_scores(mutated_results)

        results = sorted(results, key=lambda x: x.analyses[0].score, reverse=True)
        return results, self.knowledge_graph, auxiliary_graphs
