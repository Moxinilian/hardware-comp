from dataclasses import dataclass
from typing import cast
from xdsl.ir import Operation, Attribute, ParametrizedAttribute, SSAValue
from xdsl.pattern_rewriter import (
    RewritePattern,
    PatternRewriter,
)
from xdsl.dialects.builtin import (
    IntegerAttr,
    IntegerType,
    DictionaryAttr,
    ArrayAttr,
)

from dialects.comb import CombConcat, CombExtract, CombICmp, CombOr, ICmpPredicate
from dialects.hw import HwConstant
from dialects.hw_op import (
    HwOpOperandTypeIs,
    HwOperation,
    HwOpGetOpcode,
    HwOpHasOperand,
    HwOpHasResult,
    HwOpGetOperandOffset,
    HwOpOperandAmountIs,
    HwOpIsOperation,
)

from encoder import OperationContext

import math


@dataclass
class OperationNotFoundInContext(Exception):
    operation_name: str


@dataclass
class LowerIntegerHwOperation(RewritePattern):
    ctx: OperationContext

    def __init__(self, ctx: OperationContext):
        self.ctx = ctx

    @staticmethod
    def is_in_set_replace_helper(
        rewriter: PatternRewriter,
        replace_op: Operation,
        hw_op: SSAValue,
        opcode_set: list[int],
        opcode_max_width: int,
    ):
        """
        Helper to replace a boolean op with a check of whether the given HwOp SSAValue `hw_op`
        is one of the operations in the `opcode_set`.
        """
        if len(opcode_set) == 0:
            false = HwConstant.from_attr(IntegerAttr.from_int_and_width(0, 1))
            rewriter.replace_op(replace_op, false)
            return
        hw_op_typ = cast(HwOperation, hw_op.typ)
        extracted_opcode = CombExtract.from_values(
            hw_op, hw_op_typ.opcode_integer.width.data, 0
        )
        rewriter.insert_op_before(extracted_opcode, replace_op)
        opcode_checks: list[SSAValue] = []
        for opcode in opcode_set:
            constant = HwConstant.from_attr(
                IntegerAttr.from_int_and_width(opcode, opcode_max_width)
            )
            rewriter.insert_op_before(constant, replace_op)
            check = CombICmp.from_values(
                extracted_opcode.output, constant.output, ICmpPredicate.EQ
            )
            rewriter.insert_op_before(check, replace_op)
            opcode_checks.append(check.output)
        big_or = CombOr.from_values(opcode_checks)
        rewriter.replace_op(replace_op, big_or)

    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter) -> None:
        visited = set()

        def replace_hwop(attribute: Attribute) -> Attribute:
            if isinstance(attribute, HwOperation):
                return IntegerType(attribute.get_bit_width())
            elif isinstance(attribute, ArrayAttr):
                return ArrayAttr([replace_hwop(attr) for attr in attribute.data])
            elif isinstance(attribute, DictionaryAttr):
                return DictionaryAttr(
                    {k: replace_hwop(v) for k, v in attribute.data.items()}
                )
            elif isinstance(attribute, ParametrizedAttribute):
                return type(attribute).new(
                    [replace_hwop(attr) for attr in attribute.parameters]
                )
            return attribute

        def lower_op(op: Operation):
            if op in visited:
                return
            visited.add(op)

            # Before lowering, propagate the lowering to users so type information is not lost
            for result in op.results:
                for use in list(result.uses):
                    lower_op(use.operation)

            # Also lower the users of potentially created block arguments within the current op
            for region in op.regions:
                for block in region.blocks:
                    for arg in block.args:
                        for use in list(arg.uses):
                            lower_op(use.operation)

            # If the operation is a HwOpGetOpcode, extract the opcode in the operation
            if isinstance(op, HwOpGetOpcode):
                hw_op_typ = cast(HwOperation, op.op.typ)
                extracted_opcode = CombExtract.from_values(
                    op.op, hw_op_typ.opcode_integer.width.data, 0
                )
                rewriter.replace_op(op, extracted_opcode)
                return

            # If the operation is a HwOpHasOperand, check the opcode against all operations that have this operand
            if isinstance(op, HwOpHasOperand):
                expected_operand = op.operand.value.data
                opcode_max_width = cast(
                    HwOperation, op.op.typ
                ).opcode_integer.width.data
                opcodes_which_do: list[int] = [
                    x.opcode
                    for x in self.ctx.operations.values()
                    if expected_operand < len(x.operand_types)
                    and x.opcode.bit_count() <= opcode_max_width
                ]
                self.is_in_set_replace_helper(
                    rewriter, op, op.op, opcodes_which_do, opcode_max_width
                )
                return

            # If the operation is a HwOpOperandTypeIs, check the opcode against all operations that have the
            # expected type at the expected operand.
            if isinstance(op, HwOpOperandTypeIs):
                expected_operand = op.operand.value.data
                opcode_max_width = cast(
                    HwOperation, op.op.typ
                ).opcode_integer.width.data
                opcodes_which_do: list[int] = [
                    x.opcode
                    for x in self.ctx.operations.values()
                    if expected_operand < len(x.operand_types)
                    and x.operand_types[expected_operand] == op.expected_type
                    and x.opcode.bit_count() <= opcode_max_width
                ]
                self.is_in_set_replace_helper(
                    rewriter, op, op.op, opcodes_which_do, opcode_max_width
                )
                return

            # If the operation is a HwOpOperandAmountIs, check the opcode against all operations that have this operand
            if isinstance(op, HwOpOperandAmountIs):
                expected_amount = op.amount.value.data
                opcode_max_width = cast(
                    HwOperation, op.op.typ
                ).opcode_integer.width.data
                opcodes_which_do: list[int] = [
                    x.opcode
                    for x in self.ctx.operations.values()
                    if expected_amount == len(x.operand_types)
                    and x.opcode.bit_count() <= opcode_max_width
                ]
                self.is_in_set_replace_helper(
                    rewriter, op, op.op, opcodes_which_do, opcode_max_width
                )
                return

            # If the operation is a HwOpHasResult, check the opcode against all operations that have a result
            if isinstance(op, HwOpHasResult):
                opcode_max_width = cast(
                    HwOperation, op.op.typ
                ).opcode_integer.width.data
                opcodes_which_do: list[int] = [
                    x.opcode
                    for x in self.ctx.operations.values()
                    if x.result_type and x.opcode.bit_count() <= opcode_max_width
                ]
                self.is_in_set_replace_helper(
                    rewriter, op, op.op, opcodes_which_do, opcode_max_width
                )
                return

            # If the operation is a HwOpIsOperation, check the opcode against the desired operation
            if isinstance(op, HwOpIsOperation):
                opcode_max_width = cast(
                    HwOperation, op.op.typ
                ).opcode_integer.width.data
                op_name = op.op_name.data
                if not op_name in self.ctx.operations:
                    raise OperationNotFoundInContext(op_name)
                self.is_in_set_replace_helper(
                    rewriter,
                    op,
                    op.op,
                    [self.ctx.operations[op_name].opcode],
                    opcode_max_width,
                )
                return

            # If the operation is a HwOpGetOperandOffset, extract the offset from the operation
            if isinstance(op, HwOpGetOperandOffset):
                hw_op_typ = cast(HwOperation, op.op.typ)
                expected_operand = op.operand.value.data
                offset_width = hw_op_typ.operand_offset_integer.width.data
                opcode_width = hw_op_typ.opcode_integer.width.data
                extracted_offset = CombExtract.from_values(
                    op.op, offset_width, opcode_width + expected_operand * offset_width
                )
                rewriter.replace_op(op, extracted_offset)
                return

            # If the operation is unrelated to HwOperation, simply lower its attributes
            for k, v in op.attributes.items():
                op.attributes[k] = replace_hwop(v)

            # Then lower its return types
            for result in op.results:
                result.typ = replace_hwop(result.typ)

            # Finally lower potentially created block arguments
            for region in op.regions:
                for block in region.blocks:
                    for arg in block.args:
                        rewriter.modify_block_argument_type(arg, replace_hwop(arg.typ))

        for region in op.regions:
            for op in list(region.ops):
                lower_op(op)
