from .compound_may_affect_gene import CompoundAffectsGene
from .drug_may_treat_disease import DrugMayTreatDisease

TEMPLATE_QUERIES = [
    CompoundAffectsGene,
    DrugMayTreatDisease,
]


def match_template_queries(qedges, qnodes):
    for template_query in TEMPLATE_QUERIES:
        if template_query.matches_template(qedges, qnodes):
            return template_query
