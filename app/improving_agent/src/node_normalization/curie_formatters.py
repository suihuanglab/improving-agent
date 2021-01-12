"""This module provides functions to format curies for search against
the SRI Node Normalizer

Note that the following identifiers don't necessarily need to be normalized:
SPOKE type          |  biolink type               |  spoke curie format |  notes
--------------------|-----------------------------|-------------------  |------------------------------------------
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

NODE_NORMALIZATION_CURIE_QUERY_FORMATTERS = defaultdict(dict)


def register_curie_formatter(node_type, regex):  # TODO: inclue the node type here
    def wrapper(f):
        NODE_NORMALIZATION_CURIE_QUERY_FORMATTERS[node_type][regex] = f
        return f
    return wrapper


@register_curie_formatter('biolink:ChemicalSubstance', '^CHEMBL[0-9]+')
def _format_chembl(curie):
    return f"CHEMBL.COMPOUND:{curie}"


@register_curie_formatter('biolink:ChemicalSubstance', '^DB[0-9]+')
def _format_drugbank(curie):
    return f"DRUGBANK:{curie}"


@register_curie_formatter('biolink:Gene', '^[0-9]+')
def _format_ncbigene(curie):
    return f'NCBIGene:{curie}'


@register_curie_formatter('biolink:Protein', '[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}')
def _format_protein(curie):
    return f'UniProt:{curie}'


@register_curie_formatter('biolink:PhenotypicFeature', '^D[0-9]+')
def _format_symptom(curie):
    return f'MESH:{curie}'


def format_curie(search_node):
    format_funcs = NODE_NORMALIZATION_CURIE_QUERY_FORMATTERS.get(search_node.node_type)
    if not format_funcs:
        return search_node.curie
    for regex, format_func in format_funcs.items():
        if re.match(regex, str(search_node.curie)):
            return format_func(search_node.curie)

    return search_node.curie
