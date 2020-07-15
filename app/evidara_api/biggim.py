# this module interacts with biggim as of 2020-03
import codecs
import csv
import re
import time
from contextlib import closing

import requests
from fuzzywuzzy.process import extractOne
from werkzeug.utils import cached_property

from evidara_api.models.edge_attribute import EdgeAttribute
from evidara_api.util import get_evidara_logger

logger = get_evidara_logger(__name__)


class BigGimRequester:
    """A class for querying NCATS Translator BigGIM. This is held in a
    class for the ability to cache the result of tissues and potentially
    other metadata"""

    def __init__(self):
        """Instantiates a BigGimRequester object"""
        self.available_tissue_studies = {}

    @cached_property
    def available_tissues(self):
        """Returns tissues currently available in biggim"""
        r = requests.get("http://biggim.ncats.io/api/metadata/tissue")
        return r.json()["tissues"]

    def get_available_tissue_studies(self, tissue):
        """Returns columns related to tissue that can be searched in
        BigGIM"""
        # check for tissue in cached dict and get if not there
        if tissue not in self.available_tissue_studies:
            r = requests.get(f"http://biggim.ncats.io/api/metadata/tissue/{tissue}")
            self.available_tissue_studies[tissue] = r.json()["substudies"]
        
        # unpack potential tissues, returning those from GIANT and GTEx
        return [
            column["name"] for column in [
                col
                for study in self.available_tissue_studies[tissue]
                for col in study["columns"]
            ]
            if (
                re.match("GIANT|GTEx", column["name"])
                and column["table"]["name"] == "BigGIM_v1"
            )
        ]

    def search_biggim_tissues(self, genes, tissues):
        """Hits BigGIM to retrieve gene correlations for a given
        anatomical tissue
        
        Parameters
        ----------
        genes (list of str or int): ENTREZ gene ids to search. Genes are
            searched combinatorically
        tissues (list of str): one or more anatomies to search in BigGim

        Returns
        -------
        """
        if len(genes) < 2:
            # we don't want to deal with that many results
            logger.warning("Too few genes to query BigGIM, exiting without annotation")
            return []
        
        logger.info(f"Querying BigGIM for {len(genes)} genes and {len(tissues)} tissues.")
        
        columns = []
        for tissue in tissues:
            columns.extend(self.get_available_tissue_studies(tissue))
        
        # set up search strings
        search_columns = ",".join(set(columns))
        search_genes = ",".join(set([str(gene) for gene in genes]))
        r = requests.post(
            "http://biggim.ncats.io/api/biggim/query",
            json={
                "table": "BigGIM_70_v1",
                "ids1": search_genes,
                "ids2": search_genes,
                "columns": search_columns,
            },
        )

        if r.status_code != 200:
            logger.warning(f"Querying BigGIM failed with {r.status_code} and {r.text}")
            return []
        
        request_id = r.json()["request_id"]
        results_ready = False
        while not results_ready:
            time.sleep(1)
            results_r = requests.get(
                f"http://biggim.ncats.io/api/biggim/status/{request_id}"
            )
            if results_r.json()["status"] == "complete":
                results_ready = True
            elif results_r.json()["status"] == "error":
                logger.warning(f"BigGIM failed with {r.text}")
                return []
        # the below should be refactored into its own function.. could
        # be useful to serialize remote csvs easily

        # set up dict for results and fetch csv from BigGIM
        biggim_results = {}
        result_url = results_r.json()["request_uri"][0]

        # get the header row
        with closing(requests.get(result_url, stream=True)) as r:
            reader = csv.reader(codecs.iterdecode(r.iter_lines(), "utf-8"))
            header_row = next(reader)
        
        # iterate through the results
        with closing(requests.get(result_url, stream=True)) as r:
            reader = csv.DictReader(
                codecs.iterdecode(r.iter_lines(), "utf-8"), fieldnames=header_row
            )
            _ = next(reader)  # skip header row
            for row in reader:
                biggim_results[f"{str(row['Gene1'])}-{str(row['Gene2'])}"] = row

        return biggim_results

    def search_biggim_disease(self, session, genes, disease):
        """Hits BigGIM to retrieve gene correlations for a given disease
        as it relates to specific tissues. 

        This function first searches SPOKE to improve understand which
        tissue is most relevant for the disease of interest. 

        Parameters
        ----------
        session (neo4j.GraphDatabase.driver.session): neo4j database 
            connection with which tissue can be searched
        genes (list of str or int): ENTREZ gene ids to search. Genes are
            searched combinatorically
        disease (str): DOID identifier for diseases to search in SPOKE
            to determine which tissue to retrieve
        
        Returns
        -------
        <unnamed> (list of ..)
        """
        tissue_results = session.run(
            "MATCH p=(d:Disease)-[e:LOCALIZES_DlA]-(a:Anatomy) "
            "WHERE d.identifier = {disease_id} "
            "RETURN * ORDER BY e.cooccur DESC LIMIT 5",
            disease_id=disease,
        )
        top_spoke_tissues = [
            record["a"].get("name") for record in tissue_results.records()
        ]
        search_tissues = [
            extractOne(tissue, self.available_tissues)[0]
            for tissue in top_spoke_tissues
        ]
        return self.search_biggim_tissues(genes, search_tissues)

    def check_query_graph(self, query_order):
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
            if triplet[0].type == "Gene" and triplet[2].type == "Gene":
                gene_nodes_to_search.append(triplet[0])
                gene_nodes_to_search.append(triplet[2])
                gene_gene_edges.append(triplet[1])
        return gene_nodes_to_search, gene_gene_edges

    def annotate_edges_with_biggim(
        self, session, query_order, results, disease=None, anatomy=None
    ):
        """Annotates gene-gene edges with relevant metadata from BigGIM
        
        Parameters
        ----------
        session (neo4j.GraphDatabase.driver.session): neo4j cursor to 
            query SPOKE
        query_order (list of models.QNode/QEdge): the ordered 
            query_graph sent to evidARA for evaluation; here used to
            check if consecutive nodes are genes
        results (list of models.Result): results to be updated with 
            BigGIM coexpression data, if available
        disease (str): DOID for which to search SPOKE and BigGIM for 
            related tissue types 
        anatomy (str): UBERON identifier for which to search BigGIM for
            related tissue types 

        Returns
        -------
        results (list of models.Result): results with edges annotated
            with BigGIM results
        """
        # require either disease or anatomy, return if both are missing
        if disease is None and anatomy is None:
            return results
        bg_nodes, bg_edges = self.check_query_graph(query_order)
        if len(bg_nodes) and disease:
            logger.info("Query graph appropriate for BigGIM annotation")
            
            # iterate through results to extract gene ids
            genes_to_search = [
                result.knowledge_map["nodes"][qnode.node_id]
                for qnode in bg_nodes
                for result in results
            ]
            
            # query BigGIM
            bg_results = self.search_biggim_disease(session, genes_to_search, disease)
            if not len(bg_results):
                logger.info("No results returned from BigGIM")
                return results
            
            # TODO: put this in its own function
            # annotate results
            logger.info(f"Found {len(results)} BigGIM results; annotating edges.")
            uninteresting_keys = set(["GPID", "Gene1", "Gene2"])
            for result in results:
                edges_to_update = [
                    result.knowledge_map["edges"][edge.edge_id] for edge in bg_edges
                ]
                for edge in result.result_graph.edges:
                    if edge.id in edges_to_update:
                        key = None
                        if f"{edge.source_id}-{edge.target_id}" in bg_results:
                            key = f"{edge.source_id}-{edge.target_id}"
                        elif f"{edge.target_id}-{edge.source_id}" in bg_results:
                            key = f"{edge.target_id}-{edge.source_id}"
                        else:
                            continue
                        for k, v in bg_results[key].items():
                            if k not in uninteresting_keys:
                                edge.edge_attributes.append(
                                    EdgeAttribute(type=k, value=v)
                                )
        return results
