BIOLINK_SPOKE_NODE_MAPPINGS = {
    # biolink type: (spoke node type, curie handling op)
    "biolink:BiologicalProcess": ("BiologicalProcess", "no-split"),
    "biolink:Cell": ("CellType", "no-split"),
    "biolink:CellularComponent": ("CellularComponent", "no-split"),
    "biolink:ChemicalSubstance": ("Compound", "no-split"),
    "biolink:Disease": ("Disease", "no-split"),
    "biolink:Gene": ("Gene", "split"),
    "biolink:GrossAnatomicalStructure": ("Anatomy", "no-split"),
    "biolink:MolecularActivity": ("MolecularFunction", "no-split"),
    "biolink:Pathway": ("Pathway", "no-split"),
    "biolink:PhenotypicFeature": ("Symptom", "split"),
    "biolink:Protein": ("Protein", "split"),

    # for "any node type"
    "biolink:NamedThing": (False, "no-split"),

    # missing
    # : "PharmacologicClass",
    # : "SideEffect",
    # : "Food"
}

SPOKE_BIOLINK_NODE_MAPPINGS = {
    "Anatomy": "biolink:GrossAnatomicalStructure",
    "AnatomyCellType": "biolink:NamedThing",
    "BiologicalProcess": "biolink:BiologicalProcess",
    "CellType": "biolink:Cell",
    "CellularComponent": "biolink:CellularComponent",
    "Compound": "biolink:ChemicalSubstance",
    "Disease": "biolink:Disease",
    "Food": "biolink:NamedThing",
    "Gene": "biolink:Gene",
    "MolecularFunction": "biolink:MolecularActivity",
    "Nutrient": "biolink:NamedThing",
    "Pathway": "biolink:Pathway",
    "PharmacologicClass": "biolink:NamedThing",
    "Protein": "biolink:Protein",
    "SideEffect": "biolink:NamedThing",
    "Symptom": "biolink:PhenotypicFeature",
}

SPOKE_BIOLINK_EDGE_MAPPINGS = {}
#     : "EXPRESSES_AeG",
#     : "PARTICIPATES_GpMF",
#     : "INTERACTS_GiG",
#     : "DOWNREGULATES_AdG",
#     : "PARTICIPATES_GpBP",
#     : "UPREGULATES_AuG",
#     : "COVARIES_GcG",
#     : "PARTICIPATES_GpPW",
#     : "PARTICIPATES_GpCC",
#     : "UPREGULATES_DuG",
#     : "ASSOCIATES_DaG",
#     : "TRANSLATEDFROM_PtG",
#     : "CAUSES_CcSE",
#     : "BINDS_CbP",
#     : "CONTRAINDICATES_CcD",
#     : "INCLUDES_PCiC",
#     : "RESEMBLES_CrC",
#     : "DOWNREGULATES_CdG",
#     : "UPREGULATES_CuG",
#     : "REGULATES_GrG",
#     : "DOWNREGULATES_DdG",
#     : "TREATS_CtD",
#     : "AFFECTS_CamG",
#     : "PALLIATES_CpD",
#     : "LOCALIZES_DlA",
#     : "PRESENTS_DpS",
#     : "RESEMBLES_DrD",
#     : "ISA_DiD",
#     : "CONTAINS_DcD",
#     : "INTERACTS_CiP",
#     : "ISA_AiA",
#     : "CONTAINS_AcA",
#     : "PARTOF_ApA",
#     : "CONTAINS_FcCM",
#     : "INTERACTS_PiP"
# }

BIOLINK_SPOKE_EDGE_MAPPINGS = {}
