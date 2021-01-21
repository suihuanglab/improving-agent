# this module interacts with biggim as of 2020-03
import codecs
import csv
import re
import time
from contextlib import closing

import requests
from werkzeug.utils import cached_property

from improving_agent.util import get_evidara_logger

logger = get_evidara_logger(__name__)


class BigGimClient:
    """A class for querying NCATS Translator BigGIM. This is held in a
    class for the ability to cache the result of tissues and potentially
    other metadata"""

    def __init__(self):
        """Instantiates a BigGimClient object"""
        self.available_tissue_studies = {}

    @cached_property
    def tissues(self):
        return requests.get("http://biggim.ncats.io/api/metadata/tissue").json()["tissues"]

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


BIG_GIM_CLIENT = BigGimClient()
