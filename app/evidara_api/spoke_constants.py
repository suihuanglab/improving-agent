BIOLINK_SPOKE_NODE_MAPPINGS = {
    # commented lines exist in SPOKE, but don't have exact equivalents in Biolink
    "Gene": "Gene",
    #:"SideEffect",
    "BiologicalProcess": "BiologicalProcess",
    "MolecularActivity":"MolecularFunction",
    "ChemicalSubstance": "Compound",
    "CellularComponent": "CellularComponent",
    #:"PharmacologicClass",
    "Pathway": "Pathway",
    "Disease": "Disease",
    #"":"Symptom",
    "GrossAnatomicalStructure": "Anatomy",
    "Protein": "Protein",
    #"": "Food"
}

SPOKE_BIOLINK_NODE_MAPPINGS = {
    "Gene": "Gene",
    "SideEffect": "Thing",
    "BiologicalProcess": "BiologicalProcess",
    "MolecularFunction": "MolecularActivity",
    "Compound": "ChemicalSubstance",
    "CellularComponent": "CellularComponent",
    "PharmacologicClass": "Thing",
    "Pathway": "Pathway",
    "Disease": "Disease",
    "Symptom": "Thing",
    "Anatomy": "GrossAnatomicalStructure",
    "Protein": "Protein",
    "Food": "Thing"
}

SPOKE_NODE_IDENTIFIERS = {
    "Compound": "chembl_id", # should also include drugbank as list
    "Protein": "identifier",
    "Gene": "identifier",
    "Anatomy": "identifier"
}

# BIOLINK_SPOKE_EDGE_MAPPINGS = {
# not worth it right now
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