from typing import Annotated
from xdsl.irdl import irdl_op_definition, AnyAttr, Operand, VarOperand, OpAttr, AnyOf, AttrConstraint
from xdsl.ir import Operation, Block, Attribute, OpResult, Region, Dialect
from xdsl.dialects.builtin import (IntegerAttr, UnitAttr, StringAttr,
                                   ArrayAttr, SymbolRefAttr,
                                   DenseIntOrFPElementsAttr)
from pdl import (AttributeType as PdlAttributeType, TypeType as PdlTypeType,
                 OperationType as PdlOperationType, RangeType as PdlRangeType,
                 ValueType as PdlValueType, RangeValue)

# todo: traits, interfaces, effects, successor constraints

AnyPdlType: AttrConstraint = AnyOf(
    [PdlAttributeType, PdlTypeType, PdlValueType, PdlOperationType])
SingleOrManyPdlValues: AttrConstraint = AnyOf(
    [PdlValueType, PdlRangeType(RangeValue.VALUE)])
SingleOrManyPdlTypes: AttrConstraint = AnyOf(
    [PdlValueType, PdlRangeType(RangeValue.TYPE)])


@irdl_op_definition
class PdlInterpAreEqual(Operation):
    name = "pdl_interp.are_equal"

    # todo: equality constraint
    lhs: Annotated[Operand, AnyPdlType]
    rhs: Annotated[Operand, AnyPdlType]


@irdl_op_definition
class PdlInterpBranch(Operation):
    name = "pdl_interp.branch"


@irdl_op_definition
class PdlInterpCheckAttribute(Operation):
    name = "pdl_interp.check_attribute"

    constant_value: OpAttr[AnyAttr()]
    attribute: Annotated[Operand, PdlAttributeType]


@irdl_op_definition
class PdlInterpCheckOperandCount(Operation):
    name = "pdl_interp.check_operand_count"

    count: OpAttr[IntegerAttr]
    compare_at_least: OpAttr[UnitAttr]
    input_op: Annotated[Operand, PdlOperationType]


@irdl_op_definition
class PdlInterpCheckOperationName(Operation):
    name = "pdl_interp.check_operation_name"

    name: OpAttr[StringAttr]
    input_op: Annotated[Operand, PdlOperationType]


@irdl_op_definition
class PdlInterpCheckResultCount(Operation):
    name = "pdl_interp.check_result_count"

    count: OpAttr[IntegerAttr]
    compare_at_least: OpAttr[UnitAttr]
    input_op: Annotated[Operand, PdlOperationType]


@irdl_op_definition
class PdlInterpCheckType(Operation):
    name = "pdl_interp.check_type"

    type: OpAttr[AnyAttr()]
    value: Annotated[Operand, PdlTypeType]


@irdl_op_definition
class PdlInterpCheckTypes(Operation):
    name = "pdl_interp.check_types"

    type: OpAttr[ArrayAttr]
    value: Annotated[Operand, PdlRangeType(RangeValue.TYPE)]


@irdl_op_definition
class PdlInterpContinue(Operation):
    name = "pdl_interp.continue"


@irdl_op_definition
class PdlInterpCreateAttribute(Operation):
    name = "pdl_interp.create_attribute"

    value: OpAttr[AnyAttr()]
    attribute: Annotated[OpResult, PdlAttributeType]


@irdl_op_definition
class PdlInterpCreateOperation(Operation):
    name = "pdl_interp.create_operation"

    name: OpAttr[StringAttr]
    input_attribute_names: OpAttr[ArrayAttr]
    inferred_result_types: OpAttr[UnitAttr]
    input_operands: Annotated[Operand, SingleOrManyPdlValues]
    input_attributes: Annotated[Operand, PdlAttributeType]
    input_result_types: Annotated[Operand, SingleOrManyPdlTypes]
    result_op: Annotated[OpResult, PdlOperationType]


@irdl_op_definition
class PdlInterpCreateRange(Operation):
    name = "pdl_interp.create_range"

    arguments: Annotated[VarOperand, AnyAttr()]  # todo: constraints
    result: Annotated[OpResult, AnyAttr()]  # todo: constraints


@irdl_op_definition
class PdlInterpCreateType(Operation):
    name = "pdl_interp.create_type"

    value: Annotated[Operand, AnyAttr()]
    result: Annotated[OpResult, PdlTypeType]


@irdl_op_definition
class PdlInterpCreateTypes(Operation):
    name = "pdl_interp.create_types"

    value: Annotated[Operand, ArrayAttr]
    result: Annotated[OpResult, PdlRangeType(RangeValue.TYPE)]


@irdl_op_definition
class PdlInterpErase(Operation):
    name = "pdl_interp.erase"

    input_op: Annotated[Operand, PdlOperationType]


@irdl_op_definition
class PdlInterpExtract(Operation):
    name = "pdl_interp.extract"

    # todo: equality constraints
    index: Annotated[Operand, IntegerAttr]
    range: Annotated[Operand, PdlRangeType]
    result: Annotated[OpResult, AnyPdlType]


@irdl_op_definition
class PdlInterpFinalize(Operation):
    name = "pdl_interp.finalize"


@irdl_op_definition
class PdlInterpForeach(Operation):
    name = "pdl_interp.foreach"

    values: Annotated[Operand, PdlRangeType]

    region: Region


@irdl_op_definition
class PdlInterpFunc(Operation):
    name = "pdl_interp.func"

    sym_name: OpAttr[StringAttr]
    function_type: OpAttr[AnyAttr()]
    arg_attrs: OpAttr[ArrayAttr]
    res_attrs: OpAttr[ArrayAttr]
    values: Annotated[Operand, PdlRangeType]

    region: Region


@irdl_op_definition
class PdlInterpGetAttribute(Operation):
    name = "pdl_interp.get_attribute"

    name: OpAttr[StringAttr]
    input_op: Annotated[Operand, PdlOperationType]
    attribute: Annotated[OpResult, PdlAttributeType]


@irdl_op_definition
class PdlInterpGetAttributeType(Operation):
    name = "pdl_interp.get_attribute_type"

    value: Annotated[Operand, PdlAttributeType]
    result: Annotated[OpResult, PdlTypeType]


@irdl_op_definition
class PdlInterpGetDefiningOp(Operation):
    name = "pdl_interp.get_defining_op"

    value: Annotated[Operand, PdlAttributeType]
    inputOp: Annotated[OpResult, PdlOperationType]


@irdl_op_definition
class PdlInterpGetOperand(Operation):
    name = "pdl_interp.get_operand"

    index: OpAttr[IntegerAttr]
    inputOp: Annotated[Operand, PdlOperationType]
    value: Annotated[OpResult, PdlValueType]


@irdl_op_definition  #pdl.operatio
class PdlInterpGetOperands(Operation):
    name = "pdl_interp.get_operands"

    index: OpAttr[IntegerAttr]
    inputOp: Annotated[Operand, PdlOperationType]
    value: Annotated[OpResult, PdlRangeType(RangeValue.VALUE)]


@irdl_op_definition
class PdlInterpGetResult(Operation):
    name = "pdl_interp.get_result"

    index: OpAttr[IntegerAttr]
    inputOp: Annotated[Operand, PdlOperationType]
    value: Annotated[OpResult, PdlValueType]


@irdl_op_definition
class PdlInterpGetResults(Operation):
    name = "pdl_interp.get_results"

    index: OpAttr[IntegerAttr]
    inputOp: Annotated[Operand, PdlOperationType]
    value: Annotated[OpResult, PdlRangeType(RangeValue.VALUE)]


@irdl_op_definition
class PdlInterpGetUsers(Operation):
    name = "pdl_interp.get_users"

    inputOp: Annotated[Operand, PdlOperationType]
    operations: Annotated[OpResult, PdlRangeType(RangeValue.OPERATION)]


@irdl_op_definition
class PdlInterpGetValueType(Operation):
    name = "pdl_interp.get_value_type"

    value: Annotated[Operand, PdlValueType]
    result: Annotated[OpResult, SingleOrManyPdlTypes]


@irdl_op_definition
class PdlInterpIsNotNull(Operation):
    name = "pdl_interp.is_not_null"

    value: Annotated[Operand, AnyPdlType]


@irdl_op_definition
class PdlInterpRecordMatch(Operation):
    name = "pdl_interp.record_match"

    rewriter: OpAttr[SymbolRefAttr]
    root_kind: OpAttr[StringAttr]
    generated_ops: OpAttr[ArrayAttr[StringAttr]]
    benefit: OpAttr[IntegerAttr]
    inputs: Annotated[Operand, AnyPdlType]
    matched_ops: Annotated[Operand, PdlOperationType]


@irdl_op_definition
class PdlInterpReplace(Operation):
    name = "pdl_interp.replace"

    inputOp: Annotated[Operand, PdlOperationType]
    matched_ops: Annotated[Operand, SingleOrManyPdlValues]


@irdl_op_definition
class PdlSwitchAttribute(Operation):
    name = "pdl_interp.switch_attribute"

    case_values: OpAttr[ArrayAttr]
    attribute: Annotated[Operand, PdlAttributeType]


@irdl_op_definition
class PdlSwitchOperandCount(Operation):
    name = "pdl_interp.switch_operand_count"

    case_values: OpAttr[DenseIntOrFPElementsAttr]
    input_op: Annotated[Operand, PdlOperationType]


@irdl_op_definition
class PdlSwitchOperationName(Operation):
    name = "pdl_interp.switch_operation_name"

    case_values: OpAttr[ArrayAttr[StringAttr]]
    input_op: Annotated[Operand, PdlOperationType]


@irdl_op_definition
class PdlSwitchResultCount(Operation):
    name = "pdl_interp.switch_result_count"

    case_values: OpAttr[DenseIntOrFPElementsAttr]
    input_op: Annotated[Operand, PdlOperationType]


@irdl_op_definition
class PdlSwitchType(Operation):
    name = "pdl_interp.switch_type"

    case_values: OpAttr[ArrayAttr]
    input_op: Annotated[Operand, PdlTypeType]


@irdl_op_definition
class PdlSwitchTypes(Operation):
    name = "pdl_interp.switch_types"

    case_values: OpAttr[ArrayAttr[ArrayAttr]]
    input_op: Annotated[Operand, PdlRangeType(RangeValue.TYPE)]


PdlInterp = Dialect([
    PdlInterpAreEqual, PdlInterpBranch, PdlInterpCheckAttribute,
    PdlInterpCheckOperandCount, PdlInterpCheckOperationName,
    PdlInterpCheckResultCount, PdlInterpCheckType, PdlInterpCheckTypes,
    PdlInterpContinue, PdlInterpCreateAttribute, PdlInterpCreateOperation,
    PdlInterpCreateRange, PdlInterpCreateType, PdlInterpCreateTypes,
    PdlInterpErase, PdlInterpExtract, PdlInterpFinalize, PdlInterpForeach,
    PdlInterpFunc, PdlInterpGetAttribute, PdlInterpGetAttributeType,
    PdlInterpGetDefiningOp, PdlInterpGetOperand, PdlInterpGetOperands,
    PdlInterpGetResult, PdlInterpGetResults, PdlInterpGetUsers,
    PdlInterpGetValueType, PdlInterpIsNotNull, PdlInterpRecordMatch,
    PdlInterpReplace, PdlSwitchAttribute, PdlSwitchOperandCount,
    PdlSwitchOperationName, PdlSwitchResultCount, PdlSwitchType, PdlSwitchTypes
], [])
