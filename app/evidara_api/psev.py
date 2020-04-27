import numpy

from evidara_api import config
from evidara_api.util import get_evidara_logger

logger = get_evidara_logger(__name__)
# PSEV = propagated spoke entry vector

# open resources; note that future versions might not load the entire
# psev matrix into memory if it is very large, rather loading at
# a specific byte position (psev) should be considered
PSEV_MATRIX = numpy.load(config.PSEV_MATRIX)
PSEV_NODE_MAP = numpy.vectorize(lambda x: x.decode("UTF-8"))(
    numpy.load(config.PSEV_NODE_MAP)
)
PSEV_DISEASE_MAP = numpy.load(config.PSEV_DISEASE_MAP)


def get_psev_weights(
    node_identifier,
    disease_identifier,
    psev_matrix=PSEV_MATRIX,
    id_map=PSEV_NODE_MAP,
    disease_map=PSEV_DISEASE_MAP,
):
    """Returns a list of psev values for a SPOKE node

    Parameters
    ----------
    node_identifier (str or int): a SPOKE node's `identifier` property
    disease_identifier (str or int): a DOID identifier corresponding to 
        disease represented in the `psev-matrix`
    psev_matrix (numpy.ndarray): array of propagated spoke entry vectors
    id_map (numpy.ndarray): 1-d array of string spoke node identifiers
    disease_map (numpy.ndarray): 1-d array of disease DOID identifiers

    Returns
    -------
    <unnamed> (float): the psev weighting for the node specified by
        `node_identifier`

    RFE: this could support lists of node_identifiers as commented below
    """

    # return multiple if functionality is needed
    # if isinstance(node_identifier, list):
    #    node_array = numpy.array([str(i) for i in node_identifier])
    #    return psev_matrix[numpy.where(node_array.reshape(-1,1)==id_map)[1]]
    try:
        return float(
            psev_matrix[
                numpy.where(str(disease_identifier) == disease_map),
                numpy.where(str(node_identifier) == id_map),
            ][0]
        )
    except:
        logger.error(f"Couldn't find {disease_identifier}, {node_identifier} in psev")
        return float(0)
