from fuzzywuzzy.process import extractOne

from .biggim_client import BIG_GIM_CLIENT
from improving_agent.models import Attribute
from improving_agent.src.normalization.curie_formatters import format_gene_for_spoke
from improving_agent.src.biolink.spoke_biolink_constants import BIOLINK_ENTITY_GENE
from improving_agent.util import get_evidara_logger

logger = get_evidara_logger(__name__)


def format_gene_for_bg(identifier):
    return int(format_gene_for_spoke(identifier))


def get_relevant_anatomy(session, disease):
    """Returns SPOKE results for anatomy related to `disease`
    Parameters
    ----------
    session (neo4j.GraphDatabase.driver.session): neo4j database
        connection with which tissue can be searched
    genes (list of str or int): ENTREZ gene ids to search. Genes are
        searched combinatorically
    disease (str): DOID identifier for diseases to search in SPOKE
        to determine which tissue to retrieve
    """
    logger.info(f'Querying SPOKE for anatomy relevant to {disease}')
    tissue_results = session.run(
        "MATCH p=(d:Disease)-[e:LOCALIZES_DlA]-(a:Anatomy) "
        "WHERE d.identifier = {disease_id} "
        "RETURN * ORDER BY e.cooccur DESC LIMIT 5",
        disease_id=disease,
    )
    top_spoke_tissues = [record["a"].get("name") for record in tissue_results.records()]
    search_tissues = [
        extractOne(tissue, BIG_GIM_CLIENT.tissues)[0]
        for tissue in top_spoke_tissues
    ]
    return search_tissues


def check_query_graph(query_order):
    """Returns lists of nodes and edges that can be annotated by
    BigGIM

    Parameters
    ----------
    query_order (list of qnode and qedge objects):

    Returns
    -------
    gene_nodes_to_search (list of models.QNode): QNodes whose
        corresponding KnowledgeGraph Nodes can be searched in
        BigGIM
    gene_gene_edges (list of models.QEdge): QEdges whose
        corresponding KnowledgeGraph Edges can be annotated
    """
    gene_nodes_to_search = []
    gene_gene_edges = []
    first = iter(query_order)
    second = iter(query_order[2::2])
    for triplet in zip(first, first, second):
        if triplet[0].category[0] == BIOLINK_ENTITY_GENE and triplet[2].category[0] == BIOLINK_ENTITY_GENE:
            gene_nodes_to_search.append(triplet[0])
            gene_nodes_to_search.append(triplet[2])
            gene_gene_edges.append(triplet[1])
    return gene_nodes_to_search, gene_gene_edges


def annotate_edges_with_biggim(
    session,
    query_order,
    kg_edges,
    results,
    disease=None,
    anatomy=None
):
    """Annotates gene-gene edges with relevant metadata from BigGIM

    Parameters
    ----------
    session (neo4j.GraphDatabase.driver.session): neo4j cursor to
        query SPOKE
    query_order (list of models.QNode/QEdge): the ordered
        query_graph sent to evidARA for evaluation; here used to
        check if consecutive nodes are genes
    kg_edges (dict of models.Edges): result knowledge graph edges to
        update with BigGIM coexpression data
    results (list of models.Result): results from which to extract
        the appropriate edge_ids to update
    disease (str): DOID for which to search SPOKE and BigGIM for
        related tissue types
    anatomy (str): UBERON identifier for which to search BigGIM for
        related tissue types

    Returns
    -------
    edges (dict of models.Edges): edges annotated with BigGIM data
    """
    # require either disease or anatomy, return if both are missing
    if disease is None and anatomy is None:
        return kg_edges
    bg_nodes, bg_edges = check_query_graph(query_order)
    if bg_nodes and disease:
        logger.info("Query graph appropriate for BigGIM annotation")

        # iterate through results to extract gene ids and edges to update
        genes_to_search = set()
        edges_to_update = []
        for result in results:
            for bg_node in bg_nodes:
                genes_to_search.add(format_gene_for_bg(result.node_bindings[bg_node.qnode_id].id))
            for bg_edge in bg_edges:
                edges_to_update.append(result.edge_bindings[bg_edge.qedge_id].id)

        # get disease-relevant anatomy from SPOKE
        search_tissues = get_relevant_anatomy(session, disease)

        bg_results = BIG_GIM_CLIENT.search_biggim_tissues(genes_to_search, search_tissues)
        if not len(bg_results):
            logger.info("No results returned from BigGIM")

        # annotate results
        logger.info(f"Found {len(results)} BigGIM results; annotating edges.")
        uninteresting_keys = set(["GPID", "Gene1", "Gene2"])

        for edge_id in edges_to_update:
            kedge = kg_edges[edge_id]

            key = None
            formatted_subject = format_gene_for_bg(kedge.subject)
            formatted_object = format_gene_for_bg(kedge.object)
            if f"{formatted_subject}-{formatted_object}" in bg_results:
                key = f"{formatted_subject}-{formatted_object}"
            elif f"{formatted_object}-{formatted_subject}" in bg_results:
                key = f"{formatted_object}-{formatted_subject}"
            else:
                continue

            attributes = kedge.attributes
            for k, v in bg_results[key].items():
                if k not in uninteresting_keys:
                    attributes.append(Attribute(type=f'BigGIM_{k}', value=v))

            kg_edges[edge_id].attributes = attributes

    return kg_edges
