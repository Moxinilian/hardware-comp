from typing import Tuple
from xdsl.ir import Region, SSAValue, Block

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


class DotNamer:
    """Utility class to provide names for the dot representation of an OperationSpan."""

    next_id: int

    def __init__(self):
        self.next_id = 0

    def get_id(self) -> int:
        self.next_id += 1
        return self.next_id - 1


class OperationSpanCtx:
    """Utility class mapping a PDL Interp SSA value to its associated construct in a span tree."""

    value_of_operand: dict[SSAValue, "OperandSpan"]
    type_of_operand: dict[SSAValue, "OperandSpan"]
    value_of_result: dict[SSAValue, "ResultSpan"]
    type_of_result: dict[SSAValue, "ResultSpan"]
    operations: dict[SSAValue, "OperationSpan"]
    operand_range_of: dict[SSAValue, "OperationSpan"]
    operand_type_range_of: dict[SSAValue, "OperationSpan"]
    result_range_of: dict[SSAValue, "OperationSpan"]
    result_type_range_of: dict[SSAValue, "OperationSpan"]

    def __init__(self):
        self.value_of_operand = dict()
        self.type_of_operand = dict()
        self.value_of_result = dict()
        self.type_of_result = dict()
        self.operations = dict()
        self.operand_range_of = dict()
        self.operand_type_range_of = dict()
        self.result_range_of = dict()
        self.result_type_range_of = dict()


class OperationSpan:
    """Represents the use of the data embedded in an operation in the span tree."""

    pdl_values: list[SSAValue]
    all_operands_ranges: list[SSAValue]
    all_operand_types_ranges: list[SSAValue]
    all_results_ranges: list[SSAValue]
    all_result_types_ranges: list[SSAValue]

    used: bool

    operands: dict[int, "OperandSpan"]
    results: dict[int, "ResultSpan"]

    def __init__(self):
        self.pdl_values = []
        self.all_operands_ranges = []
        self.all_operand_types_ranges = []
        self.all_results_ranges = []
        self.all_result_types_ranges = []
        self.used = False
        self.operands = dict()
        self.results = dict()

    def as_dot(self, namer: DotNamer, self_name: str) -> str:
        as_dot = f'{self_name} [ label="{self_name} (aka {[val.name_hint for val in self.pdl_values]})"]\n'
        for result in self.results.values():
            as_dot += result.as_dot(namer, self_name)
        for operand in self.operands.values():
            as_dot += operand.as_dot(namer, self_name)
        return as_dot

    def add_value(self, ctx: OperationSpanCtx, value: SSAValue):
        self.pdl_values.append(value)
        ctx.operations[value] = self

    def add_operand_range(self, ctx: OperationSpanCtx, value: SSAValue):
        self.all_operands_ranges.append(value)
        ctx.operand_range_of[value] = self

    def add_operand_type_range(self, ctx: OperationSpanCtx, value: SSAValue):
        self.all_operand_types_ranges.append(value)
        ctx.operand_type_range_of[value] = self

    def add_result_range(self, ctx: OperationSpanCtx, value: SSAValue):
        self.all_results_ranges.append(value)
        ctx.result_range_of[value] = self

    def add_result_type_range(self, ctx: OperationSpanCtx, value: SSAValue):
        self.all_result_types_ranges.append(value)
        ctx.result_type_range_of[value] = self


class OperandSpan:
    """Represents the use of the data embedded in an operand in the span tree."""

    pdl_values: list[SSAValue]
    pdl_types: list[SSAValue]

    operand_of: OperationSpan
    operand_index: int
    defining_op: OperationSpan

    def __init__(self, operand_of: OperationSpan, operand_index: int):
        self.pdl_values = []
        self.pdl_types = []
        self.operand_of = operand_of
        self.operand_index = operand_index
        self.defining_op = OperationSpan()

    def as_dot(self, namer: DotNamer, user_name: str) -> str:
        operand_name = f"a{namer.get_id()}"
        as_dot = f'{operand_name} [ label="{operand_name} (aka {[val.name_hint for val in self.pdl_values]})"]\n'
        as_dot += (
            f'{user_name} -> {operand_name} [ label="operand {self.operand_index}" ]\n'
        )
        if self.defining_op.used:
            def_op_name = f"op{namer.get_id()}"
            as_dot += f"{operand_name} -> {def_op_name}\n"
            as_dot += self.defining_op.as_dot(namer, def_op_name)
        return as_dot

    def add_value(self, ctx: OperationSpanCtx, value: SSAValue):
        self.pdl_values.append(value)
        ctx.value_of_operand[value] = self

    def add_type(self, ctx: OperationSpanCtx, value: SSAValue):
        self.pdl_types.append(value)
        ctx.type_of_operand[value] = self


class ResultSpan:
    """Represents the use of the data embedded in a result in the span tree."""

    pdl_values: list[SSAValue]
    pdl_types: list[SSAValue]

    result_of: OperationSpan
    result_index: int

    def __init__(self, result_of: OperationSpan, result_index: int):
        self.pdl_values = []
        self.pdl_types = []
        self.result_of = result_of
        self.result_index = result_index

    def as_dot(self, namer: DotNamer, parent_name: str) -> str:
        result_name = f"r{namer.get_id()}"
        as_dot = f'{result_name} [ label="{result_name} (aka {[val.name_hint for val in self.pdl_values]})"]\n'
        as_dot += (
            f'{parent_name} -> {result_name} [ label="result {self.result_index}" ]\n'
        )
        return as_dot

    def add_value(self, ctx: OperationSpanCtx, value: SSAValue):
        self.pdl_values.append(value)
        ctx.value_of_result[value] = self

    def add_type(self, ctx: OperationSpanCtx, value: SSAValue):
        self.pdl_types.append(value)
        ctx.type_of_result[value] = self


def compute_usage_graph(pdli_region: Region) -> Tuple[OperationSpan, OperationSpanCtx]:
    ctx = OperationSpanCtx()

    root_value = pdli_region.blocks[0].args[0]
    root = OperationSpan()
    root.add_value(ctx, root_value)

    def add_operand(
        operation: OperationSpan, operand: SSAValue | None, index: int
    ) -> OperandSpan:
        if not index in operation.operands:
            operation.operands[index] = OperandSpan(operation, index)
        if operand:
            operation.operands[index].add_value(ctx, operand)
        return operation.operands[index]

    def add_result(
        operation: OperationSpan, result: SSAValue | None, index: int
    ) -> ResultSpan:
        if not index in operation.results:
            operation.results[index] = ResultSpan(operation, index)
        if result:
            operation.results[index].add_value(ctx, result)
        return operation.results[index]

    def walk_operation(value: SSAValue, op_span: OperationSpan) -> bool:
        used = False
        for use in value.uses:
            match use.operation:
                case PdlInterpAreEqual():
                    used = True
                case PdlInterpCheckOperandCount():
                    used = True
                case PdlInterpCheckOperationName():
                    used = True
                case PdlInterpCheckResultCount():
                    used = True
                case PdlInterpGetOperand(index=index, value=operand):
                    operand_span = add_operand(op_span, operand, index.value.data)
                    used |= walk_operand(operand, operand_span)
                case PdlInterpGetOperands(value=operands):
                    index = (
                        use.operation.index
                        if "index" in use.operation.attributes
                        else None
                    )
                    if not isinstance(operands.typ, PdlValueType):
                        if index and index.value.data != 0:
                            raise UnsupportedPatternFeature(use)
                        op_span.add_operand_range(ctx, operands)
                        used |= walk_operand_range(operands, op_span)
                        continue
                    if not index:
                        raise UnsupportedPatternFeature(use)
                    operand_span = add_operand(op_span, operands, index.value.data)
                    used |= walk_operand(operands, operand_span)
                case PdlInterpGetResult(index=index, value=result):
                    result_span = add_result(op_span, result, index.value.data)
                    used |= walk_result(result, result_span)
                case PdlInterpGetResults(value=results):
                    index = (
                        use.operation.index
                        if "index" in use.operation.attributes
                        else None
                    )
                    if not isinstance(results.typ, PdlValueType):
                        if index and index.value.data != 0:
                            raise UnsupportedPatternFeature(use)
                        op_span.add_result_range(ctx, results)
                        used |= walk_result_range(results, op_span)
                        continue
                    if not index:
                        raise UnsupportedPatternFeature(use)
                    result_span = add_result(op_span, results, index.value.data)
                    used |= walk_result(results, result_span)
                case PdlInterpIsNotNull():
                    used = True
                case PdlInterpRecordMatch():
                    used = True
                case PdlSwitchOperandCount():
                    used = True
                case PdlSwitchOperationName():
                    used = True
                case PdlSwitchResultCount():
                    used = True
                case _:
                    raise UnsupportedPatternFeature(use)
        if used:
            op_span.used = True
        return op_span.used

    def walk_operand(value: SSAValue, op_span: OperandSpan) -> bool:
        used = False
        for use in value.uses:
            match use.operation:
                case PdlInterpAreEqual():
                    used = True
                case PdlInterpGetDefiningOp(inputOp=defining_op):
                    op_span.defining_op.add_value(ctx, defining_op)
                    used |= walk_operation(defining_op, op_span.defining_op)
                case PdlInterpGetValueType(result=result):
                    op_span.add_type(ctx, result)
                    used |= walk_type(result)
                case PdlInterpIsNotNull():
                    used = True
                case PdlInterpRecordMatch():
                    used = True
                case _:
                    raise UnsupportedPatternFeature(use)
        return used

    def walk_result(value: SSAValue, res_span: ResultSpan) -> bool:
        used = False
        for use in value.uses:
            match use.operation:
                case PdlInterpAreEqual():
                    used = True
                case PdlInterpGetDefiningOp(inputOp=defining_op):
                    res_span.result_of.add_value(ctx, defining_op)
                    used |= walk_operation(defining_op, res_span.result_of)
                case PdlInterpGetValueType(result=result):
                    res_span.add_type(ctx, result)
                    used |= walk_type(result)
                case PdlInterpIsNotNull():
                    used = True
                case PdlInterpRecordMatch():
                    used = True
                case _:
                    raise UnsupportedPatternFeature(use)
        return used

    def walk_operand_range(value: SSAValue, op_span: OperationSpan) -> bool:
        used = False
        for use in value.uses:
            match use.operation:
                case PdlInterpAreEqual():
                    used = True
                case PdlInterpExtract(index=index, result=result):
                    operand_span = add_operand(op_span, result, index.value.data)
                    used |= walk_operand(result, operand_span)
                case PdlInterpGetDefiningOp(inputOp=defining_op):
                    operand_span = add_operand(op_span, None, 0)
                    operand_span.defining_op.add_value(ctx, defining_op)
                    used |= walk_operation(defining_op, operand_span.defining_op)
                case PdlInterpGetValueType(result=result):
                    op_span.add_operand_type_range(ctx, result)
                    used |= walk_type_range(result)
                case PdlInterpIsNotNull():
                    used = True
        return used

    def walk_result_range(value: SSAValue, op_span: OperationSpan) -> bool:
        used = False
        for use in value.uses:
            match use.operation:
                case PdlInterpAreEqual():
                    used = True
                case PdlInterpExtract(index=index, result=result):
                    operand_span = add_result(op_span, result, index.value.data)
                    used |= walk_result(result, operand_span)
                case PdlInterpGetDefiningOp(inputOp=defining_op):
                    op_span.add_value(ctx, defining_op)
                    used |= walk_operation(defining_op, op_span)
                case PdlInterpGetValueType(result=result):
                    op_span.add_result_type_range(ctx, result)
                    used |= walk_type_range(result)
                case PdlInterpIsNotNull():
                    used = True
        return used

    def walk_type_range(value: SSAValue) -> bool:
        used = False
        for use in value.uses:
            match use.operation:
                case PdlInterpAreEqual():
                    used = True
                case PdlInterpCheckTypes():
                    used = True
                case PdlInterpExtract(result=result):
                    used |= walk_type(result)
                case PdlInterpIsNotNull():
                    used = True
                case PdlSwitchTypes():
                    used = True
        return used

    def walk_type(value: SSAValue) -> bool:
        used = False
        for use in value.uses:
            match use.operation:
                case PdlInterpAreEqual():
                    used = True
                case PdlInterpCheckType():
                    used = True
                case PdlInterpIsNotNull():
                    used = True
                case PdlSwitchType():
                    used = True
                case _:
                    raise UnsupportedPatternFeature(use)
        return used

    walk_operation(root_value, root)

    return root, ctx
