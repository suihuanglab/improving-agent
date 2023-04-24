import connexion
import six
from typing import Dict
from typing import Tuple
from typing import Union

from improving_agent import util


def asyncquery_status(job_id):  # noqa: E501
    """Retrieve the current status of a previously submitted asyncquery given its job_id

     # noqa: E501

    :param job_id: Identifier of the job for status request
    :type job_id: str

    :rtype: Union[None, Tuple[None, int], Tuple[None, int, Dict[str, str]]
    """
    return "Not implemented", 501
