from typing import Annotated
from xdsl.irdl import (
    irdl_op_definition,
    AnyAttr,
    IRDLOperation,
    Operand,
    VarOperand,
    OpAttr,
    AnyOf,
    AttrConstraint,
)
from xdsl.ir import Operation, Block, Attribute, OpResult, Region, Dialect
from xdsl.dialects.builtin import (
    IntegerAttr,
    UnitAttr,
    StringAttr,
    ArrayAttr,
    SymbolRefAttr,
    DenseIntOrFPElementsAttr,
)
from .pdl import (
    AttributeType as PdlAttributeType,
    TypeType as PdlTypeType,
    OperationType as PdlOperationType,
    RangeType as PdlRangeType,
    ValueType as PdlValueType,
    RangeValue,
)
from xdsl.utils.exceptions import VerifyException

# todo: traits, interfaces, effects, successor constraints

AnyPdlType: AttrConstraint = AnyOf(
    [PdlAttributeType, PdlTypeType, PdlValueType, PdlOperationType]
)
SingleOrManyPdlValues: AttrConstraint = AnyOf(
    [PdlValueType, PdlRangeType(RangeValue.VALUE)]
)
SingleOrManyPdlTypes: AttrConstraint = AnyOf(
    [PdlValueType, PdlRangeType(RangeValue.TYPE)]
)


@irdl_op_definition
class PdlInterpAreEqual(IRDLOperation):
    name = "pdl_interp.are_equal"

    lhs: Annotated[Operand, AnyPdlType]
    rhs: Annotated[Operand, AnyPdlType]

    def verify_(self) -> None:
        if self.lhs.typ != self.rhs.typ:
            raise VerifyException(
                f"'{self.lhs}' is not of type the same type as '{self.rhs}'"
            )


@irdl_op_definition
class PdlInterpBranch(IRDLOperation):
    name = "pdl_interp.branch"


@irdl_op_definition
class PdlInterpCheckAttribute(IRDLOperation):
    name = "pdl_interp.check_attribute"

    constant_value: OpAttr[AnyAttr()]
    attribute: Annotated[Operand, PdlAttributeType]


@irdl_op_definition
class PdlInterpCheckOperandCount(IRDLOperation):
    name = "pdl_interp.check_operand_count"

    count: OpAttr[IntegerAttr]
    compare_at_least: OpAttr[UnitAttr]
    input_op: Annotated[Operand, PdlOperationType]


@irdl_op_definition
class PdlInterpCheckOperationName(IRDLOperation):
    name = "pdl_interp.check_operation_name"

    name: OpAttr[StringAttr]
    input_op: Annotated[Operand, PdlOperationType]


@irdl_op_definition
class PdlInterpCheckResultCount(IRDLOperation):
    name = "pdl_interp.check_result_count"

    count: OpAttr[IntegerAttr]
    compare_at_least: OpAttr[UnitAttr]
    input_op: Annotated[Operand, PdlOperationType]


@irdl_op_definition
class PdlInterpCheckType(IRDLOperation):
    name = "pdl_interp.check_type"

    type: OpAttr[AnyAttr()]
    value: Annotated[Operand, PdlTypeType]


@irdl_op_definition
class PdlInterpCheckTypes(IRDLOperation):
    name = "pdl_interp.check_types"

    types: OpAttr[ArrayAttr]
    value: Annotated[Operand, PdlRangeType(RangeValue.TYPE)]


@irdl_op_definition
class PdlInterpContinue(IRDLOperation):
    name = "pdl_interp.continue"


@irdl_op_definition
class PdlInterpCreateAttribute(IRDLOperation):
    name = "pdl_interp.create_attribute"

    value: OpAttr[AnyAttr()]
    attribute: Annotated[OpResult, PdlAttributeType]


@irdl_op_definition
class PdlInterpCreateOperation(IRDLOperation):
    name = "pdl_interp.create_operation"

    name: OpAttr[StringAttr]
    input_attribute_names: OpAttr[ArrayAttr]
    inferred_result_types: OpAttr[UnitAttr]
    input_operands: Annotated[Operand, SingleOrManyPdlValues]
    input_attributes: Annotated[Operand, PdlAttributeType]
    input_result_types: Annotated[Operand, SingleOrManyPdlTypes]
    result_op: Annotated[OpResult, PdlOperationType]


@irdl_op_definition
class PdlInterpCreateRange(IRDLOperation):
    name = "pdl_interp.create_range"

    arguments: Annotated[VarOperand, AnyAttr()]  # todo: constraints
    result: Annotated[OpResult, AnyAttr()]  # todo: constraints


@irdl_op_definition
class PdlInterpCreateType(IRDLOperation):
    name = "pdl_interp.create_type"

    value: Annotated[Operand, AnyAttr()]
    result: Annotated[OpResult, PdlTypeType]


@irdl_op_definition
class PdlInterpCreateTypes(IRDLOperation):
    name = "pdl_interp.create_types"

    value: Annotated[Operand, ArrayAttr]
    result: Annotated[OpResult, PdlRangeType(RangeValue.TYPE)]


@irdl_op_definition
class PdlInterpErase(IRDLOperation):
    name = "pdl_interp.erase"

    input_op: Annotated[Operand, PdlOperationType]


@irdl_op_definition
class PdlInterpExtract(IRDLOperation):
    name = "pdl_interp.extract"

    index: Annotated[Operand, IntegerAttr]
    range: Annotated[Operand, PdlRangeType]
    result: Annotated[OpResult, AnyPdlType]

    def verify_(self) -> None:
        if self.range.typ.data == RangeValue.ATTRIBUTE:
            if self.result.typ != PdlAttributeType:
                raise VerifyException(
                    f"extracting from attribute range '{self.range}' should "
                    f"yield an attribute and not '{self.result.typ}'"
                )
        elif self.range.typ.data == RangeValue.TYPE:
            if self.result.typ != PdlTypeType:
                raise VerifyException(
                    f"extracting from type range '{self.range}' should "
                    f"yield a type and not '{self.result.typ}'"
                )
        elif self.range.typ.data == RangeValue.OPERATION:
            if self.result.typ != PdlOperationType:
                raise VerifyException(
                    f"extracting from operation range '{self.range}' should "
                    f"yield an operation and not '{self.result.typ}'"
                )
        elif self.range.typ.data == RangeValue.VALUE:
            if self.result.typ != PdlValueType:
                raise VerifyException(
                    f"extracting from value range '{self.range}' should "
                    f"yield a value and not '{self.result.typ}'"
                )
        else:
            assert False, "unreachable range value"


@irdl_op_definition
class PdlInterpFinalize(IRDLOperation):
    name = "pdl_interp.finalize"


@irdl_op_definition
class PdlInterpForeach(IRDLOperation):
    name = "pdl_interp.foreach"

    values: Annotated[Operand, PdlRangeType]

    region: Region


@irdl_op_definition
class PdlInterpFunc(IRDLOperation):
    name = "pdl_interp.func"

    sym_name: OpAttr[StringAttr]
    function_type: OpAttr[AnyAttr()]
    arg_attrs: OpAttr[ArrayAttr]
    res_attrs: OpAttr[ArrayAttr]
    values: Annotated[Operand, PdlRangeType]

    region: Region


@irdl_op_definition
class PdlInterpGetAttribute(IRDLOperation):
    name = "pdl_interp.get_attribute"

    name: OpAttr[StringAttr]
    input_op: Annotated[Operand, PdlOperationType]
    attribute: Annotated[OpResult, PdlAttributeType]


@irdl_op_definition
class PdlInterpGetAttributeType(IRDLOperation):
    name = "pdl_interp.get_attribute_type"

    value: Annotated[Operand, PdlAttributeType]
    result: Annotated[OpResult, PdlTypeType]


@irdl_op_definition
class PdlInterpGetDefiningOp(IRDLOperation):
    name = "pdl_interp.get_defining_op"

    value: Annotated[Operand, SingleOrManyPdlValues]
    inputOp: Annotated[OpResult, PdlOperationType]


@irdl_op_definition
class PdlInterpGetOperand(IRDLOperation):
    name = "pdl_interp.get_operand"

    index: OpAttr[IntegerAttr]
    inputOp: Annotated[Operand, PdlOperationType]
    value: Annotated[OpResult, PdlValueType]


@irdl_op_definition
class PdlInterpGetOperands(IRDLOperation):
    name = "pdl_interp.get_operands"

    index: OpAttr[IntegerAttr]
    inputOp: Annotated[Operand, PdlOperationType]
    value: Annotated[OpResult, SingleOrManyPdlValues]


@irdl_op_definition
class PdlInterpGetResult(IRDLOperation):
    name = "pdl_interp.get_result"

    index: OpAttr[IntegerAttr]
    inputOp: Annotated[Operand, PdlOperationType]
    value: Annotated[OpResult, PdlValueType]


@irdl_op_definition
class PdlInterpGetResults(IRDLOperation):
    name = "pdl_interp.get_results"

    index: OpAttr[IntegerAttr]
    inputOp: Annotated[Operand, PdlOperationType]
    value: Annotated[OpResult, SingleOrManyPdlValues]


@irdl_op_definition
class PdlInterpGetUsers(IRDLOperation):
    name = "pdl_interp.get_users"

    inputOp: Annotated[Operand, PdlOperationType]
    operations: Annotated[OpResult, PdlRangeType(RangeValue.OPERATION)]


@irdl_op_definition
class PdlInterpGetValueType(IRDLOperation):
    name = "pdl_interp.get_value_type"

    value: Annotated[Operand, SingleOrManyPdlValues]
    result: Annotated[OpResult, SingleOrManyPdlTypes]

    def verify_(self) -> None:
        if not type(self.value) is type(self.result):
            raise VerifyException(
                "incoherent amount of type results with respect to value inputs"
            )


@irdl_op_definition
class PdlInterpIsNotNull(IRDLOperation):
    name = "pdl_interp.is_not_null"

    value: Annotated[Operand, AnyPdlType]


@irdl_op_definition
class PdlInterpRecordMatch(IRDLOperation):
    name = "pdl_interp.record_match"

    rewriter: OpAttr[SymbolRefAttr]
    root_kind: OpAttr[StringAttr]
    generated_ops: OpAttr[ArrayAttr[StringAttr]]
    benefit: OpAttr[IntegerAttr]
    inputs: Annotated[Operand, AnyPdlType]
    matched_ops: Annotated[Operand, PdlOperationType]


@irdl_op_definition
class PdlInterpReplace(IRDLOperation):
    name = "pdl_interp.replace"

    inputOp: Annotated[Operand, PdlOperationType]
    matched_ops: Annotated[Operand, SingleOrManyPdlValues]


@irdl_op_definition
class PdlSwitchAttribute(IRDLOperation):
    name = "pdl_interp.switch_attribute"

    case_values: OpAttr[ArrayAttr]
    attribute: Annotated[Operand, PdlAttributeType]


@irdl_op_definition
class PdlSwitchOperandCount(IRDLOperation):
    name = "pdl_interp.switch_operand_count"

    case_values: OpAttr[DenseIntOrFPElementsAttr]
    input_op: Annotated[Operand, PdlOperationType]


@irdl_op_definition
class PdlSwitchOperationName(IRDLOperation):
    name = "pdl_interp.switch_operation_name"

    case_values: OpAttr[ArrayAttr[StringAttr]]
    input_op: Annotated[Operand, PdlOperationType]


@irdl_op_definition
class PdlSwitchResultCount(IRDLOperation):
    name = "pdl_interp.switch_result_count"

    case_values: OpAttr[DenseIntOrFPElementsAttr]
    input_op: Annotated[Operand, PdlOperationType]


@irdl_op_definition
class PdlSwitchType(IRDLOperation):
    name = "pdl_interp.switch_type"

    case_values: OpAttr[ArrayAttr]
    input_op: Annotated[Operand, PdlTypeType]


@irdl_op_definition
class PdlSwitchTypes(IRDLOperation):
    name = "pdl_interp.switch_types"

    case_values: OpAttr[ArrayAttr[ArrayAttr]]
    input_op: Annotated[Operand, PdlRangeType(RangeValue.TYPE)]


PdlInterp = Dialect(
    [
        PdlInterpAreEqual,
        PdlInterpBranch,
        PdlInterpCheckAttribute,
        PdlInterpCheckOperandCount,
        PdlInterpCheckOperationName,
        PdlInterpCheckResultCount,
        PdlInterpCheckType,
        PdlInterpCheckTypes,
        PdlInterpContinue,
        PdlInterpCreateAttribute,
        PdlInterpCreateOperation,
        PdlInterpCreateRange,
        PdlInterpCreateType,
        PdlInterpCreateTypes,
        PdlInterpErase,
        PdlInterpExtract,
        PdlInterpFinalize,
        PdlInterpForeach,
        PdlInterpFunc,
        PdlInterpGetAttribute,
        PdlInterpGetAttributeType,
        PdlInterpGetDefiningOp,
        PdlInterpGetOperand,
        PdlInterpGetOperands,
        PdlInterpGetResult,
        PdlInterpGetResults,
        PdlInterpGetUsers,
        PdlInterpGetValueType,
        PdlInterpIsNotNull,
        PdlInterpRecordMatch,
        PdlInterpReplace,
        PdlSwitchAttribute,
        PdlSwitchOperandCount,
        PdlSwitchOperationName,
        PdlSwitchResultCount,
        PdlSwitchType,
        PdlSwitchTypes,
    ],
    [],
)
