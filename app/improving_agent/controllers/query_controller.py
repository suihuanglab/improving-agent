import connexion
import six

from improving_agent import util
from improving_agent.models.response import Response  # noqa: E501
from improving_agent.models.query import Query  # noqa: E501
from improving_agent.src import core


def query_post(request_body):  # noqa: E501
    """Query reasoner via one of several inputs

     # noqa: E501

    :param request_body: Query information to be submitted
    :type request_body: Dict[str, ]

    :rtype: Response
    """
    if connexion.request.is_json:
        request_json = connexion.request.get_json()
        return core.try_query(request_json)
    else:
        return ('Request was not json', 400)
