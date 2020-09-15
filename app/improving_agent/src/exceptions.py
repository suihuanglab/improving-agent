class MissingComponentError(Exception):
    """Raise when a query graph includes a subject-predicate-object 
    relationship that can't be completed given the edges and nodes
    included in the posted data"""

    pass
