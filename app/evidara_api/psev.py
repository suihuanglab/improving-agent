import numpy

from evidara_api import config

# PSEV = propagated spoke entry vector

# open resources; note that future versions might not load the entire
# psev matrix into memory if it is very large, rather loading at
# a specific byte position (psev) should be considered
PSEV_MATRIX = numpy.load(config.PSEV_MATRIX)
PSEV_MAP = numpy.vectorize(lambda x: x.decode("UTF-8"))(numpy.load(config.PSEV_MAP))


def get_psev_weights(node_identifier, psev_matrix=PSEV_MATRIX, id_map=PSEV_MAP):
    """Returns a list of psev values for a SPOKE node

    Parameters
    ----------
    node_identifier (str): a SPOKE node's `identifier` property
    psev_matrix (numpy.ndarray): array of propagated spoke entry vectors
    id_map (numpy.ndarray): 1-d array of string spoke node identifiers

    Returns
    -------
    <unnamed> (float): the psev weighting for the node specified by
        `node_identifier`

    RFE: this should support a 2-d psev-matrix (requires new arg)
    and could support lists of node_identifiers as commented below
    """

    # return multiple if functionality is needed
    # if isinstance(node_identifier, list):
    #    node_array = numpy.array([str(i) for i in node_identifier])
    #    return psev_matrix[numpy.where(node_array.reshape(-1,1)==id_map)[1]]
    return float(psev_matrix[numpy.where(str(node_identifier) == id_map)][0])
