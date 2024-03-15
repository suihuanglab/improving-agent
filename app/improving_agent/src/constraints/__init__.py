from collections import defaultdict
from numbers import Number

from improving_agent.exceptions import UnsupportedConstraint
from improving_agent.models import AttributeConstraint, QEdge
from improving_agent.src.biolink.spoke_biolink_constants import (
    BIOLINK_SLOT_HIGHEST_FDA_APPROVAL,
    BIOLINK_SLOT_MAX_RESEARCH_PHASE,
    BL_MAX_RESEARCH_PHASE_SPOKE_PHASE_ENUM_MAP,
    FDA_APPROVAL_MAX_PHASE_MAP,
    SPOKE_ANY_TYPE,
    SPOKE_BIOLINK_EDGE_ATTRIBUTE_MAPPINGS,
    SPOKE_BIOLINK_NODE_ATTRIBUTE_MAPPINGS,
    SPOKE_BIOLINK_NODE_MAPPINGS
)


SUPPORTED_CONSTRAINT_ATTRIBUTES = [
    BIOLINK_SLOT_HIGHEST_FDA_APPROVAL,
    BIOLINK_SLOT_MAX_RESEARCH_PHASE,
]

SPECIAL_CONSTRAINT_HANDLERS = {}

TRAPI_CONSTRAINT_MATCHES_OPERATOR = 'matches'
TRAPI_CONSTRAINT_CYPHER_OPERATOR_MAP = {
    '==': '=',
    TRAPI_CONSTRAINT_MATCHES_OPERATOR: '=~',
    '>': '>',
    '<': '<'
}
NEGATED_TRAPI_CONSTRAINT_CYPHER_OPERATOR_MAP = {
    '==': '<>',
    '>': '<=',
    '<': '>='
}
# this could be moved into the big constants file, but for now, it's only
# needed here and we may want some logic to dedupe many-to-one mappings
BIOLINK_SPOKE_NODE_ATTRIBUTE_MAPPINGS = {}
for node, attributes in SPOKE_BIOLINK_NODE_ATTRIBUTE_MAPPINGS.items():
    BIOLINK_SPOKE_NODE_ATTRIBUTE_MAPPINGS[node] = defaultdict(list)
    for spoke_property, biolink_mapping in attributes.items():
        BIOLINK_SPOKE_NODE_ATTRIBUTE_MAPPINGS[node][biolink_mapping.biolink_type].append(spoke_property)

BIOLINK_SPOKE_EDGE_ATTRIBUTE_MAPPINGS = {}
for node, attributes in SPOKE_BIOLINK_EDGE_ATTRIBUTE_MAPPINGS.items():
    BIOLINK_SPOKE_EDGE_ATTRIBUTE_MAPPINGS[node] = defaultdict(list)
    for spoke_property, biolink_mapping in attributes.items():
        BIOLINK_SPOKE_EDGE_ATTRIBUTE_MAPPINGS[node][biolink_mapping.biolink_type].append(spoke_property)

def special_constraint(biolink_slot):
    def wrapper(f):
        SPECIAL_CONSTRAINT_HANDLERS[biolink_slot] = f
        return f
    return wrapper


def validate_constraint_support(constraint, spoke_labels):
    '''Raises if a constraint is not supported for any of spoke_labels

    Parameters
    ----------
    constraint (models.AttributeConstraint): single constraint on a QNode
    spoke_labels (list of str): list of spoke labels attached to a QNode
    '''
    if constraint.unit_id is not None or constraint.unit_name is not None:
        raise UnsupportedConstraint(
            'imProving Agent does not support constraints with units'
        )

    # TODO: eventually, all properties/attrs should be supported and this check
    # against a constant can be removed and we can implement logic specific
    # to the Entity or predicate
    if constraint.id not in SUPPORTED_CONSTRAINT_ATTRIBUTES:
        raise UnsupportedConstraint(
            f'imProving Agent does not support constraints on {constraint.id}'
        )

    if not spoke_labels:
        return True

    inspected_biolink_types = []
    for spoke_label in spoke_labels:
        if spoke_label == SPOKE_ANY_TYPE:
            return True

        inspected_biolink_types.append(SPOKE_BIOLINK_NODE_MAPPINGS[spoke_label])
        node_attributes = BIOLINK_SPOKE_NODE_ATTRIBUTE_MAPPINGS[spoke_label]
        spoke_properties = node_attributes.get(constraint.id)
        if not spoke_properties:
            continue
        return True

    raise UnsupportedConstraint(
        f'imProving Agent does not support constraints on {constraint.id} for the '
        f'given or inferred nodes of types={", ".join(inspected_biolink_types)}'
    )


@special_constraint(BIOLINK_SLOT_HIGHEST_FDA_APPROVAL)
def _map_fda_enum(constraint_value):
    mapped_val = FDA_APPROVAL_MAX_PHASE_MAP.get(constraint_value)
    if not mapped_val:
        raise UnsupportedConstraint(
            f'Cannot handle "{constraint_value}" for constraint "{BIOLINK_SLOT_HIGHEST_FDA_APPROVAL}"'
        )
    return mapped_val


@special_constraint(BIOLINK_SLOT_MAX_RESEARCH_PHASE)
def _map_research_phase_enum(constraint_value):
    mapped_val = BL_MAX_RESEARCH_PHASE_SPOKE_PHASE_ENUM_MAP.get(constraint_value)
    if not mapped_val:
        raise UnsupportedConstraint(
            f'Cannot handle "{constraint_value}" for constraint "{BIOLINK_SLOT_MAX_RESEARCH_PHASE}"'
        )
    return mapped_val


def _get_constraint_value(constraint_id, constraint_value):
    '''Inspects a constraint's id and value to determine if it needs to
    be transformed before looking in SPOKE.

    Parameters:
    constraint_id (str):
        name of the constraint; a biolink slot type

    constraint_value (any):
        the value of the constraint as defined by
        the caller

    NOTE: hopefully temporary to work with some of the enums in Biolink
    that have different values in SPOKE
    '''
    constraint_transformer = SPECIAL_CONSTRAINT_HANDLERS.get(constraint_id)
    if not constraint_transformer:
        return constraint_value

    if isinstance(constraint_value, list):
        return [constraint_transformer(val) for val in constraint_value]

    return constraint_transformer(constraint_value)


def _build_cypher_constraint_clause(
    name: str,
    constraint: AttributeConstraint,
    operator: str,
    spoke_properties: list[str],
) -> str:
    constraint_clause = ''
    constraint_value = _get_constraint_value(constraint.id, constraint.value)
    if not isinstance(constraint_value, list):
        constraint_value = [constraint_value]

    # TODO:
    # - create a revese mapping , i.e. max_phase to biolink enum that gets called when creating the Attribute in a result node
    for i, spoke_property in enumerate(spoke_properties):
        if i > 0:
            constraint_clause = f'{constraint_clause} OR '
        curr_constraint = f'({name}.{spoke_property}'
        if operator in ('>', '>=', '<', '<='):
            if operator in ('>', '>='):
                curr_constraint = f'{curr_constraint} {operator} {max(constraint_value)})'
            elif operator in ('<', '<='):
                curr_constraint = f'{curr_constraint} {operator} {min(constraint_value)})'
        elif operator == '=~':
            for val in constraint_value:
                if not isinstance(val, str):
                    raise UnsupportedConstraint(f'{TRAPI_CONSTRAINT_MATCHES_OPERATOR} should have string values')
            curr_constraint = f'{curr_constraint} {operator} {"|".join(constraint_value)})'
            continue
        elif operator in ('=', '<>'):
            # transform values for cypher list transform via join,
            # i.e. double-quote strings and single-quote ints
            # ','.join(["'foo'"", "'bar'"]) -> "['foo','bar']"; ','.join(['1', '2']) -> "[1, 2]"
            constraint_value = [str(i) if isinstance(i, Number) else f"'{i}'" for i in constraint_value]
            curr_constraint = f'{curr_constraint} '
            if operator == '<>':
                curr_constraint = f'{curr_constraint} NOT '
            curr_constraint = f'{curr_constraint} IN [{", ".join(constraint_value)}])'
        else:
            raise ValueError(f'Do not know what to do with constraint operator={operator} in constraint={constraint}')
        constraint_clause = f'{constraint_clause}{curr_constraint}'

    if constraint_clause:
        constraint_clause = f'({constraint_clause})'
    return constraint_clause


def get_node_constraint_cypher_clause(qnode, name, constraint):
    '''Returns a Cypher "WHERE" fragment that can be used when
    querying SPOKE.

    Parameters
    ----------
    qnode (models.QNode): a single QNode from the query graph
    name (str): Cypher alias for a given query part
    constraint (models.AttributeConstraint): a constraint on `qnode`

    TODO: consider moving to a dedicated Cypher compiler module
    '''
    spoke_properties = []
    for spoke_label in qnode.spoke_labels:
        if spoke_label == SPOKE_ANY_TYPE:
            continue

        node_attributes = BIOLINK_SPOKE_NODE_ATTRIBUTE_MAPPINGS[spoke_label]
        spoke_properties.extend(node_attributes.get(constraint.id, []))

    if constraint._not:
        if constraint.operator == TRAPI_CONSTRAINT_MATCHES_OPERATOR:
            raise UnsupportedConstraint(
                'imProving Agent can not reliably invert a regular expression'
            )
        operator = NEGATED_TRAPI_CONSTRAINT_CYPHER_OPERATOR_MAP[constraint.operator]
    else:
        operator = TRAPI_CONSTRAINT_CYPHER_OPERATOR_MAP[constraint.operator]

    return _build_cypher_constraint_clause(
        name,
        constraint,
        operator,
        spoke_properties,
    )

def get_edge_constraint_cypher_clause(
    qedge: QEdge,
    name: str,
    constraint: AttributeConstraint,
) -> str:
    spoke_properties = []
    for edge_type in qedge.spoke_edge_types:
        if edge_type == SPOKE_ANY_TYPE:
            continue
        edge_attributes = BIOLINK_SPOKE_EDGE_ATTRIBUTE_MAPPINGS[edge_type]
        spoke_properties.extend(edge_attributes.get(constraint.id, []))
    
    if constraint._not:
        if constraint.operator == TRAPI_CONSTRAINT_MATCHES_OPERATOR:
            raise UnsupportedConstraint(
                'imProving Agent can not reliably invert a regular expression'
            )
        operator = NEGATED_TRAPI_CONSTRAINT_CYPHER_OPERATOR_MAP[constraint.operator]
    else:
        operator = TRAPI_CONSTRAINT_CYPHER_OPERATOR_MAP[constraint.operator]
    return _build_cypher_constraint_clause(
        name,
        constraint,
        operator,
        spoke_properties,
    )
