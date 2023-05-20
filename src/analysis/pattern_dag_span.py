from attr import dataclass
from xdsl.ir import Region, SSAValue

from dialects.pdl_interp import *
from dialects.pdl import *
from utils import UnsupportedPatternFeature


def region_has_cycles(pdli_region: Region) -> bool:
    if len(pdli_region.blocks) == 0:
        return False

    visited: set[Block] = set()

    def walk_block(block: Block) -> bool:
        if block in visited:
            return True
        visited.add(block)
        if not block.last_op:
            return False
        for succ in block.last_op.successors:
            if walk_block(succ):
                return True
        return False

    return walk_block(pdli_region.blocks[0])


@dataclass
class OperandUsage:
    """Represents an operand of an operation used by a pattern."""

    # Marks whether the SSA value itself is used, typically for equality checks.
    used_value: bool

    # Marks whether the type of the SSA value is used.
    used_type: bool

    defining_op: "OperationUsageSpan" | None

    def __init__(self):
        self.used_value = False
        self.used_type = False
        self.defining_op = OperationUsageSpan()


@dataclass
class OperationUsageSpan:
    """Represents the tree of operations that can be used by a pattern."""

    # Marks whether the operation type of the operation is used in some way.
    used_op_type: bool

    # Marks whether the amount of results of the operation is used in some way.
    used_result_amount: bool

    # Marks whether the operand count of the operation is used in some way.
    used_operand_count: bool

    # Marks whether all operands are used at once, without getting them
    # individually.
    used_all_operands: bool

    # Marks whether all operand types are used at once, without getting them
    # individually.
    used_all_operand_types: bool

    # Describes the operands that are used individually.
    used_operands: dict[int, OperandUsage]

    def __init__(self):
        self.used_op_type = False
        self.used_result_amount = False
        self.used_operand_count = False
        self.used_all_operands = False
        self.used_all_operand_types = False
        self.operands = dict()

    def mark_all_used(self):
        self.used_op_type = True
        self.used_operand_count = True
        self.used_result_type = True
        self.used_all_operands = True


def compute_usage_span(pdli_region: Region) -> OperationUsageSpan | None:
    operations: dict[SSAValue, OperationUsageSpan] = dict()
    rangeOfOperandsOf: dict[SSAValue, OperationUsageSpan] = dict()
    rangeOfTypesOfOperandsOf: dict[SSAValue, OperationUsageSpan] = dict()
    operandTypes: dict[SSAValue, OperandUsage] = dict()
    operandValues: dict[SSAValue, OperandUsage] = dict()

    root = OperationUsageSpan()
    operations[pdli_region.blocks[0].args[0]] = root

    if region_has_cycles(pdli_region):
        raise UnsupportedPatternFeature("cycles in region")

    # xDSL guarantees the block iteration order ensures operations are
    # topologically sorted, even accross blocks
    for block in pdli_region.blocks:
        for op in block.ops:
            if isinstance(op, PdlInterpAreEqual):
                if isinstance(op.lhs.typ, RangeType):
                    if op.lhs.typ.data == RangeValue.VALUE:
                        # All value ranges are ranges of operands.
                        rangeOfOperandsOf[op.lhs].used_all_operands = True
                        rangeOfOperandsOf[op.lhs].used_operand_count = True
                        rangeOfOperandsOf[op.rhs].used_all_operands = True
                        rangeOfOperandsOf[op.rhs].used_operand_count = True
                    elif op.lhs.typ.data == RangeValue.TYPE:
                        # All type ranges are ranges of the types of a
                        # range of operands.
                        rangeOfTypesOfOperandsOf[op.lhs].used_all_operand_types = True
                        rangeOfTypesOfOperandsOf[op.lhs].used_operand_count = True
                        rangeOfTypesOfOperandsOf[op.rhs].used_all_operand_types = True
                        rangeOfTypesOfOperandsOf[op.rhs].used_operand_count = True
                    else:
                        assert 0  # TODO: check if reachable
                if isinstance(op.lhs.typ, ValueType):
                    operandValues[op.lhs].used = True
                    operandValues[op.rhs].used = True
                if isinstance(op.lhs.type, OperationType):
                    operations[op.lhs].used = True
                    operations[op.lhs].use_all_operands = True
                    operations[op.rhs].used = True
                    operations[op.rhs].use_all_operands = True
                continue

            if isinstance(op, PdlInterpBranch):
                continue

            if isinstance(op, PdlInterpCheckOperandCount):
                operations[op.input_op].used = True
                continue

            if isinstance(op, PdlInterpCheckOperationName):
                operations[op.input_op].used = True
                continue

            if isinstance(op, PdlInterpCheckType):
                operandTypes[op.type].used_type = True
                continue

            if isinstance(op, PdlInterpCheckTypes):
                # All type ranges are ranges of the types of a
                # range of operands.
                rangeOfTypesOfOperandsOf[op.value].used_all_operand_types = True
                rangeOfTypesOfOperandsOf[op.value].used_operand_count = True

            if isinstance(op, PdlInterpContinue):
                continue

            if isinstance(op, PdlInterpExtract):
                if op.range.typ.data == RangeValue.TYPE:
                    # All type ranges are ranges of the types of a
                    # range of operands.
                    range_span = rangeOfTypesOfOperandsOf[op.range]
                    usage = range_span.used_operands[op.index.data] or OperandUsage()
                    range_span.used_operands[op.index.data] = usage
                    operandTypes[op.result] = usage
                elif op.range.typ.data == RangeValue.VALUE:
                    # All value ranges are ranges of operands.
                    range_span = rangeOfOperandsOf[op.range]
                    usage = range_span.used_operands[op.index.data] or OperandUsage()
                    range_span.used_operands[op.index.data] = usage
                    operandValues[op.result] = usage
                continue

            if isinstance(op, PdlInterpFinalize):
                continue

            if isinstance(op, PdlInterpGetDefiningOp):
                if isinstance(op.value.typ, PdlRangeType):
                    raise UnsupportedPatternFeature(op)
                usage = operandValues[op.value].defining_op or OperationUsageSpan()
                operandValues[op.value].defining_op = usage
                operations[op.inputOp] = usage
                continue

            if isinstance(op, PdlInterpGetOperand):
                usage = operations[op.inputOp].used_operands[op.index.data] or OperandUsage()
                operations[op.inputOp].used_operands[op.index.data] = usage
                operandValues[op.value] = usage
            
            if isinstance(op, PdlInterpGetOperands):
                if op.index:
                    raise UnsupportedPatternFeature(op)
                rangeOfOperandsOf[op.]
            

            # For any unhandled operation
            raise UnsupportedPatternFeature(op)
