"""This module provides functions to format curies for search against
the SRI Node Normalizer

Note that the following identifiers don't necessarily need to be normalized:
SPOKE type          |  biolink type               |  spoke curie format |  notes
--------------------|-----------------------------|---------------------|------------------------------------------
Anatomy             |  biolink:AnatomicalEntity   |  UBERON:1234567     |
AnatomyCellType     |  N/A                        |                     |
BiologicalProcess   |  biolink:BiologicalProcess  |  GO:0140206         |
CellType            |  biolink:Cell               |  CL:1000391         |
CellularComponent   |  biolink:CellularComponent  |  GO:0034518         |
Disease             |  biolink:Disease            |  DOID:0111771       |
Food                |  biolink:NamedThing         |  FOOD1234           |  not supported by node normalizer
MolecularFunction   |  biolink:MolecularActivity  |  GO:0001055         |
Nutrient            |  biolink:NamedThing         |  FDBN00002          |  not supported by biolink/node normalizer
Pathway             |  biolink:Pathway            |  WP314_r109375      |  not supported by node normalizer
PharmacologicClass  |  biolink:NamedThing         |  N0000175533        |  not supported by biolink/node normalizer
SideEffect          |  biolink:NamedThing         |  C0235309           |  not supported by biolink/node normalizer
"""


import re
from collections import defaultdict

from .sri_node_normalizer import (
    NODE_NORMALIZATION_RESPONSE_VALUE_EQUIVALENT_IDENTIFIERS,
    NODE_NORMALIZATION_RESPONSE_VALUE_IDENTIFIER
)
from improving_agent.exceptions import UnsupportedTypeError
from improving_agent.src.spoke_biolink_constants import (
    BIOLINK_ENTITY_CHEMICAL_SUBSTANCE,
    BIOLINK_ENTITY_GENE,
    BIOLINK_ENTITY_MOLECULAR_ACTIVITY,
    BIOLINK_ENTITY_ORGANISM_TAXON,
    BIOLINK_ENTITY_PATHWAY,
    BIOLINK_ENTITY_PROTEIN,
    BIOLINK_ENTITY_PHENOTYPIC_FEATURE,
    SPOKE_LABEL_ANATOMY,
    SPOKE_LABEL_ANATOMY_CELL_TYPE,
    SPOKE_LABEL_BIOLOGICAL_PROCESS,
    SPOKE_LABEL_CELL_TYPE,
    SPOKE_LABEL_CELLULAR_COMPONENT,
    SPOKE_LABEL_COMPOUND,
    SPOKE_LABEL_DISEASE,
    SPOKE_LABEL_EC,
    SPOKE_LABEL_FOOD,
    SPOKE_LABEL_GENE,
    SPOKE_LABEL_MOLECULAR_FUNCTION,
    SPOKE_LABEL_NUTRIENT,
    SPOKE_LABEL_ORGANISM,
    SPOKE_LABEL_PATHWAY,
    SPOKE_LABEL_PHARMACOLOGIC_CLASS,
    SPOKE_LABEL_PROTEIN,
    SPOKE_LABEL_REACTION,
    SPOKE_LABEL_SARSCOV2,
    SPOKE_LABEL_SIDE_EFFECT,
    SPOKE_LABEL_SYMPTOM
)

NODE_NORMALIZATION_SEARCH_CURIE_FORMATTERS = defaultdict(dict)
NODE_NORMALIZATION_SPOKE_CURIE_FORMATTERS = defaultdict(dict)
NODE_NORMALIZATION_KEY_FUNCTION = 'function'
NODE_NORMALIZATION_KEY_REGEX = 'regex'

SPOKE_IDENTIFIER_REGEX_ANATOMY = '^UBERON:[0-9]{7}$'
SPOKE_IDENTIFIER_REGEX_BIOLOGICAL_PROCESS = '^GO:[0-9]{7}$'
SPOKE_IDENTIFIER_REGEX_CELL_TYPE = '^CL:[0-9]{7}$'
SPOKE_IDENTIFIER_REGEX_CELLULAR_COMPONENT = '^GO:[0-9]{7}$'
SPOKE_IDENTIFIER_REGEX_COMPOUND = '^CHEMBL[0-9]{1,7}$|^(DB|c|C|D|G)[0-9]{5}$'
SPOKE_IDENTIFIER_REGEX_DISEASE = '^DOID:[0-9]{1,7}$'
SPOKE_IDENTIFIER_REGEX_EC = '^[0-9][.][0-9]{1,2}([.][0-9]{1,2})?([.][a-zM0-9]{1,4})?$'
SPOKE_IDENTIFIER_REGEX_FOOD = '^FOOD[0-9]{5}$'
SPOKE_IDENTIFIER_REGEX_GENE = '^[0-9]{1,9}$'  # Note that this is an int in SPOKE
SPOKE_IDENTIFIER_REGEX_MOLECULAR_FUNCTION = '^GO:[0-9]{7}$'
SPOKE_IDENTIFIER_REGEX_NUTRIENT = '^FDBN[0-9]{5}$'
SPOKE_IDENTIFIER_REGEX_ORGANISM = '^[0-9]{2,7}$'
# The pathway regex is unsafe and generally not great. One that covers all
# but 82 of the pathways is as follows:
# '^PWY([0-9A-Z]{1,3})?-[I0-9]{1,4}$|^P[0-9]{1,3}-PWY$|^M[0-9]{5}$|^[A-Z0-9-]+PWY(-1)?$'
# The last A-Z is not ideal either, but at least there aren't spaces
SPOKE_IDENTIFIER_REGEX_PATHWAY = '[a-zA-Z0-9-+ ]+'
SPOKE_IDENTIFIER_REGEX_PHARMACOLOGIC_CLASS = '^N[0-9]{10}$'
SPOKE_IDENTIFIER_REGEX_PROTEIN = '[OPQ][0-9][A-Z0-9]{3}[0-9]$|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$|^[0-9]{2,3}$'
SPOKE_IDENTIFIER_REGEX_REACTION = '^(TRANS-)?RXN([A-Z0-9]{1,4})?-[0-9]{1,5}|R[0-9]{5}|^[0-9A-Z-+.]+[RXN|SYN]$'  # not great
SPOKE_IDENTIFIER_REGEX_SARSCOV2 = '^[0-9]{1,3}$'
SPOKE_IDENTIFIER_REGEX_SIDE_EFFECT = '^C[0-9]{7}$'
SPOKE_IDENTIFIER_REGEX_SYMPTOM = '^D[0-9]{5,9}$'

SPOKE_IDENTIFIER_REGEX_ANATOMY_CELL_TYPE = f'{SPOKE_IDENTIFIER_REGEX_ANATOMY}/{SPOKE_IDENTIFIER_REGEX_CELL_TYPE}'

SPOKE_IDENTIFIER_REGEXES = {
    SPOKE_LABEL_ANATOMY: SPOKE_IDENTIFIER_REGEX_ANATOMY,
    SPOKE_LABEL_ANATOMY_CELL_TYPE: SPOKE_IDENTIFIER_REGEX_ANATOMY_CELL_TYPE,
    SPOKE_LABEL_BIOLOGICAL_PROCESS: SPOKE_IDENTIFIER_REGEX_BIOLOGICAL_PROCESS,
    SPOKE_LABEL_CELL_TYPE: SPOKE_IDENTIFIER_REGEX_CELL_TYPE,
    SPOKE_LABEL_CELLULAR_COMPONENT: SPOKE_IDENTIFIER_REGEX_CELLULAR_COMPONENT,
    SPOKE_LABEL_COMPOUND: SPOKE_IDENTIFIER_REGEX_COMPOUND,
    SPOKE_LABEL_DISEASE: SPOKE_IDENTIFIER_REGEX_DISEASE,
    SPOKE_LABEL_EC: SPOKE_IDENTIFIER_REGEX_EC,
    SPOKE_LABEL_FOOD: SPOKE_IDENTIFIER_REGEX_FOOD,
    SPOKE_LABEL_GENE: SPOKE_IDENTIFIER_REGEX_GENE,
    SPOKE_LABEL_MOLECULAR_FUNCTION: SPOKE_IDENTIFIER_REGEX_MOLECULAR_FUNCTION,
    SPOKE_LABEL_NUTRIENT: SPOKE_IDENTIFIER_REGEX_NUTRIENT,
    SPOKE_LABEL_ORGANISM: SPOKE_IDENTIFIER_REGEX_ORGANISM,
    SPOKE_LABEL_PATHWAY: SPOKE_IDENTIFIER_REGEX_PATHWAY,
    SPOKE_LABEL_REACTION: SPOKE_IDENTIFIER_REGEX_REACTION,
    SPOKE_LABEL_PHARMACOLOGIC_CLASS: SPOKE_IDENTIFIER_REGEX_PHARMACOLOGIC_CLASS,
    SPOKE_LABEL_PROTEIN: SPOKE_IDENTIFIER_REGEX_PROTEIN,
    SPOKE_LABEL_SARSCOV2: SPOKE_IDENTIFIER_REGEX_SARSCOV2,
    SPOKE_LABEL_SIDE_EFFECT: SPOKE_IDENTIFIER_REGEX_SIDE_EFFECT,
    SPOKE_LABEL_SYMPTOM: SPOKE_IDENTIFIER_REGEX_SYMPTOM,
}


# Formatters for searching the SRI node normalizer
def register_search_curie_formatter(node_type, regex):
    def wrapper(f):
        NODE_NORMALIZATION_SEARCH_CURIE_FORMATTERS[node_type][regex] = f
        return f
    return wrapper


@register_search_curie_formatter(BIOLINK_ENTITY_CHEMICAL_SUBSTANCE, '^CHEMBL[0-9]{1,7}$')
def _format_chembl_for_search(curie, source=None):
    return f"CHEMBL.COMPOUND:{curie}"


@register_search_curie_formatter(BIOLINK_ENTITY_CHEMICAL_SUBSTANCE, '^DB[0-9]{5}$')
def _format_drugbank_for_search(curie, source=None):
    return f'DRUGBANK:{curie}'


@register_search_curie_formatter(BIOLINK_ENTITY_CHEMICAL_SUBSTANCE, '^(C|G)[0-9]{5}$')
def _format_kegg_compound_for_search(curie, source=None):
    return f'KEGG:{curie}'


@register_search_curie_formatter(BIOLINK_ENTITY_GENE, SPOKE_IDENTIFIER_REGEX_GENE)
def _format_ncbigene_for_search(curie, source=None):
    return f'NCBIGene:{curie}'


@register_search_curie_formatter(
    BIOLINK_ENTITY_MOLECULAR_ACTIVITY,
    f'{SPOKE_IDENTIFIER_REGEX_EC}|{SPOKE_IDENTIFIER_REGEX_REACTION}'
)
def _format_ec_reaction_for_search(curie, source=None):
    # doesn't match MolecularFunction SPOKE label

    if not source:  # this happens when we receive the query
        return [f'KEGG:{curie}', f'MetaCyc:{curie}']
    if source == 'kegg':
        return f'KEGG:{curie}'
    if source == 'metacyc':
        return f'MetaCyc:{curie}'
    return curie  # this happens when we're returning results


@register_search_curie_formatter(BIOLINK_ENTITY_ORGANISM_TAXON, SPOKE_IDENTIFIER_REGEX_ORGANISM)
def _format_ncbitaxon_for_search(curie, source=None):
    return f'NCBITaxon:{curie}'


@register_search_curie_formatter(BIOLINK_ENTITY_PATHWAY, SPOKE_IDENTIFIER_REGEX_PATHWAY)
def _format_pathway_for_search(curie, source=None):
    if not source:
        return [f'KEGG:{curie}', f'MetaCyc:{curie}']
    if source == 'kegg':
        return f'KEGG:{curie}'
    if source == 'metacyc':
        return f'MetaCyc:{curie}'
    return curie


@register_search_curie_formatter(BIOLINK_ENTITY_PHENOTYPIC_FEATURE, SPOKE_IDENTIFIER_REGEX_SYMPTOM)
def _format_symptom_for_search(curie, source=None):
    return f'MESH:{curie}'


@register_search_curie_formatter(BIOLINK_ENTITY_PROTEIN, SPOKE_IDENTIFIER_REGEX_PROTEIN)
def _format_protein_for_search(curie, source=None):
    return f'UniProtKB:{curie}'


def format_curie_for_sri(category, curie, source=None):
    format_funcs = NODE_NORMALIZATION_SEARCH_CURIE_FORMATTERS.get(category)
    if not format_funcs:
        return curie
    for regex, format_func in format_funcs.items():
        if re.match(regex, str(curie)):
            return format_func(curie, source)

    return curie


# Formatters for translating SRI Normalization results to SPOKE
# It may seems silly (or insane) to do all of this checking instead of
# simply letting the database do th work for us, but these regex help
# to make the Cypher queries slightly safer by enforcing strict
# patterns before sending the queries to the DB. The goal is to not allow
# Cypher keywords like DELETE, CREATE, SET, etc to sneak into the queries
def register_spoke_curie_formatter(node_type, regex):
    def wrapper(f):
        NODE_NORMALIZATION_SPOKE_CURIE_FORMATTERS[node_type][NODE_NORMALIZATION_KEY_FUNCTION] = f
        NODE_NORMALIZATION_SPOKE_CURIE_FORMATTERS[node_type][NODE_NORMALIZATION_KEY_REGEX] = regex
        return f
    return wrapper


@register_spoke_curie_formatter(SPOKE_LABEL_ANATOMY, SPOKE_IDENTIFIER_REGEX_ANATOMY)
def _format_anatomy_for_spoke(curie):
    return f"'{curie}'"


@register_spoke_curie_formatter(SPOKE_LABEL_BIOLOGICAL_PROCESS, SPOKE_IDENTIFIER_REGEX_BIOLOGICAL_PROCESS)
def _format_biological_process_for_spoke(curie):
    return f"'{curie}'"


@register_spoke_curie_formatter(SPOKE_LABEL_CELL_TYPE, SPOKE_IDENTIFIER_REGEX_CELL_TYPE)
def _format_cell_type_for_spoke(curie):
    return f"'{curie}'"


@register_spoke_curie_formatter(SPOKE_LABEL_CELLULAR_COMPONENT, SPOKE_IDENTIFIER_REGEX_CELLULAR_COMPONENT)
def _format_cellular_component_for_spoke(curie):
    return f"'{curie}'"


@register_spoke_curie_formatter(SPOKE_LABEL_COMPOUND, '^CHEMBL.COMPOUND:|^DRUGBANK:|^KEGG:')
def _format_compound_for_spoke(curie):
    return f"'{re.sub('^CHEMBL.COMPOUND:|^DRUGBANK:|^KEGG:', '', curie)}'"


@register_spoke_curie_formatter(SPOKE_LABEL_DISEASE, SPOKE_IDENTIFIER_REGEX_DISEASE)
def _format_disease_for_spoke(curie):
    return f"'{curie}'"


@register_spoke_curie_formatter(SPOKE_LABEL_EC, SPOKE_IDENTIFIER_REGEX_EC)
def _format_ec_for_spoke(curie):
    return f"'{curie}'"


@register_spoke_curie_formatter(SPOKE_LABEL_FOOD, SPOKE_IDENTIFIER_REGEX_FOOD)
def _format_food_for_spoke(curie):
    return f"'{curie}'"


@register_spoke_curie_formatter(SPOKE_LABEL_GENE, '^NCBIGene:')
def format_gene_for_spoke(curie):
    # missing leading underscore because it's used by the BigGIM module
    return curie.replace('NCBIGene:', '')
    # this ^ is an int in SPOKE, but we just forego the addition of quotes here


@register_spoke_curie_formatter(SPOKE_LABEL_MOLECULAR_FUNCTION, SPOKE_IDENTIFIER_REGEX_MOLECULAR_FUNCTION)
def _format_molecular_function_for_spoke(curie):
    return f"'{curie}'"


@register_spoke_curie_formatter(SPOKE_LABEL_NUTRIENT, SPOKE_IDENTIFIER_REGEX_NUTRIENT)
def _format_nutrient_for_spoke(curie):
    return f"'{curie}'"


@register_spoke_curie_formatter(SPOKE_LABEL_ORGANISM, '^NCBITaxon:')
def _format_organism_for_spoke(curie):
    return curie.replace('NCBITaxon', '')


@register_spoke_curie_formatter(SPOKE_LABEL_PATHWAY, SPOKE_IDENTIFIER_REGEX_PATHWAY)
def _format_pathway_for_spoke(curie):
    # TODO: consider checking unsafe Cypher terms here as a hedge against
    # the very permissive regex
    return f"'{curie}'"


@register_spoke_curie_formatter(SPOKE_LABEL_PHARMACOLOGIC_CLASS, SPOKE_IDENTIFIER_REGEX_PHARMACOLOGIC_CLASS)
def _format_pharmacological_class_for_spoke(curie):
    return f"'{curie}'"


@register_spoke_curie_formatter(SPOKE_LABEL_PROTEIN, '^UniProtKB:')
def _format_protein_for_spoke(curie):
    return f"'{curie.replace('UniProtKB:', '')}'"


@register_spoke_curie_formatter(SPOKE_LABEL_REACTION, '^KEGG:|^MetaCyc:')
def _format_reaction_for_spoke(curie):
    return f"'{re.sub('^KEGG:|^MetaCyc:', '', curie)}'"


@register_spoke_curie_formatter(SPOKE_LABEL_SARSCOV2, SPOKE_IDENTIFIER_REGEX_SARSCOV2)
def _format_sarscov2_protein_for_spoke(curie):
    return f"'{curie}'"


@register_spoke_curie_formatter(SPOKE_LABEL_SIDE_EFFECT, SPOKE_IDENTIFIER_REGEX_SIDE_EFFECT)
def _format_side_effect_for_spoke(curie):
    return f"'{curie}'"


@register_spoke_curie_formatter(SPOKE_LABEL_SYMPTOM, '^MESH:D[0-9]+')
def _format_symptom_for_spoke(curie):
    return f"'{curie}'"


def get_label_if_appropriate_spoke_curie(spoke_labels, curie):
    for spoke_label in spoke_labels:
        if re.match(SPOKE_IDENTIFIER_REGEXES[spoke_label], curie):
            return spoke_label


def get_spoke_identifiers_from_normalized_node(spoke_labels, normalized_node, searched_curie):
    """Returns a SPOKE identifier from a node normalizer response

    Iterates through an SRI Node Normalizer response and attempts to
    find an appropriate identifier in the `equivalent_identifiers` field

    TODO: We use spoke_label here because we don't have exact mappings
    for all node types at this point in time, but to be more consistent
    we should use biolink categories here when the mapping is complete
    """
    node_type_configs = [NODE_NORMALIZATION_SPOKE_CURIE_FORMATTERS.get(spoke_label) for spoke_label in spoke_labels]

    if not node_type_configs:
        raise UnsupportedTypeError(f'Could not find a SPOKE identifer formatter func for category {",".join(spoke_labels)}')

    spoke_identifiers = []
    for identifier in normalized_node[NODE_NORMALIZATION_RESPONSE_VALUE_EQUIVALENT_IDENTIFIERS]:
        for node_type_config in node_type_configs:
            if re.match(
                    node_type_config[NODE_NORMALIZATION_KEY_REGEX],
                    identifier[NODE_NORMALIZATION_RESPONSE_VALUE_IDENTIFIER]
            ):
                spoke_identifiers.append(
                    node_type_config[NODE_NORMALIZATION_KEY_FUNCTION](identifier[NODE_NORMALIZATION_RESPONSE_VALUE_IDENTIFIER])
                )
    return spoke_identifiers
