from abc import ABC, abstractmethod
from typing import Any

from improving_agent.src.biolink.spoke_biolink_constants import KNOWLEDGE_TYPE_INFERRED


class TemplateQueryBase(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def do_query(self):
        """This method must be overridden in child classes to ensure
        that it is available to callers to access generically. It should
        execute the query and take a neo4j session as an arg 
        """
        pass

    @staticmethod
    @abstractmethod
    def matches_template(self):
        """This static method must be overridden in child classes to ensure
        that incoming queries can be matched against all the template
        supported by the class
        """
        pass

    @property
    @abstractmethod
    def template_query_name(self):
        """The name of the template query to use in log messages"""


def template_matches_inferred_one_hop(
    qedges: dict[Any],
    qnodes: dict[Any],
    allowed_subject_categories: list[str],
    allowed_object_categories: list[str],
    allowed_predicates: list[str],
) -> bool:
    if len(qedges) > 1:
        return False
    qedge = list(qedges.values())[0]
    if (
        qedge.knowledge_type != KNOWLEDGE_TYPE_INFERRED
        or qedge.predicates != allowed_predicates
    ):
        return False

    if len(qnodes) != 2:
        return False
    if not all(
        cat in allowed_subject_categories
        for cat
        in qnodes[qedge.subject].categories
    ):
        return False
    if not all(
        cat in allowed_object_categories
        for cat
        in qnodes[qedge.object].categories
    ):
        return False

    return True
