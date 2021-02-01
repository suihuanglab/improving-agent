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


class UnmatchedIdentifierError(Exception):
    """Raise when a request specifies a CURIE that cannot be mapped
    to SPOKE

    Note that this should result in a 200 response to the consumer
    with a helpful log message about the issue
    """

    pass


class UnsupportedTypeError(Exception):
    """Raise when a request specifies a category or predicate that
    imProving Agent does not support
    """
    pass
