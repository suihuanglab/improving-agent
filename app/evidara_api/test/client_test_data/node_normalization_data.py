"""This module holds test data used for testing the node normalization 
client"""
CHEMICAL_SUBSTANCE_CURIE_PREFIXES = {
    "chemical_substance": {
        "curie_prefix": [
            {
                "PUBCHEM": 200038,
                "INCHIKEY": 199545,
                "MESH": 564,
                "CHEMBL.COMPOUND": 3925,
                "HMDB": 231,
                "DRUGBANK": 27,
                "CHEBI": 258,
                "UNII": 167,
                "KEGG.COMPOUND": 43,
                "GTOPDB": 16
            }
        ]
    }
}

GENE_CURIE_PREFIXES = {
  "gene": {
        "curie_prefix": [
            {
                "NCBIGene": 41740,
                "ENSEMBL": 38556,
                "HGNC": 43545,
                "UniProtKB": 20292,
                "IUPHAR": 2927
            }
        ]
    }
}

NORMALIZED_WATER_NODE = {
  "MESH:D014867": {
        "id": {
            "identifier": "CHEBI:15377",
            "label": "water"
        },
        "equivalent_identifiers": [
            {
                "identifier": "CHEBI:15377",
                "label": "water"
            },
            {
                "identifier": "CHEMBL.COMPOUND:CHEMBL1098659",
                "label": "WATER"
            },
            {
                "identifier": "DRUGBANK:DB09145"
            },
            {
                "identifier": "PUBCHEM:962"
            },
            {
                "identifier": "PUBCHEM:22247451"
            },
            {
                "identifier": "MESH:D014867",
                "label": "Water"
            },
            {
                "identifier": "HMDB:HMDB0002111"
            },
            {
                "identifier": "INCHIKEY:QOBKEONCLBCUMN-UHFFFAOYSA-N"
            },
            {
                "identifier": "UNII:059QF0KO0R"
            },
            {
                "identifier": "KEGG.COMPOUND:C00001",
                "label": "H2O"
            }
        ],
        "type": [
            "chemical_substance",
            "molecular_entity",
            "biological_entity",
            "named_thing"
        ]
    }
}

SEMANTIC_TYPES = {
    "semantic_types": {
        "types": [
            "chemical_substance",
            "pathway",
            "gene",
            "named_thing",
            "cellular_component",
            "molecular_activity",
            "macromolecular_machine",
            "anatomical_entity",
            "genomic_entity",
            "organismal_entity",
            "disease_or_phenotypic_feature",
            "phenotypic_feature",
            "gene_family",
            "organism_taxon",
            "gene_or_gene_product",
            "biological_process_or_activity",
            "biological_entity",
            "disease",
            "biological_process",
            "molecular_entity",
            "ontology_class",
            "cell"
        ]
    }
}
