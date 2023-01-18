"""This module is a WIP, with result handling features migrated here
as there is time.
"""


def get_edge_qualifiers(qualifier_map):
    qualifiers = []
    for qualifier_type, value in qualifier_map.items():
        qualifiers.append({
            'qualifier_type_id': qualifier_type,
            'qualifier_value': value,
        })
    return qualifiers
