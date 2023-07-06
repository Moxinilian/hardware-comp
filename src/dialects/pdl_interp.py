from typing import cast
from xdsl.irdl import (
    irdl_op_definition,
    AnyAttr,
    IRDLOperation,
    Operand,
    VarOperand,
    result_def,
    attr_def,
    opt_attr_def,
    operand_def,
    region_def,
    var_operand_def,
    successor_def,
    var_successor_def,
    AnyOf,
    AttrConstraint,
    Successor,
    VarSuccessor,
    AttrSizedOperandSegments,
)
from xdsl.traits import IsTerminator
from xdsl.ir import Attribute, OpResult, Region, Dialect, Block, SSAValue
from xdsl.dialects.builtin import (
    IntegerAttr,
    UnitAttr,
    StringAttr,
    ArrayAttr,
    SymbolRefAttr,
    DenseIntOrFPElementsAttr,
    FunctionType,
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

# todo: traits, interfaces, effects

AnyPdlType: AttrConstraint = AnyOf(
    [PdlAttributeType, PdlTypeType, PdlValueType, PdlOperationType]
)
AnyPdlRange: AttrConstraint = AnyOf(
    [
        PdlRangeType(RangeValue.VALUE),
        PdlRangeType(RangeValue.TYPE),
        PdlRangeType(RangeValue.OPERATION),
        PdlRangeType(RangeValue.ATTRIBUTE),
    ]
)
AnyPdlTypeOrRange: AttrConstraint = AnyOf([AnyPdlType, AnyPdlRange])
SingleOrManyPdlValues: AttrConstraint = AnyOf(
    [PdlValueType, PdlRangeType(RangeValue.VALUE)]
)
SingleOrManyPdlTypes: AttrConstraint = AnyOf(
    [PdlValueType, PdlRangeType(RangeValue.TYPE)]
)


@irdl_op_definition
class PdlInterpAreEqual(IRDLOperation):
    name = "pdl_interp.are_equal"

    lhs: Operand = operand_def(AnyPdlTypeOrRange)
    rhs: Operand = operand_def(AnyPdlTypeOrRange)

    true_dest: Successor = successor_def()
    false_dest: Successor = successor_def()
    traits = frozenset([IsTerminator()])

    def verify_(self) -> None:
        if self.lhs.typ != self.rhs.typ:
            raise VerifyException(
                f"'{self.lhs}' is not of type the same type as '{self.rhs}'"
            )


@irdl_op_definition
class PdlInterpBranch(IRDLOperation):
    name = "pdl_interp.branch"

    dest: Successor = successor_def()
    traits = frozenset([IsTerminator()])


@irdl_op_definition
class PdlInterpCheckAttribute(IRDLOperation):
    name = "pdl_interp.check_attribute"

    constant_value: Attribute = attr_def(Attribute, attr_name="constantValue")
    attribute: Operand = operand_def(PdlAttributeType)

    true_dest: Successor = successor_def()
    false_dest: Successor = successor_def()
    traits = frozenset([IsTerminator()])


@irdl_op_definition
class PdlInterpCheckOperandCount(IRDLOperation):
    name = "pdl_interp.check_operand_count"

    count: IntegerAttr = attr_def(IntegerAttr)
    compare_at_least: UnitAttr | None = opt_attr_def(
        UnitAttr, attr_name="compareAtLeast"
    )
    input_op: Operand = operand_def(PdlOperationType)

    true_dest: Successor = successor_def()
    false_dest: Successor = successor_def()
    traits = frozenset([IsTerminator()])


@irdl_op_definition
class PdlInterpCheckOperationName(IRDLOperation):
    name = "pdl_interp.check_operation_name"

    op_name: StringAttr = attr_def(StringAttr, attr_name="name")
    input_op: Operand = operand_def(PdlOperationType)

    true_dest: Successor = successor_def()
    false_dest: Successor = successor_def()
    traits = frozenset([IsTerminator()])


@irdl_op_definition
class PdlInterpCheckResultCount(IRDLOperation):
    name = "pdl_interp.check_result_count"

    count: IntegerAttr = attr_def(IntegerAttr)
    compare_at_least: UnitAttr = attr_def(UnitAttr)
    input_op: Operand = operand_def(PdlOperationType)

    true_dest: Successor = successor_def()
    false_dest: Successor = successor_def()
    traits = frozenset([IsTerminator()])


@irdl_op_definition
class PdlInterpCheckType(IRDLOperation):
    name = "pdl_interp.check_type"

    typ: Attribute = attr_def(Attribute, attr_name="type")
    value: Operand = operand_def(PdlTypeType)

    true_dest: Successor = successor_def()
    false_dest: Successor = successor_def()
    traits = frozenset([IsTerminator()])


@irdl_op_definition
class PdlInterpCheckTypes(IRDLOperation):
    name = "pdl_interp.check_types"

    types: ArrayAttr = attr_def(ArrayAttr)
    value: Operand = operand_def(PdlRangeType(RangeValue.TYPE))

    true_dest: Successor = successor_def()
    false_dest: Successor = successor_def()
    traits = frozenset([IsTerminator()])


@irdl_op_definition
class PdlInterpContinue(IRDLOperation):
    name = "pdl_interp.continue"

    traits = frozenset([IsTerminator()])


@irdl_op_definition
class PdlInterpCreateAttribute(IRDLOperation):
    name = "pdl_interp.create_attribute"

    value: Attribute = attr_def(Attribute)
    attribute: OpResult = result_def(PdlAttributeType)


@irdl_op_definition
class PdlInterpCreateOperation(IRDLOperation):
    name = "pdl_interp.create_operation"

    op_name: StringAttr = attr_def(StringAttr, attr_name="name")
    input_attribute_names: ArrayAttr = attr_def(
        ArrayAttr, attr_name="inputAttributeNames"
    )
    inferred_result_types: UnitAttr | None = opt_attr_def(UnitAttr)
    input_operands: VarOperand = var_operand_def(SingleOrManyPdlValues)
    input_attributes: VarOperand = var_operand_def(PdlAttributeType)
    input_result_types: VarOperand = var_operand_def(SingleOrManyPdlTypes)
    result_op: OpResult = result_def(PdlOperationType)

    irdl_options = [AttrSizedOperandSegments()]


@irdl_op_definition
class PdlInterpCreateRange(IRDLOperation):
    name = "pdl_interp.create_range"

    arguments: VarOperand = var_operand_def(AnyAttr())  # todo: constraints
    result: OpResult = result_def(AnyAttr())  # todo: constraints


@irdl_op_definition
class PdlInterpCreateType(IRDLOperation):
    name = "pdl_interp.create_type"

    value: Operand = operand_def(AnyAttr())
    result: OpResult = result_def(PdlTypeType)


@irdl_op_definition
class PdlInterpCreateTypes(IRDLOperation):
    name = "pdl_interp.create_types"

    value: Operand = operand_def(ArrayAttr)
    result: OpResult = result_def(PdlRangeType(RangeValue.TYPE))


@irdl_op_definition
class PdlInterpErase(IRDLOperation):
    name = "pdl_interp.erase"

    input_op: Operand = operand_def(PdlOperationType)


@irdl_op_definition
class PdlInterpExtract(IRDLOperation):
    name = "pdl_interp.extract"

    index: IntegerAttr = attr_def(IntegerAttr)
    range: Operand = operand_def(PdlRangeType)
    result: OpResult = result_def(AnyPdlType)

    def verify_(self) -> None:
        range_type = cast(PdlRangeType, self.range.typ)
        if range_type.data == RangeValue.ATTRIBUTE:
            if self.result.typ != PdlAttributeType:
                raise VerifyException(
                    f"extracting from attribute range '{self.range}' should "
                    f"yield an attribute and not '{self.result.typ}'"
                )
        elif range_type.data == RangeValue.TYPE:
            if self.result.typ != PdlTypeType:
                raise VerifyException(
                    f"extracting from type range '{self.range}' should "
                    f"yield a type and not '{self.result.typ}'"
                )
        elif range_type.data == RangeValue.OPERATION:
            if self.result.typ != PdlOperationType:
                raise VerifyException(
                    f"extracting from operation range '{self.range}' should "
                    f"yield an operation and not '{self.result.typ}'"
                )
        elif range_type.data == RangeValue.VALUE:
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

    traits = frozenset([IsTerminator()])


@irdl_op_definition
class PdlInterpForeach(IRDLOperation):
    name = "pdl_interp.foreach"

    values: Operand = operand_def(PdlRangeType)

    region: Region = region_def()

    successor: Successor = successor_def()
    traits = frozenset([IsTerminator()])


@irdl_op_definition
class PdlInterpFunc(IRDLOperation):
    name = "pdl_interp.func"

    sym_name: StringAttr = attr_def(StringAttr)
    function_type: FunctionType = attr_def(FunctionType)
    arg_attrs: ArrayAttr | None = opt_attr_def(ArrayAttr)
    res_attrs: ArrayAttr | None = opt_attr_def(ArrayAttr)

    region: Region = region_def()


@irdl_op_definition
class PdlInterpGetAttribute(IRDLOperation):
    name = "pdl_interp.get_attribute"

    attr_name: StringAttr = attr_def(StringAttr, attr_name="name")
    input_op: Operand = operand_def(PdlOperationType)
    attribute: OpResult = result_def(PdlAttributeType)


@irdl_op_definition
class PdlInterpGetAttributeType(IRDLOperation):
    name = "pdl_interp.get_attribute_type"

    value: Operand = operand_def(PdlAttributeType)
    result: OpResult = result_def(PdlTypeType)


@irdl_op_definition
class PdlInterpGetDefiningOp(IRDLOperation):
    name = "pdl_interp.get_defining_op"

    value: Operand = operand_def(SingleOrManyPdlValues)
    inputOp: OpResult = result_def(PdlOperationType)


@irdl_op_definition
class PdlInterpGetOperand(IRDLOperation):
    name = "pdl_interp.get_operand"

    index: IntegerAttr = attr_def(IntegerAttr)
    inputOp: Operand = operand_def(PdlOperationType)
    value: OpResult = result_def(PdlValueType)


@irdl_op_definition
class PdlInterpGetOperands(IRDLOperation):
    name = "pdl_interp.get_operands"

    index: IntegerAttr = attr_def(IntegerAttr)
    inputOp: Operand = operand_def(PdlOperationType)
    value: OpResult = result_def(SingleOrManyPdlValues)


@irdl_op_definition
class PdlInterpGetResult(IRDLOperation):
    name = "pdl_interp.get_result"

    index: IntegerAttr = attr_def(IntegerAttr)
    inputOp: Operand = operand_def(PdlOperationType)
    value: OpResult = result_def(PdlValueType)


@irdl_op_definition
class PdlInterpGetResults(IRDLOperation):
    name = "pdl_interp.get_results"

    index: IntegerAttr | None = opt_attr_def(IntegerAttr)
    inputOp: Operand = operand_def(PdlOperationType)
    value: OpResult = result_def(SingleOrManyPdlValues)


@irdl_op_definition
class PdlInterpGetUsers(IRDLOperation):
    name = "pdl_interp.get_users"

    inputOp: Operand = operand_def(PdlOperationType)
    operations: OpResult = result_def(PdlRangeType(RangeValue.OPERATION))


@irdl_op_definition
class PdlInterpGetValueType(IRDLOperation):
    name = "pdl_interp.get_value_type"

    value: Operand = operand_def(SingleOrManyPdlValues)
    result: OpResult = result_def(SingleOrManyPdlTypes)

    def verify_(self) -> None:
        if not type(self.value) is type(self.result):
            raise VerifyException(
                "incoherent amount of type results with respect to value inputs"
            )


@irdl_op_definition
class PdlInterpIsNotNull(IRDLOperation):
    name = "pdl_interp.is_not_null"

    value: Operand = operand_def(AnyPdlType)

    true_dest: Successor = successor_def()
    false_dest: Successor = successor_def()
    traits = frozenset([IsTerminator()])


@irdl_op_definition
class PdlInterpRecordMatch(IRDLOperation):
    name = "pdl_interp.record_match"

    rewriter: SymbolRefAttr = attr_def(SymbolRefAttr)
    root_kind: StringAttr = attr_def(StringAttr, attr_name="rootKind")
    generated_ops: ArrayAttr[StringAttr] = attr_def(
        ArrayAttr[StringAttr], attr_name="generatedOps"
    )
    benefit: IntegerAttr = attr_def(IntegerAttr)
    inputs: VarOperand = var_operand_def(AnyPdlType)
    matched_ops: Operand = operand_def(PdlOperationType)

    dest: Successor = successor_def()
    traits = frozenset([IsTerminator()])


@irdl_op_definition
class PdlInterpReplace(IRDLOperation):
    name = "pdl_interp.replace"

    inputOp: Operand = operand_def(PdlOperationType)
    matched_ops: Operand = operand_def(SingleOrManyPdlValues)


@irdl_op_definition
class PdlInterpSwitchAttribute(IRDLOperation):
    name = "pdl_interp.switch_attribute"

    case_values: ArrayAttr = attr_def(ArrayAttr)
    attribute: Operand = operand_def(PdlAttributeType)

    default_dest: Successor = successor_def()
    cases: VarSuccessor = var_successor_def()
    traits = frozenset([IsTerminator()])

    @staticmethod
    def from_cases(attribute: SSAValue, cases: dict[Attribute, Block], default: Block):
        return PdlInterpSwitchAttribute(
            operands=[attribute],
            attributes={"case_values": ArrayAttr(list(cases.keys()))},
            successors=[default, list(cases.values())],
        )


@irdl_op_definition
class PdlInterpSwitchOperandCount(IRDLOperation):
    name = "pdl_interp.switch_operand_count"

    case_values: DenseIntOrFPElementsAttr = attr_def(DenseIntOrFPElementsAttr)
    input_op: Operand = operand_def(PdlOperationType)

    default_dest: Successor = successor_def()
    cases: VarSuccessor = var_successor_def()
    traits = frozenset([IsTerminator()])


@irdl_op_definition
class PdlInterpSwitchOperationName(IRDLOperation):
    name = "pdl_interp.switch_operation_name"

    case_values: ArrayAttr[StringAttr] = attr_def(ArrayAttr[StringAttr])
    input_op: Operand = operand_def(PdlOperationType)

    default_dest: Successor = successor_def()
    cases: VarSuccessor = var_successor_def()
    traits = frozenset([IsTerminator()])

    @staticmethod
    def from_cases(operation: SSAValue, cases: dict[StringAttr, Block], default: Block):
        return PdlInterpSwitchOperationName(
            operands=[operation],
            attributes={"case_values": ArrayAttr(list(cases.keys()))},
            successors=[default, list(cases.values())],
        )


@irdl_op_definition
class PdlInterpSwitchResultCount(IRDLOperation):
    name = "pdl_interp.switch_result_count"

    case_values: DenseIntOrFPElementsAttr = attr_def(DenseIntOrFPElementsAttr)
    input_op: Operand = operand_def(PdlOperationType)

    default_dest: Successor = successor_def()
    cases: VarSuccessor = var_successor_def()
    traits = frozenset([IsTerminator()])


@irdl_op_definition
class PdlInterpSwitchType(IRDLOperation):
    name = "pdl_interp.switch_type"

    case_values: ArrayAttr = attr_def(ArrayAttr)
    value: Operand = operand_def(PdlTypeType)

    default_dest: Successor = successor_def()
    cases: VarSuccessor = var_successor_def()
    traits = frozenset([IsTerminator()])

    @staticmethod
    def from_cases(typ: SSAValue, cases: dict[Attribute, Block], default: Block):
        return PdlInterpSwitchType(
            operands=[typ],
            attributes={"case_values": ArrayAttr(list(cases.keys()))},
            successors=[default, list(cases.values())],
        )


@irdl_op_definition
class PdlInterpSwitchTypes(IRDLOperation):
    name = "pdl_interp.switch_types"

    case_values: ArrayAttr[ArrayAttr] = attr_def(ArrayAttr[ArrayAttr])
    value: Operand = operand_def(PdlRangeType(RangeValue.TYPE))

    default_dest: Successor = successor_def()
    cases: VarSuccessor = var_successor_def()
    traits = frozenset([IsTerminator()])

    @staticmethod
    def from_cases(types: SSAValue, cases: dict[ArrayAttr, Block], default: Block):
        return PdlInterpSwitchTypes(
            operands=[types],
            attributes={"case_values": ArrayAttr(list(cases.keys()))},
            successors=[default, list(cases.values())],
        )


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
        PdlInterpSwitchAttribute,
        PdlInterpSwitchOperandCount,
        PdlInterpSwitchOperationName,
        PdlInterpSwitchResultCount,
        PdlInterpSwitchType,
        PdlInterpSwitchTypes,
    ],
    [],
)
