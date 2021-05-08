from collections import defaultdict

import connexion
import six

from improving_agent import util
from improving_agent.src.biolink.spoke_biolink_constants import PREDICATES

TRAPI_PREDICATES = defaultdict(dict)
for biolink_subject, biolink_objects in PREDICATES.items():
    for biolink_object, biolink_predicates in biolink_objects.items():
        TRAPI_PREDICATES[biolink_subject][biolink_object] = list(biolink_predicates.keys())

TRAPI_PREDICATES = {k: TRAPI_PREDICATES[k] for k in sorted(TRAPI_PREDICATES)}


def predicates_get():  # noqa: E501
    """Get supported relationships by source and target

     # noqa: E501


    :rtype: Dict[str, Dict[str, List[str]]]
    """
    return TRAPI_PREDICATES
