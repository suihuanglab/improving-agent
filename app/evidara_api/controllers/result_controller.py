import connexion
import six

from evidara_api.models.result import Result  # noqa: E501
from evidara_api import util


def get_result(result_id):  # noqa: E501
    """Request stored result

     # noqa: E501

    :param result_id: Integer identifier of the result to return
    :type result_id: int

    :rtype: Result
    """
    return "do some magic!"
