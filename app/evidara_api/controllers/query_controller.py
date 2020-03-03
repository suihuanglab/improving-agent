import connexion
import six

from evidara_api.models.message import Message  # noqa: E501
from evidara_api.models.query import Query  # noqa: E501
from evidara_api import util
from evidara_api import core


def query(body):  # noqa: E501
    """Query reasoner via one of several inputs

     # noqa: E501

    :param body: Query information to be submitted
    :type body: dict | bytes

    :rtype: Message
    """
    if connexion.request.is_json:
        body = Query.from_dict(connexion.request.get_json())  # noqa: E501
    # print(body)
    # print(type(body))
    # print(body.query_message)
    # q_message = Message(**body.query_message)
    # print(q_message)
    # print(type(body.query_message))
    # print(type(q_message))
    # print(body.query_message["query_graph"])
    return core.process_query(body)
