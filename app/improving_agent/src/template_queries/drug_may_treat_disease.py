from improving_agent.models import Edge, EdgeBinding, NodeBinding, Result
from improving_agent.src.biolink.spoke_biolink_constants import SPOKE_LABEL_COMPOUND
from improving_agent.exceptions import TemplateQuerySpecError, UnmatchedIdentifierError
from improving_agent.src.basic_query import BasicQuery
from improving_agent.src.normalization.edge_normalization import (
    BIOLINK_TREATS,
    BIOLINK_DISEASE,
    KNOWLEDGE_TYPE_INFERRED,
    SUPPORTED_INFERRED_DRUG_SUBJ
)
from improving_agent.src.provenance import IMPROVING_AGENT_PROVENANCE_ATTR
from improving_agent.src.psev import get_psev_scores
from improving_agent.util import get_evidara_logger

logger = get_evidara_logger(__name__)

CYPHER_COMPOUND_SEARCH = """
    MATCH (c:Compound)
    WHERE c.identifier in $identifiers
    RETURN c
"""


def extract_compound_result(record, querier):
    node_info = record['c']
    identifier = node_info['identifier']
    result_node = querier.make_result_node(node_info, identifier)
    return identifier, result_node


def compound_search(tx, identifiers, querier):
    records = tx.run(CYPHER_COMPOUND_SEARCH, identifiers=identifiers)
    result_nodes = {}
    for record in records:
        identifier, result_node = extract_compound_result(record, querier)
        result_nodes[identifier] = result_node
    return result_nodes


class DrugMayTreatDisease:
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
        if len(qedges) > 1:
            return False
        for qedge in qedges.values():
            if (
                qedge.knowledge_type != KNOWLEDGE_TYPE_INFERRED
                or qedge.predicates != [BIOLINK_TREATS]
            ):
                return False
        if len(qnodes) != 2:
            return False
        if not all(cat in SUPPORTED_INFERRED_DRUG_SUBJ
                   for cat
                   in qnodes[qedge.subject].categories):
            return False
        if qnodes[qedge.object].categories != [BIOLINK_DISEASE]:
            return False

        return True

    def make_result_edge(self, subj_id, obj_id):
        return Edge(
            predicate='biolink:treats',
            subject=subj_id,
            object=obj_id,
            attributes=[IMPROVING_AGENT_PROVENANCE_ATTR]
        )

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

        # do lookup
        basic_query = BasicQuery(
            self.qnodes,
            self.qedges,
            self.query_options,
            self.max_results
        )
        results, knowledge_graph = basic_query.do_query(session)

        # sort compound_psev_scores
        count_to_get = self.max_results - len(results)
        sorted_compound_scores = {
            k: v
            for k, v
            in sorted(compound_psev_scores.items(), key=lambda item: item[1])[:count_to_get]
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
            return results, knowledge_graph

        # now we can add the remaining highly scored results
        self.knowledge_graph = knowledge_graph
        new_results = []

        node_ids = list(sorted_compound_scores.keys())
        result_nodes = session.read_transaction(compound_search, node_ids, basic_query)

        for i, id_ in enumerate(result_nodes):
            result_edge = self.make_result_edge(id_, disease_concept)
            self.knowledge_graph['edges'][f'inferred_{i}'] = result_edge
            self.knowledge_graph['nodes'][id_] = result_nodes[id_]
            new_results.append(Result(
                node_bindings={self.node_id_disease: NodeBinding(disease_concept),
                               self.node_id_compound: NodeBinding(id_)},
                edge_bindings={self.edge_id_treats: EdgeBinding(f'inferred_{i}')},
                score=sorted_compound_scores[id_]
            ))

        results = sorted(results + new_results, key=lambda x: x.score, reverse=True)
        return results, self.knowledge_graph
