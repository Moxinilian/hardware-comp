from typing import cast
from xdsl.irdl import (
    irdl_op_definition,
    irdl_attr_definition,
    IRDLOperation,
    Operand,
    ParameterDef,
    result_def,
    attr_def,
    operand_def,
)
from xdsl.ir import (
    ParametrizedAttribute,
    Dialect,
    OpResult,
    SSAValue,
)
from xdsl.dialects.builtin import (
    IntegerAttr,
    IntegerType,
    i1,
)
from xdsl.utils.exceptions import VerifyException

from encoder import EncodingContext


@irdl_attr_definition
class HwOperation(ParametrizedAttribute):
    name = "hw_op.operation"

    kind_integer: ParameterDef[IntegerType]
    operand_offset_integer: ParameterDef[IntegerType]
    max_operand_amount: ParameterDef[IntegerAttr]

    @staticmethod
    def from_widths(
        kind_width: int, operand_offset_width: int, max_operand_amount: int
    ):
        assert kind_width.bit_length() <= 32
        assert operand_offset_width.bit_length() <= 32
        assert max_operand_amount.bit_length() <= 32
        return HwOperation(
            [
                IntegerType.from_width(kind_width),
                IntegerType.from_width(operand_offset_width),
                IntegerAttr.from_int_and_width(max_operand_amount, 32),
            ]
        )

    @staticmethod
    def from_encoding_ctx(enc_ctx: EncodingContext):
        return HwOperation.from_widths(
            enc_ctx.kind_width, enc_ctx.operand_offset_width, enc_ctx.max_operand_amount
        )


@irdl_op_definition
class HwOpGetKind(IRDLOperation):
    name = "hw_op.get_kind"

    op: Operand = operand_def(HwOperation)
    output: OpResult = result_def(IntegerType)

    def verify_(self) -> None:
        op_type = cast(HwOperation, self.op.typ)
        if op_type.kind_integer != self.output.typ:
            raise VerifyException("trying to get kind as the wrong type")


@irdl_op_definition
class HwOpGetOperandOffset(IRDLOperation):
    name = "hw_op.get_operand_offset"

    op: Operand = operand_def(HwOperation)
    operand: IntegerAttr = attr_def(IntegerAttr)
    output: OpResult = result_def(IntegerType)

    @staticmethod
    def from_operand(op: SSAValue, operand: int):
        return HwOpGetOperandOffset.create(
            operands=[op],
            result_types=[cast(HwOperation, op.typ).operand_offset_integer],
            attributes={"operand": IntegerAttr.from_index_int_value(operand)},
        )

    def verify_(self) -> None:
        op_type = cast(HwOperation, self.op.typ)
        if op_type.operand_offset_integer != self.output.typ:
            raise VerifyException("trying to get operand offset as the wrong type")
        if op_type.max_operand_amount.value.data <= self.operand.value.data:
            raise VerifyException("trying to fetch operand outside max range")


@irdl_op_definition
class HwOpHasOperand(IRDLOperation):
    name = "hw_op.has_operand"

    op: Operand = operand_def(HwOperation)
    operand: IntegerAttr = attr_def(IntegerAttr)
    output: OpResult = result_def(i1)

    @staticmethod
    def from_operand(op: SSAValue, operand: int):
        return HwOpGetOperandOffset.create(
            operands=[op],
            result_types=[i1],
            attributes={"operand": IntegerAttr.from_index_int_value(operand)},
        )

    def verify_(self) -> None:
        op_type = cast(HwOperation, self.op.typ)
        if op_type.max_operand_amount.value.data <= self.operand.value.data:
            raise VerifyException("trying to check operand outside max range")


HwOp = Dialect(
    [HwOpGetKind, HwOpGetOperandOffset, HwOpHasOperand],
    [HwOperation],
)
