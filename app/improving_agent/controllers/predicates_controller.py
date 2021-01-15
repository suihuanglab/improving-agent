import connexion
import six

from improving_agent import util
from improving_agent.src.spoke_biolink_constants import TRAPI_PREDICATES

def predicates_get():  # noqa: E501
    """Get supported relationships by source and target

     # noqa: E501


    :rtype: Dict[str, Dict[str, List[str]]]
    """
    return TRAPI_PREDICATES
