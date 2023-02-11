from typing import Annotated
from xdsl.irdl import irdl_op_definition, AnyAttr, Operand, VarOperand
from xdsl.ir import Operation, Block, Attribute, OpResult, Region
from xdsl.dialects.builtin import IntegerAttr, UnitAttr, StringAttr, ArrayAttr
from pdl import AttributeType as PdlAttributeType, TypeType as PdlTypeType, OperationType as PdlOperationType, RangeType as PdlRangeType, ValueType as PdlValueType

# todo: traits, interfaces, effects


@irdl_op_definition
class PdlInterpAreEqual(Operation):
    name = "pdl_interp.are_equal"

    lhs: Annotated[Operand, AnyAttr]  # todo: constraints
    rhs: Annotated[Operand, AnyAttr]  # todo: constraints

    true_dest: Annotated[Block, AnyAttr]
    false_dest: Annotated[Block, AnyAttr]


@irdl_op_definition
class PdlInterpBranch(Operation):
    name = "pdl_interp.branch"

    dest: Annotated[Block, AnyAttr]


@irdl_op_definition
class PdlInterpCheckAttribute(Operation):
    name = "pdl_interp.check_attribute"

    constant_value: Annotated[Attribute, AnyAttr]
    attribute: Annotated[Operand, PdlAttributeType]

    true_dest: Annotated[Block, AnyAttr]
    false_dest: Annotated[Block, AnyAttr]


@irdl_op_definition
class PdlInterpCheckOperandCount(Operation):
    name = "pdl_interp.check_operand_count"

    count: Annotated[Attribute, IntegerAttr]
    compare_at_least: Annotated[Attribute, UnitAttr]
    input_op: Annotated[Operand, PdlOperationType]

    true_dest: Annotated[Block, AnyAttr]
    false_dest: Annotated[Block, AnyAttr]


@irdl_op_definition
class PdlInterpCheckOperationName(Operation):
    name = "pdl_interp.check_operation_name"

    name: Annotated[Attribute, StringAttr]
    input_op: Annotated[Operand, PdlOperationType]

    true_dest: Annotated[Block, AnyAttr]
    false_dest: Annotated[Block, AnyAttr]


@irdl_op_definition
class PdlInterpCheckResultCount(Operation):
    name = "pdl_interp.check_result_count"

    count: Annotated[Attribute, IntegerAttr]
    compare_at_least: Annotated[Attribute, UnitAttr]
    input_op: Annotated[Operand, PdlOperationType]

    true_dest: Annotated[Block, AnyAttr]
    false_dest: Annotated[Block, AnyAttr]


@irdl_op_definition
class PdlInterpCheckType(Operation):
    name = "pdl_interp.check_type"

    type: Annotated[Attribute, AnyAttr]
    value: Annotated[Operand, PdlTypeType]

    true_dest: Annotated[Block, AnyAttr]
    false_dest: Annotated[Block, AnyAttr]


@irdl_op_definition
class PdlInterpCheckTypes(Operation):
    name = "pdl_interp.check_types"

    type: Annotated[Attribute, ArrayAttr]
    value: Annotated[Operand, PdlRangeType]  # todo: constraints

    true_dest: Annotated[Block, AnyAttr]
    false_dest: Annotated[Block, AnyAttr]


@irdl_op_definition
class PdlInterpContinue(Operation):
    name = "pdl_interp.continue"


@irdl_op_definition
class PdlInterpCreateAttribute(Operation):
    name = "pdl_interp.create_attribute"

    value: Annotated[Attribute, AnyAttr]
    attribute: Annotated[OpResult, PdlAttributeType]


@irdl_op_definition
class PdlInterpCreateOperation(Operation):
    name = "pdl_interp.create_operation"

    name: Annotated[Attribute, StringAttr]
    input_attribute_names: Annotated[Attribute, ArrayAttr]
    inferred_result_types: Annotated[Attribute, UnitAttr]
    input_operands: Annotated[Operand, AnyAttr]  # todo: constraints
    input_attributes: Annotated[Operand, PdlAttributeType]
    input_result_types: Annotated[Operand, AnyAttr]  # todo: constraints
    result_op: Annotated[OpResult, PdlOperationType]


@irdl_op_definition
class PdlInterpCreateRange(Operation):
    name = "pdl_interp.create_range"

    arguments: Annotated[VarOperand, AnyAttr]  # todo: constraints
    result: Annotated[OpResult, AnyAttr]  # todo: constraints


@irdl_op_definition
class PdlInterpCreateType(Operation):
    name = "pdl_interp.create_type"

    value: Annotated[Operand, AnyAttr]
    result: Annotated[OpResult, PdlTypeType]


@irdl_op_definition
class PdlInterpCreateTypes(Operation):
    name = "pdl_interp.create_types"

    value: Annotated[Operand, ArrayAttr]
    result: Annotated[OpResult, PdlRangeType]  # todo: constraints


@irdl_op_definition
class PdlInterpErase(Operation):
    name = "pdl_interp.erase"

    input_op: Annotated[Operand, PdlOperationType]


@irdl_op_definition
class PdlInterpExtract(Operation):
    name = "pdl_interp.extract"

    index: Annotated[Operand, IntegerAttr]
    range: Annotated[Operand, PdlRangeType]
    result: Annotated[OpResult, AnyAttr]  # todo: constraints


@irdl_op_definition
class PdlInterpFinalize(Operation):
    name = "pdl_interp.finalize"


@irdl_op_definition
class PdlInterpForeach(Operation):
    name = "pdl_interp.foreach"

    values: Annotated[Operand, PdlRangeType]

    successor: Annotated[Block, AnyAttr]

    region: Region


@irdl_op_definition
class PdlInterpFunction(Operation):
    name = "pdl_interp.function"

    sym_name: Annotated[Attribute, StringAttr]
    function_type: Annotated[Attribute, AnyAttr]
    arg_attrs: Annotated[Attribute, ArrayAttr]
    res_attrs: Annotated[Attribute, ArrayAttr]
    values: Annotated[Operand, PdlRangeType]

    region: Region


@irdl_op_definition
class PdlInterpGetAttribute(Operation):
    name = "pdl_interp.get_attribute"

    name: Annotated[Attribute, StringAttr]
    input_op: Annotated[Operand, PdlOperationType]
    attribute: Annotated[OpResult, PdlAttributeType]


@irdl_op_definition
class PdlInterpGetAttributeType(Operation):
    name = "pdl_interp.get_attribute_type"

    value: Annotated[Operand, PdlAttributeType]
    result: Annotated[OpResult, PdlTypeType]


@irdl_op_definition
class PdlInterpGetAttributeType(Operation):
    name = "pdl_interp.get_defining_op"

    value: Annotated[Operand, PdlAttributeType]
    inputOp: Annotated[OpResult, PdlOperationType]


@irdl_op_definition
class PdlInterpGetOperand(Operation):
    name = "pdl_interp.get_operand"

    index: Annotated[Attribute, IntegerAttr]
    inputOp: Annotated[Operand, PdlOperationType]
    value: Annotated[OpResult, PdlValueType]


@irdl_op_definition
class PdlInterpGetOperands(Operation):
    name = "pdl_interp.get_operands"

    index: Annotated[Attribute, IntegerAttr]
    inputOp: Annotated[Operand, PdlOperationType]
    value: Annotated[OpResult, PdlRangeType]  # todo: constraints


@irdl_op_definition
class PdlInterpGetResult(Operation):
    name = "pdl_interp.get_result"

    index: Annotated[Attribute, IntegerAttr]
    inputOp: Annotated[Operand, PdlOperationType]
    value: Annotated[OpResult, PdlValueType]


@irdl_op_definition
class PdlInterpGetResults(Operation):
    name = "pdl_interp.get_results"

    index: Annotated[Attribute, IntegerAttr]
    inputOp: Annotated[Operand, PdlOperationType]
    value: Annotated[OpResult, PdlRangeType]  # todo: constraints


@irdl_op_definition
class PdlInterpGetUsers(Operation):
    name = "pdl_interp.get_users"

    inputOp: Annotated[Operand, PdlOperationType]
    operations: Annotated[OpResult, PdlRangeType]  # todo: constraints


@irdl_op_definition
class PdlInterpGetValueType(Operation):
    name = "pdl_interp.get_value_type"

    value: Annotated[Operand, PdlValueType]
    result: Annotated[OpResult, PdlTypeType]  # todo: constraints


@irdl_op_definition
class PdlInterpIsNotNull(Operation):
    name = "pdl_interp.is_not_null"

    value: Annotated[Operand, AnyAttr]  # todo: constraints

    true_dest: Annotated[Block, AnyAttr]
    false_dest: Annotated[Block, AnyAttr]
