class AmbiguousPredicateMappingError(Exception):
    """Raise when a specific predicate has been requested, but no
    specific SPOKE equivalent can be found because the subject or 
    object `category` is not specified

    This should raise a 400
    """
    pass


class MissingComponentError(Exception):
    """Raise when a query graph includes a subject-predicate-object 
    relationship that can't be completed given the edges and nodes
    included in the posted data

    This should result in a 400 to the consumer
    """

    pass


class NonLinearQueryError(Exception):
    """Raise when we encounter a non-linear graph query

    This should result in a 200 with empty message
    """
    pass


class NoResultsError(Exception):
    """Raise when we can't find any results

    This should result in a 200 with empty message
    """
    pass


class TemplateQuerySpecError(Exception):
    """Raise when a template query fails because it is not specified
    as expected
    """
    pass


class UnmatchedIdentifierError(Exception):
    """Raise when a request specifies a CURIE that cannot be mapped
    to SPOKE

    Note that this should result in a 200 response to the consumer
    with a helpful log message about the issue
    """

    pass


class UnsupportedConstraint(Exception):
    """Raise when the component does not support a specific constraint.

    NOTE: this is required per the TRAPI implementation rules:
    https://github.com/NCATSTranslator/ReasonerAPI/blob/master/ImplementationRules.md#qnodeconstraints
    """
    pass


class UnsupportedKnowledgeType(Exception):
    """Raise when a qedge has a knowledge type attribute that is not
    supported.
    """
    pass


class UnsupportedQualifier(Exception):
    """Raise when a qualifier or combination thereof is not supported

    This should result in a 200 with an empty message
    """
    pass


class UnsupportedSetInterpretation(Exception):
    """Raise if we get a set interpretation that we do not support

        This should raise 501, Not Implemented
    """
    pass


class UnsupportedTypeError(Exception):
    """Raise when a request specifies a category or predicate that
    imProving Agent does not support

    This should result in a 200 with an empty message
    """
    pass
