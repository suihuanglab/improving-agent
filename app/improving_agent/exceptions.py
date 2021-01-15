class MissingComponentError(Exception):
    """Raise when a query graph includes a subject-predicate-object 
    relationship that can't be completed given the edges and nodes
    included in the posted data"""

    pass


class UnmatchedIdentifierError(Exception):
    """Raise when a request specifies a CURIE that cannot be mapped
    to SPOKE

    Note that this should result in a 200 response to the consumer
    with a helpful log message about the issue
    """

    pass
